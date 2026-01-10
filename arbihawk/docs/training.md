# Training Documentation

## Overview

The training process collects historical match data, extracts features, and trains XGBoost models for multiple betting markets.

## Training Pipeline

### 1. Data Collection

The training script automatically collects data from RapidAPI's ODDS-API:

- **Fixtures**: Match information (teams, dates, tournaments)
- **Odds**: Betting odds from multiple bookmakers
- **Scores**: Final scores for completed matches

**Date Range**: Last 30 days of data (configurable in code)

**Incremental Collection**: Only fetches new data that doesn't exist in the database, respecting API rate limits.

### 2. Feature Engineering

For each completed match, features are extracted:

- **Team Form**: Win rate, average goals scored/conceded, form points (last 5 matches)
- **Head-to-Head**: Historical results between the two teams
- **Home/Away Performance**: Team performance at home vs away
- **Odds Features**: Average odds, odds spread across bookmakers

### 3. Model Training

Models are trained for three markets:

- **1x2**: Match outcome (Home Win, Draw, Away Win)
- **over_under**: Total goals over/under 2.5
- **btts**: Both teams to score (Yes/No)

Each model uses XGBoost with:
- Cross-validation for evaluation
- Automatic hyperparameter tuning
- Model persistence to disk

### 4. Model Storage

Trained models are saved to `models/saved/{market}_model.pkl` and can be loaded for predictions.

## Running Training

Simply run:
```bash
python train.py
```

The script will:
1. Collect data from the last 30 days
2. Train models for all markets
3. Save models to disk

## Requirements

- At least 30 days of historical match data with scores
- Odds data for feature extraction
- Completed matches (with final scores) for training labels

## Troubleshooting

**No training data available**: Ensure you have collected data with completed matches (scores). Run data collection first.

**Model training fails**: Check that you have sufficient data (at least 50-100 matches recommended per market).

**API rate limits**: The collector includes rate limiting. If you hit limits, wait and run again - incremental collection will skip existing data.

