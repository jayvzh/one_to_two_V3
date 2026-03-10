from pathlib import Path
from typing import Optional
import sys
import os

V2_DIR = Path(__file__).parent.parent.parent / "one_to_two_V2"
if str(V2_DIR) not in sys.path:
    sys.path.insert(0, str(V2_DIR))

os.chdir(V2_DIR)

from src.pipeline.train_model import train_production_model
from src.pipeline.daily import DailyScorer
from src.pipeline.rolling import StabilityEvaluator, run_sensitivity_test
from src.pipeline.backtest_emotion import EmotionLayerBacktest
from src.pipeline.heatmap import HeatmapAnalyzer
from src.data.sync_cache import run_sync, SyncConfig, ensure_cache_for_training
from src.pipeline.config import load_pipeline_defaults, PipelineDefaults
from src.model.trainer import OneToTwoPredictor


class PipelineService:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or V2_DIR
        self.cache_dir = self.base_dir / "data" / "cache"
        self.model_dir = self.base_dir / "data" / "models"
        self.report_dir = self.base_dir / "reports"
        self.defaults = load_pipeline_defaults(self.base_dir)

    async def train_model(
        self,
        months: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        log_callback=None,
    ) -> dict:
        if log_callback:
            log_callback("开始模型训练...")
        
        train_months = months or self.defaults.production_train.months
        
        if log_callback:
            log_callback(f"训练参数: months={train_months}, start={start_date}, end={end_date}")
        
        availability = ensure_cache_for_training(
            cache_dir=self.cache_dir,
            train_months=max(train_months, self.defaults.production_train.cache_check_months),
            auto_sync=True,
        )
        
        if not availability.is_sufficient:
            raise ValueError("缓存数据不足，无法进行训练")
        
        if log_callback:
            log_callback("缓存检查通过，开始训练...")
        
        model_path, meta = train_production_model(
            base_dir=self.base_dir,
            train_months=train_months,
            start_date=start_date,
            end_date=end_date,
            verbose=True,
        )
        
        if log_callback:
            log_callback(f"训练完成: {model_path}")
        
        return {
            "model_path": str(model_path),
            "train_start": meta.train_start,
            "train_end": meta.train_end,
            "sample_size": meta.sample_size,
            "base_success_rate": meta.base_success_rate,
            "version": meta.version,
        }

    async def generate_daily_report(
        self,
        date: Optional[str] = None,
        log_callback=None,
    ) -> dict:
        from datetime import datetime
        
        if log_callback:
            log_callback("开始生成日报...")
        
        scorer = DailyScorer(
            cache_dir=self.cache_dir,
            model_dir=self.model_dir,
            report_dir=self.report_dir,
            cache_mode="read_write",
            preferred_model_filename=self.defaults.daily.model_filename,
        )
        
        target_date = date or datetime.now().strftime("%Y%m%d")
        
        if log_callback:
            log_callback(f"目标日期: {target_date}")
        
        result = scorer.run(target_date, generate_report=True)
        
        if log_callback:
            log_callback(f"日报生成完成: {result.date}")
        
        return {
            "date": result.date,
            "emotion_score": result.emotion_score,
            "emotion_level": result.emotion_level,
            "trade_status": result.trade_status,
            "allow_trade": result.allow_trade,
            "stocks_count": len(result.stocks),
            "is_intraday": result.is_intraday,
        }

    async def run_rolling_evaluation(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sensitivity: bool = False,
        log_callback=None,
    ) -> dict:
        if log_callback:
            log_callback("开始滚动评估...")
        
        availability = ensure_cache_for_training(
            cache_dir=self.cache_dir,
            train_months=self.defaults.rolling.train_months,
            auto_sync=True,
        )
        
        if not availability.is_sufficient:
            raise ValueError("缓存数据不足，无法进行评估")
        
        start = start_date or availability.effective_start
        end = end_date or availability.effective_end
        
        if log_callback:
            log_callback(f"评估区间: {start} ~ {end}")
        
        if sensitivity:
            if log_callback:
                log_callback("运行敏感性测试...")
            
            results = run_sensitivity_test(
                base_dir=self.base_dir,
                start_date=start,
                end_date=end,
                train_months_list=list(self.defaults.rolling.sensitivity_train_months),
                test_months=self.defaults.rolling.test_months,
                verbose=True,
            )
            
            summary = {}
            for months, report in results.items():
                summary[months] = {
                    "total_windows": report.total_windows,
                    "avg_auc": report.avg_auc,
                    "avg_top5_rate": report.avg_top5_rate,
                    "avg_top5_vs_market": report.avg_top5_vs_market,
                    "win_rate": report.win_rate,
                }
            
            if log_callback:
                log_callback("敏感性测试完成")
            
            return {
                "type": "sensitivity",
                "start_date": start,
                "end_date": end,
                "results": summary,
            }
        else:
            if log_callback:
                log_callback("运行稳定性评估...")
            
            evaluator = StabilityEvaluator(self.base_dir, cache_availability=availability)
            report = evaluator.run(
                start_date=start,
                end_date=end,
                train_months=self.defaults.rolling.train_months,
                test_months=self.defaults.rolling.test_months,
                verbose=True,
            )
            
            if log_callback:
                log_callback("稳定性评估完成")
            
            return {
                "type": "stability",
                "start_date": start,
                "end_date": end,
                "total_windows": report.total_windows,
                "avg_auc": report.avg_auc,
                "avg_top5_rate": report.avg_top5_rate,
                "avg_top5_vs_market": report.avg_top5_vs_market,
                "win_rate": report.win_rate,
            }

    async def run_backtest_emotion(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        months: Optional[int] = None,
        log_callback=None,
    ) -> dict:
        if log_callback:
            log_callback("开始情绪分层回测...")
        
        backtest = EmotionLayerBacktest(
            cache_dir=self.cache_dir,
            zt_cache_mode="read",
        )
        
        backtest_months = months or self.defaults.emotion_backtest.months
        
        result = backtest.run(
            start_date=start_date,
            end_date=end_date,
            window_days=self.defaults.emotion_backtest.window_days,
            force=False,
        )
        
        if log_callback:
            log_callback(f"回测完成: {result.total_samples} 样本")
        
        layer_stats = [
            {
                "emotion_score": s.emotion_score,
                "sample_count": s.sample_count,
                "success_count": s.success_count,
                "success_rate": s.success_rate,
                "allow_trade": s.allow_trade,
            }
            for s in result.layer_stats
        ]
        
        return {
            "start_date": result.start_date,
            "end_date": result.end_date,
            "total_samples": result.total_samples,
            "total_days": result.total_days,
            "duration_seconds": result.duration_seconds,
            "layer_stats": layer_stats,
        }

    async def run_heatmap_analysis(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        model: Optional[str] = None,
        log_callback=None,
    ) -> dict:
        if log_callback:
            log_callback("开始热力图分析...")
        
        analyzer = HeatmapAnalyzer(
            cache_dir=self.cache_dir,
            model_dir=self.model_dir,
            report_dir=self.report_dir,
        )
        
        model_path = None
        if model:
            model_path = str(self.model_dir / model)
        
        result = analyzer.run(
            start_date=start_date,
            end_date=end_date,
            model_path=model_path,
            force=False,
        )
        
        if log_callback:
            log_callback(f"热力图分析完成: {result.total_samples} 样本")
        
        heatmap_cells = []
        if result.heatmap_data:
            for cell in result.heatmap_data.cells:
                heatmap_cells.append({
                    "emotion_score": cell.emotion_score,
                    "score_bin": cell.score_bin,
                    "sample_count": cell.sample_count,
                    "success_count": cell.success_count,
                    "success_rate": cell.success_rate,
                })
        
        return {
            "start_date": result.start_date,
            "end_date": result.end_date,
            "total_samples": result.total_samples,
            "total_days": result.total_days,
            "analysis_base_success_rate": result.analysis_base_success_rate,
            "image_path": result.image_path,
            "heatmap_cells": heatmap_cells,
        }

    async def sync_cache(
        self,
        zt_trade_days: int = 14,
        index_months: int = 2,
        log_callback=None,
    ) -> dict:
        if log_callback:
            log_callback("开始同步缓存...")
        
        config = SyncConfig(
            cache_root=self.cache_dir,
            zt_trade_days=zt_trade_days,
            index_months=index_months,
        )
        
        import pandas as pd
        result = run_sync(config, now=pd.Timestamp.today(), silent=False)
        
        if log_callback:
            log_callback(f"同步完成: zt_synced={result.zt_synced}, zt_failed={result.zt_failed}")
        
        return {
            "zt_synced": result.zt_synced,
            "zt_failed": result.zt_failed,
            "index_synced": result.index_synced,
            "index_error": result.index_error,
            "success": result.success,
        }

    def get_model_list(self) -> list[dict]:
        models = []
        
        for model_file in sorted(self.model_dir.glob("model_*.joblib")):
            try:
                meta = OneToTwoPredictor.load_meta(str(model_file))
                models.append({
                    "filename": model_file.name,
                    "train_start": meta.train_start,
                    "train_end": meta.train_end,
                    "sample_size": meta.sample_size,
                    "base_success_rate": meta.base_success_rate,
                    "version": meta.version,
                })
            except Exception:
                models.append({
                    "filename": model_file.name,
                    "error": "无法读取模型元数据",
                })
        
        for model_file in sorted(self.model_dir.glob("stability_model_*.joblib")):
            try:
                meta = OneToTwoPredictor.load_meta(str(model_file))
                models.append({
                    "filename": model_file.name,
                    "type": "stability",
                    "train_start": meta.train_start,
                    "train_end": meta.train_end,
                    "sample_size": meta.sample_size,
                    "base_success_rate": meta.base_success_rate,
                })
            except Exception:
                pass
        
        return models
