from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

from app.data.market import Market
from app.data.repository import MarketRepository
from app.engine.context import Context
from app.engine.models import Bar
from app.engine.orders import OrderManager
from app.engine.portfolio import Portfolio

if TYPE_CHECKING:
    from app.adapters.simulator import Simulator
    from app.trading.strategy import Strategy

logger = logging.getLogger(__name__)


class Trader:
    """独立的交易主体，通过组合持有 Strategy、OrderManager、Portfolio。"""

    def __init__(
        self,
        id: str,
        market: Market,
        strategy: "Strategy",
        order_manager: OrderManager,
        portfolio: Portfolio,
        repository: MarketRepository,
        simulator: "Simulator",
        allowed_symbols: Optional[List[str]] = None,
    ) -> None:
        self.id = id
        self.market = market
        self.strategy = strategy
        self.order_manager = order_manager
        self.portfolio = portfolio
        self.repository = repository
        self.simulator = simulator
        self.allowed_symbols = allowed_symbols

    def initialize(self, context: Context) -> None:
        """调用 strategy.initialize(context)。"""
        self.strategy.initialize(context)

    def on_bar(self, bar: Bar) -> None:
        """构造 Context，驱动策略，撮合挂单。

        流程：
        1. 构造 Context(trader=self, repository=repository, current_time=bar.timestamp)
        2. 调用 strategy.on_bar(context, bar)
        3. 调用 order_manager.cancel_expired(bar.timestamp)
        4. 对每个挂单调用 simulator.match(order, bar)，有成交则更新 OrderManager 和 Portfolio
        """
        context = Context(
            trader=self,
            repository=self.repository,
            current_time=bar.timestamp,
        )

        self.strategy.on_bar(context, bar)

        self.order_manager.cancel_expired(bar.timestamp)

        for order in self.order_manager.get_open_orders():
            fill = self.simulator.match(order, bar)
            if fill is not None:
                self.order_manager.process_fill(fill)
                self.portfolio.update_on_fill(fill)
