from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from app.adapters.data_feed import AkshareDataFeed, BaostockDataFeed, DataFeed, YfinanceDataFeed
from app.adapters.simulator import Simulator
from app.core.config import Config, load_config
from app.data.market import Market
from app.data.repository import MarketRepository
from app.engine.core import Engine, EngineMode
from app.engine.trader import Trader
from app.engine.trader_store import TraderStore


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return _to_jsonable(value.item())
        except Exception:
            return str(value)
    return str(value)


def _print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _parse_market(value: str) -> Market:
    normalized = value.strip().upper()
    try:
        return Market(normalized)
    except Exception as exc:
        valid = ", ".join(m.value for m in Market)
        raise argparse.ArgumentTypeError(f"Invalid market '{value}'. Expected one of: {valid}") from exc


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date '{value}', expected YYYY-MM-DD") from exc


def _parse_datetime_like(value: str, is_end: bool) -> datetime:
    text = value.strip()
    if "T" in text:
        dt = datetime.fromisoformat(text)
    else:
        d = date.fromisoformat(text)
        dt = datetime.combine(d, time.max if is_end else time.min)

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _subtract_months(d: date, months: int) -> date:
    year = d.year
    month = d.month - months
    while month <= 0:
        month += 12
        year -= 1
    if month == 2:
        day_limit = 29 if ((year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)) else 28
    elif month in (4, 6, 9, 11):
        day_limit = 30
    else:
        day_limit = 31
    return date(year, month, min(d.day, day_limit))


def _resolve_data_feed(name: str) -> DataFeed:
    mapping = {
        "akshare": AkshareDataFeed,
        "baostock": BaostockDataFeed,
        "yfinance": YfinanceDataFeed,
    }
    cls = mapping.get(name.lower())
    if cls is None:
        valid = ", ".join(sorted(mapping.keys()))
        raise ValueError(f"Unknown data source '{name}', expected one of: {valid}")
    return cls()


