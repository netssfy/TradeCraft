from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.engine.trader_store import TraderStore

router = APIRouter(prefix="/traders", tags=["traders"])
store = TraderStore(base_dir="data/traders")


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
                _build_codex_cmd(),
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
    "/{trader_id}/portfolio/{mode}",
    response_model=PortfolioModel,
    summary="Get portfolio history",
    description="Returns all daily snapshots for the given mode (paper or backtest).",
)
def get_portfolio(trader_id: str, mode: str):
    _assert_exists(trader_id)
    if mode not in ("paper", "backtest"):
        raise HTTPException(status_code=400, detail="mode must be paper or backtest")
    records = store.load_portfolio(trader_id, mode)
    if records is None:
        raise HTTPException(status_code=404, detail=f"No portfolio data for mode '{mode}'.")
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
    trades = store.load_trades(trader_id, run_id, mode)
    if not trades:
        raise HTTPException(status_code=404, detail=f"Trades not found: {mode}/{run_id}")
    return [TradeModel(**t) for t in trades]


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


def _build_codex_cmd() -> List[str]:
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
