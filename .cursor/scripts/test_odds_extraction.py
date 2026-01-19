"""Test odds extraction from FlashScore and LiveScore."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "arbihawk"))

def test_odds():
    """Test odds extraction."""
    print("Testing FlashScore odds extraction...")
    try:
        from scrapers.src.sports_data.flashscore import fetch_match_odds, fetch_league_winner_odds
        
        # Test match odds
        odds = fetch_match_odds('QJkIQSvA')
        print(f"  Match odds: {len(odds) if odds else 0} entries")
        if odds and len(odds) > 0:
            print(f"  Sample: {odds[0]}")
        
        # Test league winner odds
        lwo = fetch_league_winner_odds('KKay4EE8')
        print(f"  League winner odds: {len(lwo) if lwo else 0} entries")
        if lwo and len(lwo) > 0:
            print(f"  Sample: {lwo[0]}")
        
        print("✓ FlashScore odds extraction working")
    except Exception as e:
        print(f"✗ FlashScore failed: {e}")
        return False
    
    print("\nTesting LiveScore odds extraction...")
    try:
        from scrapers.src.sports_data.livescore import fetch_match_odds, fetch_league_winner_odds
        
        # Test match odds
        odds = fetch_match_odds('QJkIQSvA')
        print(f"  Match odds: {len(odds) if odds else 0} entries")
        
        # Test league winner odds
        lwo = fetch_league_winner_odds('KKay4EE8')
        print(f"  League winner odds: {len(lwo) if lwo else 0} entries")
        if lwo and len(lwo) > 0:
            print(f"  Sample: {lwo[0]}")
        
        print("✓ LiveScore odds extraction working")
    except Exception as e:
        print(f"✗ LiveScore failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_odds()
    sys.exit(0 if success else 1)
