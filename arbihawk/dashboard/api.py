"""
Dashboard API backend using FastAPI.
Provides REST endpoints for monitoring and control.
"""

import sys
import csv
import io
import json
import asyncio
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


# =============================================================================
# WEBSOCKET CONNECTION MANAGER
# =============================================================================

class ConnectionManager:
    """Manages WebSocket connections for real-time log streaming."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message)
        disconnected = set()
        
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(message_json)
                except Exception:
                    disconnected.add(connection)
            
            # Remove disconnected clients
            self.active_connections -= disconnected
    
    def broadcast_sync(self, message: Dict[str, Any]):
        """Synchronous wrapper to broadcast from non-async context."""
        if not self.active_connections:
            return
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule the broadcast in the running loop
                asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)
            else:
                loop.run_until_complete(self.broadcast(message))
        except RuntimeError:
            # No event loop, create a new one
            asyncio.run(self.broadcast(message))


# Global connection manager
ws_manager = ConnectionManager()


# Initialize FastAPI app
app = FastAPI(
    title="Arbihawk Dashboard API",
    description="API for monitoring and controlling the betting prediction system",
    version="1.0.0"
)

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
    log_entry = {
        "timestamp": datetime.now().isoformat(),
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


# =============================================================================
# BETS ENDPOINTS
# =============================================================================

@app.get("/api/bets")
async def get_bet_history(
    result: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000)
) -> Dict[str, Any]:
    """Get bet history with optional filtering."""
    db = get_db()
    bets_df = db.get_bet_history(result=result, limit=limit)
    bets = bets_df.to_dict('records') if len(bets_df) > 0 else []
    
    return {
        "bets": bets,
        "count": len(bets)
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
    mode: str  # "collect" or "train"


@app.post("/api/automation/trigger")
async def trigger_automation(request: TriggerRequest) -> Dict[str, Any]:
    """Manually trigger data collection or training."""
    scheduler = get_scheduler()
    
    if request.mode == "collect":
        result = scheduler.trigger_collection()
    elif request.mode == "train":
        result = scheduler.trigger_training()
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
    await ws_manager.connect(websocket)
    
    try:
        # Send existing logs on connection
        logs = get_scheduler().get_logs(limit=100)
        for log in logs:
            await websocket.send_text(json.dumps(log))
        
        # Keep connection alive and wait for messages
        while True:
            try:
                # Wait for any message (ping/pong or close)
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await ws_manager.disconnect(websocket)


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
    # Get errors from logs
    logs = get_scheduler().get_logs(limit=1000)
    errors = [log for log in logs if log.get('level') == 'error']
    
    # Get failed ingestions
    db = get_db()
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
    # Use app object directly to avoid RuntimeWarning
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
