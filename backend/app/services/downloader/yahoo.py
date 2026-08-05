from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd
import yfinance as yf


class YahooDownloader:

    @staticmethod
    def download_stock_history(
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Download historical OHLCV data from Yahoo Finance.

        Example:
            HAL -> HAL.NS
        """

        yahoo_symbol = f"{symbol}.NS"

        df = yf.download(
            tickers=yahoo_symbol,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        if df.empty:
            raise Exception(f"No data found for {symbol}")

        df.reset_index(inplace=True)

        df.rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
            },
            inplace=True,
        )

        df["symbol"] = symbol

        return df