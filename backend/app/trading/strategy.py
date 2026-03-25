from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.engine.context import Context
    from app.engine.models import Bar


class Strategy(ABC):
    """策略抽象基类。

    Context 使用说明（在 initialize/on_bar 中都可用）：
    1) 读取账户状态：
       - context.portfolio.cash
       - context.portfolio.positions
    2) 读取历史数据（无前视偏差）：
       - context.history("000001.SZ", BarInterval.M1, 20)
       只会返回当前 bar 时间之前的数据，不包含当前 bar。
    3) 提交订单：
       - context.order("000001.SZ", 100)  # 市价买入 100
       - context.order("000001.SZ", -100) # 市价卖出 100（负数表示卖出）
       - context.order("000001.SZ", 100, order_type=OrderType.LIMIT, limit_price=10.5)
    """

    @abstractmethod
    def initialize(self, context: "Context") -> None:
        """策略初始化：设置参数、预加载状态等。回测/模拟开始前调用一次。"""

    @abstractmethod
    def on_bar(self, context: "Context", bar: "Bar") -> None:
        """每个 Bar 触发一次，在这里实现交易逻辑。"""
