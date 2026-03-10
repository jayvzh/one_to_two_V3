"""Pipeline module - Orchestration layer.

This module contains:
- rolling: Rolling training pipeline
- daily: Daily scoring pipeline
- backtest_emotion: Emotion layer backtest pipeline
- report: Report generation

Usage:
    from src.pipeline.daily import DailyScorer
    from src.pipeline.rolling import RollingTrainPipeline, RollingWindowConfig
"""

__all__ = [
    "DailyScorer",
    "RollingTrainPipeline",
    "RollingWindowConfig",
]
