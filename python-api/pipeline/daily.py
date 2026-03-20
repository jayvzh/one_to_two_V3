"""Daily scorer pipeline (pipeline layer).

This module contains:
- DailyScorer: Orchestrate daily scoring workflow
- DailyResult: Structured result for daily report

Design Principles:
- Only responsible for orchestration
- No business logic implementation (delegates to core)
- No data fetching (delegates to data)
- Returns structured result (report.py handles HTML)
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from core.logging import get_logger, log_banner, log_metrics, log_stage

logger = get_logger(__name__)

from core.emotion import EmotionMetrics, MarketEmotionAnalyzer
from core.features import MarketFeatureBuilder, StockFeatureBuilder
from core.rules import TradeDecision, TradeRuleEngine
from core.scoring import calc_one_to_two, detect_first_board
from data.ak import AkshareDataSource, IndexRepository, ZtRepository
from data.sync_cache import ensure_cache_for_training
from data.trade_calendar import TradingCalendar
from ml.trainer import ModelMeta, OneToTwoPredictor
from pipeline.config import load_pipeline_defaults
from pipeline.report import (
    DailyResult,
    FirstBoardStats,
    ModelScoreStats,
    StockScore,
    build_model_score_stats,
    generate_daily_html,
)


class DailyScorer:
    """Daily scorer for one-to-two strategy.
    
    Orchestrates data flow through all layers:
    data → core → model → result
    """

    def __init__(
        self,
        cache_dir: Path,
        model_dir: Path,
        report_dir: Path,
        cache_mode: str = "read_write",
        preferred_model_filename: str | None = None,
    ):
        """Initialize daily scorer.
        
        Args:
            cache_dir: Directory for cache files
            model_dir: Directory for model files
            report_dir: Directory for report output
            cache_mode: Cache mode (off | read | read_write)
            preferred_model_filename: Preferred model filename in model_dir
        """
        self.cache_dir = cache_dir
        self.model_dir = model_dir
        self.report_dir = report_dir
        self.preferred_model_filename = preferred_model_filename

        self.data_source = AkshareDataSource()
        self.calendar = TradingCalendar(cache_dir=cache_dir)

        self.zt_repo = ZtRepository(
            data_source=self.data_source,
            cache_dir=cache_dir / "zt",
            cache_mode=cache_mode,
            calendar=self.calendar,
        )

        self.index_repo = IndexRepository(
            data_source=self.data_source,
            cache_dir=cache_dir / "index",
            calendar=self.calendar,
            cache_mode=cache_mode,
        )

        self.emotion_analyzer = MarketEmotionAnalyzer()
        self.trade_rule_engine = TradeRuleEngine()
        self.market_feature_builder = MarketFeatureBuilder()
        self.stock_feature_builder = StockFeatureBuilder()
        self.model = OneToTwoPredictor()
        self.model_meta: ModelMeta | None = None

    def run(self, date: str, generate_report: bool = True) -> DailyResult:
        """Run daily scoring for a specific date.
        
        Args:
            date: Date string (YYYYMMDD)
            generate_report: Whether to generate HTML report
            
        Returns:
            DailyResult with all scoring data
        """
        date = self.calendar.normalize_date(date)

        if not self.calendar.is_trade_day(date):
            adjusted_date = self.calendar.get_recent_trade_day(date)
            logger.info(f"{date} 不是交易日，调整为: {adjusted_date}")
            date = adjusted_date

        logger.info(f"[DailyScorer] 执行日期: {date}")

        prev_date = self.calendar.prev_trade_day(date)

        today_zt, today_is_intraday = self.zt_repo.get_by_date(date)
        prev_zt, prev_is_intraday = self.zt_repo.get_by_date(prev_date)

        zt_count_today = len(today_zt)
        zt_count_prev = len(prev_zt)

        data_not_ready = today_zt.empty
        is_intraday = today_is_intraday

        if is_intraday:
            logger.info("当前为盘中时段（16:00前），涨停数据可能变动，将生成盘中报告")

        if data_not_ready:
            logger.warning("当日涨停数据未就绪，使用历史数据计算一进二成功率")
            next_day_date = prev_date
            next_day_zt, _ = prev_zt, prev_is_intraday
            while next_day_zt.empty:
                next_day_date = self.calendar.prev_trade_day(next_day_date)
                next_day_zt, _ = self.zt_repo.get_by_date(next_day_date)
            today_date = self.calendar.prev_trade_day(next_day_date)
            today_zt_for_calc, _ = self.zt_repo.get_by_date(today_date)
            while today_zt_for_calc.empty:
                today_date = self.calendar.prev_trade_day(today_date)
                today_zt_for_calc, _ = self.zt_repo.get_by_date(today_date)
            logger.info(f"使用 {today_date} -> {next_day_date} 的数据计算一进二成功率")
            one_to_two = calc_one_to_two(
                date=today_date,
                today_zt=today_zt_for_calc,
                next_day_zt=next_day_zt,
            )
        else:
            one_to_two = calc_one_to_two(
                date=prev_date,
                today_zt=prev_zt,
                next_day_zt=today_zt,
            )

        max_board_height = int(today_zt["board_count"].max()) if not today_zt.empty else 0

        emotion_metrics = EmotionMetrics(
            success_rate=one_to_two.success_rate,
            max_board_height=max_board_height,
            zt_count_today=zt_count_today,
            zt_count_yesterday=zt_count_prev,
        )

        emotion = self.emotion_analyzer.score(emotion_metrics)

        decision = self.trade_rule_engine.decide(emotion)

        try:
            index_df = self.index_repo.get_daily(
                start=prev_date,
                end=date,
            )
        except ValueError as e:
            if "指数数据不足" in str(e):
                logger.warning(f"当日指数数据未就绪，使用上一交易日数据: {prev_date}")
                index_df = self.index_repo.get_daily(
                    start=prev_date,
                    end=prev_date,
                    allow_partial=True,
                )
            else:
                raise

        market_features = self.market_feature_builder.build(
            date=date,
            one_to_two=one_to_two,
            zt_count_today=zt_count_today,
            index_df=index_df,
        )

        logger.info(f"一进二成功率: {one_to_two.success_rate:.2%}")
        logger.info(f"情绪分数: {emotion.score} ({emotion.level})")
        logger.info(f"交易决策: {decision.mode}")

        emotion_detail = {
            "rate_1to2": one_to_two.success_rate,
            "max_height": max_board_height,
            "zt_trend": zt_count_today - zt_count_prev,
            **emotion.detail,
        }

        first_board = detect_first_board(today_zt)
        first_board_stats = self._build_first_board_stats(first_board)

        stocks, model_score_stats = self._score_stocks(
            first_board=first_board,
            market_features=market_features,
            allow_trade=decision.allow_trade,
        )

        trade_status = self._get_trade_status(decision)

        result = DailyResult(
            date=date,
            emotion_score=emotion.score,
            emotion_level=emotion.level,
            emotion_detail=emotion_detail,
            trade_status=trade_status,
            allow_trade=decision.allow_trade,
            stocks=stocks,
            first_board_stats=first_board_stats,
            model_score_stats=model_score_stats,
            model_meta=self.model_meta,
            is_intraday=is_intraday,
        )

        if generate_report:
            base_report_path = self.report_dir / f"daily_report_{date}.html"
            if is_intraday:
                intraday_report_path = self.report_dir / f"daily_report_{date}_intraday.html"
                n = 1
                while intraday_report_path.exists():
                    intraday_report_path = self.report_dir / f"daily_report_{date}_intraday_{n}.html"
                    n += 1
                report_path = intraday_report_path
                logger.info(f"生成盘中报告: {report_path.name}")
            elif data_not_ready and base_report_path.exists():
                n = 1
                while True:
                    report_path = self.report_dir / f"daily_report_{date}_{n}.html"
                    if not report_path.exists():
                        break
                    n += 1
                logger.info(f"当日数据未就绪，已有报告存在，生成新文件: {report_path.name}")
            else:
                report_path = base_report_path
            html_path = generate_daily_html(result, str(report_path))
            logger.info(f"日报已生成: {html_path}")

        return result

    def _load_model(self) -> bool:
        """Load latest model from model directory.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        if self.preferred_model_filename:
            preferred_model = self.model_dir / self.preferred_model_filename
            if preferred_model.exists():
                logger.info(f"加载配置模型: {preferred_model}")
                self.model.load(str(preferred_model))
                self.model_meta = OneToTwoPredictor.load_meta(str(preferred_model))
                return True
            logger.warning(f"配置模型不存在，回退到最新模型: {preferred_model}")

        model_files = list(self.model_dir.glob("model_*.joblib"))
        if not model_files:
            logger.warning("未找到模型文件")
            return False

        latest_model = sorted(model_files)[-1]
        logger.info(f"加载模型: {latest_model}")

        self.model.load(str(latest_model))
        self.model_meta = OneToTwoPredictor.load_meta(str(latest_model))

        return True

    def _build_first_board_stats(self, first_board: pd.DataFrame) -> FirstBoardStats | None:
        """Build first board statistics.
        
        Args:
            first_board: DataFrame with first board stocks
            
        Returns:
            FirstBoardStats or None if no data
        """
        if first_board.empty:
            return None

        count = len(first_board)

        avg_turnover = first_board["turnover"].mean() if "turnover" in first_board.columns else 0.0

        avg_circ_mv = (first_board["circ_mv"] / 1e8).mean() if "circ_mv" in first_board.columns else 0.0

        early_seal_ratio = 0.0
        if "first_seal_time" in first_board.columns:
            early_seal_ratio = (first_board["first_seal_time"].astype(str).str[:4] < "1030").mean()
        elif "is_early_seal" in first_board.columns:
            early_seal_ratio = first_board["is_early_seal"].mean()

        return FirstBoardStats(
            count=count,
            avg_turnover=float(avg_turnover),
            avg_circ_mv=float(avg_circ_mv),
            early_seal_ratio=float(early_seal_ratio),
        )

    def _score_stocks(
        self,
        first_board: pd.DataFrame,
        market_features,
        allow_trade: bool,
    ) -> tuple[list[StockScore], list[ModelScoreStats]]:
        """Score first board stocks using model.
        
        Args:
            first_board: DataFrame with first board stocks
            market_features: MarketFeatures object
            allow_trade: Whether trading is allowed
            
        Returns:
            Tuple of (stock scores, model score statistics)
        """
        if first_board.empty:
            return [], []

        if not self._load_model():
            return [], []

        stock_features = self.stock_feature_builder.build(first_board)

        stock_features["is_limit_up"] = 1

        mf_df = market_features.to_frame()
        if len(mf_df) == 1:
            mf_df = pd.concat([mf_df] * len(stock_features), ignore_index=True)

        X = pd.concat([stock_features.reset_index(drop=True), mf_df.reset_index(drop=True)], axis=1)

        if self.model_meta is not None:
            feature_cols = self.model_meta.features
            X = X[feature_cols].copy()

        scores = self.model.predict_proba(X)

        first_board = first_board.copy()
        first_board["model_score"] = scores.values

        sorted_df = first_board.sort_values("model_score", ascending=False)

        if allow_trade:
            top_stocks = sorted_df.head(10)
        else:
            top_stocks = pd.DataFrame()

        stocks = []
        for _, row in top_stocks.iterrows():
            stocks.append(StockScore(
                symbol=str(row.get("symbol", "")),
                name=str(row.get("name", "")),
                model_score=float(row["model_score"]),
                turnover=float(row.get("turnover", 0)),
                circ_mv=float(row.get("circ_mv", 0)) / 1e8,
            ))

        model_score_stats = build_model_score_stats(scores)

        return stocks, model_score_stats

    def _get_trade_status(self, decision: TradeDecision) -> str:
        """Get trade status string from decision.
        
        Args:
            decision: TradeDecision object
            
        Returns:
            Trade status string
        """
        if decision.mode == "aggressive":
            return "强势交易期"
        elif decision.mode == "selective":
            return "精选交易期"
        else:
            return "观察期（不出手）"


