from __future__ import annotations

import math
from collections import defaultdict
from typing import List

from app.engine.models import Direction, Trade


class Metrics:
    @staticmethod
    def annualized_return(nav_series: List[float], trading_days: int = 252) -> float:
        """年化收益率: (final/initial)^(trading_days/n_days) - 1"""
        if len(nav_series) < 2 or nav_series[0] == 0:
            return 0.0
        n_days = len(nav_series) - 1
        return (nav_series[-1] / nav_series[0]) ** (trading_days / n_days) - 1

    @staticmethod
    def max_drawdown(nav_series: List[float]) -> float:
        """最大回撤（负值）"""
        if len(nav_series) < 2:
            return 0.0
        running_max = nav_series[0]
        max_dd = 0.0
        for nav in nav_series:
            if nav > running_max:
                running_max = nav
            if running_max != 0:
                dd = (nav - running_max) / running_max
                if dd < max_dd:
                    max_dd = dd
        return max_dd

    @staticmethod
    def sharpe_ratio(
        nav_series: List[float],
        risk_free_rate: float = 0.02,
        trading_days: int = 252,
    ) -> float:
        """夏普比率，交易次数为零时返回 0.0"""
        if len(nav_series) < 2:
            return 0.0
        daily_returns = [
            (nav_series[i] / nav_series[i - 1]) - 1
            for i in range(1, len(nav_series))
        ]
        n = len(daily_returns)
        mean_return = sum(daily_returns) / n
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / n
        std_return = math.sqrt(variance)
        if std_return == 0:
            return 0.0
        daily_rf = risk_free_rate / trading_days
        return (mean_return - daily_rf) / std_return * math.sqrt(trading_days)

    @staticmethod
    def win_rate(trades: List[Trade]) -> float:
        """胜率，无交易时返回 0.0。使用 FIFO 配对买卖计算盈亏。"""
        if not trades:
            return 0.0
        pnl_list = Metrics._compute_pnl(trades)
        if not pnl_list:
            return 0.0
        wins = sum(1 for p in pnl_list if p > 0)
        return wins / len(pnl_list)

    @staticmethod
    def profit_loss_ratio(trades: List[Trade]) -> float:
        """盈亏比，无交易时返回 0.0"""
        if not trades:
            return 0.0
        pnl_list = Metrics._compute_pnl(trades)
        if not pnl_list:
            return 0.0
        wins = [p for p in pnl_list if p > 0]
        losses = [p for p in pnl_list if p < 0]
        if not losses:
            return 0.0
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = abs(sum(losses) / len(losses))
        if avg_loss == 0:
            return 0.0
        return avg_win / avg_loss

    @staticmethod
    def _compute_pnl(trades: List[Trade]) -> List[float]:
        """FIFO 配对买卖，返回每笔已平仓交易的盈亏列表。"""
        # buy_queue: symbol -> list of (price, quantity, commission_per_unit)
        buy_queues: dict = defaultdict(list)
        pnl_list: List[float] = []

        for trade in trades:
            if trade.direction == Direction.BUY:
                buy_queues[trade.symbol].append(
                    [trade.price, trade.quantity, trade.commission / trade.quantity if trade.quantity else 0]
                )
            elif trade.direction == Direction.SELL:
                remaining = trade.quantity
                sell_commission_per_unit = trade.commission / trade.quantity if trade.quantity else 0
                queue = buy_queues[trade.symbol]
                while remaining > 0 and queue:
                    buy_price, buy_qty, buy_comm_per_unit = queue[0]
                    matched = min(remaining, buy_qty)
                    pnl = (trade.price - buy_price - buy_comm_per_unit - sell_commission_per_unit) * matched
                    pnl_list.append(pnl)
                    queue[0][1] -= matched
                    remaining -= matched
                    if queue[0][1] <= 0:
                        queue.pop(0)

        return pnl_list
