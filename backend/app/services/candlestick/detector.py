import uuid
import pandas as pd
import talib
from typing import List
from sqlmodel import Session, select
from app.models import Stock, StockPrice, StockPattern, StockPatternCategory, StockPatternSignal, DetectedBy

# Map TA-Lib candlestick pattern functions
CANDLESTICK_PATTERNS = {
    "CDLDOJI": ("Doji", StockPatternSignal.NEUTRAL, StockPatternCategory.CANDLESTICK),
    "CDLHAMMER": ("Hammer", StockPatternSignal.BUY, StockPatternCategory.CANDLESTICK),
    "CDLENGULFING": ("Engulfing", StockPatternSignal.BUY, StockPatternCategory.CANDLESTICK),
    "CDLMORNINGSTAR": ("Morning Star", StockPatternSignal.BUY, StockPatternCategory.CANDLESTICK),
    "CDLEVENINGSTAR": ("Evening Star", StockPatternSignal.SELL, StockPatternCategory.CANDLESTICK),
    "CDLSHOOTINGSTAR": ("Shooting Star", StockPatternSignal.SELL, StockPatternCategory.CANDLESTICK),
}


def detect_and_save_patterns(session: Session, stock: Stock) -> List[StockPattern]:
    print("stock id9999999999999999999999")
    print(stock.id)

    """Fetch price history for stock, detect candlestick patterns, and store them."""

    # 1. Fetch OHLC history for the stock
    prices = session.exec(
        select(StockPrice)
        .where(StockPrice.stock_id == stock.id)
        .order_by(StockPrice.date.asc())
    ).all()
    print("33333333333333333333333333333333333333333")
    print(len(prices))
    if not prices or len(prices) < 5:
        return []

    # 2. Build Pandas DataFrame
    df = pd.DataFrame([
        {
            "id": p.id,
            "date": p.date,
            "open": float(p.open),
            "high": float(p.high),
            "low": float(p.low),
            "close": float(p.close),
            "volume": int(p.volume),
        }
        for p in prices
    ])

    new_patterns: List[StockPattern] = []

    # 3. Scan for patterns using TA-Lib
    for func_name, (pattern_display_name, default_signal, category) in CANDLESTICK_PATTERNS.items():
        if not hasattr(talib, func_name):
            continue

        pattern_func = getattr(talib, func_name)
        res = pattern_func(df["open"], df["high"], df["low"], df["close"])

        # Iterate over non-zero detections (TA-Lib returns +100 for bullish, -100 for bearish)
        for idx in res.index[res != 0]:
            val = res[idx]
            price_row = df.iloc[idx]

            # Determine bullish (+100) vs bearish (-100)
            signal = StockPatternSignal.BUY if val > 0 else (StockPatternSignal.SELL if val < 0 else default_signal)
            strength = abs(int(val))  # usually 100

            pattern_obj = StockPattern(
                id=uuid.uuid4(),
                stock_id=stock.id,
                price_id=price_row["id"],
                pattern_date=price_row["date"],
                pattern_name=pattern_display_name,
                pattern_category=category,
                signal=signal,
                strength=strength,
                confidence=float(strength),
                score=float(strength),
                candle_index=int(idx),
                timeframe="1D",
                detected_by=DetectedBy.TALIB,
                remarks=f"Auto-detected {pattern_display_name} signal on {price_row['date']}"
            )
            new_patterns.append(pattern_obj)

    # 4. Save detected patterns to database
    if new_patterns:
        session.add_all(new_patterns)
        session.commit()

        # Refresh objects after commit
        for p in new_patterns:
            session.refresh(p)

    return new_patterns