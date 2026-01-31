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

## Critical / High Impact

### 1. Dynamic EV Threshold

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

### 2. Market-Specific Optimization

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

## Performance & Optimization

### 4. Incremental Feature Computation

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

### 5. Training Data Quality Filtering

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

### 6. Feature Importance Analysis

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

### Profitability (High Impact)

1. **Training Data Quality (#5)** - Important but lower impact

### Optimization (After Core Issues Fixed)

2. **Dynamic EV Threshold (#1)** - Optimization after core issues fixed
3. **Market-Specific Optimization (#2)** - Fine-tuning after baseline is solid
4. **Incremental Feature Computation (#4)** - Nice optimization
5. **Feature Importance (#6)** - Analysis tool, not critical for profitability

---

## Notes

- Focus on profitability, not extensibility
- Current goal: Models for some bet types + training structure that makes profit
- Many issues are interconnected (better EV → better profitability, faster training → more iterations)
