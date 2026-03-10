"""Tests for core/rules.py module."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


from core.emotion import EmotionResult
from core.rules import TradeDecision, TradeRuleEngine


class TestTradeRuleEngine:
    """Tests for TradeRuleEngine class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = TradeRuleEngine()

    def test_decide_aggressive(self):
        """Test aggressive mode decision (score >= 3)."""
        emotion = EmotionResult(
            score=3.5,
            level="strong",
            allow_trade=True,
            detail={},
        )
        decision = self.engine.decide(emotion)

        assert isinstance(decision, TradeDecision)
        assert decision.allow_trade is True
        assert decision.mode == "aggressive"
        assert decision.max_positions == 5

    def test_decide_selective(self):
        """Test selective mode decision (score 2-3)."""
        emotion = EmotionResult(
            score=2.5,
            level="neutral",
            allow_trade=True,
            detail={},
        )
        decision = self.engine.decide(emotion)

        assert decision.allow_trade is True
        assert decision.mode == "selective"
        assert decision.max_positions == 2

    def test_decide_observe(self):
        """Test observe mode decision (score < 2)."""
        emotion = EmotionResult(
            score=1.5,
            level="weak",
            allow_trade=False,
            detail={},
        )
        decision = self.engine.decide(emotion)

        assert decision.allow_trade is False
        assert decision.mode == "observe"
        assert decision.max_positions == 0

    def test_boundary_score_3(self):
        """Test boundary condition at score = 3."""
        emotion = EmotionResult(
            score=3.0,
            level="strong",
            allow_trade=True,
            detail={},
        )
        decision = self.engine.decide(emotion)

        assert decision.mode == "aggressive"

    def test_boundary_score_2(self):
        """Test boundary condition at score = 2."""
        emotion = EmotionResult(
            score=2.0,
            level="neutral",
            allow_trade=True,
            detail={},
        )
        decision = self.engine.decide(emotion)

        assert decision.mode == "selective"

    def test_decision_has_reason(self):
        """Test that decision contains reason string."""
        emotion = EmotionResult(
            score=3.0,
            level="strong",
            allow_trade=True,
            detail={},
        )
        decision = self.engine.decide(emotion)

        assert isinstance(decision.reason, str)
        assert len(decision.reason) > 0
