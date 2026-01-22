"""
Configuration settings for Arbihawk.
Loads configuration from JSON files.
"""

import json
from pathlib import Path
from typing import Dict, Any

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"


def _load_json_config(filename: str) -> Dict[str, Any]:
    """Load a JSON config file."""
    config_path = CONFIG_DIR / filename
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def _get_config() -> Dict[str, Any]:
    """Load main configuration."""
    return _load_json_config("config.json")


def _get_automation_config() -> Dict[str, Any]:
    """Load automation configuration."""
    return _load_json_config("automation.json")


# Load configs
_config = _get_config()
_automation_config = _get_automation_config()

# Main configuration
DB_PATH = str(BASE_DIR / _config.get("db_path", "data/arbihawk.db"))
EV_THRESHOLD = float(_config.get("ev_threshold", 0.07))

# Automation configuration
COLLECTION_SCHEDULE = _automation_config.get("collection_schedule", "0 */6 * * *")
TRAINING_SCHEDULE = _automation_config.get("training_schedule", "0 2 * * *")
INCREMENTAL_MODE = _automation_config.get("incremental_mode", True)
MATCHING_TOLERANCE_HOURS = _automation_config.get("matching_tolerance_hours", 2)
SCRAPER_ARGS = _automation_config.get("scraper_args", {})
SCRAPER_WORKERS = _automation_config.get("scraper_workers", {
    "max_workers_leagues": 5,
    "max_workers_odds": 5,
    "max_workers_leagues_playwright": 3
})

# Fake money configuration
FAKE_MONEY_CONFIG = _automation_config.get("fake_money", {
    "enabled": True,
    "starting_balance": 10000,
    "bet_sizing_strategy": "fixed",
    "fixed_stake": 100,
    "percentage_stake": 0.02,
    "unit_size_percentage": 0.01,
    "auto_bet_after_training": False
})

# Auto-betting configuration
AUTO_BET_AFTER_TRAINING = FAKE_MONEY_CONFIG.get("auto_bet_after_training", False)

# Model versioning configuration
MODEL_VERSIONING_CONFIG = _automation_config.get("model_versioning", {
    "auto_rollback_enabled": True,
    "rollback_threshold": -10.0,
    "rollback_evaluation_bets": 50,
    "max_versions_to_keep": 10
})

# Metrics configuration
METRICS_CONFIG = _automation_config.get("metrics", {
    "retention_months": 18
})

# Backup configuration
BACKUP_CONFIG = _automation_config.get("backup", {
    "max_backups": 10,
    "compress": False
})


def reload_config():
    """Reload configuration from files."""
    global _config, _automation_config
    global DB_PATH, EV_THRESHOLD, COLLECTION_SCHEDULE, TRAINING_SCHEDULE
    global INCREMENTAL_MODE, MATCHING_TOLERANCE_HOURS, SCRAPER_ARGS, SCRAPER_WORKERS
    global FAKE_MONEY_CONFIG, MODEL_VERSIONING_CONFIG, METRICS_CONFIG, BACKUP_CONFIG
    global AUTO_BET_AFTER_TRAINING
    
    _config = _get_config()
    _automation_config = _get_automation_config()
    
    DB_PATH = str(BASE_DIR / _config.get("db_path", "data/arbihawk.db"))
    EV_THRESHOLD = float(_config.get("ev_threshold", 0.07))
    COLLECTION_SCHEDULE = _automation_config.get("collection_schedule", "0 */6 * * *")
    TRAINING_SCHEDULE = _automation_config.get("training_schedule", "0 2 * * *")
    INCREMENTAL_MODE = _automation_config.get("incremental_mode", True)
    MATCHING_TOLERANCE_HOURS = _automation_config.get("matching_tolerance_hours", 2)
    SCRAPER_ARGS = _automation_config.get("scraper_args", {})
    SCRAPER_WORKERS = _automation_config.get("scraper_workers", {
        "max_workers_leagues": 5,
        "max_workers_odds": 5,
        "max_workers_leagues_playwright": 3
    })
    FAKE_MONEY_CONFIG = _automation_config.get("fake_money", {
        "enabled": True,
        "starting_balance": 10000,
        "bet_sizing_strategy": "fixed",
        "fixed_stake": 100,
        "percentage_stake": 0.02,
        "unit_size_percentage": 0.01,
        "auto_bet_after_training": False
    })
    AUTO_BET_AFTER_TRAINING = FAKE_MONEY_CONFIG.get("auto_bet_after_training", False)
    MODEL_VERSIONING_CONFIG = _automation_config.get("model_versioning", {})
    METRICS_CONFIG = _automation_config.get("metrics", {})
    BACKUP_CONFIG = _automation_config.get("backup", {})