def _rows_to_jsonable(df: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for record in df.to_dict(orient="records"):
        item: Dict[str, Any] = {}
        for key, value in record.items():
            item[str(key)] = _to_jsonable(value)
        rows.append(item)
    return rows


def cmd_data_availability(args: argparse.Namespace) -> int:
    root = Path(args.market_root)
    files = sorted(root.rglob("*.parquet")) if root.exists() else []
    grouped: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
    for file_path in files:
        rel = file_path.relative_to(root)
        if len(rel.parts) < 4:
            continue
        market, symbol, interval = rel.parts[0], rel.parts[1], rel.parts[2]
        grouped[(market, symbol, interval)].append(file_path.stem)

    items: List[Dict[str, Any]] = []
    for (market, symbol, interval), periods in sorted(grouped.items()):
        unique_periods = sorted(set(periods))
        items.append(
            {
                "market": market,
                "symbol": symbol,
                "interval": interval,
                "file_count": len(unique_periods),
                "start_period": unique_periods[0] if unique_periods else None,
                "end_period": unique_periods[-1] if unique_periods else None,
                "periods": unique_periods,
            }
        )

    _print_json(
        {
            "root": str(root),
            "total_files": len(files),
            "items": items,
        }
    )
    return 0


def cmd_data_file(args: argparse.Namespace) -> int:
    file_path = Path(args.market_root) / args.market.value / args.symbol / args.interval.value / f"{args.period}.parquet"
    if not file_path.is_file():
        raise FileNotFoundError(f"Market data file not found: {file_path}")

    df = pd.read_parquet(file_path)
    total_rows = len(df.index)
    start = max(args.offset, 0)
    end = min(start + args.limit, total_rows)
    page_df = df.iloc[start:end].copy() if start < total_rows else df.iloc[0:0].copy()

    _print_json(
        {
            "market": args.market.value,
            "symbol": args.symbol,
            "interval": args.interval.value,
            "period": args.period,
            "path": str(file_path),
            "columns": [str(column) for column in df.columns.tolist()],
            "total_rows": total_rows,
            "offset": start,
            "limit": args.limit,
            "rows": _rows_to_jsonable(page_df),
        }
    )
    return 0


def cmd_data_slice(args: argparse.Namespace) -> int:
    start = _parse_datetime_like(args.start, is_end=False)
    end = _parse_datetime_like(args.end, is_end=True)
    if start > end:
        raise ValueError("start must be <= end")

    repo = MarketRepository(base_path=args.market_root)
    bars = repo.read(
        symbol=args.symbol,
        market=args.market,
        interval=args.interval,
        start=start,
        end=end,
    )
    if args.limit > 0:
        bars = bars[: args.limit]

    rows: List[Dict[str, Any]] = []
    for bar in bars:
        rows.append(
            {
                "timestamp": bar.timestamp.isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
        )
    _print_json(
        {
            "market": args.market.value,
            "symbol": args.symbol,
            "interval": args.interval.value,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "rows": rows,
            "row_count": len(rows),
        }
    )
    return 0


def cmd_backtest_run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config_path)
    today = date.today()
    start_date = _parse_date(args.start_date) if args.start_date else _subtract_months(today, 3)
    end_date = _parse_date(args.end_date) if args.end_date else today
    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")

    run_cfg = Config(
        data_sources=cfg.data_sources,
        logging=cfg.logging,
    )

    store = TraderStore(base_dir=args.traders_dir)
    strategy_targets: List[Optional[str]]
    if args.strategy_list:
        cleaned = [s.strip() for s in args.strategy_list.split(",") if s.strip()]
        if not cleaned:
            raise ValueError("--strategy-list cannot be empty")
        strategy_targets = list(dict.fromkeys(cleaned))
    else:
        strategy_filename = args.strategy_filename.strip() if args.strategy_filename else None
        strategy_targets = [strategy_filename or None]

    repository = MarketRepository(base_path=args.market_root)
    simulator = Simulator(commission_rate=0.0003)
    traders: List[Trader] = []
    for target_strategy in strategy_targets:
        traders.append(
            Trader.from_dir(
                args.trader_id,
                store,
                repository,
                simulator,
                active_strategy=target_strategy,
            )
        )
    feed_name = run_cfg.data_sources.get(traders[0].market.value, "yfinance")
    feed = _resolve_data_feed(feed_name)

    engine = Engine(
        mode=EngineMode.BACKTEST,
        traders=traders,
        repository=repository,
        simulator=simulator,
        data_feeds=[feed],
        config=run_cfg,
        store=store,
        backtest_start=start_date.isoformat(),
        backtest_end=end_date.isoformat(),
    )
    engine.start()

    runs: List[Dict[str, Any]] = []
    for trader in traders:
        run_id = engine.run_id_for_trader(trader)
        trader.save_trades(store, run_id, mode="backtest")
        report = store.load_report(args.trader_id, run_id, mode="backtest")
        runs.append(
            {
                "strategy": trader.active_strategy,
                "run_id": run_id,
                "report": report,
            }
        )

    _print_json(
        {
            "trader_id": args.trader_id,
            "run_id": runs[0]["run_id"],
            "runs": runs,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "bar_interval": "1m",
        }
    )
    return 0


def cmd_backtest_report(args: argparse.Namespace) -> int:
    store = TraderStore(base_dir=args.traders_dir)
    report = store.load_report(args.trader_id, args.run_id, mode="backtest")
    if report is None:
        raise FileNotFoundError(
            f"Backtest report not found for trader='{args.trader_id}', run_id='{args.run_id}'"
        )
    _print_json(report)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tradecraft-cli",
        description="CLI for local market data access and backtest runs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    data_parser = subparsers.add_parser("data", help="Inspect local market data")
    data_subparsers = data_parser.add_subparsers(dest="data_cmd", required=True)

    availability_parser = data_subparsers.add_parser("availability", help="Show local parquet availability")
    availability_parser.add_argument("--market-root", default="data/market")
    availability_parser.set_defaults(func=cmd_data_availability)

    file_parser = data_subparsers.add_parser("file", help="Read one parquet file with offset/limit")
    file_parser.add_argument("--market-root", default="data/market")
    file_parser.add_argument("--market", type=_parse_market, required=True)
    file_parser.add_argument("--symbol", required=True)
    file_parser.add_argument("--interval", type=_parse_interval, required=True)
    file_parser.add_argument("--period", required=True, help="YYYY-MM period string")
    file_parser.add_argument("--offset", type=int, default=0)
    file_parser.add_argument("--limit", type=int, default=50)
    file_parser.set_defaults(func=cmd_data_file)

    slice_parser = data_subparsers.add_parser("slice", help="Read bars by symbol + time range")
    slice_parser.add_argument("--market-root", default="data/market")
    slice_parser.add_argument("--market", type=_parse_market, required=True)
    slice_parser.add_argument("--symbol", required=True)
    slice_parser.add_argument("--interval", type=_parse_interval, required=True)
    slice_parser.add_argument("--start", required=True, help="YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")
    slice_parser.add_argument("--end", required=True, help="YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")
    slice_parser.add_argument("--limit", type=int, default=500)
    slice_parser.set_defaults(func=cmd_data_slice)

    backtest_parser = subparsers.add_parser("backtest", help="Run backtests and inspect reports")
    backtest_subparsers = backtest_parser.add_subparsers(dest="backtest_cmd", required=True)

    run_parser = backtest_subparsers.add_parser("run", help="Run one backtest for a trader")
    run_parser.add_argument("--trader-id", required=True)
    run_parser.add_argument("--start-date", help="YYYY-MM-DD")
    run_parser.add_argument("--end-date", help="YYYY-MM-DD")
    run_parser.add_argument("--strategy-filename", help="Optional strategy file to run")
    run_parser.add_argument(
        "--strategy-list",
        help="Optional comma-separated strategy filenames for batch backtest run",
    )
    run_parser.add_argument("--config-path", default="config.yaml")
    run_parser.add_argument("--traders-dir", default="data/traders")
    run_parser.add_argument("--market-root", default="data/market")
    run_parser.set_defaults(func=cmd_backtest_run)

    report_parser = backtest_subparsers.add_parser("report", help="Show a historical backtest report")
    report_parser.add_argument("--trader-id", required=True)
    report_parser.add_argument("--run-id", required=True)
    report_parser.add_argument("--traders-dir", default="data/traders")
    report_parser.set_defaults(func=cmd_backtest_report)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
