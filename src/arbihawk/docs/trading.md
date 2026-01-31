# Stock/Crypto Trading System

Automated trading system for stocks and cryptocurrency using ML-driven signal generation and paper trading execution.

**📖 New to trading? Start with the [Usage Guide](trading-usage.md)**

**Domain:** Trading (Stocks & Crypto)

## Overview

The trading system provides:

- **Feature Engineering**: Technical indicators (RSI, MACD, Bollinger Bands, ATR) and strategy-specific features
- **ML Models**: XGBoost classifiers for momentum, swing, and volatility breakout strategies  
- **Signal Generation**: Identifies trading opportunities with stop-loss/take-profit levels
- **Portfolio Management**: Position sizing, P&L tracking, cash management
- **Paper Trading**: Simulated execution with slippage and order types
- **Dashboard Integration**: Real-time monitoring and control

## Architecture

```markdown
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
      "stocks": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "JNJ"],
      "crypto": ["BTC", "ETH", "BNB", "SOL", "ADA"]
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
    },
    "rate_limiting": {
      "coingecko_calls_per_min": 10
    },
    "scraping_fallback": {
      "enabled": true
    }
  }
}
```

**Note:** Crypto symbols use CoinGecko format (e.g., "BTC" not "BTC-USD"). Stock symbols use standard ticker format.

## Usage

**📖 For step-by-step instructions, see [Trading Usage Guide](trading-usage.md)**

**Quick Start:**

1. Enable trading in `config/config.json`
2. Start dashboard: VS Code task **Dashboard Backend: Start Server** (`Ctrl+Shift+P` → "Tasks: Run Task")
3. Initialize portfolio: Dashboard → Automation → Trading → "Initialize Portfolio"
4. Start daemon: Dashboard → Automation → Trading → "Start Daemon"
5. Leave it running - system handles everything automatically

**Available VS Code Tasks:**
- **Trading: Collect Data** - Fetch latest prices
- **Trading: Train Models** - Train strategy models
- **Trading: Run Trading Cycle** - Execute one cycle
- **Trading: Initialize Portfolio** - Set up portfolio
- **Trading: Check Portfolio Status** - View performance

See [Tasks Guide](tasks.md) for complete task list.

### Dashboard Features

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

**Note:** Most operations are available via dashboard UI or VS Code tasks. API endpoints are for advanced users or automation.

```bash
POST /api/trading/collect       - Trigger data collection (or use task "Trading: Collect Data")
POST /api/trading/train         - Train trading models (or use task "Trading: Train Models")
POST /api/trading/cycle         - Run trading cycle (or use task "Trading: Run Trading Cycle")
POST /api/trading/full          - Run full cycle (or use dashboard "Full Run" button)
POST /api/trading/daemon/start  - Start daemon mode (or use dashboard "Start Daemon" button)
POST /api/trading/daemon/stop   - Stop daemon mode (or use dashboard "Stop Daemon" button)
GET  /api/trading/status        - Get trading status
GET  /api/trading/portfolio     - Get portfolio status (or use task "Trading: Check Portfolio Status")
GET  /api/trading/positions     - Get open positions
GET  /api/trading/trades        - Get trade history
GET  /api/trading/signals       - Get current signals
GET  /api/trading/performance   - Get performance metrics
GET  /api/trading/models        - Get model status
POST /api/trading/positions/close   - Close a position (or use dashboard)
POST /api/trading/portfolio/initialize  - Initialize portfolio (or use dashboard/task)
```

## Position Sizing Strategies

### Risk-Based (Recommended)

Calculates position size based on stop-loss distance to risk a fixed percentage per trade.

```markdown
Risk Amount = Portfolio Value × Risk Per Trade
Max Shares = Risk Amount / (Entry Price - Stop Loss)
Position Value = Min(Max Shares × Price, Max Position Size, Available Cash)
```

### Fixed

Fixed dollar amount per trade regardless of stop-loss distance.

### Percentage

Fixed percentage of portfolio per trade.

## Feature Engineering

The trading system extracts **technical indicators and strategy-specific features** for each asset:

**Base Technical Indicators (16 features):**
- **RSI** (Relative Strength Index): Momentum oscillator (14-period default)
- **MACD**: Moving Average Convergence Divergence (12, 26, 9) + signal + histogram
- **Moving Averages**: SMA 20, 50, 200; EMA 12, 26
- **Bollinger Bands**: Upper, middle, lower bands + width (20-period, 2 std dev)
- **ATR** (Average True Range): Volatility measure (14-period) + normalized
- **Volume**: Volume SMA (20-period) + volume ratio

