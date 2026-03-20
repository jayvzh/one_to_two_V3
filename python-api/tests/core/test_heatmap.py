"""Tests for core/heatmap.py module."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import numpy as np
import pandas as pd
import pytest

from core.heatmap import (
    DEFAULT_SCORE_BINS,
    HeatmapCell,
    HeatmapData,
    bin_model_score,
    calc_success_matrix,
)


class TestHeatmapCell:
    """Tests for HeatmapCell dataclass."""

    def test_basic_attributes(self):
        """Test basic attributes of HeatmapCell."""
        cell = HeatmapCell(
            emotion_score=3.5,
            score_bin="0.6-0.7",
            sample_count=100,
            success_count=30,
            success_rate=0.3,
        )

        assert cell.emotion_score == 3.5
        assert cell.score_bin == "0.6-0.7"
        assert cell.sample_count == 100
        assert cell.success_count == 30
        assert cell.success_rate == 0.3

    def test_default_values(self):
        """Test HeatmapCell with different values."""
        cell = HeatmapCell(
            emotion_score=0.0,
            score_bin="0.0-0.5",
            sample_count=0,
            success_count=0,
            success_rate=0.0,
        )

        assert cell.emotion_score == 0.0
        assert cell.sample_count == 0
        assert cell.success_rate == 0.0

    def test_float_precision(self):
        """Test float precision for success_rate."""
        cell = HeatmapCell(
            emotion_score=2.5,
            score_bin="0.8-1.0",
            sample_count=33,
            success_count=11,
            success_rate=0.3333,
        )

        assert abs(cell.success_rate - 0.3333) < 0.0001


class TestHeatmapData:
    """Tests for HeatmapData dataclass."""

    def test_to_dataframe_empty(self):
        """Test to_dataframe with empty cells."""
        heatmap_data = HeatmapData()
        df = heatmap_data.to_dataframe()

        assert df.empty
        assert isinstance(df, pd.DataFrame)

    def test_to_dataframe_with_cells(self):
        """Test to_dataframe with cells."""
        cells = [
            HeatmapCell(3.0, "0.6-0.7", 100, 30, 0.3),
            HeatmapCell(3.5, "0.6-0.7", 50, 20, 0.4),
            HeatmapCell(3.0, "0.7-0.8", 80, 40, 0.5),
        ]
        heatmap_data = HeatmapData(
            cells=cells,
            emotion_scores=[3.0, 3.5],
            score_bins=["0.6-0.7", "0.7-0.8"],
        )
        df = heatmap_data.to_dataframe()

        assert len(df) == 3
        assert list(df.columns) == [
            "emotion_score", "score_bin", "sample_count",
            "success_count", "success_rate"
        ]
        assert df["emotion_score"].tolist() == [3.0, 3.5, 3.0]
        assert df["score_bin"].tolist() == ["0.6-0.7", "0.6-0.7", "0.7-0.8"]

    def test_to_matrix_empty(self):
        """Test to_matrix with empty cells."""
        heatmap_data = HeatmapData()
        matrix, emotion_scores, score_bins = heatmap_data.to_matrix()

        assert matrix.size == 0
        assert emotion_scores == []
        assert score_bins == []

    def test_to_matrix_with_cells(self):
        """Test to_matrix with cells."""
        cells = [
            HeatmapCell(3.0, "0.6-0.7", 100, 30, 0.3),
            HeatmapCell(3.5, "0.6-0.7", 50, 20, 0.4),
            HeatmapCell(3.0, "0.7-0.8", 80, 40, 0.5),
            HeatmapCell(3.5, "0.7-0.8", 60, 30, 0.5),
        ]
        heatmap_data = HeatmapData(
            cells=cells,
            emotion_scores=[3.0, 3.5],
            score_bins=["0.6-0.7", "0.7-0.8"],
        )
        matrix, emotion_scores, score_bins = heatmap_data.to_matrix()

        assert matrix.shape == (2, 2)
        assert emotion_scores == [3.0, 3.5]
        assert score_bins == ["0.6-0.7", "0.7-0.8"]
        assert matrix[0, 0] == 0.3
        assert matrix[1, 0] == 0.4
        assert matrix[0, 1] == 0.5
        assert matrix[1, 1] == 0.5

    def test_to_matrix_with_missing_cells(self):
        """Test to_matrix with missing cells (NaN values)."""
        cells = [
            HeatmapCell(3.0, "0.6-0.7", 100, 30, 0.3),
        ]
        heatmap_data = HeatmapData(
            cells=cells,
            emotion_scores=[3.0, 3.5],
            score_bins=["0.6-0.7", "0.7-0.8"],
        )
        matrix, emotion_scores, score_bins = heatmap_data.to_matrix()

        assert matrix.shape == (2, 2)
        assert matrix[0, 0] == 0.3
        assert np.isnan(matrix[0, 1])
        assert np.isnan(matrix[1, 0])
        assert np.isnan(matrix[1, 1])


class TestBinModelScore:
    """Tests for bin_model_score function."""

    def test_default_bins_first_interval(self):
        """Test first bin interval (0.0-0.5)."""
        assert bin_model_score(0.0) == "0.0-0.5"
        assert bin_model_score(0.25) == "0.0-0.5"
        assert bin_model_score(0.5) == "0.0-0.5"

    def test_default_bins_second_interval(self):
        """Test second bin interval (0.5-0.6)."""
        assert bin_model_score(0.55) == "0.5-0.6"
        assert bin_model_score(0.6) == "0.5-0.6"

    def test_default_bins_third_interval(self):
        """Test third bin interval (0.6-0.7)."""
        assert bin_model_score(0.65) == "0.6-0.7"
        assert bin_model_score(0.7) == "0.6-0.7"

    def test_default_bins_fourth_interval(self):
        """Test fourth bin interval (0.7-0.8)."""
        assert bin_model_score(0.75) == "0.7-0.8"
        assert bin_model_score(0.8) == "0.7-0.8"

    def test_default_bins_last_interval(self):
        """Test last bin interval (0.8-1.0)."""
        assert bin_model_score(0.85) == "0.8-1.0"
        assert bin_model_score(0.9) == "0.8-1.0"
        assert bin_model_score(1.0) == "0.8-1.0"

    def test_boundary_values(self):
        """Test boundary values between bins."""
        assert bin_model_score(0.5) == "0.0-0.5"
        assert bin_model_score(0.6) == "0.5-0.6"
        assert bin_model_score(0.7) == "0.6-0.7"
        assert bin_model_score(0.8) == "0.7-0.8"

    def test_below_range(self):
        """Test score below minimum range."""
        assert bin_model_score(-0.1) == "0.0-0.5"
        assert bin_model_score(-1.0) == "0.0-0.5"

    def test_above_range(self):
        """Test score above maximum range."""
        assert bin_model_score(1.1) == "0.8-1.0"
        assert bin_model_score(2.0) == "0.8-1.0"

    def test_custom_bins(self):
        """Test with custom bins."""
        custom_bins = [
            (0.0, 0.3, "low"),
            (0.3, 0.7, "medium"),
            (0.7, 1.0, "high"),
        ]

        assert bin_model_score(0.1, custom_bins) == "low"
        assert bin_model_score(0.5, custom_bins) == "medium"
        assert bin_model_score(0.9, custom_bins) == "high"


class TestCalcSuccessMatrix:
    """Tests for calc_success_matrix function."""

    def test_empty_input(self):
        """Test with empty input returns empty HeatmapData."""
        result = calc_success_matrix([])

        assert isinstance(result, HeatmapData)
        assert result.cells == []
        assert result.emotion_scores == []
        assert result.score_bins == []

    def test_single_record(self):
        """Test with single record."""
        records = [
            {"emotion_score": 3.0, "model_score": 0.65, "success": 1},
        ]
        result = calc_success_matrix(records)

        assert len(result.cells) == 1
        assert result.cells[0].emotion_score == 3.0
        assert result.cells[0].score_bin == "0.6-0.7"
        assert result.cells[0].sample_count == 1
        assert result.cells[0].success_count == 1
        assert result.cells[0].success_rate == 1.0

    def test_multiple_records_same_bin(self):
        """Test with multiple records in same bin."""
        records = [
            {"emotion_score": 3.0, "model_score": 0.65, "success": 1},
            {"emotion_score": 3.0, "model_score": 0.68, "success": 1},
            {"emotion_score": 3.0, "model_score": 0.62, "success": 0},
        ]
        result = calc_success_matrix(records)

        assert len(result.cells) == 1
        assert result.cells[0].sample_count == 3
        assert result.cells[0].success_count == 2
        assert result.cells[0].success_rate == pytest.approx(0.6667, rel=0.01)

    def test_multiple_records_different_bins(self):
        """Test with records in different bins."""
        records = [
            {"emotion_score": 3.0, "model_score": 0.65, "success": 1},
            {"emotion_score": 3.0, "model_score": 0.75, "success": 1},
            {"emotion_score": 3.5, "model_score": 0.65, "success": 0},
            {"emotion_score": 3.5, "model_score": 0.75, "success": 1},
        ]
        result = calc_success_matrix(records)

        assert len(result.cells) == 4
        assert sorted(result.emotion_scores) == [3.0, 3.5]

    def test_success_rate_calculation(self):
        """Test success rate calculation accuracy."""
        records = [
            {"emotion_score": 2.5, "model_score": 0.55, "success": 1},
            {"emotion_score": 2.5, "model_score": 0.58, "success": 1},
            {"emotion_score": 2.5, "model_score": 0.52, "success": 0},
            {"emotion_score": 2.5, "model_score": 0.59, "success": 0},
        ]
        result = calc_success_matrix(records)

        assert len(result.cells) == 1
        assert result.cells[0].sample_count == 4
        assert result.cells[0].success_count == 2
        assert result.cells[0].success_rate == 0.5

    def test_custom_score_bins(self):
        """Test with custom score_bins parameter."""
        records = [
            {"emotion_score": 3.0, "model_score": 0.65, "success": 1},
        ]
        custom_bins = ["low", "medium", "high"]
        result = calc_success_matrix(records, score_bins=custom_bins)

        assert result.score_bins == custom_bins

    def test_emotion_scores_sorted(self):
        """Test that emotion_scores are sorted."""
        records = [
            {"emotion_score": 4.0, "model_score": 0.65, "success": 1},
            {"emotion_score": 2.0, "model_score": 0.65, "success": 1},
            {"emotion_score": 3.0, "model_score": 0.65, "success": 1},
        ]
        result = calc_success_matrix(records)

        assert result.emotion_scores == [2.0, 3.0, 4.0]

    def test_precomputed_score_bin(self):
        """Test with precomputed score_bin in records."""
        records = [
            {"emotion_score": 3.0, "model_score": 0.65, "success": 1, "score_bin": "custom"},
        ]
        result = calc_success_matrix(records)

        assert result.cells[0].score_bin == "custom"

    def test_default_score_bins_structure(self):
        """Test that default score bins are included in result."""
        records = [
            {"emotion_score": 3.0, "model_score": 0.65, "success": 1},
        ]
        result = calc_success_matrix(records)

        expected_bins = [b[2] for b in DEFAULT_SCORE_BINS]
        assert result.score_bins == expected_bins
