from __future__ import annotations

from typing import Dict, List

from app.engine.models import Direction, Fill, Position, Trade


class Portfolio:
    def __init__(self, initial_cash: float) -> None:
        self._cash: float = initial_cash
        self._positions: Dict[str, Position] = {}
        self._trade_history: List[Trade] = []

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def positions(self) -> Dict[str, Position]:
        return self._positions

    @property
    def trade_history(self) -> List[Trade]:
        return self._trade_history

    def net_value(self, prices: Dict[str, float]) -> float:
        """现金 + 所有持仓市值"""
        holdings = sum(
            pos.quantity * prices[symbol]
            for symbol, pos in self._positions.items()
            if symbol in prices
        )
        return self._cash + holdings

    def update_on_fill(self, fill: Fill) -> None:
        """成交后更新持仓和现金，持仓归零时移除 Position"""
        if fill.direction == Direction.BUY:
            cost = fill.quantity * fill.price + fill.commission
            self._cash -= cost

            if fill.symbol in self._positions:
                pos = self._positions[fill.symbol]
                total_qty = pos.quantity + fill.quantity
                pos.avg_cost = (
                    (pos.quantity * pos.avg_cost + fill.quantity * fill.price)
                    / total_qty
                )
                pos.quantity = total_qty
            else:
                self._positions[fill.symbol] = Position(
                    symbol=fill.symbol,
                    quantity=fill.quantity,
                    avg_cost=fill.price,
                )
        else:  # SELL
            proceeds = fill.quantity * fill.price - fill.commission
            self._cash += proceeds

            if fill.symbol in self._positions:
                pos = self._positions[fill.symbol]
                pos.quantity -= fill.quantity
                if pos.quantity <= 0:
                    del self._positions[fill.symbol]

        self._trade_history.append(
            Trade(
                timestamp=fill.timestamp,
                symbol=fill.symbol,
                direction=fill.direction,
                quantity=fill.quantity,
                price=fill.price,
                commission=fill.commission,
            )
        )

    def can_sell(self, symbol: str, quantity: float) -> bool:
        """检查是否有足够持仓"""
        pos = self._positions.get(symbol)
        return pos is not None and pos.quantity >= quantity

    def get_position(self, symbol: str) -> Position | None:
        return self._positions.get(symbol)
