from __future__ import annotations

import json

import pytest

from app.engine.trader_store import TraderStore, TraderStoreError


def _prepare_trader(base_dir: str, trader_id: str, active_strategy: str = "") -> None:
    store = TraderStore(base_dir=base_dir)
    strategy_dir = store.strategy_dir(trader_id)

    import os

    os.makedirs(strategy_dir, exist_ok=True)
    with open(store.trader_json_path(trader_id), "w", encoding="utf-8") as f:
        json.dump(
            {
                "id": trader_id,
                "market": "US",
                "initial_cash": 100000.0,
                "allowed_symbols": ["AAPL"],
                "commission_rate": 0.0003,
                "order_timeout_seconds": 300,
                "active_strategy": active_strategy,
                "traits": {},
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def test_get_strategy_path_requires_active_by_default(tmp_path):
    base_dir = str(tmp_path / "traders")
    trader_id = "t1"
    _prepare_trader(base_dir, trader_id, active_strategy="")
    store = TraderStore(base_dir=base_dir)

    (tmp_path / "traders" / trader_id / "strategy" / "b.py").write_text("pass\n", encoding="utf-8")

    with pytest.raises(TraderStoreError, match="has no active_strategy"):
        store.get_strategy_path(trader_id)


def test_get_strategy_path_backtest_mode_can_ignore_active(tmp_path):
    base_dir = str(tmp_path / "traders")
    trader_id = "t2"
    _prepare_trader(base_dir, trader_id, active_strategy="")
    store = TraderStore(base_dir=base_dir)

    strategy_root = tmp_path / "traders" / trader_id / "strategy"
    first = strategy_root / "a_first.py"
    second = strategy_root / "z_second.py"
    first.write_text("pass\n", encoding="utf-8")
    second.write_text("pass\n", encoding="utf-8")

    selected = store.get_strategy_path(trader_id, require_active=False)
    assert selected.endswith("a_first.py")
