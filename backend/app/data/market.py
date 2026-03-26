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


MARKET_INFO: Dict[Market, MarketInfo] = {
    Market.CN: MarketInfo(
        "Asia/Shanghai",
        [(time(9, 30), time(11, 30)), (time(13, 0), time(15, 0))],
    ),
    Market.HK: MarketInfo(
        "Asia/Hong_Kong",
        [(time(9, 30), time(12, 0)), (time(13, 0), time(16, 0))],
    ),
    Market.US: MarketInfo(
        "America/New_York",
        [(time(9, 30), time(16, 0))],
    ),
}


def is_market_open(market: Market, bar_time: datetime) -> bool:
    """判断 bar_time 是否是该市场当日第一根 bar（开盘时刻）。"""
    import zoneinfo
    info = MARKET_INFO[market]
    local_dt = bar_time.astimezone(zoneinfo.ZoneInfo(info.timezone))
    return local_dt.time() == info.sessions[0][0]


def is_market_close(market: Market, bar_time: datetime) -> bool:
    """判断 bar_time 是否是该市场当日最后一根 bar（收盘时刻）。"""
    import zoneinfo
    info = MARKET_INFO[market]
    local_dt = bar_time.astimezone(zoneinfo.ZoneInfo(info.timezone))
    return local_dt.time() == info.sessions[-1][1]
