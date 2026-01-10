"""
Configuration settings for Arbihawk.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Load environment variables
load_dotenv(BASE_DIR / ".env")
load_dotenv(Path.cwd() / ".env")

# ODDS-API configuration
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
if not ODDS_API_KEY:
    raise ValueError("ODDS_API_KEY not found in environment variables")

# Data storage
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "arbihawk.db"))
MATCHES_DIR = DATA_DIR / "matches"

# Value betting configuration
EV_THRESHOLD = float(os.getenv("EV_THRESHOLD", "0.07"))  # 7% expected value threshold
