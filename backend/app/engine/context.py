from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

import pandas as pd

from app.data.market import BarInterval
from app.data.repository import MarketRepository
from app.engine.models import Bar, Order, OrderType

if TYPE_CHECKING:
    from app.engine.portfolio import Portfolio


class Context:
    """策略执行时的沙箱接口，由 Engine 在每个 Bar 构造并传入策略。

    防止前视偏差：history() 只返回严格早于 current_time 的 Bar 数据。
    """

    def __init__(
        self,
        trader: object,
        repository: MarketRepository,
        current_time: datetime,
    ) -> None:
        # trader is typed as object to avoid circular imports at runtime;
        # it is expected to have .market, .portfolio, and .order_manager attributes.
        self._trader = trader
        self._repository = repository
        self._current_time = current_time

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def portfolio(self) -> "Portfolio":
        """只读访问当前 Trader 的 Portfolio。"""
        return self._trader.portfolio  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Order submission
    # ------------------------------------------------------------------

    def order(
        self,
        symbol: str,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
    ) -> Order:
        """提交订单到 OrderManager。

        根据 quantity 的正负自动判断买卖方向：
        - quantity > 0 → BUY
        - quantity < 0 → SELL（取绝对值作为委托数量）
        """
        from app.engine.models import Direction

        if quantity >= 0:
            direction = Direction.BUY
            qty = quantity
        else:
            direction = Direction.SELL
            qty = abs(quantity)

        new_order = Order(
            symbol=symbol,
            market=self._trader.market,  # type: ignore[attr-defined]
            direction=direction,
            order_type=order_type,
            quantity=qty,
            limit_price=limit_price,
            created_at=self._current_time,
        )
        return self._trader.order_manager.submit(new_order)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Historical data
    # ------------------------------------------------------------------

    def history(
        self,
        symbol: str,
        interval: BarInterval,
        n: int,
    ) -> List[Bar]:
        """查询历史 Bar，只返回严格早于 current_time 的数据，防止前视偏差。

        返回最近 n 根 Bar，按时间戳升序排列。
        """
        # Ensure current_time is timezone-aware (UTC) for consistent comparison
        if self._current_time.tzinfo is None:
            end = self._current_time.replace(tzinfo=timezone.utc)
        else:
            end = self._current_time.astimezone(timezone.utc)

        # Use a far-past start to retrieve all available history up to current_time
        start = pd.Timestamp.min.to_pydatetime().replace(tzinfo=timezone.utc)

        bars = self._repository.read(
            symbol=symbol,
            market=self._trader.market,  # type: ignore[attr-defined]
            interval=interval,
            start=start,
            end=end,
        )

        # Filter: strictly before current_time (exclude the current bar itself)
        bars = [b for b in bars if _bar_timestamp_utc(b) < end]

        # Return the last n bars (most recent), ascending order
        return bars[-n:] if n < len(bars) else bars


def _bar_timestamp_utc(bar: Bar) -> datetime:
    """Return bar.timestamp as a UTC-aware datetime for comparison."""
    ts = bar.timestamp
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)
