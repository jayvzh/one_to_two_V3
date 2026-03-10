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

from src.data.trade_calendar import TradingCalendar
from src.data.ak import AkshareDataSource, IndexRepository, ZtRepository
from src.data.prepare import build_training_data
from src.core.scoring import calc_one_to_two
from src.core.features import MarketFeatureBuilder, StockFeatureBuilder
from src.core.label import OneToTwoLabelBuilder
from src.model.trainer import OneToTwoDatasetBuilder, OneToTwoPredictor
from src.model.evaluator import ModelEvaluator, EvaluationMetrics


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
    cache_dir = base_dir / "data" / "cache"
    
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
    evaluator = ModelEvaluator()
    
    if verbose:
        print(f"训练区间: {train_start} ~ {train_end}")
        print(f"测试区间: {test_start} ~ {test_end}")
    
    zt_cache_dir = cache_dir / "zt"
    raw_df = build_training_data(
        zt_cache_dir=zt_cache_dir,
        date_range=(train_start, test_end),
        verbose=verbose,
    )
    
    raw_df["date"] = raw_df["date"].astype(str)
    stock_features = stock_feature_builder.build_history(raw_df)
    stock_features = stock_features[
        (stock_features["date"] >= train_start)
        & (stock_features["date"] <= test_end)
    ].copy()
    
    labeled_df = label_builder.build(
        stock_features,
        drop_last_unlabeled=True,
        normalize_date=calendar.normalize_date,
    )
    
    train_df = labeled_df[
        (labeled_df["date"] >= train_start)
        & (labeled_df["date"] <= train_end)
    ].copy()
    
    test_df = labeled_df[
        (labeled_df["date"] >= test_start)
        & (labeled_df["date"] <= test_end)
    ].copy()
    
    if verbose:
        print(f"训练样本: {len(train_df)}")
        print(f"测试样本: {len(test_df)}")
    
    prev_date = calendar.prev_trade_day(train_end)
    index_df = index_repo.get_daily(start=prev_date, end=train_end)
    today_zt, _ = zt_repo.get_by_date(train_end)
    prev_zt, _ = zt_repo.get_by_date(prev_date)
    one_to_two = calc_one_to_two(date=prev_date, today_zt=prev_zt, next_day_zt=today_zt)
    market_features = market_feature_builder.build(
        date=train_end,
        one_to_two=one_to_two,
        zt_count_today=len(today_zt),
        index_df=index_df,
    ).to_frame()
    
    train_dataset = dataset_builder.build(
        stock_features=train_df,
        market_features=market_features,
        label_col="label",
    )
    
    model.fit(train_dataset)
    
    test_dataset = dataset_builder.build(
        stock_features=test_df,
        market_features=market_features,
        label_col="label",
    )
    
    y_proba = model.predict_proba(test_dataset.X)
    y_true = test_dataset.y
    dates = test_df["date"].reset_index(drop=True)
    symbols = test_df["symbol"].reset_index(drop=True) if "symbol" in test_df.columns else None
    
    results = {}
    
    if verbose:
        print("\n" + "=" * 60)
        print("测试1: 正常模型评估 (每日Top5)")
        print("=" * 60)
    
    metrics_normal = evaluator.evaluate(
        y_true=y_true,
        y_proba=y_proba,
        train_start=train_start,
        train_end=train_end,
        test_start=test_start,
        test_end=test_end,
        dates=dates,
        symbols=symbols,
    )
    
    results["normal"] = {
        "auc": metrics_normal.auc,
        "top5_promotion_rate": metrics_normal.top5_promotion_rate,
        "top10_promotion_rate": metrics_normal.top10_promotion_rate,
        "overall_promotion_rate": metrics_normal.overall_promotion_rate,
    }
    
    if verbose:
        print(f"AUC: {metrics_normal.auc:.4f}")
        print(f"Top5 晋级率: {metrics_normal.top5_promotion_rate:.2%}")
        print(f"Top10 晋级率: {metrics_normal.top10_promotion_rate:.2%}")
        print(f"市场均值: {metrics_normal.overall_promotion_rate:.2%}")
        print(f"Top5 vs 市场: {metrics_normal.top5_promotion_rate - metrics_normal.overall_promotion_rate:+.2%}")
    
    if verbose:
        print("\n" + "=" * 60)
        print("测试2: 随机模型对照测试")
        print("=" * 60)
    
    np.random.seed(42)
    random_proba = pd.Series(np.random.random(len(y_true)), index=y_true.index)
    
    metrics_random = evaluator.evaluate(
        y_true=y_true,
        y_proba=random_proba,
        train_start=train_start,
        train_end=train_end,
        test_start=test_start,
        test_end=test_end,
        dates=dates,
        symbols=symbols,
    )
    
    results["random"] = {
        "auc": metrics_random.auc,
        "top5_promotion_rate": metrics_random.top5_promotion_rate,
        "top10_promotion_rate": metrics_random.top10_promotion_rate,
    }
    
    if verbose:
        print(f"随机 AUC: {metrics_random.auc:.4f}")
        print(f"随机 Top5 晋级率: {metrics_random.top5_promotion_rate:.2%}")
        print(f"随机 Top10 晋级率: {metrics_random.top10_promotion_rate:.2%}")
        print(f"市场均值: {metrics_random.overall_promotion_rate:.2%}")
    
    if verbose:
        print("\n" + "=" * 60)
        print("测试3: 反向排序测试 (最低分Top5)")
        print("=" * 60)
    
    reverse_proba = 1 - y_proba
    
    metrics_reverse = evaluator.evaluate(
        y_true=y_true,
        y_proba=reverse_proba,
        train_start=train_start,
        train_end=train_end,
        test_start=test_start,
        test_end=test_end,
        dates=dates,
        symbols=symbols,
    )
    
    results["reverse"] = {
        "auc": metrics_reverse.auc,
        "top5_promotion_rate": metrics_reverse.top5_promotion_rate,
        "top10_promotion_rate": metrics_reverse.top10_promotion_rate,
    }
    
    if verbose:
        print(f"反向 AUC: {metrics_reverse.auc:.4f}")
        print(f"反向 Top5 晋级率: {metrics_reverse.top5_promotion_rate:.2%}")
        print(f"反向 Top10 晋级率: {metrics_reverse.top10_promotion_rate:.2%}")
    
    if verbose:
        print("\n" + "=" * 60)
        print("测试4: 每日Top5详情")
        print("=" * 60)
        
        print(f"{'日期':<12} {'成功/总数':<10} {'晋级率':<8} {'Top5股票'}")
        print("-" * 60)
        
        for detail in metrics_normal.daily_top5_details:
            symbols_str = ",".join(detail.top_n_symbols[:3])
            if len(detail.top_n_symbols) > 3:
                symbols_str += "..."
            print(f"{detail.date:<12} {detail.success_count}/{detail.total_count:<8} {detail.promotion_rate:.0%}     {symbols_str}")
    
    if verbose:
        print("\n" + "=" * 60)
        print("汇总对比")
        print("=" * 60)
        print(f"{'测试类型':<15} {'AUC':<10} {'Top5晋级率':<12} {'Top10晋级率':<12}")
        print("-" * 60)
        print(f"{'正常模型':<15} {results['normal']['auc']:<10.4f} {results['normal']['top5_promotion_rate']:<12.2%} {results['normal']['top10_promotion_rate']:<12.2%}")
        print(f"{'随机模型':<15} {results['random']['auc']:<10.4f} {results['random']['top5_promotion_rate']:<12.2%} {results['random']['top10_promotion_rate']:<12.2%}")
        print(f"{'反向排序':<15} {results['reverse']['auc']:<10.4f} {results['reverse']['top5_promotion_rate']:<12.2%} {results['reverse']['top10_promotion_rate']:<12.2%}")
        print(f"{'市场均值':<15} {'-':<10} {results['normal']['overall_promotion_rate']:<12.2%} {results['normal']['overall_promotion_rate']:<12.2%}")
        
        print("\n验证结论:")
        normal_vs_random = results['normal']['top5_promotion_rate'] - results['random']['top5_promotion_rate']
        normal_vs_reverse = results['normal']['top5_promotion_rate'] - results['reverse']['top5_promotion_rate']
        normal_vs_market = results['normal']['top5_promotion_rate'] - results['normal']['overall_promotion_rate']
        
        if normal_vs_random > 0.05:
            print(f"  ✓ 正常模型优于随机模型 (+{normal_vs_random:.2%})")
        else:
            print(f"  ✗ 正常模型未显著优于随机模型 (+{normal_vs_random:.2%})")
        
        if normal_vs_reverse > 0.05:
            print(f"  ✓ 正常模型优于反向排序 (+{normal_vs_reverse:.2%})")
        else:
            print(f"  ✗ 正常模型未显著优于反向排序 (+{normal_vs_reverse:.2%})")
        
        if normal_vs_market > 0.05:
            print(f"  ✓ 正常模型优于市场均值 (+{normal_vs_market:.2%})")
        else:
            print(f"  ✗ 正常模型未显著优于市场均值 (+{normal_vs_market:.2%})")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="模型评估验证测试")
    parser.add_argument("--train-start", type=str, default="20250714", help="训练开始日期")
    parser.add_argument("--train-end", type=str, default="20260113", help="训练结束日期")
    parser.add_argument("--test-start", type=str, default="20260114", help="测试开始日期")
    parser.add_argument("--test-end", type=str, default="20260213", help="测试结束日期")
    args = parser.parse_args()
    
    base_dir = Path(".")
    
    print("=" * 60)
    print("模型评估验证测试")
    print("=" * 60)
    
    run_validation_test(
        base_dir=base_dir,
        train_start=args.train_start,
        train_end=args.train_end,
        test_start=args.test_start,
        test_end=args.test_end,
        verbose=True,
    )


if __name__ == "__main__":
    main()
