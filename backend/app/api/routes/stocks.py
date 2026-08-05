import uuid
from datetime import date
from typing import Any

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from sqlmodel import col, func, or_, select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Message,
    Stock,
    StockCreate,
    StockPattern,
    StockPatternCategory,
    StockPatternPublic,
    StockPatternSignal,
    StockPatternsPublic,
    StockPricePublic,
    StockPricesPublic,
    StockPublic,
    StocksPublic,
    StockUpdate,
)
from app.services.ai_stock_service import generate_ai_stock_analysis
from app.services.candlestick.detector import detect_and_save_patterns
from app.services.downloader.yahoo import YahooDownloader
from app.services.excel_analyzer import parse_screener_excel
from app.services.news_service import analyze_news_sentiment, fetch_stock_news_rss

router = APIRouter(prefix="/stocks", tags=["stocks"])


# -------------------------------------------------------------------
# 1. READ / LIST STOCKS
# -------------------------------------------------------------------
@router.get("/", response_model=StocksPublic)
def read_stocks(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: str | None = Query(
        default=None, description="Search by symbol or name"
    ),
) -> Any:
  """Retrieve stocks sorted by newest first with optional search filter."""
  conditions = []
  if search:
    search_term = f"%{search.strip()}%"
    conditions.append(
        or_(
            col(Stock.symbol).ilike(search_term),
            col(Stock.name).ilike(search_term),
        )
    )

  count_statement = select(func.count()).select_from(Stock)
  if conditions:
    count_statement = count_statement.where(*conditions)
  count = session.exec(count_statement).one()

  statement = select(Stock).order_by(col(Stock.created_at).desc())
  if conditions:
    statement = statement.where(*conditions)

  statement = statement.offset(skip).limit(limit)
  stocks = session.exec(statement).all()

  stocks_public = [StockPublic.model_validate(stock) for stock in stocks]
  return StocksPublic(data=stocks_public, count=count)


