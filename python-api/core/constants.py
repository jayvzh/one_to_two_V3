"""Core constants and validation helpers.

This module contains:
- SchemaError: Exception for schema validation failures
- validate_required_columns: DataFrame column validation function
- Business constants: Emotion scoring thresholds, board height thresholds, trade decision thresholds

Design Principles:
- Pure domain logic with no external dependencies
- No data fetching, caching, or IO
"""
from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

# ==============================================================================
# 情绪评分阈值常量
# 用于评估市场情绪强度，基于一进二成功率计算情绪分数
# ==============================================================================
SUCCESS_RATE_HIGH = 0.28  # 成功率>=28%得2分，表示市场情绪强势
SUCCESS_RATE_MID = 0.24   # 成功率>=24%得1分，表示市场情绪中性

# ==============================================================================
# 连板高度阈值常量
# 用于评估连板股票的高度得分，连板高度越高表示市场接力情绪越强
# ==============================================================================
BOARD_HEIGHT_HIGH = 4     # 连板高度>=4得1分，表示强势接力
BOARD_HEIGHT_MID = 3      # 连板高度==3得0.5分，表示中等接力

# ==============================================================================
# 交易决策阈值常量
# 用于判断市场情绪状态，辅助交易决策
# ==============================================================================
EMOTION_STRONG = 3.0      # 情绪分数>=3为强势市场，可积极做多
EMOTION_NEUTRAL = 2.0     # 情绪分数>=2为中性市场，谨慎参与


class SchemaError(ValueError):
    """Raised when dataframe schema does not meet minimal requirements."""


class DataValidationError(Exception):
    """数据验证错误，用于数据格式、内容验证失败时抛出。"""

    def __init__(self, message: str = "数据验证失败"):
        self.message = message
        super().__init__(self.message)


class InsufficientDataError(Exception):
    """数据不足错误，用于训练数据、缓存数据不足时抛出。"""

    def __init__(self, message: str = "数据不足"):
        self.message = message
        super().__init__(self.message)


class ModelNotTrainedError(Exception):
    """模型未训练错误，用于模型未训练就进行预测时抛出。"""

    def __init__(self, message: str = "模型尚未训练"):
        self.message = message
        super().__init__(self.message)


class CacheError(Exception):
    """缓存错误，用于缓存读写失败时抛出。"""

    def __init__(self, message: str = "缓存操作失败"):
        self.message = message
        super().__init__(self.message)


def validate_required_columns(df: pd.DataFrame, required: Iterable[str], context: str) -> None:
    """Validate that DataFrame contains all required columns.
    
    Args:
        df: DataFrame to validate
        required: Iterable of required column names
        context: Context string for error message
        
    Raises:
        SchemaError: If any required columns are missing
    """
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise SchemaError(f"{context} 缺少必要列: {missing}")
