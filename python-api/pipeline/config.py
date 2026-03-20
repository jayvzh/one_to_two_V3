"""Pipeline-level runtime defaults.

Loads editable defaults from ``config/pipeline_defaults.json`` so users can tune
common date windows and model-selection behavior without touching code.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProductionTrainDefaults:
    months: int = 6
    cache_check_months: int = 6


@dataclass(frozen=True)
class DailyDefaults:
    cache_check_months: int = 2
    model_filename: str = "model_latest.joblib"


@dataclass(frozen=True)
class EmotionBacktestDefaults:
    months: int = 6
    window_days: int = 64
    cache_check_months: int = 3


@dataclass(frozen=True)
class RollingDefaults:
    train_months: int = 6
    test_months: int = 1
    sensitivity_train_months: tuple[int, ...] = (2, 3, 4, 6)


@dataclass(frozen=True)
class HeatmapDefaults:
    months: int = 1
    model_filename: str = "model_latest.joblib"


@dataclass(frozen=True)
class PipelineDefaults:
    production_train: ProductionTrainDefaults = ProductionTrainDefaults()
    daily: DailyDefaults = DailyDefaults()
    emotion_backtest: EmotionBacktestDefaults = EmotionBacktestDefaults()
    rolling: RollingDefaults = RollingDefaults()
    heatmap: HeatmapDefaults = HeatmapDefaults()


def _as_int(raw: Any, fallback: int) -> int:
    try:
        value = int(raw)
        return value if value > 0 else fallback
    except (TypeError, ValueError):
        return fallback


def _as_str(raw: Any, fallback: str) -> str:
    value = str(raw).strip() if raw is not None else ""
    return value or fallback


def _as_positive_int_tuple(raw: Any, fallback: tuple[int, ...]) -> tuple[int, ...]:
    if not isinstance(raw, list):
        return fallback

    values: list[int] = []
    for item in raw:
        try:
            num = int(item)
            if num > 0:
                values.append(num)
        except (TypeError, ValueError):
            continue

    return tuple(values) if values else fallback


def load_pipeline_defaults(base_dir: Path | None = None) -> PipelineDefaults:
    """Load pipeline defaults from ``pipeline_defaults.json``.

    Falls back to code defaults when the config file is missing or malformed.
    """
    base = base_dir or Path(".")
    config_path = base / "pipeline_defaults.json"

    if not config_path.exists():
        return PipelineDefaults()

    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return PipelineDefaults()

    production = data.get("production_train", {})
    daily = data.get("daily", {})
    emotion = data.get("emotion_backtest", {})
    rolling = data.get("rolling", {})
    heatmap = data.get("heatmap", {})

    return PipelineDefaults(
        production_train=ProductionTrainDefaults(
            months=_as_int(production.get("months"), ProductionTrainDefaults.months),
            cache_check_months=_as_int(production.get("cache_check_months"), ProductionTrainDefaults.cache_check_months),
        ),
        daily=DailyDefaults(
            cache_check_months=_as_int(daily.get("cache_check_months"), DailyDefaults.cache_check_months),
            model_filename=_as_str(daily.get("model_filename"), DailyDefaults.model_filename),
        ),
        emotion_backtest=EmotionBacktestDefaults(
            months=_as_int(emotion.get("months"), EmotionBacktestDefaults.months),
            window_days=_as_int(emotion.get("window_days"), EmotionBacktestDefaults.window_days),
            cache_check_months=_as_int(emotion.get("cache_check_months"), EmotionBacktestDefaults.cache_check_months),
        ),
        rolling=RollingDefaults(
            train_months=_as_int(rolling.get("train_months"), RollingDefaults.train_months),
            test_months=_as_int(rolling.get("test_months"), RollingDefaults.test_months),
            sensitivity_train_months=_as_positive_int_tuple(
                rolling.get("sensitivity_train_months"),
                RollingDefaults.sensitivity_train_months,
            ),
        ),
        heatmap=HeatmapDefaults(
            months=_as_int(heatmap.get("months"), HeatmapDefaults.months),
            model_filename=_as_str(heatmap.get("model_filename"), HeatmapDefaults.model_filename),
        ),
    )
