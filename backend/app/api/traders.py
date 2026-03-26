from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from app.engine.trader_store import TraderStore, TraderStoreError

router = APIRouter(prefix="/traders", tags=["traders"])
store = TraderStore(base_dir="data/traders")


# ---------------------------------------------------------------------------
# Shared models
# ---------------------------------------------------------------------------

class TraitsModel(BaseModel):
    risk_appetite: str = Field(..., description="风险偏好: conservative / balanced / aggressive within bounds")
    holding_horizon: str = Field(..., description="持仓周期: short swing / medium trend / event-driven tactical")
    signal_preference: str = Field(..., description="信号偏好: trend-following / mean-reversion / event-confirmed")
    position_construction: str = Field(..., description="建仓方式: single-entry fixed size / layered entry / risk-budget sizing")
    exit_discipline: str = Field(..., description="退出纪律: fixed stop + fixed take-profit / trailing stop / time stop + condition stop")
    universe_focus: str = Field(..., description="标的范围: large/mega-cap leaders / sector leaders / narrow watchlist")


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


class PortfolioModel(BaseModel):
    trader_id: str
    cash: float
    positions: Dict[str, PositionModel]


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


# ---------------------------------------------------------------------------
# POST /traders — 创建
# ---------------------------------------------------------------------------

class CreateTraderRequest(BaseModel):
    id: str = Field(..., description="Trader 唯一标识符")
    market: str = Field(..., description="市场: CN / HK / US")
    initial_cash: float = Field(..., gt=0, description="初始资金")
    allowed_symbols: List[str] = Field(..., min_length=1, description="允许交易的标的列表")
    commission_rate: float = Field(..., ge=0, le=0.01, description="佣金率，例如 0.0003")
    order_timeout_seconds: int = Field(300, gt=0, description="订单超时秒数")
    traits: TraitsModel


@router.post(
    "",
    response_model=TraderInfo,
    status_code=201,
    summary="创建 Trader",
    description="创建新 Trader 并初始化目录结构，active_strategy 默认为空。",
)
def create_trader(req: CreateTraderRequest):
    if req.id in store.list_traders():
        raise HTTPException(status_code=409, detail=f"Trader '{req.id}' already exists.")

    info = {
        "id": req.id,
        "market": req.market,
        "initial_cash": req.initial_cash,
        "allowed_symbols": req.allowed_symbols,
        "commission_rate": req.commission_rate,
        "order_timeout_seconds": req.order_timeout_seconds,
        "active_strategy": "",
        "traits": req.traits.model_dump(),
    }
    store.save_info(req.id, info)
    os.makedirs(store.strategy_dir(req.id), exist_ok=True)
    os.makedirs(store.trades_dir(req.id, "paper"), exist_ok=True)
    os.makedirs(store.trades_dir(req.id, "backtest"), exist_ok=True)
    os.makedirs(store.portfolio_dir(req.id), exist_ok=True)

    return _load_trader_info(req.id)


# ---------------------------------------------------------------------------
# GET /traders — 列表
# ---------------------------------------------------------------------------

@router.get("", response_model=List[TraderInfo], summary="获取所有 Trader")
def list_traders():
    return [_load_trader_info(name) for name in store.list_traders()]


# ---------------------------------------------------------------------------
# GET /traders/{id} — 详情
# ---------------------------------------------------------------------------

@router.get("/{trader_id}", response_model=TraderInfo, summary="获取 Trader 详情")
def get_trader(trader_id: str):
    _assert_exists(trader_id)
    return _load_trader_info(trader_id)


# ---------------------------------------------------------------------------
# PATCH /traders/{id} — 更新基础信息
# ---------------------------------------------------------------------------

class UpdateTraderRequest(BaseModel):
    initial_cash: Optional[float] = Field(None, gt=0)
    allowed_symbols: Optional[List[str]] = None
    commission_rate: Optional[float] = Field(None, ge=0, le=0.01)
    order_timeout_seconds: Optional[int] = Field(None, gt=0)
    traits: Optional[TraitsModel] = None


@router.patch("/{trader_id}", response_model=TraderInfo, summary="更新 Trader 基础信息")
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


# ---------------------------------------------------------------------------
# DELETE /traders/{id} — 删除
# ---------------------------------------------------------------------------

@router.delete("/{trader_id}", status_code=204, summary="删除 Trader")
def delete_trader(trader_id: str):
    _assert_exists(trader_id)
    import shutil
    shutil.rmtree(store.trader_dir(trader_id))


# ---------------------------------------------------------------------------
# GET/PUT /traders/{id}/strategy — 策略文件列表
# POST /traders/{id}/strategy — 上传策略文件
# PUT /traders/{id}/strategy/active — 设置激活策略
# ---------------------------------------------------------------------------

@router.get(
    "/{trader_id}/strategy",
    response_model=List[StrategyFileModel],
    summary="获取策略文件列表",
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
    summary="上传策略文件",
)
async def upload_strategy(trader_id: str, file: UploadFile = File(...)):
    _assert_exists(trader_id)
    if not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="只支持 .py 文件")
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
    summary="设置激活策略",
)
def set_active_strategy(trader_id: str, filename: str):
    _assert_exists(trader_id)
    sdir = store.strategy_dir(trader_id)
    if not os.path.isfile(os.path.join(sdir, filename)):
        raise HTTPException(status_code=404, detail=f"策略文件 '{filename}' 不存在")
    info = store.load_info(trader_id)
    info["active_strategy"] = filename
    store.save_info(trader_id, info)
    return _load_trader_info(trader_id)


# ---------------------------------------------------------------------------
# GET /traders/{id}/portfolio — 持仓快照
# ---------------------------------------------------------------------------

@router.get("/{trader_id}/portfolio", response_model=PortfolioModel, summary="获取持仓快照")
def get_portfolio(trader_id: str):
    _assert_exists(trader_id)
    snapshot = store.load_portfolio(trader_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="暂无持仓快照")
    return PortfolioModel(
        trader_id=snapshot["trader_id"],
        cash=snapshot["cash"],
        positions={
            sym: PositionModel(**pos)
            for sym, pos in snapshot.get("positions", {}).items()
        },
    )


# ---------------------------------------------------------------------------
# GET /traders/{id}/trades — 成交记录列表（按 mode）
# GET /traders/{id}/trades/{mode}/{run_id} — 单次运行成交记录
# ---------------------------------------------------------------------------

@router.get(
    "/{trader_id}/trades",
    response_model=Dict[str, List[str]],
    summary="获取成交记录索引",
    description="返回 paper 和 backtest 两个模式下的所有 run_id 列表。",
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
    summary="获取单次运行成交记录",
)
def get_trades(trader_id: str, mode: str, run_id: str):
    _assert_exists(trader_id)
    if mode not in ("paper", "backtest"):
        raise HTTPException(status_code=400, detail="mode 只能是 paper 或 backtest")
    trades = store.load_trades(trader_id, run_id, mode)
    if not trades:
        raise HTTPException(status_code=404, detail=f"未找到 {mode}/{run_id} 的成交记录")
    return [TradeModel(**t) for t in trades]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
