"""
Abstract base class for all data scrapers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseScraper(ABC):
    """Base class for all data scrapers."""
    
    @abstractmethod
    def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch data from the source. Returns list of data items."""
        pass
    
    @abstractmethod
    def validate(self, data: List[Dict[str, Any]]) -> bool:
        """Validate fetched data. Returns True if valid."""
        pass

