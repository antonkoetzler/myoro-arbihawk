"""
Dashboard API backend using FastAPI.
Provides REST endpoints for monitoring and control.
"""

import sys
import csv
import io
import json
import asyncio
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Set

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from data.database import Database
from data.backup import DatabaseBackup
from testing.bankroll import VirtualBankroll
from monitoring.metrics import MetricsCollector
from monitoring.reporter import MetricsReporter
from models.versioning import ModelVersionManager
from automation.scheduler import AutomationScheduler
from backtesting.backtest import BacktestEngine, BacktestResult


# =============================================================================
# WEBSOCKET CONNECTION MANAGER
# =============================================================================

# Global event loop reference - set at startup
_main_event_loop: Optional[asyncio.AbstractEventLoop] = None


class ConnectionManager:
    """Manages WebSocket connections for real-time log streaming."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._recent_logs: List[Dict[str, Any]] = []
        self._max_recent_logs = 100
        self._lock = threading.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        with self._lock:
            self.active_connections.add(websocket)
            logs_to_send = list(self._recent_logs)
        
        # Send recent logs to newly connected client
        for log in logs_to_send:
            try:
                await websocket.send_text(json.dumps(log))
            except Exception:
                break
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        with self._lock:
            self.active_connections.discard(websocket)
    
    async def _send_to_connections(self, message: Dict[str, Any]):
        """Send a message to all connected clients (async)."""
        with self._lock:
            connections = list(self.active_connections)
        
        if not connections:
            return
        
        message_json = json.dumps(message)
        disconnected = []
        
        for conn in connections:
            try:
                await conn.send_text(message_json)
            except Exception:
                disconnected.append(conn)
        
        if disconnected:
            with self._lock:
                for conn in disconnected:
                    self.active_connections.discard(conn)
    
    def broadcast_sync(self, message: Dict[str, Any]):
        """
        Broadcast a message from any thread (sync or async context).
        This is the main entry point for logging from background threads.
        """
        # Always store the log
        with self._lock:
            self._recent_logs.append(message)
            if len(self._recent_logs) > self._max_recent_logs:
                self._recent_logs.pop(0)
            has_connections = len(self.active_connections) > 0
        
        if not has_connections:
            return
        
        # Use the stored event loop reference
        if _main_event_loop is None:
            return
        
        # Schedule the async send on the main event loop
        try:
            asyncio.run_coroutine_threadsafe(
                self._send_to_connections(message),
                _main_event_loop
            )
        except Exception:
            # If scheduling fails, log is still stored and will be sent on reconnect
            pass


# Global connection manager
ws_manager = ConnectionManager()


# Initialize FastAPI app
app = FastAPI(
    title="Arbihawk Dashboard API",
    description="API for monitoring and controlling the betting prediction system",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Capture the main event loop at startup for cross-thread communication."""
    global _main_event_loop
    _main_event_loop = asyncio.get_running_loop()


# Global instances (lazy initialized)
_db: Optional[Database] = None
_scheduler: Optional[AutomationScheduler] = None
_bankroll: Optional[VirtualBankroll] = None
_metrics: Optional[MetricsCollector] = None
_versioning: Optional[ModelVersionManager] = None
_backup: Optional[DatabaseBackup] = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


def get_scheduler() -> AutomationScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AutomationScheduler(get_db())
        # Set up WebSocket broadcast callback for logs
        _scheduler.set_log_callback(broadcast_log)
    return _scheduler


def broadcast_log(level: str, message: str):
    """Callback to broadcast log messages via WebSocket."""
    now = datetime.now()
    log_entry = {
        "timestamp": now.strftime("%Y-%m-%d ~ %H:%M:%S"),
        "level": level,
        "message": message
    }
    ws_manager.broadcast_sync(log_entry)


def get_bankroll() -> VirtualBankroll:
    global _bankroll
    if _bankroll is None:
        _bankroll = VirtualBankroll(get_db())
    return _bankroll


