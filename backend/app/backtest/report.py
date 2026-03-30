from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Report:
    trader_id: str
    backtest_start: datetime
    backtest_end: datetime
    initial_cash: float
    final_nav: float
    strategy_filename: str | None
    metrics: dict

    def to_json(self) -> str:
        data = {
            "trader_id": self.trader_id,
            "backtest_start": self.backtest_start.isoformat(),
            "backtest_end": self.backtest_end.isoformat(),
            "initial_cash": self.initial_cash,
            "final_nav": self.final_nav,
            "strategy_filename": self.strategy_filename,
            "metrics": self.metrics,
        }
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "Report":
        data = json.loads(json_str)
        return cls(
            trader_id=data["trader_id"],
            backtest_start=datetime.fromisoformat(data["backtest_start"]),
            backtest_end=datetime.fromisoformat(data["backtest_end"]),
            initial_cash=data["initial_cash"],
            final_nav=data["final_nav"],
            strategy_filename=data.get("strategy_filename"),
            metrics=data["metrics"],
        )
