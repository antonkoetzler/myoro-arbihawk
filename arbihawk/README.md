# Arbihawk

The arbitrage hawk - A neural network-based betting prediction and recommendation system.

## Overview

Arbihawk uses machine learning (XGBoost) to predict match outcomes and identify value bets based on expected value calculations. The system:

- Collects match data and odds from RapidAPI's ODDS-API
- Stores data locally in SQLite
- Trains models on historical data
- Identifies value bets with positive expected value

## Setup

1. **Activate the virtual environment** (required before running any scripts):

   **Windows PowerShell:**

   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

   **Windows CMD:**

   ```cmd
   venv\Scripts\activate.bat
   ```

   **macOS/Linux:**

   ```bash
   source venv/bin/activate
   ```

2. **Install dependencies** (if not already installed):

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**

   Create a `.env` file in the `arbihawk` directory with:

   ```bash
   ODDS_API_KEY=your_rapidapi_key_here
   EV_THRESHOLD=0.07  # Optional: Expected value threshold (default 7%)
   DB_PATH=./data/arbihawk.db  # Optional: Database path
   ```

**Important**: Always activate the virtual environment before running any scripts!

## Usage

### Train Models

**Make sure the virtual environment is activated first!**

Train models for all markets (1x2, over_under, btts):

**Windows PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
python train.py
```

**Windows CMD:**

```cmd
venv\Scripts\activate.bat
python train.py
```

**macOS/Linux:**

```bash
source venv/bin/activate
python train.py
```

Or use the helper scripts:

- Windows: `.\train.ps1` (PowerShell) or `train.bat` (CMD)
- macOS/Linux: `./train.sh`

This will:

- Collect the last 30 days of match data
- Extract features from completed matches
- Train models for all markets
- Save models to `models/saved/`

See [docs/training.md](docs/training.md) for detailed training documentation.

### Get Betting Recommendations

```bash
# Get value bet recommendations
python main.py --market 1x2 --limit 10

# Use a specific model
python main.py --market 1x2 --model-path models/saved/1x2_model.pkl
```

### Test System

```bash
python test_system.py
```

## Markets

- **1x2**: Match outcome (Home Win, Draw, Away Win)
- **over_under**: Total goals over/under 2.5
- **btts**: Both teams to score (Yes/No)

## Architecture

- `data/collectors/odds_api.py`: ODDS-API data collection
- `data/database.py`: SQLite database management
- `data/features.py`: Feature engineering
- `models/predictor.py`: XGBoost prediction models
- `engine/value_bet.py`: Value betting engine
- `train.py`: Training script
- `main.py`: Main application for recommendations

## Data Storage

Data is stored locally in SQLite at `data/arbihawk.db` by default. The database includes:

- Fixtures (matches)
- Odds from multiple bookmakers
- Scores and settlements
- Indexes for efficient querying

## See Also

- [docs/setup.md](docs/setup.md) - Detailed setup instructions
- [docs/collector.md](docs/collector.md) - Data collection documentation
- [docs/predictor.md](docs/predictor.md) - Model documentation
