from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from typing import Dict, List, Tuple


class Market(Enum):
    CN = "CN"  # A股，时区 Asia/Shanghai，交易时段 09:30-11:30, 13:00-15:00
    HK = "HK"  # 港股，时区 Asia/Hong_Kong，交易时段 09:30-12:00, 13:00-16:00
    US = "US"  # 美股，时区 America/New_York，交易时段 09:30-16:00


class BarInterval(Enum):
    M1  = "1m"
    M5  = "5m"
    M15 = "15m"
    M30 = "30m"
    H1  = "60m"
    D1  = "1d"


@dataclass
class MarketInfo:
    timezone: str
    sessions: List[Tuple[time, time]]  # [(开盘, 收盘), ...]
    timestamps_are_local: bool = True  # True: bar 时间戳为本地时间（akshare）；False: UTC（yfinance）


MARKET_INFO: Dict[Market, MarketInfo] = {
    Market.CN: MarketInfo(
        "Asia/Shanghai",
        [(time(9, 30), time(11, 30)), (time(13, 0), time(15, 0))],
        timestamps_are_local=True,   # akshare 返回北京时间
    ),
    Market.HK: MarketInfo(
        "Asia/Hong_Kong",
        [(time(9, 30), time(12, 0)), (time(13, 0), time(16, 0))],
        timestamps_are_local=False,  # yfinance 返回 UTC
    ),
    Market.US: MarketInfo(
        "America/New_York",
        [(time(9, 30), time(16, 0))],
        timestamps_are_local=False,  # yfinance 返回 UTC
    ),
}


def _bar_local_time(market: Market, bar_time: datetime) -> time:
    """将 bar_time 转换为该市场的本地时间，返回 time 部分。"""
    import zoneinfo
    info = MARKET_INFO[market]
    if info.timestamps_are_local:
        # 时间戳本身就是本地时间（被错误标记为 UTC），直接取 naive 部分
        return bar_time.replace(tzinfo=None).time()
    else:
        # 真正的 UTC 时间，需要转换到本地时区
        return bar_time.astimezone(zoneinfo.ZoneInfo(info.timezone)).time()


def is_market_open(market: Market, bar_time: datetime) -> bool:
    """判断 bar_time 是否是该市场当日第一根 bar（开盘时刻）。"""
    info = MARKET_INFO[market]
    return _bar_local_time(market, bar_time) == info.sessions[0][0]


def is_market_close(market: Market, bar_time: datetime) -> bool:
    """判断 bar_time 是否是该市场当日最后一根 bar（收盘时刻）。

    收盘判断使用 15 分钟窗口，兼容 yfinance 等数据源收盘 bar 时间戳略有偏差的情况
    （如港股最后一根 1m bar 为 16:08 而非 16:00）。
    """
    info = MARKET_INFO[market]
    close_time = info.sessions[-1][1]
    local_t = _bar_local_time(market, bar_time)
    close_h, close_m = close_time.hour, close_time.minute
    window_end = time((close_h * 60 + close_m + 15) // 60, (close_m + 15) % 60)
    return close_time <= local_t < window_end
