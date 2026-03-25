from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar, Dict, List

from app.data.market import BarInterval, Market
from app.engine.models import Bar


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class DataFeedError(Exception):
    """数据源拉取失败时抛出，包含数据源名称和原因。"""

    def __init__(self, feed_name: str, reason: str) -> None:
        self.feed_name = feed_name
        self.reason = reason
        super().__init__(f"[{feed_name}] {reason}")


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class DataFeed(ABC):
    supported_markets: ClassVar[List[Market]]
    max_lookback_days: ClassVar[Dict[BarInterval, int]]

    @abstractmethod
    def fetch(
        self,
        symbol: str,
        market: Market,
        interval: BarInterval,
        start: datetime,
        end: datetime,
    ) -> List[Bar]:
        """拉取指定范围的 K 线数据，失败时抛出 DataFeedError。"""


# ---------------------------------------------------------------------------
# AkshareDataFeed — CN market
# ---------------------------------------------------------------------------

class AkshareDataFeed(DataFeed):
    supported_markets: ClassVar[List[Market]] = [Market.CN]
    max_lookback_days: ClassVar[Dict[BarInterval, int]] = {
        BarInterval.M1:  5,
        BarInterval.M5:  60,
        BarInterval.M15: 60,
        BarInterval.M30: 60,
        BarInterval.H1:  365,
        BarInterval.D1:  3650,
    }

    # akshare period strings for each interval
    _PERIOD_MAP: ClassVar[Dict[BarInterval, str]] = {
        BarInterval.M1:  "1",
        BarInterval.M5:  "5",
        BarInterval.M15: "15",
        BarInterval.M30: "30",
        BarInterval.H1:  "60",
        BarInterval.D1:  "daily",
    }

    def fetch(
        self,
        symbol: str,
        market: Market,
        interval: BarInterval,
        start: datetime,
        end: datetime,
    ) -> List[Bar]:
        try:
            import akshare as ak  # type: ignore
        except ImportError as exc:
            raise DataFeedError("AkshareDataFeed", "akshare 未安装") from exc

        period = self._PERIOD_MAP[interval]
        start_str = start.strftime("%Y%m%d%H%M%S")
        end_str = end.strftime("%Y%m%d%H%M%S")

        try:
            if interval == BarInterval.D1:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start.strftime("%Y%m%d"),
                    end_date=end.strftime("%Y%m%d"),
                    adjust="",
                )
            else:
                df = ak.stock_zh_a_hist_min_em(
                    symbol=symbol,
                    period=period,
                    start_date=start_str,
                    end_date=end_str,
                    adjust="",
                )
        except Exception as exc:
            raise DataFeedError("AkshareDataFeed", str(exc)) from exc

        if df is None or df.empty:
            return []

        bars: List[Bar] = []
        try:
            if interval == BarInterval.D1:
                for _, row in df.iterrows():
                    ts = datetime.strptime(str(row["日期"]), "%Y-%m-%d")
                    bars.append(Bar(
                        symbol=symbol,
                        market=market,
                        interval=interval,
                        timestamp=ts,
                        open=float(row["开盘"]),
                        high=float(row["最高"]),
                        low=float(row["最低"]),
                        close=float(row["收盘"]),
                        volume=float(row["成交量"]),
                    ))
            else:
                for _, row in df.iterrows():
                    ts = datetime.strptime(str(row["时间"]), "%Y-%m-%d %H:%M:%S")
                    bars.append(Bar(
                        symbol=symbol,
                        market=market,
                        interval=interval,
                        timestamp=ts,
                        open=float(row["开盘"]),
                        high=float(row["最高"]),
                        low=float(row["最低"]),
                        close=float(row["收盘"]),
                        volume=float(row["成交量"]),
                    ))
        except Exception as exc:
            raise DataFeedError("AkshareDataFeed", f"数据解析失败: {exc}") from exc

        return bars


# ---------------------------------------------------------------------------
# YfinanceDataFeed — HK / US markets
# ---------------------------------------------------------------------------

