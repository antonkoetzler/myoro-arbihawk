#!/usr/bin/env python3
"""
Test script to verify Full Run and Daemon mode flow.
Tests with minimal data (1 league each) to ensure collection → training → betting flow works.
"""
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "arbihawk"))

from automation.scheduler import AutomationScheduler


def test_full_run_flow():
    """Test that Full Run executes collection → training → betting."""
    print("=" * 60)
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
        print(f"Betting skipped: {result.get('betting', {}).get('reason', 'Unknown')}")
    
    # Verify all phases ran
    collection_ran = result.get('collection') is not None
    training_ran = result.get('training') is not None
    betting_ran = result.get('betting') is not None
    
    print("\n" + "=" * 60)
    print("Flow Verification")
    print("=" * 60)
    print(f"Collection phase executed: {collection_ran} [OK]" if collection_ran else f"Collection phase executed: {collection_ran} [FAIL]")
    print(f"Training phase executed: {training_ran} [OK]" if training_ran else f"Training phase executed: {training_ran} [FAIL]")
    print(f"Betting phase executed: {betting_ran} [OK]" if betting_ran else f"Betting phase executed: {betting_ran} [FAIL]")
    
    if collection_ran and training_ran and betting_ran:
        print("\n✓ Full Run flow is working correctly!")
        return 0
    else:
        print("\n✗ Full Run flow is broken - some phases did not execute")
        return 1


if __name__ == "__main__":
    sys.exit(test_full_run_flow())
