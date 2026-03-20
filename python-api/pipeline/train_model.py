"""Production model training script.

This script trains a model using the most recent N months of data,
designed to provide a production-ready model for daily scoring.

Usage:
    python -m src.pipeline.train_model              # Use last 6 months
    python -m src.pipeline.train_model --months 4   # Use last 4 months
    python -m src.pipeline.train_model --start 20250801 --end 20260215
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from core.logging import get_logger, log_banner, log_metrics, log_stage

logger = get_logger(__name__)

from core.features import MarketFeatureBuilder, StockFeatureBuilder
from core.label import OneToTwoLabelBuilder
from core.scoring import calc_one_to_two
from data.ak import AkshareDataSource, IndexRepository, ZtRepository
from data.cache import get_index_cache_range, get_zt_cache_range
from data.prepare import build_training_data
from data.sync_cache import ensure_cache_for_training
from data.trade_calendar import TradingCalendar
from ml.trainer import ModelMeta, OneToTwoDatasetBuilder, OneToTwoPredictor
from pipeline.config import load_pipeline_defaults


def train_production_model(
    base_dir: Path,
    train_months: int = 6,
    start_date: str | None = None,
    end_date: str | None = None,
    verbose: bool = True,
) -> tuple[Path, ModelMeta]:
    """Train a production model using recent data.
    
    Args:
        base_dir: Base directory for data
        train_months: Number of months to use for training
        start_date: Optional start date (overrides train_months)
        end_date: Optional end date (defaults to latest trade day)
        verbose: Print progress information
        
    Returns:
        Tuple of (model_path, model_meta)
    """
    cache_dir = base_dir / "datasets" / "cache"
    model_dir = base_dir / "datasets" / "models"
    snapshot_dir = base_dir / "datasets" / "snapshots"

    calendar = TradingCalendar(cache_dir=cache_dir)
    data_source = AkshareDataSource()

    index_repo = IndexRepository(
        data_source=data_source,
        cache_dir=cache_dir / "index",
        calendar=calendar,
    )
    zt_repo = ZtRepository(
        data_source=data_source,
        cache_dir=cache_dir / "zt",
    )

    market_feature_builder = MarketFeatureBuilder()
    stock_feature_builder = StockFeatureBuilder()
    label_builder = OneToTwoLabelBuilder(
        get_next_trade_day=calendar.next_trade_day
    )
    dataset_builder = OneToTwoDatasetBuilder()
    model = OneToTwoPredictor()

    zt_range = get_zt_cache_range(cache_dir)
    index_range = get_index_cache_range(cache_dir, "000300")

    if zt_range.available and index_range.available:
        cache_end_date = min(zt_range.end_date, index_range.end_date)
    else:
        cache_end_date = None

    if end_date is None:
        if cache_end_date:
            end_date = calendar.prev_trade_day(cache_end_date)
            if verbose:
                logger.info(f"训练结束日期: {end_date} (缓存结束日期 {cache_end_date} 的前一个交易日)")
                logger.info("  - 确保不使用当天的临时数据")
                logger.info("  - 确保有第二天的数据计算一进二成功率")
        else:
            end_date = calendar.get_recent_trade_day(datetime.now().strftime("%Y%m%d"))
    elif cache_end_date and int(end_date) > int(cache_end_date):
        logger.warning(f"请求的结束日期 {end_date} 超出缓存范围，调整为 {cache_end_date}")
        end_date = cache_end_date

    if start_date is None:
        end_dt = pd.to_datetime(end_date)
        start_dt = end_dt - pd.DateOffset(months=train_months)
        start_date = start_dt.strftime("%Y%m%d")
        start_date = calendar.normalize_date(start_date)
        if not calendar.is_trade_day(start_date):
            start_date = calendar.get_recent_trade_day(start_date)
            if verbose:
                logger.info(f"开始日期调整为最近的交易日: {start_date}")

    start_date = calendar.normalize_date(start_date)
    end_date = calendar.normalize_date(end_date)

    if cache_end_date:
        cache_end_dt = pd.to_datetime(cache_end_date)
        start_dt = pd.to_datetime(start_date)
        days_diff = (cache_end_dt - start_dt).days
        
        if days_diff < 2:
            raise ValueError(
                f"缓存数据不足: 缓存结束日期 {cache_end_date} 与训练开始日期 {start_date} 相差不足2天\n"
                f"提示: 需要至少2天的数据来计算一进二成功率"
            )

    if verbose:
        logger.info(f"训练区间: {start_date} ~ {end_date}")

    zt_cache_dir = cache_dir / "zt"
    raw_df = build_training_data(
        zt_cache_dir=zt_cache_dir,
        date_range=(start_date, end_date),
        verbose=verbose,
    )

    if raw_df.empty:
        raise ValueError(f"无训练数据: {start_date} ~ {end_date}")

    raw_df["date"] = raw_df["date"].astype(str)
    stock_features = stock_feature_builder.build_history(raw_df)
    stock_features = stock_features[
        (stock_features["date"] >= start_date)
        & (stock_features["date"] <= end_date)
    ].copy()

    if verbose:
        logger.info(f"股票特征: {len(stock_features)} 条")

    labeled_df = label_builder.build(
        stock_features,
        drop_last_unlabeled=True,
        normalize_date=calendar.normalize_date,
    )

    if verbose:
        logger.info(f"标注样本: {len(labeled_df)} 条")

    if len(labeled_df) == 0:
        raise ValueError(f"训练集为空: {start_date} ~ {end_date}")

    prev_date = calendar.prev_trade_day(end_date)
    index_df = index_repo.get_daily(start=prev_date, end=end_date, allow_partial=True)
    today_zt, _ = zt_repo.get_by_date(end_date)
    prev_zt, _ = zt_repo.get_by_date(prev_date)
    one_to_two = calc_one_to_two(date=prev_date, today_zt=prev_zt, next_day_zt=today_zt)
    market_features = market_feature_builder.build(
        date=end_date,
        one_to_two=one_to_two,
        zt_count_today=len(today_zt),
        index_df=index_df,
    ).to_frame()

    train_dataset = dataset_builder.build(
        stock_features=labeled_df,
        market_features=market_features,
        label_col="label",
    )

    if verbose:
        logger.info("训练模型...")

    model.fit(train_dataset)

    base_success_rate = float(train_dataset.y.mean())

    meta = ModelMeta(
        train_start=start_date,
        train_end=end_date,
        sample_size=len(train_dataset.X),
        base_success_rate=base_success_rate,
        features=train_dataset.feature_names,
        model_type="logistic_regression",
        version=datetime.now().strftime("%Y-%m-%d"),
    )

    model_dir.mkdir(parents=True, exist_ok=True)

    model_path = model_dir / "model_latest.joblib"
    model.save(str(model_path), meta=meta)

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / "train_latest.csv"
    labeled_df.to_csv(snapshot_path, index=False)

    if verbose:
        logger.info("模型训练完成")
        logger.info(f"  样本数: {len(train_dataset.X)}")
        logger.info(f"  基础胜率: {base_success_rate:.2%}")
        logger.info(f"  模型: {model_path}")

    return model_path, meta


def main() -> None:
    """Main entry point."""
    defaults = load_pipeline_defaults(Path("."))

    parser = argparse.ArgumentParser(
        description="训练生产模型"
    )
    parser.add_argument(
        "--months", "-m",
        type=int,
        default=defaults.production_train.months,
        help=f"训练数据月数 (默认: {defaults.production_train.months})"
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
    args = parser.parse_args()

    base_dir = Path(".")
    cache_dir = base_dir / "datasets" / "cache"

    log_banner(logger, "生产模型训练")

    log_stage(logger, 1, 3, "检测缓存数据")

    availability = ensure_cache_for_training(
        cache_dir=cache_dir,
        train_months=max(args.months, defaults.production_train.cache_check_months),
        auto_sync=True,
    )
    availability.print_summary(compact=True)

    if not availability.is_sufficient:
        logger.error("缓存数据不足，无法进行训练")
        logger.error("请检查网络连接后重试，或手动运行: python -m src.data.sync_cache")
        return

    log_stage(logger, 2, 3, "训练模型")

    try:
        model_path, meta = train_production_model(
            base_dir=base_dir,
            train_months=args.months,
            start_date=args.start,
            end_date=args.end,
            verbose=True,
        )
    except Exception as e:
        logger.error(f"模型训练失败: {e}")
        return

    log_stage(logger, 3, 3, "完成")
    logger.info(f"模型文件: {model_path}")
    logger.info(f"训练区间: {meta.train_start} ~ {meta.train_end}")
    logger.info(f"样本数量: {meta.sample_size}")
    logger.info(f"基础胜率: {meta.base_success_rate:.2%}")
    log_metrics(logger, "训练结果", samples=meta.sample_size, base_success_rate=meta.base_success_rate)

    log_banner(logger, "训练完成")


if __name__ == "__main__":
    main()
