"""Report generation module (pipeline layer).

This module contains:
- DailyResult: Structured data for daily report
- BacktestResult: Structured data for backtest report
- HeatmapResult: Structured data for heatmap report
- generate_daily_html: Generate HTML daily report
- generate_backtest_html: Generate HTML backtest report
- generate_heatmap_html: Generate HTML heatmap report

Design Principles:
- Only responsible for HTML rendering
- No business logic implementation
- No data fetching (receives structured data)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from ml.trainer import ModelMeta


@dataclass
class StockScore:
    """Stock with model score."""
    symbol: str
    name: str
    model_score: float
    turnover: float
    circ_mv: float


@dataclass
class FirstBoardStats:
    """First board statistics."""
    count: int
    avg_turnover: float
    avg_circ_mv: float
    early_seal_ratio: float


@dataclass
class ModelScoreStats:
    """Model score statistics item."""
    metric: str
    value: float
    description: str


@dataclass
class EmotionLayerStats:
    """Statistics for a single emotion layer."""
    emotion_score: float
    sample_count: int
    success_count: int
    success_rate: float
    allow_trade: bool


@dataclass
class DailyResult:
    """Structured result for daily report.
    
    This is the data contract between daily.py and report.py.
    daily.py produces this, report.py consumes it.
    """
    date: str
    emotion_score: float
    emotion_level: str
    emotion_detail: dict[str, float]
    trade_status: str
    allow_trade: bool
    stocks: list[StockScore] = field(default_factory=list)
    first_board_stats: FirstBoardStats | None = None
    model_score_stats: list[ModelScoreStats] = field(default_factory=list)
    model_meta: ModelMeta | None = None
    is_intraday: bool = False


@dataclass
class BacktestResult:
    """Structured result for backtest report.
    
    This is the data contract between backtest_emotion.py and report.py.
    """
    start_date: str
    end_date: str
    total_samples: int
    total_days: int
    layer_stats: list[EmotionLayerStats] = field(default_factory=list)
    model_meta: ModelMeta | None = None
    duration_seconds: float = 0.0


def generate_daily_html(result: DailyResult, output_path: str) -> str:
    """Generate HTML daily report.
    
    Args:
        result: DailyResult with all report data
        output_path: Output file path (e.g., reports/daily_report_20260117.html)
        
    Returns:
        Path to generated HTML file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("daily_report.html")

    report_date = datetime.strptime(result.date, "%Y%m%d").strftime("%Y-%m-%d")

    stocks_data = [
        {
            "symbol": s.symbol,
            "name": s.name,
            "model_score": s.model_score,
            "turnover": s.turnover,
            "circ_mv": s.circ_mv,
        }
        for s in result.stocks
    ]

    first_board_count = 0
    first_board_avg_turnover = 0.0
    first_board_avg_mv = 0.0
    first_board_early_ratio = 0.0

    if result.first_board_stats:
        fb = result.first_board_stats
        first_board_count = fb.count
        first_board_avg_turnover = fb.avg_turnover
        first_board_avg_mv = fb.avg_circ_mv
        first_board_early_ratio = fb.early_seal_ratio

    model_score_stats_data = [
        {
            "metric": s.metric,
            "value": s.value,
            "description": s.description,
        }
        for s in result.model_score_stats
    ]

    model_meta_dict = None
    if result.model_meta:
        model_meta_dict = {
            "version": result.model_meta.version,
            "sample_size": result.model_meta.sample_size,
            "train_start": result.model_meta.train_start,
            "train_end": result.model_meta.train_end,
            "base_success_rate": result.model_meta.base_success_rate,
        }

    emotion_dict = {
        "score": result.emotion_score,
        "level": result.emotion_level,
        "detail": result.emotion_detail,
    }

    template_data = {
        "date": report_date,
        "emotion": emotion_dict,
        "trade_status": result.trade_status,
        "stocks": stocks_data,
        "first_board_count": first_board_count,
        "first_board_avg_turnover": first_board_avg_turnover,
        "first_board_avg_mv": first_board_avg_mv,
        "first_board_early_ratio": first_board_early_ratio,
        "model_score_stats": model_score_stats_data,
        "model_meta": model_meta_dict,
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_intraday": result.is_intraday,
    }

    html = template.render(template_data)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    return str(output_file)


