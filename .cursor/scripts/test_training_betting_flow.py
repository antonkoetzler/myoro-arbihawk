#!/usr/bin/env python3
"""
Test script to verify training and betting flow end-to-end.
Tests feature creation with progress logging, training, and betting.
"""
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "arbihawk"))

from data.database import Database
from train import train_models
from automation.betting import BettingService
from automation.scheduler import AutomationScheduler
from utils.colors import print_header, print_success, print_error, print_info


def test_training_flow():
    """Test training flow with progress logging."""
    print("=" * 60)
    print("Testing Training Flow")
    print("=" * 60)
    
    db = Database()
    
    # Check if we have data
    fixtures = db.get_fixtures()
    scores = db.get_scores()
    
    if len(fixtures) == 0:
        print_error("No fixtures in database. Please run data collection first.")
        return False
    
    if len(scores) == 0:
        print_error("No scores in database. Models require completed matches.")
        return False
    
    print_info(f"Found {len(fixtures)} fixtures and {len(scores)} scores")
    
    # Test with log callback
    logs = []
    def log_callback(level: str, message: str):
        logs.append((level, message))
        print(f"[{level.upper()}] {message}")
    
    print("\n[INFO] Starting training with progress logging...")
    start_time = time.time()
    
    success, metrics = train_models(db, log_callback=log_callback)
    
    duration = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("Training Results")
    print("=" * 60)
    print(f"Success: {success}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Trained models: {metrics.get('trained_count', 0)}/{metrics.get('total_markets', 0)}")
    print(f"Has data: {metrics.get('has_data', False)}")
    
    # Check for progress logs
    progress_logs = [msg for level, msg in logs if "Processing features" in msg]
    if progress_logs:
        print(f"\n[SUCCESS] Found {len(progress_logs)} progress log messages")
        print("Sample progress logs:")
        for log in progress_logs[:3]:
            print(f"  {log}")
    else:
        print("\n[WARNING] No progress logs found - this might indicate an issue")
    
    if metrics.get('errors'):
        print("\n[ERROR] Errors encountered:")
        for error in metrics['errors']:
            print(f"  - {error}")
        return False
    
    return success and metrics.get('has_data', False)


def test_betting_flow():
    """Test betting flow after training."""
    print("\n" + "=" * 60)
    print("Testing Betting Flow")
    print("=" * 60)
    
    db = Database()
    
    logs = []
    def log_callback(level: str, message: str):
        logs.append((level, message))
        print(f"[{level.upper()}] {message}")
    
    betting_service = BettingService(db, log_callback=log_callback)
    
    print("\n[INFO] Starting betting cycle...")
    start_time = time.time()
    
    result = betting_service.place_bets_for_all_models(limit_per_model=5)
    
    duration = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("Betting Results")
    print("=" * 60)
    print(f"Success: {result.get('success', False)}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Total bets placed: {result.get('total_bets_placed', 0)}")
    print(f"Total stake: ${result.get('total_stake', 0.0):.2f}")
    
    if result.get('errors'):
        print("\n[WARNING] Errors encountered:")
        for error in result['errors']:
            print(f"  - {error}")
    
    return result.get('success', False)


def test_full_run():
    """Test full run (collection + training + betting)."""
    print("\n" + "=" * 60)
    print("Testing Full Run Flow")
    print("=" * 60)
    
    scheduler = AutomationScheduler()
    
    # Patch league discovery to return only 1 league for testing
    original_betano_discover = scheduler._discover_betano_leagues
    original_flashscore_discover = scheduler._discover_flashscore_leagues
    
    def limited_betano_discover():
        leagues = original_betano_discover()
        return leagues[:1] if leagues else []
    
    def limited_flashscore_discover():
        leagues = original_flashscore_discover()
        return leagues[:1] if leagues else []
    
    scheduler._discover_betano_leagues = limited_betano_discover
    scheduler._discover_flashscore_leagues = limited_flashscore_discover
    
    print("\n[INFO] Starting Full Run with 1 league each...")
    print("[INFO] This should run: Collection -> Training -> Betting\n")
    
    start_time = time.time()
    result = scheduler.run_full_with_betting()
    duration = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("Full Run Results")
    print("=" * 60)
    print(f"Success: {result.get('success', False)}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"\nCollection: {result.get('collection', {}).get('success', False)}")
    print(f"Training: {result.get('training', {}).get('success', False)}")
    print(f"Betting: {result.get('betting', {}).get('success', False)}")
    
    if result.get('betting', {}).get('skipped'):
        print(f"\n[INFO] Betting skipped: {result.get('betting', {}).get('reason', 'Unknown')}")
    
    return result.get('success', False)


def main():
    """Run all tests."""
    print_header("Training and Betting Flow Test Suite")
    
    # Test 1: Training flow
    training_ok = test_training_flow()
    
    if not training_ok:
        print_error("\n[FAILED] Training flow test failed. Skipping betting test.")
        return 1
    
    # Test 2: Betting flow
    betting_ok = test_betting_flow()
    
    # Test 3: Full run (optional - takes longer)
    # Uncomment to test full run
    # full_run_ok = test_full_run()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Training: {'✓ PASS' if training_ok else '✗ FAIL'}")
    print(f"Betting: {'✓ PASS' if betting_ok else '✗ FAIL'}")
    
    if training_ok and betting_ok:
        print_success("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print_error("\n[FAILED] Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
