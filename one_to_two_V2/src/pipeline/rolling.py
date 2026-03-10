"""Model stability evaluation script.

This script performs rolling window training to evaluate model stability:
- Fixed 6+1 window configuration (6 months train + 1 month test)
- Generates HTML report with window statistics
- Optional sensitivity test (train_months ∈ {2,3,4,6})

Usage:
    python -m src.pipeline.rolling                    # Basic stability test
    python -m src.pipeline.rolling --sensitivity      # With sensitivity test
    python -m src.pipeline.rolling --start 20250801 --end 20260215
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from ..utils.logging_config import get_logger, log_banner, log_metrics, log_stage

logger = get_logger(__name__)

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from ..core.features import MarketFeatureBuilder, StockFeatureBuilder
from ..core.label import OneToTwoLabelBuilder
from ..core.scoring import calc_one_to_two
from ..data.ak import AkshareDataSource, IndexRepository, ZtRepository
from ..data.cache import CacheAvailability
from ..data.prepare import build_training_data
from ..data.sync_cache import ensure_cache_for_training
from ..data.trade_calendar import TradingCalendar
from ..model.evaluator import ModelEvaluator
from ..model.trainer import ModelMeta, OneToTwoDatasetBuilder, OneToTwoPredictor
from .config import load_pipeline_defaults


@dataclass
class WindowResult:
    """Result of a single training window."""
    window_id: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_samples: int
    test_samples: int
    auc: float
    top5_promotion_rate: float
    top10_promotion_rate: float
    overall_promotion_rate: float
    top5_vs_market: float
    model_path: str | None = None


@dataclass
class StabilityReport:
    """Complete stability evaluation report."""
    start_date: str
    end_date: str
    train_months: int
    test_months: int
    total_windows: int
    windows: list[WindowResult] = field(default_factory=list)
    avg_auc: float = 0.0
    avg_top5_rate: float = 0.0
    avg_top10_rate: float = 0.0
    avg_top5_vs_market: float = 0.0
    win_rate: float = 0.0

    def calculate_summary(self):
        """Calculate summary statistics."""
        if not self.windows:
            return

        self.avg_auc = sum(w.auc for w in self.windows) / len(self.windows)
        self.avg_top5_rate = sum(w.top5_promotion_rate for w in self.windows) / len(self.windows)
        self.avg_top10_rate = sum(w.top10_promotion_rate for w in self.windows) / len(self.windows)
        self.avg_top5_vs_market = sum(w.top5_vs_market for w in self.windows) / len(self.windows)

        wins = sum(1 for w in self.windows if w.top5_vs_market > 0)
        self.win_rate = wins / len(self.windows)


class StabilityEvaluator:
    """Model stability evaluator with fixed 6+1 windows."""

    def __init__(
        self,
        base_dir: Path,
        cache_availability: CacheAvailability | None = None,
    ):
        self.base_dir = base_dir
        self.cache_dir = base_dir / "data" / "cache"
        self.model_dir = base_dir / "data" / "models"
        self.cache_availability = cache_availability

        self.calendar = TradingCalendar(self.cache_dir)
        self.data_source = AkshareDataSource()

        self.index_repo = IndexRepository(
            data_source=self.data_source,
            cache_dir=self.cache_dir / "index",
            calendar=self.calendar,
        )
        self.zt_repo = ZtRepository(
            data_source=self.data_source,
            cache_dir=self.cache_dir / "zt",
        )

        self.market_feature_builder = MarketFeatureBuilder()
        self.stock_feature_builder = StockFeatureBuilder()
        self.label_builder = OneToTwoLabelBuilder(
            get_next_trade_day=self.calendar.next_trade_day
        )
        self.dataset_builder = OneToTwoDatasetBuilder()
        self.evaluator = ModelEvaluator()

    def run(
        self,
        start_date: str,
        end_date: str,
        train_months: int = 6,
        test_months: int = 1,
        verbose: bool = True,
    ) -> StabilityReport:
        """Run stability evaluation with fixed windows.
        
        Args:
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            train_months: Training months per window
            test_months: Test months per window
            verbose: Print progress
            
        Returns:
            StabilityReport with all results
        """
        start_date = self.calendar.normalize_date(start_date)
        end_date = self.calendar.normalize_date(end_date)

        windows = self._generate_fixed_windows(
            start_date=start_date,
            end_date=end_date,
            train_months=train_months,
            test_months=test_months,
        )

        if verbose:
            logger.info(f"生成 {len(windows)} 个窗口")

        report = StabilityReport(
            start_date=start_date,
            end_date=end_date,
            train_months=train_months,
            test_months=test_months,
            total_windows=len(windows),
        )

        iterator = enumerate(windows)
        if HAS_TQDM and verbose and len(windows) > 1:
            iterator = tqdm(list(enumerate(windows)), desc="评估进度", unit="窗口")

        for i, (train_start, train_end, test_start, test_end) in iterator:
            if verbose and not HAS_TQDM:
                logger.info(f"窗口 {i + 1}/{len(windows)}: {train_start} ~ {train_end}")

            try:
                result = self._evaluate_window(
                    window_id=i + 1,
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                    verbose=verbose,
                )
                report.windows.append(result)
            except Exception as e:
                if verbose:
                    logger.error(f"窗口 {i + 1} 评估失败: {e}")
                continue

        report.calculate_summary()
        return report

    def _generate_fixed_windows(
        self,
        start_date: str,
        end_date: str,
        train_months: int,
        test_months: int,
    ) -> list[tuple[str, str, str, str]]:
        """Generate rolling training windows.
        
        Strategy: Generate windows by rolling forward, each window uses
        train_months for training and test_months for testing.
        Windows roll by test_months each step.
        
        Example with 9 months data, 6+1 config:
        - Window 1: Train months 1-6, Test month 7
        - Window 2: Train months 2-7, Test month 8
        - Window 3: Train months 3-8, Test month 9
        """
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)

        total_months = (end_ts.year - start_ts.year) * 12 + (end_ts.month - start_ts.month) + 1
        required_months = train_months + test_months

        if total_months < required_months:
            return []

        windows = []

        test_start_ts = start_ts + pd.DateOffset(months=train_months)

        while True:
            test_end_ts = test_start_ts + pd.DateOffset(months=test_months) - pd.Timedelta(days=1)

            if test_end_ts > end_ts:
                break

            train_start_ts = test_start_ts - pd.DateOffset(months=train_months)
            train_end_ts = test_start_ts - pd.Timedelta(days=1)

            train_start = self._to_trade_day(train_start_ts, "forward")
            train_end = self._to_trade_day(train_end_ts, "backward")
            test_start = self._to_trade_day(test_start_ts, "forward")
            test_end = self._to_trade_day(test_end_ts, "backward")

            if train_start >= start_date and test_end <= end_date:
                windows.append((train_start, train_end, test_start, test_end))

            test_start_ts = test_start_ts + pd.DateOffset(months=test_months)

            if len(windows) > 20:
                break

        return windows

    def _to_trade_day(self, date_ts: pd.Timestamp, direction: str) -> str:
        """Convert to nearest trade day."""
        date_str = date_ts.strftime("%Y%m%d")

        if self.calendar.is_trade_day(date_str):
            return date_str

        if direction == "forward":
            try:
                return self.calendar.next_trade_day(date_str)
            except ValueError:
                pass
        else:
            try:
                return self.calendar.prev_trade_day(date_str)
            except ValueError:
                pass

        calendar_df = self.calendar._load_calendar()
        calendar_df["date_n"] = calendar_df["date"].astype(str).str.replace("-", "")
        available = calendar_df["date_n"].tolist()

        if direction == "forward":
            candidates = [d for d in available if d >= date_str]
            return candidates[0] if candidates else available[-1]
        else:
            candidates = [d for d in available if d <= date_str]
            return candidates[-1] if candidates else available[0]

    def _evaluate_window(
        self,
        window_id: int,
        train_start: str,
        train_end: str,
        test_start: str,
        test_end: str,
        verbose: bool = True,
    ) -> WindowResult:
        """Evaluate a single window."""
        if verbose:
            logger.info(f"  训练: {train_start} ~ {train_end}")
            logger.info(f"  测试: {test_start} ~ {test_end}")

        zt_cache_dir = self.cache_dir / "zt"
        raw_df = build_training_data(
            zt_cache_dir=zt_cache_dir,
            date_range=(train_start, test_end),
            verbose=False,
        )

        raw_df["date"] = raw_df["date"].astype(str)
        stock_features = self.stock_feature_builder.build_history(raw_df)
        stock_features = stock_features[
            (stock_features["date"] >= train_start)
            & (stock_features["date"] <= test_end)
        ].copy()

        labeled_df = self.label_builder.build(
            stock_features,
            drop_last_unlabeled=True,
            normalize_date=self.calendar.normalize_date,
        )

        train_df = labeled_df[
            (labeled_df["date"] >= train_start)
            & (labeled_df["date"] <= train_end)
        ].copy()

        test_df = labeled_df[
            (labeled_df["date"] >= test_start)
            & (labeled_df["date"] <= test_end)
        ].copy()

        if len(train_df) == 0:
            raise ValueError("训练集为空")
        if len(test_df) == 0:
            raise ValueError("测试集为空")

        prev_date = self.calendar.prev_trade_day(train_end)
        index_df = self.index_repo.get_daily(start=prev_date, end=train_end)
        today_zt, _ = self.zt_repo.get_by_date(train_end)
        prev_zt, _ = self.zt_repo.get_by_date(prev_date)
        one_to_two = calc_one_to_two(date=prev_date, today_zt=prev_zt, next_day_zt=today_zt)
        market_features = self.market_feature_builder.build(
            date=train_end,
            one_to_two=one_to_two,
            zt_count_today=len(today_zt),
            index_df=index_df,
        ).to_frame()

        train_dataset = self.dataset_builder.build(
            stock_features=train_df,
            market_features=market_features,
            label_col="label",
        )

        model = OneToTwoPredictor()
        model.fit(train_dataset)

        test_dataset = self.dataset_builder.build(
            stock_features=test_df,
            market_features=market_features,
            label_col="label",
        )

        y_proba = model.predict_proba(test_dataset.X)
        y_true = test_dataset.y

        metrics = self.evaluator.evaluate(
            y_true=y_true,
            y_proba=y_proba,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            dates=test_df["date"].reset_index(drop=True),
            symbols=test_df["symbol"].reset_index(drop=True) if "symbol" in test_df.columns else None,
        )

        self.model_dir.mkdir(parents=True, exist_ok=True)
        model_path = self.model_dir / f"stability_model_{window_id}.joblib"

        meta = ModelMeta(
            train_start=train_start,
            train_end=train_end,
            sample_size=len(train_dataset.X),
            base_success_rate=float(train_dataset.y.mean()),
            features=train_dataset.feature_names,
            model_type="logistic_regression",
            version=datetime.now().strftime("%Y-%m-%d"),
        )
        model.save(str(model_path), meta=meta)

        if verbose:
            logger.info(f"  AUC: {metrics.auc:.4f}, Top5: {metrics.top5_promotion_rate:.2%}")

        return WindowResult(
            window_id=window_id,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            train_samples=len(train_df),
            test_samples=len(test_df),
            auc=metrics.auc,
            top5_promotion_rate=metrics.top5_promotion_rate,
            top10_promotion_rate=metrics.top10_promotion_rate,
            overall_promotion_rate=metrics.overall_promotion_rate,
            top5_vs_market=metrics.top5_promotion_rate - metrics.overall_promotion_rate,
            model_path=str(model_path),
        )


def generate_stability_html(report: StabilityReport, output_path: str) -> str:
    """Generate HTML report for stability evaluation."""

    rows = []
    for w in report.windows:
        rows.append(f"""
        <tr>
            <td>{w.window_id}</td>
            <td>{w.train_start} ~ {w.train_end}</td>
            <td>{w.test_start} ~ {w.test_end}</td>
            <td>{w.train_samples}</td>
            <td>{w.test_samples}</td>
            <td>{w.auc:.4f}</td>
            <td>{w.top5_promotion_rate:.2%}</td>
            <td>{w.top10_promotion_rate:.2%}</td>
            <td>{w.overall_promotion_rate:.2%}</td>
            <td class="{'positive' if w.top5_vs_market > 0 else 'negative'}">{w.top5_vs_market:+.2%}</td>
        </tr>
        """)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>模型稳定性评估报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
        .summary-card {{ background: #f9f9f9; padding: 20px; border-radius: 8px; text-align: center; }}
        .summary-card h3 {{ margin: 0; color: #666; font-size: 14px; }}
        .summary-card .value {{ font-size: 28px; font-weight: bold; color: #333; margin: 10px 0; }}
        .summary-card .positive {{ color: #4CAF50; }}
        .summary-card .negative {{ color: #f44336; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: center; border-bottom: 1px solid #ddd; }}
        th {{ background: #4CAF50; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .positive {{ color: #4CAF50; font-weight: bold; }}
        .negative {{ color: #f44336; font-weight: bold; }}
        .config {{ background: #e8f5e9; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>模型稳定性评估报告</h1>
        
        <div class="config">
            <strong>配置:</strong> 训练 {report.train_months} 月 + 测试 {report.test_months} 月 | 
            <strong>日期范围:</strong> {report.start_date} ~ {report.end_date} | 
            <strong>窗口数:</strong> {report.total_windows}
        </div>
        
        <h2>汇总统计</h2>
        <div class="summary">
            <div class="summary-card">
                <h3>平均 AUC</h3>
                <div class="value">{report.avg_auc:.4f}</div>
            </div>
            <div class="summary-card">
                <h3>平均 Top5 晋级率</h3>
                <div class="value">{report.avg_top5_rate:.2%}</div>
            </div>
            <div class="summary-card">
                <h3>平均 Top5 vs 市场</h3>
                <div class="value {'positive' if report.avg_top5_vs_market > 0 else 'negative'}">{report.avg_top5_vs_market:+.2%}</div>
            </div>
            <div class="summary-card">
                <h3>胜率 (Top5 > 市场)</h3>
                <div class="value {'positive' if report.win_rate > 0.5 else 'negative'}">{report.win_rate:.1%}</div>
            </div>
        </div>
        
        <h2>窗口详情</h2>
        <table>
            <thead>
                <tr>
                    <th>窗口</th>
                    <th>训练区间</th>
                    <th>测试区间</th>
                    <th>训练样本</th>
                    <th>测试样本</th>
                    <th>AUC</th>
                    <th>Top5 晋级率</th>
                    <th>Top10 晋级率</th>
                    <th>市场均值</th>
                    <th>Top5 vs 市场</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        
        <div class="footer">
            生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def run_sensitivity_test(
    base_dir: Path,
    start_date: str,
    end_date: str,
    train_months_list: list[int] = [2, 3, 4, 6],
    test_months: int = 1,
    verbose: bool = True,
) -> dict[int, StabilityReport]:
    """Run sensitivity test with different train_months values."""
    results = {}

    for months in train_months_list:
        if verbose:
            logger.info("=" * 50)
            logger.info(f"敏感性测试: train_months = {months}")
            logger.info("=" * 50)

        evaluator = StabilityEvaluator(base_dir)
        report = evaluator.run(
            start_date=start_date,
            end_date=end_date,
            train_months=months,
            test_months=test_months,
            verbose=verbose,
        )
        results[months] = report

    return results


def generate_sensitivity_html(
    results: dict[int, StabilityReport],
    output_path: str,
) -> str:
    """Generate HTML report for sensitivity test."""

    rows = []
    for months, report in sorted(results.items()):
        rows.append(f"""
        <tr>
            <td>{months}</td>
            <td>{report.total_windows}</td>
            <td>{report.avg_auc:.4f}</td>
            <td>{report.avg_top5_rate:.2%}</td>
            <td>{report.avg_top10_rate:.2%}</td>
            <td class="{'positive' if report.avg_top5_vs_market > 0 else 'negative'}">{report.avg_top5_vs_market:+.2%}</td>
            <td class="{'positive' if report.win_rate > 0.5 else 'negative'}">{report.win_rate:.1%}</td>
        </tr>
        """)

    best_months = max(results.keys(), key=lambda m: results[m].avg_top5_vs_market)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>敏感性测试报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #2196F3; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .best {{ background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2196F3; }}
        .best h3 {{ margin: 0 0 10px 0; color: #1976D2; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: center; border-bottom: 1px solid #ddd; }}
        th {{ background: #2196F3; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .positive {{ color: #4CAF50; font-weight: bold; }}
        .negative {{ color: #f44336; font-weight: bold; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>训练窗口敏感性测试报告</h1>
        
        <div class="best">
            <h3>最佳训练窗口: {best_months} 个月</h3>
            <p>平均 Top5 vs 市场: <strong class="positive">{results[best_months].avg_top5_vs_market:+.2%}</strong></p>
            <p>胜率: <strong>{results[best_months].win_rate:.1%}</strong></p>
        </div>
        
        <h2>对比结果</h2>
        <table>
            <thead>
                <tr>
                    <th>训练月数</th>
                    <th>窗口数</th>
                    <th>平均 AUC</th>
                    <th>平均 Top5 晋级率</th>
                    <th>平均 Top10 晋级率</th>
                    <th>Top5 vs 市场</th>
                    <th>胜率</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        
        <div class="footer">
            生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def main() -> None:
    """Main entry point."""
    defaults = load_pipeline_defaults(Path("."))

    parser = argparse.ArgumentParser(
        description="模型稳定性评估"
    )
    parser.add_argument(
        "--start", "-s",
        type=str,
        help="开始日期 (YYYYMMDD)"
    )
    parser.add_argument(
        "--end", "-e",
        type=str,
        help="结束日期 (YYYYMMDD)"
    )
    parser.add_argument(
        "--train-months",
        type=int,
        default=defaults.rolling.train_months,
        help=f"训练月数 (默认: {defaults.rolling.train_months})"
    )
    parser.add_argument(
        "--sensitivity",
        action="store_true",
        help="运行敏感性测试 (train_months ∈ {2,3,4,6})"
    )
    args = parser.parse_args()

    base_dir = Path(".")
    cache_dir = base_dir / "data" / "cache"
    report_dir = base_dir / "reports"

    log_banner(logger, "模型稳定性评估")

    log_stage(logger, 1, 3, "检测缓存数据")

    availability = ensure_cache_for_training(
        cache_dir=cache_dir,
        train_months=args.train_months,
        auto_sync=True,
    )
    availability.print_summary(compact=True)

    if not availability.is_sufficient:
        logger.error("缓存数据不足，无法进行评估")
        return

    start_date = args.start or availability.effective_start
    end_date = args.end or availability.effective_end

    if args.sensitivity:
        log_stage(logger, 2, 3, "敏感性测试")

        results = run_sensitivity_test(
            base_dir=base_dir,
            start_date=start_date,
            end_date=end_date,
            train_months_list=list(defaults.rolling.sensitivity_train_months),
            test_months=defaults.rolling.test_months,
            verbose=True,
        )

        log_stage(logger, 3, 3, "生成报告")

        report_path = report_dir / f"sensitivity_report_{datetime.now().strftime('%Y%m%d')}.html"
        html_path = generate_sensitivity_html(results, str(report_path))
        logger.info(f"HTML报告: {html_path}")

        logger.info("汇总:")
        logger.info(f"{'训练月数':<8} {'平均AUC':<10} {'Top5 vs 市场':<12} {'胜率':<8}")
        logger.info("-" * 50)
        for months, report in sorted(results.items()):
            logger.info(f"{months:<8} {report.avg_auc:<10.4f} {report.avg_top5_vs_market:+.2%} {report.win_rate:<8.1%}")
            log_metrics(logger, f"train_months={months}", avg_auc=report.avg_auc, top5_vs_market=report.avg_top5_vs_market, win_rate=report.win_rate)
    else:
        log_stage(logger, 2, 3, "稳定性评估")
        logger.info(f"训练区间: {start_date} ~ {end_date}")
        logger.info(f"窗口配置: 训练{args.train_months}月 + 测试{defaults.rolling.test_months}月")

        evaluator = StabilityEvaluator(base_dir, cache_availability=availability)
        report = evaluator.run(
            start_date=start_date,
            end_date=end_date,
            train_months=args.train_months,
            test_months=defaults.rolling.test_months,
            verbose=True,
        )

        log_stage(logger, 3, 3, "生成报告")

        report_path = report_dir / f"stability_report_{datetime.now().strftime('%Y%m%d')}.html"
        html_path = generate_stability_html(report, str(report_path))
        logger.info(f"HTML报告: {html_path}")

        logger.info("汇总统计:")
        logger.info(f"  平均 AUC: {report.avg_auc:.4f}")
        logger.info(f"  平均 Top5 晋级率: {report.avg_top5_rate:.2%}")
        logger.info(f"  平均 Top5 vs 市场: {report.avg_top5_vs_market:+.2%}")
        logger.info(f"  胜率: {report.win_rate:.1%}")
        log_metrics(logger, "评估摘要", avg_auc=report.avg_auc, avg_top5_rate=report.avg_top5_rate, avg_top5_vs_market=report.avg_top5_vs_market, win_rate=report.win_rate)

    log_banner(logger, "评估完成")


if __name__ == "__main__":
    main()
