"""
Automation scheduler for data collection and model training.
"""

import time
import subprocess
import threading
import logging
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from collections import deque

from data.database import Database
from data.ingestion import DataIngestionService
from data.matchers import ScoreMatcher
from data.settlement import BetSettlement
from data.backup import DatabaseBackup
from monitoring.metrics import MetricsCollector
import config


class AutomationScheduler:
    """
    Manages scheduled data collection and training cycles.
    
    Features:
    - Cron-based and interval-based scheduling
    - Subprocess execution of scrapers
    - Data ingestion and matching
    - Training with backup
    - Logging and monitoring
    
    Example usage:
        scheduler = AutomationScheduler()
        
        # Run data collection
        result = scheduler.run_collection()
        
        # Run training
        result = scheduler.run_training()
        
        # Start daemon mode
        scheduler.start_daemon()
    """
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.ingestion = DataIngestionService(self.db)
        self.matcher = ScoreMatcher(self.db)
        self.settlement = BetSettlement(self.db)
        self.backup = DatabaseBackup()
        self.metrics = MetricsCollector(self.db)
        
        # Configuration
        self.collection_schedule = config.COLLECTION_SCHEDULE
        self.training_schedule = config.TRAINING_SCHEDULE
        self.scraper_args = config.SCRAPER_ARGS
        
        # State
        self._running = False
        self._stop_event = threading.Event()
        self._logs = deque(maxlen=1000)
        self._current_task = None
        self._last_collection = None
        self._last_training = None
        self._log_callback: Optional[Callable[[str, str], None]] = None
        
        # Scraper paths (relative to arbihawk root)
        self.scrapers_dir = Path(__file__).parent.parent / "scrapers"
        self.betano_script = self.scrapers_dir / "src" / "sportsbooks" / "betano.py"
        self.fbref_script = self.scrapers_dir / "src" / "sports_data" / "fbref.py"
        
        # Scrapers venv Python interpreter
        if platform.system() == "Windows":
            self.scrapers_python = self.scrapers_dir / "venv" / "Scripts" / "python.exe"
        else:
            self.scrapers_python = self.scrapers_dir / "venv" / "bin" / "python"
    
    def set_log_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set a callback function to be called when logs are added.
        
        Args:
            callback: Function that takes (level, message) and handles the log
        """
        self._log_callback = callback
    
    def _log(self, level: str, message: str) -> None:
        """Log a message with timestamp."""
        timestamp = datetime.now().isoformat()
        entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message
        }
        self._logs.append(entry)
        
        # Also print to console
        print(f"[{timestamp}] [{level.upper()}] {message}")
        
        # Call WebSocket broadcast callback if set
        if self._log_callback:
            try:
                self._log_callback(level, message)
            except Exception:
                pass  # Don't let callback errors affect logging
    
    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent logs."""
        return list(self._logs)[-limit:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self._running,
            "current_task": self._current_task,
            "last_collection": self._last_collection,
            "last_training": self._last_training,
            "log_count": len(self._logs)
        }
    
    def run_collection(self) -> Dict[str, Any]:
        """
        Run data collection cycle.
        
        1. Execute Betano scraper
        2. Ingest Betano data
        3. Execute FBref scraper
        4. Ingest FBref data
        5. Match scores to fixtures
        6. Settle bets
        
        Returns:
            Result dict with collection stats
        """
        self._current_task = "collection"
        start_time = time.time()
        
        result = {
            "success": True,
            "betano": {"success": False, "records": 0},
            "fbref": {"success": False, "records": 0},
            "matching": {"matched": 0, "unmatched": 0},
            "settlement": {"settled": 0},
            "errors": []
        }
        
        try:
            # Run Betano scraper
            self._log("info", "Starting Betano scraper...")
            try:
                betano_result = self._run_scraper("betano")
                if not betano_result.get("success"):
                    self._log("error", f"Betano failed: {betano_result.get('error', 'Unknown error')}")
            except Exception as e:
                self._log("error", f"Betano exception: {e}")
                betano_result = {"success": False, "error": str(e), "records": 0}
            result["betano"] = betano_result
            
            if betano_result.get("success"):
                self._log("info", f"Betano: {betano_result.get('records', 0)} records ingested")
            else:
                self._log("error", f"Betano failed: {betano_result.get('error', 'Unknown')}")
                result["errors"].append(f"Betano: {betano_result.get('error', 'Unknown')}")
            
            # Run FBref scraper
            self._log("info", "Starting FBref scraper...")
            try:
                fbref_result = self._run_scraper("fbref")
                if not fbref_result.get("success"):
                    self._log("error", f"FBref failed: {fbref_result.get('error', 'Unknown error')}")
            except Exception as e:
                self._log("error", f"FBref exception: {e}")
                fbref_result = {"success": False, "error": str(e), "records": 0}
            result["fbref"] = fbref_result
            
            if fbref_result.get("success"):
                self._log("info", f"FBref: {fbref_result.get('records', 0)} records ingested")
            else:
                self._log("error", f"FBref failed: {fbref_result.get('error', 'Unknown')}")
                result["errors"].append(f"FBref: {fbref_result.get('error', 'Unknown')}")
            
            # Match scores to fixtures
            self._log("info", "Matching scores to fixtures...")
            # Get unmatched FBref scores and try to match them
            # For now, matching is done during FBref ingestion
            result["matching"] = {"matched": 0, "unmatched": 0}
            
            # Settle pending bets
            self._log("info", "Settling pending bets...")
            settlement_result = self.settlement.settle_pending_bets()
            result["settlement"] = {
                "settled": settlement_result.get("settled", 0),
                "wins": settlement_result.get("wins", 0),
                "losses": settlement_result.get("losses", 0)
            }
            self._log("info", f"Settled {settlement_result.get('settled', 0)} bets")
            
            # Record metrics
            duration_ms = (time.time() - start_time) * 1000
            self.metrics.record_ingestion(
                source="betano",
                records=result["betano"].get("records", 0),
                success=result["betano"].get("success", False),
                duration_ms=duration_ms
            )
            
            self._last_collection = datetime.now().isoformat()
            self._log("info", f"Collection completed in {duration_ms/1000:.1f}s")
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))
            self._log("error", f"Collection failed: {e}")
        
        finally:
            self._current_task = None
        
        return result
    
    def _run_scraper(self, source: str) -> Dict[str, Any]:
        """Run a scraper and ingest its output."""
        if source == "betano":
            script_path = self.betano_script
            args = self.scraper_args.get("betano", [])
        elif source == "fbref":
            script_path = self.fbref_script
            args = self.scraper_args.get("fbref", [])
        else:
            return {"success": False, "error": f"Unknown source: {source}"}
        
        if not script_path.exists():
            return {"success": False, "error": f"Scraper not found: {script_path}"}
        
        # Check if scrapers venv exists
        if not self.scrapers_python.exists():
            return {
                "success": False,
                "error": f"Scrapers venv not found. Run 'Setup: Initialize Scrapers Venv' task first. Expected: {self.scrapers_python}"
            }
        
        # Use scrapers venv Python interpreter
        python_exe = str(self.scrapers_python.resolve())
        script_path_str = str(script_path.resolve())
        
        # Build command as list for proper subprocess handling
        cmd_parts = [python_exe, script_path_str] + args
        
        self._log("info", f"Executing: {' '.join(cmd_parts)}")
        
        # Run scraper and capture output with real-time logging
        result = self.ingestion.ingest_from_subprocess(
            cmd_parts, 
            source, 
            timeout=600,
            log_callback=self._log
        )
        
        if not result.get("success"):
            self._log("error", f"{source.capitalize()} scraper error: {result.get('error', 'Unknown')}")
        else:
            self._log("info", f"{source.capitalize()} scraper completed: {result.get('records', 0)} records")
        
        return result
    
    def run_training(self) -> Dict[str, Any]:
        """
        Run model training cycle.
        
        1. Create database backup
        2. Run training
        3. Save model version
        
        Returns:
            Result dict with training stats
        """
        self._current_task = "training"
        start_time = time.time()
        
        result = {
            "success": False,
            "backup_path": None,
            "markets_trained": 0,
            "errors": []
        }
        
        try:
            # Create backup before training
            self._log("info", "Creating database backup...")
            backup_path = self.backup.create_backup("pre_training")
            result["backup_path"] = backup_path
            
            if backup_path:
                self._log("info", f"Backup created: {backup_path}")
            else:
                self._log("warning", "Backup creation failed")
            
            # Run training
            self._log("info", "Starting model training...")
            
            # Import train module and run
            from train import train_models
            success, metrics = train_models(self.db)
            
            result["success"] = success
            result["metrics"] = metrics
            result["markets_trained"] = metrics.get("trained_count", 0)
            
            if success:
                self._log("info", f"Training completed: {result['markets_trained']} markets trained")
                
                # Record model metrics
                for market, market_metrics in metrics.get("markets", {}).items():
                    if "samples" in market_metrics:
                        self.metrics.record_model(
                            market=market,
                            cv_score=market_metrics.get("cv_score", 0),
                            training_samples=market_metrics.get("samples", 0)
                        )
            else:
                self._log("error", "Training failed")
                result["errors"].append("Training failed")
            
            self._last_training = datetime.now().isoformat()
            
            duration_ms = (time.time() - start_time) * 1000
            self._log("info", f"Training cycle completed in {duration_ms/1000:.1f}s")
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))
            self._log("error", f"Training failed: {e}")
        
        finally:
            self._current_task = None
        
        return result
    
    def run_full_cycle(self) -> Dict[str, Any]:
        """
        Run full automation cycle (collection + training).
        
        Returns:
            Combined result dict
        """
        self._log("info", "Starting full automation cycle...")
        
        collection_result = self.run_collection()
        training_result = self.run_training()
        
        return {
            "collection": collection_result,
            "training": training_result,
            "success": collection_result.get("success", False) and training_result.get("success", False)
        }
    
    def start_daemon(self, interval_seconds: int = 21600) -> None:
        """
        Start scheduler in daemon mode.
        
        Args:
            interval_seconds: Interval between cycles (default: 6 hours)
        """
        if self._running:
            self._log("warning", "Daemon already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        self._log("info", f"Starting daemon mode (interval: {interval_seconds}s)")
        
        while not self._stop_event.is_set():
            try:
                self.run_full_cycle()
            except Exception as e:
                self._log("error", f"Cycle error: {e}")
            
            # Wait for next cycle
            self._stop_event.wait(interval_seconds)
        
        self._running = False
        self._log("info", "Daemon stopped")
    
    def stop_daemon(self) -> None:
        """Stop daemon mode."""
        if not self._running:
            self._log("warning", "Daemon not running")
            return
        
        self._log("info", "Stopping daemon...")
        self._stop_event.set()
    
    def trigger_collection(self) -> Dict[str, Any]:
        """Manually trigger data collection (for dashboard). Runs in background thread."""
        if self._current_task:
            return {"success": False, "error": f"Task already running: {self._current_task}"}
        
        def run_in_background():
            try:
                self.run_collection()
            except Exception as e:
                self._log("error", f"Background collection failed: {e}")
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Collection started in background"}
    
    def trigger_training(self) -> Dict[str, Any]:
        """Manually trigger training (for dashboard). Runs in background thread."""
        if self._current_task:
            return {"success": False, "error": f"Task already running: {self._current_task}"}
        
        def run_in_background():
            try:
                self.run_training()
            except Exception as e:
                self._log("error", f"Background training failed: {e}")
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Training started in background"}
