"""
# ──────────────────────────────────────────────────────────────────────────────
# MWVSE TRADING PANEL — Data Models
# Engineered by @ghostwwn (https://github.com/ghostwwn)
# ──────────────────────────────────────────────────────────────────────────────
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class TradeAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    SHORT = "short"
    COVER = "cover"

class OrderType(str, Enum):
    MARKET = "Market"
    LIMIT = "Limit"
    STOP = "Stop"

class TradeOrder(BaseModel):
    secret: str = Field(..., description="Authentication secret configured in .env")
    ticker: str = Field(..., description="Ticker symbol (e.g. TSLA, NVDA, TQQQ)")
    action: TradeAction = Field(..., description="Trade action: buy, sell, short, cover")
    shares: Optional[int] = Field(default=None, description="Exact shares to trade")
    dollar_amount: Optional[float] = Field(default=None, description="Dollar amount to allocate")
    full_port: bool = Field(default=False, description="Set True only if allocating 100% buying power")
    order_type: OrderType = Field(default=OrderType.MARKET, description="Order type: Market or Limit")
    price: Optional[float] = Field(default=None, description="Limit trigger price")

class ExecutionResult(BaseModel):
    status: str = Field(..., description="SUCCESS, ERROR, or IGNORED")
    message: str = Field(..., description="Execution summary or rejection reason")
    ticker: str
    action: str
    shares: Optional[int] = None
    price: Optional[float] = None
    order_id: Optional[str] = None

class Holding(BaseModel):
    symbol: str
    shares: int
    pos_type: str = "Buy"  # Buy or Short
    price: float
    value: float
    gain_dollar: float
    gain_percent: float

Position = Holding

class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    net_worth: float
    today_return: str
    trades_count: int
    total_return: str

class PortfolioSnapshot(BaseModel):
    net_worth: float = 100000.0
    cash: float = 0.0
    buying_power: float = 0.0
    rank: int = 1
    total_players: int = 1
    today_gain_dollar: float = 0.0
    today_gain_pct: float = 0.0
    holdings: List[Holding] = []
    leaderboard: List[LeaderboardEntry] = []
    updated_at: str = ""

class AISignal(BaseModel):
    target_ticker: str
    action: str  # BUY or SHORT
    confidence: int  # 0 to 100
    reason: str
    suggested_shares: int = 25
