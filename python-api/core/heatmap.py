"""Heatmap core logic (pure domain layer).

This module contains:
- HeatmapCell: Single cell data for heatmap
- HeatmapData: Complete heatmap data structure
- bin_model_score: Model score binning function
- calc_success_matrix: Success rate matrix calculation
- HeatmapPlotter: Heatmap plotting with matplotlib

Design Principles:
- Pure domain logic with no external dependencies
- No data fetching, caching, or IO
- matplotlib is used only in HeatmapPlotter for visualization
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_SCORE_BINS = [
    (0.0, 0.5, "0.0-0.5"),
    (0.5, 0.6, "0.5-0.6"),
    (0.6, 0.7, "0.6-0.7"),
    (0.7, 0.8, "0.7-0.8"),
    (0.8, 1.0, "0.8-1.0"),
]


@dataclass
class HeatmapCell:
    """Single cell data for heatmap."""
    emotion_score: float
    score_bin: str
    sample_count: int
    success_count: int
    success_rate: float


@dataclass
class HeatmapData:
    """Complete heatmap data structure."""
    cells: list[HeatmapCell] = field(default_factory=list)
    emotion_scores: list[float] = field(default_factory=list)
    score_bins: list[str] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame for analysis."""
        if not self.cells:
            return pd.DataFrame()

        data = [
            {
                "emotion_score": c.emotion_score,
                "score_bin": c.score_bin,
                "sample_count": c.sample_count,
                "success_count": c.success_count,
                "success_rate": c.success_rate,
            }
            for c in self.cells
        ]
        return pd.DataFrame(data)

    def to_matrix(self) -> tuple[np.ndarray, list[float], list[str]]:
        """Convert to matrix format for plotting.
        
        Returns:
            Tuple of (matrix, emotion_scores, score_bins)
        """
        if not self.cells:
            return np.array([]), [], []

        df = self.to_dataframe()

        pivot = df.pivot(
            index="emotion_score",
            columns="score_bin",
            values="success_rate",
        )

        pivot = pivot.reindex(
            index=self.emotion_scores,
            columns=self.score_bins,
        )

        return pivot.values, self.emotion_scores, self.score_bins


def bin_model_score(
    score: float,
    bins: list[tuple[float, float, str]] | None = None,
) -> str:
    """Bin model score into discrete categories.
    
    Args:
        score: Model score (0.0 to 1.0)
        bins: List of (low, high, label) tuples
        
    Returns:
        Bin label string
    """
    if bins is None:
        bins = DEFAULT_SCORE_BINS

    for low, high, label in bins:
        if low <= score <= high:
            return label

    if score < bins[0][0]:
        return bins[0][2]
    return bins[-1][2]


def calc_success_matrix(
    records: list[dict],
    emotion_scores: list[float] | None = None,
    score_bins: list[str] | None = None,
) -> HeatmapData:
    """Calculate success rate matrix from records.
    
    Args:
        records: List of dicts with keys: emotion_score, model_score, success
        emotion_scores: List of emotion scores to include (optional)
        score_bins: List of score bin labels (optional)
        
    Returns:
        HeatmapData with success rate matrix
    """
    if not records:
        return HeatmapData()

    df = pd.DataFrame(records)

    if "score_bin" not in df.columns:
        df["score_bin"] = df["model_score"].apply(bin_model_score)

    grouped = df.groupby(
        ["emotion_score", "score_bin"],
        observed=True,
    ).agg(
        sample_count=("success", "count"),
        success_count=("success", "sum"),
    ).reset_index()

    grouped["success_rate"] = grouped["success_count"] / grouped["sample_count"]
    grouped["success_rate"] = grouped["success_rate"].round(4)

    cells = []
    for _, row in grouped.iterrows():
        cells.append(HeatmapCell(
            emotion_score=row["emotion_score"],
            score_bin=row["score_bin"],
            sample_count=int(row["sample_count"]),
            success_count=int(row["success_count"]),
            success_rate=row["success_rate"],
        ))

    unique_emotions = sorted(df["emotion_score"].unique())
    unique_bins = [b[2] for b in DEFAULT_SCORE_BINS]

    if score_bins:
        unique_bins = score_bins

    return HeatmapData(
        cells=cells,
        emotion_scores=list(unique_emotions),
        score_bins=unique_bins,
    )


