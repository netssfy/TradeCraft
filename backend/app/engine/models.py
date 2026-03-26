from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from app.data.market import BarInterval, Market


# ---------------------------------------------------------------------------
# Bar
# ---------------------------------------------------------------------------

@dataclass
class Bar:
    symbol: str
    market: Market
    interval: BarInterval
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


# ---------------------------------------------------------------------------
# Order enums
# ---------------------------------------------------------------------------

class Direction(Enum):
    BUY  = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT  = "limit"


class OrderStatus(Enum):
    PENDING    = "pending"
    SUBMITTED  = "submitted"
    PARTIAL    = "partial"
    FILLED     = "filled"
    CANCELLED  = "cancelled"


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

@dataclass
class Order:
    symbol: str
    market: Market
    direction: Direction
    order_type: OrderType
    quantity: float
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    limit_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    timeout_seconds: Optional[int] = None


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------

@dataclass
class Fill:
    order_id: str
    symbol: str
    market: Market
    direction: Direction
    quantity: float
    price: float
    commission: float
    timestamp: datetime


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    timestamp: datetime
    symbol: str
    direction: Direction
    quantity: float
    price: float
    commission: float


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------

@dataclass
class Position:
    symbol: str
    quantity: float
    avg_cost: float

    def unrealized_pnl(self, current_price: float) -> float:
        return (current_price - self.avg_cost) * self.quantity
