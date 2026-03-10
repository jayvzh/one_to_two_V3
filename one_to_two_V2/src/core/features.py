"""Feature engineering (pure domain layer).

This module contains:
- MarketFeatures: Data class for market-level features
- StockFeatureBuilder: Build stock-level features
- MarketFeatureBuilder: Build market-level features

Design Principles:
- Pure domain logic with no external dependencies
- No data fetching, caching, or IO
- No akshare or data_source dependencies
"""
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .constants import validate_required_columns
from .scoring import OneToTwoResult


@dataclass
class MarketFeatures:
    """Market-level features."""
    date: str
    success_rate: float
    first_board_ratio: float
    index_return: float

    def to_frame(self) -> pd.DataFrame:
        """Convert to DataFrame."""
        return pd.DataFrame([asdict(self)])


def _time_to_minutes(t) -> float:
    """Convert 'HHMMSS' or 'HHMM' to minutes from 09:30.
    
    Args:
        t: Time string like '092500' or '92500'
        
    Returns:
        Minutes from 09:30, or NaN if invalid
    """
    try:
        t = str(int(t)).zfill(6)
        hh = int(t[:2])
        mm = int(t[2:4])
        return float((hh * 60 + mm) - (9 * 60 + 30))
    except (ValueError, TypeError):
        return np.nan


class StockFeatureBuilder:
    """Build stock-level features from raw data."""

    BASE_FEATURE_COLS: list[str] = [
        "circ_mv",
        "turnover",
        "amount",
        "first_seal_minutes",
        "is_early_seal",
        "open_times",
    ]

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        """Build stock features from raw DataFrame.
        
        Args:
            df: DataFrame with stock data (may have first_seal_time instead of first_seal_minutes)
            
        Returns:
            DataFrame with stock features
        """
        df = df.copy()

        if "first_seal_minutes" not in df.columns and "first_seal_time" in df.columns:
            df["first_seal_minutes"] = df["first_seal_time"].apply(_time_to_minutes)

        if "is_early_seal" not in df.columns and "first_seal_minutes" in df.columns:
            df["is_early_seal"] = (df["first_seal_minutes"] <= 60).astype(int)

        if "open_times" not in df.columns and "炸板次数" in df.columns:
            df["open_times"] = df["炸板次数"]

        validate_required_columns(df, self.BASE_FEATURE_COLS, context="StockFeatureBuilder.build")
        features = df[self.BASE_FEATURE_COLS].copy()

        if "is_early_seal" in features.columns:
            features["is_early_seal"] = features["is_early_seal"].astype(int)

        for col in features.columns:
            if features[col].isna().any():
                median_val = features[col].median()
                if pd.notna(median_val):
                    features[col] = features[col].fillna(median_val)
                else:
                    features[col] = features[col].fillna(0)

        return features

    def build_history(self, df: pd.DataFrame) -> pd.DataFrame:
        """Build stock features with history columns.
        
        Args:
            df: DataFrame with stock data including date, symbol, is_limit_up
            
        Returns:
            DataFrame with stock features and history columns
        """
        validate_required_columns(df, ["date", "symbol", "is_limit_up"], context="StockFeatureBuilder.build_history")
        features = self.build(df)
        features["date"] = df["date"].astype(str)
        features["symbol"] = df["symbol"].astype(str)
        features["is_limit_up"] = df["is_limit_up"].astype(int)
        return features


class MarketFeatureBuilder:
    """Build market-level features from domain results."""

    def build(
        self,
        date: str,
        one_to_two: OneToTwoResult,
        zt_count_today: int,
        index_df: pd.DataFrame,
        date_col: str = "date",
        close_col: str = "close",
    ) -> MarketFeatures:
        """Build market features.
        
        Args:
            date: Date string (YYYYMMDD)
            one_to_two: OneToTwoResult from calc_one_to_two
            zt_count_today: Today's limit-up count
            index_df: DataFrame with index data
            date_col: Column name for date
            close_col: Column name for close price
            
        Returns:
            MarketFeatures with market-level features
        """
        if zt_count_today > 0:
            first_board_ratio = one_to_two.first_board_count / zt_count_today
        else:
            first_board_ratio = 0.0

        validate_required_columns(index_df, [date_col, close_col], context="MarketFeatureBuilder")

        index_df = index_df.sort_values(date_col)
        if len(index_df) >= 2:
            prev_close = float(index_df.iloc[-2][close_col])
            last_close = float(index_df.iloc[-1][close_col])
            index_return = (last_close - prev_close) / prev_close
        else:
            index_return = 0.0

        return MarketFeatures(
            date=date,
            success_rate=one_to_two.success_rate,
            first_board_ratio=round(first_board_ratio, 4),
            index_return=round(index_return, 4),
        )
