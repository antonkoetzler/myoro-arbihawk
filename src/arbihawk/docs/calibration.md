# Probability Calibration

## Overview

Probability calibration is a critical component for profitable prediction systems. This document explains why calibration matters, how it's implemented in Arbihawk, and the research evidence supporting its importance.

## Why Calibration Matters

### The Problem

Raw machine learning model probabilities (especially from XGBoost) are often **miscalibrated**:
- **Overconfident**: Model predicts 80% probability, but actual frequency is only 60%
- **Underconfident**: Model predicts 40% probability, but actual frequency is 60%

When probabilities are miscalibrated:
- **Expected Value (EV) calculations are wrong** - You think a bet has value when it doesn't
- **Kelly betting fails** - Optimal bet sizing requires accurate probabilities
- **Profitability suffers** - You make bets based on incorrect edge estimates

### The Research Evidence

**Walsh & Joshi (2023/2024) Study: "Machine learning for sports betting: should model selection be based on accuracy or calibration?"**

This study compared two betting systems for NBA:
- **Calibration-selected system**: Models chosen based on calibration quality
- **Accuracy-selected system**: Models chosen based on prediction accuracy

**Results:**

| Metric | Calibration-Selected | Accuracy-Selected |
|--------|---------------------|-------------------|
| Average ROI (fixed staking) | **+34.7%** | -35.2% |
| Best-case ROI (Kelly staking) | **+36.93%** | +5.56% |

**Key Findings:**
- Calibration-driven model selection gave **much better profit**
- Accuracy-driven selection sometimes lost consistently
- Kelly betting with miscalibrated models was particularly risky
- **Calibration is necessary for profitable betting, but not sufficient** - you still need good features and enough data

## How Calibration Works

### Calibration Methods

Arbihawk supports two calibration methods:

1. **Isotonic Regression** (default)
   - Non-parametric, more flexible
   - Works well with sufficient data (≥50 samples)
   - Can handle any probability distribution shape

2. **Platt Scaling**
   - Parametric (logistic regression)
   - Requires less data
   - Assumes sigmoid-shaped probability distribution

### Calibration Process

1. **Data Split**: Training data is split into:
   - **Training set (80%)**: Used to train the base XGBoost model
   - **Calibration set (20%)**: Used to fit the calibrator

2. **Model Training**: XGBoost model is trained on the training set

3. **Calibration**: 
   - Get uncalibrated predictions on calibration set
   - Fit calibrator to map uncalibrated → calibrated probabilities
   - For multiclass: calibrate each class separately (one-vs-rest)

4. **Evaluation**: Calculate calibration metrics:
   - **Brier Score**: Measures probability accuracy (lower is better, perfect = 0.0)
   - **Expected Calibration Error (ECE)**: Measures how well predicted probabilities match actual frequencies (lower is better)

5. **Application**: When making predictions, calibrated probabilities are used automatically

## Calibration Metrics

### Brier Score

**Formula:**
```
Brier Score = mean((predicted_probability - actual_outcome)²)
```

**Interpretation:**
- **0.0**: Perfect calibration
- **< 0.20**: Good calibration
- **< 0.15**: Very good calibration
- **> 0.30**: Poor calibration

### Expected Calibration Error (ECE)

**How it works:**
1. Bin predictions by probability (e.g., 0.0-0.1, 0.1-0.2, ..., 0.9-1.0)
2. For each bin, compare:
   - Average predicted probability in bin
   - Actual frequency of outcomes in bin
3. Weight by proportion of samples in each bin
4. Sum absolute differences

**Interpretation:**
- **0.0**: Perfect calibration
- **< 0.05**: Good calibration
- **< 0.10**: Acceptable calibration
- **> 0.15**: Poor calibration

## Implementation in Arbihawk

### Training with Calibration

Calibration is **automatically enabled** when:
- `enable_calibration=True` (default)
- At least 50 training samples available
- `calibration_split > 0` (default: 0.2)

```python
from models.predictor import BettingPredictor

predictor = BettingPredictor(market='1x2', enable_calibration=True)
predictor.train(X, y, calibration_split=0.2)
```

### Accessing Calibration Metrics

```python
# After training
metrics = predictor.calibration_metrics

# Metrics structure:
{
    'uncalibrated': {
        'brier_score': 0.25,
        'ece': 0.12
    },
    'calibrated': {
        'brier_score': 0.18,  # Improved!
        'ece': 0.06           # Improved!
    },
    'improvement': {
        'brier_score': 0.07,  # How much better
        'ece': 0.06
    }
}
```

### Using Calibrated Probabilities

Calibrated probabilities are used **automatically** in predictions:

```python
# Calibrated probabilities are returned automatically
probabilities = predictor.predict_probabilities(features)

# These probabilities are well-calibrated and can be used for EV calculations
for outcome, prob in probabilities.items():
    ev = (prob * odds) - 1
    if ev > threshold:
        # Place bet
```

## Dashboard Display

The dashboard displays calibration metrics for each model version:

- **Brier Score**: Probability accuracy metric
- **ECE**: Expected Calibration Error
- **Calibration Improvement**: How much calibration improved the metrics

Metrics are only shown for models that have calibration data (newer models).

## Model Persistence

Calibrated models are saved with:
- Trained XGBoost model
- Calibrator (isotonic regression or Platt scaling per class)
- Calibration metrics (Brier Score, ECE, improvement)
- Label encoder
- Training metadata

**Backward Compatibility**: Old models without calibration still load and work correctly (they just won't have calibrated probabilities).

## Best Practices

1. **Always enable calibration** - It's enabled by default for good reason
2. **Monitor calibration metrics** - Check Brier Score and ECE in dashboard
3. **Recalibrate periodically** - As data drifts, recalibrate models
4. **Use sufficient data** - Calibration requires at least 50 samples
5. **Compare uncalibrated vs calibrated** - Check improvement metrics

## Troubleshooting

### Calibration Not Applied

**Symptom**: `calibrator` is `None` after training

**Causes**:
- Insufficient data (< 50 samples)
- `enable_calibration=False`
- `calibration_split=0`

**Solution**: Ensure you have enough data and calibration is enabled

### Poor Calibration Metrics

**Symptom**: High Brier Score (> 0.30) or ECE (> 0.15)

**Causes**:
- Insufficient training data
- Poor feature quality
- Model overfitting

**Solution**:
- Collect more historical data
- Improve feature engineering
- Check for data quality issues

### Calibration Makes Metrics Worse

**Symptom**: Calibration improvement is negative

**Causes**:
- Very small calibration set
- Overfitting on calibration set
- Insufficient data

**Solution**: 
- Increase calibration split (but not too much - need training data)
- Collect more data
- This is rare but can happen with very small datasets

## References

- Walsh, B., & Joshi, S. (2023/2024). "Machine learning for sports betting: should model selection be based on accuracy or calibration?" *ScienceDirect*
- Niculescu-Mizil, A., & Caruana, R. (2005). "Predicting good probabilities with supervised learning." *ICML*
- Platt, J. (1999). "Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods." *Advances in large margin classifiers*

## Summary

Probability calibration is **essential** for profitable betting because:

1. ✅ **Improves ROI** - Research shows +35% ROI improvement
2. ✅ **Accurate EV calculations** - Well-calibrated probabilities = accurate edge estimates
3. ✅ **Better bet sizing** - Kelly betting requires accurate probabilities
4. ✅ **Risk management** - Avoid overconfident bets that lose money

Arbihawk implements calibration automatically, tracks metrics, and displays them in the dashboard. Always check calibration metrics when evaluating model performance.
