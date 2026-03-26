from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.engine.context import Context
    from app.engine.models import Bar


class Strategy(ABC):
    """策略抽象基类。

    Context 使用说明（在所有回调中都可用）：
    1) 读取账户状态：
       - context.portfolio.cash
       - context.portfolio.positions
    2) 读取历史数据（无前视偏差）：
       - context.history("000001", BarInterval.M1, 20)
    3) 提交订单：
       - context.order("000001", 100)   # 市价买入 100
       - context.order("000001", -100)  # 市价卖出 100
    """

    @abstractmethod
    def initialize(self, context: "Context") -> None:
        """策略初始化，回测/模拟开始前调用一次。"""

    @abstractmethod
    def on_bar(self, context: "Context", bar: "Bar") -> None:
        """每个 Bar 触发一次。"""

    def on_market_open(self, context: "Context", bar: "Bar") -> None:
        """当日第一根 Bar 触发，可用于开盘建仓、重置状态等。默认不做任何事。"""

    def on_market_close(self, context: "Context", bar: "Bar") -> None:
        """当日最后一根 Bar 触发，可用于收盘平仓、记录日志等。默认不做任何事。"""
