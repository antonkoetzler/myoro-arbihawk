# Backlog

This document tracks major gaps and improvements, organized by category and priority.

**Domains:**

- **Betting**: Sports betting prediction system
- **Trading**: Stock/crypto trading system (NEW)

**Categories:**

- **Profitability**: Tasks that improve model accuracy and profitability
- **Performance**: Tasks that optimize runtime and system efficiency
- **Data Quality**: Tasks that improve data collection and validation

---

## Recently Completed

### Stock/Crypto Trading System ✅

**Status:** COMPLETED
**Impact:** New revenue domain with ML-driven trading

**Implemented:**

- Feature engineering (RSI, MACD, Bollinger Bands, ATR, momentum features)
- ML predictors for momentum, swing, and volatility strategies
- Trade signal engine with expected value calculations
- Portfolio management with position sizing (risk-based, fixed, percentage)
- Paper trading executor with market/limit orders, stop-loss, take-profit
- Trading service orchestrating the full workflow
- Dashboard integration (Trading tab)
- VSCode tasks for training and trading cycles
- Comprehensive test suite
- Documentation

See [Trading Guide](trading.md) for details.

### Profitability-Based Model Selection ✅

**Status:** COMPLETED  
**Impact:** Ensures only profitable models are activated, improving overall system profitability

**Implemented:**

- Betting metrics (ROI, profit, Sharpe ratio) computed during training
- Profitability-based model activation with configurable thresholds
- Models below ROI threshold saved but not activated (for comparison)
- Configurable minimum bets requirement for meaningful evaluation
- Integration with model versioning system

**Configuration:**

Edit `config/automation.json` → `model_versioning.profitability_selection`:

- `enabled`: Enable profitability-based selection (default: true)
- `min_roi`: Minimum ROI to activate (default: 0.0 = break even)
- `min_bets`: Minimum bets for evaluation (default: 10)
- `save_unprofitable`: Save unprofitable models for comparison (default: true)

---

## Critical Issues (High Impact)

---

## Important Issues (Medium Impact)

### 1. Feature Engineering Gaps

**Category:** Profitability  
**Status:** Basic features only (21 features)  
**Impact:** Missing predictive signals that could improve accuracy  
**Readiness:** ✅ Good to go - Can be done iteratively, high impact on model performance

**Current Features:**

- Team form (last 5 matches): win rate, avg goals scored/conceded, form points
- Head-to-head: wins, draws, avg goals
- Home/away performance
- Odds features: average odds, odds spread

**Missing Features:**

- **Form momentum**: Recent trend (improving/declining), not just averages
- **Opponent strength adjustments**: Form vs. strong teams vs. weak teams
- **Rest days**: Days between matches (fatigue factor)
- **Market-specific features**:
  - Over/Under: Recent goal trends, defensive stats, shot statistics
  - BTTS: Recent scoring/conceding patterns, attacking strength
- **Tournament context**: Match importance, stage (regular season vs. playoffs)
- **Temporal features**: Day of week, time of day (mentioned in docs but not implemented)

---

---

### 3. Dynamic EV Threshold

**Category:** Profitability  
**Status:** Fixed threshold (0.07)  
**Impact:** May miss value bets or take too many low-confidence bets  
**Readiness:** ⏸️ Wait until profitability achieved - Optimization task, focus on core issues first

**Current State:**

- Fixed EV threshold: `config.EV_THRESHOLD = 0.07` (7%)
- Same threshold regardless of model confidence or market conditions

**What's Needed:**

- Adjust threshold based on model confidence (higher confidence = lower threshold)
- Market-specific thresholds (different for 1x2 vs. over_under)
- Dynamic adjustment based on recent performance
- Consider prediction uncertainty in threshold calculation

---

### 4. Market-Specific Optimization

**Category:** Profitability  
**Status:** Same approach for all markets  
**Impact:** Suboptimal models for different market types  
**Readiness:** ⏸️ Wait until profitability achieved - Fine-tuning task, address after baseline is profitable

**Current State:**

- Same hyperparameters for 1x2, over_under, btts
- Same feature set (though some features may not be relevant)
- Same training approach

**What's Needed:**

- Market-specific hyperparameter tuning
- Market-specific feature engineering
- Different model architectures if needed (e.g., regression for over/under goals)
- Separate calibration for each market

---

## Performance & Optimization (Critical for Runtime)

**Current Issue:** ~~Full Run takes 2+ hours. Target: 60-75 minutes.~~ Feature engineering optimized.

### 5. Vectorize Feature Engineering

**Category:** Performance  
**Status:** ✅ COMPLETED  
**Impact:** CRITICAL - Feature engineering was the main bottleneck (60-90+ minutes)  
**Readiness:** ✅ Implemented

**Implementation:**

- Data cached at instance level (fixtures, scores, odds loaded once)
- Lazy-indexed team lookups for fast filtering
- Vectorized numpy operations for aggregations
- Features computed once for all markets (1x2, over_under, btts)
- `create_training_data()` returns all labels in one pass

