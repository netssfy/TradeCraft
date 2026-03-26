from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.engine.events import EventBus, EventType
from app.engine.models import Fill, Order, OrderStatus

logger = logging.getLogger(__name__)


class OrderManager:
    def __init__(
        self,
        trader_id: str,
        allowed_symbols: Optional[List[str]],
        event_bus: EventBus,
    ) -> None:
        self.trader_id = trader_id
        self.allowed_symbols = allowed_symbols
        self._event_bus = event_bus
        self._orders: Dict[str, Order] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, order: Order) -> Order:
        """校验 Symbol 权限，分配唯一 ID，状态设为 SUBMITTED。
        若 Symbol 不在 allowed_symbols 内，将订单状态设为 CANCELLED 并记录原因。
        """
        # Assign a fresh UUID regardless of what the caller set
        order.id = str(uuid.uuid4())

        if self.allowed_symbols is not None and order.symbol not in self.allowed_symbols:
            order.status = OrderStatus.CANCELLED
            reason = (
                f"Symbol '{order.symbol}' is not in allowed_symbols for trader '{self.trader_id}'"
            )
            logger.warning("Order rejected: %s", reason)
            self._orders[order.id] = order
            self._publish_status_change(order)
            return order

        order.status = OrderStatus.SUBMITTED
        self._orders[order.id] = order
        self._publish_status_change(order)
        logger.debug("Order submitted: id=%s symbol=%s", order.id, order.symbol)
        return order

    def cancel(self, order_id: str) -> bool:
        """手动撤销未完全成交的订单。返回 True 表示撤销成功，False 表示订单不存在或已终结。"""
        order = self._orders.get(order_id)
        if order is None:
            logger.warning("cancel: order '%s' not found", order_id)
            return False

        if order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            logger.warning(
                "cancel: order '%s' is already in terminal state %s", order_id, order.status
            )
            return False

        order.status = OrderStatus.CANCELLED
        self._publish_status_change(order)
        logger.debug("Order cancelled: id=%s", order_id)
        return True

    def process_fill(self, fill: Fill) -> None:
        """更新订单状态（PARTIAL 或 FILLED），并通过 EventBus 发布状态变更事件。"""
        order = self._orders.get(fill.order_id)
        if order is None:
            logger.warning("process_fill: order '%s' not found", fill.order_id)
            return

        if fill.quantity < order.quantity:
            order.status = OrderStatus.PARTIAL
        else:
            order.status = OrderStatus.FILLED

        self._publish_status_change(order)
        logger.debug(
            "Fill processed: order_id=%s fill_qty=%s order_qty=%s new_status=%s",
            fill.order_id,
            fill.quantity,
            order.quantity,
            order.status,
        )

    def cancel_expired(self, current_time: datetime) -> List[Order]:
        """撤销所有超时未成交的订单，返回被撤销的订单列表。"""
        cancelled: List[Order] = []
        for order in list(self._orders.values()):
            if order.status not in (OrderStatus.SUBMITTED, OrderStatus.PARTIAL):
                continue
            if order.timeout_seconds is None:
                continue
            elapsed = (current_time - order.created_at).total_seconds()
            if elapsed >= order.timeout_seconds:
                order.status = OrderStatus.CANCELLED
                self._publish_status_change(order)
                cancelled.append(order)
                logger.debug(
                    "Order expired and cancelled: id=%s elapsed=%.1fs timeout=%ds",
                    order.id,
                    elapsed,
                    order.timeout_seconds,
                )
        return cancelled

    def get_open_orders(self) -> List[Order]:
        """返回所有未完成订单（状态为 SUBMITTED 或 PARTIAL）。"""
        return [
            o for o in self._orders.values()
            if o.status in (OrderStatus.SUBMITTED, OrderStatus.PARTIAL)
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _publish_status_change(self, order: Order) -> None:
        self._event_bus.publish(EventType.ORDER_STATUS_CHANGED, order)
