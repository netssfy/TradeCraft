"""
Engine — 系统核心调度器。

支持 BACKTEST（回测）和 PAPER（模拟盘）两种运行模式，共享同一套主循环逻辑。
"""
from __future__ import annotations

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
from app.engine.trader_store import TraderStore

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
        store: Optional[TraderStore] = None,
    ) -> None:
        self.mode = mode
        self.traders = traders
        self.repository = repository
        self.simulator = simulator
        self.data_feeds = data_feeds
        self.config = config
        self.store = store or TraderStore()

        self._stop_flag: bool = False

        # run_id: backtest 用时间戳+uuid，paper 用日期
        if mode == EngineMode.PAPER:
            self._run_id: str = datetime.utcnow().strftime("%Y%m%d")
        else:
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
        bar_interval = _parse_bar_interval(self.config.bar_interval)

        for trader in self.traders:
            market = trader.market
            symbols = trader.allowed_symbols

            if symbols is None:
                logger.debug(
                    "Trader '%s' has allowed_symbols=None; cannot dispatch bars without symbol list.",
                    trader.id,
                )
                continue

            for symbol in symbols:
                # PAPER 模式：先 fetch 并写入 repository，再读取
                if self.mode == EngineMode.PAPER:
                    feed = self._feed_for_market.get(market)
                    if feed is not None:
                        try:
                            fetched = feed.fetch(
                                symbol, market, bar_interval,
                                bar_time - timedelta(minutes=30),
                                bar_time,
                            )
                            if fetched:
                                self.repository.write(fetched, market, symbol, bar_interval)
                        except Exception as exc:
                            logger.error(
                                "PAPER fetch failed for %s/%s at %s: %s",
                                market.value, symbol, bar_time.isoformat(), exc,
                            )

                bars = self.repository.read(
                    symbol, market, bar_interval,
                    bar_time - timedelta(seconds=60 * 20),
                    bar_time,
                )
                if not bars:
                    continue

                bar = bars[-1]

                try:
                    trader.on_bar(bar)
                except Exception as exc:
                    logger.error(
                        "Trader '%s' strategy raised an exception on bar %s/%s@%s: %s. Skipping.",
                        trader.id, symbol, bar_interval.value, bar_time.isoformat(), exc,
                        exc_info=True,
                    )

        # PAPER 模式：每 tick 实时落盘 portfolio 和 trades
        if self.mode == EngineMode.PAPER:
            for trader in self.traders:
                try:
                    trader.save_portfolio(self.store)
                    trader.save_trades(self.store, self._run_id, mode="paper")
                except Exception as exc:
                    logger.error("PAPER persist failed for trader '%s': %s", trader.id, exc)

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
        """PAPER 模式：每分钟第 2 秒触发一次，对齐时钟避免漂移。"""
        logger.info("Paper trading loop started.")
        while not self._stop_flag:
            now = datetime.now(tz=timezone.utc)
            self._tick(now)

            if self._stop_flag:
                break

            # 对齐到下一分钟的第 2 秒
            next_run = now.replace(second=2, microsecond=0) + timedelta(minutes=1)
            sleep_secs = (next_run - datetime.now(tz=timezone.utc)).total_seconds()
            if sleep_secs > 0:
                time.sleep(sleep_secs)

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
        for trader in self.traders:
            try:
                path = trader.save_portfolio(self.store)
                logger.info("Portfolio persisted for trader '%s' → %s", trader.id, path)
            except Exception as exc:
                logger.error("Failed to persist portfolio for trader '%s': %s", trader.id, exc)

    def _persist_trade_records(self) -> None:
        """持久化所有 Trader 的已成交记录。"""
        mode = "paper" if self.mode == EngineMode.PAPER else "backtest"
        for trader in self.traders:
            try:
                path = trader.save_trades(self.store, self._run_id, mode=mode)
                logger.info("Trade records persisted for trader '%s' → %s", trader.id, path)
            except Exception as exc:
                logger.error("Failed to persist trade records for trader '%s': %s", trader.id, exc)

    # ------------------------------------------------------------------
    # Report generation (task 12.3)
    # ------------------------------------------------------------------

    def _generate_reports(self) -> list:
        """回测结束时为每个 Trader 生成 Report，写入 data/traders/{name}/trades/{run_id}_report.json。"""
        from app.backtest.metrics import Metrics
        from app.backtest.report import Report

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

            # initial_cash: 从 trader.json 读取，fallback 到当前 cash
            try:
                info = self.store.load_info(trader.id)
                initial_cash = float(info.get("initial_cash", portfolio.cash))
            except Exception:
                initial_cash = portfolio.cash

            final_nav = portfolio.cash
            # 加上持仓市值：用回测结束时各 symbol 的最新收盘价估算
            for symbol, pos in portfolio.positions.items():
                if pos.quantity <= 0:
                    continue
                bar_interval = _parse_bar_interval(self.config.bar_interval)
                bars = self.repository.read(
                    symbol, trader.market, bar_interval,
                    backtest_start, backtest_end,
                )
                if bars:
                    final_nav += pos.quantity * bars[-1].close
            nav_series = [initial_cash, final_nav] if final_nav != initial_cash else [initial_cash, initial_cash]

            metrics_dict = {
                "annualized_return": Metrics.annualized_return(nav_series),
                "max_drawdown": Metrics.max_drawdown(nav_series),
                "sharpe_ratio": Metrics.sharpe_ratio(nav_series),
                "win_rate": Metrics.win_rate(trades),
                "profit_loss_ratio": Metrics.profit_loss_ratio(trades),
            }

            report = Report(
                trader_id=trader.id,
                backtest_start=backtest_start,
                backtest_end=backtest_end,
                initial_cash=initial_cash,
                final_nav=final_nav,
                metrics=metrics_dict,
                trades=list(trades),
            )

            # 写入 trader 自己的 backtest 目录
            trades_dir = self.store.trades_dir(trader.id, "backtest")
            os.makedirs(trades_dir, exist_ok=True)
            path = os.path.join(trades_dir, f"{self._run_id}_report.json")
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(report.to_json())
                logger.info("Report written for trader '%s' → %s", trader.id, path)
            except Exception as exc:
                logger.error("Failed to write report for trader '%s': %s", trader.id, exc)

            reports.append(report)

        return reports

    # ------------------------------------------------------------------
    # Factory — from_traders_dir()
    # ------------------------------------------------------------------

    @classmethod
    def from_traders_dir(
        cls,
        config_path: Optional[str] = None,
        traders_dir: str = "data/traders",
    ) -> "Engine":
        """从 data/traders/ 目录加载所有 Trader，结合全局配置构建 Engine。

        config.yaml 只需保留全局字段：mode、bar_interval、backtest、data_sources、logging。
        Trader 相关配置全部来自各自的 trader.json。
        """
        from app.adapters.data_feed import AkshareDataFeed, BaostockDataFeed, YfinanceDataFeed
        from app.engine.trader import Trader
        from app.engine.trader_store import TraderStore

        config = load_config(config_path)
        mode = EngineMode(config.mode)

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

        repository = MarketRepository()
        # commission_rate per-trader; use a default simulator (each trader carries its own rate)
        simulator = Simulator(commission_rate=0.0003)

        store = TraderStore(base_dir=traders_dir)
        trader_names = store.list_traders()
        if not trader_names:
            raise ValueError(f"No traders found in '{traders_dir}'. Create a trader first.")

        traders: List[Trader] = []
        for name in trader_names:
            try:
                trader = Trader.from_dir(name, store, repository, simulator)
                traders.append(trader)
                logger.info("Loaded trader '%s' from %s", name, store.trader_dir(name))
            except Exception as exc:
                logger.error("Failed to load trader '%s': %s", name, exc, exc_info=True)

        if not traders:
            raise ValueError("No traders could be loaded successfully.")

        return cls(
            mode=mode,
            traders=traders,
            repository=repository,
            simulator=simulator,
            data_feeds=data_feeds,
            config=config,
            store=store,
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