def generate_heatmap_html(result, output_path: str) -> str:
    """Generate HTML heatmap report.
    
    Args:
        result: HeatmapResult with all heatmap data
        output_path: Output file path (e.g., reports/heatmap_report.html)
        
    Returns:
        Path to generated HTML file
    """

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("heatmap_report.html")

    start_date = datetime.strptime(result.start_date, "%Y%m%d").strftime("%Y-%m-%d")
    end_date = datetime.strptime(result.end_date, "%Y%m%d").strftime("%Y-%m-%d")

    heatmap_cells = []
    if result.heatmap_data:
        heatmap_cells = [
            {
                "emotion_score": c.emotion_score,
                "score_bin": c.score_bin,
                "sample_count": c.sample_count,
                "success_count": c.success_count,
                "success_rate": c.success_rate,
            }
            for c in result.heatmap_data.cells
        ]

    model_meta_dict = None
    if result.model_meta:
        model_meta_dict = {
            "version": result.model_meta.version,
            "sample_size": result.model_meta.sample_size,
            "train_start": result.model_meta.train_start,
            "train_end": result.model_meta.train_end,
            "base_success_rate": result.model_meta.base_success_rate,
        }

    duration = result.duration_seconds
    if duration < 60:
        duration_str = f"{duration:.1f}秒"
    elif duration < 3600:
        minutes, seconds = divmod(int(duration), 60)
        duration_str = f"{minutes}分{seconds}秒"
    else:
        hours, remainder = divmod(int(duration), 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours}小时{minutes}分{seconds}秒"

    image_relative_path = ""
    if result.image_path:
        image_path = Path(result.image_path)
        image_relative_path = f"images/{image_path.name}"

    template_data = {
        "start_date": start_date,
        "end_date": end_date,
        "total_samples": result.total_samples,
        "total_days": result.total_days,
        "analysis_base_success_rate": result.analysis_base_success_rate,
        "heatmap_cells": heatmap_cells,
        "model_meta": model_meta_dict,
        "image_path": image_relative_path,
        "duration": duration_str,
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    html = template.render(template_data)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    return str(output_file)


def build_model_score_stats(scores: pd.Series) -> list[ModelScoreStats]:
    """Build model score statistics from score series.
    
    Args:
        scores: Series of model scores
        
    Returns:
        List of ModelScoreStats
    """
    if scores is None or len(scores) == 0:
        return []

    desc = scores.describe()

    metric_descriptions = {
        "count": ("样本数量", "参与评分的首板股票总数"),
        "mean": ("平均值", "所有首板股票的平均模型评分"),
        "std": ("标准差", "评分分布的离散程度，越小越集中"),
        "min": ("最小值", "模型评分的最低值"),
        "25%": ("25分位数", "25%的股票评分低于此值"),
        "50%": ("中位数", "50%的股票评分低于此值，反映中间水平"),
        "75%": ("75分位数", "75%的股票评分低于此值"),
        "max": ("最大值", "模型评分的最高值"),
    }

    stats = []
    for metric, value in desc.items():
        metric_name, description = metric_descriptions.get(metric, (metric, ""))
        stats.append(ModelScoreStats(
            metric=metric_name,
            value=float(value),
            description=description,
        ))

    return stats


def generate_backtest_html(result: BacktestResult, output_path: str) -> str:
    """Generate HTML backtest report.
    
    Args:
        result: BacktestResult with all backtest data
        output_path: Output file path (e.g., reports/backtest_report.html)
        
    Returns:
        Path to generated HTML file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("backtest_report.html")

    start_date = datetime.strptime(result.start_date, "%Y%m%d").strftime("%Y-%m-%d")
    end_date = datetime.strptime(result.end_date, "%Y%m%d").strftime("%Y-%m-%d")

    layer_stats_data = [
        {
            "emotion_score": s.emotion_score,
            "sample_count": s.sample_count,
            "success_count": s.success_count,
            "success_rate": s.success_rate,
            "allow_trade": s.allow_trade,
        }
        for s in result.layer_stats
    ]

    total_success = sum(s.success_count for s in result.layer_stats)
    overall_rate = total_success / result.total_samples if result.total_samples > 0 else 0

    duration = result.duration_seconds
    if duration < 60:
        duration_str = f"{duration:.1f}秒"
    elif duration < 3600:
        minutes, seconds = divmod(int(duration), 60)
        duration_str = f"{minutes}分{seconds}秒"
    else:
        hours, remainder = divmod(int(duration), 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours}小时{minutes}分{seconds}秒"

    template_data = {
        "start_date": start_date,
        "end_date": end_date,
        "total_samples": result.total_samples,
        "total_days": result.total_days,
        "overall_success_rate": overall_rate,
        "layer_stats": layer_stats_data,
        "duration": duration_str,
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    html = template.render(template_data)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    return str(output_file)