class HeatmapPlotter:
    """Heatmap plotting with matplotlib.
    
    Usage:
        plotter = HeatmapPlotter()
        plotter.plot(heatmap_data, "output.png")
    """

    def __init__(
        self,
        figsize: tuple[int, int] = (12, 8),
        dpi: int = 150,
        cmap: str = "YlGnBu",
    ):
        """Initialize plotter.
        
        Args:
            figsize: Figure size (width, height)
            dpi: Dots per inch
            cmap: Colormap name
        """
        self.figsize = figsize
        self.dpi = dpi
        self.cmap = cmap
        self._plt = None
        self._np = None

    def _init_matplotlib(self):
        """Lazy import matplotlib."""
        if self._plt is None:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            self._plt = plt

            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False

    def plot(
        self,
        data: HeatmapData,
        output_path: str,
        title: str | None = None,
        model_meta: dict | None = None,
        analysis_range: tuple[str, str] | None = None,
        analysis_sample_count: int = 0,
        analysis_base_success_rate: float = 0.0,
    ) -> str:
        """Generate heatmap image.
        
        Args:
            data: HeatmapData with success rate matrix
            output_path: Output file path
            title: Optional title
            model_meta: Optional model metadata for title
            analysis_range: Optional tuple of (start_date, end_date) for analysis range
            analysis_sample_count: Sample count for analysis range
            analysis_base_success_rate: Base success rate for analysis range
            
        Returns:
            Path to generated image
        """
        self._init_matplotlib()

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        matrix, emotion_scores, score_bins = data.to_matrix()

        if matrix.size == 0:
            raise ValueError("No data to plot")

        fig, ax = self._plt.subplots(figsize=self.figsize)

        im = ax.imshow(matrix, cmap=self.cmap, aspect="auto", vmin=0, vmax=0.5)

        ax.set_xticks(range(len(score_bins)))
        ax.set_xticklabels(score_bins, rotation=45, ha="right", fontsize=10)

        ax.set_yticks(range(len(emotion_scores)))
        ax.set_yticklabels([str(e) for e in emotion_scores], fontsize=10)

        cbar = fig.colorbar(im, ax=ax, label="一进二成功率")
        cbar.ax.tick_params(labelsize=10)

        if title:
            ax.set_title(title, fontsize=12, fontweight="bold", pad=20)
        elif model_meta:
            title = self._build_title(model_meta, analysis_range, analysis_sample_count, analysis_base_success_rate)
            ax.set_title(title, fontsize=11, fontweight="bold", pad=15)
        else:
            default_title = "情绪 × 模型分数 一进二成功率热力图"
            if analysis_range:
                default_title += f" | 分析区间: {analysis_range[0]} ~ {analysis_range[1]}"
            ax.set_title(default_title, fontsize=12, fontweight="bold")

        ax.set_xlabel("模型分数区间", fontsize=11)
        ax.set_ylabel("市场情绪", fontsize=11)

        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                val = matrix[i, j]
                if not math.isnan(val):
                    text_color = "white" if val > 0.25 else "black"
                    ax.text(
                        j, i, f"{val:.1%}",
                        ha="center", va="center",
                        fontsize=9, fontweight="bold",
                        color=text_color,
                    )

        fig.tight_layout()
        fig.savefig(str(output_file), dpi=self.dpi, bbox_inches="tight")
        self._plt.close(fig)

        return str(output_file)

    def _build_title(
        self,
        model_meta: dict,
        analysis_range: tuple[str, str] | None = None,
        analysis_sample_count: int = 0,
        analysis_base_success_rate: float = 0.0,
    ) -> str:
        """Build title from model metadata.
        
        Args:
            model_meta: Model metadata dict
            analysis_range: Optional tuple of (start_date, end_date) for analysis range
            analysis_sample_count: Sample count for analysis range
            analysis_base_success_rate: Base success rate for analysis range
        """
        lines = []
        lines.append("情绪 × 模型分数 一进二成功率热力图")
        
        sub_parts = []
        if analysis_range:
            sub_parts.append(f"分析区间: {analysis_range[0]} ~ {analysis_range[1]}")
        
        if analysis_sample_count > 0:
            sub_parts.append(f"样本量: {analysis_sample_count}")
        
        if analysis_base_success_rate > 0:
            sub_parts.append(f"基础胜率: {analysis_base_success_rate:.1%}")
        
        if sub_parts:
            lines.append(" | ".join(sub_parts))
        
        if "version" in model_meta:
            version_str = f"模型版本: {model_meta['version']}"
            if "train_start" in model_meta and "train_end" in model_meta:
                version_str += f" (训练: {model_meta['train_start']} ~ {model_meta['train_end']})"
            lines.append(version_str)
        
        return "\n".join(lines)
