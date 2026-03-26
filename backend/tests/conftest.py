"""
公共测试 fixtures 占位。
后续各模块测试可在此添加共享 fixture。
"""
import pytest


@pytest.fixture
def sample_config_yaml(tmp_path):
    """生成一个最小合法配置文件，供测试使用。"""
    config_content = """
mode: backtest
bar_interval: 1m
backtest:
  start_date: "2023-01-01"
  end_date: "2023-12-31"
data_sources:
  CN: akshare
  HK: yfinance
  US: yfinance
traders:
  - id: trader_test
    market: CN
    initial_cash: 100000.0
    allowed_symbols:
      - "000001.SZ"
    strategy_path: "strategies/test_strategy.py"
    strategy_params: {}
    order_timeout_seconds: 300
    commission_rate: 0.0003
logging:
  level: INFO
  file: "data/logs/test.log"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)
    return str(config_file)
