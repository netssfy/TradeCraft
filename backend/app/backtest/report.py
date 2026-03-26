from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from app.engine.models import Direction, Trade


@dataclass
class Report:
    trader_id: str
    backtest_start: datetime
    backtest_end: datetime
    initial_cash: float
    final_nav: float
    metrics: dict
    trades: List[Trade] = field(default_factory=list)

    def to_json(self) -> str:
        data = {
            "trader_id": self.trader_id,
            "backtest_start": self.backtest_start.isoformat(),
            "backtest_end": self.backtest_end.isoformat(),
            "initial_cash": self.initial_cash,
            "final_nav": self.final_nav,
            "metrics": self.metrics,
            "trades": [
                {
                    "timestamp": t.timestamp.isoformat(),
                    "symbol": t.symbol,
                    "direction": t.direction.value,
                    "quantity": t.quantity,
                    "price": t.price,
                    "commission": t.commission,
                }
                for t in self.trades
            ],
        }
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "Report":
        data = json.loads(json_str)
        trades = [
            Trade(
                timestamp=datetime.fromisoformat(t["timestamp"]),
                symbol=t["symbol"],
                direction=Direction(t["direction"]),
                quantity=t["quantity"],
                price=t["price"],
                commission=t["commission"],
            )
            for t in data.get("trades", [])
        ]
        return cls(
            trader_id=data["trader_id"],
            backtest_start=datetime.fromisoformat(data["backtest_start"]),
            backtest_end=datetime.fromisoformat(data["backtest_end"]),
            initial_cash=data["initial_cash"],
            final_nav=data["final_nav"],
            metrics=data["metrics"],
            trades=trades,
        )
