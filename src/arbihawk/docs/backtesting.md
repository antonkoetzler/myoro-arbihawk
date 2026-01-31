# Backtesting Framework

Temporal validation framework for betting models using walk-forward validation.

## Overview

The backtesting framework simulates historical betting performance by:

1. Splitting data into temporal periods (walk-forward validation)
2. Training models on historical data up to each period
3. Making predictions on test period matches
4. Simulating betting with odds available at prediction time
5. Tracking performance metrics (ROI, Sharpe ratio, drawdown, etc.)

## Usage

### Command Line

```bash
# Run with default dates (last 6 months test, 3 months training before)
python -m backtesting.runner

# Custom date range
python -m backtesting.runner 2024-01-01 2024-06-01 2024-12-31 30

# Help
python -m backtesting.runner --help

# Via automation runner
python -m automation.runner --mode=backtest
```

### Python API

```python
from backtesting.backtest import BacktestEngine

engine = BacktestEngine(ev_threshold=0.05)  # 5% EV threshold

result = engine.run_backtest(
    train_start="2024-01-01",
    test_start="2024-06-01",
    test_end="2024-12-31",
    period_days=30,  # 30-day test windows
    min_training_samples=50
)

print(f"ROI: {result.overall_metrics['roi']:.2%}")
print(f"Win rate: {result.overall_metrics['win_rate']:.2%}")
print(f"Sharpe ratio: {result.overall_metrics['sharpe_ratio']:.2f}")
```

## Key Features

- **Temporal Validation**: Respects time ordering - only uses past data to predict future
- **Odds Filtering**: Only uses odds available at prediction time (not future odds)
- **Multiple Markets**: Tests 1x2, over_under, and btts markets
- **Performance Metrics**: ROI, Sharpe ratio, max drawdown, win rate, etc.
- **Period Breakdown**: See performance by time period
- **Market Breakdown**: See performance by market type

## Requirements

- Completed matches with scores in database
- Odds data with timestamps (`created_at` field)
- Minimum training samples (default: 50 per market)

## Output

Results are saved to `backtesting/results/backtest_YYYYMMDD_HHMMSS.json` with:

- Overall metrics
- Performance by market
- Performance by period
- Individual bet records

## Notes

- The framework only places bets on fixtures that have:
  - Completed scores (for evaluation)
  - Odds available at prediction time
  - EV above threshold
- If no bets are placed, check:
  - Odds data availability
  - EV threshold (may be too high)
  - Training data sufficiency
