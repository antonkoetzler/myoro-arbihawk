# Scrapers

## Overview

Multi-level abstract scraper system for fetching data from different sources.

## Structure

**BaseScraper** - Abstract base class for all scrapers.

**SportsbookScraper** - Abstract base for sportsbook odds scrapers. Defines:

- `fetch_odds()` - Fetch odds data
- `parse_odds()` - Parse raw data
- `normalize_odds()` - Convert to standard format

## How It Works

1. **BaseScraper** provides core interface (`fetch()`, `validate()`)
2. **SportsbookScraper** adds sportsbook-specific methods
3. Concrete implementations extend these base classes

## Adding New Sportsbooks

1. Inherit from `SportsbookScraper`
2. Implement `fetch_odds()`, `parse_odds()`, `normalize_odds()`
3. Add to `data/scrapers/__init__.py`

## Note

The system now uses RapidAPI's ODDS-API for data collection. See `data/collectors/odds_api.py` for the main data collection implementation.
