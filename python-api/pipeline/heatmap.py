"""Heatmap analysis pipeline (pipeline layer).

This module contains:
- HeatmapRecord: Single record for heatmap analysis
- HeatmapResult: Complete result of heatmap analysis
- HeatmapAnalyzer: Heatmap analysis pipeline

Design Principles:
- Independent module (can run standalone)
- Outputs structured data and HTML report
- Uses core modules for calculation
- Validates model effectiveness across emotion regimes
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from core.logging import get_logger, log_banner, log_metrics, log_stage

logger = get_logger(__name__)

from core.emotion import EmotionMetrics, MarketEmotionAnalyzer
from core.features import MarketFeatureBuilder, StockFeatureBuilder
from core.heatmap import HeatmapCell, HeatmapData, HeatmapPlotter, calc_success_matrix
from core.scoring import calc_one_to_two, detect_first_board
from data.ak import AkshareDataSource, ZtRepository
from data.trade_calendar import TradingCalendar
from ml.trainer import ModelMeta, OneToTwoPredictor
from pipeline.config import load_pipeline_defaults
from pipeline.report import generate_heatmap_html


@dataclass
class HeatmapRecord:
    """Single record for heatmap analysis."""
    date: str
    symbol: str
    emotion_score: float
    model_score: float
    success: int


@dataclass
class HeatmapResult:
    """Complete result of heatmap analysis."""
    start_date: str
    end_date: str
    total_samples: int
    total_days: int
    analysis_base_success_rate: float = 0.0
    records: list[HeatmapRecord] = field(default_factory=list)
    heatmap_data: HeatmapData | None = None
    image_path: str = ""
    duration_seconds: float = 0.0
    model_meta: ModelMeta | None = None

    def to_dataframe(self) -> pd.DataFrame:
        """Convert records to DataFrame."""
        if not self.records:
            return pd.DataFrame()

        data = [
            {
                "date": r.date,
                "symbol": r.symbol,
                "emotion_score": r.emotion_score,
                "model_score": r.model_score,
                "success": r.success,
            }
            for r in self.records
        ]
        return pd.DataFrame(data)


class HeatmapAnalyzer:
    """Heatmap analysis pipeline.
    
    Analyzes model effectiveness across different emotion regimes.
    
    Usage:
        analyzer = HeatmapAnalyzer(
            cache_dir=Path("./data/cache"),
            model_dir=Path("./data/models"),
            report_dir=Path("./data/reports"),
        )
        result = analyzer.run()
    """

    def __init__(
        self,
        cache_dir: Path,
        model_dir: Path,
        report_dir: Path,
        zt_cache_mode: str = "read",
    ):
        """Initialize heatmap analyzer.
        
        Args:
            cache_dir: Directory for cache files
            model_dir: Directory for model files
            report_dir: Directory for report output
            zt_cache_mode: Cache mode for ZtRepository
        """
        self.cache_dir = cache_dir
        self.model_dir = model_dir
        self.report_dir = report_dir

        self.data_source = AkshareDataSource()
        self.calendar = TradingCalendar(cache_dir=cache_dir)

        self.zt_repo = ZtRepository(
            data_source=self.data_source,
            cache_dir=cache_dir / "zt",
            cache_mode=zt_cache_mode,
        )

        self.emotion_analyzer = MarketEmotionAnalyzer()
        self.market_feature_builder = MarketFeatureBuilder()
        self.stock_feature_builder = StockFeatureBuilder()
        self.model = OneToTwoPredictor()
        self.model_meta: ModelMeta | None = None
        self.plotter = HeatmapPlotter()

    def run(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        model_path: str | None = None,
        force: bool = False,
    ) -> HeatmapResult:
        """Run heatmap analysis.
        
        Args:
            start_date: Start date (YYYYMMDD), if None, uses cache range
            end_date: End date (YYYYMMDD), if None, uses cache range
            model_path: Path to model file, if None, uses latest model
            force: Force recalculation, ignore cache
            
        Returns:
            HeatmapResult with all analysis data
        """
        start_time = time.time()

        cache_start, cache_end = self._detect_cache_range()

        if end_date is None:
            end_date = cache_end if cache_end else datetime.now().strftime("%Y%m%d")

        if start_date is None:
            defaults = load_pipeline_defaults(Path("."))
            default_months = defaults.heatmap.months
            start_date = self._get_default_start_date(end_date, months=default_months)
            logger.info(f"默认分析范围: 最近{default_months}个月 ({start_date} ~ {end_date})")

        start_date = self.calendar.normalize_date(start_date)
        end_date = self.calendar.normalize_date(end_date)

        original_end_date = end_date
        end_date = self.calendar.prev_trade_day(end_date)
        logger.info(f"结束日期修正: {original_end_date} -> {end_date} (确保最后一天首板股票有第二天数据计算成功率)")

        log_banner(logger, "系统有效性验证（热力图分析）", width=60)
        logger.info(f"分析区间: {start_date} ~ {end_date}")

        heatmap_cache_dir = self.cache_dir / "heatmap"
        heatmap_cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = heatmap_cache_dir / f"heatmap_result_{start_date}_{end_date}.json"

        if not force and cache_file.exists():
            cached_result = self._load_cache(cache_file)
            if cached_result is not None:
                logger.info(f"使用缓存结果: {cache_file}")

                if cached_result.model_meta is None:
                    self._load_model(model_path)
                    cached_result.model_meta = self.model_meta

                if not cached_result.image_path or not Path(cached_result.image_path).exists():
                    if cached_result.heatmap_data:
                        cached_result.image_path = self._generate_heatmap_image(
                            cached_result.heatmap_data,
                            cached_result.start_date,
                            cached_result.end_date,
                            cached_result.total_samples,
                            cached_result.analysis_base_success_rate,
                        )
                else:
                    expected_filename = f"heatmap_{cached_result.start_date}_{cached_result.end_date}.png"
                    if expected_filename not in cached_result.image_path:
                        cached_result.image_path = self._generate_heatmap_image(
                            cached_result.heatmap_data,
                            cached_result.start_date,
                            cached_result.end_date,
                            cached_result.total_samples,
                            cached_result.analysis_base_success_rate,
                        )

                self._generate_report(cached_result)
                self._print_summary(cached_result)

                return cached_result

        if not self._load_model(model_path):
            raise RuntimeError("无法加载模型")

        records = self._collect_history(start_date, end_date)

        if not records:
            logger.warning("无有效分析数据")
            if cache_file.exists():
                cache_file.unlink()
                logger.info("已清除无效缓存")
            return HeatmapResult(
                start_date=start_date,
                end_date=end_date,
                total_samples=0,
                total_days=0,
            )

        record_dicts = [
            {
                "emotion_score": r.emotion_score,
                "model_score": r.model_score,
                "success": r.success,
            }
            for r in records
        ]

        heatmap_data = calc_success_matrix(record_dicts)

        analysis_base_success_rate = sum(r.success for r in records) / len(records) if records else 0.0

        image_path = self._generate_heatmap_image(heatmap_data, start_date, end_date, len(records), analysis_base_success_rate)

        duration = time.time() - start_time

        result = HeatmapResult(
            start_date=start_date,
            end_date=end_date,
            total_samples=len(records),
            total_days=len(set(r.date for r in records)),
            analysis_base_success_rate=analysis_base_success_rate,
            records=records,
            heatmap_data=heatmap_data,
            image_path=image_path,
            duration_seconds=duration,
            model_meta=self.model_meta,
        )

        self._save_cache(cache_file, result)

        self._generate_report(result)

        self._print_summary(result)

        return result

    def _detect_cache_range(self) -> tuple[str | None, str | None]:
        """Detect available cache date range from zt cache files."""
        zt_cache_dir = self.cache_dir / "zt"
        if not zt_cache_dir.exists():
            return None, None

        cache_files = list(zt_cache_dir.glob("zt_*.csv"))
        if not cache_files:
            return None, None

        dates = []
        for f in cache_files:
            try:
                date_str = f.stem.replace("zt_", "")
                if len(date_str) == 8 and date_str.isdigit():
                    dates.append(date_str)
            except Exception:
                continue

        if not dates:
            return None, None

        return min(dates), max(dates)

    def _get_default_start_date(self, end_date: str, months: int = 1) -> str:
        """Calculate default start date from end date and months.
        
        Args:
            end_date: End date (YYYYMMDD)
            months: Number of months to go back
            
        Returns:
            Start date string (YYYYMMDD)
        """
        end_dt = pd.to_datetime(end_date)
        start_dt = end_dt - pd.DateOffset(months=months)
        return start_dt.strftime("%Y%m%d")

    def _load_model(self, model_path: str | None) -> bool:
        """Load model from file."""
        if model_path:
            model_file = Path(model_path)
        else:
            model_files = list(self.model_dir.glob("model_*.joblib"))
            if not model_files:
                logger.warning("未找到模型文件")
                return False
            model_file = sorted(model_files)[-1]

        logger.info(f"加载模型: {model_file}")

        self.model.load(str(model_file))
        self.model_meta = OneToTwoPredictor.load_meta(str(model_file))

        return True

    def _collect_history(
        self,
        start_date: str,
        end_date: str,
    ) -> list[HeatmapRecord]:
        """Collect historical data for heatmap analysis.
        
        For each trading day T:
        1. Get previous day's (T-1) first-board stocks
        2. Calculate emotion score for T-1
        3. Use model to predict model score
        4. Check if stock succeeded in T (became second-board)
        """
        records = []

        trade_dates = self._get_trade_dates(start_date, end_date)

        if len(trade_dates) < 2:
            logger.warning("交易日不足，无法进行分析")
            return records

        logger.info(f"共 {len(trade_dates)} 个交易日")

        for i, current_date in enumerate(trade_dates[1:], start=1):
            prev_date = trade_dates[i - 1]

            try:
                prev_zt, _ = self.zt_repo.get_by_date(prev_date)
                current_zt, _ = self.zt_repo.get_by_date(current_date)

                if prev_zt.empty:
                    continue

                prev_first_board = detect_first_board(prev_zt)

                if prev_first_board.empty:
                    continue

                one_to_two = calc_one_to_two(
                    date=prev_date,
                    today_zt=prev_zt,
                    next_day_zt=current_zt,
                )

                max_board_height = int(current_zt["board_count"].max()) if not current_zt.empty else 0

                emotion_metrics = EmotionMetrics(
                    success_rate=one_to_two.success_rate,
                    max_board_height=max_board_height,
                    zt_count_today=len(current_zt),
                    zt_count_yesterday=len(prev_zt),
                )

                emotion = self.emotion_analyzer.score(emotion_metrics)

                stock_features = self.stock_feature_builder.build(prev_first_board)
                stock_features["is_limit_up"] = 1

                market_features = self._build_market_features(prev_date, one_to_two, len(prev_zt))
                mf_df = market_features.to_frame()

                if len(mf_df) == 1:
                    mf_df = pd.concat([mf_df] * len(stock_features), ignore_index=True)

                X = pd.concat([stock_features.reset_index(drop=True), mf_df.reset_index(drop=True)], axis=1)

                if self.model_meta is not None:
                    feature_cols = self.model_meta.features
                    X = X[feature_cols].copy()

                model_scores = self.model.predict_proba(X)

                prev_first_board = prev_first_board.copy()
                prev_first_board["model_score"] = model_scores.values

                current_second_board = current_zt[current_zt["board_count"] == 2]
                success_codes = set(current_second_board["symbol"].tolist())

                for _, row in prev_first_board.iterrows():
                    symbol = row["symbol"]
                    success = 1 if symbol in success_codes else 0

                    records.append(HeatmapRecord(
                        date=prev_date,
                        symbol=symbol,
                        emotion_score=emotion.score,
                        model_score=float(row["model_score"]),
                        success=success,
                    ))

            except Exception as e:
                logger.warning(f"处理日期 {current_date} 时出错: {e}")
                continue

        return records

    def _build_market_features(self, date: str, one_to_two, zt_count: int):
        """Build market features for a single date."""
        from core.features import MarketFeatures
        return MarketFeatures(
            date=date,
            success_rate=one_to_two.success_rate,
            first_board_ratio=0.0,
            index_return=0.0,
        )

    def _get_trade_dates(self, start_date: str, end_date: str) -> list[str]:
        """Get list of trade dates in range."""
        df = self.calendar._load_calendar()
        all_dates = df["date"].tolist()
        
        start_dash = self.calendar._to_dash_date(start_date)
        end_dash = self.calendar._to_dash_date(end_date)
        
        dates = [
            d.replace("-", "")
            for d in all_dates
            if start_dash <= d <= end_dash
        ]
        
        return dates

    def _generate_heatmap_image(
        self,
        heatmap_data: HeatmapData,
        start_date: str = "",
        end_date: str = "",
        analysis_sample_count: int = 0,
        analysis_base_success_rate: float = 0.0,
    ) -> str:
        """Generate heatmap image."""
        images_dir = self.report_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        if start_date and end_date:
            filename = f"heatmap_{start_date}_{end_date}.png"
        else:
            filename = f"heatmap_{datetime.now().strftime('%Y%m%d')}.png"
        image_path = images_dir / filename

        model_meta_dict = None
        if self.model_meta:
            model_meta_dict = {
                "version": self.model_meta.version,
                "train_start": self.model_meta.train_start,
                "train_end": self.model_meta.train_end,
            }

        analysis_range = (start_date, end_date) if start_date and end_date else None
        self.plotter.plot(
            heatmap_data,
            str(image_path),
            model_meta=model_meta_dict,
            analysis_range=analysis_range,
            analysis_sample_count=analysis_sample_count,
            analysis_base_success_rate=analysis_base_success_rate,
        )

        return str(image_path.absolute())

    def _generate_report(self, result: HeatmapResult) -> str:
        """Generate HTML report."""
        report_path = self.report_dir / f"heatmap_report_{result.start_date}_{result.end_date}.html"

        html_path = generate_heatmap_html(result, str(report_path))

        return html_path

    def _load_cache(self, cache_file: Path) -> HeatmapResult | None:
        """Load result from cache file."""
        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)

            records = [
                HeatmapRecord(
                    date=r["date"],
                    symbol=r["symbol"],
                    emotion_score=r["emotion_score"],
                    model_score=r["model_score"],
                    success=r["success"],
                )
                for r in data.get("records", [])
            ]

            cells = [
                HeatmapCell(
                    emotion_score=c["emotion_score"],
                    score_bin=c["score_bin"],
                    sample_count=c["sample_count"],
                    success_count=c["success_count"],
                    success_rate=c["success_rate"],
                )
                for c in data.get("heatmap_cells", [])
            ]

            heatmap_data = HeatmapData(
                cells=cells,
                emotion_scores=data.get("emotion_scores", []),
                score_bins=data.get("score_bins", []),
            )

            model_meta = None
            if data.get("model_meta"):
                model_meta = ModelMeta(**data["model_meta"])

            return HeatmapResult(
                start_date=data["start_date"],
                end_date=data["end_date"],
                total_samples=data["total_samples"],
                total_days=data["total_days"],
                analysis_base_success_rate=data.get("analysis_base_success_rate", 0.0),
                records=records,
                heatmap_data=heatmap_data,
                image_path=data.get("image_path", ""),
                duration_seconds=data.get("duration_seconds", 0),
                model_meta=model_meta,
            )
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return None

    def _save_cache(self, cache_file: Path, result: HeatmapResult) -> None:
        """Save result to cache file."""
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        cells_data = []
        if result.heatmap_data:
            cells_data = [
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
                "train_start": result.model_meta.train_start,
                "train_end": result.model_meta.train_end,
                "sample_size": result.model_meta.sample_size,
                "base_success_rate": result.model_meta.base_success_rate,
                "features": result.model_meta.features,
                "model_type": result.model_meta.model_type,
                "version": result.model_meta.version,
            }

        data = {
            "start_date": result.start_date,
            "end_date": result.end_date,
            "total_samples": result.total_samples,
            "total_days": result.total_days,
            "analysis_base_success_rate": result.analysis_base_success_rate,
            "duration_seconds": result.duration_seconds,
            "records": [
                {
                    "date": r.date,
                    "symbol": r.symbol,
                    "emotion_score": r.emotion_score,
                    "model_score": r.model_score,
                    "success": r.success,
                }
                for r in result.records
            ],
            "heatmap_cells": cells_data,
            "emotion_scores": result.heatmap_data.emotion_scores if result.heatmap_data else [],
            "score_bins": result.heatmap_data.score_bins if result.heatmap_data else [],
            "image_path": result.image_path,
            "model_meta": model_meta_dict,
        }

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"结果已缓存: {cache_file}")

    def _print_summary(self, result: HeatmapResult) -> None:
        """Print analysis summary."""
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

        log_banner(logger, "热力图分析结果汇总", width=60)
        logger.info(f"分析区间: {result.start_date} ~ {result.end_date}")
        logger.info(f"总样本数: {result.total_samples}")
        logger.info(f"交易日数: {result.total_days}")
        logger.info(f"计算耗时: {duration_str}")
        log_metrics(
            logger,
            "热力图摘要",
            total_samples=result.total_samples,
            total_days=result.total_days,
            duration_seconds=round(result.duration_seconds, 2),
        )

        if result.heatmap_data and result.heatmap_data.cells:
            logger.info("热力图数据预览:")
            logger.info(f"{'情绪':<8} {'分数区间':<12} {'样本数':<8} {'成功率':<8}")
            logger.info("-" * 40)
            for cell in result.heatmap_data.cells[:10]:
                logger.info(f"{cell.emotion_score:<8.1f} {cell.score_bin:<12} {cell.sample_count:<8} {cell.success_rate*100:<8.1f}%")
            if len(result.heatmap_data.cells) > 10:
                logger.info(f"... 共 {len(result.heatmap_data.cells)} 个数据单元")

        logger.info("=" * 60)


def main() -> None:
    """Main entry point."""
    import argparse

    from data.sync_cache import ensure_cache_for_training

    defaults = load_pipeline_defaults(Path("."))

    parser = argparse.ArgumentParser(description="系统有效性验证（热力图分析）")
    parser.add_argument("--start", type=str, help="开始日期 (YYYYMMDD)")
    parser.add_argument("--end", type=str, help="结束日期 (YYYYMMDD)")
    parser.add_argument("--model", type=str, help="模型文件路径")
    parser.add_argument("--force", "-f", action="store_true", help="强制重新计算")
    parser.add_argument("--output", "-o", type=str, help="输出CSV文件路径")
    args = parser.parse_args()

    base_dir = Path(".")
    cache_dir = base_dir / "datasets" / "cache"

    log_stage(logger, 1, 3, "检测缓存数据")
    ensure_cache_for_training(
        cache_dir=cache_dir,
        train_months=defaults.heatmap.months,
        auto_sync=True,
    )

    analyzer = HeatmapAnalyzer(
        cache_dir=cache_dir,
        model_dir=base_dir / "datasets" / "models",
        report_dir=base_dir / "reports",
    )

    resolved_model_path = args.model
    if resolved_model_path is None and defaults.heatmap.model_filename:
        resolved_model_path = str(base_dir / "datasets" / "models" / defaults.heatmap.model_filename)

    result = analyzer.run(
        start_date=args.start,
        end_date=args.end,
        model_path=resolved_model_path,
        force=args.force,
    )

    if args.output:
        df = result.to_dataframe()
        df.to_csv(args.output, index=False)
        logger.info(f"结果已保存: {args.output}")
    else:
        heatmap_cache_dir = base_dir / "datasets" / "cache" / "heatmap"
        heatmap_cache_dir.mkdir(parents=True, exist_ok=True)
        output_path = heatmap_cache_dir / f"heatmap_history_{result.start_date}_{result.end_date}.csv"
        df = result.to_dataframe()
        df.to_csv(output_path, index=False)

    log_banner(logger, "热力图分析完成！", width=60)
    if result.image_path:
        logger.info(f"热力图图片: {result.image_path}")
    logger.info(f"HTML报告: reports/heatmap_report_{result.start_date}_{result.end_date}.html")
    logger.info(f"历史数据: data/cache/heatmap/heatmap_history_{result.start_date}_{result.end_date}.csv")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
