"""One-to-two scoring logic (pure domain layer).

Business Background:
    "One-to-two" (一进二) is a popular A-share trading strategy that focuses on
    identifying first-board stocks (首板) that have the potential to successfully
    advance to second-board (二板) status on the next trading day.

    Key Concepts:
    - First-board (首板): A stock that has just hit its first consecutive limit-up
      (涨停) day. This represents the initial momentum breakout.

    - Second-board (二板): A stock that has achieved two consecutive limit-up days.
      Successfully advancing from first-board to second-board is the core objective
      of the one-to-two strategy.

    - One-to-two Success Rate: The percentage of first-board stocks that successfully
      become second-board stocks on the next trading day. This metric is crucial for
      evaluating market conditions and strategy profitability.

    Business Significance:
    - First-board detection identifies potential trading candidates from the daily
      limit-up pool, filtering for stocks with fresh momentum.

    - Second-board detection identifies successful breakouts, used for calculating
      the actual success rate and validating trading signals.

    - Success rate calculation provides the core input for market emotion analysis,
      helping traders determine whether current conditions favor the one-to-two strategy.

This module contains:
- OneToTwoResult: Data class for one-to-two calculation results
- detect_first_board: Detect first-board stocks
- detect_second_board: Detect second-board stocks
- calc_one_to_two: Calculate one-to-two success rate

Design Principles:
- Pure domain logic with no external dependencies
- No data fetching, caching, or IO
- No akshare or data_source dependencies
"""
from dataclasses import dataclass

import pandas as pd

from .constants import validate_required_columns


@dataclass
class OneToTwoResult:
    """Result of one-to-two calculation."""
    date: str
    first_board_count: int
    success_count: int
    success_rate: float


def detect_first_board(zt_df: pd.DataFrame, board_col: str = "board_count") -> pd.DataFrame:
    """Identify first-board stocks (board_count == 1).
    
    Args:
        zt_df: DataFrame with limit-up pool data
        board_col: Column name for board count
        
    Returns:
        DataFrame filtered to first-board stocks
    """
    validate_required_columns(zt_df, [board_col], context="detect_first_board")
    return zt_df[zt_df[board_col] == 1].copy()


def detect_second_board(zt_df: pd.DataFrame, board_col: str = "board_count") -> pd.DataFrame:
    """Identify second-board stocks (board_count == 2).
    
    Args:
        zt_df: DataFrame with limit-up pool data
        board_col: Column name for board count
        
    Returns:
        DataFrame filtered to second-board stocks
    """
    validate_required_columns(zt_df, [board_col], context="detect_second_board")
    return zt_df[zt_df[board_col] == 2].copy()


def calc_one_to_two(
    date: str,
    today_zt: pd.DataFrame,
    next_day_zt: pd.DataFrame,
    code_col: str = "symbol",
    board_col: str = "board_count",
) -> OneToTwoResult:
    """Calculate one-to-two success rate.
    
    Args:
        date: Date string (YYYYMMDD)
        today_zt: Today's limit-up pool data
        next_day_zt: Next day's limit-up pool data
        code_col: Column name for stock code
        board_col: Column name for board count
        
    Returns:
        OneToTwoResult with success rate calculation
    """
    validate_required_columns(today_zt, [code_col, board_col], context="calc_one_to_two.today_zt")
    validate_required_columns(next_day_zt, [code_col, board_col], context="calc_one_to_two.next_day_zt")

    first_board = detect_first_board(today_zt, board_col=board_col)
    second_board = detect_second_board(next_day_zt, board_col=board_col)

    if first_board.empty:
        return OneToTwoResult(date, 0, 0, 0.0)

    fb_codes = set(first_board[code_col])
    sb_codes = set(second_board[code_col])
    success_codes = fb_codes & sb_codes
    success_rate = len(success_codes) / len(fb_codes)

    return OneToTwoResult(
        date=date,
        first_board_count=len(fb_codes),
        success_count=len(success_codes),
        success_rate=round(success_rate, 4),
    )
