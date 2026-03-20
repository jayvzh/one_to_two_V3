"""Cache utilities (data layer).

This module contains:
- FeatureRepository: Feature data caching with read/write strategies
- get_zt_cache_range: Get limit-up pool cache date range
- get_index_cache_range: Get index cache date range
- check_cache_availability: Check if cache meets training requirements

Design Principles:
- Unified feature persistence and reading
- Support date-based cache reading (hit/miss)
- Basic data quality validation (nulls, duplicates, time series)
"""
from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from core.logging import get_logger, log_banner

from core.constants import CacheError

logger = get_logger(__name__)


@dataclass
class CacheRange:
    """Cache date range information."""
    source: str
    start_date: str | None
    end_date: str | None
    count: int
    available: bool

    def __str__(self) -> str:
        if not self.available:
            return f"[{self.source}] 无缓存数据"
        return f"[{self.source}] {self.start_date} ~ {self.end_date} ({self.count} 条)"


def get_zt_cache_range(cache_dir: Path) -> CacheRange:
    """Get limit-up pool cache date range.

    Args:
        cache_dir: Base cache directory

    Returns:
        CacheRange with zt cache information
    """
    zt_dir = cache_dir / "zt"
    if not zt_dir.exists():
        return CacheRange(
            source="涨停池缓存",
            start_date=None,
            end_date=None,
            count=0,
            available=False,
        )

    zt_files = list(zt_dir.glob("zt_*.csv"))
    if not zt_files:
        return CacheRange(
            source="涨停池缓存",
            start_date=None,
            end_date=None,
            count=0,
            available=False,
        )

    dates = []
    date_pattern = re.compile(r"zt_(\d{8})\.csv")
    for f in zt_files:
        match = date_pattern.match(f.name)
        if match:
            dates.append(match.group(1))

    if not dates:
        return CacheRange(
            source="涨停池缓存",
            start_date=None,
            end_date=None,
            count=0,
            available=False,
        )

    dates.sort()
    return CacheRange(
        source="涨停池缓存",
        start_date=dates[0],
        end_date=dates[-1],
        count=len(dates),
        available=True,
    )


def get_index_cache_range(cache_dir: Path, symbol: str = "000300") -> CacheRange:
    """Get index cache date range.

    Args:
        cache_dir: Base cache directory
        symbol: Index symbol

    Returns:
        CacheRange with index cache information
    """
    index_file = cache_dir / "index" / f"{symbol}_full.csv"
    if not index_file.exists():
        return CacheRange(
            source=f"指数缓存({symbol})",
            start_date=None,
            end_date=None,
            count=0,
            available=False,
        )

    try:
        try:
            df = pd.read_csv(index_file)
        except UnicodeDecodeError:
            df = pd.read_csv(index_file, encoding="gbk")
        if df.empty:
            return CacheRange(
                source=f"指数缓存({symbol})",
                start_date=None,
                end_date=None,
                count=0,
                available=False,
            )

        date_col = "date" if "date" in df.columns else "日期"
        dates = df[date_col].astype(str).str.replace("-", "", regex=False).tolist()
        dates = [d for d in dates if len(d) == 8 and d.isdigit()]
        dates.sort()

        if not dates:
            return CacheRange(
                source=f"指数缓存({symbol})",
                start_date=None,
                end_date=None,
                count=0,
                available=False,
            )

        return CacheRange(
            source=f"指数缓存({symbol})",
            start_date=dates[0],
            end_date=dates[-1],
            count=len(dates),
            available=True,
        )
    except Exception:
        return CacheRange(
            source=f"指数缓存({symbol})",
            start_date=None,
            end_date=None,
            count=0,
            available=False,
        )


