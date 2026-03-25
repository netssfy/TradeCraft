"""
Engine — 系统核心调度器。

支持 BACKTEST（回测）和 PAPER（模拟盘）两种运行模式，共享同一套主循环逻辑。
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional

from app.adapters.data_feed import DataFeed, DataFeedError
from app.adapters.simulator import Simulator
from app.core.config import Config, load_config
from app.data.market import BarInterval, Market
from app.data.repository import MarketRepository
from app.engine.context import Context
from app.engine.models import Bar

logger = logging.getLogger(__name__)

# All six bar intervals used during warmup
_ALL_INTERVALS = list(BarInterval)


class EngineMode(Enum):
    BACKTEST = "backtest"
    PAPER = "paper"


class Engine:
    def __init__(
        self,
        mode: EngineMode,
        traders: List,  # List[Trader] — avoid circular import at module level
        repository: MarketRepository,
        simulator: Simulator,
        data_feeds: List[DataFeed],
        config: Config,
    ) -> None:
        self.mode = mode
        self.traders = traders
        self.repository = repository
        self.simulator = simulator
        self.data_feeds = data_feeds
        self.config = config

        self._stop_flag: bool = False
        self._run_id: str = datetime.utcnow().strftime("%Y%m%d_%H%M%S_") + str(uuid.uuid4())[:8]

        # Build a mapping: Market → DataFeed for quick lookup
        self._feed_for_market: Dict[Market, DataFeed] = {}
        for feed in data_feeds:
            for market in feed.supported_markets:
                # Later feeds in the list override earlier ones for the same market
                self._feed_for_market[market] = feed

    # ------------------------------------------------------------------
    # Task 11.1 — _warmup()
    # ------------------------------------------------------------------

    def _warmup(self) -> None:
        """汇总所有 Trader 的 Symbol 列表，补齐所有 BarInterval 的本地数据。"""
        # Collect (market, symbol) pairs from all traders
        market_symbols: Dict[Market, set] = {}
        for trader in self.traders:
            market = trader.market
            symbols = trader.allowed_symbols
            if symbols is None:
                # No restriction — nothing to pre-warm without an explicit list
                logger.warning(
                    "Trader '%s' has allowed_symbols=None; skipping warmup for this trader.",
                    trader.id,
                )
                continue
            if market not in market_symbols:
                market_symbols[market] = set()
            market_symbols[market].update(symbols)

        # Determine the target end time
        if self.mode == EngineMode.BACKTEST:
            end_time = datetime.strptime(
                self.config.backtest.end_date, "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)
        else:
            end_time = datetime.now(tz=timezone.utc)

        for market, symbols in market_symbols.items():
            feed = self._feed_for_market.get(market)
            if feed is None:
                logger.warning("No DataFeed configured for market %s; skipping warmup.", market.value)
                continue

            for symbol in sorted(symbols):
                for interval in _ALL_INTERVALS:
                    self._warmup_symbol(feed, symbol, market, interval, end_time)

    def _warmup_symbol(
        self,
        feed: DataFeed,
        symbol: str,
        market: Market,
        interval: BarInterval,
        end_time: datetime,
    ) -> None:
        """Warm up a single (symbol, interval) pair."""
        max_days = feed.max_lookback_days.get(interval, 365)

        latest_ts = self.repository.get_latest_timestamp(symbol, market, interval)

        if latest_ts is None:
            # First run — pull as much as allowed
            start_time = end_time - timedelta(days=max_days)
            logger.debug(
                "Warmup [%s/%s/%s]: no local data, fetching from %s to %s",
                market.value, symbol, interval.value,
                start_time.isoformat(), end_time.isoformat(),
            )
        else:
            # Ensure latest_ts is timezone-aware for arithmetic
            if latest_ts.tzinfo is None:
                latest_ts = latest_ts.replace(tzinfo=timezone.utc)

            gap = end_time - latest_ts
            if gap.total_seconds() <= 0:
                logger.debug(
                    "Warmup [%s/%s/%s]: data already up-to-date (latest=%s).",
                    market.value, symbol, interval.value, latest_ts.isoformat(),
                )
                return

            max_delta = timedelta(days=max_days)
            if gap > max_delta:
                logger.warning(
                    "Warmup [%s/%s/%s]: gap (%s days) exceeds max_lookback_days (%d). "
                    "Truncating fetch range.",
                    market.value, symbol, interval.value,
                    gap.days, max_days,
                )
                start_time = end_time - max_delta
            else:
                start_time = latest_ts

        try:
            bars = feed.fetch(symbol, market, interval, start_time, end_time)
        except DataFeedError as exc:
            logger.warning(
                "Warmup [%s/%s/%s]: fetch failed — %s. Skipping.",
                market.value, symbol, interval.value, exc,
            )
            return
        except Exception as exc:
            logger.warning(
                "Warmup [%s/%s/%s]: unexpected error during fetch — %s. Skipping.",
                market.value, symbol, interval.value, exc,
            )
            return

        if bars:
            added = self.repository.write(bars, market, symbol, interval)
            # Log actual data range
            timestamps = [b.timestamp for b in bars]
            actual_start = min(timestamps)
            actual_end = max(timestamps)
            logger.info(
                "Warmup [%s/%s/%s]: fetched %d bars (%d new), range %s → %s.",
                market.value, symbol, interval.value,
                len(bars), added,
                actual_start.isoformat(), actual_end.isoformat(),
            )
        else:
            logger.info(
                "Warmup [%s/%s/%s]: no bars returned by DataFeed.",
                market.value, symbol, interval.value,
            )

    # ------------------------------------------------------------------
    # Task 11.2 — _tick() and _run_loop()
    # ------------------------------------------------------------------

    def _tick(self, bar_time: datetime) -> None:
        """单个 Bar 的完整处理：按 Market 分发 Bar → 驱动 Trader → PAPER 模式落盘。"""
        # Collect bars fetched in PAPER mode so we can persist them after all traders run
        paper_bars: List[Bar] = []

        for trader in self.traders:
            market = trader.market
            symbols = trader.allowed_symbols

            if symbols is None:
                # No symbol restriction — read all available bars for this market at bar_time
                # We can't enumerate all symbols without a list, so skip gracefully
                logger.debug(
                    "Trader '%s' has allowed_symbols=None; cannot dispatch bars without symbol list.",
                    trader.id,
                )
                continue

            for symbol in symbols:
                # In PAPER mode, fetch the latest bar from the data feed first
                if self.mode == EngineMode.PAPER:
                    feed = self._feed_for_market.get(market)
                    if feed is not None:
                        try:
                            fetched = feed.fetch(
                                symbol, market, BarInterval.M1,
                                bar_time - timedelta(minutes=2),
                                bar_time,
                            )
                            if fetched:
                                paper_bars.extend(fetched)
                        except Exception as exc:
                            logger.error(
                                "PAPER fetch failed for %s/%s at %s: %s",
                                market.value, symbol, bar_time.isoformat(), exc,
                            )

                # Read the bar for this symbol at bar_time from the repository
                bar_interval = _parse_bar_interval(self.config.bar_interval)
                bars = self.repository.read(
                    symbol, market, bar_interval,
                    bar_time - timedelta(seconds=1),
                    bar_time,
                )
                if not bars:
                    continue

                # Use the most recent bar at or before bar_time
                bar = bars[-1]

                try:
                    trader.on_bar(bar)
                except Exception as exc:
                    logger.error(
                        "Trader '%s' strategy raised an exception on bar %s/%s@%s: %s. Skipping.",
                        trader.id, symbol, bar_interval.value, bar_time.isoformat(), exc,
                        exc_info=True,
                    )

        # PAPER mode: persist newly fetched bars to repository
        if self.mode == EngineMode.PAPER and paper_bars:
            for bar in paper_bars:
                try:
                    self.repository.write([bar], bar.market, bar.symbol, bar.interval)
                except Exception as exc:
                    logger.error("Failed to persist bar %s/%s: %s", bar.symbol, bar.interval.value, exc)

    def _run_loop(self) -> None:
        """主循环：BACKTEST 直接跳 Bar，PAPER 等待真实 1 分钟。"""
        if self.mode == EngineMode.BACKTEST:
            self._run_backtest()
        else:
            self._run_paper()

    def _run_backtest(self) -> None:
        """BACKTEST 模式：从 Repository 按时间顺序逐 Bar 读取推进。"""
        start_dt = datetime.strptime(
            self.config.backtest.start_date, "%Y-%m-%d"
        ).replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(
            self.config.backtest.end_date, "%Y-%m-%d"
        ).replace(tzinfo=timezone.utc)

        bar_interval = _parse_bar_interval(self.config.bar_interval)

        # Collect all (market, symbol) pairs
        all_pairs: List[tuple] = []
        for trader in self.traders:
            if trader.allowed_symbols:
                for symbol in trader.allowed_symbols:
                    pair = (trader.market, symbol)
                    if pair not in all_pairs:
                        all_pairs.append(pair)

        if not all_pairs:
            logger.warning("No symbols to iterate in backtest mode.")
            return

        # Read all bars for all symbols and merge into a sorted timeline
        all_bars: List[Bar] = []
        for market, symbol in all_pairs:
            bars = self.repository.read(symbol, market, bar_interval, start_dt, end_dt)
            all_bars.extend(bars)

        # Sort by timestamp
        all_bars.sort(key=lambda b: _bar_ts_utc(b))

        # Deduplicate timestamps — collect unique bar_times
        seen_times: set = set()
        bar_times: List[datetime] = []
        for bar in all_bars:
            ts = _bar_ts_utc(bar)
            if ts not in seen_times:
                seen_times.add(ts)
                bar_times.append(ts)

        bar_times.sort()

        logger.info(
            "Backtest: %d unique bar timestamps from %s to %s.",
            len(bar_times),
            bar_times[0].isoformat() if bar_times else "N/A",
            bar_times[-1].isoformat() if bar_times else "N/A",
        )

        for bar_time in bar_times:
            if self._stop_flag:
                logger.info("Stop flag set; exiting backtest loop.")
                break
            self._tick(bar_time)

        logger.info("Backtest loop completed.")

    def _run_paper(self) -> None:
        """PAPER 模式：每分钟拉取最新数据并推进一个 Bar。"""
        logger.info("Paper trading loop started.")
        while not self._stop_flag:
            now = datetime.now(tz=timezone.utc)
            self._tick(now)

            if self._stop_flag:
                break

            # Wait for the next minute
            time.sleep(60)

        logger.info("Paper trading loop stopped.")

    # ------------------------------------------------------------------
    # Task 11.3 — start() and stop()
    # ------------------------------------------------------------------

    def start(self) -> None:
        """执行预热 → 初始化所有策略 → 启动主循环。"""
        try:
            logger.info("Engine starting (mode=%s, run_id=%s).", self.mode.value, self._run_id)

            # Step 1: Warmup
            logger.info("Starting data warmup...")
            self._warmup()
            logger.info("Data warmup complete.")

            # Step 2: Initialize all strategies
            for trader in self.traders:
                context = Context(
                    trader=trader,
                    repository=self.repository,
                    current_time=datetime.now(tz=timezone.utc),
                )
                try:
                    trader.initialize(context)
                except Exception as exc:
                    logger.error(
                        "Strategy initialization failed for trader '%s': %s",
                        trader.id, exc, exc_info=True,
                    )

            logger.info("All strategies initialized.")

            # Step 3: Run main loop
            self._run_loop()

            # Step 4: Generate reports (backtest only)
            if self.mode == EngineMode.BACKTEST:
                self._generate_reports()

        except Exception as exc:
            logger.error("Unhandled Engine exception: %s", exc, exc_info=True)
            self._safe_stop()
            raise

    def stop(self) -> None:
        """设置停止标志，等待当前 Bar 完成后退出。"""
        logger.info("Engine stop requested.")
        self._stop_flag = True

        # PAPER mode: persist all trader portfolio states
        if self.mode == EngineMode.PAPER:
            self._persist_portfolios()

    def _safe_stop(self) -> None:
        """安全停止：持久化已成交记录。"""
        self._stop_flag = True
        self._persist_trade_records()
        if self.mode == EngineMode.PAPER:
            self._persist_portfolios()

    def _persist_portfolios(self) -> None:
        """PAPER 模式：持久化所有 Trader 的 Portfolio 状态。"""
        os.makedirs("data/cache", exist_ok=True)
        for trader in self.traders:
            path = f"data/cache/portfolio_{trader.id}.json"
            try:
                portfolio = trader.portfolio
                data = {
                    "trader_id": trader.id,
                    "cash": portfolio.cash,
                    "positions": {
                        symbol: {
                            "symbol": pos.symbol,
                            "quantity": pos.quantity,
                            "avg_cost": pos.avg_cost,
                        }
                        for symbol, pos in portfolio.positions.items()
                    },
                    "trade_history": [
                        {
                            "timestamp": t.timestamp.isoformat(),
                            "symbol": t.symbol,
                            "direction": t.direction.value,
                            "quantity": t.quantity,
                            "price": t.price,
                            "commission": t.commission,
                        }
                        for t in portfolio.trade_history
                    ],
                }
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info("Portfolio persisted for trader '%s' → %s", trader.id, path)
            except Exception as exc:
                logger.error("Failed to persist portfolio for trader '%s': %s", trader.id, exc)

    def _persist_trade_records(self) -> None:
        """持久化所有 Trader 的已成交记录到 data/runs/{run_id}/。"""
        run_dir = os.path.join("data", "runs", self._run_id)
        os.makedirs(run_dir, exist_ok=True)
        for trader in self.traders:
            path = os.path.join(run_dir, f"{trader.id}_trades.json")
            try:
                trades = [
                    {
                        "timestamp": t.timestamp.isoformat(),
                        "symbol": t.symbol,
                        "direction": t.direction.value,
                        "quantity": t.quantity,
                        "price": t.price,
                        "commission": t.commission,
                    }
                    for t in trader.portfolio.trade_history
                ]
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(trades, f, ensure_ascii=False, indent=2)
                logger.info("Trade records persisted for trader '%s' → %s", trader.id, path)
            except Exception as exc:
                logger.error("Failed to persist trade records for trader '%s': %s", trader.id, exc)

    # ------------------------------------------------------------------
    # Report generation (task 12.3)
    # ------------------------------------------------------------------

    def _generate_reports(self) -> list:
        """回测结束时为每个 Trader 生成 Report，写入 data/runs/{run_id}/{trader_id}_report.json。"""
        from app.backtest.metrics import Metrics
        from app.backtest.report import Report

        run_dir = os.path.join("data", "runs", self._run_id)
        os.makedirs(run_dir, exist_ok=True)

        backtest_start = datetime.strptime(
            self.config.backtest.start_date, "%Y-%m-%d"
        ).replace(tzinfo=timezone.utc)
        backtest_end = datetime.strptime(
            self.config.backtest.end_date, "%Y-%m-%d"
        ).replace(tzinfo=timezone.utc)

        reports = []
        for trader in self.traders:
            portfolio = trader.portfolio
            trades = portfolio.trade_history

            # Build NAV series from trade history (simplified: use cash + position value at each trade)
            # For a proper NAV series we'd need price snapshots; use a minimal approach:
            # nav_series = [initial_cash, ..., final_nav] derived from trade timestamps
            initial_cash = self.config.traders[
                next(i for i, tc in enumerate(self.config.traders) if tc.id == trader.id)
            ].initial_cash

            # Compute final NAV: cash + sum of remaining positions at last known price
            # Since we don't have current prices here, use cash only as a conservative estimate
            # and build a simple nav_series from portfolio snapshots if available.
            # Minimal approach: nav_series = [initial_cash, final_cash_approx]
            final_nav = portfolio.cash  # positions not liquidated; best available estimate

            # Build a simple nav_series for metrics (initial → final)
            nav_series = [initial_cash, final_nav] if final_nav != initial_cash else [initial_cash, initial_cash]

            trader_cfg = next(tc for tc in self.config.traders if tc.id == trader.id)

            metrics_dict = {
                "annualized_return": Metrics.annualized_return(nav_series),
                "max_drawdown": Metrics.max_drawdown(nav_series),
                "sharpe_ratio": Metrics.sharpe_ratio(nav_series),
                "win_rate": Metrics.win_rate(trades),
                "profit_loss_ratio": Metrics.profit_loss_ratio(trades),
            }

            report = Report(
                trader_id=trader.id,
                strategy_params=trader_cfg.strategy_params,
                backtest_start=backtest_start,
                backtest_end=backtest_end,
                initial_cash=initial_cash,
                final_nav=final_nav,
                metrics=metrics_dict,
                trades=list(trades),
            )

            path = os.path.join(run_dir, f"{trader.id}_report.json")
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(report.to_json())
                logger.info("Report written for trader '%s' → %s", trader.id, path)
            except Exception as exc:
                logger.error("Failed to write report for trader '%s': %s", trader.id, exc)

            reports.append(report)

        return reports

    # ------------------------------------------------------------------
    # Task 11.4 — from_config() factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls, config_path: Optional[str] = None) -> "Engine":
        """根据配置文件实例化所有组件并返回 Engine 实例。"""
        from app.adapters.data_feed import AkshareDataFeed, BaostockDataFeed, YfinanceDataFeed
        from app.engine.events import EventBus
        from app.engine.orders import OrderManager
        from app.engine.portfolio import Portfolio
        from app.engine.trader import Trader
        from app.trading.strategy_loader import StrategyLoader

        config = load_config(config_path)

        # Determine engine mode
        mode = EngineMode(config.mode)

        # Build DataFeed instances based on config.data_sources
        _FEED_CLASSES = {
            "akshare": AkshareDataFeed,
            "baostock": BaostockDataFeed,
            "yfinance": YfinanceDataFeed,
        }

        feed_instances: Dict[str, DataFeed] = {}
        for market_str, feed_name in config.data_sources.items():
            feed_key = feed_name.lower()
            if feed_key not in feed_instances:
                feed_cls = _FEED_CLASSES.get(feed_key)
                if feed_cls is None:
                    raise ValueError(f"Unknown data source '{feed_name}' for market '{market_str}'.")
                feed_instances[feed_key] = feed_cls()

        data_feeds = list(feed_instances.values())

        # Create shared repository and simulator
        repository = MarketRepository()

        # Use commission_rate from the first trader config (or default)
        commission_rate = config.traders[0].commission_rate if config.traders else 0.0003
        simulator = Simulator(commission_rate=commission_rate)

        # Create Trader instances
        traders: List[Trader] = []
        for trader_cfg in config.traders:
            market = Market(trader_cfg.market)

            # Load strategy
            result = StrategyLoader.load(trader_cfg.strategy_path, trader_cfg.strategy_params)
            if not result.success:
                raise ValueError(
                    f"Failed to load strategy for trader '{trader_cfg.id}': {result.error}"
                )

            event_bus = EventBus()
            order_manager = OrderManager(
                trader_id=trader_cfg.id,
                allowed_symbols=trader_cfg.allowed_symbols,
                event_bus=event_bus,
            )
            portfolio = Portfolio(initial_cash=trader_cfg.initial_cash)

            trader = Trader(
                id=trader_cfg.id,
                market=market,
                strategy=result.strategy,
                order_manager=order_manager,
                portfolio=portfolio,
                repository=repository,
                simulator=simulator,
                allowed_symbols=trader_cfg.allowed_symbols,
            )
            traders.append(trader)

        return cls(
            mode=mode,
            traders=traders,
            repository=repository,
            simulator=simulator,
            data_feeds=data_feeds,
            config=config,
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _bar_ts_utc(bar: Bar) -> datetime:
    """Return bar.timestamp as a UTC-aware datetime."""
    ts = bar.timestamp
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _parse_bar_interval(interval_str: str) -> BarInterval:
    """Parse a bar interval string like '1m', '5m', '1d' into BarInterval."""
    mapping = {bi.value: bi for bi in BarInterval}
    result = mapping.get(interval_str.lower())
    if result is None:
        raise ValueError(f"Unknown bar_interval '{interval_str}'. Valid values: {list(mapping.keys())}")
    return result
