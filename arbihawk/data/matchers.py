"""
Score matching service for linking FBref scores to Betano fixtures.
Uses fuzzy team name matching and time proximity.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd

try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

from .database import Database
import config


class ScoreMatcher:
    """
    Matches FBref scores to Betano fixtures.
    
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
    
    # Common team name variations for normalization
    TEAM_ALIASES = {
        "man utd": "manchester united",
        "man united": "manchester united",
        "man city": "manchester city",
        "spurs": "tottenham",
        "tottenham hotspur": "tottenham",
        "wolverhampton": "wolves",
        "wolverhampton wanderers": "wolves",
        "nottm forest": "nottingham forest",
        "west ham": "west ham united",
        "sheffield utd": "sheffield united",
        "newcastle utd": "newcastle united",
        "brighton": "brighton and hove albion",
        "real": "real madrid",
        "atleti": "atletico madrid",
        "atletico": "atletico madrid",
        "barca": "barcelona",
        "fc barcelona": "barcelona",
        "bayern": "bayern munich",
        "fc bayern": "bayern munich",
        "dortmund": "borussia dortmund",
        "bvb": "borussia dortmund",
        "gladbach": "borussia monchengladbach",
        "psg": "paris saint-germain",
        "paris sg": "paris saint-germain",
        "inter": "inter milan",
        "internazionale": "inter milan",
        "ac milan": "milan",
        "juve": "juventus",
    }
    
    def __init__(self, db: Optional[Database] = None,
                 tolerance_hours: Optional[int] = None,
                 min_match_score: int = 80):
        """
        Initialize matcher.
        
        Args:
            db: Database instance
            tolerance_hours: Time tolerance for matching (default from config)
            min_match_score: Minimum fuzzy match score (0-100)
        """
        self.db = db or Database()
        self.tolerance_hours = tolerance_hours or config.MATCHING_TOLERANCE_HOURS
        self.min_match_score = min_match_score
        self._unmatched = []
    
    def normalize_team_name(self, name: str) -> str:
        """
        Normalize team name for better matching.
        
        Args:
            name: Original team name
            
        Returns:
            Normalized team name
        """
        if not name:
            return ""
        
        # Convert to lowercase
        normalized = name.lower().strip()
        
        # Remove common suffixes
        suffixes = [" fc", " cf", " sc", " ac", " afc", " bc"]
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        
        # Check aliases
        if normalized in self.TEAM_ALIASES:
            normalized = self.TEAM_ALIASES[normalized]
        
        return normalized
    
    def calculate_team_similarity(self, name1: str, name2: str) -> int:
        """
        Calculate similarity between two team names.
        
        Args:
            name1: First team name
            name2: Second team name
            
        Returns:
            Similarity score (0-100)
        """
        n1 = self.normalize_team_name(name1)
        n2 = self.normalize_team_name(name2)
        
        # Exact match after normalization
        if n1 == n2:
            return 100
        
        # Use fuzzy matching if available
        if HAS_RAPIDFUZZ:
            # Try different fuzzy matching strategies
            ratio = fuzz.ratio(n1, n2)
            partial_ratio = fuzz.partial_ratio(n1, n2)
            token_sort = fuzz.token_sort_ratio(n1, n2)
            
            # Return the highest score
            return max(ratio, partial_ratio, token_sort)
        
        # Fallback: simple substring matching
        if n1 in n2 or n2 in n1:
            return 85
        
        # Check if main part matches
        n1_parts = n1.split()
        n2_parts = n2.split()
        
        common = set(n1_parts) & set(n2_parts)
        if common:
            total = len(set(n1_parts) | set(n2_parts))
            return int((len(common) / total) * 100)
        
        return 0
    
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
        except:
            try:
                match_dt = datetime.strptime(match_time, '%Y-%m-%d')
            except:
                return None
        
        # Calculate time window
        start_window = (match_dt - timedelta(hours=self.tolerance_hours)).isoformat()
        end_window = (match_dt + timedelta(hours=self.tolerance_hours)).isoformat()
        
        # Get fixtures in time window
        fixtures = self.db.get_fixtures(from_date=start_window, to_date=end_window)
        
        if len(fixtures) == 0:
            self._log_unmatched(home_team, away_team, match_time, "No fixtures in time window")
            return None
        
        # Find best match
        best_match = None
        best_score = 0
        
        for _, fixture in fixtures.iterrows():
            fixture_home = fixture['home_team_name']
            fixture_away = fixture['away_team_name']
            
            # Calculate team similarity scores
            home_score = self.calculate_team_similarity(home_team, fixture_home)
            away_score = self.calculate_team_similarity(away_team, fixture_away)
            
            # Combined score (both teams must match well)
            combined_score = (home_score + away_score) / 2
            
            # Must meet minimum threshold
            if combined_score >= self.min_match_score and combined_score > best_score:
                best_score = combined_score
                best_match = fixture['fixture_id']
        
        if best_match is None:
            self._log_unmatched(home_team, away_team, match_time, "No match above threshold")
        
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
