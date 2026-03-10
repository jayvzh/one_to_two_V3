import json
from pathlib import Path
from typing import Any, Optional
from dataclasses import asdict

V2_DIR = Path(__file__).parent.parent.parent / "one_to_two_V2"


class ConfigService:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or V2_DIR / "config" / "pipeline_defaults.json"
        self._config_cache: Optional[dict] = None

    def _load_config(self) -> dict:
        if self._config_cache is not None:
            return self._config_cache
        
        if not self.config_path.exists():
            self._config_cache = self._get_default_config()
        else:
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    self._config_cache = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._config_cache = self._get_default_config()
        
        return self._config_cache

    def _get_default_config(self) -> dict:
        return {
            "production_train": {
                "months": 6,
                "cache_check_months": 6,
            },
            "daily": {
                "cache_check_months": 2,
                "model_filename": "model_latest.joblib",
            },
            "emotion_backtest": {
                "months": 6,
                "window_days": 64,
                "cache_check_months": 3,
            },
            "rolling": {
                "train_months": 6,
                "test_months": 1,
                "sensitivity_train_months": [2, 3, 4, 6],
            },
            "heatmap": {
                "months": 1,
                "model_filename": "model_latest.joblib",
            },
        }

    def get_config(self) -> dict:
        return self._load_config()

    def update_config(self, updates: dict[str, Any]) -> dict:
        config = self._load_config()
        
        for key, value in updates.items():
            if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                config[key].update(value)
            else:
                config[key] = value
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        self._config_cache = config
        return config

    def get_section(self, section: str) -> Optional[dict]:
        config = self._load_config()
        return config.get(section)

    def update_section(self, section: str, values: dict) -> Optional[dict]:
        config = self._load_config()
        if section not in config:
            config[section] = {}
        config[section].update(values)
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        self._config_cache = config
        return config.get(section)
