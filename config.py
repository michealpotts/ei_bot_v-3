import os
from pathlib import Path
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "graphql_timeout": 120000,
    "page_navigation_timeout": 60000,
    "overlay_load_timeout": 30000,
    
    "max_retries": 5,
    "base_backoff": 1.0,
    "max_backoff": 60.0,
    
    "min_project_delay": 1.5,
    "max_project_delay": 4.0,
    "min_page_delay": 2.0,
    "max_page_delay": 5.0,
    
    "retry_queue_max_size": 100,
    "retry_queue_file": "retry_queue.json",
    
    "log_file": "scraper.log",
    "log_level": "INFO",
    
    "checkpoint_file": "scraper_checkpoint.json",
    
    "max_pages": None,
    "date_range_start": None,
    "date_range_end": None,
}

CONFIG_FILE = "scraper_config.json"


class Config:
    
    def __init__(self, config_file: str = CONFIG_FILE):
        self.config_file = Path(config_file)
        self.config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self._load_config()
    
    def _load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
                    logger.info(f"[OK] Loaded config from {self.config_file}")
            except Exception as e:
                logger.warning(f"[WARNING] Failed to load config file: {e}, using defaults")
        
        env_mappings = {
            "GRAPHQL_TIMEOUT": ("graphql_timeout", int),
            "PAGE_NAV_TIMEOUT": ("page_navigation_timeout", int),
            "OVERLAY_TIMEOUT": ("overlay_load_timeout", int),
            "MAX_RETRIES": ("max_retries", int),
            "BASE_BACKOFF": ("base_backoff", float),
            "MAX_BACKOFF": ("max_backoff", float),
            "MIN_PROJECT_DELAY": ("min_project_delay", float),
            "MAX_PROJECT_DELAY": ("max_project_delay", float),
            "MIN_PAGE_DELAY": ("min_page_delay", float),
            "MAX_PAGE_DELAY": ("max_page_delay", float),
            "RETRY_QUEUE_MAX_SIZE": ("retry_queue_max_size", int),
            "RETRY_QUEUE_FILE": ("retry_queue_file", str),
            "LOG_FILE": ("log_file", str),
            "LOG_LEVEL": ("log_level", str),
            "CHECKPOINT_FILE": ("checkpoint_file", str),
            "MAX_PAGES": ("max_pages", lambda x: int(x) if x else None),
        }
        
        for env_var, (config_key, converter) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    self.config[config_key] = converter(env_value)
                except Exception as e:
                    logger.warning(f"[WARNING] Failed to parse {env_var}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        return self.config[key]
    
    def __setitem__(self, key: str, value: Any):
        self.config[key] = value
    
    def save(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"[SAVE] Saved config to {self.config_file}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to save config: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        return self.config.copy()


_config_instance: Config = None


def get_config() -> Config:
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