# -------------------------------------------------------------------
# 2. READ SINGLE STOCK BY ID
# -------------------------------------------------------------------
@router.get("/{id}", response_model=StockPublic)
def read_stock(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
  """Get stock by ID."""
  stock = session.get(Stock, id)
  if not stock:
    raise HTTPException(status_code=404, detail="Stock not found")
  return stock


# -------------------------------------------------------------------
# 3. CREATE SINGLE STOCK
# -------------------------------------------------------------------
@router.post("/", response_model=StockPublic)
def create_stock(
    *, session: SessionDep, current_user: CurrentUser, stock_in: StockCreate
) -> Any:
  """Create a new stock record (Admin restricted)."""
  if not current_user.is_superuser:
    raise HTTPException(status_code=403, detail="Not enough permissions")

  symbol_upper = stock_in.symbol.strip().upper()
  existing = session.exec(
      select(Stock).where(Stock.symbol == symbol_upper)
  ).first()
  if existing:
    raise HTTPException(
        status_code=400, detail="Stock ticker symbol already exists."
    )

  db_stock = Stock.model_validate(stock_in)
  db_stock.symbol = symbol_upper
  session.add(db_stock)
  session.commit()
  session.refresh(db_stock)
  return db_stock


# -------------------------------------------------------------------
# 4. UPDATE STOCK
# -------------------------------------------------------------------
@router.put("/{id}", response_model=StockPublic)
def update_stock(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    stock_in: StockUpdate,
) -> Any:
  """Update a stock record (Admin restricted)."""
  if not current_user.is_superuser:
    raise HTTPException(status_code=403, detail="Not enough permissions")

  stock = session.get(Stock, id)
  if not stock:
    raise HTTPException(status_code=404, detail="Stock not found")

  update_dict = stock_in.model_dump(exclude_unset=True)
  if "symbol" in update_dict and update_dict["symbol"]:
    update_dict["symbol"] = update_dict["symbol"].strip().upper()

  stock.sqlmodel_update(update_dict)
  session.add(stock)
  session.commit()
  session.refresh(stock)
  return stock


# -------------------------------------------------------------------
# 5. DELETE STOCK
# -------------------------------------------------------------------
@router.delete("/{id}")
def delete_stock(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
  """Delete a stock record (Admin restricted)."""
  if not current_user.is_superuser:
    raise HTTPException(status_code=403, detail="Not enough permissions")

  stock = session.get(Stock, id)
  if not stock:
    raise HTTPException(status_code=404, detail="Stock not found")

  session.delete(stock)
  session.commit()
  return Message(message="Stock deleted successfully")


# -------------------------------------------------------------------
# 6. BULK UPLOAD STOCKS (EXCEL / CSV FROM GOOGLE SHEETS)
# -------------------------------------------------------------------
@router.post("/upload-excel", response_model=Message)
def upload_stock_excel(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> Any:
  """Bulk ingest stock data from an exported Google Sheet (.xlsx, .xls, .csv).

  Updates existing stocks if symbol matches, or inserts new entries.
  """
  if not current_user.is_superuser:
    raise HTTPException(status_code=403, detail="Not enough permissions")

  filename = file.filename.lower() if file.filename else ""
  if not filename.endswith((".xlsx", ".xls", ".csv")):
    raise HTTPException(
        status_code=400,
        detail=(
            "Invalid file format. Upload a valid Excel (.xlsx, .xls) or CSV"
            " file."
        ),
    )

  try:
    if filename.endswith(".csv"):
      df = pd.read_csv(file.file)
    else:
      df = pd.read_excel(file.file)

    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.where(pd.notnull(df), None)

    processed_count = 0

    for _, row in df.iterrows():
      symbol_raw = row.get("symbol")
      name_raw = row.get("name")

      if not symbol_raw or not name_raw:
        continue

      symbol_clean = str(symbol_raw).strip().upper()
      name_clean = str(name_raw).strip()
      price_clean = (
          float(row.get("price", 0.0))
          if row.get("price") is not None
          else 0.0
      )
      market_cap_clean = (
          float(row.get("market_cap"))
          if row.get("market_cap") is not None
          else None
      )
      desc_clean = (
          str(row.get("description")).strip()
          if row.get("description") is not None
          else None
      )

      existing_stock = session.exec(
          select(Stock).where(Stock.symbol == symbol_clean)
      ).first()

      if existing_stock:
        existing_stock.name = name_clean
        existing_stock.price = price_clean
        existing_stock.market_cap = market_cap_clean
        existing_stock.description = desc_clean
        session.add(existing_stock)
      else:
        new_stock = Stock(
            symbol=symbol_clean,
            name=name_clean,
            price=price_clean,
            market_cap=market_cap_clean,
            description=desc_clean,
        )
        session.add(new_stock)

      processed_count += 1

    if processed_count == 0:
      raise HTTPException(
          status_code=400,
          detail=(
              "No readable rows found. Ensure sheet headers include 'symbol'"
              " and 'name'."
          ),
      )

    session.commit()
    return Message(
        message=(
            f"Successfully processed {processed_count} stock records from"
            " spreadsheet."
        )
    )

  except Exception as e:
    session.rollback()
    raise HTTPException(
        status_code=500, detail=f"Failed to process sheet dataset: {str(e)}"
    )


# -------------------------------------------------------------------
# 7. HISTORICAL PRICES & OHLC INGESTION
# -------------------------------------------------------------------
@router.post("/{id}/history", response_model=Message)
def upload_stock_history(
    id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> Any:
  """Upload OHLC historical CSV/Excel data for a specific stock ticker."""
  if not current_user.is_superuser:
    raise HTTPException(status_code=403, detail="Not enough permissions")

  stock = session.get(Stock, id)
  if not stock:
    raise HTTPException(status_code=404, detail="Stock not found")

  try:
    filename = file.filename.lower() if file.filename else ""
    if filename.endswith(".csv"):
      df = pd.read_csv(file.file)
    else:
      df = pd.read_excel(file.file)

    df.columns = [str(c).strip().lower() for c in df.columns]

    required_cols = {"date", "open", "high", "low", "close", "volume"}
    if not required_cols.issubset(set(df.columns)):
      raise HTTPException(
          status_code=400,
          detail=(
              "Missing required columns. Sheet must contain:"
              f" {required_cols}"
          ),
      )

    crud.save_stock_history(session=session, stock=stock, df=df)
    return Message(
        message=f"Successfully imported price history for {stock.symbol}"
    )

  except Exception as e:
    raise HTTPException(
        status_code=500, detail=f"Error saving stock history: {str(e)}"
    )


@router.get("/{id}/prices", response_model=StockPricesPublic)
def get_stock_prices(
    id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    limit: int = Query(default=200, le=1000),
) -> Any:
  """Get historical OHLC price rows for a given stock."""
  stock = session.get(Stock, id)
  if not stock:
    raise HTTPException(status_code=404, detail="Stock not found")

  prices = crud.get_stock_prices(session=session, stock_id=stock.id, limit=limit)
  return StockPricesPublic(
      data=[StockPricePublic.model_validate(p) for p in prices],
      count=len(prices),
  )


# -------------------------------------------------------------------
# 8. PATTERN SCREENER & DETECTED PATTERNS
# -------------------------------------------------------------------


@router.get("/{id}/patterns", response_model=StockPatternsPublic)
def get_stock_patterns(
    id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    pattern_category: StockPatternCategory | None = None,
    signal: StockPatternSignal | None = None,
    min_strength: int = Query(default=0, ge=0, le=100),
) -> Any:
    """Retrieve detected chart/candlestick patterns for a specific stock, auto-generating if empty."""
    print("5555555555555555555555555555555")
    print(id)
    stock = session.get(Stock, id)
    print("444444444444444444444444444444444444444444444")
    print(stock)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Step 1: Query database for existing patterns
    conditions = [col(StockPattern.stock_id) == stock.id]
    if pattern_category:
        conditions.append(col(StockPattern.pattern_category) == pattern_category)
    if signal:
        conditions.append(col(StockPattern.signal) == signal)
    if min_strength > 0:
        conditions.append(col(StockPattern.strength) >= min_strength)

    statement = (
        select(StockPattern)
        .where(*conditions)
        .order_by(col(StockPattern.pattern_date).desc())
    )
    patterns = session.exec(statement).all()

    # Step 2: Fallback — Auto-detect patterns if database table is empty for this stock
    if not patterns:
        patterns = detect_and_save_patterns(session=session, stock=stock)
        print("2222222222222222222222222222222222222222222222")
        # Apply optional filters if requested
        if pattern_category:
            patterns = [p for p in patterns if p.pattern_category == pattern_category]
        if signal:
            patterns = [p for p in patterns if p.signal == signal]
        if min_strength > 0:
            patterns = [p for p in patterns if (p.strength or 0) >= min_strength]

    return StockPatternsPublic(
        data=[StockPatternPublic.model_validate(p) for p in patterns],
        count=len(patterns),
    )


@router.get("/patterns/screener", response_model=StockPatternsPublic)
def screen_patterns(
    session: SessionDep,
    current_user: CurrentUser,
    target_date: date | None = Query(
        default=None, description="Filter by detection date"
    ),
    signal: StockPatternSignal | None = Query(
        default=None, description="BUY, SELL, or NEUTRAL"
    ),
    category: StockPatternCategory | None = Query(
        default=None, description="Pattern category"
    ),
    min_strength: int = Query(default=50, ge=0, le=100),
    skip: int = 0,
    limit: int = 100,
) -> Any:
  """Screen across all stocks to find active patterns matching signal/strength parameters."""
  conditions = [col(StockPattern.strength) >= min_strength]

  if target_date:
    conditions.append(col(StockPattern.pattern_date) == target_date)
  if signal:
    conditions.append(col(StockPattern.signal) == signal)
  if category:
    conditions.append(col(StockPattern.pattern_category) == category)

  statement = (
      select(StockPattern)
      .where(*conditions)
      .order_by(col(StockPattern.pattern_date).desc())
      .offset(skip)
      .limit(limit)
  )
  patterns = session.exec(statement).all()

  count_statement = (
      select(func.count()).select_from(StockPattern).where(*conditions)
  )
  count = session.exec(count_statement).one()

  return StockPatternsPublic(
      data=[StockPatternPublic.model_validate(p) for p in patterns],
      count=count,
  )


# -------------------------------------------------------------------
# 9. LIVE NEWS & SENTIMENT
# -------------------------------------------------------------------
@router.get("/{id}/news")
def get_stock_news(
    id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
  """Fetch live news and sentiment analysis for a given stock."""
  stock = session.get(Stock, id)
  if not stock:
    raise HTTPException(status_code=404, detail="Stock not found")

  raw_articles = fetch_stock_news_rss(stock.symbol, stock.name)

  analyzed_news = []
  for article in raw_articles:
    sentiment_data = analyze_news_sentiment(article["title"], stock.name)

    analyzed_news.append({
        "title": article["title"],
        "url": article["link"],
        "source": article["source"],
        "published_at": article["published"],
        "sentiment": sentiment_data.get("sentiment"),
        "score": sentiment_data.get("score"),
        "positive_points": sentiment_data.get("positive_points", []),
        "negative_points": sentiment_data.get("negative_points", []),
    })

  return {"stock": stock.symbol, "news": analyzed_news}


# -------------------------------------------------------------------
# 10. TECHNICAL INDICATOR COMPUTATION
# -------------------------------------------------------------------
@router.post("/{id}/calculate-indicators", response_model=Message)
def calculate_stock_indicators(
    id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
  """Trigger TA-Lib Engine to compute EMAs, RSI, MACD, ATR & BBands for a given stock."""
  from app.services.indicators.talib_engine import TAEngine

  stock = session.get(Stock, id)
  if not stock:
    raise HTTPException(status_code=404, detail="Stock not found")

  engine = TAEngine(session)
  count = engine.process_stock(stock.id)

  return Message(
      message=f"Successfully updated {count} indicator rows for {stock.symbol}"
  )
#-----------------------stock history--------------------
@router.post("/{symbol}/download-history")
def download_history(
    symbol: str,
    session: SessionDep,
):

    stock = crud.get_stock_by_symbol(
        session=session,
        symbol=symbol,
    )

    if not stock:
        raise HTTPException(
            status_code=404,
            detail="Stock not found",
        )
    df = YahooDownloader.download_stock_history(symbol)
    crud.save_stock_history(
        session=session,
        stock=stock,
        df=df,
    )

    return {
        "symbol": symbol,
        "records": len(df),
    }

#-----------------------all stock history--------------------

@router.post("/download-all")
def download_all(
    session: SessionDep,
):

    stocks = crud.get_all_stocks(session)

    total = 0

    for stock in stocks:

        try:

            df = YahooDownloader.download_stock_history(
                stock.symbol
            )

            crud.save_stock_history(
                session,
                stock,
                df,
            )

            total += 1

        except Exception as ex:

            print(ex)

    return {
        "completed": total
    }


#---------excel analyze-----------------------------------------------------

@router.post("/analyze-excel")
async def analyze_stock_excel(file: UploadFile = File(...)):
    """Analyze Screener Excel file and return structured financial & AI insights."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400, detail="Only Excel files (.xlsx, .xls) are accepted."
        )

    try:
        content = await file.read()
        parsed_metrics = parse_screener_excel(content)
        ai_recommendation = generate_ai_stock_analysis(parsed_metrics)

        return {
            "status": "success",
            "parsed_metrics": parsed_metrics,
            "ai_analysis": ai_recommendation,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze stock file: {str(e)}"
        )