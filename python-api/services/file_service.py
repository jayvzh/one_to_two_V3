from pathlib import Path
from typing import Optional
from datetime import datetime
import json

V2_DIR = Path(__file__).parent.parent.parent / "one_to_two_V2"


class FileService:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or V2_DIR
        self.report_dir = self.base_dir / "reports"
        self.model_dir = self.base_dir / "data" / "models"
        self.cache_dir = self.base_dir / "data" / "cache"

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
