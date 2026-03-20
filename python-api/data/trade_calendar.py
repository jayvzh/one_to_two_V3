"""Trading calendar (data layer).

This module contains:
- TradingCalendar: Trading calendar functionality

Design Principles:
- All public methods: accept & return YYYYMMDD format
- Internal implementation may use YYYY-MM-DD, but not exposed
"""
from pathlib import Path

import pandas as pd


class TradingCalendar:
    """Trading calendar for trade day validation and calculation.
    
    Design conventions (very important):
    - All public methods: accept & return YYYYMMDD only
    - Internal implementation may use YYYY-MM-DD, but not exposed
    """

    def __init__(self, cache_dir: Path):
        """Initialize trading calendar.
        
        Args:
            cache_dir: Directory for calendar cache file
        """
        self.cache_dir = cache_dir
        self._calendar_path = self.cache_dir / "trade_calendar.csv"
        self._calendar_df: pd.DataFrame | None = None
        self._trade_days_set: set | None = None

    def normalize_date(self, date: str) -> str:
        """Normalize date format to YYYYMMDD.
        
        Supports input YYYYMMDD / YYYY-MM-DD
        
        Args:
            date: Date string to normalize
            
        Returns:
            Date string in YYYYMMDD format
        """
        if "-" in date:
            return date.replace("-", "")
        return date

    def is_trade_day(self, date: str) -> bool:
        """Check if a date is a trade day.
        
        Args:
            date: Date string (YYYYMMDD)
            
        Returns:
            True if trade day, False otherwise
        """
        date = self.normalize_date(date)
        dash_date = self._to_dash_date(date)
        if self._trade_days_set is None:
            df = self._load_calendar()
            self._trade_days_set = set(df["date"])
        return dash_date in self._trade_days_set

    def prev_trade_day(self, date: str) -> str:
        """Get previous trade day.
        
        Args:
            date: Date string (YYYYMMDD)
            
        Returns:
            Previous trade day (YYYYMMDD)
            
        Raises:
            ValueError: If date is not a trade day or is the earliest trade day
        """
        date = self.normalize_date(date)
        dash_date = self._to_dash_date(date)

        df = self._load_calendar()
        dates: list[str] = df["date"].tolist()

        if dash_date not in dates:
            raise ValueError(f"{date} 不是交易日，无法获取 prev_trade_day")

        idx = dates.index(dash_date)
        if idx == 0:
            raise ValueError("已经是最早交易日")

        return dates[idx - 1].replace("-", "")

    def get_recent_trade_day(self, date: str) -> str:
        """Get the most recent trade day on or before the given date.
        
        If the date is a trade day, returns it directly.
        Otherwise, finds the most recent trade day before it.
        
        Args:
            date: Date string (YYYYMMDD)
            
        Returns:
            Most recent trade day (YYYYMMDD)
            
        Raises:
            ValueError: If no trade day found before the given date
        """
        date = self.normalize_date(date)
        dash_date = self._to_dash_date(date)

        df = self._load_calendar()
        dates: list[str] = df["date"].tolist()

        if dash_date in dates:
            return date

        for d in reversed(dates):
            if d < dash_date:
                return d.replace("-", "")

        raise ValueError(f"找不到 {date} 之前的交易日")

    def next_trade_day(self, date: str) -> str:
        """Get next trade day.
        
        Args:
            date: Date string (YYYYMMDD)
            
        Returns:
            Next trade day (YYYYMMDD)
            
        Raises:
            ValueError: If date is not a trade day or is the last trade day
        """
        date = self.normalize_date(date)
        dash_date = self._to_dash_date(date)

        df = self._load_calendar()
        dates: list[str] = df["date"].tolist()

        if dash_date not in dates:
            raise ValueError(f"{date} 不是交易日，无法获取 next_trade_day")

        idx = dates.index(dash_date)
        if idx >= len(dates) - 1:
            raise ValueError("已经是最后交易日")

        return dates[idx + 1].replace("-", "")

    def _to_dash_date(self, date_yyyymmdd: str) -> str:
        """Convert YYYYMMDD to YYYY-MM-DD (internal use only)."""
        return (
            f"{date_yyyymmdd[:4]}-"
            f"{date_yyyymmdd[4:6]}-"
            f"{date_yyyymmdd[6:]}"
        )

    def _load_calendar(self) -> pd.DataFrame:
        """Load or fetch trading calendar (YYYY-MM-DD)."""
        if self._calendar_df is not None:
            return self._calendar_df

        if self._calendar_path.exists():
            df = pd.read_csv(self._calendar_path)
        else:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            import akshare as ak
            df = ak.tool_trade_date_hist_sina()
            df = df.rename(columns={"trade_date": "date"})
            df.to_csv(self._calendar_path, index=False)

        df["date"] = df["date"].astype(str)
        df = df.sort_values("date")

        self._calendar_df = df
        return df
