import uuid
from datetime import UTC, date as DateType, datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import EmailStr
from sqlalchemy import BigInteger, DateTime, Index, Text
from sqlmodel import Column, Field, JSON, Relationship, SQLModel


def get_datetime_utc() -> datetime:
  return datetime.now(UTC)


# ==========================================
# ENUMS
# ==========================================


class StockPatternCategory(str, Enum):
  CANDLESTICK = "Candlestick"
  CHART = "Chart"
  BREAKOUT = "Breakout"
  VOLUME = "Volume"
  MOMENTUM = "Momentum"
  SUPPORT_RESISTANCE = "Support Resistance"
  CUSTOM = "Custom"
  AI = "AI"


class StockPatternSignal(str, Enum):
  BUY = "BUY"
  SELL = "SELL"
  NEUTRAL = "NEUTRAL"


class DetectedBy(str, Enum):
  TALIB = "TA-Lib"
  CUSTOM = "Custom"
  AI = "AI"
  USER = "User"


# ==========================================
# USER MODELS
# ==========================================


class UserBase(SQLModel):
  email: EmailStr = Field(unique=True, index=True, max_length=255)
  is_active: bool = True
  is_superuser: bool = False
  full_name: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
  password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
  email: EmailStr = Field(max_length=255)
  password: str = Field(min_length=8, max_length=128)
  full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(SQLModel):
  email: EmailStr | None = Field(default=None, max_length=255)
  is_active: bool | None = None
  is_superuser: bool | None = None
  full_name: str | None = Field(default=None, max_length=255)
  password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
  full_name: str | None = Field(default=None, max_length=255)
  email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
  current_password: str = Field(min_length=8, max_length=128)
  new_password: str = Field(min_length=8, max_length=128)


class User(UserBase, table=True):
  id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
  hashed_password: str
  created_at: datetime | None = Field(
      default_factory=get_datetime_utc,
      sa_type=DateTime(timezone=True),
  )
  items: list["Item"] = Relationship(
      back_populates="owner",
      sa_relationship_kwargs={"cascade": "all, delete-orphan"},
  )


class UserPublic(UserBase):
  id: uuid.UUID
  created_at: datetime | None = None


class UsersPublic(SQLModel):
  data: list[UserPublic]
  count: int


# ==========================================
# ITEM MODELS
# ==========================================


class ItemBase(SQLModel):
  title: str = Field(min_length=1, max_length=255)
  description: str | None = Field(
      default=None, sa_column=Column(Text, nullable=True)
  )


class ItemCreate(ItemBase):
  pass


class ItemUpdate(SQLModel):
  title: str | None = Field(default=None, min_length=1, max_length=255)
  description: str | None = Field(default=None)


class Item(ItemBase, table=True):
  id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
  created_at: datetime | None = Field(
      default_factory=get_datetime_utc,
      sa_type=DateTime(timezone=True),
  )
  owner_id: uuid.UUID = Field(
      foreign_key="user.id", nullable=False, ondelete="CASCADE"
  )
  owner: User | None = Relationship(back_populates="items")


class ItemPublic(ItemBase):
  id: uuid.UUID
  owner_id: uuid.UUID
  created_at: datetime | None = None


class ItemsPublic(SQLModel):
  data: list[ItemPublic]
  count: int


# ==========================================
# AUTH / GENERIC SCHEMAS
# ==========================================


class Message(SQLModel):
  message: str


class Token(SQLModel):
  access_token: str
  token_type: str = "bearer"


class TokenPayload(SQLModel):
  sub: str | None = None


class NewPassword(SQLModel):
  token: str
  new_password: str = Field(min_length=8, max_length=128)


# ==========================================
# STOCK MODEL
# ==========================================


class StockBase(SQLModel):
  symbol: str = Field(index=True, unique=True, max_length=50)
  name: str = Field(max_length=255)
  price: float = Field(default=0.0)
  market_cap: float | None = Field(default=None)
  description: str | None = Field(
      default=None, sa_column=Column(Text, nullable=True)
  )


class Stock(StockBase, table=True):
  id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
  created_at: datetime | None = Field(
      default_factory=get_datetime_utc,
      sa_type=DateTime(timezone=True),
  )

  # Relationships
  prices: list["StockPrice"] = Relationship(
      back_populates="stock",
      sa_relationship_kwargs={"cascade": "all, delete-orphan"},
  )
  patterns: list["StockPattern"] = Relationship(
      back_populates="stock",
      sa_relationship_kwargs={"cascade": "all, delete-orphan"},
  )


class StockCreate(StockBase):
  pass


class StockUpdate(SQLModel):
  symbol: str | None = Field(default=None, max_length=50)
  name: str | None = Field(default=None, max_length=255)
  price: float | None = None
  market_cap: float | None = None
  description: str | None = None


class StockPublic(StockBase):
  id: uuid.UUID
  created_at: datetime | None = None


class StocksPublic(SQLModel):
  data: list[StockPublic]
  count: int


# ==========================================
# STOCK PRICE MODEL
# ==========================================


class StockPriceBase(SQLModel):
  date: DateType = Field(...)
  open: float
  high: float
  low: float
  close: float
  adj_close: float | None = None
  volume: int = Field(sa_column=Column(BigInteger, nullable=False))


