from app.trading.strategy import Strategy

class MyStrategy(Strategy):
    def initialize(self, context):
        self.fast = self.fast_period if hasattr(self, 'fast_period') else 5

    def on_bar(self, context, bar):
        # 你的交易逻辑
        pass
