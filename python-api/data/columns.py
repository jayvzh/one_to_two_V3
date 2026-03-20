"""Centralized column mapping from raw cn columns to canonical fields.

This module contains:
- ZT_POOL_COLUMN_MAP: Column mapping for limit-up pool data (AkShare)
- INDEX_COLUMN_MAP: Column mapping for index data
- normalize_zt_pool_columns: Normalize limit-up pool DataFrame columns
- normalize_index_columns: Normalize index DataFrame columns
"""
from __future__ import annotations

import pandas as pd

ZT_POOL_COLUMN_MAP = {
    "代码": "symbol",
    "名称": "name",
    "连板数": "board_count",
    "涨跌幅": "change_pct",
    "流通市值": "circ_mv",
    "换手率": "turnover",
    "成交额": "amount",
    "首次封板时间": "first_seal_time",
    "炸板次数": "open_times",
}

ZT_POOL_COLUMN_MAP_REVERSE = {v: k for k, v in ZT_POOL_COLUMN_MAP.items()}

INDEX_COLUMN_MAP = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "turnover_amount",
    "振幅": "amplitude",
    "涨跌幅": "change_pct",
}

INDEX_COLUMN_MAP_REVERSE = {v: k for k, v in INDEX_COLUMN_MAP.items()}


def _add_alias_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Add alias columns based on mapping.
    
    Args:
        df: DataFrame to process
        mapping: Column mapping dict
        
    Returns:
        DataFrame with alias columns added
    """
    out = df.copy()
    for raw_col, std_col in mapping.items():
        if raw_col in out.columns and std_col not in out.columns:
            out[std_col] = out[raw_col]
    return out


def normalize_zt_pool_columns(df: pd.DataFrame, date: str | None = None) -> pd.DataFrame:
    """Normalize limit-up pool DataFrame columns.
    
    - If data has Chinese column names, add English column names
    - If data has English column names, add Chinese column names
    - If date column is not provided, use the passed date parameter
    
    Args:
        df: DataFrame to normalize
        date: Optional date string to add as date column
        
    Returns:
        Normalized DataFrame
    """
    out = _add_alias_columns(df, ZT_POOL_COLUMN_MAP)
    out = _add_alias_columns(out, ZT_POOL_COLUMN_MAP_REVERSE)

    if date is not None and "date" not in out.columns:
        out["date"] = str(date)
    return out


def normalize_index_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize index DataFrame columns.
    
    - If data has Chinese column names, add English column names
    - If data has English column names, add Chinese column names
    - Date column is converted to YYYYMMDD format
    
    Args:
        df: DataFrame to normalize
        
    Returns:
        Normalized DataFrame
    """
    out = _add_alias_columns(df, INDEX_COLUMN_MAP)
    out = _add_alias_columns(out, INDEX_COLUMN_MAP_REVERSE)

    if "date" in out.columns:
        out["date"] = out["date"].astype(str).str.replace("-", "", regex=False)

    if "日期" in out.columns:
        out["日期"] = out["日期"].astype(str).str.replace("-", "", regex=False)

    return out
