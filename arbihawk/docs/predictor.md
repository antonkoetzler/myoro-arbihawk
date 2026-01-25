# Predictor Architecture

## Overview

The predictor is the core component that makes betting predictions. It uses XGBoost for classification and includes probability calibration to ensure accurate probability estimates for profitable betting.

## Structure

**BasePredictor** - Abstract base class that all predictors inherit from. Ensures consistent interface.

**BettingPredictor** - Main predictor class. Handles:

- Training on historical match data
- Probability calibration (isotonic regression or Platt scaling)
- Predicting outcome probabilities (home win, draw, away win)
- Calculating Expected Value (EV) for bets

## How It Works

1. **Train**: Model learns from historical matches with known outcomes
   - Splits data into training and calibration sets (20% for calibration)
   - Trains XGBoost model on training set
   - Calibrates probabilities on separate calibration set
   - Evaluates calibration quality (Brier Score, ECE)
2. **Predict**: Model outputs calibrated probabilities for future matches
3. **Calculate EV**: Compare calibrated model probability vs. betting odds to find value

## Probability Calibration

**Why Calibration Matters:**
- Raw XGBoost probabilities are often miscalibrated (overconfident or underconfident)
- Research shows calibration-based model selection improves ROI from -35% to +35%
- Well-calibrated probabilities are essential for accurate EV calculations

**Calibration Methods:**
- **Isotonic Regression** (default): Non-parametric, more flexible, works well with sufficient data
- **Platt Scaling**: Parametric (logistic regression), requires less data

**Calibration Metrics:**
- **Brier Score**: Measures probability accuracy (lower is better, perfect = 0.0)
- **Expected Calibration Error (ECE)**: Measures how well predicted probabilities match actual frequencies (lower is better)

Calibration is automatically enabled when training with sufficient data (≥50 samples). The system tracks both uncalibrated and calibrated metrics to measure improvement.

## Expected Value Formula

```text
EV = (Probability × Odds) - 1
```

If EV > 0, the bet has positive expected value. Calibrated probabilities ensure more accurate EV calculations.

## Model Persistence

Models are saved with:
- Trained XGBoost model
- Calibrator (if calibration was applied)
- Calibration metrics (Brier Score, ECE)
- Label encoder
- Training metadata

Old models without calibration are backward compatible and will load correctly.

## Future Scaling

New model types can be added by:

1. Inheriting from `BasePredictor`
2. Implementing the required methods
3. Adding to an ensemble system (future)
