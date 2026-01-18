# Data Collector

## Overview

The Data Collector manages data ingestion from external scrapers into the SQLite database.

## Data Sources

- **Betano Scraper** - Fixtures and odds from Betano sportsbook
- **Flashscore Scraper** - Match scores and results (primary)
- **Livescore Scraper** - Match scores and results (fallback)

## How It Works

1. Scrapers output JSON to stdout
2. Arbihawk reads the JSON via stdin or subprocess
3. Data is validated against JSON schemas
4. Valid data is stored in SQLite database
5. Match scores are matched to Betano fixtures using fuzzy team name matching

## Usage

Data collection is handled by the automation system:

```bash
# Collect data once
python -m automation.runner --mode=collect

# Run full automation cycle
python -m automation.runner --once
```

## See Also

- [Ingestion Guide](ingestion.md) - Detailed ingestion process
- [Automation Guide](automation.md) - Scheduling data collection