class YfinanceDataFeed(DataFeed):
    supported_markets: ClassVar[List[Market]] = [Market.HK, Market.US]
    max_lookback_days: ClassVar[Dict[BarInterval, int]] = {
        BarInterval.M1:  7,
        BarInterval.M5:  60,
        BarInterval.M15: 60,
        BarInterval.M30: 60,
        BarInterval.H1:  730,
        BarInterval.D1:  3650,
    }

    # yfinance interval strings for each BarInterval
    _INTERVAL_MAP: ClassVar[Dict[BarInterval, str]] = {
        BarInterval.M1:  "1m",
        BarInterval.M5:  "5m",
        BarInterval.M15: "15m",
        BarInterval.M30: "30m",
        BarInterval.H1:  "60m",
        BarInterval.D1:  "1d",
    }

    def fetch(
        self,
        symbol: str,
        market: Market,
        interval: BarInterval,
        start: datetime,
        end: datetime,
    ) -> List[Bar]:
        try:
            import yfinance as yf  # type: ignore
        except ImportError as exc:
            raise DataFeedError("YfinanceDataFeed", "yfinance 未安装") from exc

        yf_interval = self._INTERVAL_MAP[interval]

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                interval=yf_interval,
                start=start,
                end=end,
                auto_adjust=True,
            )
        except Exception as exc:
            raise DataFeedError("YfinanceDataFeed", str(exc)) from exc

        if df is None or df.empty:
            return []

        bars: List[Bar] = []
        try:
            for ts, row in df.iterrows():
                # yfinance returns timezone-aware timestamps; convert to naive UTC
                if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
                    ts = ts.utctimetuple()
                    ts = datetime(*ts[:6])
                else:
                    ts = ts.to_pydatetime().replace(tzinfo=None)
                bars.append(Bar(
                    symbol=symbol,
                    market=market,
                    interval=interval,
                    timestamp=ts,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]),
                ))
        except Exception as exc:
            raise DataFeedError("YfinanceDataFeed", f"数据解析失败: {exc}") from exc

        return bars


# ---------------------------------------------------------------------------
# BaostockDataFeed — CN market
# ---------------------------------------------------------------------------

class BaostockDataFeed(DataFeed):
    supported_markets: ClassVar[List[Market]] = [Market.CN]
    max_lookback_days: ClassVar[Dict[BarInterval, int]] = {
        BarInterval.M1:  5,
        BarInterval.M5:  60,
        BarInterval.M15: 60,
        BarInterval.M30: 60,
        BarInterval.H1:  365,
        BarInterval.D1:  3650,
    }

    # baostock frequency strings for each BarInterval
    _FREQ_MAP: ClassVar[Dict[BarInterval, str]] = {
        BarInterval.M1:  "1",
        BarInterval.M5:  "5",
        BarInterval.M15: "15",
        BarInterval.M30: "30",
        BarInterval.H1:  "60",
        BarInterval.D1:  "d",
    }

    def fetch(
        self,
        symbol: str,
        market: Market,
        interval: BarInterval,
        start: datetime,
        end: datetime,
    ) -> List[Bar]:
        try:
            import baostock as bs  # type: ignore
        except ImportError as exc:
            raise DataFeedError("BaostockDataFeed", "baostock 未安装") from exc

        frequency = self._FREQ_MAP[interval]
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        try:
            lg = bs.login()
            if lg.error_code != "0":
                raise DataFeedError("BaostockDataFeed", f"登录失败: {lg.error_msg}")

            if interval == BarInterval.D1:
                rs = bs.query_history_k_data_plus(
                    symbol,
                    "date,open,high,low,close,volume",
                    start_date=start_str,
                    end_date=end_str,
                    frequency=frequency,
                    adjustflag="3",
                )
            else:
                rs = bs.query_history_k_data_plus(
                    symbol,
                    "date,time,open,high,low,close,volume",
                    start_date=start_str,
                    end_date=end_str,
                    frequency=frequency,
                    adjustflag="3",
                )

            if rs.error_code != "0":
                bs.logout()
                raise DataFeedError("BaostockDataFeed", f"查询失败: {rs.error_msg}")

            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())

            bs.logout()
        except DataFeedError:
            raise
        except Exception as exc:
            try:
                bs.logout()
            except Exception:
                pass
            raise DataFeedError("BaostockDataFeed", str(exc)) from exc

        bars: List[Bar] = []
        try:
            for row in data_list:
                if interval == BarInterval.D1:
                    date_str, open_, high, low, close, volume = row
                    ts = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    date_str, time_str, open_, high, low, close, volume = row
                    # baostock time format: "20240101093000000"
                    dt_str = date_str + " " + time_str[:6]
                    ts = datetime.strptime(dt_str, "%Y-%m-%d %H%M%S")

                if not open_ or not close:
                    continue

                bars.append(Bar(
                    symbol=symbol,
                    market=market,
                    interval=interval,
                    timestamp=ts,
                    open=float(open_),
                    high=float(high),
                    low=float(low),
                    close=float(close),
                    volume=float(volume),
                ))
        except Exception as exc:
            raise DataFeedError("BaostockDataFeed", f"数据解析失败: {exc}") from exc

        return bars
