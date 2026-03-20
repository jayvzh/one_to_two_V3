"""Validation test script for model evaluation.

This script performs validation tests to verify the correctness of model evaluation:
1. Random model baseline test
2. Reverse sorting test (lowest score Top5)
3. Daily Top5 detail output

Usage:
    python scripts/validation_test.py
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from data.trade_calendar import TradingCalendar
from data.ak import AkshareDataSource, IndexRepository, ZtRepository
from data.prepare import build_training_data
from core.scoring import calc_one_to_two
from core.features import MarketFeatureBuilder, StockFeatureBuilder
from core.label import OneToTwoLabelBuilder
from ml.trainer import OneToTwoDatasetBuilder, OneToTwoPredictor
from ml.evaluator import ModelEvaluator, EvaluationMetrics


def run_validation_test(
    base_dir: Path,
    train_start: str,
    train_end: str,
    test_start: str,
    test_end: str,
    verbose: bool = True,
) -> dict:
    """Run validation tests for model evaluation.

    Returns:
        Dictionary with test results
    """
    cache_dir = base_dir / "datasets" / "cache"

    calendar = TradingCalendar(cache_dir=cache_dir)
