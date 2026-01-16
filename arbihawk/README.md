# Arbihawk

The arbitrage hawk - A neural network-based betting prediction and recommendation system.

## Overview

Arbihawk uses machine learning (XGBoost) to predict match outcomes and identify value bets based on expected value calculations. The system:

- Collects match data and odds from scrapers (Betano, FBref)
- Stores data locally in SQLite
- Trains models on historical data
- Identifies value bets with positive expected value
- Tracks performance with fake money system
- Provides a dashboard for monitoring and control

## Setup

1. **Clone the repository with submodules:**

   ```bash
   git clone --recurse-submodules <repo-url>
   cd arbihawk
   ```

   Or if already cloned:

   ```bash
   git submodule update --init --recursive
   ```

2. **Create and activate the virtual environment:**

   **Windows PowerShell:**

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

   **macOS/Linux:**

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure settings (optional):**

   Edit `config/config.json` for main settings:

   ```json
   {
     "db_path": "data/arbihawk.db",
     "ev_threshold": 0.07
   }
   ```

   Edit `config/automation.json` for automation settings.

## Usage

### Common Workflows

1. **Collect Data** - Run data collection to gather fixtures, odds, and scores
2. **Train Models** - Train prediction models on historical data
3. **Start Dashboard** - Launch the monitoring dashboard at http://localhost:8000
4. **Run Automation** - Execute automated collection and training cycles

All commands are available as VS Code tasks for convenience. See [Tasks Guide](docs/tasks.md) for the complete reference.

## Markets

- **1x2**: Match outcome (Home Win, Draw, Away Win)
- **over_under**: Total goals over/under 2.5
- **btts**: Both teams to score (Yes/No)

## Architecture

```
arbihawk/
├── automation/          # Scheduled data collection and training
├── config/              # JSON configuration files
├── dashboard/           # FastAPI backend and React frontend
├── data/                # Database and data processing
├── engine/              # Value betting engine
├── models/              # XGBoost prediction models
├── monitoring/          # Metrics and reporting
├── scrapers/            # Git submodule for data scrapers
├── testing/             # Fake money system
└── docs/                # Documentation
```

## Data Storage

Data is stored locally in SQLite at `data/arbihawk.db`. The database includes:

- Fixtures (matches)
- Odds from scrapers
- Scores for completed matches
- Bet history (fake money)
- Model versions
- Performance metrics

## Configuration

All configuration is stored in JSON files in the `config/` directory:

- `config.json` - Main settings (database path, EV threshold)
- `automation.json` - Automation schedules, scraper args, fake money settings

## Documentation Index

- [Tasks Guide](docs/tasks.md) - Using VS Code tasks for all commands
- [Setup Guide](docs/setup.md) - Detailed setup instructions
- [Training Guide](docs/training.md) - Model training documentation
- [Predictor Guide](docs/predictor.md) - Model architecture and usage
- [Ingestion Guide](docs/ingestion.md) - Data ingestion from scrapers
- [Automation Guide](docs/automation.md) - Automated scheduling and workflows
- [Testing Guide](docs/testing.md) - Fake money system and performance testing
- [Monitoring Guide](docs/monitoring.md) - Metrics and performance tracking
- [Versioning Guide](docs/versioning.md) - Model versioning and rollback
- [Dashboard Guide](docs/dashboard.md) - Dashboard usage and API reference
