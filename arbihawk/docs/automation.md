# Automation Guide

## Overview

The automation system handles scheduled data collection and model training. It orchestrates the entire pipeline from scraping data to training models, with built-in scheduling, error handling, and monitoring.

## How It Works

The automation system runs in several modes:

- **Collection Mode**: Executes scrapers and ingests data only
- **Training Mode**: Trains models on collected data only
- **Betting Mode**: Places bets using active models (if enabled)
- **Full Cycle**: Runs collection → training → betting sequentially
- **Daemon Mode**: Continuously runs full cycles at configured intervals
- **Once Mode**: Runs a single full cycle and exits (useful for cron jobs)

## Data Collection Cycle

When running collection, the system:

1. Executes Betano scraper to fetch fixtures and odds
2. Ingests Betano data into the database with validation
3. Executes Flashscore scraper to fetch match scores (primary)
4. If Flashscore fails, executes Livescore scraper as fallback
5. Ingests match score data into the database
6. Matches scores to fixtures using fuzzy team name matching
7. Settles any pending bets based on completed match results

## Training Cycle

When running training, the system:

1. Creates a database backup (if configured)
2. Extracts features from historical match data
3. Trains XGBoost models for all markets (1x2, over_under, btts)
4. Saves models to disk with versioning
5. Records training metrics
6. Checks for rollback conditions (if auto-rollback enabled)

## Betting Cycle

When running betting (automatically after training if enabled, or manually):

1. Checks if fake money is enabled
2. Checks if auto-betting is enabled (for automatic execution)
3. Loads all active models (1x2, over_under, btts)
4. For each model:
   - Finds value bets using ValueBetEngine
   - Places bets via VirtualBankroll
   - Tags each bet with the model market for tracking
5. Returns summary of bets placed per model

**Note**: Betting only executes if `fake_money.enabled` is true. For automatic betting after training, `auto_bet_after_training` must also be true.

## Configuration

Edit `config/automation.json` to configure automation behavior:

```json
{
  "collection_schedule": "0 */6 * * *",
  "training_schedule": "0 2 * * *",
  "incremental_mode": true,
  "matching_tolerance_hours": 2,
  "scraper_args": {
    "betano": [],
    "flashscore": ["--headless"],
    "livescore": ["--no-proxy"]
  }
}
```

### Configuration Options

- **collection_schedule**: Cron expression for when to run collection
- **training_schedule**: Cron expression for when to run training
- **incremental_mode**: Only fetch new data (skips existing records)
- **matching_tolerance_hours**: Time window for matching scores to fixtures
- **scraper_args**: Command-line arguments passed to scrapers

## Dashboard Control

The dashboard provides a web interface to:

- Trigger collection manually
- Trigger training manually
- Trigger betting manually
- Start/stop daemon mode
- Configure fake money settings (including auto-betting)
- Stop running automation tasks
- View real-time logs
- Monitor automation status

Access these controls at the Automation page in the dashboard.

### Configuration via Dashboard

All fake money settings can be changed via the dashboard:

- Toggle auto-betting after training
- View current settings (starting balance, bet sizing strategy, etc.)
- No manual config file editing required

Settings are persisted to `config/automation.json` and reloaded automatically.

## Running Automation

### Local Development

For local development, use VS Code tasks (see [Tasks Guide](tasks.md)):

- **Automation: Collect Data** - Run data collection
- **Automation: Train Models** - Run training
- **Automation: Full Cycle** - Run complete cycle
- **Automation: Run Daemon** - Run continuously
- **Automation: Check Status** - Check current status

### Production Deployment

For production servers using cron or systemd, use the CLI directly:

```bash
# Run data collection only
python -m automation.runner --mode=collect

# Run training only
python -m automation.runner --mode=train

# Run full cycle (collection + training + betting)
python -m automation.runner --mode=full

# Run as continuous daemon
python -m automation.runner --daemon --interval=21600

# Run once and exit (for cron jobs)
python -m automation.runner --once

# Check status
python -m automation.runner --status
```

### Cron Configuration

Add to crontab for scheduled execution:

```bash
# Run every 6 hours
0 */6 * * * cd /path/to/arbihawk && python -m automation.runner --once

# Run training daily at 2 AM
0 2 * * * cd /path/to/arbihawk && python -m automation.runner --mode=train
```

## Troubleshooting

### Scraper Not Found

Ensure scrapers are installed as a git submodule:

```bash
git submodule update --init --recursive
```

Or use the **Setup: Initialize Git Submodules** task (see [Tasks Guide](tasks.md)).

### Rate Limiting

If scrapers hit rate limits:

- Adjust delays in scraper args
- Increase interval between cycles
- Enable incremental mode to skip existing data

### Training Fails

Check that you have enough data. Use the **Database: Check Stats** task or run:

```bash
python -c "from data.database import Database; db = Database(); print(db.get_database_stats())"
```

Ensure you have at least 100+ completed matches with scores before training.

### Daemon Not Starting

- Check that no other automation process is running
- Verify database is accessible
- Check logs for specific error messages
