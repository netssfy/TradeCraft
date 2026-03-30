"""
配置管理模块。

支持 YAML 格式配置文件，环境变量覆盖（前缀 TRADECRAFT_），
优先级：环境变量 > 用户配置 > 默认配置。
缺少必填字段时抛出 ConfigError。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml


class ConfigError(Exception):
    """配置错误：缺少必填字段或字段值非法时抛出。"""


# ---------------------------------------------------------------------------
# 子配置数据类
# ---------------------------------------------------------------------------

@dataclass
class BacktestConfig:
    start_date: str = "2023-01-01"
    end_date: str = "2023-12-31"


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "data/logs/tradecraft.log"


@dataclass
class TraderConfig:
    id: str = ""
    market: str = "CN"
    initial_cash: float = 1000000.0
    allowed_symbols: Optional[List[str]] = None
    strategy_path: str = ""
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    order_timeout_seconds: int = 300
    commission_rate: float = 0.0003


# ---------------------------------------------------------------------------
# 顶层配置数据类
# ---------------------------------------------------------------------------

@dataclass
class Config:
    mode: str = "backtest"
    bar_interval: str = "1m"
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    data_sources: Dict[str, str] = field(
        default_factory=lambda: {"CN": "akshare", "HK": "yfinance", "US": "yfinance"}
    )
    traders: List[TraderConfig] = field(default_factory=list)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


# ---------------------------------------------------------------------------
# 必填字段定义
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = ["mode", "bar_interval"]


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

def _deep_merge(base: Dict, override: Dict) -> Dict:
    """递归合并两个字典，override 中的值覆盖 base 中的值。"""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env_overrides(data: Dict) -> Dict:
    """
    将前缀为 TRADECRAFT_ 的环境变量应用到配置字典。

    规则：
    - TRADECRAFT_MODE          → data["mode"]
    - TRADECRAFT_BAR_INTERVAL  → data["bar_interval"]
    - TRADECRAFT_LOGGING_LEVEL → data["logging"]["level"]
    - TRADECRAFT_TRADERS_0_INITIAL_CASH → data["traders"][0]["initial_cash"]
    """
    prefix = "TRADECRAFT_"
    result = dict(data)

    for env_key, env_val in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        # 去掉前缀，转小写，按 _ 分割
        parts = env_key[len(prefix):].lower().split("_")
        _set_nested(result, parts, env_val)

    return result


def _set_nested(data: Any, parts: List[str], value: str) -> None:
    """按路径 parts 将 value 写入嵌套字典/列表结构。"""
    if not parts:
        return

    key = parts[0]

    # 尝试将 key 解析为列表索引
    if isinstance(data, list):
        try:
            idx = int(key)
            if idx < len(data):
                if len(parts) == 1:
                    data[idx] = _coerce(value)
                else:
                    _set_nested(data[idx], parts[1:], value)
        except (ValueError, IndexError):
            pass
        return

    if not isinstance(data, dict):
        return

    if len(parts) == 1:
        data[key] = _coerce(value)
        return

    # 尝试匹配多词 key（如 bar_interval 对应 parts ["bar", "interval"]）
    # 先尝试直接匹配 key
    if key in data:
        _set_nested(data[key], parts[1:], value)
    else:
        # 尝试将 parts[0] + "_" + parts[1] 合并为 key
        for length in range(len(parts), 0, -1):
            candidate = "_".join(parts[:length])
            if candidate in data:
                if length == len(parts):
                    data[candidate] = _coerce(value)
                else:
                    _set_nested(data[candidate], parts[length:], value)
                return


def _coerce(value: str) -> Any:
    """将字符串环境变量值转换为合适的 Python 类型。"""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _dict_to_config(data: Dict) -> Config:
    """将原始字典转换为 Config 数据类实例。"""
    backtest_raw = data.get("backtest", {})
    backtest = BacktestConfig(
        start_date=backtest_raw.get("start_date", "2023-01-01"),
        end_date=backtest_raw.get("end_date", "2023-12-31"),
    )

    logging_raw = data.get("logging", {})
    logging_cfg = LoggingConfig(
        level=logging_raw.get("level", "INFO"),
        file=logging_raw.get("file", "data/logs/tradecraft.log"),
    )

    traders_raw = data.get("traders", [])
    traders = []
    for t in traders_raw:
        traders.append(
            TraderConfig(
                id=t.get("id", ""),
                market=t.get("market", "CN"),
                initial_cash=float(t.get("initial_cash", 1000000.0)),
                allowed_symbols=t.get("allowed_symbols", None),
                strategy_path=t.get("strategy_path", ""),
                strategy_params=t.get("strategy_params", {}),
                order_timeout_seconds=int(t.get("order_timeout_seconds", 300)),
                commission_rate=float(t.get("commission_rate", 0.0003)),
            )
        )

    return Config(
        mode=data.get("mode", "backtest"),
        bar_interval=data.get("bar_interval", "1m"),
        backtest=backtest,
        data_sources=data.get(
            "data_sources", {"CN": "akshare", "HK": "yfinance", "US": "yfinance"}
        ),
        traders=traders,
        logging=logging_cfg,
    )


def _validate(data: Dict) -> None:
    """检查必填字段，缺失时抛出 ConfigError 并列出所有缺失字段。"""
    missing = [f for f in _REQUIRED_FIELDS if not data.get(f)]
    if missing:
        raise ConfigError(
            f"配置文件缺少必填字段：{', '.join(missing)}"
        )


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG: Dict = {
    "mode": "backtest",
    "bar_interval": "1m",
    "backtest": {
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
    },
    "data_sources": {
        "CN": "akshare",
        "HK": "yfinance",
        "US": "yfinance",
    },
    "traders": [],
    "logging": {
        "level": "INFO",
        "file": "data/logs/tradecraft.log",
    },
}


def load_config(config_path: Optional[str] = None) -> Config:
    """
    加载配置，优先级：环境变量 > 用户配置文件 > 默认配置。

    Args:
        config_path: YAML 配置文件路径，为 None 时仅使用默认配置和环境变量。

    Returns:
        Config 实例。

    Raises:
        ConfigError: 缺少必填字段时抛出。
    """
    merged: Dict = dict(_DEFAULT_CONFIG)

    if config_path is not None:
        with open(config_path, "r", encoding="utf-8") as f:
            user_data = yaml.safe_load(f) or {}
        merged = _deep_merge(merged, user_data)

    merged = _apply_env_overrides(merged)

    _validate(merged)

    return _dict_to_config(merged)
