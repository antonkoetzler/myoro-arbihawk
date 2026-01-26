# Stock/Crypto Trading System

Automated trading system for stocks and cryptocurrency using ML-driven signal generation and paper trading execution.

**📖 New to trading? Start with the [Usage Guide](trading-usage.md)**

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

## Training Models

Models are automatically trained during the trading cycle. They can also be trained manually:

**Via Dashboard:**
- Automation tab → Trading group → "Actions" → "Train Models"

**Via VS Code Task:**
- **Trading: Train Models** (`Ctrl+Shift+P` → "Tasks: Run Task")

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

**Optional but recommended** - API keys improve data collection reliability:

- **Alpha Vantage**: Stock data (free tier: 25 calls/day)
  - Without key: Falls back to yfinance (Yahoo Finance scraping)
- **CoinGecko**: Crypto data (free tier: 10-30 calls/minute, no key required)
  - Works without API key, but rate limits are stricter

**Note:** The system works without API keys using fallback methods (yfinance for stocks, CoinGecko free tier for crypto).

## File Structure

Key files for the trading system (for reference - no code editing needed):

```markdown
arbihawk/
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
