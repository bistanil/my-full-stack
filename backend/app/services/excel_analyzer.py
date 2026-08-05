import io
from typing import Any, Dict
import pandas as pd


def parse_screener_excel(file_content: bytes) -> Dict[str, Any]:
  """Parses Screener.in exported Excel file to retrieve fundamental financial data."""
  # Wrap the bytes object in io.BytesIO so pandas can treat it as a file-like stream
  excel_file = io.BytesIO(file_content)

  # Load the "Data Sheet" tab directly
  df = pd.read_excel(excel_file, sheet_name="Data Sheet")

  company_name = df.columns[1] if len(df.columns) > 1 else "Unknown Stock"

  def get_val(label: str):
    row = df[df.iloc[:, 0] == label]
    if not row.empty:
      val = row.iloc[0, 1]
      return float(val) if pd.notna(val) else None
    return None

  current_price = get_val("Current Price")
  market_cap = get_val("Market Capitalization")
  face_value = get_val("Face Value")

  # Extract historical P&L Sales and Profits
  pnl_idx = df[df.iloc[:, 0] == "PROFIT & LOSS"].index
  historical_sales = {}
  historical_profits = {}

  if not pnl_idx.empty:
    idx = pnl_idx[0]
    dates = df.iloc[idx + 1, 1:].dropna().tolist()
    sales = df.iloc[idx + 2, 1:].dropna().tolist()
    profits = df.iloc[idx + 15, 1:].dropna().tolist()

    for d, s, p in zip(dates, sales, profits):
      year_str = str(d)[:10]
      historical_sales[year_str] = float(s) if pd.notna(s) else 0
      historical_profits[year_str] = float(p) if pd.notna(p) else 0

  return {
    "company_name": str(company_name).strip(),
    "current_price": current_price,
    "market_cap": market_cap,
    "face_value": face_value,
    "historical_sales": historical_sales,
    "historical_profits": historical_profits,
  }