# Monitoring Guide

## Overview

The monitoring system tracks all aspects of the prediction system.

## Metric Types

### Ingestion Metrics

- `records_betano`: Records processed from Betano
- `records_fbref`: Records processed from FBref
- `success_betano`: Ingestion success (1/0)
- `duration_betano`: Processing time in ms

### Matching Metrics

- `total_processed`: Scores processed
- `matched`: Successfully matched
- `unmatched`: Failed to match
- `match_rate`: Match rate (0-1)

### Model Metrics

- `cv_score_{market}`: Cross-validation score
- `samples_{market}`: Training samples
- `accuracy_{market}`: Model accuracy

### Betting Metrics

- `roi`: Return on investment
- `win_rate`: Win rate
- `total_bets`: Total bets placed
- `profit`: Total profit/loss

## Using the API

```python
from monitoring.metrics import MetricsCollector

collector = MetricsCollector()

# Record a metric
collector.record("betting", "roi", 0.15)

# Get recent metrics
metrics = collector.get_metrics(metric_type="betting", days=7)

# Get latest value
latest = collector.get_latest("betting", "roi")
```

## Reports

```python
from monitoring.reporter import MetricsReporter

reporter = MetricsReporter()

# Generate summary
report = reporter.generate_summary(days=7)

# Print to console
reporter.print_report(report)
```

## Retention

Metrics are retained for 18 months by default (configurable). Old metrics are automatically cleaned up.

## Dashboard

The dashboard provides:

- Real-time metric visualization
- Summary statistics
- Export functionality (CSV/JSON)
