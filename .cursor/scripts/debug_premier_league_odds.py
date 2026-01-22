#!/usr/bin/env python3
"""Debug script to investigate Premier League odds extraction failures."""
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from sports_data.flashscore import (
    scrape_league,
    extract_event_id_from_match,
    fetch_match_odds,
    ODDS_GRAPHQL_BASE,
    PROJECT_ID
)
from shared.tui import TUI
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from shared.browser_utils import get_playwright_context
from shared.league_config import get_flashscore_leagues

LEAGUE_MAPPING = get_flashscore_leagues()


def test_event_id_extraction():
    """Test if event IDs are being extracted correctly from Premier League page."""
    print("\n" + "="*60)
    print("TEST 1: Event ID Extraction")
    print("="*60)
    
    league_name = "Premier League"
    league_info = LEAGUE_MAPPING[league_name]
    url = f"https://www.flashscore.com/football/{league_info['country']}/{league_info['slug']}/results/"
    
    print(f"Loading page: {url}")
    
    try:
        with sync_playwright() as p:
            browser, context = get_playwright_context(p, headless=True)
            page = context.new_page()
            
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            time.sleep(1)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find match containers
            match_containers = soup.find_all('div', class_=lambda x: x and 'event__match' in str(x))
            print(f"Found {len(match_containers)} match containers")
            
            event_ids = []
            for idx, match_div in enumerate(match_containers[:10]):  # Test first 10
                event_id = extract_event_id_from_match(match_div, html)
                if event_id:
                    event_ids.append(event_id)
                    print(f"  Match {idx+1}: event_id = {event_id}")
                else:
                    print(f"  Match {idx+1}: NO event_id found")
                    # Debug: print HTML snippet
                    print(f"    HTML snippet: {str(match_div)[:200]}...")
            
            page.close()
            context.close()
            browser.close()
            
            print(f"\nExtracted {len(event_ids)} event IDs from first 10 matches")
            return event_ids
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_odds_api_direct(event_ids: List[str]):
    """Test odds API directly with extracted event IDs."""
    print("\n" + "="*60)
    print("TEST 2: Direct API Testing")
    print("="*60)
    
    if not event_ids:
        print("No event IDs to test")
        return
    
    # Test first 5 event IDs
    test_ids = event_ids[:5]
    print(f"Testing {len(test_ids)} event IDs...")
    
    for event_id in test_ids:
        print(f"\nTesting event_id: {event_id}")
        
        # Test with default geo codes
        url = f"{ODDS_GRAPHQL_BASE}?_hash=oce&eventId={event_id}&projectId={PROJECT_ID}&geoIpCode=BR&geoIpSubdivisionCode=BRSP"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.flashscore.com/',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  Response keys: {list(data.keys())}")
                
                odds_comparison = data.get('data', {}).get('findOddsByEventId', {})
                if odds_comparison:
                    markets = odds_comparison.get('markets', [])
                    print(f"  Markets found: {len(markets)}")
                    if markets:
                        print(f"  First market: {markets[0].get('name', 'N/A')}")
                        print(f"  SUCCESS: Odds data available")
                    else:
                        print(f"  WARNING: No markets in response")
                        print(f"  Full response: {json.dumps(data, indent=2)[:500]}")
                else:
                    print(f"  ERROR: No 'findOddsByEventId' in response")
                    print(f"  Full response: {json.dumps(data, indent=2)[:500]}")
            elif response.status_code == 429:
                print(f"  ERROR: Rate limited (429)")
            else:
                print(f"  ERROR: Status {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"  EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(0.5)  # Small delay between requests


def test_full_scrape():
    """Test full scrape with detailed logging."""
    print("\n" + "="*60)
    print("TEST 3: Full Scrape with Debug Logging")
    print("="*60)
    
    # Monkey patch fetch_match_odds to add debug logging
    original_fetch = fetch_match_odds
    
    def debug_fetch_match_odds(event_id: str, geo_code: str = "BR", geo_subdivision: str = "BRSP") -> Optional[List[Dict]]:
        print(f"  [DEBUG] Fetching odds for event_id={event_id}, geo={geo_code}/{geo_subdivision}")
        result = original_fetch(event_id, geo_code, geo_subdivision)
        if result is None:
            print(f"  [DEBUG] FAILED for event_id={event_id}")
        elif result == "RATE_LIMITED":
            print(f"  [DEBUG] RATE_LIMITED for event_id={event_id}")
        else:
            print(f"  [DEBUG] SUCCESS for event_id={event_id}: {len(result)} odds entries")
        return result
    
    # Temporarily replace the function
    import sports_data.flashscore
    sports_data.flashscore.fetch_match_odds = debug_fetch_match_odds
    
    try:
        matches, error, league_winner_odds = scrape_league("Premier League", max_workers_odds=2)
        
        print(f"\nResults:")
        print(f"  Matches found: {len(matches)}")
        print(f"  Error flag: {error}")
        
        matches_with_odds = sum(1 for m in matches if m.get('odds'))
        print(f"  Matches with odds: {matches_with_odds}/{len(matches)}")
        
        if matches:
            # Show first match details
            first_match = matches[0]
            print(f"\nFirst match:")
            print(f"  Teams: {first_match.get('home_team')} vs {first_match.get('away_team')}")
            print(f"  Has odds: {bool(first_match.get('odds'))}")
            if first_match.get('odds'):
                print(f"  Odds count: {len(first_match['odds'])}")
            else:
                print(f"  No odds attached")
        
    finally:
        # Restore original function
        sports_data.flashscore.fetch_match_odds = original_fetch


def main():
    """Run all debug tests."""
    print("Premier League Odds Debugging")
    print("="*60)
    
    # Test 1: Event ID extraction
    event_ids = test_event_id_extraction()
    
    # Test 2: Direct API testing
    if event_ids:
        test_odds_api_direct(event_ids)
    
    # Test 3: Full scrape
    test_full_scrape()
    
    print("\n" + "="*60)
    print("Debugging complete")
    print("="*60)


if __name__ == "__main__":
    main()
