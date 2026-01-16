# Arbihawk - Next Steps

## Configuration

All configuration is in JSON files:

- `config/config.json` - Database path, EV threshold
- `config/automation.json` - Schedules, fake money settings, model versioning

## Running Automation

The automation system can run in several modes:

- **Once**: Run a single cycle and exit (useful for cron)
- **Daemon**: Run continuously in the background
- **Collection only**: Just gather data
- **Training only**: Just train models

See [Automation Guide](docs/automation.md) for details on configuration, scheduling, and execution modes.

## What You Need To Do

1. **Add scrapers submodule** - The scrapers repo needs to be added as a git submodule at `scrapers/`
1. **Collect initial data** - Run the collection cycle a few times to build up the database
1. **Train initial models** - Once you have enough data (100+ matches with scores), train the models
1. **Monitor performance** - Use the dashboard to track ROI and win rates
1. **Tune configuration** - Adjust bet sizing strategy and EV threshold based on results

## Documentation

Full documentation is in the `docs/` directory:

- [Tasks Guide](docs/tasks.md) - Using VS Code tasks for all commands
- [Automation Guide](docs/automation.md)
- [Ingestion Guide](docs/ingestion.md)
- [Testing Guide](docs/testing.md)
- [Monitoring Guide](docs/monitoring.md)
- [Versioning Guide](docs/versioning.md)
- [Dashboard Guide](docs/dashboard.md)
