# Predictor Architecture

## Overview

The predictor is the core component that makes betting predictions. It's designed to be extended with multiple models later.

## Structure

**BasePredictor** - Abstract base class that all predictors inherit from. Ensures consistent interface.

**BettingPredictor** - Main predictor class. Handles:

- Training on historical match data
- Predicting outcome probabilities (home win, draw, away win)
- Calculating Expected Value (EV) for bets

## How It Works

1. **Train**: Model learns from historical matches with known outcomes
2. **Predict**: Model outputs probabilities for future matches
3. **Calculate EV**: Compare model probability vs. betting odds to find value

## Expected Value Formula

```text
EV = (Probability × Odds) - 1
```

If EV > 0, the bet has positive expected value.

## Future Scaling

New model types can be added by:

1. Inheriting from `BasePredictor`
2. Implementing the required methods
3. Adding to an ensemble system (future)
