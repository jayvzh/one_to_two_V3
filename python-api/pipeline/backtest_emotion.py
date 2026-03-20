"""Emotion layer backtest pipeline (pipeline layer).

This module contains:
- BacktestRecord: Single backtest record
- EmotionBacktestResult: Aggregated backtest result
- EmotionLayerBacktest: Emotion layer backtest pipeline

Design Principles:
- Independent module (no dependency on daily.py)
- Outputs structured data only (no HTML)
- Can output CSV for verification
- Uses core modules for calculation
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
from core.scoring import calc_one_to_two, detect_first_board
from data.ak import AkshareDataSource, ZtRepository
from data.sync_cache import ensure_cache_for_training
from data.trade_calendar import TradingCalendar
from pipeline.config import load_pipeline_defaults
from pipeline.report import BacktestResult, EmotionLayerStats, generate_backtest_html


@dataclass
class BacktestRecord:
    """Single backtest record for a stock."""
    date: str
    symbol: str
    emotion_score: float
    emotion_level: str
    allow_trade: bool
    success_1to2: int


@dataclass
class EmotionBacktestResult:
    """Complete result of emotion layer backtest."""
    start_date: str
    end_date: str
    total_samples: int
    total_days: int
    records: list[BacktestRecord] = field(default_factory=list)
    layer_stats: list[EmotionLayerStats] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dataframe(self) -> pd.DataFrame:
        """Convert records to DataFrame."""
        if not self.records:
            return pd.DataFrame()

        data = [
            {
                "date": r.date,
                "symbol": r.symbol,
                "emotion_score": r.emotion_score,
                "emotion_level": r.emotion_level,
                "allow_trade": r.allow_trade,
                "success_1to2": r.success_1to2,
            }
            for r in self.records
        ]
        return pd.DataFrame(data)

    def to_summary_dataframe(self) -> pd.DataFrame:
        """Convert layer stats to DataFrame."""
        if not self.layer_stats:
            return pd.DataFrame()

        data = [
            {
                "emotion_score": s.emotion_score,
                "sample_count": s.sample_count,
                "success_count": s.success_count,
                "success_rate": s.success_rate,
                "allow_trade": s.allow_trade,
            }
            for s in self.layer_stats
        ]
        return pd.DataFrame(data)


class EmotionLayerBacktest:
    """Emotion layer backtest pipeline.
    
    Performs historical backtest to analyze one-to-two success rate
    across different emotion score layers.
    
    Usage:
        backtest = EmotionLayerBacktest(cache_dir=Path("./data/cache"))
        result = backtest.run(start_date="20260101", end_date="20260115")
        result.to_dataframe().to_csv("backtest_result.csv")
    """

    DEFAULT_WINDOW_DAYS = 64

    def __init__(
        self,
        cache_dir: Path,
        zt_cache_mode: str = "read",
    ):
        """Initialize emotion layer backtest.
        
        Args:
            cache_dir: Directory for cache files
            zt_cache_mode: Cache mode for ZtRepository
        """
        self.cache_dir = cache_dir
        self.data_source = AkshareDataSource()
        self.calendar = TradingCalendar(cache_dir=cache_dir)

        self.zt_repo = ZtRepository(
            data_source=self.data_source,
            cache_dir=cache_dir / "zt",
            cache_mode=zt_cache_mode,
        )

        self.emotion_analyzer = MarketEmotionAnalyzer()

    def run(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        window_days: int = DEFAULT_WINDOW_DAYS,
        force: bool = False,
    ) -> EmotionBacktestResult:
        """Run emotion layer backtest.
        
        Args:
            start_date: Start date (YYYYMMDD), if None, uses window_days from end_date
            end_date: End date (YYYYMMDD), if None, uses today
            window_days: Number of trading days to backtest
            force: Force recalculation, ignore cache
            
        Returns:
            EmotionBacktestResult with all backtest data
        """
        start_time = time.time()

        cache_start, cache_end = self._detect_cache_range()

        if end_date is None:
            end_date = cache_end if cache_end else datetime.now().strftime("%Y%m%d")

        if start_date is None:
            defaults = load_pipeline_defaults(Path("."))
            default_months = defaults.emotion_backtest.months
            start_date = self._get_default_start_date(end_date, months=default_months)
            logger.info(f"默认分析范围: 最近{default_months}个月 ({start_date} ~ {end_date})")

        start_date = self.calendar.normalize_date(start_date)
        end_date = self.calendar.normalize_date(end_date)

        logger.info(f"回测区间: {start_date} ~ {end_date}")

        emotion_cache_dir = self.cache_dir / "emotion"
        emotion_cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = emotion_cache_dir / f"emotion_backtest_{start_date}_{end_date}.json"

        if not force and cache_file.exists():
            cached_result = self._load_cache(cache_file)
            if cached_result is not None:
                logger.info("使用缓存结果")
                return cached_result

        records = self._run_backtest(start_date, end_date)

        if not records:
            logger.warning("无有效回测数据")
            if cache_file.exists():
                cache_file.unlink()
                logger.info("已清除无效缓存")
            return EmotionBacktestResult(
                start_date=start_date,
                end_date=end_date,
                total_samples=0,
                total_days=0,
            )

        layer_stats = self._aggregate_by_emotion(records)

        duration = time.time() - start_time

        result = EmotionBacktestResult(
            start_date=start_date,
            end_date=end_date,
            total_samples=len(records),
            total_days=len(set(r.date for r in records)),
            records=records,
            layer_stats=layer_stats,
            duration_seconds=duration,
        )

        self._save_cache(cache_file, result)

        self._print_summary(result)

        return result

    def _get_start_date(self, end_date: str, window_days: int) -> str:
        """Calculate start date from end date and window."""
        end_dt = pd.to_datetime(end_date)
        start_dt = end_dt - pd.Timedelta(days=window_days * 2)
        return start_dt.strftime("%Y%m%d")

    def _get_default_start_date(self, end_date: str, months: int = 6) -> str:
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

    def _detect_cache_range(self) -> tuple[str | None, str | None]:
        """Detect available cache date range from zt cache files.
        
        Returns:
            Tuple of (earliest_date, latest_date) or (None, None) if no cache
        """
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

    def _run_backtest(self, start_date: str, end_date: str) -> list[BacktestRecord]:
        """Run backtest for each trading day.
        
        For each trading day T:
        1. Get previous day's (T-1) first-board stocks
        2. Calculate emotion score for T-1
        3. Check if each stock succeeded in T (became second-board)
        """
        records = []

        trade_dates = self._get_trade_dates(start_date, end_date)

        logger.info(f"回测区间 {start_date} ~ {end_date} 共 {len(trade_dates)} 个交易日")

        if len(trade_dates) < 2:
            logger.warning("交易日不足，无法进行回测")
            return records

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

                current_second_board = current_zt[current_zt["board_count"] == 2]
                success_codes = set(current_second_board["symbol"].tolist())

                for _, row in prev_first_board.iterrows():
                    symbol = row["symbol"]
                    success = 1 if symbol in success_codes else 0

                    records.append(BacktestRecord(
                        date=prev_date,
                        symbol=symbol,
                        emotion_score=emotion.score,
                        emotion_level=emotion.level,
                        allow_trade=emotion.allow_trade,
                        success_1to2=success,
                    ))

            except Exception as e:
                logger.warning(f"处理日期 {current_date} 时出错: {e}")
                continue

        return records

    def _get_trade_dates(self, start_date: str, end_date: str) -> list[str]:
        """Get list of trade dates in range."""
        logger.debug(f"获取交易日: start={start_date}, end={end_date}")
        
        df = self.calendar._load_calendar()
        all_dates = df["date"].tolist()
        
        start_dash = self.calendar._to_dash_date(start_date)
        end_dash = self.calendar._to_dash_date(end_date)
        
        dates = [
            d.replace("-", "")
            for d in all_dates
            if start_dash <= d <= end_dash
        ]
        
        logger.debug(f"找到 {len(dates)} 个交易日")
        return dates

    def _aggregate_by_emotion(self, records: list[BacktestRecord]) -> list[EmotionLayerStats]:
        """Aggregate records by emotion score."""
        df = pd.DataFrame([
            {
                "emotion_score": r.emotion_score,
                "success_1to2": r.success_1to2,
                "allow_trade": r.allow_trade,
            }
            for r in records
        ])

        if df.empty:
            return []

        grouped = df.groupby("emotion_score").agg(
            sample_count=("success_1to2", "count"),
            success_count=("success_1to2", "sum"),
            allow_trade=("allow_trade", "first"),
        ).reset_index()

        stats = []
        for _, row in grouped.iterrows():
            success_rate = row["success_count"] / row["sample_count"] if row["sample_count"] > 0 else 0
            stats.append(EmotionLayerStats(
                emotion_score=row["emotion_score"],
                sample_count=int(row["sample_count"]),
                success_count=int(row["success_count"]),
                success_rate=round(success_rate, 4),
                allow_trade=row["allow_trade"],
            ))

        return sorted(stats, key=lambda x: x.emotion_score)

    def _load_cache(self, cache_file: Path) -> EmotionBacktestResult | None:
        """Load result from cache file."""
        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)

            records = [
                BacktestRecord(
                    date=r["date"],
                    symbol=r["symbol"],
                    emotion_score=r["emotion_score"],
                    emotion_level=r["emotion_level"],
                    allow_trade=r["allow_trade"],
                    success_1to2=r["success_1to2"],
                )
                for r in data.get("records", [])
            ]

            layer_stats = [
                EmotionLayerStats(
                    emotion_score=s["emotion_score"],
                    sample_count=s["sample_count"],
                    success_count=s["success_count"],
                    success_rate=s["success_rate"],
                    allow_trade=s["allow_trade"],
                )
                for s in data.get("layer_stats", [])
            ]

            return EmotionBacktestResult(
                start_date=data["start_date"],
                end_date=data["end_date"],
                total_samples=data["total_samples"],
                total_days=data["total_days"],
                records=records,
                layer_stats=layer_stats,
                duration_seconds=data.get("duration_seconds", 0),
            )
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return None

    def _save_cache(self, cache_file: Path, result: EmotionBacktestResult) -> None:
        """Save result to cache file."""
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "start_date": result.start_date,
            "end_date": result.end_date,
            "total_samples": result.total_samples,
            "total_days": result.total_days,
            "duration_seconds": result.duration_seconds,
            "records": [
                {
                    "date": r.date,
                    "symbol": r.symbol,
                    "emotion_score": r.emotion_score,
                    "emotion_level": r.emotion_level,
                    "allow_trade": r.allow_trade,
                    "success_1to2": r.success_1to2,
                }
                for r in result.records
            ],
            "layer_stats": [
                {
                    "emotion_score": s.emotion_score,
                    "sample_count": s.sample_count,
                    "success_count": s.success_count,
                    "success_rate": s.success_rate,
                    "allow_trade": s.allow_trade,
                }
                for s in result.layer_stats
            ],
        }

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"结果已缓存: {cache_file}")

    def _print_summary(self, result: EmotionBacktestResult) -> None:
        """Print backtest summary."""
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

        logger.info(f"总样本数: {result.total_samples}")
        logger.info(f"交易日数: {result.total_days}")
        logger.info(f"计算耗时: {duration_str}")
        logger.info("情绪分层统计:")
        logger.info(f"{'情绪分数':<8} {'样本数':<8} {'成功率':<10} {'可交易':<6}")
        logger.info("-" * 40)

        for stat in result.layer_stats:
            trade_str = "✓" if stat.allow_trade else "✗"
            logger.info(f"{stat.emotion_score:<8.1f} {stat.sample_count:<8} {stat.success_rate*100:<10.2f}% {trade_str:<6}")


def main() -> None:
    """Main entry point."""
    import argparse

    defaults = load_pipeline_defaults(Path("."))

    parser = argparse.ArgumentParser(description="情绪分层回测")
    parser.add_argument("--start", type=str, help="开始日期 (YYYYMMDD)")
    parser.add_argument("--end", type=str, help="结束日期 (YYYYMMDD)")
    parser.add_argument("--window", type=int, default=defaults.emotion_backtest.window_days, help=f"回测窗口天数 (默认: {defaults.emotion_backtest.window_days})")
    parser.add_argument("--force", "-f", action="store_true", help="强制重新计算")
    parser.add_argument("--output", "-o", type=str, help="输出CSV文件路径")
    parser.add_argument("--report", "-r", action="store_true", help="生成HTML报告")
    args = parser.parse_args()

    base_dir = Path(".")
    cache_dir = base_dir / "datasets" / "cache"

    log_banner(logger, "情绪分层回测启动")

    log_stage(logger, 1, 3, "检测缓存数据")

    availability = ensure_cache_for_training(
        cache_dir=cache_dir,
        train_months=defaults.emotion_backtest.cache_check_months,
        auto_sync=True,
    )
    availability.print_summary(compact=True)

    if not availability.is_sufficient:
        logger.error("缓存数据不足，无法执行回测")
        logger.error("请检查网络连接后重试，或手动运行: python -m src.data.sync_cache")
        return

    log_stage(logger, 2, 3, "执行回测计算")

    backtest = EmotionLayerBacktest(
        cache_dir=cache_dir,
        zt_cache_mode="read",
    )

    result = backtest.run(
        start_date=args.start,
        end_date=args.end,
        window_days=args.window,
        force=args.force,
    )

    log_stage(logger, 3, 3, "输出结果")

    report_path_str = ""

    if args.output:
        df = result.to_dataframe()
        df.to_csv(args.output, index=False)
        logger.info(f"结果已保存: {args.output}")
    else:
        emotion_cache_dir = base_dir / "datasets" / "cache" / "emotion"
        emotion_cache_dir.mkdir(parents=True, exist_ok=True)
        output_path = emotion_cache_dir / f"emotion_backtest_{result.start_date}_{result.end_date}.csv"
        df = result.to_dataframe()
        df.to_csv(output_path, index=False)
        logger.info(f"详细结果: {output_path}")

        summary_path = emotion_cache_dir / f"emotion_backtest_summary_{result.start_date}_{result.end_date}.csv"
        summary_df = result.to_summary_dataframe()
        summary_df.to_csv(summary_path, index=False)
        logger.info(f"汇总结果: {summary_path}")

    if args.report or True:
        report_result = BacktestResult(
            start_date=result.start_date,
            end_date=result.end_date,
            total_samples=result.total_samples,
            total_days=result.total_days,
            layer_stats=result.layer_stats,
            duration_seconds=result.duration_seconds,
        )

        report_dir = base_dir / "reports"
        report_path = report_dir / f"backtest_report_{result.start_date}_{result.end_date}.html"
        html_path = generate_backtest_html(report_result, str(report_path))
        report_path_str = html_path

    log_banner(logger, "情绪分层回测完成！")
    if report_path_str:
        logger.info(f"HTML报告: {report_path_str}")
    log_metrics(logger, "回测摘要", total_days=result.total_days, total_samples=result.total_samples, duration_seconds=round(result.duration_seconds, 2))
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
