from __future__ import annotations

from datetime import datetime

from app.engine.models import Bar, Direction, Fill, Order, OrderType


class Simulator:
    def __init__(self, commission_rate: float = 0.0003):
        self.commission_rate = commission_rate

    def match(self, order: Order, bar: Bar) -> Fill | None:
        """
        撮合规则：
        - 市价单：以 bar.close 成交
        - 限价买单：bar.high >= limit_price → 以 limit_price 成交
        - 限价卖单：bar.low <= limit_price → 以 limit_price 成交
        - 不考虑流动性，价格触及即全部成交
        """
        if order.order_type == OrderType.MARKET:
            fill_price = bar.close
        elif order.order_type == OrderType.LIMIT:
            if order.limit_price is None:
                return None
            if order.direction == Direction.BUY:
                if bar.high >= order.limit_price:
                    fill_price = order.limit_price
                else:
                    return None
            else:  # SELL
                if bar.low <= order.limit_price:
                    fill_price = order.limit_price
                else:
                    return None
        else:
            return None

        commission = fill_price * order.quantity * self.commission_rate

        return Fill(
            order_id=order.id,
            symbol=order.symbol,
            market=order.market,
            direction=order.direction,
            quantity=order.quantity,
            price=fill_price,
            commission=commission,
            timestamp=bar.timestamp,
        )
