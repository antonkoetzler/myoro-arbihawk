# Arbihawk

The arbitrage hawk - A multi-domain prediction and trading system powered by machine learning.

## Overview

Arbihawk uses machine learning (XGBoost) for two domains:

### Sports Betting
- Collects match data and odds from scrapers (Betano, Flashscore, Livescore)
- Predicts match outcomes (1x2, Over/Under, BTTS)
- Identifies value bets with positive expected value
- Tracks performance with fake money system

### Stock/Crypto Trading
- Fetches price data from Alpha Vantage (stocks) and CoinGecko (crypto)
- Technical analysis features (RSI, MACD, Bollinger Bands, ATR)
- Three strategies: Momentum, Swing Trading, Volatility Breakout
- Paper trading with portfolio management and position sizing

Both domains share:
- SQLite local storage
- Model versioning and training pipelines
- Dashboard for monitoring and control
- Automated scheduling

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
│   ├── features.py      # Betting feature engineering
│   └── stock_features.py # Trading feature engineering
├── engine/              # Signal engines
│   ├── value_bet.py     # Value betting engine
│   └── trade_signal.py  # Trading signal engine
├── models/              # XGBoost prediction models
│   ├── predictor.py     # Betting predictor
│   └── trading_predictor.py # Trading predictor
├── trading/             # Stock/crypto trading
│   ├── portfolio_manager.py
│   ├── execution.py
│   └── service.py
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

### General
- [Tasks Guide](docs/tasks.md) - Using VS Code tasks for all commands
- [Setup Guide](docs/setup.md) - Detailed setup instructions
- [Dashboard Guide](docs/dashboard.md) - Dashboard usage and API reference
- [Automation Guide](docs/automation.md) - Automated scheduling and workflows
- [Versioning Guide](docs/versioning.md) - Model versioning and rollback

### Sports Betting
- [Training Guide](docs/training.md) - Model training documentation
- [Predictor Guide](docs/predictor.md) - Model architecture and usage
- [Calibration Guide](docs/calibration.md) - Probability calibration and ROI improvement
- [Ingestion Guide](docs/ingestion.md) - Data ingestion from scrapers
- [Testing Guide](docs/testing.md) - Fake money system and performance testing
- [Monitoring Guide](docs/monitoring.md) - Metrics and performance tracking

### Stock/Crypto Trading
- [Trading Guide](docs/trading.md) - **Complete trading system documentation** ⭐

### Development
- [Profitability Backlog](docs/backlog/backlog.md) - Tracked improvements for profitability