@dataclass
class CacheAvailability:
    """Cache availability check result."""
    zt_range: CacheRange
    index_range: CacheRange
    effective_start: str | None
    effective_end: str | None
    train_months_requested: int
    train_months_available: int
    is_sufficient: bool
    warnings: list[str]

    def print_summary(self, compact: bool = False) -> None:
        """Print cache availability summary.
        
        Args:
            compact: If True, print compact format for pipeline integration
        """
        if compact:
            logger.info(f"涨停池缓存: {self.zt_range.start_date} ~ {self.zt_range.end_date} ({self.zt_range.count}天)")
            logger.info(f"指数缓存:   {self.index_range.start_date} ~ {self.index_range.end_date} ({self.index_range.count}天)")
            logger.info(f"有效交集:   {self.effective_start} ~ {self.effective_end}")
            logger.info(f"预期训练窗口: {self.train_months_requested} 个月")
            logger.info(f"实际可用窗口: {self.train_months_available} 个月")

            if self.train_months_available < self.train_months_requested:
                logger.warning("数据不足，将使用全部可用数据")

            for warning in self.warnings:
                logger.warning(warning)
        else:
            logger.info("")
            log_banner(logger, "缓存数据检测报告", width=60)
            logger.info(f"涨停池缓存: {self.zt_range}")
            logger.info(f"指数缓存:   {self.index_range}")
            logger.info("=" * 60)

            if self.is_sufficient:
                logger.info(f"有效数据范围: {self.effective_start} ~ {self.effective_end}")
                logger.info(f"预期训练窗口: {self.train_months_requested} 个月")
                logger.info(f"实际可用窗口: {self.train_months_available} 个月")
            else:
                logger.warning("缓存数据不足，无法进行训练")

            for warning in self.warnings:
                logger.warning(warning)

            logger.info("=" * 60)


def check_cache_availability(
    cache_dir: Path,
    train_months: int = 6,
    test_months: int = 1,
    index_symbol: str = "000300",
) -> CacheAvailability:
    """Check if cache meets training requirements.

    Args:
        cache_dir: Base cache directory
        train_months: Requested training window in months
        test_months: Requested test window in months
        index_symbol: Index symbol to check

    Returns:
        CacheAvailability with check results
    """
    zt_range = get_zt_cache_range(cache_dir)
    index_range = get_index_cache_range(cache_dir, index_symbol)

    warnings = []

    if not zt_range.available:
        warnings.append("涨停池缓存不存在或为空")

    if not index_range.available:
        warnings.append("指数缓存不存在或为空")

    if not zt_range.available or not index_range.available:
        return CacheAvailability(
            zt_range=zt_range,
            index_range=index_range,
            effective_start=None,
            effective_end=None,
            train_months_requested=train_months,
            train_months_available=0,
            is_sufficient=False,
            warnings=warnings,
        )

    effective_start = max(zt_range.start_date, index_range.start_date)
    effective_end = min(zt_range.end_date, index_range.end_date)

    if effective_start > effective_end:
        warnings.append("涨停池和指数缓存的时间范围无交集")
        return CacheAvailability(
            zt_range=zt_range,
            index_range=index_range,
            effective_start=None,
            effective_end=None,
            train_months_requested=train_months,
            train_months_available=0,
            is_sufficient=False,
            warnings=warnings,
        )

    start_ts = pd.to_datetime(effective_start)
    end_ts = pd.to_datetime(effective_end)
    actual_months = (end_ts.year - start_ts.year) * 12 + (end_ts.month - start_ts.month)

    train_months_available = actual_months

    is_sufficient = actual_months >= train_months

    if not is_sufficient:
        warnings.append(
            f"缓存数据跨度({actual_months}个月) < 预期训练窗口({train_months}个月)，"
            f"将使用全部可用数据进行训练"
        )

    if zt_range.start_date > index_range.start_date:
        warnings.append(
            f"涨停池缓存起始日期({zt_range.start_date})晚于指数缓存({index_range.start_date})，"
            f"有效起始日期调整为{effective_start}"
        )

    if zt_range.end_date < index_range.end_date:
        warnings.append(
            f"涨停池缓存结束日期({zt_range.end_date})早于指数缓存({index_range.end_date})，"
            f"有效结束日期调整为{effective_end}"
        )

    return CacheAvailability(
        zt_range=zt_range,
        index_range=index_range,
        effective_start=effective_start,
        effective_end=effective_end,
        train_months_requested=train_months,
        train_months_available=train_months_available,
        is_sufficient=True,
        warnings=warnings,
    )


