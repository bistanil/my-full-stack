import uuid
from datetime import date
from typing import Any, List, Optional

import pandas as pd
from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import (
    Item,
    ItemCreate,
    StockPattern,
    StockPatternCreate,
    Stock,
    StockCreate,
    StockIndicator,
    StockIndicatorCreate,
    StockPrice,
    StockPriceCreate,
    StockUpdate,
    User,
    UserCreate,
    UserUpdate,
)

# Dummy hash to use for timing attack prevention when user is not found
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


# ==========================================
# USER CRUD
# ==========================================

def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        verify_password(password, DUMMY_HASH)
        return None
    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user


# ==========================================
# ITEM CRUD
# ==========================================

def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


# ==========================================
# STOCK & STOCK PRICE CRUD
# ==========================================

def get_stock_by_symbol(*, session: Session, symbol: str) -> Stock | None:
    statement = select(Stock).where(Stock.symbol == symbol.upper())
    return session.exec(statement).first()


def create_stock(*, session: Session, stock_in: StockCreate) -> Stock:
    stock_in.symbol = stock_in.symbol.upper()
    db_stock = Stock.model_validate(stock_in)
    session.add(db_stock)
    session.commit()
    session.refresh(db_stock)
    return db_stock


def save_stock_history(session: Session, stock: Stock, df: pd.DataFrame):
    if df.empty:
        return

    # 1. Flatten MultiIndex columns if present (e.g. from yfinance / YahooDownloader)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 2. Normalize column names to lowercase for safe access
    df.columns = [str(col).lower().strip() for col in df.columns]

    # Fetch existing dates to avoid duplicate key errors
    existing_dates = set(
        session.exec(
            select(StockPrice.date).where(StockPrice.stock_id == stock.id)
        ).all()
    )

    new_prices = []

    for idx, row in df.iterrows():
        # Get date from a 'date' column or from index
        if "date" in df.columns:
            raw_date = row["date"]
        else:
            raw_date = idx

        # Parse date safely
        if hasattr(raw_date, "date"):
            record_date = raw_date.date()
        else:
            record_date = pd.to_datetime(raw_date).date()

        if record_date in existing_dates:
            continue

        # Extract prices using fallback options (open/close or adj_close)
        open_val = row.get("open", row.get("close", 0.0))
        high_val = row.get("high", open_val)
        low_val = row.get("low", open_val)
        close_val = row.get("close", row.get("adj_close", open_val))
        volume_val = row.get("volume", 0)

        new_prices.append(
            StockPrice(
                stock_id=stock.id,
                date=record_date,
                open=round(float(open_val), 2),
                high=round(float(high_val), 2),
                low=round(float(low_val), 2),
                close=round(float(close_val), 2),
                volume=int(volume_val),
            )
        )

    if new_prices:
        session.add_all(new_prices)
        session.commit()


def get_stock_prices(
        *, session: Session, stock_id: uuid.UUID, limit: int = 500
) -> List[StockPrice]:
    statement = (
        select(StockPrice)
        .where(StockPrice.stock_id == stock_id)
        .order_by(StockPrice.date.asc())
        .limit(limit)
    )
    return list(session.exec(statement).all())


# ==========================================
# PATTERN ENGINE CRUD
# ==========================================

def save_patterns(
        *, session: Session, patterns_in: List[StockPatternCreate]
) -> List[StockPattern]:
    db_patterns = []
    for pattern_data in patterns_in:
        db_pattern = StockPattern.model_validate(pattern_data)
        session.add(db_pattern)
        db_patterns.append(db_pattern)

    session.commit()
    for item in db_patterns:
        session.refresh(item)
    return db_patterns