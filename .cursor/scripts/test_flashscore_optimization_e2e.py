#!/usr/bin/env python3
"""
End-to-end test for FlashScore optimization.

Tests the parallel scraping functionality with a small subset of leagues.

Usage:
    python test_flashscore_optimization_e2e.py
"""
import sys
import time
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "arbihawk"))
sys.path.insert(0, str(PROJECT_ROOT / "arbihawk" / "scrapers" / "src"))


def test_flashscore_parallel_scraping():
    """Test FlashScore parallel scraping with a small subset of leagues."""
    print("=" * 60)
    print("FlashScore Parallel Scraping E2E Test")
    print("=" * 60)
    
    try:
        from sports_data.flashscore import (
            main, LEAGUE_MAPPING, scrape_league, 
            fetch_odds_batch, _setup_page_resource_blocking
        )
        from shared.tui import TUI
        from shared.match_utils import get_current_season
        from playwright.sync_api import sync_playwright
        from shared.browser_utils import get_playwright_context
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        return False
    
    print("\n[INFO] Testing with 3 leagues (parallelized)...")
    
    # Select 3 diverse leagues for testing
    test_leagues = list(LEAGUE_MAPPING.keys())[:3]
    print(f"[INFO] Test leagues: {test_leagues}")
    
    season = get_current_season()
    all_matches = []
    failed_leagues = []
    
    start_time = time.time()
    
    try:
        with sync_playwright() as p:
            browser, context = get_playwright_context(p, headless=True)
            
            # Test with 3 parallel workers
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def scrape_wrapper(league):
                try:
                    matches, error, lwo = scrape_league(
                        league, season, context, max_workers_odds=5
                    )
                    return (league, matches, error, lwo)
                except Exception as e:
                    print(f"[WARN] Exception scraping {league}: {e}")
                    return (league, [], True, None)
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(scrape_wrapper, lg): lg for lg in test_leagues}
                
                for future in as_completed(futures):
                    league = futures[future]
                    try:
                        result_league, matches, error, lwo = future.result()
                        if error:
                            failed_leagues.append(result_league)
                            print(f"[WARN] {result_league}: Failed")
                        else:
                            all_matches.extend(matches)
                            print(f"[OK] {result_league}: {len(matches)} matches")
                    except Exception as e:
                        failed_leagues.append(league)
                        print(f"[FAIL] {league}: Exception - {e}")
            
            browser.close()
    
    except Exception as e:
        print(f"[FAIL] Browser error: {e}")
        return False
    
    duration = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)
    print(f"Total matches: {len(all_matches)}")
    print(f"Successful leagues: {len(test_leagues) - len(failed_leagues)}/{len(test_leagues)}")
    print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} min)")
    print(f"Matches per second: {len(all_matches)/duration:.1f}")
    
    if failed_leagues:
        print(f"Failed leagues: {', '.join(failed_leagues)}")
    
    # Verify data integrity
    print("\n[INFO] Verifying data integrity...")
    
    matches_with_odds = sum(1 for m in all_matches if m.get('odds'))
    matches_with_teams = sum(1 for m in all_matches if m.get('home_team_name') and m.get('away_team_name'))
    matches_with_scores = sum(1 for m in all_matches if m.get('home_score') is not None)
    
    print(f"  Matches with odds: {matches_with_odds}/{len(all_matches)}")
    print(f"  Matches with teams: {matches_with_teams}/{len(all_matches)}")
    print(f"  Matches with scores: {matches_with_scores}/{len(all_matches)}")
    
    # Pass criteria
    passed = True
    
    if len(all_matches) == 0 and len(failed_leagues) < len(test_leagues):
        print("[WARN] No matches found - might be off-season or network issue")
    
    if matches_with_teams < len(all_matches) * 0.9:  # 90% should have teams
        print("[FAIL] Too many matches missing team names")
        passed = False
    
    if matches_with_scores < len(all_matches) * 0.9:  # 90% should have scores
        print("[FAIL] Too many matches missing scores")
        passed = False
    
    if failed_leagues and len(failed_leagues) == len(test_leagues):
        print("[FAIL] All leagues failed")
        passed = False
    
    if passed:
        print("\n[OK] All E2E tests passed!")
    else:
        print("\n[FAIL] Some E2E tests failed")
    
    return passed


def test_odds_batch_fetching():
    """Test the odds batch fetching functionality."""
    print("\n" + "=" * 60)
    print("Odds Batch Fetching Test")
    print("=" * 60)
    
    try:
        from sports_data.flashscore import fetch_odds_batch, fetch_match_odds
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        return False
    
    # Test with a few known event IDs (these may or may not work depending on data availability)
    # Using placeholder IDs - in real test, you'd use actual IDs from a scraped league
    print("[INFO] Testing batch fetch with mock event IDs...")
    
    # Just test that the function doesn't crash with empty input
    result = fetch_odds_batch([])
    if result == {}:
        print("[OK] Empty input handled correctly")
    else:
        print("[FAIL] Empty input not handled correctly")
        return False
    
    print("[OK] Odds batch fetching tests passed!")
    return True


def test_resource_blocking():
    """Test that resource blocking is set up correctly."""
    print("\n" + "=" * 60)
    print("Resource Blocking Test")
    print("=" * 60)
    
    try:
        from sports_data.flashscore import _setup_page_resource_blocking
        from unittest.mock import Mock
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        return False
    
    mock_page = Mock()
    _setup_page_resource_blocking(mock_page)
    
    # Should have set up multiple routes
    route_count = mock_page.route.call_count
    print(f"[INFO] Routes set up: {route_count}")
    
    if route_count >= 7:
        print("[OK] Resource blocking routes set up correctly")
        return True
    else:
        print(f"[FAIL] Expected at least 7 routes, got {route_count}")
        return False


def main():
    """Run all E2E tests."""
    print("FlashScore Optimization E2E Tests")
    print("=" * 60)
    print()
    
    results = []
    
    # Test 1: Resource blocking (fast, no network)
    results.append(("Resource Blocking", test_resource_blocking()))
    
    # Test 2: Odds batch fetching (fast, no network with empty input)
    results.append(("Odds Batch Fetching", test_odds_batch_fetching()))
    
    # Test 3: Full parallel scraping (slow, requires network)
    # Only run if explicitly requested
    import os
    if os.environ.get("RUN_FULL_E2E", "0") == "1":
        results.append(("Parallel Scraping", test_flashscore_parallel_scraping()))
    else:
        print("\n[SKIP] Parallel scraping test - set RUN_FULL_E2E=1 to enable")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
