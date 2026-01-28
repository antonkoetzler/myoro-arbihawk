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

# Environment configuration
ENVIRONMENT = _config.get("environment", "debug")  # 'debug' or 'production'

# Main configuration - DB path depends on environment
# Environment-based path takes priority
if ENVIRONMENT == "debug":
    default_db_path = "data/arbihawk_debug.db"
else:
    default_db_path = "data/arbihawk.db"

# Use explicit db_path only if environment is not set, otherwise use environment-based path
if "environment" in _config:
    DB_PATH = str(BASE_DIR / default_db_path)
elif "db_path" in _config:
    DB_PATH = str(BASE_DIR / _config["db_path"])
else:
    DB_PATH = str(BASE_DIR / default_db_path)
EV_THRESHOLD = float(_config.get("ev_threshold", 0.07))

# Bookmaker margin configuration (defaults based on industry research)
# Margins represent the overround/vig that bookmakers add to odds
# Typical ranges: 1x2 (4-6%), over_under (5-8%), btts (6-8%)
BOOKMAKER_MARGINS = _config.get("bookmaker_margins", {
    "1x2": 0.05,  # 5% margin for match result markets
    "over_under": 0.06,  # 6% margin for over/under markets
    "btts": 0.07  # 7% margin for both teams to score markets
})

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
    "max_versions_to_keep": 10,
    "profitability_selection": {
        "enabled": True,
        "min_roi": 0.0,  # Minimum ROI to activate (0% = break even)
        "min_bets": 10,  # Minimum number of bets for evaluation to be meaningful
        "save_unprofitable": True  # Save unprofitable models for comparison but don't activate
    }
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

# Hyperparameter tuning configuration
HYPERPARAMETER_TUNING_CONFIG = _automation_config.get("hyperparameter_tuning", {
    "enabled": False,  # Disabled until sufficient data (10k+ samples recommended)
    "search_space": "small",  # 'small', 'medium', or 'large' (changed default to 'small' for faster tuning)
    "min_samples": 300,
    "n_jobs": 1,  # Number of parallel workers (1 = sequential, -1 = all CPUs)
    "timeout": None,  # Maximum time in seconds (None = no timeout)
    "early_stopping_patience": 10  # Stop if no improvement in last N trials (None = disabled)
})

# Trading configuration (stocks/crypto)
TRADING_CONFIG = _config.get("trading", {
    "enabled": False,
    "watchlist": {
        "stocks": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "JNJ"],
        "crypto": ["BTC", "ETH", "BNB", "SOL", "ADA"]
    },
    "api_keys": {
        "alpha_vantage": "",
        "coingecko": ""
    },
    "update_frequency": {
        "stocks": "daily",
        "crypto": "hourly"
    },
    "rate_limiting": {
        "alpha_vantage_calls_per_min": 5,
        "alpha_vantage_calls_per_day": 25,
        "coingecko_calls_per_min": 30
    },
    "scraping_fallback": {
        "enabled": True,
        "retry_api_after_hours": 24
    },
    "historical_backfill_days": 365
})

# Trading hyperparameter tuning configuration
TRADING_HYPERPARAMETER_TUNING_CONFIG = _automation_config.get("trading_hyperparameter_tuning", {
    "enabled": False,  # Disabled until sufficient data (10k+ samples recommended)
    "search_space": "small",  # 'small', 'medium', or 'large'
    "min_samples": 300,
    "n_jobs": 1,  # Number of parallel workers (1 = sequential, -1 = all CPUs)
    "timeout": None,  # Maximum time in seconds (None = no timeout)
    "early_stopping_patience": 10  # Stop if no improvement in last N trials (None = disabled)
})


def reload_config():
    """Reload configuration from files."""
    global _config, _automation_config
    global ENVIRONMENT, DB_PATH, EV_THRESHOLD, COLLECTION_SCHEDULE, TRAINING_SCHEDULE
    global INCREMENTAL_MODE, MATCHING_TOLERANCE_HOURS, SCRAPER_ARGS, SCRAPER_WORKERS
    global FAKE_MONEY_CONFIG, MODEL_VERSIONING_CONFIG, METRICS_CONFIG, BACKUP_CONFIG
    global AUTO_BET_AFTER_TRAINING, BOOKMAKER_MARGINS, HYPERPARAMETER_TUNING_CONFIG
    global TRADING_CONFIG, TRADING_HYPERPARAMETER_TUNING_CONFIG
    
    _config = _get_config()
    _automation_config = _get_automation_config()
    
    ENVIRONMENT = _config.get("environment", "debug")
    
    if ENVIRONMENT == "debug":
        default_db_path = "data/arbihawk_debug.db"
    else:
        default_db_path = "data/arbihawk.db"
    
    # Environment-based path takes priority
    if "environment" in _config:
        DB_PATH = str(BASE_DIR / default_db_path)
    elif "db_path" in _config:
        DB_PATH = str(BASE_DIR / _config["db_path"])
    else:
        DB_PATH = str(BASE_DIR / default_db_path)
    EV_THRESHOLD = float(_config.get("ev_threshold", 0.07))
    BOOKMAKER_MARGINS = _config.get("bookmaker_margins", {
        "1x2": 0.05,
        "over_under": 0.06,
        "btts": 0.07
    })
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
    MODEL_VERSIONING_CONFIG = _automation_config.get("model_versioning", {
        "auto_rollback_enabled": True,
        "rollback_threshold": -10.0,
        "rollback_evaluation_bets": 50,
        "max_versions_to_keep": 10,
        "profitability_selection": {
            "enabled": True,
            "min_roi": 0.0,
            "min_bets": 10,
            "save_unprofitable": True
        }
    })
    METRICS_CONFIG = _automation_config.get("metrics", {})
    BACKUP_CONFIG = _automation_config.get("backup", {})
    HYPERPARAMETER_TUNING_CONFIG = _automation_config.get("hyperparameter_tuning", {
        "enabled": False,  # Disabled until sufficient data (10k+ samples recommended)
        "search_space": "small",  # Changed default to 'small' for faster tuning
        "min_samples": 300,
        "n_jobs": 1,
        "timeout": None,
        "early_stopping_patience": 10
    })
    TRADING_HYPERPARAMETER_TUNING_CONFIG = _automation_config.get("trading_hyperparameter_tuning", {
        "enabled": False,
        "search_space": "small",
        "min_samples": 300,
        "n_jobs": 1,
        "timeout": None,
        "early_stopping_patience": 10
    })
    
    TRADING_CONFIG = _config.get("trading", {
        "enabled": False,
        "watchlist": {
            "stocks": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "JNJ"],
            "crypto": ["BTC", "ETH", "BNB", "SOL", "ADA"]
        },
        "api_keys": {
            "alpha_vantage": "",
            "coingecko": ""
        },
        "update_frequency": {
            "stocks": "daily",
            "crypto": "hourly"
        },
        "rate_limiting": {
            "alpha_vantage_calls_per_min": 5,
            "alpha_vantage_calls_per_day": 25,
            "coingecko_calls_per_min": 30
        },
        "scraping_fallback": {
            "enabled": True,
            "retry_api_after_hours": 24
        },
        "historical_backfill_days": 365
    })
