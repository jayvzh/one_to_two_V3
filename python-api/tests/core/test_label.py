"""Tests for core/label.py module."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pandas as pd
import pytest

from core.constants import SchemaError
from core.label import OneToTwoLabelBuilder


class TestOneToTwoLabelBuilder:
    """Tests for OneToTwoLabelBuilder class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.trade_days = ["20260101", "20260102", "20260103", "20260104"]
        self.trade_day_map = {
            "20260101": "20260102",
            "20260102": "20260103",
            "20260103": "20260104",
        }

        def get_next_trade_day(date: str) -> str:
            if date not in self.trade_day_map:
                raise ValueError(f"No next trade day for {date}")
            return self.trade_day_map[date]

        self.builder = OneToTwoLabelBuilder(get_next_trade_day=get_next_trade_day)

    def test_build_basic(self):
        """Test basic label building."""
        df = pd.DataFrame({
            "date": ["20260101", "20260101", "20260102", "20260102"],
            "symbol": ["000001", "000002", "000001", "000002"],
            "is_limit_up": [1, 0, 1, 1],
        })

        result = self.builder.build(df, drop_last_unlabeled=True)

        assert "label" in result.columns
        assert len(result) == 4
        labels = result["label"].tolist()
        assert all(l in [0, 1] for l in labels)

    def test_build_with_normalize_date(self):
        """Test label building with date normalization."""
        df = pd.DataFrame({
            "date": ["2026-01-01", "2026-01-01"],
            "symbol": ["000001", "000002"],
            "is_limit_up": [1, 0],
        })

        def normalize_date(date: str) -> str:
            return date.replace("-", "")

        result = self.builder.build(
            df,
            drop_last_unlabeled=True,
            normalize_date=normalize_date,
        )

        assert "label" in result.columns

    def test_build_missing_column(self):
        """Test with missing required column."""
        df = pd.DataFrame({
            "date": ["20260101"],
            "symbol": ["000001"],
        })

        with pytest.raises(SchemaError):
            self.builder.build(df)

    def test_build_empty_df(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame({
            "date": [],
            "symbol": [],
            "is_limit_up": [],
        })

        result = self.builder.build(df, drop_last_unlabeled=True)
        assert len(result) == 0

    def test_build_keep_unlabeled(self):
        """Test keeping unlabeled rows."""
        df = pd.DataFrame({
            "date": ["20260101", "20260104"],
            "symbol": ["000001", "000002"],
            "is_limit_up": [1, 0],
        })

        result = self.builder.build(df, drop_last_unlabeled=False)

        assert len(result) == 2
        assert result[result["date"] == "20260104"]["label"].isna().any()

    def test_to_binary_limit_up(self):
        """Test _to_binary_limit_up conversion."""
        assert self.builder._to_binary_limit_up(1) == 1
        assert self.builder._to_binary_limit_up(0) == 0
        assert self.builder._to_binary_limit_up(True) == 1
        assert self.builder._to_binary_limit_up(False) == 0
        assert self.builder._to_binary_limit_up("1") == 1
        assert self.builder._to_binary_limit_up("0") == 0
        assert self.builder._to_binary_limit_up("true") == 1
        assert self.builder._to_binary_limit_up("false") == 0
        assert self.builder._to_binary_limit_up(None) == 0
        assert self.builder._to_binary_limit_up(pd.NA) == 0

    def test_symbol_padding(self):
        """Test that symbol is zero-padded to 6 digits."""
        df = pd.DataFrame({
            "date": ["20260101", "20260101"],
            "symbol": ["1", "2"],
            "is_limit_up": [1, 0],
        })

        result = self.builder.build(df, drop_last_unlabeled=True)

        assert result["symbol"].tolist() == ["000001", "000002"]