**Momentum Strategy Features (13 additional features):**
- Price returns: 1d, 5d, 20d, 60d
- Volume changes: 1d, 5d, 20d
- Volatility: 20-day rolling standard deviation
- RSI momentum: 5-day change
- Price vs. moving averages: Distance to SMA20, SMA50
- Momentum score: Composite momentum indicator

**Swing Trading Features (14 additional features):**
- RSI conditions: Oversold, overbought, neutral
- MACD signals: Bullish/bearish cross, above/below signal
- Price position: Above/below SMA20, SMA50, SMA200
- Distance to moving averages
- Bollinger Band position: Near upper/lower bands
- Volume conditions: High/low volume
- Trend indicators: Uptrend, downtrend

**Volatility Breakout Features (8 additional features):**
- Bollinger Band width percentile
- Bollinger squeeze detection
- ATR percentile
- Low volatility detection
- Historical volatility
- Volume surge detection
- Breakout bias: Up/down direction

**Total Features by Strategy:**
- **Momentum**: 29 features (16 base + 13 momentum)
- **Swing**: 30 features (16 base + 14 swing)
- **Volatility**: 37 features (16 base + 13 momentum + 8 volatility)

## Training Models

Models are automatically trained during the trading cycle. They can also be trained manually:

**Via Dashboard:**
- Automation tab → Trading group → "Actions" → "Train Models"

**Via VS Code Task:**
- **Trading: Train Models** (`Ctrl+Shift+P` → "Tasks: Run Task")

Training creates versioned models in `models/saved/trading/`.

**Model Training Details:**
- **Algorithm**: XGBoost classifier
- **Prediction Target**: Direction (up/down) for next N days (strategy-specific horizon)
- **Cross-validation**: Temporal split (training data always before test data)
- **Hyperparameter Tuning**: Optional, optimizes for Sharpe ratio (configurable)
- **Model Versioning**: Automatic versioning with performance tracking

**Hyperparameter Tuning** (optional):
- Uses Optuna for automated hyperparameter optimization
- Optimizes for Sharpe ratio (risk-adjusted returns)
- Temporal cross-validation (ensures training data is always before test data)
- Configurable search space (small/medium/large)
- Early stopping if no improvement
- Parallel execution support
- Default: **Disabled** (enable in `config/automation.json`)

**Configuration** (`config/automation.json` → `trading_hyperparameter_tuning`):
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
- **Small search space**: ~30-45 minutes per strategy (15 trials × 2-3 min/trial)
- **With parallelization (n_jobs=4)**: ~8-12 minutes per strategy
- **Medium search space**: ~60-90 minutes per strategy (30 trials)
- **Large search space**: ~120-180 minutes per strategy (60 trials)

**Recommendation:** Enable tuning when you have 10,000+ training samples per strategy for best results.

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

**Optional but recommended** - API keys improve data collection reliability:

- **Alpha Vantage**: Stock data (free tier: 25 calls/day)
  - Without key: Falls back to yfinance (Yahoo Finance scraping)
- **CoinGecko**: Crypto data (free tier: 10-30 calls/minute, no key required)
  - Works without API key, but rate limits are stricter

**Note:** The system works without API keys using fallback methods (yfinance for stocks, CoinGecko free tier for crypto).

## File Structure

Key files for the trading system (for reference - no code editing needed):

```markdown
src/arbihawk/
├── data/
│   ├── stock_features.py      # Feature engineering
│   ├── stock_ingestion.py     # Data collection
│   └── crypto_ingestion.py   # Crypto data collection
├── models/
│   ├── trading_predictor.py   # ML model class
│   └── saved/                # Trained models (momentum, swing, volatility)
├── engine/
│   └── trade_signal.py        # Signal generation
├── trading/
│   ├── portfolio_manager.py   # Portfolio management
│   ├── execution.py           # Paper trading
│   └── service.py             # Orchestration
└── docs/
    ├── trading.md             # This file (technical reference)
    └── trading-usage.md       # Usage guide
```

**Note:** All operations can be performed via dashboard UI or VS Code tasks - no code editing required.

## Limitations

- **Paper Trading Only**: No live execution
- **Data Delays**: Free API tiers have rate limits
- **No Fundamental Analysis**: Pure technical/ML approach
- **Market Hours**: No after-hours trading simulation
