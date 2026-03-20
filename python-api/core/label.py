"""Label builder (pure domain layer).

This module contains:
- OneToTwoLabelBuilder: Build training labels for one-to-two prediction

Design Principles:
- Pure domain logic with no external dependencies
- No data fetching, caching, or IO
- No akshare or data_source dependencies
- Uses callback for next_trade_day to avoid dependency on data layer
"""
from collections.abc import Callable

import pandas as pd

from .constants import validate_required_columns


class OneToTwoLabelBuilder:
    """Build training labels for one-to-two prediction.
    
    Uses a callback function for getting next trade day to avoid
    dependency on data layer (TradingCalendar).
    """

    def __init__(self, get_next_trade_day: Callable[[str], str]):
        """Initialize label builder.
        
        Args:
            get_next_trade_day: Callback function that takes a date (YYYYMMDD)
                               and returns the next trade day (YYYYMMDD)
        """
        self.get_next_trade_day = get_next_trade_day

    def build(
        self,
        daily_df: pd.DataFrame,
        date_col: str = "date",
        stock_col: str = "symbol",
        limit_up_col: str = "is_limit_up",
        drop_last_unlabeled: bool = True,
        normalize_date: Callable[[str], str] | None = None,
    ) -> pd.DataFrame:
        """Build labels for one-to-two prediction.
        
        Args:
            daily_df: DataFrame with daily stock data
            date_col: Column name for date
            stock_col: Column name for stock code
            limit_up_col: Column name for limit-up flag
            drop_last_unlabeled: Whether to drop rows without labels
            normalize_date: Optional callback to normalize date format
            
        Returns:
            DataFrame with labels added
        """
        df = daily_df.copy()
        validate_required_columns(df, [date_col, stock_col, limit_up_col], context="OneToTwoLabelBuilder")

        df = self._normalize_input(
            df,
            date_col=date_col,
            stock_col=stock_col,
            limit_up_col=limit_up_col,
            normalize_date=normalize_date,
        )

        df = df.sort_values([stock_col, date_col])
        limit_map: dict[tuple, bool] = {
            (row[stock_col], row[date_col]): row[limit_up_col]
            for _, row in df.iterrows()
        }

        labels = []
        for _, row in df.iterrows():
            symbol = row[stock_col]
            date = row[date_col]
            try:
                next_date = self.get_next_trade_day(date)
            except ValueError:
                labels.append(None)
                continue
            labels.append(int(limit_map.get((symbol, next_date), False)))

        df["label"] = labels
        if drop_last_unlabeled:
            df = df[df["label"].notna()].copy()
            df["label"] = df["label"].astype(int)
        return df

    def _normalize_input(
        self,
        df: pd.DataFrame,
        *,
        date_col: str,
        stock_col: str,
        limit_up_col: str,
        normalize_date: Callable[[str], str] | None = None,
    ) -> pd.DataFrame:
        """Normalize input columns to avoid date/format differences.
        
        Args:
            df: DataFrame to normalize
            date_col: Column name for date
            stock_col: Column name for stock code
            limit_up_col: Column name for limit-up flag
            normalize_date: Optional callback to normalize date format
            
        Returns:
            Normalized DataFrame
        """
        out = df.copy()
        if normalize_date:
            out[date_col] = out[date_col].astype(str).map(normalize_date)
        else:
            out[date_col] = out[date_col].astype(str)
        out[stock_col] = out[stock_col].astype(str).str.zfill(6)
        out[limit_up_col] = out[limit_up_col].map(self._to_binary_limit_up)
        return out

    @staticmethod
    def _to_binary_limit_up(value) -> int:
        """Map is_limit_up to 0/1, compatible with bool/int/str.
        
        Args:
            value: Value to convert
            
        Returns:
            0 or 1
        """
        if pd.isna(value):
            return 0

        text = str(value).strip().lower()
        if text in {"1", "1.0", "true", "t", "yes", "y"}:
            return 1
        if text in {"0", "0.0", "false", "f", "no", "n", ""}:
            return 0

        try:
            return int(float(text) != 0)
        except ValueError as exc:
            raise ValueError(f"is_limit_up 存在无法识别的值: {value}") from exc
