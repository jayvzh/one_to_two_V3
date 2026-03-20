"""Market emotion analysis (pure domain layer).

This module contains:
- EmotionMetrics: Data class for emotion metrics input
- EmotionResult: Data class for emotion analysis result
- MarketEmotionAnalyzer: Emotion scoring engine

Design Principles:
- Pure domain logic with no external dependencies
- No data fetching, caching, or IO
- No akshare or data_source dependencies
"""
from dataclasses import dataclass


@dataclass
class EmotionMetrics:
    """Input metrics for emotion analysis."""
    success_rate: float
    max_board_height: int
    zt_count_today: int
    zt_count_yesterday: int


@dataclass
class EmotionResult:
    """Result of market emotion analysis."""
    score: float
    level: str
    allow_trade: bool
    detail: dict[str, float]


class MarketEmotionAnalyzer:
    """Market emotion scoring engine.

    Business Background:
        Market emotion reflects the overall trading environment for one-to-two strategy.
        Strong emotion indicates favorable conditions for limit-up continuation,
        while weak emotion suggests higher risk of failed breakouts.

        Why these three dimensions were chosen:
        1. Success Rate: Core indicator of one-to-two profitability. Historical data shows
           that in strong markets, one-to-two success rate typically exceeds 28%, while
           in weak markets it falls below 24%. These thresholds are derived from extensive
           backtesting across different market cycles.

        2. Board Height (Max consecutive limit-ups): Reflects market risk appetite.
           Higher board heights indicate stronger speculative sentiment and greater
           willingness to chase momentum stocks.

        3. Limit-up Count Trend: Measures market momentum direction. Rising limit-up
           counts suggest increasing participation and improving sentiment, while
           declining counts signal fading interest.

        Threshold Selection Rationale:
        - 28% success rate threshold: Based on historical statistics, one-to-two success
          rate in strong markets typically exceeds 28%, making this a reliable indicator
          of favorable trading conditions.
        - 24% success rate threshold: In weak markets, success rate drops below 24%,
          indicating elevated risk and unfavorable trading environment.

    Scoring rules (from design document):
    1. Success rate scoring
       - >= 28% : +2
       - 24% ~ 28% : +1
       - < 24% : +0

    2. Board height scoring
       - >= 4 : +1
       - == 3 : +0.5
       - < 3 : +0

    3. Limit-up count trend scoring
       - Today > Yesterday : +1
       - Today ~= Yesterday : +0.5
       - Today < Yesterday : +0
    """

    def score(self, metrics: EmotionMetrics) -> EmotionResult:
        """Calculate emotion score from metrics.

        Args:
            metrics: EmotionMetrics with market data

        Returns:
            EmotionResult with score and trading decision
        """
        score = 0.0
        detail = {}

        # 成功率评分：核心指标，反映一进二策略的盈利能力
        # 强势市场成功率通常超过28%，弱势市场低于24%
        if metrics.success_rate >= 0.28:
            s = 2.0
        elif metrics.success_rate >= 0.24:
            s = 1.0
        else:
            s = 0.0
        score += s
        detail['success_rate_score'] = s

        # 板块高度评分：反映市场风险偏好和投机情绪
        # 高度>=4表示追涨意愿强，高度==3为中性，高度<3为弱势
        if metrics.max_board_height >= 4:
            s = 1.0
        elif metrics.max_board_height == 3:
            s = 0.5
        else:
            s = 0.0
        score += s
        detail['height_score'] = s

        # 涨停趋势评分：衡量市场动量方向
        # 今日涨停数>昨日表示参与度提升，相等为平稳，<昨日为情绪消退
        if metrics.zt_count_today > metrics.zt_count_yesterday:
            s = 1.0
        elif metrics.zt_count_today == metrics.zt_count_yesterday:
            s = 0.5
        else:
            s = 0.0
        score += s
        detail['zt_trend_score'] = s

        if score >= 3:
            level = 'strong'
            allow_trade = True
        elif score >= 2:
            level = 'neutral'
            allow_trade = True
        else:
            level = 'weak'
            allow_trade = False

        return EmotionResult(
            score=score,
            level=level,
            allow_trade=allow_trade,
            detail=detail
        )
