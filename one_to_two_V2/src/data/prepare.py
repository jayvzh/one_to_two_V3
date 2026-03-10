"""Data preparation utilities for training.

This module contains:
- build_training_data: Build training data from cached zt pool data
"""
from pathlib import Path

import pandas as pd

from ..utils.logging_config import get_logger

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

logger = get_logger(__name__)

from ..core.constants import InsufficientDataError


def build_training_data(
    zt_cache_dir: Path,
    output_path: Path | None = None,
    date_range: tuple[str, str] | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """Build training data from cached zt pool data.
    
    Args:
        zt_cache_dir: Directory containing zt cache files (zt_YYYYMMDD.csv)
        output_path: Optional path to save the training data
        date_range: Optional (start, end) date range in YYYYMMDD format
        verbose: Print progress information
        
    Returns:
        DataFrame with training data
    """
    zt_files = sorted(zt_cache_dir.glob("zt_*.csv"))

    if not zt_files:
        raise InsufficientDataError(f"No zt cache files found in {zt_cache_dir}")

    if date_range:
        start, end = date_range
        zt_files = [f for f in zt_files if start <= f.stem.replace("zt_", "") <= end]

    if verbose:
        logger.info(f"找到 {len(zt_files)} 个缓存文件")
        if date_range:
            logger.info(f"日期范围: {date_range[0]} ~ {date_range[1]}")

    all_data: list[pd.DataFrame] = []
    failed_files: list[str] = []

    iterator = tqdm(zt_files, desc="读取缓存文件", unit="个") if HAS_TQDM and verbose else zt_files

    for zt_file in iterator:
        date = zt_file.stem.replace("zt_", "")

        try:
            df = pd.read_csv(zt_file, dtype={"symbol": str})
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(zt_file, dtype={"symbol": str}, encoding="gbk")
            except Exception as e:
                failed_files.append(f"{zt_file.name}: {e}")
                continue
        except Exception as e:
            failed_files.append(f"{zt_file.name}: {e}")
            continue

        if "symbol" not in df.columns:
            if verbose:
                logger.warning(f"{zt_file.name}: 缺少 symbol 列")
            continue

        df = _prepare_row(df, date)
        if not df.empty:
            all_data.append(df)

    if failed_files and verbose:
        logger.warning(f"{len(failed_files)} 个文件读取失败:")
        for f in failed_files[:5]:
            logger.warning(f"  - {f}")
        if len(failed_files) > 5:
            logger.warning(f"  ... 还有 {len(failed_files) - 5} 个")

    if not all_data:
        raise InsufficientDataError("No valid data found")

    if verbose:
        logger.info(f"成功读取 {len(all_data)} 天的数据")

    result = pd.concat(all_data, ignore_index=True)

    result = result.sort_values(["symbol", "date"]).reset_index(drop=True)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output_path, index=False)
        logger.info(f"Training data saved to {output_path}, rows={len(result)}")

    return result


def _prepare_row(df: pd.DataFrame, date: str) -> pd.DataFrame:
    """Prepare a single day's data for training.
    
    Args:
        df: DataFrame with zt pool data
        date: Date string (YYYYMMDD)
        
    Returns:
        DataFrame with prepared columns
    """
    required_cols = ["symbol", "board_count", "circ_mv", "turnover", "amount", "first_seal_time", "open_times"]

    available_cols = [c for c in required_cols if c in df.columns]

    if "symbol" not in available_cols:
        return pd.DataFrame()

    out = df[available_cols].copy()

    out["date"] = date

    out["is_limit_up"] = 1

    if "first_seal_time" in out.columns:
        out["first_seal_time"] = out["first_seal_time"].astype(str).str.zfill(6)
        out["first_seal_minutes"] = out["first_seal_time"].apply(_time_to_minutes)
        out["is_early_seal"] = (out["first_seal_minutes"] <= 600).astype(int)
    else:
        out["first_seal_minutes"] = 0
        out["is_early_seal"] = 0

    return out


def _time_to_minutes(time_str: str) -> int:
    """Convert time string (HHMMSS) to minutes from midnight.
    
    Args:
        time_str: Time string in HHMMSS format
        
    Returns:
        Minutes from midnight
    """
    try:
        time_str = str(time_str).zfill(6)
        hours = int(time_str[:2])
        minutes = int(time_str[2:4])
        return hours * 60 + minutes
    except (ValueError, IndexError):
        return 0


def main() -> None:
    """Main entry point."""
    zt_cache_dir = Path("./data/cache/zt")
    output_path = Path("./data/training_data.csv")

    df = build_training_data(
        zt_cache_dir=zt_cache_dir,
        output_path=output_path,
    )

    logger.info("")
    logger.info("数据统计:")
    logger.info(f"  总行数: {len(df)}")
    logger.info(f"  日期范围: {df['date'].min()} ~ {df['date'].max()}")
    logger.info(f"  股票数量: {df['symbol'].nunique()}")
    logger.info(f"  列: {list(df.columns)}")


if __name__ == "__main__":
    main()
