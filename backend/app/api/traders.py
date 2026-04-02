from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.core.ai_agent import build_agent_cmd
from app.engine.trader_store import TraderStore

router = APIRouter(prefix="/traders", tags=["traders"])
store = TraderStore(base_dir="data/traders")
logger = logging.getLogger(__name__)
engine_logger = logging.getLogger("app.engine.core")


class TraitsModel(BaseModel):
    risk_appetite: str = Field(..., description="Risk appetite.")
    holding_horizon: str = Field(..., description="Holding horizon.")
    signal_preference: str = Field(..., description="Signal preference.")
    position_construction: str = Field(..., description="Position sizing style.")
    exit_discipline: str = Field(..., description="Exit discipline.")
    universe_focus: str = Field(..., description="Universe focus.")


class TraderInfo(BaseModel):
    id: str
    market: str
    initial_cash: float
    allowed_symbols: List[str]
    commission_rate: float
    order_timeout_seconds: int
    active_strategy: str
    traits: TraitsModel


class PositionModel(BaseModel):
    symbol: str
    quantity: float
    avg_cost: float


class PortfolioSnapshotModel(BaseModel):
    date: str
    cash: float
    positions: Dict[str, PositionModel]


class PortfolioModel(BaseModel):
    trader_id: str
    mode: str
    snapshots: List[PortfolioSnapshotModel]


class TradeModel(BaseModel):
    timestamp: str
    symbol: str
    direction: str
    quantity: float
    price: float
    commission: float


class StrategyFileModel(BaseModel):
    filename: str
    is_active: bool


class StrategyCodeModel(BaseModel):
    filename: str
    code: str


class BacktestRunResult(BaseModel):
    trader_id: str
    run_id: str


class BacktestRunRequest(BaseModel):
    start_date: Optional[str] = Field(None, description="Backtest start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Backtest end date (YYYY-MM-DD)")
    strategy_filename: Optional[str] = Field(None, description="Strategy filename to run for this backtest")


class BacktestMetricsModel(BaseModel):
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_loss_ratio: float


class BacktestReportModel(BaseModel):
    trader_id: str
    backtest_start: str
    backtest_end: str
    initial_cash: float
    final_nav: float
    strategy_filename: Optional[str] = None
    metrics: BacktestMetricsModel


class CreateTraderRequest(BaseModel):
    id: str = Field(..., description="Trader unique id")
    market: str = Field(..., description="CN / HK / US")
    initial_cash: float = Field(..., gt=0, description="Initial cash")
    allowed_symbols: List[str] = Field(..., min_length=1, description="Allowed symbols")
    commission_rate: float = Field(..., ge=0, le=0.01, description="Commission rate")
    order_timeout_seconds: int = Field(300, gt=0, description="Order timeout in seconds")


