"""
Scrapers for different data sources.
"""

from .base import BaseScraper
from .sportsbook import SportsbookScraper

__all__ = ["BaseScraper", "SportsbookScraper"]

