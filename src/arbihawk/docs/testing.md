# Testing Guide (Fake Money System)

## Overview

The fake money system allows testing bot performance without risking real money.

## Configuration

Edit `config/automation.json` or use the dashboard configuration panel:

```json
{
  "fake_money": {
    "enabled": true,
    "starting_balance": 10000,
    "bet_sizing_strategy": "fixed",
    "fixed_stake": 100,
    "percentage_stake": 0.02,
    "unit_size_percentage": 0.01,
    "auto_bet_after_training": false
  }
}
```

### Configuration Options

- **enabled**: Enable/disable fake money system
- **starting_balance**: Initial balance (default: 10000)
- **bet_sizing_strategy**: Strategy for calculating stake (fixed, percentage, kelly, unit)
- **fixed_stake**: Fixed amount to bet (for fixed strategy)
- **percentage_stake**: Percentage of bankroll to bet (for percentage strategy)
- **unit_size_percentage**: Size of one unit as percentage (for unit strategy)
- **auto_bet_after_training**: Automatically place bets after training completes (default: false)

## Bet Sizing Strategies

### Fixed (Default)

Bet the same amount every time. Safest option.

```python
stake = min(fixed_stake, balance)  # e.g., $100
```

### Percentage

Bet a percentage of current bankroll.

```python
stake = balance * percentage_stake  # e.g., 2%
```

### Kelly Criterion

Optimal bet sizing based on edge and probability. Uses fractional Kelly (1/4) for safety.

```python
# Kelly formula: f* = (bp - q) / b
# Where: b = odds - 1, p = win probability, q = 1 - p
kelly_fraction = (b * p - q) / b * 0.25  # 1/4 Kelly
stake = balance * kelly_fraction
```

### Unit Based

Bet 1-3 units based on confidence level.

```python
unit_size = balance * 0.01  # 1% = 1 unit

if confidence >= 0.65:
    units = 3
elif confidence >= 0.55:
    units = 2
else:
    units = 1

stake = unit_size * units
```

## Using the System

```python
from testing.bankroll import VirtualBankroll

bankroll = VirtualBankroll()

# Place a bet
bet_id = bankroll.place_bet(
    fixture_id="123",
    market_id="1x2",
    market_name="Match Result",
    outcome_id="home",
    outcome_name="Home Win",
    odds=2.10,
    confidence=0.55
)

# Get stats
stats = bankroll.get_stats()
print(f"Balance: ${stats['current_balance']}")
print(f"ROI: {stats['roi']:.2%}")
print(f"Win Rate: {stats['win_rate']:.1%}")
```

## Performance Tracking

The system tracks:

- Current balance and profit
- Total bets placed
- Win/loss count
- ROI (Return on Investment)
- Win rate
- **Per-model performance**: Track performance separately for each model (1x2, over_under, btts)

### Per-Model Tracking

Each bet is tagged with the model market that generated it (`model_market` field). This allows you to:

- View performance breakdown by model in the dashboard
- Identify which models are most profitable
- Compare model performance over time
- Filter bet history by model

## Automated Betting

The system can automatically place bets after training:

1. Enable `auto_bet_after_training` in configuration (via dashboard or config file)
2. When training completes, the system will:
   - Load all active models (1x2, over_under, btts)
   - Find value bets for each model
   - Place bets via VirtualBankroll
   - Track which model generated each bet

### Manual Betting

You can also place bets manually:

- **Dashboard**: Click "Place Bets" button in Automation tab
- **API**: `POST /api/automation/trigger` with `{"mode": "betting"}`
- **Python**: Use `BettingService.place_bets_for_all_models()`

## Dashboard

View performance in the dashboard at <http://localhost:8000>

- **System**: Errors and database statistics
- **Bets**: Bankroll stats, recent bets, per-model performance
- **Betting**: Full bet history table with export
- **Automation**: Control collection, training, betting, and daemon mode
