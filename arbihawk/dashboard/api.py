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
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
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
from models.predictor import BettingPredictor
from engine.value_bet import ValueBetEngine
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
    description="API for monitoring and controlling the ML-powered prediction & trading platform",
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


def broadcast_log(level: str, message: str, domain: str = "betting"):
    """Callback to broadcast log messages via WebSocket.
    
    Args:
        level: Log level (info, warning, error, success)
        message: Log message
        domain: Domain identifier (betting, trading)
    """
    now = datetime.now()
    log_entry = {
        "timestamp": now.strftime("%Y-%m-%d ~ %H:%M:%S"),
        "level": level,
        "message": message,
        "domain": domain
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
    search: Optional[str] = Query(None, description="Search across all fields (tournament, market, outcome, result, odds, stake, payout)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=50, ge=1, le=1000, description="Items per page")
) -> Dict[str, Any]:
    """Get bet history with optional filtering, search, and pagination."""
    db = get_db()
    offset = (page - 1) * per_page
    
    # If search is provided, fetch more results for client-side filtering
    # Otherwise use normal pagination
    limit = 10000 if search else per_page
    
    bets_df = db.get_bet_history(
        result=result,
        market_name=market_name,
        outcome_name=outcome_name,
        tournament_name=tournament_name,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=0 if search else offset
    )
    
    # Apply search filter if provided
    if search and len(bets_df) > 0:
        import unicodedata
        
        def normalize_text(text: str) -> str:
            """Normalize text by removing accents and converting to lowercase."""
            if not text:
                return ''
            text_lower = text.lower()
            # Remove diacritics (accents)
            normalized = unicodedata.normalize('NFD', text_lower)
            ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
            return ascii_text
        
        search_normalized = normalize_text(search)
        
        def matches_search(row):
            """Check if row matches search query across all relevant fields."""
            fields_to_check = [
                str(row.get('tournament_name', '')),
                str(row.get('market_name', '')),
                str(row.get('outcome_name', '')),
                str(row.get('result', '')),
                str(row.get('odds', '')),
                str(row.get('stake', '')),
                str(row.get('payout', '')),
                str(row.get('model_market', '')),
            ]
            for field in fields_to_check:
                field_normalized = normalize_text(field)
                if search_normalized in field_normalized:
                    return True
            return False
        
        bets_df = bets_df[bets_df.apply(matches_search, axis=1)]
    
    # Apply pagination after search
    if search and len(bets_df) > 0:
        bets_df = bets_df.iloc[offset:offset + per_page]
    
    bets = bets_df.to_dict('records') if len(bets_df) > 0 else []
    
    # Get total count
    if search:
        # For search, count is based on filtered results
        # We already have the full filtered set, just need to count it before pagination
        bets_df_count = db.get_bet_history(
            result=result,
            market_name=market_name,
            outcome_name=outcome_name,
            tournament_name=tournament_name,
            date_from=date_from,
            date_to=date_to,
            limit=10000,
            offset=0
        )
        if len(bets_df_count) > 0:
            import unicodedata
            def normalize_text(text: str) -> str:
                if not text:
                    return ''
                text_lower = text.lower()
                normalized = unicodedata.normalize('NFD', text_lower)
                return normalized.encode('ascii', 'ignore').decode('ascii')
            
            search_normalized = normalize_text(search)
            def matches_search(row):
                fields_to_check = [
                    str(row.get('tournament_name', '')),
                    str(row.get('market_name', '')),
                    str(row.get('outcome_name', '')),
                    str(row.get('result', '')),
                    str(row.get('odds', '')),
                    str(row.get('stake', '')),
                    str(row.get('payout', '')),
                    str(row.get('model_market', '')),
                ]
                for field in fields_to_check:
                    field_normalized = normalize_text(field)
                    if search_normalized in field_normalized:
                        return True
                return False
            bets_df_count = bets_df_count[bets_df_count.apply(matches_search, axis=1)]
            total_count = len(bets_df_count)
        else:
            total_count = 0
    else:
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


@app.get("/api/bets/top-confidence")
async def get_top_confidence_bet(
    sort_by: str = Query(default="confidence", pattern="^(confidence|ev)$", description="Sort by 'confidence' (probability) or 'ev' (expected value)"),
    limit: int = Query(default=1, ge=1, le=10, description="Number of top bets to return")
) -> Dict[str, Any]:
    """
    Get the most confident bet(s) for today.
    
    Queries fixtures for today's date, finds value bets across all active models,
    and returns the top bet(s) sorted by confidence (probability) or expected value.
    """
    db = get_db()
    version_manager = get_versioning()
    markets = ['1x2', 'over_under', 'btts']
    
    # Get today's date
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get fixtures for today
    fixtures = db.get_fixtures(from_date=today, to_date=today)
    
    if len(fixtures) == 0:
        return {
            "bets": [],
            "count": 0,
            "message": "No fixtures found for today"
        }
    
    all_value_bets = []
    
    # Process each market
    for market in markets:
        try:
            # Get active model version
            active_version = version_manager.get_active_version(domain='betting', market=market)
            if not active_version:
                continue
            
            model_path = active_version.get('model_path')
            if not model_path or not Path(model_path).exists():
                continue
            
            # Load model
            predictor = BettingPredictor(market=market)
            predictor.load(model_path)
            
            if not predictor.is_trained:
                continue
            
            # Create value bet engine
            engine = ValueBetEngine(predictor, db, ev_threshold=0.0)  # Use 0 threshold to get all bets
            
            # Find value bets for today's fixtures
            fixture_ids = fixtures['fixture_id'].tolist()
            value_bets = engine.find_value_bets(fixture_ids=fixture_ids, market=market)
            
            if len(value_bets) > 0:
                all_value_bets.append(value_bets)
        
        except Exception as e:
            # Log error but continue with other markets
            continue
    
    if len(all_value_bets) == 0:
        return {
            "bets": [],
            "count": 0,
            "message": "No value bets found for today"
        }
    
    # Combine all value bets
    combined_bets = pd.concat(all_value_bets, ignore_index=True) if len(all_value_bets) > 0 else pd.DataFrame()
    
    if len(combined_bets) == 0:
        return {
            "bets": [],
            "count": 0,
            "message": "No value bets found for today"
        }
    
    # Sort by specified criteria
    if sort_by == "ev":
        combined_bets = combined_bets.sort_values('expected_value', ascending=False)
    else:  # default to confidence (probability)
        combined_bets = combined_bets.sort_values('probability', ascending=False)
    
    # Get top N bets
    top_bets = combined_bets.head(limit)
    
    # Convert to list of dicts and enrich with tournament_name from fixtures
    bets = []
    fixtures_dict = {row['fixture_id']: row for _, row in fixtures.iterrows()}
    
    for _, bet_row in top_bets.iterrows():
        fixture_id = bet_row.get('fixture_id', '')
        fixture_info = fixtures_dict.get(fixture_id, {})
        
        bets.append({
            "fixture_id": fixture_id,
            "home_team": bet_row.get('home_team', ''),
            "away_team": bet_row.get('away_team', ''),
            "start_time": bet_row.get('start_time', ''),
            "market": bet_row.get('market', ''),
            "outcome": bet_row.get('outcome', ''),
            "odds": float(bet_row.get('odds', 0)),
            "probability": float(bet_row.get('probability', 0)),
            "expected_value": float(bet_row.get('expected_value', 0)),
            "bookmaker": bet_row.get('bookmaker', ''),
            "tournament_name": fixture_info.get('tournament_name', '')
        })
    
    return {
        "bets": bets,
        "count": len(bets),
        "sort_by": sort_by
    }


# =============================================================================
# MODELS ENDPOINTS
# =============================================================================

@app.get("/api/models")
async def get_model_versions(
    market: Optional[str] = None
) -> Dict[str, Any]:
    """Get model versions and performance for betting domain."""
    versions = get_versioning().get_all_versions(domain='betting', market=market)
    
    # Parse performance_metrics JSON for each version
    for version in versions:
        perf_metrics_str = version.get('performance_metrics')
        if perf_metrics_str:
            try:
                perf_metrics = json.loads(perf_metrics_str) if isinstance(perf_metrics_str, str) else perf_metrics_str
                version['performance_metrics'] = perf_metrics
                
                # Extract calibration metrics if available
                if isinstance(perf_metrics, dict):
                    version['brier_score'] = perf_metrics.get('brier_score')
                    version['ece'] = perf_metrics.get('ece')
                    version['calibration_improvement'] = perf_metrics.get('calibration_improvement')
            except (json.JSONDecodeError, TypeError):
                version['performance_metrics'] = {}
    
    # Get active versions for each market
    active = {}
    for m in ["1x2", "over_under", "btts"]:
        active_v = get_versioning().get_active_version(domain='betting', market=m)
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
# TRADING ENDPOINTS
# =============================================================================

# Global trading service (lazy initialized)
_trading_service = None


def get_trading_service():
    """Get or create trading service."""
    global _trading_service
    if _trading_service is None:
        from trading.service import TradingService
        _trading_service = TradingService(get_db(), log_callback=lambda level, msg: broadcast_log(level, msg, domain="trading"))
    return _trading_service


@app.post("/api/trading/collect")
async def trigger_trading_collection() -> Dict[str, Any]:
    """Trigger trading data collection (stocks and crypto)."""
    scheduler = get_scheduler()
    result = scheduler.trigger_trading_collection()
    return result


@app.get("/api/trading/status")
async def get_trading_status() -> Dict[str, Any]:
    """Get trading collection status."""
    scheduler = get_scheduler()
    status = scheduler.get_status()
    
    current_task = status.get("current_task", "")
    is_trading_task = current_task in ["trading_collection", "trading_training", "trading_cycle", "trading_full_run"]
    
    return {
        "enabled": config.TRADING_CONFIG.get("enabled", False),
        "current_task": current_task if is_trading_task else None,
        "last_collection": status.get("last_trading_collection"),
        "last_collection_duration_seconds": status.get("last_trading_collection_duration_seconds"),
        "watchlist": config.TRADING_CONFIG.get("watchlist", {}),
        "api_keys_configured": {
            "alpha_vantage": bool(config.TRADING_CONFIG.get("api_keys", {}).get("alpha_vantage")),
            "coingecko": bool(config.TRADING_CONFIG.get("api_keys", {}).get("coingecko"))
        }
    }


@app.post("/api/trading/train")
async def trigger_trading_training() -> Dict[str, Any]:
    """Trigger trading model training."""
    scheduler = get_scheduler()
    result = scheduler.trigger_trading_training()
    return result


@app.post("/api/trading/cycle")
async def trigger_trading_cycle() -> Dict[str, Any]:
    """Trigger trading cycle (signals + execution)."""
    scheduler = get_scheduler()
    result = scheduler.trigger_trading_cycle()
    return result


@app.post("/api/trading/full")
async def trigger_full_trading_cycle() -> Dict[str, Any]:
    """Trigger full trading cycle (collection + training + cycle)."""
    scheduler = get_scheduler()
    result = scheduler.trigger_full_trading_cycle()
    return result


@app.post("/api/trading/daemon/start")
async def start_trading_daemon(request: DaemonStartRequest = DaemonStartRequest()) -> Dict[str, Any]:
    """Start trading daemon mode."""
    scheduler = get_scheduler()
    status = scheduler.get_status()
    
    if status.get("trading_daemon_running"):
        return {
            "success": False,
            "error": "Trading daemon is already running"
        }
    
    # Start daemon in background thread
    def run_daemon():
        try:
            scheduler.start_trading_daemon(interval_seconds=request.interval_seconds)
        except Exception as e:
            broadcast_log("error", f"Trading daemon error: {e}")
    
    thread = threading.Thread(target=run_daemon, daemon=True)
    thread.start()
    
    return {
        "success": True,
        "message": f"Trading daemon started with {request.interval_seconds}s interval"
    }


@app.post("/api/trading/daemon/stop")
async def stop_trading_daemon() -> Dict[str, Any]:
    """Stop trading daemon mode."""
    scheduler = get_scheduler()
    scheduler.stop_trading_daemon()
    return {
        "success": True,
        "message": "Trading daemon stop signal sent"
    }


@app.get("/api/trading/portfolio")
async def get_trading_portfolio() -> Dict[str, Any]:
    """Get portfolio overview."""
    try:
        service = get_trading_service()
        return service.get_portfolio_summary()
    except Exception as e:
        return {
            "cash_balance": 0,
            "portfolio_value": 0,
            "available_cash": 0,
            "positions_count": 0,
            "realized_pnl": 0,
            "unrealized_pnl": 0,
            "total_pnl": 0,
            "error": str(e)
        }


@app.get("/api/trading/positions")
async def get_trading_positions() -> Dict[str, Any]:
    """Get active positions."""
    try:
        service = get_trading_service()
        positions = service.get_positions_detail()
        return {
            "positions": positions,
            "count": len(positions)
        }
    except Exception as e:
        return {
            "positions": [],
            "count": 0,
            "error": str(e)
        }


@app.get("/api/trading/trades")
async def get_trading_trades(
    limit: int = Query(default=50, ge=1, le=500)
) -> Dict[str, Any]:
    """Get trade history."""
    try:
        service = get_trading_service()
        trades = service.get_trade_history(limit=limit)
        return {
            "trades": trades,
            "count": len(trades)
        }
    except Exception as e:
        return {
            "trades": [],
            "count": 0,
            "error": str(e)
        }


@app.get("/api/trading/signals")
async def get_trading_signals(
    limit: int = Query(default=10, ge=1, le=50)
) -> Dict[str, Any]:
    """Get current trading signals."""
    try:
        service = get_trading_service()
        signals = service.get_current_signals(limit=limit)
        return {
            "signals": signals,
            "count": len(signals)
        }
    except Exception as e:
        return {
            "signals": [],
            "count": 0,
            "error": str(e)
        }


@app.get("/api/trading/performance")
async def get_trading_performance() -> Dict[str, Any]:
    """Get trading performance metrics."""
    try:
        service = get_trading_service()
        return service.get_performance()
    except Exception as e:
        return {
            "roi": 0,
            "total_return": 0,
            "win_rate": 0,
            "profit": 0,
            "total_trades": 0,
            "error": str(e)
        }


@app.get("/api/trading/performance/by-strategy")
async def get_trading_performance_by_strategy() -> Dict[str, Any]:
    """Get performance metrics by strategy."""
    try:
        service = get_trading_service()
        return service.get_performance_by_strategy()
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/trading/models")
async def get_trading_models() -> Dict[str, Any]:
    """Get trading model versions/status."""
    try:
        service = get_trading_service()
        models = service.get_model_status()
        # Ensure we return a dict with strategy keys, not an error
        if isinstance(models, dict) and 'error' not in models:
            return models
        # If service returned error or empty, return empty dict with strategies
        return {
            'momentum': {'available': False, 'path': '', 'version': None, 'cv_score': None, 'created_at': None},
            'swing': {'available': False, 'path': '', 'version': None, 'cv_score': None, 'created_at': None},
            'volatility': {'available': False, 'path': '', 'version': None, 'cv_score': None, 'created_at': None}
        }
    except Exception as e:
        # Return empty models dict instead of error
        return {
            'momentum': {'available': False, 'path': '', 'version': None, 'cv_score': None, 'created_at': None},
            'swing': {'available': False, 'path': '', 'version': None, 'cv_score': None, 'created_at': None},
            'volatility': {'available': False, 'path': '', 'version': None, 'cv_score': None, 'created_at': None}
        }


class WatchlistUpdate(BaseModel):
    stocks: Optional[List[str]] = None
    crypto: Optional[List[str]] = None


@app.put("/api/trading/watchlist")
async def update_trading_watchlist(update: WatchlistUpdate) -> Dict[str, Any]:
    """Update trading watchlist."""
    import config
    
    # Load current config
    config_path = Path(__file__).parent.parent / "config" / "config.json"
    with open(config_path, 'r') as f:
        main_config = json.load(f)
    
    # Get current watchlist
    trading_config = main_config.get("trading", {})
    watchlist = trading_config.get("watchlist", {"stocks": [], "crypto": []})
    
    # Update watchlist
    if update.stocks is not None:
        watchlist["stocks"] = update.stocks
    if update.crypto is not None:
        watchlist["crypto"] = update.crypto
    
    trading_config["watchlist"] = watchlist
    main_config["trading"] = trading_config
    
    # Save config
    with open(config_path, 'w') as f:
        json.dump(main_config, f, indent=2)
    
    # Reload config
    config.reload_config()
    
    return {
        "success": True,
        "message": "Watchlist updated",
        "watchlist": watchlist
    }


@app.get("/api/trading/price-history/{symbol}")
async def get_price_history(
    symbol: str,
    limit: int = Query(default=100, ge=1, le=1000)
) -> Dict[str, Any]:
    """Get price history for a symbol."""
    try:
        db = get_db()
        df = db.get_price_history(symbol=symbol, limit=limit)
        
        if df.empty:
            return {
                "symbol": symbol,
                "data": [],
                "count": 0
            }
        
        # Convert to list of dicts
        data = df.to_dict('records')
        
        return {
            "symbol": symbol,
            "data": data,
            "count": len(data)
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "data": [],
            "count": 0,
            "error": str(e)
        }


class ClosePositionRequest(BaseModel):
    symbol: str


@app.post("/api/trading/positions/close")
async def close_trading_position(request: ClosePositionRequest) -> Dict[str, Any]:
    """Manually close a position."""
    try:
        service = get_trading_service()
        result = service.close_position_manual(request.symbol)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


class InitPortfolioRequest(BaseModel):
    starting_balance: Optional[float] = None


@app.post("/api/trading/portfolio/initialize")
async def initialize_trading_portfolio(request: InitPortfolioRequest = InitPortfolioRequest()) -> Dict[str, Any]:
    """Initialize trading portfolio with starting balance."""
    try:
        service = get_trading_service()
        service.initialize_portfolio(request.starting_balance)
        return {
            "success": True,
            "message": "Portfolio initialized"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
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


@app.post("/api/database/reset")
async def reset_database(preserve_models: bool = True) -> Dict[str, Any]:
    """
    Reset current environment database by clearing all data tables.
    
    Args:
        preserve_models: If True, keep model_versions intact
        
    Returns:
        Dict with reset results
    """
    try:
        db = get_db()
        result = db.reset_database(preserve_models=preserve_models)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/database/sync-prod-to-debug")
async def sync_prod_to_debug() -> Dict[str, Any]:
    """
    Sync all data from production database to debug database (one-way).
    
    This copies all production data to debug for testing purposes.
    Clears existing debug data first.
    
    Returns:
        Dict with sync results
    """
    import config as config_module
    from pathlib import Path
    
    # Check if we're in debug mode
    if config_module.ENVIRONMENT != "debug":
        raise HTTPException(
            status_code=400,
            detail="Sync is only available when in debug environment"
        )
    
    # Get production database path
    BASE_DIR = Path(__file__).parent.parent
    production_db_path = str(BASE_DIR / "data" / "arbihawk.db")
    
    if not Path(production_db_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"Production database not found: {production_db_path}"
        )
    
    try:
        db = get_db()
        result = db.sync_from_production(production_db_path)
        
        # Reset global instances to reload data
        global _db, _scheduler, _bankroll, _metrics, _versioning
        _db = None
        _scheduler = None
        _bankroll = None
        _metrics = None
        _versioning = None
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

@app.get("/api/config/environment")
async def get_environment() -> Dict[str, Any]:
    """Get current environment configuration."""
    import config
    return {
        "environment": config.ENVIRONMENT,
        "db_path": config.DB_PATH
    }


class EnvironmentUpdate(BaseModel):
    environment: str  # 'debug' or 'production'


@app.put("/api/config/environment")
async def update_environment(env_update: EnvironmentUpdate) -> Dict[str, Any]:
    """Update environment configuration."""
    if env_update.environment not in ['debug', 'production']:
        raise HTTPException(status_code=400, detail="Environment must be 'debug' or 'production'")
    
    import config as config_module
    
    # Load current config
    config_path = Path(__file__).parent.parent / "config" / "config.json"
    with open(config_path, 'r') as f:
        main_config = json.load(f)
    
    # Update environment
    main_config['environment'] = env_update.environment
    
    # Save config
    with open(config_path, 'w') as f:
        json.dump(main_config, f, indent=2)
    
    # Reload config module
    config_module.reload_config()
    
    # Reset global instances to use new database
    global _db, _scheduler, _bankroll, _metrics, _versioning, _backup
    _db = None
    _scheduler = None
    _bankroll = None
    _metrics = None
    _versioning = None
    _backup = None
    
    return {
        "environment": config_module.ENVIRONMENT,
        "db_path": config_module.DB_PATH,
        "message": f"Environment switched to {env_update.environment}. Database connections reset."
    }


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