class FeatureRepository:
    """Feature data repository.
    
    Responsibilities:
    - Unified feature persistence and reading paths
    - Support date-based cache reading (hit/miss)
    - Basic data quality validation (nulls, duplicates, time series)
    """

    def __init__(
        self,
        cache_dir: Path,
        cache_mode: str = "read_write",  # off | read | read_write
    ):
        """Initialize repository.
        
        Args:
            cache_dir: Directory for cache files
            cache_mode: Cache mode (off | read | read_write)
        """
        self.cache_dir = cache_dir
        self.cache_mode = cache_mode

    def _cache_path(self, date: str) -> Path:
        """Get cache file path for a date."""
        return self.cache_dir / f"feature_{date}.csv"

    @staticmethod
    def _read_cache(cache_path: Path) -> pd.DataFrame:
        """Read feature cache preserving symbol encoding (e.g., 000001 keeps leading zeros)."""
        return pd.read_csv(cache_path, dtype={"symbol": str})

    def get_by_date(self, date: str) -> pd.DataFrame:
        """Get feature data for a specific date.
        
        Args:
            date: Date string (YYYYMMDD)
            
        Returns:
            DataFrame with feature data
            
        Raises:
            FileNotFoundError: If cache does not exist
        """
        cache_path = self._cache_path(date)
        if cache_path.exists():
            return self._read_cache(cache_path)
        raise FileNotFoundError(f"Feature 缓存不存在: {cache_path}")

    def save_by_date(self, date: str, df: pd.DataFrame) -> Path:
        """Save feature data for a specific date.
        
        Args:
            date: Date string (YYYYMMDD)
            df: DataFrame with feature data
            
        Returns:
            Path to saved cache file
            
        Raises:
            RuntimeError: If cache_mode is read
        """
        if self.cache_mode == "read":
            raise CacheError("cache_mode=read，禁止写入 feature 缓存")

        self.validate_quality(df)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self._cache_path(date)
        df.to_csv(cache_path, index=False)
        return cache_path

    def get_or_build(
        self,
        date: str,
        builder: Callable[[], pd.DataFrame],
        refresh: bool = False
    ) -> pd.DataFrame:
        """Get feature data from cache or build if not cached.
        
        Args:
            date: Date string (YYYYMMDD)
            builder: Function to build feature data if not cached
            refresh: Force refresh from builder
            
        Returns:
            DataFrame with feature data
        """
        cache_path = self._cache_path(date)

        if self.cache_mode in ("read", "read_write") and not refresh and cache_path.exists():
            return self._read_cache(cache_path)

        if self.cache_mode == "read":
            raise CacheError(f"Feature 缓存未命中且 cache_mode=read: {date}")

        df = builder()
        self.validate_quality(df)

        if self.cache_mode == "read_write":
            df.to_csv(cache_path, index=False)

        return df

    @staticmethod
    def validate_quality(
        df: pd.DataFrame,
        *,
        required_columns: Iterable[str] = ("date", "symbol"),
    ) -> None:
        """Validate feature data quality.
        
        Args:
            df: DataFrame to validate
            required_columns: Required column names
            
        Raises:
            ValueError: If validation fails
        """
        required_columns = tuple(required_columns)
        missing_cols = [c for c in required_columns if c not in df.columns]
        if missing_cols:
            raise ValueError(f"缺少必需列: {missing_cols}")

        if df.empty:
            raise ValueError("特征数据为空")

        if df[list(required_columns)].isna().any().any():
            raise ValueError("必需列存在空值")

        dup_mask = df.duplicated(subset=list(required_columns), keep=False)
        if dup_mask.any():
            dup_rows = df.loc[dup_mask, list(required_columns)].head(5).to_dict("records")
            raise ValueError(f"存在重复键（前5条）: {dup_rows}")

        date_series = pd.to_datetime(df["date"], errors="coerce")
        if date_series.isna().any():
            raise ValueError("date 列存在无法解析的日期")

        if not date_series.is_monotonic_increasing:
            raise ValueError("date 列未按时间升序排列")
