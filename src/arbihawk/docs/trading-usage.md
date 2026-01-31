# Trading System - Usage Guide

Step-by-step guide for using the automated trading system.

## Quick Start

### 1. Initial Setup

**Enable trading:**

1. Edit `config/config.json`
2. Set `trading.enabled` to `true`
3. Configure your watchlist:
   - **Stocks**: Use standard ticker symbols (e.g., "AAPL", "MSFT")
   - **Crypto**: Use CoinGecko format (e.g., "BTC", "ETH", not "BTC-USD")

**Initialize portfolio:**

1. Open dashboard → Automation tab → Trading group
2. Click "Actions" → "Initialize Portfolio"
3. Portfolio starts with $10,000 (configurable)

### 2. Test the System (Recommended First Step)

**Before leaving it in daemon mode, test with a manual run:**

1. **Start the backend server:**
   - VS Code task: **Dashboard Backend: Start Server** (`Ctrl+Shift+P` → "Tasks: Run Task")

2. **Open dashboard:**
   - Navigate to `http://localhost:8000`
   - Go to **Automation** tab
   - Switch to **Trading** group (top right)

3. **Run a test cycle:**
   - Click **"Actions"** → **"Full Run"**
   - Watch the logs to ensure everything works
   - Verify: Data collected, models trained, signals found

4. **Check results:**
   - Go to **Trading** tab
   - Verify portfolio initialized
   - Check if any positions were opened
   - Review logs for errors

**If everything looks good, proceed to daemon mode.**

### 3. Start Automated Trading (Daemon Mode)

**Once tested, start daemon for continuous operation:**

1. **In dashboard (Automation tab → Trading group):**
   - Click **"Actions"** → **"Start Daemon"**
   - Leave it running - it handles everything automatically

**That's it!** The system will now:

- Collect fresh data every hour
- Retrain models with new data
- Find trading opportunities
- Execute trades automatically
- Manage positions (stop-loss/take-profit)

### 4. Monitor Performance

**Check dashboard regularly:**

- **Trading tab**: Portfolio value, P&L, active positions
- **Automation tab → Logs**: See what's happening in real-time
- **Automation tab → Status**: Check if daemon is running

**Key metrics to watch:**

- Portfolio value (should grow over time if profitable)
- Win rate (percentage of profitable trades)
- Total P&L (realized + unrealized)
- Number of open positions

## How Daemon Mode Works

**Each cycle (default: 1 hour):**

1. **Data Collection** (~30 seconds)
   - Fetches latest prices for all watchlist symbols
   - Stocks: Uses Alpha Vantage API (with yfinance fallback)
   - Crypto: Uses CoinGecko API

2. **Model Training** (~10 seconds)
   - Retrains all 3 strategy models (momentum, swing, volatility)
   - Uses fresh data to improve predictions
   - Saves updated models to disk

3. **Trading Cycle** (~5 seconds)
   - Updates existing positions with current prices
   - Checks stop-loss/take-profit levels (closes if hit)
   - Finds new trading signals from all strategies
   - Executes top 3 signals (opens new positions)

## Manual Operations

### One-Time Full Run

If you want to run a single cycle manually:

1. Dashboard → Automation tab → Trading group
2. Click **"Actions"** → **"Full Run"**
3. Waits for completion (check logs)

### Individual Steps

For testing or debugging, use VS Code tasks:

- **Trading: Collect Data** - Fetches latest prices only
- **Trading: Train Models** - Retrains models only
- **Trading: Run Trading Cycle** - Executes trades only (no collection/training)

Access via: `Ctrl+Shift+P` → "Tasks: Run Task" → Select task name

See [Tasks Guide](tasks.md) for complete list of trading tasks.

## Best Practices

### ✅ Do This

- **Leave daemon running 24/7** - System is designed for continuous operation
- **Monitor weekly** - Check portfolio performance, adjust if needed
- **Let it run** - Don't manually interfere with positions
- **Check logs** - Review what happened if something seems off
- **Start small** - Use default $10k portfolio, scale up if profitable

### ❌ Don't Do This

