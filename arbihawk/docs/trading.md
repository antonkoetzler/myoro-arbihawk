# Stock/Crypto Trading System

Automated trading system for stocks and cryptocurrency using ML-driven signal generation and paper trading execution.

## Overview

The trading system provides:
- **Feature Engineering**: Technical indicators (RSI, MACD, Bollinger Bands, ATR) and strategy-specific features
- **ML Models**: XGBoost classifiers for momentum, swing, and volatility breakout strategies  
- **Signal Generation**: Identifies trading opportunities with stop-loss/take-profit levels
- **Portfolio Management**: Position sizing, P&L tracking, cash management
- **Paper Trading**: Simulated execution with slippage and order types
- **Dashboard Integration**: Real-time monitoring and control

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Data Ingestion │───▶│ Feature Engineer│───▶│   ML Predictor  │
│  (stock_ingestion)   │ (stock_features)│    │(trading_predictor)
└─────────────────┘    └─────────────────┘    └────────┬────────┘
                                                       │
                       ┌─────────────────┐             │
                       │  Signal Engine  │◀────────────┘
                       │  (trade_signal) │
                       └────────┬────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│Portfolio Manager│    │ Paper Executor  │    │Trading Service  │
│(portfolio_manager)   │   (execution)   │    │   (service)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Strategies

### 1. Momentum Strategy
Identifies assets with strong directional movement.

**Entry Criteria:**
- Strong price momentum (20-day return)
- RSI not in extreme territory (30-70)
- MACD confirming trend direction
- ML confidence > 60%

**Position Management:**
- ATR-based stop-loss (2x ATR)
- 2:1 minimum risk/reward ratio

### 2. Swing Strategy
Captures reversals at support/resistance levels.

**Entry Criteria:**
- RSI oversold (<30) in uptrend OR RSI overbought (>70) in downtrend
- MACD bullish/bearish crossover
- Price at MA support/resistance
- ML confidence > 65%

**Position Management:**
- Tighter stops at swing points
- 2:1 minimum risk/reward ratio

### 3. Volatility Breakout (Crypto)
Trades breakouts from Bollinger Band squeezes.

**Entry Criteria:**
- Bollinger Band squeeze (low volatility period)
- Volume surge on breakout
- Price breaks upper/lower band
- ML confidence > 65%

**Position Management:**
- Wider stops for volatility
- 2:1 minimum risk/reward ratio

## Configuration

Edit `config/config.json`:

```json
{
  "trading": {
    "enabled": true,
    "watchlist": {
      "stocks": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
      "crypto": ["BTC-USD", "ETH-USD"]
    },
    "strategies": {
      "momentum": {
        "min_confidence": 0.6,
        "min_risk_reward": 2.0
      },
      "swing": {
        "min_confidence": 0.65,
        "min_risk_reward": 2.0
      },
      "volatility": {
        "min_confidence": 0.65,
        "min_risk_reward": 2.0
      }
    },
    "position_sizing": {
      "strategy": "risk_based",
      "risk_per_trade": 0.02,
      "max_position_size": 0.05,
      "max_positions": 12
    },
    "portfolio": {
      "starting_balance": 10000.0,
      "cash_reserve": 0.15
    }
  }
}
```

## Usage

### VSCode Tasks

Run from Command Palette (`Ctrl+Shift+P` > "Tasks: Run Task"):

- **Trading: Collect Data** - Fetch latest price data
- **Trading: Train Models** - Train ML models for all strategies
- **Trading: Run Trading Cycle** - Execute one trading cycle
- **Trading: Initialize Portfolio** - Set up portfolio with starting balance
- **Trading: Check Portfolio Status** - View current performance

### Dashboard

The Trading tab in the dashboard provides:

1. **Portfolio Overview**
   - Total value, cash balance, P&L
   - ROI, win rate, Sharpe ratio

2. **Active Positions**
   - Current holdings with unrealized P&L
   - Manual close functionality

3. **Current Signals**
   - Real-time trading opportunities
   - Confidence, risk/reward, expected value

4. **Trade History**
   - Completed trades with P&L
   - Performance by strategy

5. **Model Status**
   - Training status per strategy
   - Last update timestamps

### API Endpoints

```
POST /api/trading/train         - Train trading models
POST /api/trading/cycle         - Run trading cycle
GET  /api/trading/portfolio     - Get portfolio status
GET  /api/trading/positions     - Get open positions
GET  /api/trading/trades        - Get trade history
GET  /api/trading/signals       - Get current signals
GET  /api/trading/performance   - Get performance metrics
GET  /api/trading/models        - Get model status
POST /api/trading/positions/close   - Close a position
POST /api/trading/portfolio/initialize  - Initialize portfolio
```

## Position Sizing Strategies

### Risk-Based (Recommended)
Calculates position size based on stop-loss distance to risk a fixed percentage per trade.

```
Risk Amount = Portfolio Value × Risk Per Trade
Max Shares = Risk Amount / (Entry Price - Stop Loss)
Position Value = Min(Max Shares × Price, Max Position Size, Available Cash)
```

### Fixed
Fixed dollar amount per trade regardless of stop-loss distance.

### Percentage
Fixed percentage of portfolio per trade.

## Training Models

Models are trained on historical price data with forward-looking labels:

```python
# Example training
from train_trading import train_trading_models

train_trading_models(
    min_samples=200,
    test_size=0.2,
    save_models=True
)
```

Training creates versioned models in `models/saved/trading/`.

## Performance Metrics

- **ROI**: Return on investment since inception
- **Win Rate**: Percentage of profitable trades
- **Sharpe Ratio**: Risk-adjusted return
- **Max Drawdown**: Largest peak-to-trough decline
- **Profit Factor**: Gross profits / Gross losses

## Risk Management

The system enforces:
- Maximum 12 concurrent positions
- Maximum 5% portfolio in single position
- 15% cash reserve
- 2% maximum risk per trade
- Stop-loss on every position

## API Keys

Required API keys in `config/config.json`:
- **Alpha Vantage**: Stock data (free tier: 25 calls/day)
- **CoinGecko**: Crypto data (free tier: 30 calls/minute)

## Files

```
arbihawk/
├── data/
│   ├── stock_features.py      # Feature engineering
│   └── stock_ingestion.py     # Data collection
├── models/
│   ├── trading_predictor.py   # ML model class
│   └── saved/trading/         # Trained models
├── engine/
│   └── trade_signal.py        # Signal generation
├── trading/
│   ├── portfolio_manager.py   # Portfolio management
│   ├── execution.py           # Paper trading
│   └── service.py             # Orchestration
├── train_trading.py           # Training script
└── docs/trading.md            # This file
```

## Limitations

- **Paper Trading Only**: No live execution
- **Data Delays**: Free API tiers have rate limits
- **No Fundamental Analysis**: Pure technical/ML approach
- **Market Hours**: No after-hours trading simulation
