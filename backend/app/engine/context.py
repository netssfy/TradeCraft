from __future__ import annotations

from bisect import bisect_left
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from app.data.market import BarInterval
from app.data.repository import MarketRepository
from app.engine.models import Bar, Order, OrderType

if TYPE_CHECKING:
    from app.engine.portfolio import Portfolio


_HISTORY_SERIES_CACHE: Dict[Tuple[int, str, str, str], Tuple[List[datetime], List[Bar]]] = {}


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

        market = self._trader.market  # type: ignore[attr-defined]
        cache_key = (id(self._repository), market.value, symbol, interval.value)
        cached = _HISTORY_SERIES_CACHE.get(cache_key)

        # Load full local series once, then serve history slices with binary search.
        # This removes repeated parquet scans for every on_bar callback.
        if cached is None or (cached[0] and end > cached[0][-1]):
            series = self._repository.read(
                symbol=symbol,
                market=market,
                interval=interval,
                start=datetime(1900, 1, 1, tzinfo=timezone.utc),
                end=datetime(2100, 1, 1, tzinfo=timezone.utc),
            )
            times = [_bar_timestamp_utc(b) for b in series]
            cached = (times, series)
            _HISTORY_SERIES_CACHE[cache_key] = cached

        times, series = cached
        if not times:
            return []

        # Find first index where timestamp >= end, so result is strictly before end.
        idx = bisect_left(times, end)
        start_idx = max(0, idx - n)
        return series[start_idx:idx]


def _bar_timestamp_utc(bar: Bar) -> datetime:
    """Return bar.timestamp as a UTC-aware datetime for comparison."""
    ts = bar.timestamp
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)