**Results:** Feature engineering reduced from 60-90 minutes to ~15 seconds (~99% reduction)

---

### 6. Add Database Query Caching

**Category:** Performance  
**Status:** ✅ COMPLETED (as part of Task #5)  
**Impact:** HIGH - Same data loaded thousands of times  
**Readiness:** ✅ Implemented

**Implementation:**

- Fixtures, scores, and odds cached at FeatureEngineer instance level
- Lazy-indexed lookups by team_id and fixture_id
- `invalidate_cache()` method for clearing when new data is ingested

---

### 7. Compute Features Once for All Markets

**Category:** Performance  
**Status:** ✅ COMPLETED (as part of Task #5)  
**Impact:** HIGH - Triples feature engineering time unnecessarily  
**Readiness:** ✅ Implemented

**Implementation:**

- `create_training_data()` now returns `(X, labels_dict, dates)` where `labels_dict` contains labels for all markets
- `train_models()` computes features once and reuses for all 3 markets
- Labels generated vectorized using numpy operations

---

### 8. Optimize Database Queries for Feature Engineering

**Category:** Performance  
**Status:** Queries load all data even when filtering needed  
**Impact:** MEDIUM - Unnecessary data transfer and memory usage  
**Readiness:** ✅ Good to go - SQL optimization

**Current State:**

- `get_team_form()` calls `get_fixtures(to_date=before_date)` but still loads all scores
- `get_head_to_head()` loads all fixtures/scores, then filters in pandas
- No date/team filtering in SQL queries

**What's Needed:**

- Add SQL WHERE clauses to filter by date range in `get_fixtures()`
- Add team_id filtering in SQL for team-specific queries
- Use indexed columns (start_time, home_team_id, away_team_id) for faster queries
- Consider adding composite indexes for common query patterns

**Expected Impact:** Reduce query time and memory usage, especially as data grows

---

### 9. Incremental Feature Computation

**Category:** Performance  
**Status:** All features recomputed from scratch each time  
**Impact:** MEDIUM - Could cache intermediate results  
**Readiness:** ⏸️ Lower priority - Nice optimization after vectorization

**Current State:**

- Team form recalculated for every match, even if team's recent matches haven't changed
- Head-to-head stats recalculated even if teams haven't played new matches
- No incremental updates

**What's Needed:**

- Cache team form stats per team/date combination
- Cache head-to-head stats per team pair
- Only recompute when new matches are added for that team/pair
- Use hash-based cache keys (team_id + date, team_pair + date)

**Expected Impact:** Further speedup for incremental training runs (when only new matches added)

---

## Nice-to-Have (Lower Priority)

### 10. Training Data Quality Filtering

**Category:** Data Quality  
**Status:** Not implemented  
**Impact:** Poor data quality reduces model performance  
**Readiness:** ✅ Good to go - Foundational issue that prevents problems before they occur

**What's Needed:**

- Filter matches with missing/incomplete odds data
- Exclude very old data (e.g., >2 years) that may not be relevant
- Handle outliers and data quality issues
- Ensure minimum data quality standards before training

---

### 11. Feature Importance Analysis

**Category:** Profitability  
**Status:** Not implemented  
**Impact:** Can't identify which features matter or remove noise  
**Readiness:** ⏸️ Wait until profitability achieved - Analysis tool, not critical for initial profitability

**What's Needed:**

- Track feature importance from XGBoost models
- Store feature importance in model versioning
- Use for feature selection (remove low-importance features)
- Display in dashboard for analysis

---

## Recommended Priority Order

### Performance (Critical - ~~Blocking~~ RESOLVED)

1. ~~**Vectorize Feature Engineering (#5)**~~ ✅ COMPLETED - Reduced from 60-90 min to ~15 sec
2. ~~**Add Database Query Caching (#6)**~~ ✅ COMPLETED - Part of #5
3. ~~**Compute Features Once for All Markets (#7)**~~ ✅ COMPLETED - Part of #5

### Profitability (High Impact)

4. **Feature Engineering Gaps (#1)** - Incremental improvements, can be done iteratively
5. **Training Data Quality (#10)** - Important but lower impact

### Optimization (After Core Issues Fixed)

7. **Optimize Database Queries (#8)** - SQL-level optimizations (lower priority now that caching is in place)
8. **Dynamic EV Threshold (#3)** - Optimization after core issues fixed
9. **Market-Specific Optimization (#4)** - Fine-tuning after baseline is solid
10. **Incremental Feature Computation (#9)** - Nice optimization after vectorization
11. **Feature Importance (#11)** - Analysis tool, not critical for profitability

---

## Notes

- ✅ **Feature Engineering Optimization** completed - Feature engineering reduced from 60-90 minutes to ~15 seconds
- Focus on profitability, not extensibility
- Current goal: Models for some bet types + training structure that makes profit
- ✅ **Probability Calibration** has been implemented (see [Calibration Guide](calibration.md))
- Many issues are interconnected (better EV → better profitability, faster training → more iterations)
