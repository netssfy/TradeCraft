from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional

from app.data.market import Market
from app.data.repository import MarketRepository
from app.engine.context import Context
from app.engine.models import Bar
from app.engine.orders import OrderManager
from app.engine.portfolio import Portfolio

if TYPE_CHECKING:
    from app.adapters.simulator import Simulator
    from app.engine.trader_store import TraderStore
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
        strategy_filename: Optional[str] = None,
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
        self.strategy_filename = strategy_filename

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
        strategy_filename: Optional[str] = None,
        require_active_strategy: bool = True,
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
        strategy_path = store.get_strategy_path(
            name,
            strategy_filename=strategy_filename,
            require_active=require_active_strategy,
        )
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
        snapshot = store.load_latest_portfolio(name)
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
            strategy_filename=os.path.basename(strategy_path),
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

    def save_portfolio(
        self,
        store: "TraderStore",
        mode: str = "paper",
        date: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> str:  # noqa: F821
        """将当前持仓快照追加到 portfolio/{mode}.json。

        若提供 date（YYYY-MM-DD）则写入带日期的记录；否则用当前 UTC 日期。
        """
        from datetime import date as _date
        record_date = date or _date.today().isoformat()
        snapshot = {
            "date": record_date,
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
        if run_id:
            snapshot["run_id"] = run_id
        return store.append_portfolio_snapshot(self.id, mode, snapshot, run_id=run_id)

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


# ------------------------------------------------------------------
# Strategy research (Codex)
# ------------------------------------------------------------------

def _codex_cmd() -> List[str]:
    repo_root = Path(__file__).resolve().parents[3]
    return [
        "codex.cmd",
        "exec",
        "-C",
        str(repo_root),
        "--dangerously-bypass-approvals-and-sandbox",
        "--sandbox",
        "danger-full-access",
        "-",
    ]


def _research_prompt(
    info: Dict[str, Any],
    store: "TraderStore",
    mode: str,
    target: Optional[str],
) -> str:
    repo_root = Path(__file__).resolve().parents[3]
    backend_root = Path(__file__).resolve().parents[2]
    strategy_contract = (repo_root / "backend" / "app" / "trading" / "strategy.py").as_posix()
    trader_id = info["id"]
    trader_skill_path = Path(store.trader_dir(trader_id)) / "SKILL.md"
    if not trader_skill_path.is_file():
        raise ValueError(f"Trader skill not found: {trader_skill_path.as_posix()}")

    traits = info.get("traits", {})
    traits_str = ", ".join(f"{k}={v}" for k, v in traits.items())
    sdir = Path(store.strategy_dir(trader_id))
    strategy_dir_abs = (backend_root / sdir).resolve()
    existing: List[str] = []
    if strategy_dir_abs.is_dir():
        existing = sorted(f for f in os.listdir(strategy_dir_abs) if f.endswith(".py"))
    existing_str = ", ".join(existing) if existing else "(none)"
    mode_instruction = (
        "Create one new strategy file with a unique filename; do not overwrite existing files. "
        if mode == "create"
        else (
            f"Update only the selected strategy file '{target}' in place; do not create new strategy files. "
            "Keep the filename unchanged. "
        )
    )

    return (
        f"Use [{trader_id} skill]({trader_skill_path.as_posix()}). "
        f"You are researching a trading strategy for existing trader '{trader_id}'. "
        f"Market: {info['market']}. "
        f"Allowed symbols: {', '.join(info['allowed_symbols'])}. "
        f"Commission rate: {info['commission_rate']}. "
        f"Trader traits: {traits_str}. "
        f"Existing strategy files: {existing_str}. "
        f"Strategy interface contract: {strategy_contract}. "
        f"Authoritative strategy output directory (absolute): {strategy_dir_abs.as_posix()}. "
        "Ignore any conflicting relative output path in skill references. "
        "Follow the autoresearch daily loop: generate candidate variants, evaluate, keep or discard with rationale. "
        "Implement the final accepted variant as a Python file in the trader strategy directory "
        f"({strategy_dir_abs.as_posix()}/). "
        f"The file must import and subclass Strategy from {strategy_contract}. "
        f"Implement initialize and on_bar methods. "
        "Keep logic explainable, enforce risk constraints from trader traits. "
        "Do not call backend API directly. "
        f"{mode_instruction}"
        "Produce strategy code artifacts only. "
    )


def research_strategy(
    trader_id: str,
    store: "TraderStore",
    mode: str = "create",
    target: Optional[str] = None,
) -> Generator[Dict[str, Any], None, None]:
    """调用 Codex 为指定交易员研究并生成交易策略。

    Yields 事件字典：
      - {"event": "log",    "message": str}
      - {"event": "error",  "message": str}
      - {"event": "result", "strategies": list[str]}
    """
    info = store.load_info(trader_id)

    if mode not in {"create", "update"}:
        msg = f"Invalid mode: {mode}"
        logger.error("[research][%s] %s", trader_id, msg)
        yield {"event": "error", "message": msg}
        return

    if mode == "update":
        if not target:
            msg = "Update mode requires a target strategy filename."
            logger.error("[research][%s] %s", trader_id, msg)
            yield {"event": "error", "message": msg}
            return
        target_path = Path(store.strategy_dir(trader_id)) / target
        if not target.endswith(".py") or not target_path.is_file():
            msg = f"Target strategy not found: {target}"
            logger.error("[research][%s] %s", trader_id, msg)
            yield {"event": "error", "message": msg}
            return

    start_msg = (
        f"Starting strategy research for trader '{trader_id}' (mode={mode}{', target=' + target if target else ''})..."
    )
    logger.info("[research][%s] %s", trader_id, start_msg)
    yield {
        "event": "log",
        "message": start_msg,
    }

    try:
        process = subprocess.Popen(
            _codex_cmd(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except Exception as exc:
        msg = f"Failed to start Codex: {exc}"
        logger.exception("[research][%s] %s", trader_id, msg)
        yield {"event": "error", "message": msg}
        return

    prompt = _research_prompt(info, store, mode=mode, target=target)
    assert process.stdin is not None
    process.stdin.write(prompt)
    process.stdin.close()

    assert process.stdout is not None
    for raw in process.stdout:
        line = raw.rstrip("\r\n")
        logger.info("[research][%s][codex] %s", trader_id, line)
        yield {"event": "log", "message": line}

    return_code = process.wait()
    if return_code != 0:
        msg = f"Codex exited with status {return_code}"
        logger.error("[research][%s] %s", trader_id, msg)
        yield {"event": "error", "message": msg}
        return

    sdir = store.strategy_dir(trader_id)
    files: List[str] = []
    if os.path.isdir(sdir):
        files = sorted(f for f in os.listdir(sdir) if f.endswith(".py"))

    logger.info("[research][%s] completed, strategies=%s", trader_id, files)
    yield {"event": "result", "strategies": files}
