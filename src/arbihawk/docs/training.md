# Training Documentation

## Overview

The training system builds machine learning models for two domains:

- **Betting Domain**: Predicts sports betting outcomes (1x2, Over/Under, BTTS) - **This guide**
- **Trading Domain**: Predicts stock/crypto price direction (Momentum, Swing, Volatility strategies) - See [Trading Guide](trading.md#training-models)

Both domains use XGBoost classifiers with feature engineering, probability calibration, and optional hyperparameter tuning.

**Domain:** Betting

## Training Pipeline

### 1. Data Collection

The training process requires historical match data with:

- **Fixtures**: Match information (teams, dates, tournaments)
- **Odds**: Betting odds from bookmakers
- **Scores**: Final scores for completed matches

**Note**: Training only uses completed matches (those with final scores). The system automatically filters for matches that have been played and scored.

### 2. Feature Engineering

For each completed match, the system extracts **27 features**:

**Team Performance Features (16 features):**
- **Team Form** (last 5 matches): Win rate, average goals scored/conceded, form points (4 features × 2 teams = 8)
- **Head-to-Head**: Historical wins, draws, average goals (5 features)
- **Home/Away Performance**: Win rate and average goals at home/away (4 features)

**Market Features (4 features):**
- **Odds Features**: Average odds for home/draw/away, odds spread across bookmakers

**Temporal Features (4 features):**
- **Day of week**: 0 (Monday) to 6 (Sunday)
- **Hour**: Hour of day (0-23)
- **Is weekend**: 1 if Saturday/Sunday, 0 otherwise
- **Time period**: 0=morning (6-12), 1=afternoon (12-18), 2=evening (18-24), 3=night (0-6)

**Fatigue Features (2 features):**
- **Rest days**: Days since team's last match (home and away teams)

**Additional Features (1 feature):**
- **Odds spread**: Difference between max and min odds for home team

These features are automatically computed from the database and normalized for model training.

**Note:** For trading domain features, see [Trading Guide](trading.md#feature-engineering).

### 3. Model Training

Models are trained for three betting markets:

- **1x2**: Match outcome (Home Win, Draw, Away Win) - 3-class classification
- **over_under**: Total goals over/under 2.5 - Binary classification
- **btts**: Both teams to score (Yes/No) - Binary classification

Each model uses **XGBoost** with:
- Cross-validation for evaluation
- **Probability calibration** (isotonic regression or Platt scaling)
- Calibration metrics tracking (Brier Score, Expected Calibration Error)
- Class balancing for imbalanced datasets
- **Hyperparameter tuning** (optional, configurable)
- Model persistence to disk

**Calibration** ensures predicted probabilities are well-calibrated, which is critical for profitable betting. The system automatically:
- Splits data into training (80%) and calibration (20%) sets
- Trains model on training set
- Calibrates probabilities on separate calibration set
- Tracks calibration quality metrics

**Hyperparameter Tuning** (optional):
- Uses Optuna for automated hyperparameter optimization
- **Betting Domain**: Optimizes for ROI/profitability (not just accuracy)
- **Trading Domain**: Optimizes for Sharpe ratio (risk-adjusted returns)
- Temporal cross-validation (ensures training data is always before test data)
- Configurable search space (small/medium/large)
- Early stopping if no improvement
- Parallel execution support
- Default: **Disabled** (enable in `config/automation.json`)

**Betting Configuration** (`config/automation.json` → `hyperparameter_tuning`):
```json
{
  "enabled": false,  // Set to true to enable tuning
  "search_space": "small",  // 'small', 'medium', or 'large'
  "n_trials": null,  // null = auto (15/30/60), or specify number
  "n_jobs": 1,  // 1 = sequential, -1 = all CPUs, N = N workers
  "timeout": null,  // Maximum seconds (null = no timeout)
  "early_stopping_patience": 10,  // Stop if no improvement in N trials
  "min_samples": 300  // Minimum samples required for tuning
}
```

**Performance Impact:**
- **Small search space**: ~1.1 hours (3 markets × 15 trials × 3 min/trial)
- **With parallelization (n_jobs=4)**: ~17 minutes
- **Medium search space**: ~2.2 hours (3 markets × 30 trials)
- **Large search space**: ~4.4 hours (3 markets × 60 trials)

**Trading Configuration** (`config/automation.json` → `trading_hyperparameter_tuning`):
```json
{
  "enabled": false,  // Set to true to enable tuning
  "search_space": "small",  // 'small', 'medium', or 'large'
  "n_trials": null,  // null = auto (15/30/60), or specify number
  "n_jobs": 1,  // 1 = sequential, -1 = all CPUs, N = N workers
  "timeout": null,  // Maximum seconds (null = no timeout)
  "early_stopping_patience": 10,  // Stop if no improvement in N trials
  "min_samples": 300  // Minimum samples required for tuning
}
```

**Recommendation:** 
- **Betting**: Enable tuning when you have 10,000+ training samples for best results
- **Trading**: Enable tuning when you have 10,000+ training samples per strategy for best results

### 4. Model Storage

Trained models are saved to `models/saved/{market}_model.pkl` and include:

- The trained XGBoost model
- Feature names and order
- Training metadata (samples, CV score, timestamp)

Models are automatically versioned (see [Versioning Guide](versioning.md)) and can be rolled back if performance degrades.

## Running Training

Use the **Training: Train All Models** task (see [Tasks Guide](tasks.md)), or run:

```bash
python train.py
```

The training script will:

1. Check for sufficient data (warns if data is insufficient)
2. Extract features from all completed matches
3. Train models for each market
4. Save models with versioning
5. Display training metrics

## Requirements

Before training, ensure you have:

- **At least 100+ completed matches** with scores (recommended minimum)
- **Odds data** for feature extraction
- **Historical data** spanning multiple weeks/months for better predictions

The system will warn you if there's insufficient data and skip training for markets without enough samples.

## Model Performance

Training metrics include:

- **Cross-validation score**: Average accuracy across folds
- **Sample count**: Number of training examples
- **Feature count**: Number of features used
- **Label distribution**: Class balance in training data
- **Calibration metrics** (if calibration enabled):
  - **Brier Score**: Probability accuracy (lower is better)
  - **Expected Calibration Error (ECE)**: Calibration quality (lower is better)
  - **Calibration improvement**: Difference between uncalibrated and calibrated metrics

These metrics are stored with each model version and can be viewed in the dashboard.

## Troubleshooting

### No Training Data Available

**Symptom**: Script warns "No training data available"

**Solution**: 
- Run data collection to gather match data
- Ensure matches have been completed (have final scores)
- Check database using **Database: Check Stats** task

### Model Training Fails

**Symptom**: Training script errors or crashes

**Solution**:
- Verify you have sufficient data (at least 50-100 matches per market)
- Check database integrity
- Review error logs for specific issues
- Ensure all dependencies are installed

### Poor Model Performance

**Symptom**: Low cross-validation scores or poor predictions

**Solution**:
- Collect more historical data (more matches = better models)
- Check data quality (ensure scores are correctly matched)
- Review feature engineering logic
- Consider adjusting model hyperparameters

### API Rate Limits

**Symptom**: Data collection fails due to rate limits

**Solution**:
- The collector includes built-in rate limiting
- Wait and run again - incremental collection will skip existing data
- Adjust collection schedule to spread requests over time