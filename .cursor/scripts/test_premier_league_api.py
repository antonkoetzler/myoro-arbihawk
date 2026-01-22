#!/usr/bin/env python3
"""Quick test of FlashScore odds API for Premier League."""
import requests
import json

ODDS_GRAPHQL_BASE = "https://global.ds.lsapp.eu/odds/pq_graphql"
PROJECT_ID = 401

# Test with a known event ID format (8 alphanumeric chars)
# These are example IDs - we'll need to extract real ones from the page
test_event_ids = [
    "QJkIQSvA",  # Example from code comments
    "test1234",  # Invalid test
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.flashscore.com/',
    'Accept': 'application/json'
}

print("Testing FlashScore Odds API")
print("=" * 60)

for event_id in test_event_ids:
    print(f"\nTesting event_id: {event_id}")
    url = f"{ODDS_GRAPHQL_BASE}?_hash=oce&eventId={event_id}&projectId={PROJECT_ID}&geoIpCode=BR&geoIpSubdivisionCode=BRSP"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Response keys: {list(data.keys())}")
            
            if 'errors' in data:
                print(f"  Errors: {data['errors']}")
            
            odds_comparison = data.get('data', {}).get('findOddsByEventId', {})
            if odds_comparison:
                markets = odds_comparison.get('markets', [])
                print(f"  Markets: {len(markets)}")
                if markets:
                    print(f"  ✓ SUCCESS: Found {len(markets)} markets")
                else:
                    print(f"  ⚠ WARNING: Empty markets array")
            else:
                print(f"  ✗ FAILED: No findOddsByEventId in response")
                print(f"  Full response (first 500 chars):")
                print(f"  {json.dumps(data, indent=2)[:500]}")
        else:
            print(f"  ✗ FAILED: HTTP {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"  ✗ EXCEPTION: {e}")

print("\n" + "=" * 60)
print("Test complete. If all fail, the API might be blocking or event IDs are wrong.")
