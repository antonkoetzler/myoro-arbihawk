# VS Code Tasks Reference

## Accessing Tasks

Press `Ctrl+Shift+P` → "Tasks: Run Task" or use `Terminal > Run Task...`

## Task List

### Setup

**Setup: Install Dependencies**  
Installs Python dependencies from `requirements.txt`

**Setup: Initialize Git Submodules**  
Initializes git submodules, creates scrapers venv, and installs scrapers requirements

### Automation

**Automation: Collect Data**  
Runs data collection (Betano + Flashscore/Livescore)

**Automation: Train Models**  
Trains all prediction models

**Automation: Full Cycle**  
Runs collection followed by training

**Automation: Run Once**  
Runs single full cycle and exits

**Automation: Run Daemon**  
Runs continuously in background

**Automation: Check Status**  
Displays scheduler status

### Training

**Training: Train All Models**  
Trains models for all markets (1x2, over_under, btts)

### Dashboard Backend

**Dashboard Backend: Start Server**  
Starts backend server at <http://localhost:8000>

**Dashboard Backend: Start with Reload**  
Starts backend with auto-reload for development

### Dashboard Frontend

**Dashboard Frontend: Install Dependencies**  
Installs frontend dependencies (bun)

**Dashboard Frontend: Start Dev Server**  
Starts frontend development server (auto-installs dependencies first)

### Database

**Database: Check Stats**  
Displays database statistics (row counts per table)

### Trading

**Trading: Collect Data**  
Fetches latest price data for all watchlist symbols (stocks and crypto)

**Trading: Train Models**  
Trains all trading strategy models (momentum, swing, volatility)

**Trading: Run Trading Cycle**  
Executes one trading cycle (updates positions, finds signals, executes trades)

**Trading: Initialize Portfolio**  
Initializes portfolio with starting balance ($10k default)

**Trading: Check Portfolio Status**  
Displays portfolio performance metrics and current status

## Notes

- All Python tasks use the virtual environment at `arbihawk/venv/`
- Background tasks can be stopped with `Ctrl+C` or by closing the terminal
- Tasks are for local development; use CLI commands for production
