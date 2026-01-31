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
- JSON configuration files (`config/config.json`, `config/automation.json`)

## Setup

1. **Clone repository:**
   - `git clone --recurse-submodules <repo-url>`
   - Or if already cloned: `git submodule update --init --recursive`

2. **Initialize project:**
   - VS Code task: **Setup: Initialize Git Submodules** (`Ctrl+Shift+P` → "Tasks: Run Task")
   - VS Code task: **Setup: Install Dependencies** (`Ctrl+Shift+P` → "Tasks: Run Task")

3. **Configure (optional):**
   - Edit `config/config.json` for main settings
   - Edit `config/automation.json` for automation settings
   - API keys (optional): Add Alpha Vantage/CoinGecko keys to `config/config.json` → `trading.api_keys` for better data collection reliability

## Quick Start

1. **Start the backend:**
   - VS Code task: **Dashboard Backend: Start Server** (`Ctrl+Shift+P` → "Tasks: Run Task")

2. **Start the frontend:**
   - VS Code task: **Dashboard Frontend: Start Dev Server** (`Ctrl+Shift+P` → "Tasks: Run Task")

3. **Open the dashboard:**
   - Navigate to <http://localhost:5173>

4. **Sports Betting:**
   - Collect data: Dashboard → Automation tab → Betting group → "Actions" → "Collect Data"
   - Train models: Dashboard → Automation tab → Betting group → "Actions" → "Train Models"
   - Start daemon: Dashboard → Automation tab → Betting group → "Actions" → "Start Daemon"
   - **Daemon mode:** Runs collection → training → betting cycles automatically at configured intervals
   - Monitor: Dashboard → Betting tab for value bets and performance

5. **Stock/Crypto Trading:**
   - Enable trading: Edit `config/config.json` → Set `trading.enabled` to `true`
   - Initialize portfolio: Dashboard → Automation tab → Trading group → "Actions" → "Initialize Portfolio"
   - Test first: Dashboard → Automation tab → Trading group → "Actions" → "Full Run"
   - Start daemon: Dashboard → Automation tab → Trading group → "Actions" → "Start Daemon"
   - **Daemon mode:** Runs collection → training → trading cycle every hour automatically
   - Monitor: Dashboard → Trading tab for portfolio performance and positions

**Both systems can run simultaneously in daemon mode for hands-off operation.**

All commands are available as VS Code tasks. See [Tasks Guide](docs/tasks.md) for complete reference.

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

- [Trading Usage Guide](docs/trading-usage.md) - **Step-by-step usage instructions** ⭐
- [Trading Guide](docs/trading.md) - Technical reference (architecture, strategies, API)

### Development

- [Profitability Backlog](docs/backlog/backlog.md) - Tracked improvements for profitability
