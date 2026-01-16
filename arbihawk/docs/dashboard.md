# Dashboard Guide

## Overview

The dashboard is a local web interface for monitoring and controlling the betting prediction system. It provides real-time status, performance metrics, and manual controls for automation.

The dashboard runs on **<http://localhost:8000>** and consists of:

- **Backend**: FastAPI server providing REST API endpoints
- **Frontend**: React-based web interface (optional, can be built separately)

## Features

### Overview Page

- Current bankroll balance and profit
- ROI and win rate statistics
- Recent bet history
- Database statistics (row counts per table)
- Error alerts and warnings

### Betting Page

- Complete bet history with filtering
- Export functionality (CSV/JSON)
- Bet details: odds, stake, outcome, profit/loss

### Automation Page

- Current scheduler status
- Manual trigger buttons for collection/training
- Start/stop controls for daemon mode
- Real-time log viewer with error highlighting

### Models Page

- All model versions with metadata
- Active model indicator per market
- Manual rollback controls
- Training metrics and performance history

### Logs Page

- Real-time log stream
- Error highlighting
- Filtering by log level

## API Endpoints

The dashboard backend exposes REST API endpoints:

### Metrics

- `GET /api/metrics` - All metrics with filtering
- `GET /api/metrics/summary` - Summary statistics
- `GET /api/metrics/export` - Export to CSV/JSON

### Bankroll

- `GET /api/bankroll` - Current balance and stats
- `GET /api/bankroll/report` - Detailed performance report

### Bets

- `GET /api/bets` - Bet history with filtering
- `GET /api/bets/export` - Export to CSV/JSON

### Models

- `GET /api/models` - Model versions and metadata
- `POST /api/models/rollback` - Rollback to specific version

### Automation

- `GET /api/automation/status` - Scheduler status
- `POST /api/automation/trigger` - Trigger collection/training
- `POST /api/automation/stop` - Stop running tasks
- `GET /api/automation/logs` - Recent logs

### Database

- `GET /api/database/stats` - Table row counts
- `GET /api/database/backups` - List backups

### Health

- `GET /api/health` - Health check endpoint
- `GET /api/errors` - Recent errors and alerts

## Starting the Dashboard

### Backend Server

Start the dashboard backend using the **Dashboard: Start Server** task (see [Tasks Guide](tasks.md)), or run:

```bash
python -m dashboard.api
```

For development with auto-reload, use the **Dashboard: Start with Reload** task, or:

```bash
uvicorn dashboard.api:app --reload
```

Then open <http://localhost:8000> in your browser.

### Frontend Development

If developing the frontend separately:

1. Install dependencies: **Frontend: Install Dependencies** task
2. Start dev server: **Frontend: Start Dev Server** task

Or manually:

```bash
cd dashboard/frontend
bun install
bun run dev
```

## Architecture

The dashboard uses:

- **FastAPI** for the backend API
- **React + Vite** for the frontend (if built)
- **Polling** (every 30 seconds) instead of WebSockets for simplicity
- **Static file serving** for the built frontend

## Data Flow

1. Frontend polls API endpoints every 30 seconds
2. Backend queries database and returns JSON
3. Frontend updates UI with latest data
4. User actions trigger POST requests to backend
5. Backend executes actions and returns results

## Configuration

Dashboard settings are minimal - it reads from the same configuration files as the rest of the system:

- `config/config.json` - Database path, general settings
- `config/automation.json` - Automation configuration

The dashboard automatically uses these configurations when making API calls.
