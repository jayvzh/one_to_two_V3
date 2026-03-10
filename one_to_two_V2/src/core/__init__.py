"""Core module - Pure strategy logic.

This module contains:
- constants: Schema validation helpers
- scoring: One-to-two calculation logic
- rules: Trade rule engine
- emotion: Market emotion analysis
- features: Feature engineering
- label: Label builder
"""
from .constants import (
    BOARD_HEIGHT_HIGH,
    BOARD_HEIGHT_MID,
    EMOTION_NEUTRAL,
    EMOTION_STRONG,
    SUCCESS_RATE_HIGH,
    SUCCESS_RATE_MID,
    CacheError,
    DataValidationError,
    InsufficientDataError,
    ModelNotTrainedError,
    SchemaError,
    validate_required_columns,
)
from .emotion import EmotionMetrics, EmotionResult, MarketEmotionAnalyzer
from .features import MarketFeatureBuilder, MarketFeatures, StockFeatureBuilder
from .label import OneToTwoLabelBuilder
from .rules import TradeDecision, TradeRuleEngine
from .scoring import OneToTwoResult, calc_one_to_two, detect_first_board, detect_second_board

__all__ = [
    "SchemaError",
    "validate_required_columns",
    "SUCCESS_RATE_HIGH",
    "SUCCESS_RATE_MID",
    "BOARD_HEIGHT_HIGH",
    "BOARD_HEIGHT_MID",
    "EMOTION_STRONG",
    "EMOTION_NEUTRAL",
    "OneToTwoResult",
    "detect_first_board",
    "detect_second_board",
    "calc_one_to_two",
    "TradeDecision",
    "TradeRuleEngine",
    "EmotionMetrics",
    "EmotionResult",
    "MarketEmotionAnalyzer",
    "MarketFeatures",
    "StockFeatureBuilder",
    "MarketFeatureBuilder",
    "OneToTwoLabelBuilder",
]
