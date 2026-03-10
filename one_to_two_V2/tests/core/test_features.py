"""Tests for core/features.py module."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from core.constants import SchemaError
from core.features import (
    MarketFeatureBuilder,
    MarketFeatures,
    StockFeatureBuilder,
    _time_to_minutes,
)
from core.scoring import OneToTwoResult


class TestTimeToMinutes:
    """Tests for _time_to_minutes function."""

    def test_normal_time_conversion(self):
        """Test normal time conversion (09:25:00 -> 5 minutes from 09:30)."""
        result = _time_to_minutes("092500")
        assert result == -5.0

    def test_time_after_open(self):
        """Test time after market open (10:00:00 -> 30 minutes from 09:30)."""
        result = _time_to_minutes("100000")
        assert result == 30.0

    def test_time_exactly_open(self):
        """Test time exactly at market open (09:30:00 -> 0 minutes)."""
        result = _time_to_minutes("093000")
        assert result == 0.0

    def test_time_with_short_format(self):
        """Test time with short format (92500 -> -5 minutes)."""
        result = _time_to_minutes("92500")
        assert result == -5.0

    def test_time_with_integer_input(self):
        """Test time with integer input."""
        result = _time_to_minutes(92500)
        assert result == -5.0

    def test_invalid_time_returns_nan(self):
        """Test invalid time returns NaN."""
        result = _time_to_minutes("invalid")
        assert np.isnan(result)

    def test_none_time_returns_nan(self):
        """Test None time returns NaN."""
        result = _time_to_minutes(None)
        assert np.isnan(result)

    def test_empty_string_returns_nan(self):
        """Test empty string returns NaN."""
        result = _time_to_minutes("")
        assert np.isnan(result)


class TestMarketFeatures:
    """Tests for MarketFeatures data class."""

    def test_to_frame(self):
        """Test to_frame method returns correct DataFrame."""
        features = MarketFeatures(
            date="20260101",
            success_rate=0.25,
            first_board_ratio=0.5,
            index_return=0.01,
        )
        df = features.to_frame()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert list(df.columns) == ["date", "success_rate", "first_board_ratio", "index_return"]
        assert df.iloc[0]["date"] == "20260101"
        assert df.iloc[0]["success_rate"] == 0.25
        assert df.iloc[0]["first_board_ratio"] == 0.5
        assert df.iloc[0]["index_return"] == 0.01

    def test_to_frame_single_row(self):
        """Test to_frame returns single row DataFrame."""
        features = MarketFeatures(
            date="20260102",
            success_rate=0.0,
            first_board_ratio=0.0,
            index_return=-0.02,
        )
        df = features.to_frame()

        assert len(df) == 1


class TestStockFeatureBuilder:
    """Tests for StockFeatureBuilder class."""

    @pytest.fixture
    def builder(self):
        """Create a StockFeatureBuilder instance."""
        return StockFeatureBuilder()

    @pytest.fixture
    def sample_df(self):
        """Create a sample DataFrame with required columns."""
        return pd.DataFrame({
            "circ_mv": [100.0, 200.0, 300.0],
            "turnover": [0.1, 0.2, 0.3],
            "amount": [1000.0, 2000.0, 3000.0],
            "first_seal_minutes": [5.0, 30.0, 90.0],
            "is_early_seal": [1, 1, 0],
            "open_times": [0, 1, 2],
        })

    def test_build_basic(self, builder, sample_df):
        """Test build method with basic DataFrame."""
        result = builder.build(sample_df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert set(result.columns) == set(StockFeatureBuilder.BASE_FEATURE_COLS)

    def test_build_with_first_seal_time_conversion(self, builder):
        """Test first_seal_time to first_seal_minutes conversion."""
        df = pd.DataFrame({
            "circ_mv": [100.0],
            "turnover": [0.1],
            "amount": [1000.0],
            "first_seal_time": ["092500"],
            "open_times": [0],
        })
        result = builder.build(df)

        assert "first_seal_minutes" in result.columns
        assert result.iloc[0]["first_seal_minutes"] == -5.0

    def test_build_is_early_seal_calculation(self, builder):
        """Test is_early_seal calculation based on first_seal_minutes."""
        df = pd.DataFrame({
            "circ_mv": [100.0, 200.0],
            "turnover": [0.1, 0.2],
            "amount": [1000.0, 2000.0],
            "first_seal_minutes": [30.0, 90.0],
            "open_times": [0, 0],
        })
        result = builder.build(df)

        assert "is_early_seal" in result.columns
        assert result.iloc[0]["is_early_seal"] == 1
        assert result.iloc[1]["is_early_seal"] == 0

    def test_build_is_early_seal_boundary(self, builder):
        """Test is_early_seal at exactly 60 minutes boundary."""
        df = pd.DataFrame({
            "circ_mv": [100.0],
            "turnover": [0.1],
            "amount": [1000.0],
            "first_seal_minutes": [60.0],
            "open_times": [0],
        })
        result = builder.build(df)

        assert result.iloc[0]["is_early_seal"] == 1

    def test_build_open_times_from_chinese_column(self, builder):
        """Test open_times extraction from 炸板次数 column."""
        df = pd.DataFrame({
            "circ_mv": [100.0],
            "turnover": [0.1],
            "amount": [1000.0],
            "first_seal_minutes": [30.0],
            "is_early_seal": [1],
            "炸板次数": [3],
        })
        result = builder.build(df)

        assert "open_times" in result.columns
        assert result.iloc[0]["open_times"] == 3

    def test_build_fillna_with_median(self, builder):
        """Test NaN values are filled with median."""
        df = pd.DataFrame({
            "circ_mv": [100.0, 200.0, np.nan],
            "turnover": [0.1, 0.2, 0.3],
            "amount": [1000.0, 2000.0, 3000.0],
            "first_seal_minutes": [5.0, 30.0, 60.0],
            "is_early_seal": [1, 1, 1],
            "open_times": [0, 0, 0],
        })
        result = builder.build(df)

        assert not result["circ_mv"].isna().any()
        assert result.iloc[2]["circ_mv"] == 150.0

    def test_build_fillna_with_zero_when_all_nan(self, builder):
        """Test NaN values filled with 0 when all values are NaN."""
        df = pd.DataFrame({
            "circ_mv": [np.nan, np.nan, np.nan],
            "turnover": [0.1, 0.2, 0.3],
            "amount": [1000.0, 2000.0, 3000.0],
            "first_seal_minutes": [5.0, 30.0, 60.0],
            "is_early_seal": [1, 1, 1],
            "open_times": [0, 0, 0],
        })
        result = builder.build(df)

        assert not result["circ_mv"].isna().any()
        assert result["circ_mv"].tolist() == [0.0, 0.0, 0.0]

    def test_build_missing_required_column_raises_error(self, builder):
        """Test SchemaError raised when required column is missing."""
        df = pd.DataFrame({
            "circ_mv": [100.0],
            "turnover": [0.1],
        })
        with pytest.raises(SchemaError):
            builder.build(df)

    def test_build_is_early_seal_dtype(self, builder, sample_df):
        """Test is_early_seal is converted to int type."""
        result = builder.build(sample_df)

        assert result["is_early_seal"].dtype == np.int64 or result["is_early_seal"].dtype == int

    def test_build_history_basic(self, builder):
        """Test build_history method with basic DataFrame."""
        df = pd.DataFrame({
            "date": ["20260101", "20260101"],
            "symbol": ["000001", "000002"],
            "is_limit_up": [1, 0],
            "circ_mv": [100.0, 200.0],
            "turnover": [0.1, 0.2],
            "amount": [1000.0, 2000.0],
            "first_seal_minutes": [30.0, 60.0],
            "is_early_seal": [1, 1],
            "open_times": [0, 1],
        })
        result = builder.build_history(df)

        assert "date" in result.columns
        assert "symbol" in result.columns
        assert "is_limit_up" in result.columns
        assert len(result) == 2

    def test_build_history_missing_columns_raises_error(self, builder):
        """Test build_history raises SchemaError when required columns missing."""
        df = pd.DataFrame({
            "circ_mv": [100.0],
            "turnover": [0.1],
            "amount": [1000.0],
            "first_seal_minutes": [30.0],
            "is_early_seal": [1],
            "open_times": [0],
        })
        with pytest.raises(SchemaError):
            builder.build_history(df)

    def test_build_history_dtypes(self, builder):
        """Test build_history converts date, symbol, is_limit_up to string/int."""
        df = pd.DataFrame({
            "date": [20260101],
            "symbol": ["000001"],
            "is_limit_up": [1],
            "circ_mv": [100.0],
            "turnover": [0.1],
            "amount": [1000.0],
            "first_seal_minutes": [30.0],
            "is_early_seal": [1],
            "open_times": [0],
        })
        result = builder.build_history(df)

        assert result.iloc[0]["date"] == "20260101"
        assert result.iloc[0]["symbol"] == "000001"
        assert result.iloc[0]["is_limit_up"] == 1


class TestMarketFeatureBuilder:
    """Tests for MarketFeatureBuilder class."""

    @pytest.fixture
    def builder(self):
        """Create a MarketFeatureBuilder instance."""
        return MarketFeatureBuilder()

    @pytest.fixture
    def sample_one_to_two_result(self):
        """Create a sample OneToTwoResult."""
        return OneToTwoResult(
            date="20260101",
            first_board_count=10,
            success_count=3,
            success_rate=0.3,
        )

    @pytest.fixture
    def sample_index_df(self):
        """Create a sample index DataFrame."""
        return pd.DataFrame({
            "date": ["20260101", "20260102"],
            "close": [3000.0, 3030.0],
        })

    def test_build_basic(self, builder, sample_one_to_two_result, sample_index_df):
        """Test build method with basic inputs."""
        result = builder.build(
            date="20260102",
            one_to_two=sample_one_to_two_result,
            zt_count_today=20,
            index_df=sample_index_df,
        )

        assert isinstance(result, MarketFeatures)
        assert result.date == "20260102"
        assert result.success_rate == 0.3
        assert result.first_board_ratio == 0.5
        assert result.index_return == 0.01

    def test_build_zero_zt_count(self, builder, sample_one_to_two_result, sample_index_df):
        """Test build with zero zt_count_today."""
        result = builder.build(
            date="20260102",
            one_to_two=sample_one_to_two_result,
            zt_count_today=0,
            index_df=sample_index_df,
        )

        assert result.first_board_ratio == 0.0

    def test_build_custom_column_names(self, builder, sample_one_to_two_result):
        """Test build with custom column names."""
        index_df = pd.DataFrame({
            "交易日期": ["20260101", "20260102"],
            "收盘价": [3000.0, 3060.0],
        })
        result = builder.build(
            date="20260102",
            one_to_two=sample_one_to_two_result,
            zt_count_today=10,
            index_df=index_df,
            date_col="交易日期",
            close_col="收盘价",
        )

        assert result.index_return == 0.02

    def test_build_missing_index_columns(self, builder, sample_one_to_two_result):
        """Test build raises SchemaError with missing index columns."""
        index_df = pd.DataFrame({
            "date": ["20260101", "20260102"],
        })
        with pytest.raises(SchemaError):
            builder.build(
                date="20260102",
                one_to_two=sample_one_to_two_result,
                zt_count_today=10,
                index_df=index_df,
            )

    def test_build_first_board_ratio_calculation(self, builder, sample_index_df):
        """Test first_board_ratio calculation."""
        one_to_two = OneToTwoResult(
            date="20260101",
            first_board_count=5,
            success_count=2,
            success_rate=0.4,
        )
        result = builder.build(
            date="20260102",
            one_to_two=one_to_two,
            zt_count_today=25,
            index_df=sample_index_df,
        )

        assert result.first_board_ratio == 0.2

    def test_build_index_return_calculation(self, builder, sample_one_to_two_result):
        """Test index_return calculation."""
        index_df = pd.DataFrame({
            "date": ["20260101", "20260102"],
            "close": [3000.0, 2940.0],
        })
        result = builder.build(
            date="20260102",
            one_to_two=sample_one_to_two_result,
            zt_count_today=10,
            index_df=index_df,
        )

        assert result.index_return == -0.02

    def test_build_sorts_index_by_date(self, builder, sample_one_to_two_result):
        """Test build sorts index DataFrame by date."""
        index_df = pd.DataFrame({
            "date": ["20260102", "20260101"],
            "close": [3030.0, 3000.0],
        })
        result = builder.build(
            date="20260102",
            one_to_two=sample_one_to_two_result,
            zt_count_today=10,
            index_df=index_df,
        )

        assert result.index_return == 0.01
