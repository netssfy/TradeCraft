from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/market", tags=["market"])


class MarketDataItem(BaseModel):
    market: str
    symbol: str
    interval: str
    file_count: int
    start_period: str | None
    end_period: str | None
    periods: List[str]


class MarketDataAvailability(BaseModel):
    root: str
    total_files: int
    items: List[MarketDataItem]


class MarketDataFileDetail(BaseModel):
    market: str
    symbol: str
    interval: str
    period: str
    path: str
    columns: List[str]
    total_rows: int
    page: int
    page_size: int
    rows: List[Dict[str, Any]]


@router.get("/availability", response_model=MarketDataAvailability, summary="List local market data availability")
def list_market_data_availability():
    root = Path("data/market")
    files = sorted(root.rglob("*.parquet")) if root.exists() else []
    grouped: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)

    for file_path in files:
        rel = file_path.relative_to(root)
        if len(rel.parts) < 4:
            continue
        market, symbol, interval = rel.parts[0], rel.parts[1], rel.parts[2]
        period = file_path.stem
        grouped[(market, symbol, interval)].append(period)

    items: List[MarketDataItem] = []
    for (market, symbol, interval), periods in sorted(grouped.items()):
        unique_periods = sorted(set(periods))
        items.append(
            MarketDataItem(
                market=market,
                symbol=symbol,
                interval=interval,
                file_count=len(unique_periods),
                start_period=unique_periods[0] if unique_periods else None,
                end_period=unique_periods[-1] if unique_periods else None,
                periods=unique_periods,
            )
        )

    return MarketDataAvailability(
        root=root.as_posix(),
        total_files=len(files),
        items=items,
    )


@router.get(
    "/file/{market}/{symbol}/{interval}/{period}",
    response_model=MarketDataFileDetail,
    summary="Get one local market data file content",
)
def get_market_data_file(
    market: str,
    symbol: str,
    interval: str,
    period: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    root = Path("data/market")
    file_path = root / market / symbol / interval / f"{period}.parquet"
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Market data file not found: {file_path.as_posix()}")

    try:
        df = pd.read_parquet(file_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read parquet file: {exc}")

    total_rows = len(df.index)
    start = (page - 1) * page_size
    end = start + page_size
    page_df = df.iloc[start:end].copy() if start < total_rows else df.iloc[0:0].copy()
    page_rows = _rows_to_jsonable(page_df)

    return MarketDataFileDetail(
        market=market,
        symbol=symbol,
        interval=interval,
        period=period,
        path=file_path.as_posix(),
        columns=[str(column) for column in df.columns.tolist()],
        total_rows=total_rows,
        page=page,
        page_size=page_size,
        rows=page_rows,
    )


def _rows_to_jsonable(df: pd.DataFrame) -> List[Dict[str, Any]]:
    records = df.to_dict(orient="records")
    rows: List[Dict[str, Any]] = []
    for record in records:
        item: Dict[str, Any] = {}
        for key, value in record.items():
            item[str(key)] = _to_jsonable(value)
        rows.append(item)
    return rows


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
