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
    """独立的交易主体，通过组合持有 Strategy、OrderManager、Portfolio。

    实例化方式：
    - 直接构造（测试 / Engine 内部）
    - Trader.from_dir(name, store, ...)  从 data/traders/{name}/ 目录加载
    """

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
        commission_rate: float = 0.0003,
        order_timeout_seconds: int = 300,
        traits: Optional[dict] = None,
    ) -> None:
        self.id = id
        self.market = market
        self.strategy = strategy
        self.order_manager = order_manager
        self.portfolio = portfolio
        self.repository = repository
        self.simulator = simulator
        self.allowed_symbols = allowed_symbols
        self.commission_rate = commission_rate
        self.order_timeout_seconds = order_timeout_seconds
        self.traits: dict = traits or {}

    # ------------------------------------------------------------------
    # Factory — 从 trader 目录加载
    # ------------------------------------------------------------------

    @classmethod
    def from_dir(
        cls,
        name: str,
        store: "TraderStore",  # noqa: F821 — resolved at runtime
        repository: MarketRepository,
        simulator: "Simulator",
    ) -> "Trader":
        """从 data/traders/{name}/ 目录加载 Trader。

        trader.json 必须包含：
          - market: str
          - initial_cash: float
        可选字段：
          - allowed_symbols: list[str]
          - commission_rate: float
          - order_timeout_seconds: int
          - strategy_params: dict
        """
        from app.engine.events import EventBus
        from app.engine.trader_store import TraderStore
        from app.trading.strategy_loader import StrategyLoader

        info = store.load_info(name)

        market = Market(info["market"])
        initial_cash = float(info["initial_cash"])
        allowed_symbols: Optional[List[str]] = info.get("allowed_symbols")
        commission_rate: float = float(info.get("commission_rate", 0.0003))
        order_timeout_seconds: int = int(info.get("order_timeout_seconds", 300))
        traits: dict = info.get("traits", {})

        # 加载策略
        strategy_path = store.get_strategy_path(name)
        result = StrategyLoader.load(strategy_path)
        if not result.success:
            raise ValueError(f"Failed to load strategy for trader '{name}': {result.error}")

        event_bus = EventBus()
        order_manager = OrderManager(
            trader_id=name,
            allowed_symbols=allowed_symbols,
            event_bus=event_bus,
        )

        # 尝试从持仓快照恢复（paper 模式续跑时有用）
        snapshot = store.load_portfolio(name)
        if snapshot is not None:
            cash = float(snapshot.get("cash", initial_cash))
        else:
            cash = initial_cash

        portfolio = Portfolio(initial_cash=cash)

        # 恢复持仓
        if snapshot:
            from app.engine.models import Position
            for sym, pos_data in snapshot.get("positions", {}).items():
                portfolio.positions[sym] = Position(
                    symbol=pos_data["symbol"],
                    quantity=float(pos_data["quantity"]),
                    avg_cost=float(pos_data["avg_cost"]),
                )

        return cls(
            id=name,
            market=market,
            strategy=result.strategy,
            order_manager=order_manager,
            portfolio=portfolio,
            repository=repository,
            simulator=simulator,
            allowed_symbols=allowed_symbols,
            commission_rate=commission_rate,
            order_timeout_seconds=order_timeout_seconds,
            traits=traits,
        )

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    def save_trades(self, store: "TraderStore", run_id: str, mode: str = "backtest") -> str:  # noqa: F821
        """将本次运行的成交记录写入 trades/{mode}/{run_id}.json。"""
        trades = [
            {
                "timestamp": t.timestamp.isoformat(),
                "symbol": t.symbol,
                "direction": t.direction.value,
                "quantity": t.quantity,
                "price": t.price,
                "commission": t.commission,
            }
            for t in self.portfolio.trade_history
        ]
        return store.save_trades(self.id, run_id, trades, mode)

    def save_portfolio(self, store: "TraderStore") -> str:  # noqa: F821
        """将当前持仓快照写入 portfolio/latest.json。"""
        snapshot = {
            "trader_id": self.id,
            "cash": self.portfolio.cash,
            "positions": {
                symbol: {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "avg_cost": pos.avg_cost,
                }
                for symbol, pos in self.portfolio.positions.items()
            },
        }
        return store.save_portfolio(self.id, snapshot)

    # ------------------------------------------------------------------
    # 运行时接口
    # ------------------------------------------------------------------

    def initialize(self, context: Context) -> None:
        """调用 strategy.initialize(context)。"""
        self.strategy.initialize(context)

    def on_bar(self, bar: Bar) -> None:
        """构造 Context，驱动策略，撮合挂单。"""
        from app.data.market import is_market_close, is_market_open

        context = Context(
            trader=self,
            repository=self.repository,
            current_time=bar.timestamp,
        )

        if is_market_open(self.market, bar.timestamp):
            self.strategy.on_market_open(context, bar)

        self.strategy.on_bar(context, bar)

        if is_market_close(self.market, bar.timestamp):
            self.strategy.on_market_close(context, bar)

        self.order_manager.cancel_expired(bar.timestamp)

        for order in self.order_manager.get_open_orders():
            fill = self.simulator.match(order, bar)
            if fill is not None:
                self.order_manager.process_fill(fill)
                self.portfolio.update_on_fill(fill)
