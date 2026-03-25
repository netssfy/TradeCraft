from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.engine.context import Context
    from app.engine.models import Bar


class Strategy(ABC):
    """策略抽象基类。所有用户策略必须继承此类并实现两个抽象方法。"""

    @abstractmethod
    def initialize(self, context: "Context") -> None:
        """策略初始化，设置参数、订阅数据等。在回测/模拟开始前调用一次。"""

    @abstractmethod
    def on_bar(self, context: "Context", bar: "Bar") -> None:
        """每个 Bar 触发，包含交易逻辑。"""
