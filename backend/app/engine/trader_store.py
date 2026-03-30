"""
TraderStore — Trader 持久化管理。

目录结构：
  data/traders/{name}/
    trader.json       # 基础信息（market、initial_cash、allowed_symbols 等）
    strategy/         # 策略文件（.py）
    trades/           # 历史成交记录（按 run_id 分文件）
    portfolio/        # 持仓快照
"""
from __future__ import annotations

import json
import os
import shutil
from typing import Any, Dict, List, Optional


TRADER_JSON = "trader.json"
STRATEGY_DIR = "strategy"
TRADES_DIR = "trades"
PORTFOLIO_DIR = "portfolio"


class TraderStoreError(Exception):
    pass


class TraderStore:
    """负责 data/traders/{name}/ 目录的读写操作。"""

    def __init__(self, base_dir: str = "data/traders") -> None:
        self.base_dir = base_dir

    # ------------------------------------------------------------------
    # 目录路径辅助
    # ------------------------------------------------------------------

    def trader_dir(self, name: str) -> str:
        return os.path.join(self.base_dir, name)

    def trader_json_path(self, name: str) -> str:
        return os.path.join(self.trader_dir(name), TRADER_JSON)

    def strategy_dir(self, name: str) -> str:
        return os.path.join(self.trader_dir(name), STRATEGY_DIR)

    def trades_dir(self, name: str, mode: str = "backtest") -> str:
        return os.path.join(self.trader_dir(name), "trades", mode)

    def trade_run_dir(self, name: str, mode: str, run_id: str) -> str:
        return os.path.join(self.trades_dir(name, mode), run_id)

    def trade_run_trades_path(self, name: str, mode: str, run_id: str) -> str:
        return os.path.join(self.trade_run_dir(name, mode, run_id), "trades.json")

    def trade_run_report_path(self, name: str, mode: str, run_id: str) -> str:
        return os.path.join(self.trade_run_dir(name, mode, run_id), "report.json")

    def portfolio_dir(self, name: str) -> str:
        return os.path.join(self.trader_dir(name), PORTFOLIO_DIR)

    # ------------------------------------------------------------------
    # 基础信息
    # ------------------------------------------------------------------

    def load_info(self, name: str) -> Dict[str, Any]:
        """读取 trader.json，返回原始字典。"""
        path = self.trader_json_path(name)
        if not os.path.exists(path):
            raise TraderStoreError(f"Trader '{name}' not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_info(self, name: str, info: Dict[str, Any]) -> None:
        """写入 trader.json。"""
        os.makedirs(self.trader_dir(name), exist_ok=True)
        path = self.trader_json_path(name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # 策略文件
    # ------------------------------------------------------------------

    def get_strategy_path(
        self,
        name: str,
        strategy_filename: Optional[str] = None,
        require_active: bool = True,
    ) -> str:
        """返回 active_strategy 指定的策略文件路径。
        
        优先读取 trader.json 中的 active_strategy 字段；
        若未配置则 fallback 到 strategy/ 目录下第一个 .py 文件。
        """
        sdir = self.strategy_dir(name)
        if not os.path.isdir(sdir):
            raise TraderStoreError(f"Strategy directory not found for trader '{name}': {sdir}")

        selected = strategy_filename
        if not selected:
            # 尝试从 trader.json 读取 active_strategy
            try:
                info = self.load_info(name)
                selected = info.get("active_strategy")
            except TraderStoreError:
                selected = None

        if not selected:
            if require_active:
                raise TraderStoreError(
                    f"Trader '{name}' has no active_strategy configured in trader.json"
                )
            candidates = sorted(f for f in os.listdir(sdir) if f.endswith(".py"))
            if not candidates:
                raise TraderStoreError(
                    f"Trader '{name}' has no strategy files in {sdir}"
                )
            selected = candidates[0]

        path = os.path.join(sdir, selected)
        if not os.path.isfile(path):
            raise TraderStoreError(
                f"strategy '{selected}' not found in {sdir}"
            )
        return path

    def install_strategy(self, name: str, src_path: str) -> str:
        """将策略文件复制到 strategy/ 目录，返回目标路径。"""
        sdir = self.strategy_dir(name)
        os.makedirs(sdir, exist_ok=True)
        dst = os.path.join(sdir, os.path.basename(src_path))
        shutil.copy2(src_path, dst)
        return dst

    # ------------------------------------------------------------------
    # 历史成交
    # ------------------------------------------------------------------

    def save_trades(self, name: str, run_id: str, trades: List[Dict[str, Any]], mode: str = "backtest") -> str:
        """将成交记录写入 trades/{mode}/{run_id}.json，返回文件路径。"""
        run_dir = self.trade_run_dir(name, mode, run_id)
        os.makedirs(run_dir, exist_ok=True)
        path = self.trade_run_trades_path(name, mode, run_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)
        return path

    def load_trades(self, name: str, run_id: str, mode: str = "backtest") -> List[Dict[str, Any]]:
        """读取指定 run_id 的成交记录。"""
        path = self.trade_run_trades_path(name, mode, run_id)
        if not os.path.exists(path):
            path = os.path.join(self.trades_dir(name, mode), f"{run_id}.json")
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_report(self, name: str, run_id: str, report: Dict[str, Any], mode: str = "backtest") -> str:
        run_dir = self.trade_run_dir(name, mode, run_id)
        os.makedirs(run_dir, exist_ok=True)
        path = self.trade_run_report_path(name, mode, run_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return path

    def load_report(self, name: str, run_id: str, mode: str = "backtest") -> Optional[Dict[str, Any]]:
        path = self.trade_run_report_path(name, mode, run_id)
        if not os.path.exists(path):
            path = os.path.join(self.trades_dir(name, mode), f"{run_id}_report.json")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_trade_runs(self, name: str, mode: str = "backtest") -> List[str]:
        """列出所有历史 run_id。"""
        tdir = self.trades_dir(name, mode)
        if not os.path.isdir(tdir):
            return []
        run_ids = set()
        for entry in os.listdir(tdir):
            full_path = os.path.join(tdir, entry)
            if os.path.isdir(full_path):
                run_ids.add(entry)
                continue
            if entry.endswith(".json") and not entry.endswith("_report.json"):
                run_ids.add(entry[:-5])
        return sorted(run_ids)

    # ------------------------------------------------------------------
    # 持仓快照
    # ------------------------------------------------------------------

    def _portfolio_path(self, name: str, mode: str, run_id: Optional[str] = None) -> str:
        # Backtest snapshots are stored as portfolio/{run_id}.json for one-to-one mapping.
        if mode == "backtest" and run_id:
            return os.path.join(self.portfolio_dir(name), f"{run_id}.json")
        return os.path.join(self.portfolio_dir(name), f"{mode}.json")

    def append_portfolio_snapshot(
        self,
        name: str,
        mode: str,
        snapshot: Dict[str, Any],
        run_id: Optional[str] = None,
    ) -> str:
        """将单日快照追加（或更新）到 portfolio/{mode}.json 数组中。

        snapshot 必须包含 "date" 字段（YYYY-MM-DD）。
        若同一 date 已存在则覆盖，否则追加。
        返回文件路径。
        """
        pdir = self.portfolio_dir(name)
        os.makedirs(pdir, exist_ok=True)
        path = self._portfolio_path(name, mode, run_id=run_id)

        records: List[Dict[str, Any]] = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                records = json.load(f)

        date = snapshot.get("date")
        # 更新已有日期或追加
        for i, rec in enumerate(records):
            if rec.get("date") == date:
                records[i] = snapshot
                break
        else:
            records.append(snapshot)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return path

    def load_portfolio(
        self,
        name: str,
        mode: str = "paper",
        run_id: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """读取 portfolio/{mode}.json，返回快照数组；文件不存在时返回 None。"""
        if mode == "backtest" and run_id:
            # New layout: one file per backtest run.
            path = self._portfolio_path(name, mode, run_id=run_id)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            # Backward compatibility for historical backtest.json layout.
            legacy_path = self._portfolio_path(name, mode)
            if not os.path.exists(legacy_path):
                return None
            with open(legacy_path, "r", encoding="utf-8") as f:
                records = json.load(f)
            return [r for r in records if r.get("run_id") == run_id]

        path = self._portfolio_path(name, mode)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_latest_portfolio(self, name: str) -> Optional[Dict[str, Any]]:
        """从 paper.json 或 backtest.json 中取最新一条快照，用于恢复持仓。"""
        for mode in ("paper", "backtest"):
            records = self.load_portfolio(name, mode)
            if records:
                return records[-1]
        return None

    # ------------------------------------------------------------------
    # 枚举所有 trader
    # ------------------------------------------------------------------

    def list_traders(self) -> List[str]:
        """返回 base_dir 下所有有效 trader 的名称列表。"""
        if not os.path.isdir(self.base_dir):
            return []
        return sorted(
            d for d in os.listdir(self.base_dir)
            if os.path.isfile(os.path.join(self.base_dir, d, TRADER_JSON))
        )
