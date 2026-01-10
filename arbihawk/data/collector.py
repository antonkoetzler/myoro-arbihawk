"""
Data collector for fetching match data.
"""

from typing import List, Dict, Any, Optional
from .collectors.odds_api import ODDSAPICollector
from .database import Database


class DataCollector:
    """Collects historical match data for training using ODDS-API."""
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.odds_collector = ODDSAPICollector(self.db)
    
    def collect_fixtures(self, sport_id: int, from_date: str, to_date: str,
                        tournament_ids: Optional[List[int]] = None,
                        incremental: bool = True) -> int:
        """Collect fixtures for a date range."""
        return self.odds_collector.collect_fixtures(
            sport_id, from_date, to_date, tournament_ids, incremental
        )
    
    def collect_odds_for_fixtures(self, fixture_ids: Optional[List[str]] = None,
                                  bookmakers: Optional[List[str]] = None,
                                  limit: Optional[int] = None) -> int:
        """Collect odds for fixtures that have odds available."""
        collected = 0
        
        if fixture_ids:
            fixtures = self.db.get_fixtures()
            fixtures = fixtures[fixtures['fixture_id'].isin(fixture_ids)]
        else:
            # Get fixtures without odds, but only those that likely have odds
            # We'll check hasOdds field if available, otherwise limit to recent fixtures
            fixtures = self.db.get_fixtures()
            if len(fixtures) == 0:
                return 0
            
            # Skip fixtures that already have odds
            odds = self.db.get_odds()
            if len(odds) > 0:
                fixtures_with_odds = odds['fixture_id'].unique()
                fixtures = fixtures[~fixtures['fixture_id'].isin(fixtures_with_odds)]
            
            # Limit to most recent fixtures to avoid hitting rate limits
            if limit:
                fixtures = fixtures.tail(limit)
            else:
                # Default: only collect odds for last 100 fixtures
                fixtures = fixtures.tail(100)
        
        if len(fixtures) == 0:
            return 0
        
        print_info(f"Collecting odds for {len(fixtures)} fixtures (limited to avoid rate limits)...")
        
        for idx, (_, fixture) in enumerate(fixtures.iterrows(), 1):
            if idx % 10 == 0:
                print_info(f"  Progress: {idx}/{len(fixtures)}")
            
            if self.odds_collector.collect_odds(fixture['fixture_id'], bookmakers):
                collected += 1
        
        return collected
    
    def collect_scores_for_fixtures(self, fixture_ids: Optional[List[str]] = None,
                                   limit: Optional[int] = None) -> int:
        """Collect scores for completed fixtures only."""
        collected = 0
        
        if fixture_ids:
            fixtures = self.db.get_fixtures()
            fixtures = fixtures[fixtures['fixture_id'].isin(fixture_ids)]
        else:
            # Only get fixtures that are finished (status = 'finished')
            fixtures = self.db.get_fixtures()
            fixtures = fixtures[fixtures['status'] == 'finished']
            
            # Skip fixtures that already have scores
            scores = self.db.get_scores()
            if len(scores) > 0:
                fixtures_with_scores = scores['fixture_id'].unique()
                fixtures = fixtures[~fixtures['fixture_id'].isin(fixtures_with_scores)]
            
            # Limit to avoid rate limits
            if limit:
                fixtures = fixtures.tail(limit)
            else:
                # Default: only collect scores for last 100 finished fixtures
                fixtures = fixtures.tail(100)
        
        if len(fixtures) == 0:
            return 0
        
        print_info(f"Collecting scores for {len(fixtures)} finished fixtures...")
        
        for idx, (_, fixture) in enumerate(fixtures.iterrows(), 1):
            if idx % 10 == 0:
                print_info(f"  Progress: {idx}/{len(fixtures)}")
            
            if self.odds_collector.collect_scores(fixture['fixture_id']):
                collected += 1
        
        return collected