class StockPrice(StockPriceBase, table=True):
  id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
  stock_id: uuid.UUID = Field(
      foreign_key="stock.id", nullable=False, index=True, ondelete="CASCADE"
  )
  created_at: datetime | None = Field(
      default_factory=get_datetime_utc,
      sa_type=DateTime(timezone=True),
  )

  # Relationships
  stock: Optional[Stock] = Relationship(back_populates="prices")
  patterns: list["StockPattern"] = Relationship(
      back_populates="stock_price",
      sa_relationship_kwargs={"cascade": "all, delete-orphan"},
  )

  def to_ta_dict(self) -> dict:
    return {
        "timestamp": int(
            datetime.combine(self.date, datetime.min.time()).timestamp()
        ),
        "open": float(self.open),
        "high": float(self.high),
        "low": float(self.low),
        "close": float(self.close),
        "volume": float(self.volume),
    }


class StockPriceCreate(StockPriceBase):
  stock_id: uuid.UUID


class StockPriceUpdate(SQLModel):
  date: DateType | None = None
  open: float | None = None
  high: float | None = None
  low: float | None = None
  close: float | None = None
  adj_close: float | None = None
  volume: int | None = None


class StockPricePublic(StockPriceBase):
  id: uuid.UUID
  stock_id: uuid.UUID
  created_at: datetime | None = None


class StockPricesPublic(SQLModel):
  data: list[StockPricePublic]
  count: int


# ==========================================
# STOCK NEWS MODEL
# ==========================================


class StockNews(SQLModel, table=True):
  id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
  stock_id: uuid.UUID = Field(foreign_key="stock.id", index=True)
  title: str
  url: str
  source: str
  published_at: datetime
  sentiment: str  # "POSITIVE", "NEGATIVE", "NEUTRAL"
  score: float

  positive_points: List[str] = Field(
      sa_column=Column(JSON, nullable=False, default=list)
  )
  negative_points: List[str] = Field(
      sa_column=Column(JSON, nullable=False, default=list)
  )

  created_at: datetime = Field(
      default_factory=lambda: datetime.now(timezone.utc)
  )


# ==========================================
# STOCK INDICATOR MODEL
# ==========================================


class StockIndicatorBase(SQLModel):
  date: DateType = Field(...)

  ema_20: float | None = None
  ema_50: float | None = None
  ema_200: float | None = None

  rsi_14: float | None = None
  adx_14: float | None = None

  macd: float | None = None
  macd_signal: float | None = None
  macd_hist: float | None = None

  atr_14: float | None = None
  bb_upper: float | None = None
  bb_middle: float | None = None
  bb_lower: float | None = None


class StockIndicator(StockIndicatorBase, table=True):
  id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
  stock_id: uuid.UUID = Field(
      foreign_key="stock.id", nullable=False, index=True, ondelete="CASCADE"
  )
  created_at: datetime | None = Field(
      default_factory=get_datetime_utc,
      sa_type=DateTime(timezone=True),
  )


class StockIndicatorCreate(StockIndicatorBase):
  stock_id: uuid.UUID


class StockIndicatorPublic(StockIndicatorBase):
  id: uuid.UUID
  stock_id: uuid.UUID
  created_at: datetime | None = None


# ==========================================
# PATTERN ENGINE MODEL (StockPattern)
# ==========================================


class StockPatternBase(SQLModel):
  pattern_date: DateType = Field(...)
  pattern_name: str = Field(max_length=100, index=True)
  pattern_category: StockPatternCategory = Field(
      default=StockPatternCategory.CANDLESTICK
  )
  signal: StockPatternSignal = Field(default=StockPatternSignal.NEUTRAL)
  strength: int = Field(default=0, ge=0, le=100)
  confidence: float = Field(default=0.0, ge=0.0, le=100.0)
  score: float = Field(default=0.0)
  candle_index: int | None = None
  timeframe: str = Field(default="1D", max_length=10)
  detected_by: DetectedBy = Field(default=DetectedBy.TALIB)
  remarks: str | None = Field(default=None, sa_column=Column(Text, nullable=True))


class StockPattern(StockPatternBase, table=True):
  id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
  stock_id: uuid.UUID = Field(
      foreign_key="stock.id", nullable=False, index=True, ondelete="CASCADE"
  )
  price_id: uuid.UUID | None = Field(
      default=None,
      foreign_key="stockprice.id",
      index=True,
      ondelete="CASCADE",
  )

  created_at: datetime = Field(
      default_factory=get_datetime_utc,
      sa_type=DateTime(timezone=True),
  )

  # Relationships
  stock: Optional[Stock] = Relationship(back_populates="patterns")
  stock_price: Optional[StockPrice] = Relationship(back_populates="patterns")

  __table_args__ = (
      Index("idx_stock_patterns_stock_date", "stock_id", "pattern_date"),
  )


class StockPatternCreate(StockPatternBase):
  stock_id: uuid.UUID
  price_id: uuid.UUID | None = None


class StockPatternUpdate(SQLModel):
  pattern_date: DateType | None = None
  pattern_name: str | None = None
  pattern_category: StockPatternCategory | None = None
  signal: StockPatternSignal | None = None
  strength: int | None = None
  confidence: float | None = None
  score: float | None = None
  candle_index: int | None = None
  timeframe: str | None = None
  detected_by: DetectedBy | None = None
  remarks: str | None = None


class StockPatternPublic(StockPatternBase):
  id: uuid.UUID
  stock_id: uuid.UUID
  price_id: uuid.UUID | None = None
  created_at: datetime


class StockPatternsPublic(SQLModel):
  data: list[StockPatternPublic]
  count: int