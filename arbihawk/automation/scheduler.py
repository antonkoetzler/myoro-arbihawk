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
from automation.betting import BettingService
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
        self.betting_service = BettingService(self.db)
        
        # Configuration
        self.collection_schedule = config.COLLECTION_SCHEDULE
        self.training_schedule = config.TRAINING_SCHEDULE
        self.scraper_args = config.SCRAPER_ARGS
        
        # State
        self._running = False
        self._stop_event = threading.Event()  # For daemon mode
        self._stop_task_event = threading.Event()  # For stopping individual tasks
        self._logs = deque(maxlen=1000)
        self._current_task = None
        self._last_collection = None
        self._last_training = None
        self._last_betting = None
        self._log_callback: Optional[Callable[[str, str], None]] = None
        
        # Scraper paths (relative to arbihawk root)
        self.scrapers_dir = Path(__file__).parent.parent / "scrapers"
        self.betano_script = self.scrapers_dir / "src" / "sportsbooks" / "betano.py"
        self.flashscore_script = self.scrapers_dir / "src" / "sports_data" / "flashscore.py"
        self.livescore_script = self.scrapers_dir / "src" / "sports_data" / "livescore.py"
        
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
            "last_betting": getattr(self, '_last_betting', None),
            "log_count": len(self._logs)
        }
    
    def run_collection(self) -> Dict[str, Any]:
        """
        Run data collection cycle.
        
        1. Execute Betano scraper
        2. Ingest Betano data
        3. Execute Flashscore scraper (primary)
        4. Ingest Flashscore data
        5. Execute Livescore scraper (fallback if Flashscore fails)
        6. Ingest Livescore data
        7. Match scores to fixtures
        8. Settle bets
        
        Returns:
            Result dict with collection stats
        """
        self._current_task = "collection"
        self._stop_task_event.clear()  # Reset stop flag
        start_time = time.time()
        
        result = {
            "success": True,
            "betano": {"success": False, "records": 0},
            "flashscore": {"success": False, "records": 0},
            "livescore": {"success": False, "records": 0},
            "matching": {"matched": 0, "unmatched": 0},
            "settlement": {"settled": 0},
            "errors": []
        }
        
        try:
            # Check if stopped
            if self._stop_task_event.is_set():
                self._log("info", "Collection stopped by user")
                result["stopped"] = True
                return result
            
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
                self._log("success", f"✓ Betano completed: {betano_result.get('records', 0)} records ingested")
            else:
                self._log("error", f"Betano failed: {betano_result.get('error', 'Unknown')}")
                result["errors"].append(f"Betano: {betano_result.get('error', 'Unknown')}")
            
            # Check if stopped
            if self._stop_task_event.is_set():
                self._log("info", "Collection stopped by user after Betano")
                result["stopped"] = True
                return result
            
            # Run Flashscore scraper (primary)
            self._log("info", "Starting Flashscore scraper...")
            try:
                flashscore_result = self._run_scraper("flashscore")
                if not flashscore_result.get("success"):
                    self._log("error", f"Flashscore failed: {flashscore_result.get('error', 'Unknown error')}")
            except Exception as e:
                self._log("error", f"Flashscore exception: {e}")
                flashscore_result = {"success": False, "error": str(e), "records": 0}
            result["flashscore"] = flashscore_result
            
            if flashscore_result.get("success"):
                self._log("success", f"✓ Flashscore completed: {flashscore_result.get('records', 0)} records ingested")
            else:
                self._log("warning", f"Flashscore failed: {flashscore_result.get('error', 'Unknown')}")
                result["errors"].append(f"Flashscore: {flashscore_result.get('error', 'Unknown')}")
            
            # Check if stopped
            if self._stop_task_event.is_set():
                self._log("info", "Collection stopped by user after Flashscore")
                result["stopped"] = True
                return result
            
            # Run Livescore scraper (fallback if Flashscore failed)
            if not flashscore_result.get("success"):
                self._log("info", "Flashscore failed, trying Livescore as fallback...")
                try:
                    livescore_result = self._run_scraper("livescore")
                    if not livescore_result.get("success"):
                        self._log("error", f"Livescore failed: {livescore_result.get('error', 'Unknown error')}")
                except Exception as e:
                    self._log("error", f"Livescore exception: {e}")
                    livescore_result = {"success": False, "error": str(e), "records": 0}
                result["livescore"] = livescore_result
                
                if livescore_result.get("success"):
                    self._log("success", f"✓ Livescore completed: {livescore_result.get('records', 0)} records ingested")
                else:
                    self._log("error", f"Livescore failed: {livescore_result.get('error', 'Unknown')}")
                    result["errors"].append(f"Livescore: {livescore_result.get('error', 'Unknown')}")
            else:
                # Flashscore succeeded, skip Livescore
                result["livescore"] = {"success": False, "records": 0, "skipped": True, "reason": "Flashscore succeeded"}
            
            # Check if stopped
            if self._stop_task_event.is_set():
                self._log("info", "Collection stopped by user after score scrapers")
                result["stopped"] = True
                return result
            
            # Match scores to fixtures
            self._log("info", "Matching scores to fixtures...")
            # Matching is done during score ingestion, but run batch matching for any unmatched
            try:
                from data.matchers import ScoreMatcher
                matcher = ScoreMatcher(self.db)
                
                # Get all unmatched scores (scores with fixture_ids not in fixtures)
                all_scores = self.db.get_scores()
                fixtures = self.db.get_fixtures()
                fixture_ids_set = set(fixtures['fixture_id'].tolist())
                unmatched = all_scores[~all_scores['fixture_id'].isin(fixture_ids_set)]
                
                # Clean up old fbref scores that can't be matched (they have no team info)
                old_unmatched = unmatched[unmatched['fixture_id'].str.startswith('fbref_', na=False)]
                if len(old_unmatched) > 0:
                    self._log("info", f"Cleaning up {len(old_unmatched)} old unmatched fbref scores...")
                    with self.db._get_connection() as conn:
                        cursor = conn.cursor()
                        # Use executemany for better performance
                        temp_ids = [(tid,) for tid in old_unmatched['fixture_id']]
                        cursor.executemany("DELETE FROM scores WHERE fixture_id = ?", temp_ids)
                    self._log("info", f"Removed {len(old_unmatched)} old unmatched scores")
                
                # Count remaining unmatched
                remaining_unmatched = len(unmatched) - len(old_unmatched)
                matched_count = len(all_scores) - len(unmatched)
                
                result["matching"] = {
                    "matched": matched_count,
                    "unmatched": remaining_unmatched,
                    "cleaned_old": len(old_unmatched)
                }
                self._log("info", f"Score matching: {matched_count} matched, {remaining_unmatched} unmatched")
            except Exception as e:
                self._log("error", f"Error during batch matching: {e}")
                result["matching"] = {"matched": 0, "unmatched": 0, "error": str(e)}
            
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
            # Record score scraper metrics
            if result["flashscore"].get("success"):
                self.metrics.record_ingestion(
                    source="flashscore",
                    records=result["flashscore"].get("records", 0),
                    success=True,
                    duration_ms=duration_ms
                )
            elif result.get("livescore", {}).get("success"):
                self.metrics.record_ingestion(
                    source="livescore",
                    records=result["livescore"].get("records", 0),
                    success=True,
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
        elif source == "flashscore":
            script_path = self.flashscore_script
            args = self.scraper_args.get("flashscore", ["--headless"])
        elif source == "livescore":
            script_path = self.livescore_script
            args = self.scraper_args.get("livescore", ["--no-proxy"])
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
            timeout=None,
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
        self._stop_task_event.clear()  # Reset stop flag
        start_time = time.time()
        
        result = {
            "success": False,
            "backup_path": None,
            "markets_trained": 0,
            "has_data": False,
            "errors": []
        }
        
        try:
            # Check if stopped
            if self._stop_task_event.is_set():
                self._log("info", "Training stopped by user")
                result["stopped"] = True
                return result
            
            # Create backup before training
            self._log("info", "Creating database backup...")
            backup_path = self.backup.create_backup("pre_training")
            result["backup_path"] = backup_path
            
            if backup_path:
                self._log("info", f"Backup created: {backup_path}")
            else:
                self._log("warning", "Backup creation failed")
            
            # Check if stopped
            if self._stop_task_event.is_set():
                self._log("info", "Training stopped by user")
                result["stopped"] = True
                return result
            
            # Run training
            self._log("info", "Starting model training...")
            
            # Import train module and run
            from train import train_models
            success, metrics = train_models(self.db)
            
            result["success"] = success
            result["metrics"] = metrics
            result["markets_trained"] = metrics.get("trained_count", 0)
            result["has_data"] = metrics.get("has_data", False)
            
            # Handle training result based on new logic
            # success=True means no errors, but may still have no data
            if success:
                if metrics.get("has_data"):
                    # Models were actually trained
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
                    # No data available for training - this is a warning, not an error
                    no_data_reason = metrics.get("no_data_reason", "No training data available")
                    self._log("warning", f"Training completed but no models trained: {no_data_reason}")
            else:
                # Actual errors occurred during training
                training_errors = metrics.get("errors", [])
                error_msg = "; ".join(training_errors) if training_errors else "Unknown error"
                self._log("error", f"Training failed: {error_msg}")
                result["errors"].extend(training_errors)
            
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
    
    def stop_task(self) -> Dict[str, Any]:
        """Stop the currently running task (collection or training)."""
        if not self._current_task:
            return {"success": False, "message": "No task is currently running"}
        
        task_name = self._current_task
        self._log("info", f"Stopping {task_name}...")
        self._stop_task_event.set()
        
        return {"success": True, "message": f"Stop signal sent to {task_name}"}
    
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
    def run_betting(self) -> Dict[str, Any]:
        """
        Run betting cycle.
        
        Places bets using active models if fake money is enabled
        and auto_bet_after_training is enabled.
        
        Returns:
            Result dict with betting stats
        """
        self._current_task = "betting"
        self._stop_task_event.clear()
        start_time = time.time()
        
        result = {
            "success": False,
            "bets_placed": 0,
            "total_stake": 0.0,
            "by_model": {},
            "errors": []
        }
        
        try:
            # Check if stopped
            if self._stop_task_event.is_set():
                self._log("info", "Betting stopped by user")
                result["stopped"] = True
                return result
            
            # Check if fake money is enabled
            if not config.FAKE_MONEY_CONFIG.get("enabled", False):
                self._log("info", "Fake money is disabled, skipping betting")
                result["success"] = True
                result["skipped"] = True
                result["reason"] = "Fake money disabled"
                return result
            
            # Check if auto-betting is enabled
            if not config.AUTO_BET_AFTER_TRAINING:
                self._log("info", "Auto-betting after training is disabled, skipping betting")
                result["success"] = True
                result["skipped"] = True
                result["reason"] = "Auto-betting disabled"
                return result
            
            # Check if stopped
            if self._stop_task_event.is_set():
                self._log("info", "Betting stopped by user")
                result["stopped"] = True
                return result
            
            # Run betting
            self._log("info", "Starting betting cycle...")
            betting_result = self.betting_service.place_bets_for_all_models(limit_per_model=10)
            
            result["success"] = betting_result.get("success", False)
            result["bets_placed"] = betting_result.get("total_bets_placed", 0)
            result["total_stake"] = betting_result.get("total_stake", 0.0)
            result["by_model"] = betting_result.get("by_model", {})
            result["errors"] = betting_result.get("errors", [])
            
            if result["success"]:
                if result["bets_placed"] > 0:
                    self._log("success", f"✓ Betting completed: {result['bets_placed']} bets placed, ${result['total_stake']:.2f} total stake")
                else:
                    self._log("info", "Betting completed: No value bets found")
            else:
                error_msg = "; ".join(result["errors"]) if result["errors"] else "Unknown error"
                self._log("error", f"Betting failed: {error_msg}")
            
            self._last_betting = datetime.now().isoformat()
            
            duration_ms = (time.time() - start_time) * 1000
            self._log("info", f"Betting cycle completed in {duration_ms/1000:.1f}s")
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))
            self._log("error", f"Betting failed: {e}")
        
        finally:
            self._current_task = None
        
        return result
    
    def trigger_betting(self) -> Dict[str, Any]:
        """Manually trigger betting (for dashboard). Runs in background thread."""
        if self._current_task:
            return {"success": False, "error": f"Task already running: {self._current_task}"}
        
        def run_in_background():
            try:
                self.run_betting()
            except Exception as e:
                self._log("error", f"Background betting failed: {e}")
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Betting started in background"}

