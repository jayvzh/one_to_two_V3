"""Model evaluator (model layer).

This module contains:
- EvaluationMetrics: Data class for evaluation metrics
- DailyTopNDetail: Data class for daily Top N detail
- ModelEvaluator: Evaluate model performance

Design Principles:
- No business rule logic here
- No data fetching (belongs to data layer)
- Pure ML evaluation operations
- Top N calculation is per-day, not global
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from sklearn.metrics import roc_auc_score

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DailyTopNDetail:
    """Daily Top N detail for analysis."""
    date: str
    top_n_symbols: list[str]
    success_count: int
    total_count: int
    promotion_rate: float


@dataclass
class EvaluationMetrics:
    """Evaluation metrics data class."""
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    auc: float
    top5_promotion_rate: float
    top10_promotion_rate: float
    overall_promotion_rate: float
    quantile_promotion_rates: dict[str, float]
    sample_count: int
    daily_top5_details: list[DailyTopNDetail] = field(default_factory=list)
    daily_top10_details: list[DailyTopNDetail] = field(default_factory=list)


class ModelEvaluator:
    """Model evaluator for one-to-two prediction.
    
    Responsibilities:
    - Calculate model validation metrics (AUC, Top5/Top10 promotion rate, quantile analysis)
    - Top N promotion rate is calculated per-day, then averaged
    - Output formatted evaluation reports
    """

    def evaluate(
        self,
        y_true: pd.Series,
        y_proba: pd.Series,
        train_start: str,
        train_end: str,
        test_start: str,
        test_end: str,
        dates: pd.Series | None = None,
        symbols: pd.Series | None = None,
    ) -> EvaluationMetrics:
        """Evaluate model performance.
        
        Args:
            y_true: True labels (0/1)
            y_proba: Predicted probabilities
            train_start: Training set start date
            train_end: Training set end date
            test_start: Test set start date
            test_end: Test set end date
            dates: Optional date series for per-day Top N calculation
            symbols: Optional symbol series for daily detail output
            
        Returns:
            EvaluationMetrics with all metrics
        """
        if len(y_true) != len(y_proba):
            raise ValueError(f"y_true 和 y_proba 长度不一致: {len(y_true)} vs {len(y_proba)}")

        sample_count = len(y_true)

        auc = self._calculate_auc(y_true, y_proba)
        overall_promotion_rate = self._calculate_overall_promotion_rate(y_true)

        if dates is not None:
            top5_promotion_rate, daily_top5_details = self._calculate_daily_top_n_promotion_rate(
                y_true=y_true,
                y_proba=y_proba,
                dates=dates,
                symbols=symbols,
                n=5,
            )
            top10_promotion_rate, daily_top10_details = self._calculate_daily_top_n_promotion_rate(
                y_true=y_true,
                y_proba=y_proba,
                dates=dates,
                symbols=symbols,
                n=10,
            )
        else:
            top5_promotion_rate = self._calculate_global_top_n_promotion_rate(y_true, y_proba, n=5)
            top10_promotion_rate = self._calculate_global_top_n_promotion_rate(y_true, y_proba, n=10)
            daily_top5_details = []
            daily_top10_details = []

        quantile_promotion_rates = self._calculate_quantile_promotion_rates(
            y_true, y_proba, quantiles=[0.2, 0.4, 0.6, 0.8]
        )

        return EvaluationMetrics(
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            auc=auc,
            top5_promotion_rate=top5_promotion_rate,
            top10_promotion_rate=top10_promotion_rate,
            overall_promotion_rate=overall_promotion_rate,
            quantile_promotion_rates=quantile_promotion_rates,
            sample_count=sample_count,
            daily_top5_details=daily_top5_details,
            daily_top10_details=daily_top10_details,
        )

    def _calculate_auc(self, y_true: pd.Series, y_proba: pd.Series) -> float:
        """Calculate AUC metric."""
        try:
            return roc_auc_score(y_true, y_proba)
        except ValueError:
            return 0.0

    def _calculate_global_top_n_promotion_rate(
        self, y_true: pd.Series, y_proba: pd.Series, n: int
    ) -> float:
        """Calculate global Top N promotion rate (legacy method, not recommended).
        
        This method selects Top N from the entire dataset, which is incorrect
        for time-series prediction. Use _calculate_daily_top_n_promotion_rate instead.
        """
        if len(y_true) < n:
            return 0.0

        top_n_indices = y_proba.nlargest(n).index.tolist()
        top_n_labels = y_true.iloc[top_n_indices]
        promotion_rate = top_n_labels.mean()
        return promotion_rate

    def _calculate_daily_top_n_promotion_rate(
        self,
        y_true: pd.Series,
        y_proba: pd.Series,
        dates: pd.Series,
        symbols: pd.Series | None,
        n: int,
    ) -> tuple[float, list[DailyTopNDetail]]:
        """Calculate daily Top N promotion rate.
        
        For each trading day, select Top N stocks with highest predicted probability,
        then calculate the average promotion rate across all days.
        
        Args:
            y_true: True labels
            y_proba: Predicted probabilities
            dates: Date for each sample
            symbols: Symbol for each sample (optional, for detail output)
            n: Top N count per day
            
        Returns:
            Tuple of (average promotion rate, list of daily details)
        """
        df = pd.DataFrame({
            "y_true": y_true.values,
            "y_proba": y_proba.values,
            "date": dates.values,
        })

        if symbols is not None:
            df["symbol"] = symbols.values

        daily_rates = []
        daily_details = []

        for date, group in df.groupby("date"):
            if len(group) < n:
                continue

            top_n = group.nlargest(n, "y_proba")
            success_count = int(top_n["y_true"].sum())
            total_count = n
            rate = success_count / total_count

            daily_rates.append(rate)

            if symbols is not None:
                top_n_symbols = top_n["symbol"].tolist()
            else:
                top_n_symbols = []

            daily_details.append(DailyTopNDetail(
                date=str(date),
                top_n_symbols=top_n_symbols,
                success_count=success_count,
                total_count=total_count,
                promotion_rate=rate,
            ))

        if not daily_rates:
            return 0.0, []

        avg_rate = sum(daily_rates) / len(daily_rates)
        return avg_rate, daily_details

    def _calculate_overall_promotion_rate(self, y_true: pd.Series) -> float:
        """Calculate overall promotion rate."""
        return y_true.mean()

    def _calculate_quantile_promotion_rates(
        self, y_true: pd.Series, y_proba: pd.Series, quantiles: list[float]
    ) -> dict[str, float]:
        """Calculate quantile group promotion rates.
        
        Args:
            y_true: True labels
            y_proba: Predicted probabilities
            quantiles: Quantile list, e.g. [0.2, 0.4, 0.6, 0.8]
            
        Returns:
            Dict of quantile group promotion rates, e.g. {"0-20%": 0.1, "20-40%": 0.2, ...}
        """
        df = pd.DataFrame({"y_true": y_true, "y_proba": y_proba})
        df = df.sort_values("y_proba", ascending=False).reset_index(drop=True)

        quantile_promotion_rates = {}
        prev_quantile = 0

        for q in quantiles:
            q_end = int(len(df) * q)
            if q_end == 0:
                continue

            segment = df.iloc[prev_quantile:q_end]
            promotion_rate = segment["y_true"].mean()
            quantile_key = f"{int(prev_quantile/len(df)*100)}-{int(q*100)}%"
            quantile_promotion_rates[quantile_key] = promotion_rate

            prev_quantile = q_end

        last_segment = df.iloc[prev_quantile:]
        if len(last_segment) > 0:
            promotion_rate = last_segment["y_true"].mean()
            quantile_key = f"{int(prev_quantile/len(df)*100)}-100%"
            quantile_promotion_rates[quantile_key] = promotion_rate

        return quantile_promotion_rates

    def print_report(self, metrics: EvaluationMetrics, show_daily: bool = False) -> None:
        """Print evaluation report."""
        logger.info("=" * 60)
        logger.info("模型评估报告")
        logger.info("=" * 60)
        logger.info(f"训练区间：{metrics.train_start} ~ {metrics.train_end}")
        logger.info(f"测试区间：{metrics.test_start} ~ {metrics.test_end}")
        logger.info(f"样本数量：{metrics.sample_count}")
        logger.info("-" * 60)
        logger.info(f"AUC：{metrics.auc:.4f}")
        logger.info(f"Top5 晋级率：{metrics.top5_promotion_rate:.2%}")
        logger.info(f"Top10 晋级率：{metrics.top10_promotion_rate:.2%}")
        logger.info(f"全样本晋级率：{metrics.overall_promotion_rate:.2%}")
        logger.info("-" * 60)
        logger.info("分位数分组晋级率：")
        for quantile, rate in metrics.quantile_promotion_rates.items():
            logger.info(f"  {quantile}: {rate:.2%}")

        if show_daily and metrics.daily_top5_details:
            logger.info("-" * 60)
            logger.info("每日Top5详情：")
            for detail in metrics.daily_top5_details:
                logger.info(f"  {detail.date}: {detail.success_count}/{detail.total_count} ({detail.promotion_rate:.0%})")

        logger.info("=" * 60)

        if metrics.top5_promotion_rate > metrics.overall_promotion_rate + 0.15:
            logger.info("✓ 模型 Top5 晋级率超过市场均值 15% 以上，具有实盘意义")
        else:
            logger.info("✗ 模型 Top5 晋级率未超过市场均值 15% 以上，实盘意义有限")
        logger.info("=" * 60)

    def get_report_dict(self, metrics: EvaluationMetrics) -> dict:
        """Get evaluation report as dictionary."""
        return {
            "train_start": metrics.train_start,
            "train_end": metrics.train_end,
            "test_start": metrics.test_start,
            "test_end": metrics.test_end,
            "sample_count": metrics.sample_count,
            "auc": metrics.auc,
            "top5_promotion_rate": metrics.top5_promotion_rate,
            "top10_promotion_rate": metrics.top10_promotion_rate,
            "overall_promotion_rate": metrics.overall_promotion_rate,
            "quantile_promotion_rates": metrics.quantile_promotion_rates,
        }
