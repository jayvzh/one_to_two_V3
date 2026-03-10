"""Tests for core/emotion.py module."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


from core.emotion import EmotionMetrics, EmotionResult, MarketEmotionAnalyzer


class TestMarketEmotionAnalyzer:
    """Tests for MarketEmotionAnalyzer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = MarketEmotionAnalyzer()

    def test_score_strong_emotion(self):
        """Test strong emotion (score >= 3)."""
        metrics = EmotionMetrics(
            success_rate=0.30,
            max_board_height=5,
            zt_count_today=100,
            zt_count_yesterday=80,
        )
        result = self.analyzer.score(metrics)

        assert isinstance(result, EmotionResult)
        assert result.score >= 3
        assert result.level == "strong"
        assert result.allow_trade is True

    def test_score_neutral_emotion(self):
        """Test neutral emotion (score 2-3)."""
        metrics = EmotionMetrics(
            success_rate=0.25,
            max_board_height=3,
            zt_count_today=80,
            zt_count_yesterday=80,
        )
        result = self.analyzer.score(metrics)

        assert 2 <= result.score < 3
        assert result.level == "neutral"
        assert result.allow_trade is True

    def test_score_weak_emotion(self):
        """Test weak emotion (score < 2)."""
        metrics = EmotionMetrics(
            success_rate=0.20,
            max_board_height=2,
            zt_count_today=50,
            zt_count_yesterday=80,
        )
        result = self.analyzer.score(metrics)

        assert result.score < 2
        assert result.level == "weak"
        assert result.allow_trade is False

    def test_success_rate_scoring(self):
        """Test success rate scoring logic."""
        metrics_high = EmotionMetrics(
            success_rate=0.30,
            max_board_height=0,
            zt_count_today=0,
            zt_count_yesterday=0,
        )
        result_high = self.analyzer.score(metrics_high)
        assert result_high.detail["success_rate_score"] == 2.0

        metrics_mid = EmotionMetrics(
            success_rate=0.26,
            max_board_height=0,
            zt_count_today=0,
            zt_count_yesterday=0,
        )
        result_mid = self.analyzer.score(metrics_mid)
        assert result_mid.detail["success_rate_score"] == 1.0

        metrics_low = EmotionMetrics(
            success_rate=0.20,
            max_board_height=0,
            zt_count_today=0,
            zt_count_yesterday=0,
        )
        result_low = self.analyzer.score(metrics_low)
        assert result_low.detail["success_rate_score"] == 0.0

    def test_board_height_scoring(self):
        """Test board height scoring logic."""
        metrics_high = EmotionMetrics(
            success_rate=0.30,
            max_board_height=5,
            zt_count_today=0,
            zt_count_yesterday=0,
        )
        result_high = self.analyzer.score(metrics_high)
        assert result_high.detail["height_score"] == 1.0

        metrics_mid = EmotionMetrics(
            success_rate=0.30,
            max_board_height=3,
            zt_count_today=0,
            zt_count_yesterday=0,
        )
        result_mid = self.analyzer.score(metrics_mid)
        assert result_mid.detail["height_score"] == 0.5

        metrics_low = EmotionMetrics(
            success_rate=0.30,
            max_board_height=2,
            zt_count_today=0,
            zt_count_yesterday=0,
        )
        result_low = self.analyzer.score(metrics_low)
        assert result_low.detail["height_score"] == 0.0

    def test_zt_trend_scoring(self):
        """Test limit-up count trend scoring logic."""
        metrics_up = EmotionMetrics(
            success_rate=0.30,
            max_board_height=5,
            zt_count_today=100,
            zt_count_yesterday=80,
        )
        result_up = self.analyzer.score(metrics_up)
        assert result_up.detail["zt_trend_score"] == 1.0

        metrics_flat = EmotionMetrics(
            success_rate=0.30,
            max_board_height=5,
            zt_count_today=80,
            zt_count_yesterday=80,
        )
        result_flat = self.analyzer.score(metrics_flat)
        assert result_flat.detail["zt_trend_score"] == 0.5

        metrics_down = EmotionMetrics(
            success_rate=0.30,
            max_board_height=5,
            zt_count_today=50,
            zt_count_yesterday=80,
        )
        result_down = self.analyzer.score(metrics_down)
        assert result_down.detail["zt_trend_score"] == 0.0

    def test_detail_contains_all_scores(self):
        """Test that detail contains all score components."""
        metrics = EmotionMetrics(
            success_rate=0.30,
            max_board_height=5,
            zt_count_today=100,
            zt_count_yesterday=80,
        )
        result = self.analyzer.score(metrics)

        assert "success_rate_score" in result.detail
        assert "height_score" in result.detail
        assert "zt_trend_score" in result.detail
