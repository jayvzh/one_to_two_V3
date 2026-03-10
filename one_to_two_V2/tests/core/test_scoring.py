"""Tests for core/scoring.py module."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pandas as pd
import pytest

from core.constants import SchemaError
from core.scoring import (
    OneToTwoResult,
    calc_one_to_two,
    detect_first_board,
    detect_second_board,
)


class TestDetectFirstBoard:
    """Tests for detect_first_board function."""

    def test_detect_first_board_basic(self):
        """Test basic first board detection."""
        df = pd.DataFrame({
            "symbol": ["000001", "000002", "000003"],
            "board_count": [1, 2, 1],
        })
        result = detect_first_board(df)
        assert len(result) == 2
        assert set(result["symbol"]) == {"000001", "000003"}

    def test_detect_first_board_empty(self):
        """Test with no first board stocks."""
        df = pd.DataFrame({
            "symbol": ["000001", "000002"],
            "board_count": [2, 3],
        })
        result = detect_first_board(df)
        assert len(result) == 0

    def test_detect_first_board_missing_column(self):
        """Test with missing board_count column."""
        df = pd.DataFrame({"symbol": ["000001"]})
        with pytest.raises(SchemaError):
            detect_first_board(df)

    def test_detect_first_board_custom_column(self):
        """Test with custom board column name."""
        df = pd.DataFrame({
            "symbol": ["000001", "000002"],
            "连板数": [1, 2],
        })
        result = detect_first_board(df, board_col="连板数")
        assert len(result) == 1


class TestDetectSecondBoard:
    """Tests for detect_second_board function."""

    def test_detect_second_board_basic(self):
        """Test basic second board detection."""
        df = pd.DataFrame({
            "symbol": ["000001", "000002", "000003"],
            "board_count": [1, 2, 2],
        })
        result = detect_second_board(df)
        assert len(result) == 2
        assert set(result["symbol"]) == {"000002", "000003"}


class TestCalcOneToTwo:
    """Tests for calc_one_to_two function."""

    def test_calc_one_to_two_basic(self):
        """Test basic one-to-two calculation."""
        today_zt = pd.DataFrame({
            "symbol": ["000001", "000002", "000003"],
            "board_count": [1, 1, 2],
        })
        next_day_zt = pd.DataFrame({
            "symbol": ["000001", "000003", "000004"],
            "board_count": [2, 3, 1],
        })
        result = calc_one_to_two("20260101", today_zt, next_day_zt)

        assert isinstance(result, OneToTwoResult)
        assert result.date == "20260101"
        assert result.first_board_count == 2
        assert result.success_count == 1
        assert result.success_rate == 0.5

    def test_calc_one_to_two_no_first_board(self):
        """Test with no first board stocks."""
        today_zt = pd.DataFrame({
            "symbol": ["000001", "000002"],
            "board_count": [2, 3],
        })
        next_day_zt = pd.DataFrame({
            "symbol": ["000001"],
            "board_count": [3],
        })
        result = calc_one_to_two("20260101", today_zt, next_day_zt)

        assert result.first_board_count == 0
        assert result.success_count == 0
        assert result.success_rate == 0.0

    def test_calc_one_to_two_no_success(self):
        """Test with no successful promotions."""
        today_zt = pd.DataFrame({
            "symbol": ["000001", "000002"],
            "board_count": [1, 1],
        })
        next_day_zt = pd.DataFrame({
            "symbol": ["000003", "000004"],
            "board_count": [1, 1],
        })
        result = calc_one_to_two("20260101", today_zt, next_day_zt)

        assert result.first_board_count == 2
        assert result.success_count == 0
        assert result.success_rate == 0.0

    def test_calc_one_to_two_all_success(self):
        """Test with all first board stocks promoted."""
        today_zt = pd.DataFrame({
            "symbol": ["000001", "000002"],
            "board_count": [1, 1],
        })
        next_day_zt = pd.DataFrame({
            "symbol": ["000001", "000002"],
            "board_count": [2, 2],
        })
        result = calc_one_to_two("20260101", today_zt, next_day_zt)

        assert result.first_board_count == 2
        assert result.success_count == 2
        assert result.success_rate == 1.0

    def test_calc_one_to_two_custom_columns(self):
        """Test with custom column names."""
        today_zt = pd.DataFrame({
            "代码": ["000001"],
            "连板数": [1],
        })
        next_day_zt = pd.DataFrame({
            "代码": ["000001"],
            "连板数": [2],
        })
        result = calc_one_to_two(
            "20260101",
            today_zt,
            next_day_zt,
            code_col="代码",
            board_col="连板数",
        )

        assert result.first_board_count == 1
        assert result.success_count == 1
