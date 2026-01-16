# Model Versioning Guide

## Overview

The versioning system tracks model versions and enables rollback.

## How It Works

1. Each training run creates a new model version
2. Versions are stored with metadata (samples, CV score, etc.)
3. Only one version is active per market
4. Can rollback to previous versions if needed

## Configuration

Edit `config/automation.json`:

```json
{
  "model_versioning": {
    "auto_rollback_enabled": true,
    "rollback_threshold": -10.0,
    "rollback_evaluation_bets": 50,
    "max_versions_to_keep": 10
  }
}
```

## Auto-Rollback

When enabled, the system checks if the current model is underperforming:

- Evaluates ROI over the last N bets (default: 50)
- If ROI drops below threshold (default: -10%), rolls back
- Creates backup before rollback

## Using the API

```python
from models.versioning import ModelVersionManager

manager = ModelVersionManager()

# Save a new version
version_id = manager.save_version(
    market="1x2",
    model_path="models/saved/1x2_model.pkl",
    training_samples=1000,
    cv_score=0.65
)

# Get active version
active = manager.get_active_version("1x2")

# Rollback
manager.rollback_to_version(previous_version_id)

# Compare versions
comparison = manager.compare_versions(v1, v2)
```

## Dashboard

The dashboard shows:

- All model versions with metadata
- Active version indicator
- Manual rollback button

## Best Practices

1. Start with lenient rollback threshold (-10%)
2. Increase strictness as you gain confidence
3. Keep multiple versions for comparison
4. Monitor betting performance after training
