from __future__ import annotations

from collections import defaultdict
from enum import Enum
from typing import Any, Callable, Dict, List


class EventType(Enum):
    ORDER_STATUS_CHANGED = "order_status_changed"
    FILL_EXECUTED        = "fill_executed"
    BAR_COMPLETED        = "bar_completed"
    ENGINE_STOPPED       = "engine_stopped"


class EventBus:
    def __init__(self) -> None:
        self._handlers: Dict[EventType, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Register a handler for the given event type."""
        self._handlers[event_type].append(handler)

    def publish(self, event_type: EventType, payload: Any) -> None:
        """Invoke all handlers registered for the given event type."""
        for handler in self._handlers[event_type]:
            handler(payload)
