# Training Documentation

## Overview

The training system builds machine learning models to predict betting outcomes. It extracts features from historical match data and trains XGBoost models for multiple betting markets.

## Training Pipeline

### 1. Data Collection

The training process requires historical match data with:

- **Fixtures**: Match information (teams, dates, tournaments)
- **Odds**: Betting odds from bookmakers
- **Scores**: Final scores for completed matches

**Note**: Training only uses completed matches (those with final scores). The system automatically filters for matches that have been played and scored.

### 2. Feature Engineering

For each completed match, the system extracts features:

- **Team Form**: Win rate, average goals scored/conceded, form points (last 5 matches)
- **Head-to-Head**: Historical results between the two teams
- **Home/Away Performance**: Team performance at home vs away venues
- **Odds Features**: Average odds, odds spread across bookmakers
- **Temporal Features**: Day of week, time of day, season progression

These features are automatically computed from the database and normalized for model training.

### 3. Model Training

Models are trained for three betting markets:

- **1x2**: Match outcome (Home Win, Draw, Away Win) - 3-class classification
- **over_under**: Total goals over/under 2.5 - Binary classification
- **btts**: Both teams to score (Yes/No) - Binary classification

Each model uses **XGBoost** with:
- Cross-validation for evaluation
- Automatic hyperparameter tuning
- Class balancing for imbalanced datasets
- Model persistence to disk

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