- **Don't manually close positions** - Let stop-loss/take-profit handle it
- **Don't stop/start frequently** - Let the system build momentum
- **Don't change config mid-run** - Restart daemon after config changes
- **Don't panic on losses** - Short-term losses are normal, focus on long-term

## Stopping the System

**To stop daemon:**

1. Dashboard → Automation tab → Trading group
2. Click **"Actions"** → **"Stop Daemon"**

**To stop backend:**

- If started via VS Code task: Close the terminal or press `Ctrl+C`
- If started manually: Press `Ctrl+C` in terminal

**Note:** Stopping the backend also stops the daemon (it runs in a background thread).

## Troubleshooting

### Daemon Not Starting

- Check that trading is enabled in config
- Verify backend server is running
- Check logs for error messages
- Ensure portfolio is initialized

### No Trades Executing

- Check if models are trained (Model Status in dashboard)
- Verify you have enough data (at least 200+ price records)
- Check confidence thresholds (may be too high)
- Review signals in dashboard (may not meet criteria)

### Portfolio Losing Money

- Review trade history to see what's happening
- Check if stop-losses are being hit too often
- Consider adjusting confidence thresholds
- Review strategy performance (which strategies are profitable?)

### Data Collection Failing

- Check API keys (Alpha Vantage, CoinGecko)
- Verify internet connection
- Check rate limits (free tiers have limits)
- Review logs for specific errors

## Configuration Tips

### Adjust Trading Frequency

**More active (1 hour interval):**

- Better for volatile markets
- More opportunities
- More API calls (watch rate limits)

**Less active (6 hour interval):**

- Better for stable markets
- Fewer opportunities
- Less API usage

**Change interval:**

- Default: 1 hour (3600 seconds)
- Currently fixed at 1 hour
- For custom intervals, use dashboard API (advanced users only)

### Adjust Risk Settings

**More conservative:**

- Lower `risk_per_trade` (e.g., 0.01 = 1%)
- Higher `min_confidence` (e.g., 0.7 = 70%)
- Lower `max_position_size` (e.g., 0.03 = 3%)

**More aggressive:**

- Higher `risk_per_trade` (e.g., 0.03 = 3%)
- Lower `min_confidence` (e.g., 0.55 = 55%)
- Higher `max_position_size` (e.g., 0.10 = 10%)

**Edit in:** `config/config.json` → `trading` section

## What to Expect

### First Week

- System collecting data
- Models training on limited data
- Few trades (waiting for good signals)
- Portfolio may fluctuate

### First Month

- Models improving with more data
- More consistent trading
- Better signal quality
- Clearer performance trends

### Long Term

- Stable performance patterns
- Strategy-specific insights
- Optimized model predictions
- Compound growth (if profitable)

## Next Steps

- **Monitor performance** - Track ROI, win rate, Sharpe ratio
- **Review strategies** - See which strategies work best
- **Adjust config** - Fine-tune based on results
- **Scale up** - Increase portfolio size if profitable
- **Read technical docs** - See [trading.md](trading.md) for architecture details

## Complete Workflow (Once Everything Works)

**Step-by-step process:**

1. ✅ **Enable trading:** Edit `config/config.json` → `trading.enabled = true`
2. ✅ **Start backend:** VS Code task **Dashboard Backend: Start Server**
3. ✅ **Test first:** Dashboard → Automation → Trading → "Full Run" (verify everything works)
4. ✅ **Initialize portfolio:** Dashboard → Automation → Trading → "Initialize Portfolio"
5. ✅ **Start daemon:** Dashboard → Automation → Trading → "Start Daemon"
6. ✅ **Leave it running 24/7** - System operates automatically
7. ✅ **Monitor weekly** - Check portfolio performance via dashboard
8. ✅ **Don't interfere** - Let stop-loss/take-profit manage positions

**The system is designed to run continuously with minimal intervention.**

## Related Documentation

- **[trading.md](trading.md)** - Technical reference (architecture, strategies, API)
- **[dashboard.md](dashboard.md)** - Dashboard usage guide
- **[automation.md](automation.md)** - Automation system overview
