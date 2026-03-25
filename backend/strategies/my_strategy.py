from app.trading.strategy import Strategy


class MyStrategy(Strategy):
    def initialize(self, context):
        # 可在初始化阶段读取账户信息
        # cash = context.portfolio.cash
        # positions = context.portfolio.positions
        self.fast = self.fast_period if hasattr(self, "fast_period") else 5

    def on_bar(self, context, bar):
        # 1) 获取历史数据（只返回当前 bar 之前的数据，避免前视偏差）
        # from app.data.market import BarInterval
        # bars = context.history(bar.symbol, BarInterval.M1, 20)

        # 2) 根据条件下单
        # context.order(bar.symbol, 100)   # 买入 100
        # context.order(bar.symbol, -100)  # 卖出 100

        # 3) 读取当前资金/持仓
        # cash = context.portfolio.cash
        # pos = context.portfolio.positions.get(bar.symbol)
        pass
