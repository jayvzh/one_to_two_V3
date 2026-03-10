"""AkShare data source and repositories (data layer).

This module contains:
- AkshareDataSource: Fetch raw stock data from AkShare API
- ZtRepository: Limit-up pool data access
- IndexRepository: Index data access

Design Principles:
- All I/O operations in one place
- Retry mechanism for network requests
- Lazy load akshare module for offline testing support
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd

from ..utils.logging_config import get_logger

from .columns import normalize_index_columns, normalize_zt_pool_columns
from .trade_calendar import TradingCalendar

logger = get_logger(__name__)


class DataSourceError(Exception):
    """Raised when data source fails."""
    pass


class AkshareDataSource:
    """AkShare data source implementation.
    
    Only responsible for "how to get data", not caching or business logic.
    Lazy loads akshare module for offline testing support.
    """

    def __init__(self, max_retries: int = 3, retry_sleep: float = 1.0):
        """Initialize data source.
        
        Args:
            max_retries: Maximum number of retries for network requests
            retry_sleep: Sleep time between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_sleep = retry_sleep

    def _retry(self, func, *args, **kwargs) -> pd.DataFrame:
        """Execute function with retry mechanism."""
        import socket
        import urllib.error

        last_err: Exception | None = None
        for i in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except (TimeoutError, socket.gaierror, urllib.error.URLError, ConnectionError) as e:
                last_err = e
                logger.warning(f"网络请求失败 (尝试 {i + 1}/{self.max_retries}): {type(e).__name__}: {e}")
                time.sleep(self.retry_sleep)
            except Exception as e:
                last_err = e
                time.sleep(self.retry_sleep)

        raise DataSourceError(
            f"数据获取失败（网络错误或API限制）: {last_err}\n"
            f"提示：请检查网络连接，或使用本地缓存数据。"
        ) from last_err

    @staticmethod
    def _load_akshare() -> Any:
        """Lazy load akshare module."""
        try:
            import akshare as ak  # type: ignore
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "未安装 akshare，无法执行在线数据拉取。"
                "若仅运行离线测试，可忽略；若需在线功能，请先安装项目依赖。"
            ) from exc
        return ak

    def get_zt_pool(self, date: str) -> pd.DataFrame:
        """Get limit-up pool data for a specific date.
        
        Args:
            date: Date string (YYYYMMDD)
            
        Returns:
            DataFrame with limit-up pool data
        """
        ak = self._load_akshare()
        return self._retry(ak.stock_zt_pool_em, date=date)

    def get_index_daily(
        self,
        symbol: str,
        start: str,
        end: str,
    ) -> pd.DataFrame:
        """Get index daily data with fallback strategies.
        
        Priority:
        1. stock_zh_index_daily (dedicated index API)
        2. index_zh_a_hist (supports date range)
        3. stock_zh_a_hist (compatible fallback)
        
        Args:
            symbol: Index symbol (e.g., "000300")
            start: Start date (YYYYMMDD)
            end: End date (YYYYMMDD)
            
        Returns:
            DataFrame with index daily data
        """
        ak = self._load_akshare()
        symbol = self._normalize_index_symbol(symbol)

        try:
            df = self._retry(ak.stock_zh_index_daily, symbol=symbol)
            if not df.empty:
                return self._filter_by_date(df, start, end)
        except Exception:
            pass

        try:
            df = self._retry(
                ak.index_zh_a_hist,
                symbol=symbol,
                period="daily",
                start_date=start,
                end_date=end
            )
            if not df.empty:
                return df
        except Exception:
            pass

        return self._retry(
            ak.stock_zh_a_hist,
            symbol=symbol,
            period="daily",
            start_date=start,
            end_date=end,
            adjust="qfq",
        )

    @staticmethod
    def _normalize_index_symbol(symbol: str) -> str:
        """Normalize index symbol format."""
        if symbol.startswith(("sh", "sz")):
            return symbol
        return f"sh{symbol}"

    @staticmethod
    def _filter_by_date(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
        """Filter DataFrame by date range."""
        df = df.copy()
        date_col = "日期" if "日期" in df.columns else "date"
        df["_date_temp"] = pd.to_datetime(df[date_col], errors="coerce")

        start_dt = pd.to_datetime(start, format="%Y%m%d", errors="coerce")
        end_dt = pd.to_datetime(end, format="%Y%m%d", errors="coerce")

        mask = (df["_date_temp"] >= start_dt) & (df["_date_temp"] <= end_dt)
        filtered = df[mask].copy()

        if "_date_temp" in filtered.columns:
            filtered = filtered.drop(columns=["_date_temp"])

        return filtered


class ZtRepository:
    """Limit-up pool data repository.
    
    Unified data access with pluggable cache strategy.
    """

    def __init__(
        self,
        data_source: AkshareDataSource,
        cache_dir: Path,
        cache_mode: str = "read_write",  # off | read | read_write
        calendar: "TradingCalendar | None" = None,
    ):
        """Initialize repository.
        
        Args:
            data_source: AkshareDataSource instance
            cache_dir: Directory for cache files
            cache_mode: Cache mode (off | read | read_write)
            calendar: TradingCalendar instance for intraday detection
        """
        self.data_source = data_source
        self.cache_dir = cache_dir
        self.cache_mode = cache_mode
        self.calendar = calendar

    def _cache_path(self, date: str) -> Path:
        """Get cache file path for a date."""
        return self.cache_dir / f"zt_{date}.csv"

    def _intraday_cache_path(self, date: str) -> Path:
        """Get intraday cache file path for a date."""
        return self.cache_dir / f"zt_{date}_intraday.csv"

    def _is_intraday(self, date: str) -> bool:
        """Check if current time is before market close (16:00) and date is a trade day.
        
        Args:
            date: Date string (YYYYMMDD)
            
        Returns:
            True if current time is before 16:00 and date is a trade day, False otherwise
        """
        from datetime import datetime
        now = datetime.now()
        today = now.strftime("%Y%m%d")
        
        if date != today:
            return False
        
        if self.calendar and not self.calendar.is_trade_day(date):
            return False
        
        return now.hour < 16

    def get_by_date(self, date: str, refresh: bool = False) -> tuple[pd.DataFrame, bool]:
        """Get limit-up pool data for a specific date.
        
        Args:
            date: Date string (YYYYMMDD)
            refresh: Force refresh from data source
            
        Returns:
            Tuple of (DataFrame with limit-up pool data, is_intraday flag)
        """
        from datetime import datetime
        cache_path = self._cache_path(date)
        intraday_cache_path = self._intraday_cache_path(date)

        if self.cache_mode in ("read", "read_write") and not refresh:
            if cache_path.exists():
                try:
                    return self._validate_df(self._read_cache(cache_path, date=date)), False
                except ValueError:
                    if self.cache_mode == "read":
                        raise

        if self.cache_mode == "read":
            raise RuntimeError(
                f"缓存未命中且 cache_mode=read: {date}\n"
                f"提示：当前为离线模式，请确保本地缓存存在，或切换到 read_write 模式。"
            )

        try:
            df = self.data_source.get_zt_pool(date)
        except DataSourceError:
            if cache_path.exists():
                print(f"[WARN] 网络请求失败，使用本地缓存: {cache_path}")
                return self._validate_df(self._read_cache(cache_path, date=date)), False
            if intraday_cache_path.exists():
                print(f"[WARN] 网络请求失败，使用本地缓存: {intraday_cache_path}")
                is_intraday_cache = self._is_intraday(date)
                return self._validate_df(self._read_cache(intraday_cache_path, date=date)), is_intraday_cache
            raise

        df = self._validate_df(df)

        is_intraday = self._is_intraday(date)

        if self.cache_mode == "read_write" and not df.empty:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            df_normalized = normalize_zt_pool_columns(df, date=date)
            if is_intraday:
                df_normalized.to_csv(intraday_cache_path, index=False)
            else:
                df_normalized.to_csv(cache_path, index=False)

        return df, is_intraday

    @staticmethod
    def _read_cache(cache_path: Path, date: str) -> pd.DataFrame:
        """Read cache with encoding fallback."""
        try:
            df = pd.read_csv(cache_path, dtype={"代码": str, "symbol": str})
        except UnicodeDecodeError:
            df = pd.read_csv(cache_path, dtype={"代码": str, "symbol": str}, encoding="gbk")

        return normalize_zt_pool_columns(df, date=date)

    @staticmethod
    def _validate_df(df: pd.DataFrame) -> pd.DataFrame:
        """Validate DataFrame structure and data quality."""
        if df.empty:
            logger.warning("涨停池数据为空，当日可能暂无涨停股票")
            return pd.DataFrame(columns=["symbol", "name", "board_count", "date"])

        df = normalize_zt_pool_columns(df)
        required_columns = ["symbol", "board_count"]
        missing_cols = [c for c in required_columns if c not in df.columns]
        if missing_cols:
            raise ValueError(f"涨停池数据缺少列: {missing_cols}")

        if df[required_columns].isna().any().any():
            raise ValueError("涨停池关键列存在空值")

        df = df.copy()
        df["symbol"] = df["symbol"].astype(str).str.zfill(6)
        if df.duplicated(subset=["symbol"], keep=False).any():
            raise ValueError("涨停池存在重复代码")

        df["board_count"] = pd.to_numeric(df["board_count"], errors="coerce")
        if df["board_count"].isna().any():
            raise ValueError("涨停池连板数存在非法值")
        df["board_count"] = df["board_count"].astype(int)

        return df


class IndexRepository:
    """Index data repository.
    
    Fetches and caches index daily data.
    Coordinates with TradingCalendar for trade day validation.
    """

    def __init__(
        self,
        data_source: AkshareDataSource,
        cache_dir: Path,
        calendar: TradingCalendar,
        cache_mode: str = "read_write",  # off | read | read_write
        default_symbol: str = "000300",  # CSI 300
    ):
        """Initialize repository.
        
        Args:
            data_source: AkshareDataSource instance
            cache_dir: Directory for cache files
            calendar: TradingCalendar instance
            cache_mode: Cache mode (off | read | read_write)
            default_symbol: Default index symbol
        """
        self.data_source = data_source
        self.cache_dir = cache_dir
        self.cache_mode = cache_mode
        self.calendar = calendar
        self.default_symbol = default_symbol

    def _cache_path(self, symbol: str) -> Path:
        """Get cache file path for a symbol."""
        return self.cache_dir / f"{symbol}_full.csv"

    def _normalize_df_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize date column to YYYYMMDD for filtering."""
        df = normalize_index_columns(df)
        df = df.copy()
        if "_date_norm" not in df.columns:
            df["_date_norm"] = df["date"].astype(str).str.replace("-", "")
        return df

    @staticmethod
    def _validate_df(df: pd.DataFrame) -> pd.DataFrame:
        """Validate DataFrame structure and data quality."""
        if df.empty:
            raise ValueError("指数数据为空，请检查日期范围或数据源")

        df = normalize_index_columns(df)
        required_columns = ["date", "close"]
        missing_cols = [c for c in required_columns if c not in df.columns]
        if missing_cols:
            raise ValueError(f"指数数据缺少列: {missing_cols}")

        if df[required_columns].isna().any().any():
            raise ValueError("指数数据关键列存在空值")

        if df.duplicated(subset=["date"], keep=False).any():
            raise ValueError("指数数据存在重复日期")

        date_series = pd.to_datetime(df["date"], errors="coerce")
        if date_series.isna().any():
            raise ValueError("指数数据日期格式非法")

        if not date_series.is_monotonic_increasing:
            raise ValueError("指数数据未按日期升序排列")

        return df

    def get_daily(
        self,
        start: str,
        end: str,
        symbol: str | None = None,
        refresh: bool = False,
        allow_partial: bool = False,
    ) -> pd.DataFrame:
        """Get index daily data for a date range.
        
        Args:
            start: Start date (YYYYMMDD)
            end: End date (YYYYMMDD)
            symbol: Index symbol (optional, uses default if not provided)
            refresh: Force refresh from data source
            allow_partial: Allow returning partial data (less than 2 rows)
            
        Returns:
            DataFrame with index daily data
        """
        symbol = symbol or self.default_symbol

        start = self.calendar.normalize_date(start)
        end = self.calendar.normalize_date(end)

        if not self.calendar.is_trade_day(start):
            start = self.calendar.prev_trade_day(start)
        if not self.calendar.is_trade_day(end):
            end = self.calendar.prev_trade_day(end)

        cache_path = self._cache_path(symbol)

        if self.cache_mode in ("read", "read_write") and not refresh:
            if cache_path.exists():
                try:
                    df = pd.read_csv(cache_path)
                except UnicodeDecodeError:
                    df = pd.read_csv(cache_path, encoding="gbk")
                df = self._validate_df(df)
                df = self._normalize_df_date(df)
                mask = (df["_date_norm"] >= start) & (df["_date_norm"] <= end)
                sliced = df.loc[mask]
                if len(sliced) >= 2:
                    return sliced

        if self.cache_mode == "read":
            raise RuntimeError(
                f"IndexRepository 缓存未命中且 cache_mode=read: {symbol}\n"
                f"提示：当前为离线模式，请确保本地缓存存在，或切换到 read_write 模式。"
            )

        safe_start = self.calendar.prev_trade_day(
            self.calendar.prev_trade_day(start)
        )

        try:
            df = self.data_source.get_index_daily(
                symbol=symbol,
                start=safe_start,
                end=end,
            )
        except DataSourceError:
            if cache_path.exists():
                logger.warning(f"网络请求失败，使用本地缓存: {cache_path}")
                try:
                    df = pd.read_csv(cache_path)
                except UnicodeDecodeError:
                    df = pd.read_csv(cache_path, encoding="gbk")
                df = self._validate_df(df)
                df = self._normalize_df_date(df)
                mask = (df["_date_norm"] >= start) & (df["_date_norm"] <= end)
                sliced = df.loc[mask]
                if len(sliced) >= 2:
                    return sliced
            raise

        df = self._validate_df(df)
        df = self._normalize_df_date(df)
        df = df[df["_date_norm"] >= start].drop(columns=["_date_norm"])

        if self.cache_mode == "read_write":
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            if cache_path.exists():
                try:
                    old = pd.read_csv(cache_path)
                except UnicodeDecodeError:
                    old = pd.read_csv(cache_path, encoding="gbk")
                old["date"] = old["date"].astype(str)
                old["_date_norm"] = old["date"].str.replace("-", "")
                old = old[old["_date_norm"] >= start].drop(columns=["_date_norm"])
                df["date"] = df["date"].astype(str)
                df = (
                    pd.concat([old, df])
                    .drop_duplicates(subset=["date"], keep="last")
                    .sort_values("date")
                )
                df = self._validate_df(df)
            df.to_csv(cache_path, index=False)

        df = self._normalize_df_date(df)
        mask = (df["_date_norm"] >= start) & (df["_date_norm"] <= end)
        sliced = df.loc[mask]

        if len(sliced) < 2 and not allow_partial:
            raise ValueError(
                f"指数数据不足: symbol={symbol}, start={start}, end={end}, rows={len(sliced)}"
            )

        return sliced