def get_metrics() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector(get_db())
    return _metrics


def get_versioning() -> ModelVersionManager:
    global _versioning
    if _versioning is None:
        _versioning = ModelVersionManager(get_db())
    return _versioning


def get_backup() -> DatabaseBackup:
    global _backup
    if _backup is None:
        _backup = DatabaseBackup()
    return _backup


# =============================================================================
# METRICS ENDPOINTS
# =============================================================================

@app.get("/api/metrics")
async def get_all_metrics(
    metric_type: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=365)
) -> Dict[str, Any]:
    """Get all metrics with optional filtering."""
    metrics = get_metrics().get_metrics(metric_type=metric_type, days=days)
    return {
        "metrics": metrics,
        "count": len(metrics)
    }


@app.get("/api/metrics/summary")
async def get_metrics_summary() -> Dict[str, Any]:
    """Get summary of all metrics."""
    reporter = MetricsReporter(get_metrics())
    return reporter.generate_summary()


@app.get("/api/metrics/export")
async def export_metrics(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    days: int = Query(default=30, ge=1, le=365)
) -> Response:
    """Export metrics to JSON or CSV."""
    metrics = get_metrics().get_metrics(days=days, limit=10000)
    
    if format == "csv":
        output = io.StringIO()
        if metrics:
            writer = csv.DictWriter(output, fieldnames=metrics[0].keys())
            writer.writeheader()
            writer.writerows(metrics)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=metrics.csv"}
        )
    
    return JSONResponse(content={"metrics": metrics})


# =============================================================================
# BANKROLL ENDPOINTS
# =============================================================================

@app.get("/api/bankroll")
async def get_bankroll_stats() -> Dict[str, Any]:
    """Get fake money bankroll status and history."""
    return get_bankroll().get_stats()


@app.get("/api/bankroll/report")
async def get_bankroll_report() -> Dict[str, Any]:
    """Get detailed bankroll performance report."""
    return get_bankroll().get_performance_report()


@app.get("/api/bankroll/by-model")
async def get_bankroll_by_model(
    market: str = Query(..., description="Model market: 1x2, over_under, or btts")
) -> Dict[str, Any]:
    """Get bankroll statistics for a specific model market."""
    if market not in ['1x2', 'over_under', 'btts']:
        raise HTTPException(status_code=400, detail="Invalid market. Must be: 1x2, over_under, or btts")
    
    return get_bankroll().get_stats_by_model(market)


# =============================================================================
# BETS ENDPOINTS
# =============================================================================

