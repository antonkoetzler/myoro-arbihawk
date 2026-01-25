# Stock & Crypto Trading Backlog

## Quick Reference

**Status:** Not Started  
**Timeline:** 4-6 weeks to paper trading, 6-8 weeks to production  
**First Task:** [0. Architecture Extension Design](#0-architecture-extension-design)

**Decision:** Pivot to stocks/crypto now - betting base is solid enough, architecture is 70% reusable.

---

## Architecture Analysis

### What Can Be Shared (No Changes Needed)

1. **`BasePredictor`** - Abstract class, already generic, can extend directly
2. **Database migration system** - Exists, can add new migrations
3. **Scheduler infrastructure** - Generic scheduling, can add new methods
4. **Metrics/backup systems** - Generic, work for both domains
5. **Training pipeline pattern** - Reusable (load data → features → train → save)

### What Needs Extension (Minimal Changes)

1. **`ModelVersionManager`** - Uses `market` field, needs `domain` field added
   - Migration: Add `domain` column to `model_versions` table (default "betting" for existing)
   - Update methods to filter by `domain` + `market/strategy`
   - **Impact**: Low - existing betting code continues to work (defaults to "betting" domain)

### What Needs to Be Separate (New Components)

1. **Database tables** - New tables for stocks/crypto (no refactoring of betting tables)
2. **Feature engineering** - `StockFeatureEngineer` separate from `FeatureEngineer`
3. **Signal engine** - `TradeSignalEngine` separate from `ValueBetEngine`
4. **Services** - `TradingService` separate from `BettingService`
5. **Portfolio management** - `PortfolioManager` separate from `VirtualBankroll` (or extend)
6. **Training script** - `train_trading.py` separate from `train.py` (or unified with domain param)
7. **Scheduler methods** - Add `run_trading_*` methods alongside existing betting methods

### Architecture Decision: Hybrid Approach

**Strategy**: Keep betting system untouched, add trading alongside with minimal shared infrastructure changes.

**Rationale**:

- Zero risk to existing betting system
- Minimal refactoring (only `ModelVersionManager` needs small extension)
- Clear separation of concerns
- Can share: `BasePredictor`, migration system, scheduler infrastructure
- Must separate: Features, signals, services, tables

**Key Extension Point**: `ModelVersionManager` - add `domain` field to support both "betting" and "trading" domains.

---

## Data Sources Research

### Free APIs (Require Free Registration)

**Stocks:**

- **Alpha Vantage** - Free API key (no payment), 5 calls/min, 500/day. Real-time + historical data, 60+ indicators.
- **Marketstack** - Free tier: 100 requests/month. End-of-day data, 30,000+ tickers. Requires free API key.

**Crypto:**

- **CoinGecko API** - No API key required for basic endpoints. 18,936+ coins, real-time prices, historical data. REST JSON endpoints.
- **CoinPaprika API** - Free, no credit card. Real-time prices, volume, market cap. REST + WebSocket.
- **FreeCryptoAPI** - 100,000 requests/month free. Real-time prices, 3,000+ coins, technical analysis (RSI, MACD).

**Verdict:** Use free APIs first (Alpha Vantage for stocks, CoinGecko for crypto). Fallback to scraping if rate limits hit.

### Scraping Targets (If APIs Fail)

**Stocks - Best for Scraping:**

1. **Yahoo Finance** (`finance.yahoo.com`)
   - Popular, consistent structure
   - `yfinance` Python library available (unofficial but widely used)
   - Endpoints: `/quote/{symbol}`, historical data via query params
   - Simple HTML structure, some JSON endpoints available
   - **Note:** May violate ToS, use at own risk

2. **Finviz** (`finviz.com`)
   - Good for fundamental data (P/E, P/B, market cap)
   - Simple HTML tables, easy to parse
   - Unofficial Python wrapper exists (`finviz` package)
   - **Note:** Rate limiting, may block scrapers

3. **TradingView** (`tradingview.com`)
   - Has internal API endpoints (not public)
   - Complex, requires reverse engineering
   - **Not recommended** - too complex

**Crypto - Best for Scraping:**

1. **CoinGecko** (`coingecko.com`)
   - Has public API (prefer API over scraping)
   - If scraping: Simple HTML, some JSON endpoints
   - Popular, consistent

2. **CoinMarketCap** (`coinmarketcap.com`)
   - Popular, but requires API key for official access
   - HTML structure is complex (React-based)
   - **Not recommended** - use their API instead

3. **Binance** (`binance.com`)
   - Has excellent official API (prefer API)
   - If scraping: Complex, requires authentication
   - **Not recommended** - use official API

**Recommendation:** Start with free APIs (Alpha Vantage + CoinGecko). Only scrape if absolutely necessary (rate limits, API failures). Yahoo Finance via `yfinance` is easiest scraping fallback.

---

## Implementation Plan

### Phase 0: Architecture Extension (Day 1)

#### 0. Architecture Extension Design

**Priority:** Critical  
**Effort:** 1 day  
**Status:** Not Started  
**Dependencies:** None

**Tasks:**

- [ ] Design `ModelVersionManager` extension:
  - [ ] Add `domain` field to `model_versions` table (migration)
  - [ ] Default existing rows to `domain='betting'`
  - [ ] Update `save_version()` to accept `domain` parameter (default "betting")
  - [ ] Update `get_active_version()` to accept `domain` parameter
  - [ ] Update `get_all_versions()` to filter by `domain` (optional)
  - [ ] Ensure backward compatibility (existing betting code works unchanged)
- [ ] Design database schema for trading:
  - [ ] New tables: `stocks`, `crypto`, `price_history`, `indicators`, `trades`, `positions`, `portfolio`
  - [ ] No changes to existing betting tables
- [ ] Design component separation:
  - [ ] `StockFeatureEngineer` vs `FeatureEngineer` (separate classes)
  - [ ] `TradeSignalEngine` vs `ValueBetEngine` (separate classes)
  - [ ] `TradingService` vs `BettingService` (separate classes)
  - [ ] `PortfolioManager` vs `VirtualBankroll` (separate class, similar pattern)
- [ ] Design scheduler extension:
  - [ ] Add `run_trading_collection()` method
  - [ ] Add `run_trading_training()` method
  - [ ] Add `run_trading_cycle()` method
  - [ ] Keep existing betting methods unchanged

**Migration Plan:**

```sql
-- Migration 5: Add domain field to model_versions
ALTER TABLE model_versions ADD COLUMN domain TEXT DEFAULT 'betting';
CREATE INDEX IF NOT EXISTS idx_model_versions_domain_market ON model_versions(domain, market);
CREATE INDEX IF NOT EXISTS idx_model_versions_domain_active ON model_versions(domain, market, is_active);
```

**Backward Compatibility:**

- All existing `ModelVersionManager` calls default to `domain='betting'`
- Existing betting code requires zero changes
- New trading code explicitly sets `domain='trading'`

---

### Phase 1: Foundation (Week 1-2)

#### 1.1 ModelVersionManager Extension

**Priority:** Critical  
**Effort:** 0.5 days  
**Status:** Not Started  
**Dependencies:** 0 (Architecture Design)

**Tasks:**

- [ ] Create database migration (Migration 5):
  - [ ] Add `domain` column to `model_versions` table
  - [ ] Set default to 'betting' for existing rows
  - [ ] Add indexes for (domain, market) queries
- [ ] Update `Database.insert_model_version()`:
  - [ ] Add `domain` parameter (default "betting")
  - [ ] Update SQL INSERT to include domain
- [ ] Update `Database.set_active_model()`:
  - [ ] Add `domain` parameter (default "betting")
  - [ ] Update WHERE clause to include domain
- [ ] Update `Database.get_active_model()`:
  - [ ] Add `domain` parameter (default "betting")
  - [ ] Update WHERE clause to include domain
- [ ] Update `Database.get_model_versions()`:
  - [ ] Add `domain` parameter (optional, None = all domains)
  - [ ] Update WHERE clause if domain provided
- [ ] Update `ModelVersionManager`:
  - [ ] Add `domain` parameter to `save_version()` (default "betting")
  - [ ] Add `domain` parameter to `get_active_version()` (default "betting")
  - [ ] Add `domain` parameter to `get_all_versions()` (optional)
  - [ ] Update `rollback_to_version()` to preserve domain
- [ ] Test backward compatibility:
  - [ ] Verify existing betting code works unchanged
  - [ ] Verify existing model versions still accessible
- [ ] Update `train.py` to pass `domain='betting'` explicitly (for clarity)

---

#### 1.2 Database Schema Extension

**Priority:** Critical  
**Effort:** 2-3 days  
**Status:** Not Started  
**Dependencies:** 1.1 (ModelVersionManager Extension)

**Tasks:**

- [ ] Add migration system for stock/crypto tables
- [ ] Create `stocks` table (symbol, name, sector, market_cap, exchange)
- [ ] Create `crypto` table (symbol, name, market_cap)
- [ ] Create `price_history` table (unified for stocks/crypto)
- [ ] Create `indicators` table (technical indicators)
- [ ] Create `trades` table (executed orders)
- [ ] Create `positions` table (active holdings)
- [ ] Create `portfolio` table (account balance snapshots)
- [ ] Add indexes for performance (symbol, timestamp, asset_type)
- [ ] Test schema with sample data

**Schema:**

```sql
-- See full schema in original backlog
```

---

#### 1.3 Data Collection Layer

**Priority:** Critical  
**Effort:** 3-4 days  
**Dependencies:** 1.2 (Database schema)

**Tasks:**

- [ ] Research and test Alpha Vantage API (stocks)
- [ ] Research and test CoinGecko API (crypto)
- [ ] Create `data/stock_ingestion.py`:
  - [ ] `fetch_price_history(symbol, period)` - Alpha Vantage
  - [ ] `fetch_fundamental_data(symbol)` - Alpha Vantage or Finviz scraping
  - [ ] `ingest_to_database(symbol, data)`
- [ ] Create `data/crypto_ingestion.py`:
  - [ ] `fetch_price_history(symbol, period)` - CoinGecko
  - [ ] `fetch_market_data(symbol)` - CoinGecko
  - [ ] `ingest_to_database(symbol, data)`
- [ ] Create unified `DataIngestionService` wrapper
- [ ] Add data validation (missing data, outliers)
- [ ] Add error handling and retry logic
- [ ] Add rate limiting (respect API limits)

**Fallback (If APIs Fail):**

- [ ] Implement Yahoo Finance scraping via `yfinance` library
- [ ] Implement CoinGecko HTML scraping (if API fails)

**APIs to Use:**

- **Stocks**: Alpha Vantage (free API key) → Fallback: Yahoo Finance scraping
- **Crypto**: CoinGecko (no API key needed) → Fallback: CoinGecko HTML scraping

---

#### 1.4 Feature Engineering

**Priority:** Critical  
**Effort:** 3-4 days  
**Dependencies:** 1.2 (Database), 1.3 (Data collection)

**Tasks:**

- [ ] Create `data/stock_features.py` (similar to `features.py`)
- [ ] Implement technical indicators (vectorized):
  - [ ] RSI (Relative Strength Index) - 14 period default
  - [ ] MACD (12, 26, 9) + signal + histogram
  - [ ] Moving Averages: SMA 20, 50, 200
  - [ ] Bollinger Bands (20 period, 2 std dev)
  - [ ] ATR (Average True Range) - 14 period
  - [ ] Volume SMA (20 period)
- [ ] Implement momentum features:
  - [ ] Price change: 1d, 5d, 20d, 60d
  - [ ] Volume change: 1d, 5d, 20d
  - [ ] Volatility: rolling std dev (20d)
  - [ ] Relative strength vs. market index
- [ ] Implement fundamental features (stocks only):
  - [ ] P/E ratio, P/B ratio
  - [ ] Market cap (log scale)
  - [ ] Sector/industry encoding
- [ ] Create `create_training_data()` function (vectorized, like betting)
- [ ] Cache indicator calculations (avoid recomputation)
- [ ] Test feature generation on sample data

**Feature Categories:**

1. Technical Indicators (RSI, MACD, MA, Bollinger, ATR)
2. Momentum Features (price/volume changes, volatility)
3. Fundamental Features (P/E, P/B, market cap, sector)

---

### Phase 2: Model Development (Week 2-3)

#### 2.1 Base Prediction Models

**Priority:** High  
**Effort:** 2-3 days  
**Dependencies:** 1.4 (Features)

**Tasks:**

- [ ] Extend `BasePredictor` for stock/crypto (reuse from betting)
- [ ] Create `StockPredictor` class:
  - [ ] Inherit from `BasePredictor`
  - [ ] Implement `train(features, labels)`
  - [ ] Implement `predict_probabilities(features)`
  - [ ] Support classification (direction) and regression (magnitude)
- [ ] Create `CryptoPredictor` class (similar to StockPredictor)
- [ ] Implement prediction targets:
  - [ ] Direction: up/down in next N days (classification)
  - [ ] Magnitude: price change % (regression)
  - [ ] Volatility: significant move prediction (classification)
- [ ] Reuse XGBoost training pipeline
- [ ] Add model versioning (reuse existing `ModelVersionManager`)
- [ ] Test training on sample data

**Prediction Targets:**

- **Direction**: Will price go up or down in next 5 days? (classification)
- **Magnitude**: How much will price change? (regression, optional)
- **Volatility**: Will there be a >5% move? (classification, optional)

---

#### 2.2 Strategy-Specific Models

**Priority:** High  
**Effort:** 3-4 days  
**Dependencies:** 2.1 (Base models)

**Tasks:**

- [ ] **Momentum Model**:
  - [ ] Train on momentum features (price change, volume, RSI)
  - [ ] Predict: momentum continuation vs. reversal
  - [ ] Target: 5-20 day holding period
- [ ] **Swing Trading Model**:
  - [ ] Train on technical indicators (RSI, MACD, MA, Bollinger)
  - [ ] Predict: price direction (up/down)
  - [ ] Target: 2 days to 2 weeks holding period
- [ ] **Pairs Trading Model** (later phase):
  - [ ] Train on price ratio/spread features
  - [ ] Predict: mean reversion probability
- [ ] **Value Investing Model** (later phase):
  - [ ] Train on fundamental features
  - [ ] Predict: quality score + return prediction
- [ ] **Volatility Breakout Model** (crypto):
  - [ ] Train on volatility features (Bollinger width, ATR)
  - [ ] Predict: breakout probability and direction

**Model Architecture:**

- Reuse `BettingPredictor` pattern
- Each strategy = separate model (easier to manage)
- Train on strategy-specific feature subsets

**Priority Order:**

1. Momentum Model (easiest, most similar to betting)
2. Swing Trading Model (uses technical indicators)
3. Volatility Breakout (crypto-specific)
4. Pairs Trading (more complex)
5. Value Investing (requires fundamental data)

---

### Phase 3: Trading Engine (Week 3-4)

#### 3.1 Trade Signal Engine

**Priority:** Critical  
**Effort:** 3-4 days  
**Dependencies:** 2.2 (Models trained)

**Tasks:**

- [ ] Create `engine/trade_signal.py` (similar to `value_bet.py`)
- [ ] Implement `TradeSignalEngine` class:
  - [ ] `find_momentum_signals(symbols, lookback_days=20)`
  - [ ] `find_swing_signals(symbols, timeframe='1d')`
  - [ ] `calculate_ev(probability, expected_return, risk)` - Expected Value
  - [ ] `calculate_risk_reward(entry, stop_loss, take_profit)` - Risk/Reward ratio
- [ ] Strategy-specific signal logic:
  - [ ] Momentum: Top performers + ML confirmation + volume
  - [ ] Swing: Technical confluence + ML direction prediction
  - [ ] Volatility: Bollinger squeeze + ML breakout prediction
- [ ] Filter signals by:
  - [ ] Minimum confidence threshold (0.6+)
  - [ ] Minimum risk-reward ratio (1:2+)
  - [ ] Maximum positions per strategy
- [ ] Return signal DataFrame (symbol, strategy, confidence, entry, stop_loss, take_profit)

---

#### 3.2 Position Management

**Priority:** Critical  
**Effort:** 2-3 days  
**Dependencies:** 3.1 (Signal engine)

**Tasks:**

- [ ] Create `trading/portfolio_manager.py` (similar to `VirtualBankroll`)
- [ ] Implement `PortfolioManager` class:
  - [ ] Track cash balance
  - [ ] Track active positions
  - [ ] Calculate portfolio value (cash + positions)
  - [ ] Calculate P&L (realized + unrealized)
- [ ] Implement position sizing:
  - [ ] Fixed: $X per trade
  - [ ] Percentage: X% of portfolio
  - [ ] Risk-based: Size based on stop-loss (1-2% risk per trade)
  - [ ] Kelly Criterion (optional, advanced)
- [ ] Implement position tracking:
  - [ ] Open position (entry)
  - [ ] Update position (price updates)
  - [ ] Close position (exit)
- [ ] Implement stop-loss and take-profit logic:
  - [ ] Check positions daily for stop-loss/take-profit hits
  - [ ] Auto-close positions when thresholds hit
- [ ] Portfolio rules:
  - [ ] Max positions (10-15)
  - [ ] Max position size (5% of portfolio)
  - [ ] Cash reserve (10-20%)

---

#### 3.3 Order Execution (Paper Trading)

**Priority:** High  
**Effort:** 4-5 days  
**Dependencies:** 3.2 (Portfolio manager)

**Tasks:**

- [ ] Create `trading/execution.py`
- [ ] Implement `PaperTradingExecutor` class:
  - [ ] `execute_market_order(symbol, quantity, price)` - Immediate fill
  - [ ] `execute_limit_order(symbol, quantity, price)` - Fill if price reached
  - [ ] `execute_stop_loss_order(symbol, quantity, price)` - Fill if price drops
  - [ ] `execute_take_profit_order(symbol, quantity, price)` - Fill if price rises
- [ ] Simulate realistic execution:
  - [ ] Slippage: 0.1-0.5% for market orders
  - [ ] Fill delays: 1-5 seconds
  - [ ] Partial fills (for large orders)
- [ ] Order tracking:
  - [ ] Pending orders (limit, stop-loss, take-profit)
  - [ ] Filled orders (record in `trades` table)
  - [ ] Cancelled orders
- [ ] Integration with PortfolioManager:
  - [ ] Update cash on buy
  - [ ] Update cash on sell
  - [ ] Update positions on fill
- [ ] Error handling:
  - [ ] Insufficient funds
  - [ ] Invalid orders
  - [ ] Market closed (for stocks)

---

### Phase 4: Automation & Integration (Week 4-5)

#### 4.1 Scheduler Integration

**Priority:** High  
**Effort:** 2-3 days  
**Dependencies:** 1.2 (Data collection), 2.2 (Models), 3.3 (Execution)

**Tasks:**

- [ ] Extend `AutomationScheduler` for stock/crypto:
  - [ ] `run_stock_collection()` - Fetch stock data (daily)
  - [ ] `run_crypto_collection()` - Fetch crypto data (hourly/daily)
  - [ ] `run_trading_training()` - Train stock/crypto models (weekly)
  - [ ] `run_trading_cycle()` - Generate signals + execute trades (daily)
- [ ] Add scheduling:
  - [ ] Stock data: Daily at market close (4 PM EST)
  - [ ] Crypto data: Every 6 hours (24/7 market)
  - [ ] Model training: Weekly (Sunday night)
  - [ ] Trading cycle: Daily (9:30 AM EST for stocks, anytime for crypto)
- [ ] Add configuration:
  - [ ] `config/trading.json` - Trading-specific config
  - [ ] Symbols to track (stocks + crypto)
  - [ ] Strategies to enable
  - [ ] Position sizing strategy
- [ ] Add logging and monitoring (reuse existing system)

---

#### 4.2 Dashboard Extension

**Priority:** Medium  
**Effort:** 3-4 days  
**Dependencies:** 3.3 (Execution), 4.1 (Scheduler)

**Tasks:**

- [ ] Add "Trading" tab to dashboard frontend
- [ ] Display active positions:
  - [ ] Symbol, quantity, entry price, current price, P&L
  - [ ] Strategy, stop-loss, take-profit
- [ ] Display portfolio overview:
  - [ ] Cash balance, total value, P&L
  - [ ] Portfolio value chart (over time)
- [ ] Display trade history:
  - [ ] Table of all trades (buy/sell)
  - [ ] Filter by strategy, symbol, date
- [ ] Display strategy performance:
  - [ ] Performance by strategy (ROI, win rate, Sharpe ratio)
  - [ ] Performance charts
- [ ] Add price charts:
  - [ ] Stock/crypto price chart (candlestick)
  - [ ] Technical indicators overlay (RSI, MACD, MA)
- [ ] Add signal display:
  - [ ] Current signals (before execution)
  - [ ] Signal confidence, risk-reward

---

### Phase 5: Real Broker Integration (Optional)

#### 5.1 Broker APIs

**Priority:** Low (after paper trading success)  
**Effort:** 5-7 days  
**Dependencies:** 3.3 (Paper trading working), 4.1 (Scheduler)

**Tasks:**

- [ ] Research broker APIs:
  - [ ] **Stocks**: Alpaca (free, paper trading, good API)
  - [ ] **Crypto**: Binance (free, excellent API, paper trading)
- [ ] Implement broker connection layer:
  - [ ] Abstract interface (`BrokerInterface`)
  - [ ] Alpaca implementation (`AlpacaBroker`)
  - [ ] Binance implementation (`BinanceBroker`)
- [ ] Implement real order execution:
  - [ ] Replace `PaperTradingExecutor` with real broker calls
  - [ ] Handle authentication (API keys)
  - [ ] Handle order status updates
- [ ] Add security:
  - [ ] Store API keys securely (environment variables)
  - [ ] Add order validation (prevent accidental large orders)
  - [ ] Add kill switch (emergency stop)
- [ ] Test with paper trading accounts first

---

## Strategy Details

### Strategy 1: Momentum Trading

**Concept:** Find assets with strong recent performance, predict continuation.

**Features:**

- Price change: 5d, 20d, 60d
- Volume trends
- RSI momentum
- Relative strength vs. market

**Entry:**

- Top 10-20% performers (momentum)
- ML predicts continuation (confidence > 0.6)
- Volume confirmation
- Risk-reward > 1:2

**Exit:**

- ML predicts reversal
- Stop-loss: 5-10%
- Take-profit: 10-20%
- Momentum weakens

---

### Strategy 2: Swing Trading (Technical Indicators)

**Concept:** Use technical analysis + ML to predict price direction.

**Features:**

- RSI, MACD, Moving Averages, Bollinger Bands, Volume

**Entry:**

- RSI oversold in uptrend → buy
- MACD bullish crossover
- Price touches support (MA)
- ML confirms direction (confidence > 0.65)

**Exit:**

- RSI overbought
- MACD bearish crossover
- Stop-loss: 5-10%
- Take-profit: 10-20%

---

### Strategy 3: Pairs Trading

**Concept:** Find correlated assets, trade when relationship diverges.

**Features:**

- Price ratio/spread
- Correlation coefficient
- Z-score of divergence

**Entry:**

- Divergence > 2 std dev
- ML predicts reversion (confidence > 0.7)
- Historical correlation > 0.7

**Exit:**

- Relationship reverts to mean
- Stop-loss on continued divergence

---

### Strategy 4: Value Investing with ML

**Concept:** Find undervalued stocks using fundamentals + ML.

**Features:**

- P/E, P/B, Market cap, Sector, Earnings growth, ROE, ROA

**Entry:**

- Low P/E, P/B (undervalued)
- ML predicts quality (confidence > 0.7)
- ML predicts 15%+ returns (confidence > 0.6)

**Exit:**

- Target return achieved (15-30%)
- ML predicts overvaluation
- Time-based (6-12 months)

---

### Strategy 5: Crypto Volatility Breakout

**Concept:** Identify low-volatility periods, predict breakouts.

**Features:**

- Bollinger Band width, ATR, Volume patterns, Historical volatility

**Entry:**

- Low volatility (Bollinger squeeze)
- ML predicts breakout (confidence > 0.65)
- Volume increase on breakout

**Exit:**

- Target move: 10-30%
- Stop-loss: 5-8%
- Volatility expansion complete

---

## Risk Management

### Position Sizing

- **Default**: Risk 1-2% of portfolio per trade
- **Maximum**: 5% of portfolio per position
- **Diversification**: Max 10-15 positions

### Stop-Loss Rules

- Momentum/Swing: 5-10%
- Pairs: Stop if divergence continues
- Value: 15-20% (longer-term)
- Volatility: 5-8%

### Take-Profit Rules

- Momentum/Swing: 10-20%
- Pairs: Revert to mean
- Value: 15-30%
- Volatility: 10-30%

### Portfolio Rules

- Cash Reserve: 10-20%
- Sector Diversification: Don't over-concentrate
- Max Drawdown: Stop trading if down 20%

---

## Success Metrics

### Paper Trading Phase

- Sharpe Ratio: > 1.0
- Win Rate: > 50%
- Profit Factor: > 1.5
- Max Drawdown: < 15%
- Monthly Returns: Consistent positive

### Real Trading Phase

- Same as paper trading
- Plus: Real execution slippage tracking
- Plus: Broker fee impact

---

## Timeline

### Minimum Viable (Paper Trading)

- Phase 1: 1-2 weeks (Foundation)
- Phase 2: 1 week (Models)
- Phase 3: 1-2 weeks (Trading Engine)
- Phase 4: 1 week (Automation)
- **Total: 4-6 weeks**

### Full Production (Real Broker)

- Add Phase 5: 1-2 weeks (Broker Integration)
- **Total: 6-8 weeks**

---

## Next Steps

**Start with: [0. Architecture Extension Design](#0-architecture-extension-design)**

**Why this first?**

- Need to design the extension points before building
- `ModelVersionManager` extension is the only shared component that needs changes
- Once designed, can proceed with database schema and other components
- Ensures backward compatibility is maintained

**Then:**

1. **[1.1 ModelVersionManager Extension](#11-modelversionmanager-extension)** - Add domain support (0.5 days)
2. **[1.2 Database Schema Extension](#12-database-schema-extension)** - Create trading tables (2-3 days)
3. **[1.3 Data Collection Layer](#13-data-collection-layer)** - Set up Alpha Vantage + CoinGecko (3-4 days)
4. **[1.4 Feature Engineering](#14-feature-engineering)** - Technical indicators (3-4 days)

**Recommendation:** Focus on **Momentum** and **Swing Trading** first (most similar to betting, easiest to implement).
