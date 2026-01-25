#!/usr/bin/env python3
"""
Quick test to verify training progress logging works.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "arbihawk"))

from data.database import Database
from data.features import FeatureEngineer

def test_progress_logging():
    """Test that progress logging works."""
    print("Testing progress logging in feature creation...")
    
    db = Database()
    feature_engineer = FeatureEngineer(db)
    
    logs = []
    def log_callback(level: str, message: str):
        logs.append((level, message))
        print(f"[{level.upper()}] {message}")
    
    # Test with a small subset - just verify logging works
    print("\n[INFO] Testing feature creation with progress logging...")
    X, y = feature_engineer.create_training_data(market='1x2', log_callback=log_callback)
    
    print(f"\n[INFO] Created {len(X)} samples")
    
    # Check for progress logs
    progress_logs = [msg for level, msg in logs if "Processing features" in msg]
    if progress_logs:
        print(f"\n[SUCCESS] Found {len(progress_logs)} progress log messages")
        print("Sample progress logs:")
        for log in progress_logs[:5]:
            print(f"  {log}")
        return True
    else:
        print("\n[WARNING] No progress logs found")
        return len(X) < 100  # If very few samples, no progress logs is OK
    
if __name__ == "__main__":
    success = test_progress_logging()
    sys.exit(0 if success else 1)
