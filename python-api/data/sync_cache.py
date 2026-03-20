"""Cache synchronization script.

This script synchronizes:
1. ZT pool data: last 14 trading days (akshare API limit)
2. Index data: last N months (configurable)

Usage:
    python -m src.data.sync_cache
    python -m src.data.sync_cache --zt-trade-days 14 --index-months 2
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from core.logging import get_logger

from .ak import AkshareDataSource, IndexRepository, ZtRepository
from .cache import CacheAvailability, check_cache_availability, get_zt_cache_range
from .trade_calendar import TradingCalendar

logger = get_logger(__name__)


@dataclass(frozen=True)
class SyncConfig:
    """Sync configuration."""
    cache_root: Path = Path("data/cache")
    zt_trade_days: int = 14
    index_months: int = 2
    index_symbol: str = "000300"


@dataclass
class SyncResult:
    """Sync result."""
    zt_synced: int = 0
    zt_failed: int = 0
    index_synced: bool = False
    index_error: str | None = None
    availability: CacheAvailability | None = None

    @property
    def success(self) -> bool:
        return self.zt_failed == 0 and self.index_error is None


def _recent_trade_days(calendar: TradingCalendar, end_trade_day: str, n: int) -> list[str]:
    """Get recent N trade days ending at end_trade_day."""
    dates = [end_trade_day]
    cursor = end_trade_day
    while len(dates) < n:
        cursor = calendar.prev_trade_day(cursor)
        dates.append(cursor)
    dates.reverse()
    return dates


def _resolve_latest_trade_day(calendar: TradingCalendar, now: pd.Timestamp) -> str:
    """Resolve the latest trade day from current time.
    
    For intraday (before 16:00), returns the previous trade day to avoid
    using temporary/incomplete data.
    """
    today = now.strftime("%Y%m%d")
    
    if calendar.is_trade_day(today):
        if now.hour < 16:
            return calendar.prev_trade_day(today)
        return today
    
    return calendar.get_recent_trade_day(today)


def _get_all_trade_dates(calendar: TradingCalendar, start_date: str, end_date: str) -> list[str]:
    """Get all trade dates in range."""
    df = calendar._load_calendar()
    all_dates = df["date"].tolist()
    
    start_dash = calendar._to_dash_date(start_date)
    end_dash = calendar._to_dash_date(end_date)
    
    return [
        d.replace("-", "")
        for d in all_dates
        if start_dash <= d <= end_dash
    ]


def _find_missing_zt_dates(zt_cache_dir: Path, all_trade_dates: list[str]) -> list[str]:
    """Find missing ZT cache dates.
    
    Note: Intraday cache files (zt_{date}_intraday.csv) are ignored
    as they contain incomplete/temporary data.
    """
    missing = []
    for date in all_trade_dates:
        cache_path = zt_cache_dir / f"zt_{date}.csv"
        if not cache_path.exists():
            missing.append(date)
    return missing


def _build_zt_sync_dates(
    calendar: TradingCalendar,
    zt_repo: ZtRepository,
    end_trade_day: str,
    recent_n: int,
) -> tuple[list[str], list[str]]:
    """Build ZT sync dates: all target dates and missing dates."""
    candidate_dates = _recent_trade_days(calendar, end_trade_day=end_trade_day, n=recent_n)
    missing_dates = [d for d in candidate_dates if not zt_repo._cache_path(d).exists()]
    return candidate_dates, missing_dates


def _build_index_sync_plan(
    calendar: TradingCalendar,
    cache_path: Path,
    end_trade_day: str,
    months: int,
    zt_start_date: str | None = None,
) -> tuple[str, str]:
    """Build index sync plan: start and end dates.
    
    Args:
        calendar: TradingCalendar instance
        cache_path: Path to index cache file
        end_trade_day: End trade day for sync
        months: Number of months to sync
        zt_start_date: Optional ZT cache start date to limit index start date
    """
    end_ts = pd.to_datetime(end_trade_day)
    window_start_ts = end_ts - pd.DateOffset(months=months)

    calendar_df = calendar._load_calendar().copy()
    calendar_df["date_n"] = calendar_df["date"].astype(str).str.replace("-", "")

    end_trade_day_n = end_trade_day.replace("-", "")
    
    if zt_start_date:
        window_start_raw = zt_start_date
    else:
        window_start_raw = window_start_ts.strftime("%Y%m%d")

    available = calendar_df[calendar_df["date_n"] <= end_trade_day_n]["date_n"].tolist()
    if not available:
        raise ValueError(f"交易日历中不存在 <= {end_trade_day} 的交易日")

    window_candidates = [d for d in available if int(d) >= int(window_start_raw)]
    target_start = str(window_candidates[0]) if window_candidates else str(available[0])

    if not cache_path.exists():
        return target_start, end_trade_day

    try:
        cached = pd.read_csv(cache_path)
    except UnicodeDecodeError:
        try:
            cached = pd.read_csv(cache_path, encoding="gbk")
        except Exception:
            return target_start, end_trade_day
    except Exception:
        return target_start, end_trade_day

    if cached.empty or "date" not in cached.columns:
        return target_start, end_trade_day

    cached_dates = (
        cached["date"]
        .astype(str)
        .str.replace("-", "")
        .dropna()
        .sort_values()
        .tolist()
    )
    if not cached_dates:
        return target_start, end_trade_day

    latest_cached = cached_dates[-1]
    earliest_cached = cached_dates[0]

    need_fetch_end = int(latest_cached) < int(end_trade_day)
    need_fetch_start = int(earliest_cached) > int(target_start)

    if not need_fetch_end and not need_fetch_start:
        return "", ""

    if end_trade_day not in available:
        return "", ""

    if not need_fetch_end:
        return target_start, str(earliest_cached)

    if end_trade_day in cached_dates:
        return "", ""

    missing_start_candidates = [d for d in available if int(d) > int(latest_cached)]
    if not missing_start_candidates:
        return "", ""

    fetch_start = max(int(target_start), int(missing_start_candidates[0]))
    return str(fetch_start), end_trade_day


def run_sync(config: SyncConfig, now: pd.Timestamp | None = None, silent: bool = False) -> SyncResult:
    """Run cache synchronization.
    
    Args:
        config: Sync configuration
        now: Current timestamp (for testing)
        silent: If True, suppress detailed output
        
    Returns:
        SyncResult with sync statistics
    """
    now = now or pd.Timestamp.today()
    result = SyncResult()

    cache_root = config.cache_root
    calendar = TradingCalendar(cache_dir=cache_root)
    ds = AkshareDataSource(max_retries=5, retry_sleep=2.0)

    zt_repo = ZtRepository(
        data_source=ds,
        cache_dir=cache_root / "zt",
        cache_mode="read_write",
        calendar=calendar,
    )
    index_repo = IndexRepository(
        data_source=ds,
        cache_dir=cache_root / "index",
        calendar=calendar,
        cache_mode="read_write",
        default_symbol=config.index_symbol,
    )

    end_trade_day = _resolve_latest_trade_day(calendar, now=now)

    is_intraday = (
        now.hour < 16
        and now.strftime("%Y%m%d") == end_trade_day
        and calendar.is_trade_day(end_trade_day)
    )

    if not silent:
        logger.info(f"[SYNC] 最新交易日: {end_trade_day}")
        if is_intraday:
            logger.info("[SYNC] 当前为盘中时段，指数数据将同步至上一交易日")
        else:
            logger.info("[SYNC] 当前为盘后时段，数据将同步至最新交易日")
        logger.info(f"[SYNC] 缓存目录: {cache_root}")

    zt_all_dates, zt_missing_dates = _build_zt_sync_dates(
        calendar=calendar,
        zt_repo=zt_repo,
        end_trade_day=end_trade_day,
        recent_n=config.zt_trade_days,
    )

    zt_range = get_zt_cache_range(cache_root)
    zt_start_date = zt_range.start_date if zt_range.available else None

    index_end_trade_day = calendar.prev_trade_day(end_trade_day) if is_intraday else end_trade_day

    if not silent:
        print(
            f"[ZT] 目标交易日范围: {zt_all_dates[0]} ~ {zt_all_dates[-1]}, 共 {len(zt_all_dates)} 天"
        )

    if not zt_missing_dates:
        if not silent:
            print("[ZT] 本地缓存已覆盖目标范围，无需拉取")
    else:
        if not silent:
            print(f"[ZT] 需拉取 {len(zt_missing_dates)} 天: {', '.join(zt_missing_dates)}")
        for date in zt_missing_dates:
            try:
                df, is_intraday = zt_repo.get_by_date(date=date, refresh=False)
                result.zt_synced += 1
                if not silent:
                    intraday_marker = " (盘中)" if is_intraday else ""
                    print(f"  [OK] {date}{intraday_marker}")
            except Exception as e:
                result.zt_failed += 1
                if not silent:
                    print(f"  [FAIL] {date}: {e}")
        if not silent:
            print("[ZT] 同步完成")

    index_cache_path = index_repo._cache_path(config.index_symbol)
    index_start, index_end = _build_index_sync_plan(
        calendar=calendar,
        cache_path=index_cache_path,
        end_trade_day=index_end_trade_day,
        months=config.index_months,
        zt_start_date=zt_start_date,
    )

    if not index_start:
        if not silent:
            print("[INDEX] 本地缓存已是最新，无需拉取")
        result.index_synced = True
    else:
        if not silent:
            print(
                f"[INDEX] 目标交易日范围: {index_start} ~ {index_end}"
                f" (窗口: 最近 {config.index_months} 个月)"
            )
        try:
            index_repo.get_daily(
                start=index_start,
                end=index_end,
                symbol=config.index_symbol,
                refresh=True,
            )
            result.index_synced = True
            if not silent:
                logger.info("[INDEX] 同步完成")
        except Exception as e:
            result.index_error = f"{type(e).__name__}: {e}"
            if not silent:
                logger.error(f"[INDEX] 同步失败: {result.index_error}")
                logger.warning("[INDEX] 提示: 网络连接不稳定，请稍后重试或检查网络连接")

    result.availability = check_cache_availability(
        cache_dir=cache_root,
        train_months=6,
        index_symbol=config.index_symbol,
    )

    if not silent:
        logger.info("")
        logger.info("[SYNC] 缓存同步完成")

    return result


def ensure_cache_for_training(
    cache_dir: Path,
    train_months: int = 6,
    index_symbol: str = "000300",
    auto_sync: bool = True,
) -> CacheAvailability:
    """Ensure cache is available for training, sync if needed.
    
    This function:
    1. Checks current cache availability
    2. If cache is missing/insufficient and auto_sync is True, syncs data
    3. Returns updated cache availability
    
    Sync strategy:
    - ZT data: Use existing cache (waizaowang provides historical data)
    - Index data: Sync to match ZT cache range (akshare has no time limit for index)
    
    Args:
        cache_dir: Cache directory
        train_months: Required training months
        index_symbol: Index symbol
        auto_sync: Whether to auto-sync if cache is missing
        
    Returns:
        CacheAvailability with current status
    """
    from .cache import get_index_cache_range, get_zt_cache_range

    availability = check_cache_availability(
        cache_dir=cache_dir,
        train_months=train_months,
        index_symbol=index_symbol,
    )

    need_sync = False
    sync_reasons = []

    if not availability.zt_range.available:
        need_sync = True
        sync_reasons.append("涨停池缓存不存在")

    if not availability.index_range.available:
        need_sync = True
        sync_reasons.append("指数缓存不存在")

    zt_range = get_zt_cache_range(cache_dir)
    index_range = get_index_cache_range(cache_dir, index_symbol)

    if zt_range.available and index_range.available:
        if index_range.start_date > zt_range.start_date:
            need_sync = True
            sync_reasons.append(
                f"指数缓存起始({index_range.start_date})晚于涨停池({zt_range.start_date})，需补全"
            )

        if index_range.end_date < zt_range.end_date:
            need_sync = True
            sync_reasons.append(
                f"指数缓存结束({index_range.end_date})早于涨停池({zt_range.end_date})，需补全"
            )

    if zt_range.available:
        calendar = TradingCalendar(cache_dir=cache_dir)
        latest_trade_day = _resolve_latest_trade_day(calendar, pd.Timestamp.today())
        all_trade_dates = _get_all_trade_dates(calendar, zt_range.start_date, latest_trade_day)
        missing_dates = _find_missing_zt_dates(cache_dir / "zt", all_trade_dates)
        
        if missing_dates:
            need_sync = True
            sync_reasons.append(f"涨停池缓存缺失 {len(missing_dates)} 天数据")

    if need_sync and auto_sync:
        logger.info("")
        logger.info("[AUTO-SYNC] 检测到缓存不足，自动拉取数据...")
        for reason in sync_reasons:
            logger.info(f"  - {reason}")

        calendar = TradingCalendar(cache_dir=cache_dir)
        ds = AkshareDataSource(max_retries=5, retry_sleep=2.0)
        
        zt_repo = ZtRepository(
            data_source=ds,
            cache_dir=cache_dir / "zt",
            cache_mode="read_write",
            calendar=calendar,
        )
        index_repo = IndexRepository(
            data_source=ds,
            cache_dir=cache_dir / "index",
            calendar=calendar,
            cache_mode="read_write",
            default_symbol=index_symbol,
        )

        if zt_range.available:
            latest_trade_day = _resolve_latest_trade_day(calendar, pd.Timestamp.today())
            
            all_trade_dates = _get_all_trade_dates(calendar, zt_range.start_date, latest_trade_day)
            missing_dates = _find_missing_zt_dates(cache_dir / "zt", all_trade_dates)
            
            if missing_dates:
                logger.info(f"  [ZT] 发现 {len(missing_dates)} 个缺失的涨停池日期，尝试补全...")
                synced = 0
                failed = 0
                for date in missing_dates:
                    try:
                        df, is_intraday = zt_repo.get_by_date(date=date, refresh=True)
                        if not is_intraday:
                            synced += 1
                        else:
                            logger.info(f"    [SKIP] {date} 为盘中数据，跳过")
                    except Exception as e:
                        failed += 1
                        logger.warning(f"    [FAIL] {date}: {e}")
                
                if synced > 0:
                    logger.info(f"  [ZT] 成功补全 {synced} 天涨停池数据")
                if failed > 0:
                    logger.warning(f"  [ZT] 补全失败 {failed} 天")
                
                zt_range = get_zt_cache_range(cache_dir)
            
            if zt_range.end_date < latest_trade_day:
                logger.info(f"  [ZT] 涨停池缓存 ({zt_range.end_date}) 早于最新交易日 ({latest_trade_day})，尝试更新...")
                
                try:
                    df, is_intraday = zt_repo.get_by_date(date=latest_trade_day, refresh=True)
                    if not is_intraday:
                        logger.info(f"  [ZT] 成功更新涨停池数据至 {latest_trade_day}")
                        zt_range = get_zt_cache_range(cache_dir)
                    else:
                        logger.info(f"  [ZT] 当前为盘中时段，跳过更新")
                except Exception as e:
                    logger.warning(f"  [ZT] 更新失败: {e}")
            else:
                logger.info(f"  [INFO] 涨停池缓存已是最新 ({zt_range.end_date})")
            
            index_start = zt_range.start_date
            index_end = zt_range.end_date

            logger.info(f"  [INDEX] 同步指数数据: {index_start} ~ {index_end}")
            try:
                index_repo.get_daily(
                    start=index_start,
                    end=index_end,
                    symbol=index_symbol,
                    refresh=True,
                )
                logger.info("  [INDEX] 同步完成")
            except Exception as e:
                logger.error(f"  [INDEX] 同步失败: {e}")
        else:
            config = SyncConfig(
                cache_root=cache_dir,
                zt_trade_days=14,
                index_months=max(train_months, 2),
                index_symbol=index_symbol,
            )
            sync_result = run_sync(config, silent=False)

            if sync_result.zt_failed > 0:
                logger.warning(f"涨停池同步失败 {sync_result.zt_failed} 天")

            if sync_result.index_error:
                logger.warning(f"指数同步失败: {sync_result.index_error}")

        availability = check_cache_availability(
            cache_dir=cache_dir,
            train_months=train_months,
            index_symbol=index_symbol,
        )

    return availability


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="同步 zt / index 缓存数据")
    parser.add_argument("--cache-root", default="data/cache", help="缓存根目录")
    parser.add_argument("--zt-trade-days", type=int, default=14, help="zt 同步最近 N 个交易日 (默认14，akshare API限制)")
    parser.add_argument("--index-months", type=int, default=2, help="index 同步最近 N 个月")
    parser.add_argument("--index-symbol", default="000300", help="指数代码，默认沪深300")
    args = parser.parse_args()

    run_sync(
        SyncConfig(
            cache_root=Path(args.cache_root),
            zt_trade_days=args.zt_trade_days,
            index_months=args.index_months,
            index_symbol=args.index_symbol,
        )
    )


if __name__ == "__main__":
    main()
