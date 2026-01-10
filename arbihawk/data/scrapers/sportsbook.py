"""
Abstract base class for sportsbook scrapers.
"""

from abc import abstractmethod
from typing import List, Dict, Any
from .base import BaseScraper


class SportsbookScraper(BaseScraper):
    """Abstract base class for sportsbook odds scrapers."""
    
    @abstractmethod
    def fetch_odds(self, event_id: str = None, **kwargs) -> List[Dict[str, Any]]:
        """Fetch odds for events. Can fetch all or specific event."""
        pass
    
    @abstractmethod
    def parse_odds(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw odds data into standardized format."""
        pass
    
    @abstractmethod
    def normalize_odds(self, odds: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize odds to standard format (home_win, draw, away_win)."""
        pass
    
    def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch odds data."""
        return self.fetch_odds(**kwargs)
    
    def validate(self, data: List[Dict[str, Any]]) -> bool:
        """Validate odds data structure."""
        if not isinstance(data, list):
            return False
        for item in data[:3]:  # Check first 3 items
            if not isinstance(item, dict):
                return False
            # Check for required fields
            if 'eventId' not in item and 'teams' not in item:
                return False
        return True

