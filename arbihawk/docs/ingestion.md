# Ingestion Guide

## Overview

The ingestion system reads JSON from scrapers and stores data in SQLite.

## Data Sources

### Betano Scraper

Outputs JSON with leagues, fixtures, and odds:

```json
[
  {
    "league_id": 5,
    "league_name": "La Liga",
    "fixtures": [
      {
        "fixture_id": "123456",
        "home_team_name": "Real Madrid",
        "away_team_name": "Barcelona",
        "start_time": "2024-01-15T20:00:00Z",
        "odds": [
          {
            "market_id": "1x2",
            "market_name": "Match Result",
            "outcome_id": "1",
            "outcome_name": "Home",
            "odds_value": 2.10
          }
        ]
      }
    ]
  }
]
```

### FBref Scraper

Outputs JSON with match scores:

```json
{
  "matches": [
    {
      "home_team": "Real Madrid",
      "away_team": "Barcelona",
      "home_score": 2,
      "away_score": 1,
      "start_time": "2024-01-15",
      "league": "La Liga"
    }
  ],
  "total_matches": 1,
  "season": "2024-2025"
}
```

## Piping Data

Scrapers output to stdout for piping:

```bash
# Direct pipe
python scrapers/src/sportsbooks/betano.py | python -m data.ingestion betano

# From file
python -m data.ingestion betano --file output.json
```

## Validation

Data is validated against JSON schemas before ingestion:

- Required fields are checked
- Types are validated
- Invalid data is logged but doesn't stop ingestion

## Matching Algorithm

FBref scores are matched to Betano fixtures using:

1. **Team Name Matching**: Fuzzy matching with rapidfuzz
2. **Time Proximity**: Within configurable tolerance (default 2 hours)
3. **Name Normalization**: Common aliases handled

## Deduplication

- Fixtures: Deduplicated by `fixture_id`
- Odds: Deduplicated by `fixture_id` + `market_id` + `outcome_id`
- Scores: Deduplicated by `fixture_id`

## Ingestion Metadata

Each ingestion is tracked:

- Source (betano/fbref)
- Timestamp
- Records count
- Validation status
- Errors (if any)
