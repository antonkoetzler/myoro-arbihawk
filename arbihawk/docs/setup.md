# Setup Guide

## Prerequisites

- **Python 3.10 or higher**
- **Git** (for submodules)
- **Bun** (optional, for frontend development)

## Installation Steps

### 1. Clone Repository

Clone the repository with submodules:

```bash
git clone --recurse-submodules <repo-url>
cd arbihawk
```

If already cloned, initialize submodules:

```bash
git submodule update --init --recursive
```

Or use the **Setup: Initialize Git Submodules** task (see [Tasks Guide](tasks.md)).

### 2. Create Virtual Environment

Create a virtual environment in the project directory:

**Windows PowerShell:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Or use the **Setup: Install Dependencies** task (see [Tasks Guide](tasks.md)).

### 4. Configure Settings

Edit `config/config.json` for main settings:

```json
{
  "db_path": "data/arbihawk.db",
  "ev_threshold": 0.07
}
```

Edit `config/automation.json` for automation settings (schedules, scraper args, fake money configuration).

## Project Structure

```
arbihawk/
├── automation/      # Scheduled data collection and training
├── config/          # JSON configuration files
├── dashboard/       # FastAPI backend and React frontend
├── data/            # Database and data processing
├── engine/          # Value betting engine
├── models/          # XGBoost prediction models
├── monitoring/      # Metrics and reporting
├── scrapers/        # Git submodule for data scrapers
├── testing/         # Fake money system
└── docs/            # Documentation
```

## Configuration Files

All configuration is stored in JSON files (no .env files):

- **`config/config.json`** - Main settings (database path, EV threshold)
- **`config/automation.json`** - Automation schedules, scraper args, fake money settings, model versioning

## Export/Import Data

To transfer your Arbihawk installation to a different computer:

### Export

```bash
python export_data.py [output_path]
```

Exports database, models, and configuration to a zip archive. If `output_path` is not provided, creates a timestamped file in the current directory.

**What's exported:**
- Database file (`arbihawk.db` or `arbihawk_debug.db`)
- All model files (`models/saved/*.pkl`)
- All configuration files (`config/*.json`)
- Version information (schema version, Python version, platform, package versions)

### Import

```bash
python import_data.py <export_file.zip> [--overwrite-db] [--overwrite-models] [--overwrite-config]
```

Imports data from an export archive. The script will:
- Validate schema version compatibility
- Automatically run database migrations if needed
- Back up existing database before import (if overwriting)
- Prompt before overwriting existing files (unless flags are used)

**Options:**
- `--overwrite-db`: Overwrite existing database
- `--overwrite-models`: Overwrite existing model files
- `--overwrite-config`: Overwrite existing configuration files

**Note:** The import script handles schema migrations automatically. If importing an older export, migrations will be applied to bring the database up to the current schema version.

## Next Steps

After setup:

1. **Run data collection** to populate the database (see [Automation Guide](automation.md))
2. **Train models** on collected data (see [Training Guide](training.md))
3. **Start the dashboard** to monitor performance (see [Dashboard Guide](dashboard.md))
4. **Configure automation** schedule for continuous operation (see [Automation Guide](automation.md))

## Running Commands

All common commands are available as VS Code tasks. See [Tasks Guide](tasks.md) for the complete list and how to use them.

## Verification

Verify your setup by:

1. Checking database exists: `data/arbihawk.db` should be created on first run
2. Running a test collection: Use **Automation: Collect Data** task
3. Checking database stats: Use **Database: Check Stats** task