@app.get("/api/bets")
async def get_bet_history(
    result: Optional[str] = Query(None, description="Filter by result: win, loss, or pending"),
    market_name: Optional[str] = Query(None, description="Filter by market name (partial match)"),
    outcome_name: Optional[str] = Query(None, description="Filter by outcome name (partial match)"),
    tournament_name: Optional[str] = Query(None, description="Filter by tournament/league name (partial match)"),
    date_from: Optional[str] = Query(None, description="Filter bets from this date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter bets until this date (YYYY-MM-DD)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=50, ge=1, le=1000, description="Items per page")
) -> Dict[str, Any]:
    """Get bet history with optional filtering and pagination."""
    db = get_db()
    offset = (page - 1) * per_page
    
    bets_df = db.get_bet_history(
        result=result,
        market_name=market_name,
        outcome_name=outcome_name,
        tournament_name=tournament_name,
        date_from=date_from,
        date_to=date_to,
        limit=per_page,
        offset=offset
    )
    bets = bets_df.to_dict('records') if len(bets_df) > 0 else []
    
    total_count = db.get_bet_history_count(
        result=result,
        market_name=market_name,
        outcome_name=outcome_name,
        tournament_name=tournament_name,
        date_from=date_from,
        date_to=date_to
    )
    
    return {
        "bets": bets,
        "count": len(bets),
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "total_pages": (total_count + per_page - 1) // per_page if per_page > 0 else 0
    }


@app.get("/api/bets/filter-values")
async def get_bet_filter_values() -> Dict[str, Any]:
    """Get unique values for bet history filters."""
    db = get_db()
    # Get a large sample to extract unique values (bypass API limit for this endpoint)
    bets_df = db.get_bet_history(limit=10000, offset=0)
    
    unique_markets = []
    unique_tournaments = []
    
    if len(bets_df) > 0:
        if 'market_name' in bets_df.columns:
            unique_markets = sorted(bets_df['market_name'].dropna().unique().tolist())
        if 'tournament_name' in bets_df.columns:
            unique_tournaments = sorted(bets_df['tournament_name'].dropna().unique().tolist())
    
    return {
        "markets": unique_markets,
        "tournaments": unique_tournaments
    }


@app.get("/api/bets/export")
async def export_bets(
    format: str = Query(default="json", pattern="^(json|csv)$")
) -> Response:
    """Export bet history to JSON or CSV."""
    db = get_db()
    bets_df = db.get_bet_history(limit=10000)
    bets = bets_df.to_dict('records') if len(bets_df) > 0 else []
    
    if format == "csv":
        output = io.StringIO()
        if bets:
            writer = csv.DictWriter(output, fieldnames=bets[0].keys())
            writer.writeheader()
            writer.writerows(bets)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=bets.csv"}
        )
    
    return JSONResponse(content={"bets": bets})


# =============================================================================
# MODELS ENDPOINTS
# =============================================================================

@app.get("/api/models")
async def get_model_versions(
    market: Optional[str] = None
) -> Dict[str, Any]:
    """Get model versions and performance."""
    versions = get_versioning().get_all_versions(market=market)
    
    # Get active versions for each market
    active = {}
    for m in ["1x2", "over_under", "btts"]:
        active_v = get_versioning().get_active_version(m)
        if active_v:
            active[m] = active_v.get("version_id")
    
    return {
        "versions": versions,
        "active": active,
        "count": len(versions)
    }


class RollbackRequest(BaseModel):
    version_id: int


