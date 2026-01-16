# Testing Guide (Fake Money System)

## Overview

The fake money system allows testing bot performance without risking real money.

## Configuration

Edit `config/automation.json`:

```json
{
  "fake_money": {
    "enabled": true,
    "starting_balance": 10000,
    "bet_sizing_strategy": "fixed",
    "fixed_stake": 100,
    "percentage_stake": 0.02,
    "unit_size_percentage": 0.01
  }
}
```

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

## Dashboard

View performance in the dashboard at http://localhost:8000

- **Overview**: Balance, ROI, win rate
- **Betting**: Full bet history with export
