"""Trade rule engine (pure domain layer).

This module contains:
- TradeDecision: Data class for trade decision results
- TradeRuleEngine: Rule engine for converting emotion to trading actions

Design Principles:
- Pure domain logic with no external dependencies
- No data fetching, caching, or IO
- No akshare or data_source dependencies
"""
from dataclasses import dataclass

from .emotion import EmotionResult


@dataclass
class TradeDecision:
    """Trade decision result."""
    allow_trade: bool
    mode: str
    reason: str
    max_positions: int
    remark: str | None = None


class TradeRuleEngine:
    """One-to-two trade rule engine.

    Business Background:
        Trading decisions are based on market emotion scores, which aggregate multiple
        market indicators into a single actionable metric. The emotion score determines
        the trading mode and position sizing for the one-to-two strategy.

        Why emotion score >= 3 allows active participation:
        - Score >= 3 indicates strong market conditions with favorable one-to-two success
          rate (typically >28%), high board height (>=4), and rising limit-up counts
        - Historical backtesting shows that trading in strong emotion environments
          yields significantly higher success rates and lower drawdown risk
        - The combination of high success rate + strong momentum provides a favorable
          risk-reward ratio for aggressive position sizing

        Threshold Selection Rationale:
        - Score >= 3 (Strong): All three dimensions show positive signals, indicating
          optimal trading conditions with high probability of success
        - Score 2-3 (Neutral): Mixed signals, selective participation with reduced
          position size to manage risk
        - Score < 2 (Weak): Unfavorable conditions with low success probability,
          avoid trading to preserve capital

    Rules from project design document 3.2:

    Emotion score >= 3:
        - Strong environment
        - Allow active participation in one-to-two

    Emotion score 2 ~ 3:
        - Neutral environment
        - Selective participation, control position

    Emotion score < 2:
        - Weak environment
        - No participation in one-to-two
    """

    def decide(self, emotion: EmotionResult) -> TradeDecision:
        """Make trade decision based on emotion result.
        
        Args:
            emotion: EmotionResult from MarketEmotionAnalyzer
            
        Returns:
            TradeDecision with trading mode and parameters
        """
        score = emotion.score

        if score >= 3:
            return TradeDecision(
                allow_trade=True,
                mode="aggressive",
                max_positions=5,
                reason="情绪强势，允许积极参与一进二",
            )

        if score >= 2:
            return TradeDecision(
                allow_trade=True,
                mode="selective",
                max_positions=2,
                reason="情绪中性，精选参与一进二",
            )

        return TradeDecision(
            allow_trade=False,
            mode="observe",
            max_positions=0,
            reason="情绪偏弱，放弃一进二交易",
        )