@app.post("/api/models/rollback")
async def rollback_model(request: RollbackRequest) -> Dict[str, Any]:
    """Manually rollback to a model version."""
    success = get_versioning().rollback_to_version(request.version_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return {
        "success": True,
        "version_id": request.version_id,
        "message": f"Rolled back to version {request.version_id}"
    }


# =============================================================================
# AUTOMATION ENDPOINTS
# =============================================================================

@app.get("/api/automation/status")
async def get_automation_status() -> Dict[str, Any]:
    """Get automation scheduler status."""
    return get_scheduler().get_status()


class TriggerRequest(BaseModel):
    mode: str  # "collect", "train", "betting", "full", or "backtest"
    max_workers_leagues: Optional[int] = None  # Override for collection (Betano)
    max_workers_odds: Optional[int] = None  # Override for collection
    max_workers_leagues_playwright: Optional[int] = None  # Override for collection (FlashScore)


class TriggerBacktestRequest(BaseModel):
    train_start: str
    test_start: str
    test_end: str
    period_days: int = 30
    ev_threshold: Optional[float] = None


@app.post("/api/automation/trigger")
async def trigger_automation(request: TriggerRequest) -> Dict[str, Any]:
    """Manually trigger data collection, training, or betting."""
    scheduler = get_scheduler()
    
    # Apply worker overrides if provided
    if (request.max_workers_leagues is not None or 
        request.max_workers_odds is not None or 
        request.max_workers_leagues_playwright is not None):
        scheduler.set_scraper_workers(
            max_workers_leagues=request.max_workers_leagues,
            max_workers_odds=request.max_workers_odds,
            max_workers_leagues_playwright=request.max_workers_leagues_playwright
        )
    
    if request.mode == "collect":
        result = scheduler.trigger_collection()
    elif request.mode == "train":
        result = scheduler.trigger_training()
    elif request.mode == "betting":
        result = scheduler.trigger_betting()
    elif request.mode == "full":
        result = scheduler.trigger_full_run()
    elif request.mode == "backtest":
        # Backtest requires additional parameters, use dedicated endpoint
        raise HTTPException(status_code=400, detail="Use /api/backtesting/run for backtesting")
    else:
        raise HTTPException(status_code=400, detail="Invalid mode")
    
    return result


@app.post("/api/automation/stop")
async def stop_automation() -> Dict[str, Any]:
    """Stop running automation tasks (either daemon or current task)."""
    scheduler = get_scheduler()
    status = scheduler.get_status()
    
    # If a task is currently running, stop it
    if status.get("current_task"):
        result = scheduler.stop_task()
        return result
    
    # Otherwise, try to stop daemon mode
    if status.get("running"):
        scheduler.stop_daemon()
        return {
            "success": True,
            "message": "Stop signal sent to daemon"
        }
    
    return {
        "success": False,
        "message": "No task or daemon is currently running"
    }


class DaemonStartRequest(BaseModel):
    interval_seconds: int = 21600  # Default 6 hours


@app.post("/api/automation/daemon/start")
async def start_daemon(request: DaemonStartRequest = DaemonStartRequest()) -> Dict[str, Any]:
    """Start daemon mode."""
    scheduler = get_scheduler()
    status = scheduler.get_status()
    
    if status.get("running"):
        return {
            "success": False,
            "error": "Daemon is already running"
        }
    
    # Start daemon in background thread
    def run_daemon():
        try:
            scheduler.start_daemon(interval_seconds=request.interval_seconds)
        except Exception as e:
            broadcast_log("error", f"Daemon error: {e}")
    
    thread = threading.Thread(target=run_daemon, daemon=True)
    thread.start()
    
    return {
        "success": True,
        "message": f"Daemon started with {request.interval_seconds}s interval"
    }


@app.get("/api/automation/logs")
async def get_automation_logs(
    limit: int = Query(default=100, ge=1, le=1000)
) -> Dict[str, Any]:
    """Get automation logs."""
    logs = get_scheduler().get_logs(limit=limit)
    
    return {
        "logs": logs,
        "count": len(logs)
    }


# =============================================================================
# WEBSOCKET ENDPOINTS
# =============================================================================

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    try:
        await ws_manager.connect(websocket)
    except Exception:
        return
    
    try:
        while True:
            try:
                # Wait for messages (ping/pong or close)
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            await ws_manager.disconnect(websocket)
        except Exception:
            pass


# =============================================================================
# INGESTION ENDPOINTS
# =============================================================================

@app.get("/api/ingestion/stats")
async def get_ingestion_stats() -> Dict[str, Any]:
    """Get ingestion statistics."""
    db = get_db()
    metadata = db.get_ingestion_metadata(limit=100)
    records = metadata.to_dict('records') if len(metadata) > 0 else []
    
    # Calculate stats
    total_records = sum(r.get('records_count', 0) for r in records)
    success_count = sum(1 for r in records if r.get('validation_status') == 'success')
    
    return {
        "recent": records[:10],
        "total_ingestions": len(records),
        "total_records": total_records,
        "success_rate": success_count / len(records) if records else 0
    }


# =============================================================================
# ERRORS ENDPOINTS
# =============================================================================

@app.get("/api/errors")
async def get_recent_errors() -> Dict[str, Any]:
    """Get recent errors/alerts."""
    db = get_db()
    
    # Get dismissed log error keys
    dismissed_log_keys = db.get_dismissed_log_errors()
    
    # Get errors from logs and filter dismissed
    logs = get_scheduler().get_logs(limit=1000)
    errors = [
        log for log in logs 
        if log.get('level') == 'error' 
        and f"log-{log.get('timestamp')}-{log.get('message')}" not in dismissed_log_keys
    ]
    
    # Get failed ingestions (already filtered by dismissed in get_ingestion_metadata)
    metadata = db.get_ingestion_metadata(limit=100)
    failed = [
        r for r in metadata.to_dict('records') 
        if r.get('validation_status') not in ['success', None]
    ]
    
    return {
        "log_errors": errors[-20:],
        "ingestion_errors": failed[-10:],
        "total_errors": len(errors) + len(failed)
    }


@app.post("/api/errors/dismiss")
async def dismiss_error(error_type: str = Query(...), error_id: Optional[int] = Query(None), error_key: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Dismiss an error."""
    db = get_db()
    
    if error_type == "ingestion" and error_id:
        db.dismiss_ingestion_error(error_id)
    elif error_type == "log" and error_key:
        db.dismiss_log_error(error_key)
    else:
        raise HTTPException(status_code=400, detail="Invalid parameters")
    
    return {"success": True}


# =============================================================================
# DATABASE ENDPOINTS
# =============================================================================

@app.get("/api/database/stats")
async def get_database_stats() -> Dict[str, Any]:
    """Get database statistics."""
    return get_db().get_database_stats()


@app.get("/api/database/backups")
async def get_backups() -> Dict[str, Any]:
    """Get list of database backups."""
    backups = get_backup().list_backups()
    
    return {
        "backups": backups,
        "count": len(backups)
    }


# =============================================================================
# BACKTESTING ENDPOINTS
# =============================================================================

class BacktestRequest(BaseModel):
    train_start: str
    test_start: str
    test_end: str
    period_days: int = 30
    ev_threshold: Optional[float] = None
    markets: Optional[List[str]] = None
    min_training_samples: int = 50


@app.post("/api/backtesting/run")
async def run_backtest(request: BacktestRequest) -> Dict[str, Any]:
    """Run a backtest with specified parameters."""
    try:
        engine = BacktestEngine(ev_threshold=request.ev_threshold)
        result = engine.run_backtest(
            train_start=request.train_start,
            test_start=request.test_start,
            test_end=request.test_end,
            markets=request.markets,
            period_days=request.period_days,
            min_training_samples=request.min_training_samples
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtesting/results")
async def get_backtest_results() -> Dict[str, Any]:
    """Get list of saved backtest results."""
    results_dir = Path(__file__).parent.parent / "backtesting" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    for result_file in sorted(results_dir.glob("backtest_*.json"), reverse=True):
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)
                results.append({
                    "filename": result_file.name,
                    "created_at": result_file.stat().st_mtime,
                    "total_bets": data.get("total_bets", 0),
                    "roi": data.get("overall_metrics", {}).get("roi", 0),
                    "win_rate": data.get("overall_metrics", {}).get("win_rate", 0)
                })
        except Exception:
            continue
    
    return {
        "results": results[:50],  # Limit to 50 most recent
        "count": len(results)
    }


# =============================================================================
# CONFIG ENDPOINTS
# =============================================================================

@app.get("/api/config/scraper-workers")
async def get_scraper_workers_config() -> Dict[str, Any]:
    """Get scraper workers configuration."""
    import config
    return config.SCRAPER_WORKERS


class ScraperWorkersUpdate(BaseModel):
    max_workers_leagues: Optional[int] = None
    max_workers_odds: Optional[int] = None
    max_workers_leagues_playwright: Optional[int] = None


@app.put("/api/config/scraper-workers")
async def update_scraper_workers_config(config_update: ScraperWorkersUpdate) -> Dict[str, Any]:
    """Update scraper workers configuration."""
    import config as config_module
    
    # Load current config
    config_path = Path(__file__).parent.parent / "config" / "automation.json"
    with open(config_path, 'r') as f:
        automation_config = json.load(f)
    
    # Update scraper_workers section
    scraper_workers = automation_config.get("scraper_workers", {
        "max_workers_leagues": 5,
        "max_workers_odds": 5,
        "max_workers_leagues_playwright": 3
    })
    update_dict = config_update.dict(exclude_unset=True)
    scraper_workers.update(update_dict)
    automation_config["scraper_workers"] = scraper_workers
    
    # Save config
    with open(config_path, 'w') as f:
        json.dump(automation_config, f, indent=2)
    
    # Reload config
    config_module.reload_config()
    
    # Update scheduler with new values
    scheduler = get_scheduler()
    scheduler.set_scraper_workers(
        max_workers_leagues=scraper_workers.get("max_workers_leagues"),
        max_workers_odds=scraper_workers.get("max_workers_odds"),
        max_workers_leagues_playwright=scraper_workers.get("max_workers_leagues_playwright")
    )
    
    return {
        "success": True,
        "message": "Scraper workers configuration updated",
        "config": scraper_workers
    }


@app.get("/api/config/fake-money")
async def get_fake_money_config() -> Dict[str, Any]:
    """Get fake money configuration."""
    import config
    return config.FAKE_MONEY_CONFIG


class FakeMoneyConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    starting_balance: Optional[float] = None
    bet_sizing_strategy: Optional[str] = None
    fixed_stake: Optional[float] = None
    percentage_stake: Optional[float] = None
    unit_size_percentage: Optional[float] = None
    auto_bet_after_training: Optional[bool] = None


@app.put("/api/config/fake-money")
async def update_fake_money_config(config_update: FakeMoneyConfigUpdate) -> Dict[str, Any]:
    """Update fake money configuration."""
    import config
    
    # Load current config
    config_path = Path(__file__).parent.parent / "config" / "automation.json"
    with open(config_path, 'r') as f:
        automation_config = json.load(f)
    
    # Update fake_money section
    fake_money = automation_config.get("fake_money", {})
    update_dict = config_update.dict(exclude_unset=True)
    fake_money.update(update_dict)
    automation_config["fake_money"] = fake_money
    
    # Save config
    with open(config_path, 'w') as f:
        json.dump(automation_config, f, indent=2)
    
    # Reload config
    config.reload_config()
    
    return {
        "success": True,
        "message": "Configuration updated",
        "config": fake_money
    }


@app.get("/api/config/automation")
async def get_automation_config() -> Dict[str, Any]:
    """Get automation configuration."""
    import config
    config_path = Path(__file__).parent.parent / "config" / "automation.json"
    with open(config_path, 'r') as f:
        return json.load(f)


class AutomationConfigUpdate(BaseModel):
    collection_schedule: Optional[str] = None
    training_schedule: Optional[str] = None
    incremental_mode: Optional[bool] = None
    matching_tolerance_hours: Optional[int] = None


@app.put("/api/config/automation")
async def update_automation_config(config_update: AutomationConfigUpdate) -> Dict[str, Any]:
    """Update automation configuration."""
    import config
    
    # Load current config
    config_path = Path(__file__).parent.parent / "config" / "automation.json"
    with open(config_path, 'r') as f:
        automation_config = json.load(f)
    
    # Update config
    update_dict = config_update.dict(exclude_unset=True)
    automation_config.update(update_dict)
    
    # Save config
    with open(config_path, 'w') as f:
        json.dump(automation_config, f, indent=2)
    
    # Reload config
    config.reload_config()
    
    return {
        "success": True,
        "message": "Configuration updated",
        "config": automation_config
    }


# =============================================================================
# HEALTH ENDPOINT
# =============================================================================

@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


# =============================================================================
# STATIC FILES (Frontend)
# =============================================================================

# Serve frontend static files if they exist
frontend_dir = Path(__file__).parent / "frontend" / "dist"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run the dashboard server."""
    import uvicorn
    print("Starting Arbihawk Dashboard...")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
