from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.data.market import BarInterval, Market
from app.engine.models import Bar


class MarketRepository:
    """本地市场数据缓存，按月分片存储为 Parquet 文件。

    存储路径：{base_path}/{Market}/{Symbol}/{interval}/YYYY-MM.parquet
    """

    def __init__(self, base_path: str = "data/market") -> None:
        self.base_path = base_path
        self._parquet_cache: Dict[str, Tuple[float, pd.DataFrame]] = {}
        self._parquet_cache_max = 256

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _dir_path(self, market: Market, symbol: str, interval: BarInterval) -> str:
        return os.path.join(self.base_path, market.value, symbol, interval.value)

    def _file_path(self, market: Market, symbol: str, interval: BarInterval, year: int, month: int) -> str:
        filename = f"{year:04d}-{month:02d}.parquet"
        return os.path.join(self._dir_path(market, symbol, interval), filename)

    @staticmethod
    def _bars_to_df(bars: List[Bar]) -> pd.DataFrame:
        records = [
            {
                "timestamp": bar.timestamp,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
            for bar in bars
        ]
        df = pd.DataFrame(records)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df

    @staticmethod
    def _df_to_bars(df: pd.DataFrame, symbol: str, market: Market, interval: BarInterval) -> List[Bar]:
        bars: List[Bar] = []
        for _, row in df.iterrows():
            ts = row["timestamp"]
            if hasattr(ts, "to_pydatetime"):
                ts = ts.to_pydatetime()
            bars.append(
                Bar(
                    symbol=symbol,
                    market=market,
                    interval=interval,
                    timestamp=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )
        return bars

    def _read_parquet(self, path: str) -> pd.DataFrame:
        """Read a single parquet file; return empty DataFrame if not found."""
        if not os.path.exists(path):
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        mtime = os.path.getmtime(path)
        cached = self._parquet_cache.get(path)
        if cached and cached[0] == mtime:
            return cached[1]
        df = pd.read_parquet(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        self._cache_parquet(path, mtime, df)
        return df

    def _write_parquet(self, path: str, df: pd.DataFrame) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_parquet(path, index=False)
        mtime = os.path.getmtime(path)
        self._cache_parquet(path, mtime, df)

    def _cache_parquet(self, path: str, mtime: float, df: pd.DataFrame) -> None:
        self._parquet_cache[path] = (mtime, df)
        if len(self._parquet_cache) > self._parquet_cache_max:
            oldest_key = next(iter(self._parquet_cache))
            self._parquet_cache.pop(oldest_key, None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write(
        self,
        bars: List[Bar],
        market: Market,
        symbol: str,
        interval: BarInterval,
    ) -> int:
        """幂等写入，返回实际新增条数。

        按月分片：每个 YYYY-MM.parquet 只存该月数据。
        去重依据：timestamp（精确匹配）。
        """
        if not bars:
            return 0

        new_df = self._bars_to_df(bars)

        # Group incoming bars by (year, month) — strip tz before to_period to avoid warning
        new_df["_ym"] = new_df["timestamp"].dt.tz_localize(None).dt.to_period("M")
        groups = new_df.groupby("_ym")

        total_added = 0

        for period, group in groups:
            year, month = period.year, period.month
            path = self._file_path(market, symbol, interval, year, month)

            existing = self._read_parquet(path)

            incoming = group.drop(columns=["_ym"]).copy()

            if existing.empty:
                merged = incoming
                added = len(merged)
            else:
                # Deduplicate: keep only timestamps not already stored
                existing_ts = set(existing["timestamp"].astype(str))
                incoming_ts_str = incoming["timestamp"].astype(str)
                mask = ~incoming_ts_str.isin(existing_ts)
                new_rows = incoming[mask]
                added = len(new_rows)
                if added == 0:
                    continue
                merged = pd.concat([existing, new_rows], ignore_index=True)

            merged = merged.sort_values("timestamp").reset_index(drop=True)
            self._write_parquet(path, merged)
            total_added += added

        return total_added

    def read(
        self,
        symbol: str,
        market: Market,
        interval: BarInterval,
        start: datetime,
        end: datetime,
    ) -> List[Bar]:
        """按条件查询，结果按时间戳升序排列。"""
        dir_path = self._dir_path(market, symbol, interval)
        if not os.path.isdir(dir_path):
            return []

        start_ts = pd.Timestamp(start, tz="UTC") if start.tzinfo is None else pd.Timestamp(start).tz_convert("UTC")
        end_ts = pd.Timestamp(end, tz="UTC") if end.tzinfo is None else pd.Timestamp(end).tz_convert("UTC")

        # Determine which monthly files overlap with [start, end]
        start_period = pd.Period(start_ts, freq="M")
        end_period = pd.Period(end_ts, freq="M")

        frames: List[pd.DataFrame] = []
        period = start_period
        while period <= end_period:
            path = self._file_path(market, symbol, interval, period.year, period.month)
            df = self._read_parquet(path)
            if not df.empty:
                frames.append(df)
            period += 1

        if not frames:
            return []

        combined = pd.concat(frames, ignore_index=True)
        combined["timestamp"] = pd.to_datetime(combined["timestamp"], utc=True)
        mask = (combined["timestamp"] >= start_ts) & (combined["timestamp"] <= end_ts)
        filtered = combined[mask].sort_values("timestamp").reset_index(drop=True)

        return self._df_to_bars(filtered, symbol, market, interval)

    def get_latest_timestamp(
        self,
        symbol: str,
        market: Market,
        interval: BarInterval,
    ) -> Optional[datetime]:
        """返回本地最新数据时间戳，无数据时返回 None。"""
        dir_path = self._dir_path(market, symbol, interval)
        if not os.path.isdir(dir_path):
            return None

        parquet_files = sorted(
            f for f in os.listdir(dir_path) if f.endswith(".parquet")
        )
        if not parquet_files:
            return None

        # The last file (lexicographically) holds the most recent month
        latest_file = os.path.join(dir_path, parquet_files[-1])
        df = self._read_parquet(latest_file)
        if df.empty:
            return None

        latest_ts = df["timestamp"].max()
        if hasattr(latest_ts, "to_pydatetime"):
            return latest_ts.to_pydatetime()
        return latest_ts