def main() -> None:
    """Main entry point."""
    base_dir = Path(".")
    defaults = load_pipeline_defaults(base_dir)
    cache_dir = base_dir / "datasets" / "cache"

    log_banner(logger, "每日评分启动")

    log_stage(logger, 1, 3, "检测缓存数据")

    availability = ensure_cache_for_training(
        cache_dir=cache_dir,
        train_months=defaults.daily.cache_check_months,
        auto_sync=True,
    )
    availability.print_summary(compact=True)

    if not availability.is_sufficient:
        logger.error("缓存数据不足，无法执行每日评分")
        logger.error("请检查网络连接后重试，或手动运行: python -m src.data.sync_cache")
        return

    log_stage(logger, 2, 3, "加载模型与数据")

    scorer = DailyScorer(
        cache_dir=cache_dir,
        model_dir=base_dir / "datasets" / "models",
        report_dir=base_dir / "reports",
        cache_mode="read_write",
        preferred_model_filename=defaults.daily.model_filename,
    )

    today = datetime.now().strftime("%Y%m%d")
    result = scorer.run(today)

    log_stage(logger, 3, 3, "评分结果")
    logger.info(f"日期: {result.date}")
    logger.info(f"情绪分数: {result.emotion_score}")
    logger.info(f"交易状态: {result.trade_status}")
    logger.info(f"候选股票: {len(result.stocks)} 只")
    log_metrics(logger, "关键结果", date=result.date, emotion_score=result.emotion_score, candidates=len(result.stocks))

    log_banner(logger, "每日评分结束")


if __name__ == "__main__":
    main()
