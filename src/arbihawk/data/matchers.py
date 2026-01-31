"""
Score matching service for linking match scores (Flashscore/Livescore) to Betano fixtures.
Uses central match_identity layer (fuzzy + aliases) and time proximity.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd

from .database import Database
from . import match_identity
import config


class ScoreMatcher:
    """
    Matches match scores (Flashscore/Livescore) to Betano fixtures.
    
    Uses fuzzy team name matching and time proximity to find
    corresponding fixtures for incoming scores.
    
    Example usage:
        matcher = ScoreMatcher()
        
        # Match a score to a fixture
        fixture_id = matcher.match_score(
            home_team="Manchester United",
            away_team="Liverpool",
            match_time="2024-01-15T15:00:00Z"
        )
    """
    
    def __init__(self, db: Optional[Database] = None,
                 tolerance_hours: Optional[int] = None,
                 min_match_score: Optional[int] = None):
        """
        Initialize matcher. Uses central match_identity and config for aliases/threshold.
        
        Args:
            db: Database instance
            tolerance_hours: Time tolerance for matching (default from config)
            min_match_score: Minimum fuzzy match score (0-100); default from config (75)
        """
        self.db = db or Database()
        self.tolerance_hours = tolerance_hours or config.MATCHING_TOLERANCE_HOURS
        self.min_match_score = (
            min_match_score
            if min_match_score is not None
            else getattr(config, "MATCHING_MIN_MATCH_SCORE", 75)
        )
        self._aliases = getattr(config, "TEAM_ALIASES", {})
        self._unmatched = []
    
    def normalize_team_name(self, name: str) -> str:
        """Normalize team name (delegates to match_identity)."""
        return match_identity.normalize_team_name(name, self._aliases)
    
    def calculate_team_similarity(self, name1: str, name2: str) -> int:
        """Similarity 0-100 (delegates to match_identity)."""
        return match_identity.team_similarity(name1, name2, self._aliases)
    
    def match_score(self, home_team: str, away_team: str,
                    match_time: str) -> Optional[str]:
        """
        Find matching fixture for a score.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            match_time: Match time (ISO format)
            
        Returns:
            fixture_id if match found, None otherwise
        """
        # Get fixtures within time window
        try:
            match_dt = datetime.fromisoformat(match_time.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            try:
                match_dt = datetime.strptime(match_time, '%Y-%m-%d')
            except (ValueError, TypeError):
                return None
        
        # Calculate time window
        start_window = (match_dt - timedelta(hours=self.tolerance_hours)).isoformat()
        end_window = (match_dt + timedelta(hours=self.tolerance_hours)).isoformat()
        
        # Get fixtures in time window
        fixtures = self.db.get_fixtures(from_date=start_window, to_date=end_window)
        
        if len(fixtures) == 0:
            self._log_unmatched(home_team, away_team, match_time, "no fixtures in window")
            return None
        
        # Find best match
        best_match = None
        best_score = 0
        best_score_seen = 0
        
        for _, fixture in fixtures.iterrows():
            fixture_home = fixture['home_team_name']
            fixture_away = fixture['away_team_name']
            home_score = self.calculate_team_similarity(home_team, fixture_home)
            away_score = self.calculate_team_similarity(away_team, fixture_away)
            combined_score = (home_score + away_score) / 2
            if combined_score > best_score_seen:
                best_score_seen = combined_score
            if combined_score >= self.min_match_score and combined_score > best_score:
                best_score = combined_score
                best_match = fixture['fixture_id']
        
        if best_match is None:
            self._log_unmatched(
                home_team, away_team, match_time,
                f"best score {best_score_seen:.0f} below threshold {self.min_match_score}"
            )
        
        return best_match
    
    def match_scores_batch(self, scores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Match multiple scores to fixtures.
        
        Args:
            scores: List of score dicts with home_team, away_team, match_time
            
        Returns:
            Dict with matched and unmatched counts
        """
        matched = 0
        unmatched = 0
        results = []
        
        for score in scores:
            fixture_id = self.match_score(
                home_team=score.get('home_team', ''),
                away_team=score.get('away_team', ''),
                match_time=score.get('match_time', score.get('start_time', ''))
            )
            
            if fixture_id:
                matched += 1
                results.append({
                    "score": score,
                    "fixture_id": fixture_id,
                    "matched": True
                })
            else:
                unmatched += 1
                results.append({
                    "score": score,
                    "fixture_id": None,
                    "matched": False
                })
        
        return {
            "total": len(scores),
            "matched": matched,
            "unmatched": unmatched,
            "match_rate": matched / len(scores) if scores else 0,
            "results": results
        }
    
    def update_scores_with_matches(self, scores: List[Dict[str, Any]]) -> int:
        """
        Match scores and update database with matched fixture IDs.
        
        Args:
            scores: List of score dicts
            
        Returns:
            Number of scores updated
        """
        updated = 0
        
        for score in scores:
            fixture_id = self.match_score(
                home_team=score.get('home_team', ''),
                away_team=score.get('away_team', ''),
                match_time=score.get('match_time', score.get('start_time', ''))
            )
            
            if fixture_id:
                self.db.insert_score(fixture_id, {
                    'home_score': score.get('home_score'),
                    'away_score': score.get('away_score'),
                    'status': 'finished'
                })
                updated += 1
        
        return updated
    
    def _log_unmatched(self, home_team: str, away_team: str,
                       match_time: str, reason: str) -> None:
        """Log unmatched score for review."""
        self._unmatched.append({
            "home_team": home_team,
            "away_team": away_team,
            "match_time": match_time,
            "reason": reason
        })
    
    def get_unmatched(self) -> List[Dict[str, Any]]:
        """Get list of unmatched scores."""
        return self._unmatched
    
    def clear_unmatched(self) -> None:
        """Clear unmatched log."""
        self._unmatched = []
