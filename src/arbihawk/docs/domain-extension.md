# ModelVersionManager Domain Extension

## Overview

The `ModelVersionManager` has been extended to support multiple domains (betting and trading). This allows the system to track models for both betting and trading strategies independently.

## Changes

### Database Schema

- Added `domain` column to `model_versions` table (Migration 5)
- Default value: `'betting'` for existing rows
- Composite indexes added: `(domain, market)` and `(domain, market, is_active)`

### API Changes

All `ModelVersionManager` methods now require explicit `domain` parameter:

**Before:**

```python
manager.save_version(market="1x2", ...)
manager.get_active_version(market="1x2")
```

**After:**

```python
manager.save_version(domain="betting", market="1x2", ...)
manager.get_active_version(domain="betting", market="1x2")
```

### Updated Files

- `data/database.py` - Migration 5, updated methods
- `models/versioning.py` - Added domain parameter to all methods
- `train.py` - Passes `domain='betting'` explicitly
- `automation/betting.py` - Passes `domain='betting'` explicitly
- `dashboard/api.py` - Passes `domain='betting'` for betting markets
- `tests/test_model_training.py` - Updated all tests + added domain separation test

## Backward Compatibility

All existing betting code has been updated to explicitly pass `domain='betting'`. The betting system continues to work exactly as before.

## Usage

### Betting Models

```python
from models.versioning import ModelVersionManager

manager = ModelVersionManager()

# Save betting model
version_id = manager.save_version(
    domain="betting",
    market="1x2",
    model_path="models/saved/1x2_model.pkl",
    training_samples=1000,
    cv_score=0.65
)

# Get active betting model
active = manager.get_active_version(domain="betting", market="1x2")
```

### Trading Models (Future)

```python
# Save trading model
version_id = manager.save_version(
    domain="trading",
    market="momentum",
    model_path="models/saved/momentum_model.pkl",
    training_samples=2000,
    cv_score=0.70
)

# Get active trading model
active = manager.get_active_version(domain="trading", market="momentum")
```

### Domain Separation

Models in different domains are completely independent:

- Betting models: `domain='betting'`, `market='1x2'`, `'over_under'`, `'btts'`
- Trading models: `domain='trading'`, `market='momentum'`, `'swing'`, `'pairs'`, etc.

Activating a model in one domain does not affect the other domain.

## Testing

Run the domain separation test:

```bash
cd src/arbihawk
python -m pytest tests/test_model_training.py::TestModelTraining::test_domain_separation -v
```

Run all model training tests:

```bash
cd src/arbihawk
python -m pytest tests/test_model_training.py -v
```
