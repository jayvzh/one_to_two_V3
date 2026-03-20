from pathlib import Path
from typing import Optional
from datetime import datetime
import json
import zipfile
import tempfile
import shutil
import sys
import os

from core.paths import get_data_path

PROJECT_ROOT = get_data_path()

from data.cache import get_zt_cache_range, get_index_cache_range


class FileService:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or PROJECT_ROOT
        self.report_dir = self.base_dir / "reports"
        self.model_dir = self.base_dir / "datasets" / "models"
        self.cache_dir = self.base_dir / "datasets" / "cache"

    def get_reports(self, report_type: Optional[str] = None) -> list[dict]:
        reports = []
        
        if not self.report_dir.exists():
            return reports
        
        for report_file in sorted(self.report_dir.glob("*.html"), reverse=True):
            name = report_file.stem
            
            if report_type and not name.startswith(report_type):
                continue
            
            report_info = {
                "filename": report_file.name,
                "name": name,
                "path": str(report_file),
                "size": report_file.stat().st_size,
                "modified": datetime.fromtimestamp(report_file.stat().st_mtime).isoformat(),
            }
            
            if name.startswith("daily_report"):
                report_info["type"] = "daily"
                date_part = name.replace("daily_report_", "").replace("_intraday", "")
                report_info["date"] = date_part[:8] if len(date_part) >= 8 else date_part
            elif name.startswith("backtest_report"):
                report_info["type"] = "backtest"
                date_part = name.replace("backtest_report_", "")
                if "_" in date_part:
                    parts = date_part.split("_")
                    report_info["start_date"] = parts[0]
                    report_info["end_date"] = parts[1] if len(parts) > 1 else ""
            elif name.startswith("heatmap_report"):
                report_info["type"] = "heatmap"
                date_part = name.replace("heatmap_report_", "")
                if "_" in date_part:
                    parts = date_part.split("_")
                    report_info["start_date"] = parts[0]
                    report_info["end_date"] = parts[1] if len(parts) > 1 else ""
            elif name.startswith("stability_report"):
                report_info["type"] = "stability"
            elif name.startswith("sensitivity_report"):
                report_info["type"] = "sensitivity"
            else:
                report_info["type"] = "unknown"
            
            reports.append(report_info)
        
        return reports

    def get_report_content(self, filename: str) -> Optional[str]:
        report_path = self.report_dir / filename
        if not report_path.exists():
            return None
        
        with open(report_path, encoding="utf-8") as f:
            return f.read()

    def get_model_meta(self, filename: str) -> Optional[dict]:
        meta_path = self.model_dir / filename.replace(".joblib", ".meta.json")
        if not meta_path.exists():
            return None
        
        with open(meta_path, encoding="utf-8") as f:
            return json.load(f)

    def get_images(self) -> list[dict]:
        images = []
        images_dir = self.report_dir / "images"
        
        if not images_dir.exists():
            return images
        
        for img_file in sorted(images_dir.glob("*.png"), reverse=True):
            images.append({
                "filename": img_file.name,
                "path": str(img_file),
                "size": img_file.stat().st_size,
                "modified": datetime.fromtimestamp(img_file.stat().st_mtime).isoformat(),
            })
        
        return images

    def delete_report(self, filename: str) -> bool:
        report_path = self.report_dir / filename
        if not report_path.exists():
            return False
        
        report_path.unlink()
        return True

    def import_cache(self, zip_path: Path) -> dict:
        if not zip_path.exists():
            raise ValueError(f"文件不存在: {zip_path}")
        
        if not zipfile.is_zipfile(zip_path):
            raise ValueError("文件不是有效的 zip 格式")
        
        zt_count = 0
        index_count = 0
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_path)
            
            extracted_zt_dir = temp_path / "zt"
            extracted_index_dir = temp_path / "index"
            
            if not extracted_zt_dir.exists() and not extracted_index_dir.exists():
                raise ValueError("zip 文件必须包含 zt/ 或 index/ 目录")
            
            if extracted_zt_dir.exists() and extracted_zt_dir.is_dir():
                zt_files = list(extracted_zt_dir.glob("*.csv"))
                if len(zt_files) == 0:
                    raise ValueError("zt 目录中没有找到 csv 文件")
                
                target_zt_dir = self.cache_dir / "zt"
                target_zt_dir.mkdir(parents=True, exist_ok=True)
                
                for zt_file in zt_files:
                    target_file = target_zt_dir / zt_file.name
                    shutil.copy2(zt_file, target_file)
                    zt_count += 1
            
            if extracted_index_dir.exists() and extracted_index_dir.is_dir():
                index_files = list(extracted_index_dir.glob("*.csv"))
                if len(index_files) == 0:
                    raise ValueError("index 目录中没有找到 csv 文件")
                
                target_index_dir = self.cache_dir / "index"
                target_index_dir.mkdir(parents=True, exist_ok=True)
                
                for index_file in index_files:
                    target_file = target_index_dir / index_file.name
                    shutil.copy2(index_file, target_file)
                    index_count += 1
        
        return {
            "success": True,
            "message": f"成功导入 {zt_count} 个涨停池文件和 {index_count} 个指数文件",
            "zt_count": zt_count,
            "index_count": index_count
        }

    def export_cache(self) -> tuple[Path, str]:
        if not self.cache_dir.exists():
            raise ValueError("缓存目录不存在")
        
        cache_files = list(self.cache_dir.glob("*"))
        if not cache_files:
            raise ValueError("缓存目录为空")
        
        exports_dir = self.base_dir / "datasets" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cache_export_{timestamp}.zip"
        zip_path = exports_dir / filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in self.cache_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.cache_dir)
                    zipf.write(file_path, arcname)
        
        return zip_path, filename

    def get_cache_status(self) -> dict:
        zt_range = get_zt_cache_range(self.cache_dir)
        index_range = get_index_cache_range(self.cache_dir)
        
        return {
            "zt_cache": {
                "available": zt_range.available,
                "start_date": zt_range.start_date,
                "end_date": zt_range.end_date,
                "count": zt_range.count,
            },
            "index_cache": {
                "available": index_range.available,
                "start_date": index_range.start_date,
                "end_date": index_range.end_date,
                "count": index_range.count,
            },
            "cache_dir": str(self.cache_dir),
        }