@router.post(
    "",
    status_code=201,
    summary="Create Trader",
    description="Stream Codex trainer output, then emit final trader info.",
)
def create_trader(req: CreateTraderRequest):
    # 1) duplicate check by id
    if req.id in store.list_traders() or os.path.exists(store.trader_dir(req.id)):
        raise HTTPException(status_code=409, detail=f"Trader '{req.id}' already exists.")

    # 2) create dirs first
    os.makedirs(store.trader_dir(req.id), exist_ok=True)
    os.makedirs(store.strategy_dir(req.id), exist_ok=True)
    os.makedirs(store.trades_dir(req.id, "paper"), exist_ok=True)
    os.makedirs(store.trades_dir(req.id, "backtest"), exist_ok=True)
    os.makedirs(store.portfolio_dir(req.id), exist_ok=True)

    def _stream():
        yield _sse_event("log", {"message": "Starting Codex trainer..."})
        traits: Optional[Dict[str, Any]] = None
        output_lines: List[str] = []

        try:
            process = subprocess.Popen(
                _build_agent_cmd(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except Exception as exc:
            yield _sse_event("error", {"message": f"Failed to start Codex: {exc}"})
            return

        prompt = _build_codex_prompt(req)
        assert process.stdin is not None
        process.stdin.write(prompt)
        process.stdin.close()

        assert process.stdout is not None
        for raw in process.stdout:
            line = raw.rstrip("\r\n")
            output_lines.append(line)
            yield _sse_event("log", {"message": line})

            if "FINAL_TRAITS_JSON:" in line:
                candidate = line.split("FINAL_TRAITS_JSON:", 1)[1].strip()
                try:
                    traits = json.loads(candidate)
                except json.JSONDecodeError:
                    pass

        return_code = process.wait()
        if return_code != 0:
            yield _sse_event("error", {"message": f"Codex exited with status {return_code}"})
            return

        if traits is None:
            joined = "\n".join(output_lines)
            match = re.search(r"FINAL_TRAITS_JSON:\s*(\{.*\})", joined)
            if match:
                try:
                    traits = json.loads(match.group(1))
                except json.JSONDecodeError:
                    traits = None

        if traits is None:
            yield _sse_event("error", {"message": "Trainer output missing FINAL_TRAITS_JSON"})
            return

        # 4) save info
        info = {
            "id": req.id,
            "market": req.market,
            "initial_cash": req.initial_cash,
            "allowed_symbols": req.allowed_symbols,
            "commission_rate": req.commission_rate,
            "order_timeout_seconds": req.order_timeout_seconds,
            "active_strategy": "",
            "traits": TraitsModel(**traits).model_dump(),
        }
        store.save_info(req.id, info)

        final_info = _load_trader_info(req.id).model_dump()
        yield _sse_event("result", final_info)

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.get("", response_model=List[TraderInfo], summary="List traders")
def list_traders():
    return [_load_trader_info(name) for name in store.list_traders()]


@router.get("/{trader_id}", response_model=TraderInfo, summary="Get trader")
def get_trader(trader_id: str):
    _assert_exists(trader_id)
    return _load_trader_info(trader_id)


class UpdateTraderRequest(BaseModel):
    initial_cash: Optional[float] = Field(None, gt=0)
    allowed_symbols: Optional[List[str]] = None
    commission_rate: Optional[float] = Field(None, ge=0, le=0.01)
    order_timeout_seconds: Optional[int] = Field(None, gt=0)
    traits: Optional[TraitsModel] = None


@router.patch("/{trader_id}", response_model=TraderInfo, summary="Update trader")
def update_trader(trader_id: str, req: UpdateTraderRequest):
    _assert_exists(trader_id)
    info = store.load_info(trader_id)
    if req.initial_cash is not None:
        info["initial_cash"] = req.initial_cash
    if req.allowed_symbols is not None:
        info["allowed_symbols"] = req.allowed_symbols
    if req.commission_rate is not None:
        info["commission_rate"] = req.commission_rate
    if req.order_timeout_seconds is not None:
        info["order_timeout_seconds"] = req.order_timeout_seconds
    if req.traits is not None:
        info["traits"] = req.traits.model_dump()
    store.save_info(trader_id, info)
    return _load_trader_info(trader_id)


@router.delete("/{trader_id}", status_code=204, summary="Delete trader")
def delete_trader(trader_id: str):
    _assert_exists(trader_id)
    import shutil

    shutil.rmtree(store.trader_dir(trader_id))


@router.get(
    "/{trader_id}/strategy",
    response_model=List[StrategyFileModel],
    summary="List strategy files",
)
def list_strategies(trader_id: str):
    _assert_exists(trader_id)
    sdir = store.strategy_dir(trader_id)
    info = store.load_info(trader_id)
    active = info.get("active_strategy", "")
    if not os.path.isdir(sdir):
        return []
    return [
        StrategyFileModel(filename=f, is_active=(f == active))
        for f in sorted(os.listdir(sdir))
        if f.endswith(".py")
    ]


@router.post(
    "/{trader_id}/strategy",
    response_model=StrategyFileModel,
    status_code=201,
    summary="Upload strategy file",
)
async def upload_strategy(trader_id: str, file: UploadFile = File(...)):
    _assert_exists(trader_id)
    if not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only .py files are supported.")
    sdir = store.strategy_dir(trader_id)
    os.makedirs(sdir, exist_ok=True)
    dest = os.path.join(sdir, file.filename)
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    info = store.load_info(trader_id)
    active = info.get("active_strategy", "")
    return StrategyFileModel(filename=file.filename, is_active=(file.filename == active))


@router.post(
    "/{trader_id}/strategy/research",
    status_code=200,
    summary="Research strategy",
    description="Invoke Codex to research and generate a trading strategy for the specified trader.",
)
def research_strategy(
    trader_id: str,
    mode: str = Query(default="create", pattern="^(create|update)$"),
    target: Optional[str] = Query(default=None),
):
    from app.engine.trader import research_strategy as _research

    _assert_exists(trader_id)
    return _research_strategy_internal(trader_id, mode=mode, target=target, fn=_research)


def _research_strategy_internal(
    trader_id: str,
    mode: str,
    target: Optional[str],
    fn,
):
    _assert_exists(trader_id)

    def _stream():
        for evt in fn(trader_id, store, mode=mode, target=target):
            yield _sse_event(evt["event"], {k: v for k, v in evt.items() if k != "event"})

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.put(
    "/{trader_id}/strategy/active",
    response_model=TraderInfo,
    summary="Set active strategy",
)
def set_active_strategy(trader_id: str, filename: str):
    _assert_exists(trader_id)
    sdir = store.strategy_dir(trader_id)
    if not os.path.isfile(os.path.join(sdir, filename)):
        raise HTTPException(status_code=404, detail=f"Strategy file '{filename}' not found.")
    info = store.load_info(trader_id)
    info["active_strategy"] = filename
    store.save_info(trader_id, info)
    return _load_trader_info(trader_id)


@router.get(
    "/{trader_id}/strategy/{filename}/code",
    response_model=StrategyCodeModel,
    summary="Get strategy source code",
)
def get_strategy_code(trader_id: str, filename: str):
    _assert_exists(trader_id)

    normalized = os.path.basename(filename)
    if normalized != filename:
        raise HTTPException(status_code=400, detail="Invalid strategy filename.")
    if not normalized.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only .py strategy files are supported.")

    path = os.path.join(store.strategy_dir(trader_id), normalized)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"Strategy file '{normalized}' not found.")

    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    return StrategyCodeModel(filename=normalized, code=code)


@router.get(
    "/{trader_id}/portfolio/{mode}",
    response_model=PortfolioModel,
    summary="Get portfolio history",
    description="Returns all daily snapshots for the given mode (paper or backtest).",
)
def get_portfolio(trader_id: str, mode: str, run_id: Optional[str] = None):
    _assert_exists(trader_id)
    if mode not in ("paper", "backtest"):
        raise HTTPException(status_code=400, detail="mode must be paper or backtest")
    records = store.load_portfolio(trader_id, mode, run_id=run_id if mode == "backtest" else None)
    if records is None:
        raise HTTPException(status_code=404, detail=f"No portfolio data for mode '{mode}'.")

    if mode == "backtest" and run_id:
        if not records:
            report = store.load_report(trader_id, run_id, mode="backtest")
            if report is None:
                raise HTTPException(status_code=404, detail=f"No portfolio data for backtest run '{run_id}'.")
            full_records = store.load_portfolio(trader_id, mode) or []
            try:
                start = datetime.fromisoformat(report["backtest_start"]).date()
                end = datetime.fromisoformat(report["backtest_end"]).date()
            except Exception:
                raise HTTPException(status_code=404, detail=f"No portfolio data for backtest run '{run_id}'.")
            filtered = []
            for r in full_records:
                d = r.get("date")
                if not isinstance(d, str):
                    continue
                try:
                    rd = date.fromisoformat(d)
                except ValueError:
                    continue
                if start <= rd <= end:
                    filtered.append(r)
            records = filtered
        if not records:
            raise HTTPException(status_code=404, detail=f"No portfolio data for backtest run '{run_id}'.")
    snapshots = [
        PortfolioSnapshotModel(
            date=r["date"],
            cash=r["cash"],
            positions={sym: PositionModel(**pos) for sym, pos in r.get("positions", {}).items()},
        )
        for r in records
    ]
    return PortfolioModel(trader_id=trader_id, mode=mode, snapshots=snapshots)


@router.get(
    "/{trader_id}/trades",
    response_model=Dict[str, List[str]],
    summary="List trade runs",
)
def list_trades(trader_id: str):
    _assert_exists(trader_id)
    return {
        "paper": store.list_trade_runs(trader_id, "paper"),
        "backtest": store.list_trade_runs(trader_id, "backtest"),
    }


@router.get(
    "/{trader_id}/trades/{mode}/{run_id}",
    response_model=List[TradeModel],
    summary="Get one trade run",
)
def get_trades(trader_id: str, mode: str, run_id: str):
    _assert_exists(trader_id)
    if mode not in ("paper", "backtest"):
        raise HTTPException(status_code=400, detail="mode must be paper or backtest")
    if run_id not in store.list_trade_runs(trader_id, mode):
        raise HTTPException(status_code=404, detail=f"Trades not found: {mode}/{run_id}")
    trades = store.load_trades(trader_id, run_id, mode)
    if not isinstance(trades, list):
        raise HTTPException(status_code=422, detail=f"Invalid trades payload for run: {mode}/{run_id}")
    if any(not isinstance(t, dict) for t in trades):
        raise HTTPException(status_code=422, detail=f"Invalid trade record format for run: {mode}/{run_id}")
    return [TradeModel(**t) for t in trades]


@router.get(
    "/{trader_id}/backtest/report/{run_id}",
    response_model=BacktestReportModel,
    summary="Get one backtest report",
)
def get_backtest_report(trader_id: str, run_id: str):
    _assert_exists(trader_id)
    report = store.load_report(trader_id, run_id, mode="backtest")
    if report is None:
        raise HTTPException(status_code=404, detail=f"Backtest report not found: {run_id}")
    try:
        return BacktestReportModel(**report)
    except Exception:
        raise HTTPException(status_code=422, detail=f"Invalid backtest report format: {run_id}")


@router.delete(
    "/{trader_id}/backtest/run/{run_id}",
    status_code=204,
    summary="Delete one backtest run",
)
def delete_backtest_run(trader_id: str, run_id: str):
    _assert_exists(trader_id)
    if run_id not in store.list_trade_runs(trader_id, "backtest"):
        raise HTTPException(status_code=404, detail=f"Backtest run not found: {run_id}")
    deleted = store.delete_trade_run(trader_id, run_id, mode="backtest")
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Backtest run not found: {run_id}")
    return None


@router.post(
    "/{trader_id}/backtest/run",
    response_model=BacktestRunResult,
    summary="Run one backtest for a trader",
)
def run_backtest_once(trader_id: str, req: BacktestRunRequest):
    from app.adapters.data_feed import AkshareDataFeed, BaostockDataFeed, YfinanceDataFeed
    from app.adapters.simulator import Simulator
    from app.core.config import load_config
    from app.data.repository import MarketRepository
    from app.engine.core import Engine, EngineMode
    from app.engine.trader import Trader

    _assert_exists(trader_id)

    today = date.today()
    default_start = _subtract_months(today, 3)
    start_date_raw = req.start_date or default_start.isoformat()
    end_date_raw = req.end_date or today.isoformat()

    try:
        start_date = date.fromisoformat(start_date_raw)
        end_date = date.fromisoformat(end_date_raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="start_date/end_date must be YYYY-MM-DD")

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")

    repo_root = Path(__file__).resolve().parents[3]
    config = load_config(str(repo_root / "backend" / "config.yaml"))

    repository = MarketRepository()
    simulator = Simulator(commission_rate=0.0003)
    strategy_filename = req.strategy_filename
    if strategy_filename is not None:
        strategy_filename = strategy_filename.strip() or None

    try:
        trader = Trader.from_dir(
            trader_id,
            store,
            repository,
            simulator,
            strategy_filename=strategy_filename,
            require_active_strategy=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid strategy selection: {exc}")

    feed_cls_map = {
        "akshare": AkshareDataFeed,
        "baostock": BaostockDataFeed,
        "yfinance": YfinanceDataFeed,
    }
    feed_name = config.data_sources.get(trader.market.value, "yfinance").lower()
    feed_cls = feed_cls_map.get(feed_name)
    if feed_cls is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown data source '{feed_name}' for market '{trader.market.value}'.",
        )

    engine = Engine(
        mode=EngineMode.BACKTEST,
        traders=[trader],
        repository=repository,
        simulator=simulator,
        data_feeds=[feed_cls()],
        config=config,
        store=store,
        backtest_start=start_date.isoformat(),
        backtest_end=end_date.isoformat(),
    )

    try:
        engine.start()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {exc}")

    # Ensure trade run metadata exists even when there are no fills.
    trader.save_trades(store, engine._run_id, mode="backtest")
    logger.info("Backtest API completed: trader_id=%s run_id=%s", trader_id, engine._run_id)
    engine_logger.info("Backtest API completed: trader_id=%s run_id=%s", trader_id, engine._run_id)

    return BacktestRunResult(trader_id=trader_id, run_id=engine._run_id)


def _assert_exists(trader_id: str):
    if trader_id not in store.list_traders():
        raise HTTPException(status_code=404, detail=f"Trader '{trader_id}' not found.")


def _load_trader_info(trader_id: str) -> TraderInfo:
    info = store.load_info(trader_id)
    return TraderInfo(
        id=info["id"],
        market=info["market"],
        initial_cash=info["initial_cash"],
        allowed_symbols=info["allowed_symbols"],
        commission_rate=info["commission_rate"],
        order_timeout_seconds=info.get("order_timeout_seconds", 300),
        active_strategy=info.get("active_strategy", ""),
        traits=TraitsModel(**info.get("traits", {})),
    )


def _sse_event(event: str, payload: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _subtract_months(d: date, months: int) -> date:
    year = d.year
    month = d.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(d.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 2:
        is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        return 29 if is_leap else 28
    if month in (4, 6, 9, 11):
        return 30
    return 31


def _build_agent_cmd() -> List[str]:
    from app.core.config import load_config
    repo_root = Path(__file__).resolve().parents[3]
    config_path = repo_root / "backend" / "config.yaml"
    cfg = load_config(str(config_path))
    agent_type = cfg.ai_agent.type
    return build_agent_cmd(agent_type, repo_root)


def _build_codex_prompt(req: CreateTraderRequest) -> str:
    repo_root = Path(__file__).resolve().parents[3]
    skill_path = (repo_root / "skills" / "retail-quant-trainer" / "SKILL.md").as_posix()
    return (
        f"Use [$retail-quant-trainer]({skill_path}). "
        f"Create exactly one trader with id '{req.id}'. "
        f"Market: {req.market}. "
        f"Initial cash: {req.initial_cash}. "
        f"Allowed symbols: {', '.join(req.allowed_symbols)}. "
        f"Commission rate: {req.commission_rate}. "
        f"Order timeout seconds: {req.order_timeout_seconds}. "
        "Do not call backend API directly. "
        "Create trader skill artifacts only. "
        "At the end print exactly one line: "
        'FINAL_TRAITS_JSON: {"risk_appetite":"...","holding_horizon":"...","signal_preference":"...","position_construction":"...","exit_discipline":"...","universe_focus":"..."}'
    )
