import logging
import uuid
from datetime import date
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from app import crud
from app.models import Stock, StockIndicator, StockPrice

logger = logging.getLogger(__name__)

# Try importing TA-Lib, fallback to pandas vectorized calculations if not installed
try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    logger.warning("TA-Lib C-library not detected. Falling back to native pandas/numpy indicators.")


class TAEngine:
    """
    Technical Analysis Engine responsible for reading StockPrice history,
    calculating indicators (EMA, RSI, MACD, ADX, ATR, Bollinger Bands),
    and syncing results into the StockIndicator database table.
    """

    def __init__(self, session: Session):
        self.session = session

    def fetch_price_df(self, stock_id: uuid.UUID) -> pd.DataFrame:
        """
        Retrieves historical price records for a stock ordered chronologically.
        """
        statement = (
            select(StockPrice)
            .where(StockPrice.stock_id == stock_id)
            .order_by(StockPrice.date.asc())
        )
        prices = self.session.exec(statement).all()

        if not prices:
            return pd.DataFrame()

        data = [
            {
                "price_id": p.id,
                "date": p.date,
                "open": float(p.open),
                "high": float(p.high),
                "low": float(p.low),
                "close": float(p.close),
                "volume": float(p.volume),
            }
            for p in prices
        ]
        df = pd.DataFrame(data)
        return df

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes technical indicators on the OHLCV DataFrame.
        """
        if df.empty or len(df) < 5:
            logger.warning("Insufficient price data points for indicator calculation.")
            return df

        close = df["close"].values
        high = df["high"].values
        low = df["low"].values

        if HAS_TALIB:
            # --- Exponential Moving Averages ---
            df["ema_20"] = talib.EMA(close, timeperiod=20)
            df["ema_50"] = talib.EMA(close, timeperiod=50)
            df["ema_200"] = talib.EMA(close, timeperiod=200)

            # --- RSI & ADX & ATR ---
            df["rsi_14"] = talib.RSI(close, timeperiod=14)
            df["adx_14"] = talib.ADX(high, low, close, timeperiod=14)
            df["atr_14"] = talib.ATR(high, low, close, timeperiod=14)

            # --- MACD ---
            macd, macd_signal, macd_hist = talib.MACD(
                close, fastperiod=12, slowperiod=26, signalperiod=9
            )
            df["macd"] = macd
            df["macd_signal"] = macd_signal
            df["macd_hist"] = macd_hist

            # --- Bollinger Bands ---
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
            )
            df["bb_upper"] = bb_upper
            df["bb_middle"] = bb_middle
            df["bb_lower"] = bb_lower

        else:
            # Fallback calculations if TA-Lib wrapper isn't installed
            close_s = df["close"]
            high_s = df["high"]
            low_s = df["low"]

            # EMAs
            df["ema_20"] = close_s.ewm(span=20, adjust=False).mean()
            df["ema_50"] = close_s.ewm(span=50, adjust=False).mean()
            df["ema_200"] = close_s.ewm(span=200, adjust=False).mean()

            # RSI
            delta = close_s.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df["rsi_14"] = 100 - (100 / (1 + rs))

            # MACD
            ema12 = close_s.ewm(span=12, adjust=False).mean()
            ema26 = close_s.ewm(span=26, adjust=False).mean()
            df["macd"] = ema12 - ema26
            df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
            df["macd_hist"] = df["macd"] - df["macd_signal"]

            # Bollinger Bands
            df["bb_middle"] = close_s.rolling(window=20).mean()
            std = close_s.rolling(window=20).std()
            df["bb_upper"] = df["bb_middle"] + (std * 2)
            df["bb_lower"] = df["bb_middle"] - (std * 2)

            # ATR
            tr1 = high_s - low_s
            tr2 = (high_s - close_s.shift(1)).abs()
            tr3 = (low_s - close_s.shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            df["atr_14"] = tr.rolling(window=14).mean()

            df["adx_14"] = None  # Complex calculation omitted in basic fallback

        # Clean NaN/Inf values for database compatibility
        df = df.replace({np.nan: None, np.inf: None, -np.inf: None})
        return df

    def save_indicators(self, stock_id: uuid.UUID, df: pd.DataFrame) -> int:
        """
        Upserts calculated indicator records into the stock_indicator table.
        """
        if df.empty or "ema_20" not in df.columns:
            return 0

        # Existing indicators lookup map (key: date)
        existing_stmt = select(StockIndicator).where(StockIndicator.stock_id == stock_id)
        existing_records = {
            ind.date: ind for ind in self.session.exec(existing_stmt).all()
        }

        saved_count = 0
        for row in df.itertuples():
            record_date = row.date

            # Prepare value dict safely handling potential Nones
            data_dict = {
                "stock_id": stock_id,
                "price_id": getattr(row, "price_id", None),
                "date": record_date,
                "ema_20": row.ema_20,
                "ema_50": row.ema_50,
                "ema_200": row.ema_200,
                "rsi_14": row.rsi_14,
                "adx_14": getattr(row, "adx_14", None),
                "macd": row.macd,
                "macd_signal": row.macd_signal,
                "macd_hist": row.macd_hist,
                "atr_14": row.atr_14,
            }

            if record_date in existing_records:
                # Update existing record
                db_obj = existing_records[record_date]
                for key, val in data_dict.items():
                    setattr(db_obj, key, val)
                self.session.add(db_obj)
            else:
                # Insert new record
                db_obj = StockIndicator(**data_dict)
                self.session.add(db_obj)

            saved_count += 1

        self.session.commit()
        return saved_count

    def process_stock(self, stock_id: uuid.UUID) -> int:
        """
        Main execution pipeline for a single stock ticker.
        """
        df = self.fetch_price_df(stock_id)
        if df.empty:
            return 0

        calculated_df = self.calculate_indicators(df)
        return self.save_indicators(stock_id, calculated_df)


# -------------------------------------------------------------------
# HELPER EXECUTION FUNCTION
# -------------------------------------------------------------------
def run_indicator_pipeline(session: Session, stock_id: Optional[uuid.UUID] = None) -> Dict[str, int]:
    """
    Triggers TA engine execution for a specific stock or all stocks in the database.
    """
    engine = TAEngine(session)
    results = {}

    if stock_id:
        stocks = [session.get(Stock, stock_id)]
    else:
        stocks = session.exec(select(Stock)).all()

    for stock in stocks:
        if stock:
            count = engine.process_stock(stock.id)
            results[stock.symbol] = count

    return results