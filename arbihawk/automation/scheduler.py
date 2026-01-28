"""
Automation scheduler for data collection and model training.
"""

import time
import subprocess
import threading
import platform
import json
import sys
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

# Thread-local storage for domain context
# This ensures each thread (betting vs trading) has its own domain
_thread_local = threading.local()

from data.database import Database
from data.ingestion import DataIngestionService
from data.stock_ingestion import StockIngestionService
from data.crypto_ingestion import CryptoIngestionService
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
        self.betting_service = BettingService(self.db, log_callback=self._log)
        
        # Trading services (lazy initialization)
        self._ingestion_service: Optional[DataIngestionService] = None
        self._stock_service = None
        self._crypto_service = None
        
        # Trading state
        self._last_trading_collection = None
        self._last_trading_collection_duration = None
        
        # Configuration
        self.collection_schedule = config.COLLECTION_SCHEDULE
        self.training_schedule = config.TRAINING_SCHEDULE
        self.scraper_args = config.SCRAPER_ARGS
        self.scraper_workers = config.SCRAPER_WORKERS
        
        # State
        self._running = False
        self._trading_daemon_running = False
        self._stop_event = threading.Event()  # For daemon mode
        self._trading_daemon_stop_event = threading.Event()  # For trading daemon mode
        self._stop_task_event = threading.Event()  # For stopping individual tasks
        self._logs = deque(maxlen=1000)
        self._current_task = None
        # Note: _current_domain is now stored in thread-local storage to prevent
        # race conditions when betting and trading run in parallel
        self._last_collection = None
        self._last_training = None
        self._last_betting = None
        self._log_callback: Optional[Callable[[str, str, str], None]] = None  # Updated to accept domain
        
        # Performance metrics
        self._last_collection_duration = None
        self._last_training_duration = None
        self._last_betting_duration = None
        self._last_full_run_duration = None
        self._scraper_durations: Dict[str, float] = {}
        
        # Scraper paths (relative to arbihawk root)
        self.scrapers_dir = Path(__file__).parent.parent / "scrapers"
        self.betano_script = self.scrapers_dir / "src" / "sportsbooks" / "betano.py"
        self.flashscore_script = self.scrapers_dir / "src" / "sports_data" / "flashscore.py"
        self.livescore_script = self.scrapers_dir / "src" / "sports_data" / "livescore.py"
        self.stocks_script = self.scrapers_dir / "src" / "stocks" / "stock_scraper.py"
        self.crypto_script = self.scrapers_dir / "src" / "crypto" / "crypto_scraper.py"
        
        # Scrapers venv Python interpreter
        if platform.system() == "Windows":
            self.scrapers_python = self.scrapers_dir / "venv" / "Scripts" / "python.exe"
        else:
            self.scrapers_python = self.scrapers_dir / "venv" / "bin" / "python"
    
    def set_log_callback(self, callback: Callable[[str, str, str], None]) -> None:
        """Set a callback function to be called when logs are added.
        
        Args:
            callback: Function that takes (level, message, domain) and handles the log
        """
        self._log_callback = callback
    
    def _get_current_domain(self) -> str:
        """Get current domain from thread-local storage."""
        return getattr(_thread_local, 'domain', 'betting')
    
    def _set_current_domain(self, domain: str) -> None:
        """Set current domain in thread-local storage."""
        _thread_local.domain = domain
    
    def _log(self, level: str, message: str, domain: Optional[str] = None) -> None:
        """Log a message with timestamp and domain.
        
        Args:
            level: Log level (info, warning, error, success)
            message: Log message
            domain: Domain identifier (betting, trading). If None, uses thread-local domain.
        """
        # Use provided domain or fall back to thread-local domain (safe for parallel execution)
        log_domain = domain if domain is not None else self._get_current_domain()
        
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d ~ %H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "domain": log_domain
        }
        self._logs.append(entry)
        
        # Also print to console with domain prefix
        # Handle encoding errors on Windows (charmap can't encode emojis)
        try:
            domain_prefix = f"[{log_domain.upper()}]" if log_domain else ""
            print(f"[{timestamp}] {domain_prefix} [{level.upper()}] {message}")
        except (UnicodeEncodeError, UnicodeDecodeError):
            # If message contains characters that can't be encoded, sanitize it
            try:
                safe_message = message.encode('ascii', errors='replace').decode('ascii')
                domain_prefix = f"[{log_domain.upper()}]" if log_domain else ""
                print(f"[{timestamp}] {domain_prefix} [{level.upper()}] {safe_message}")
            except:
                # Last resort: just print a generic message
                print(f"[{timestamp}] [{level.upper()}] [ENCODING ERROR: Message contains unsupported characters]")
        
        # Call WebSocket broadcast callback if set
        # IMPORTANT: Always pass domain - no fallback to 2-arg call
        if self._log_callback:
            try:
                # Domain is REQUIRED for proper log separation
                self._log_callback(level, message, log_domain)
            except Exception as e:
                # Log the error but don't crash
                try:
                    print(f"[ERROR] Log callback failed: {e}. Domain: {log_domain}, Message: {message[:50]}")
                except:
                    pass  # Don't let callback errors affect logging
    
    def _store_run_history(self, run_type: str, started_at: datetime,
                          result: Dict[str, Any]) -> None:
        """
        Store run history in database.
        
        Args:
            run_type: Type of run (collection, training, betting, etc.)
            started_at: Datetime when run started
            result: Result dictionary from the run
        """
        try:
            completed_at = datetime.now().isoformat()
            duration = result.get("duration_seconds")
            if duration is None and "start_time" in result:
                # Calculate duration if not provided
                duration = (datetime.now() - started_at).total_seconds()
            
            self.db.insert_run_history(
                run_type=run_type,
                domain=self._get_current_domain(),
                started_at=started_at.isoformat(),
                completed_at=completed_at,
                duration_seconds=duration,
                success=result.get("success", False),
                stopped=result.get("stopped", False),
                skipped=result.get("skipped", False),
                skip_reason=result.get("reason"),
                result_data=result,
                errors=result.get("errors", [])
            )
        except Exception as e:
            # Don't let run history storage failures break the run
            self._log("warning", f"Failed to store run history: {e}")
    
    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent logs."""
        return list(self._logs)[-limit:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self._running,
            "trading_daemon_running": self._trading_daemon_running,
            "current_task": self._current_task,
            "last_collection": self._last_collection,
            "last_training": self._last_training,
            "last_betting": getattr(self, '_last_betting', None),
            "last_trading_collection": self._last_trading_collection,
            "log_count": len(self._logs),
            # Performance metrics
            "last_collection_duration_seconds": self._last_collection_duration,
            "last_training_duration_seconds": self._last_training_duration,
            "last_betting_duration_seconds": self._last_betting_duration,
            "last_full_run_duration_seconds": self._last_full_run_duration,
            "last_trading_collection_duration_seconds": self._last_trading_collection_duration,
            "scraper_durations_seconds": self._scraper_durations.copy()
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
            
            # Run Betano scraper in parallel mode
            self._log("info", "=" * 60)
            self._log("info", "Starting Betano scraper (PARALLEL MODE)...")
            self._log("info", f"Workers: {self.scraper_workers.get('max_workers_leagues', 5)}")
            self._log("info", "=" * 60)
            betano_start = time.time()
            try:
                betano_result = self._run_scraper_parallel("betano")
                if not betano_result.get("success"):
                    self._log("error", f"Betano failed: {betano_result.get('error', 'Unknown error')}")
            except Exception as e:
                self._log("error", f"Betano exception: {e}")
                betano_result = {"success": False, "error": str(e), "records": 0}
            betano_duration = time.time() - betano_start
            self._scraper_durations["betano"] = betano_duration
            result["betano"] = betano_result
            result["betano"]["duration_seconds"] = betano_duration
            
            if betano_result.get("success"):
                self._log("success", f"✓ Betano completed: {betano_result.get('records', 0)} records in {betano_duration/60:.1f} min")
            else:
                self._log("error", f"Betano failed: {betano_result.get('error', 'Unknown')}")
                result["errors"].append(f"Betano: {betano_result.get('error', 'Unknown')}")
            
            # Check if stopped
            if self._stop_task_event.is_set():
                self._log("info", "Collection stopped by user after Betano")
                result["stopped"] = True
                return result
            
            # Run Flashscore scraper in parallel mode
            self._log("info", "=" * 60)
            self._log("info", "Starting Flashscore scraper (PARALLEL MODE)...")
            playwright_workers = self.scraper_workers.get('max_workers_leagues_playwright', 3)
            odds_workers = self.scraper_workers.get('max_workers_odds', 5)
            self._log("info", f"Workers: {playwright_workers} leagues, {odds_workers} odds")
            self._log("info", "=" * 60)
            flashscore_start = time.time()
            try:
                flashscore_result = self._run_scraper_parallel("flashscore")
                if not flashscore_result.get("success"):
                    self._log("error", f"Flashscore failed: {flashscore_result.get('error', 'Unknown error')}")
            except Exception as e:
                self._log("error", f"Flashscore exception: {e}")
                flashscore_result = {"success": False, "error": str(e), "records": 0}
            flashscore_duration = time.time() - flashscore_start
            self._scraper_durations["flashscore"] = flashscore_duration
            result["flashscore"] = flashscore_result
            result["flashscore"]["duration_seconds"] = flashscore_duration
            
            if flashscore_result.get("success"):
                self._log("success", f"✓ Flashscore completed: {flashscore_result.get('records', 0)} records in {flashscore_duration/60:.1f} min")
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
                livescore_start = time.time()
                try:
                    livescore_result = self._run_scraper("livescore")
                    if not livescore_result.get("success"):
                        self._log("error", f"Livescore failed: {livescore_result.get('error', 'Unknown error')}")
                except Exception as e:
                    self._log("error", f"Livescore exception: {e}")
                    livescore_result = {"success": False, "error": str(e), "records": 0}
                livescore_duration = time.time() - livescore_start
                self._scraper_durations["livescore"] = livescore_duration
                result["livescore"] = livescore_result
                result["livescore"]["duration_seconds"] = livescore_duration
                
                if livescore_result.get("success"):
                    self._log("success", f"✓ Livescore completed: {livescore_result.get('records', 0)} records in {livescore_duration:.1f}s")
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
            self._last_collection_duration = duration_ms / 1000
            result["duration_seconds"] = self._last_collection_duration
            self._log("info", f"Collection completed in {duration_ms/1000/60:.1f} minutes")
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))
            self._log("error", f"Collection failed: {e}")
        
        finally:
            # Store run history before clearing task
            try:
                self._store_run_history("collection", started_at, result)
            except Exception:
                pass  # Don't let history storage break the run
            self._current_task = None
        
        return result
    
    def _discover_betano_leagues(self) -> List[int]:
        """Discover all Betano league IDs by running a quick discovery."""
        import os
        try:
            script_path = self.betano_script
            python_exe = str(self.scrapers_python.resolve())
            
            # Run a quick Python script to discover leagues
            discover_code = f"""
import sys
import json
sys.path.insert(0, r'{script_path.parent.parent}')
from sportsbooks.betano import BetanoScraper
scraper = BetanoScraper(delay=0.5)
leagues = scraper.discover_leagues()
league_ids = [l['id'] for l in leagues]
print(json.dumps(league_ids))
"""
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            
            result = subprocess.run(
                [python_exe, "-c", discover_code],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(script_path.parent.parent),
                env=env
            )
            
            if result.returncode == 0 and result.stdout.strip():
                league_ids = json.loads(result.stdout.strip())
                return league_ids
        except Exception as e:
            self._log("warning", f"Failed to discover Betano leagues: {e}")
        
        return []
    
    def _discover_flashscore_leagues(self) -> List[str]:
        """Discover all FlashScore league names from config."""
        try:
            # Use importlib to properly load the module from scrapers directory
            league_config_path = self.scrapers_dir / "src" / "shared" / "league_config.py"
            if not league_config_path.exists():
                self._log("warning", f"League config not found at {league_config_path}")
                return []
            
            spec = importlib.util.spec_from_file_location("shared.league_config", league_config_path)
            if spec is None or spec.loader is None:
                self._log("warning", "Failed to load league_config module spec")
                return []
            
            league_config_module = importlib.util.module_from_spec(spec)
            # Add scrapers src to path for any relative imports in the module
            scrapers_src = str(self.scrapers_dir / "src")
            if scrapers_src not in sys.path:
                sys.path.insert(0, scrapers_src)
            try:
                spec.loader.exec_module(league_config_module)
                get_flashscore_leagues = league_config_module.get_flashscore_leagues
                leagues = get_flashscore_leagues()
                return list(leagues.keys())
            finally:
                # Clean up path
                if scrapers_src in sys.path:
                    sys.path.remove(scrapers_src)
        except Exception as e:
            self._log("warning", f"Failed to discover FlashScore leagues: {e}")
            return []
    
    def _run_single_league_scraper(
        self, 
        source: str, 
        league_identifier: str,
        max_workers_odds: int = 15,
        worker_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run scraper for a single league.
        
        Args:
            source: "betano" or "flashscore"
            league_identifier: League ID (for Betano) or league name (for FlashScore)
            max_workers_odds: Max workers for odds fetching (FlashScore only)
            
        Returns:
            Result dict with success status and records
        """
        if source == "betano":
            script_path = self.betano_script
            args = list(self.scraper_args.get("betano", []))
            args.extend(["--league-id", str(league_identifier)])
        elif source == "flashscore":
            script_path = self.flashscore_script
            args = list(self.scraper_args.get("flashscore", ["--headless"]))
            args.extend([
                "--league", league_identifier,
                "--max-workers-odds", str(max_workers_odds),
                "--market-types", "HOME_DRAW_AWAY", "OVER_UNDER", "BOTH_TEAMS_TO_SCORE"
            ])
        else:
            return {"success": False, "error": f"Unknown source: {source}"}
        
        if not script_path.exists():
            return {"success": False, "error": f"Scraper not found: {script_path}"}
        
        if not self.scrapers_python.exists():
            return {
                "success": False,
                "error": f"Scrapers venv not found: {self.scrapers_python}"
            }
        
        python_exe = str(self.scrapers_python.resolve())
        script_path_str = str(script_path.resolve())
        cmd_parts = [python_exe, script_path_str] + args
        
        # Run scraper and capture output with worker_id
        result = self.ingestion.ingest_from_subprocess(
            cmd_parts,
            source,
            timeout=None,
            log_callback=self._log,
            stop_event=self._stop_task_event,
            worker_id=worker_id
        )
        
        # Completion logging is handled in _run_scraper_parallel
        
        return result
    
    def _run_scraper_parallel(self, source: str) -> Dict[str, Any]:
        """Run scraper in parallel mode - multiple workers calling scraper per league.
        
        Args:
            source: "betano" or "flashscore"
            
        Returns:
            Result dict with collection stats
        """
        import os
        # Use playwright workers for FlashScore (browser-based), regular workers for Betano
        if source == "flashscore":
            max_workers = self.scraper_workers.get("max_workers_leagues_playwright", 3)
        else:
            max_workers = self.scraper_workers.get("max_workers_leagues", 5)
        max_workers_odds = self.scraper_workers.get("max_workers_odds", 5)
        
        self._log("info", f"Starting parallel {source} scraping with {max_workers} workers...")
        
        # Discover leagues
        if source == "betano":
            leagues = self._discover_betano_leagues()
            if not leagues:
                # Fallback to old method if discovery fails
                self._log("warning", "League discovery failed, falling back to sequential mode")
                return self._run_scraper("betano")
        elif source == "flashscore":
            leagues = self._discover_flashscore_leagues()
            if not leagues:
                self._log("error", "No FlashScore leagues found")
                return {"success": False, "error": "No leagues found", "records": 0}
        else:
            return {"success": False, "error": f"Unknown source: {source}", "records": 0}
        
        self._log("info", f"Discovered {len(leagues)} {source} leagues")
        self._log("info", f"Starting {max_workers} parallel workers to process leagues...")
        
        # Use ThreadPoolExecutor to run multiple scraper instances in parallel
        all_results = []
        failed_leagues = []
        total_records = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all league scraping tasks with worker IDs
            self._log("info", f"Submitting {len(leagues)} league scraping tasks to worker pool...")
            futures = {
                executor.submit(
                    self._run_single_league_scraper,
                    source,
                    league,
                    max_workers_odds,
                    (idx % max_workers) + 1  # Worker ID cycles 1-5
                ): (league, (idx % max_workers) + 1)
                for idx, league in enumerate(leagues)
            }
            self._log("info", f"All tasks submitted - {max_workers} workers processing leagues in parallel")
            
            completed = 0
            for future in as_completed(futures):
                league, worker_id = futures[future]
                if self._stop_task_event.is_set():
                    self._log("info", f"Stopping {source} scraping...")
                    # Cancel remaining futures
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    break
                
                try:
                    result = future.result()
                    completed += 1
                    
                    if result.get("success"):
                        records = result.get("records", 0)
                        total_records += records
                        all_results.append(result)
                        self._log("info", f"[WORKER #{worker_id}] [{source.upper()}] Completed: {league} - {records} records ({completed}/{len(leagues)})")
                    else:
                        failed_leagues.append(league)
                        error = result.get("error", "Unknown")
                        self._log("warning", f"[WORKER #{worker_id}] [{source.upper()}] Failed: {league} - {error}")
                except Exception as e:
                    failed_leagues.append(league)
                    self._log("error", f"[WORKER #{worker_id}] [{source.upper()}] Exception: {league} - {e}")
        
        success = len(all_results) > 0
        self._log("info", f"{source} parallel scraping complete: {completed}/{len(leagues)} leagues, {total_records} total records")
        
        return {
            "success": success,
            "records": total_records,
            "leagues_processed": completed,
            "leagues_total": len(leagues),
            "failed_leagues": failed_leagues
        }
    
    def _run_scraper(self, source: str) -> Dict[str, Any]:
        """Run a scraper in sequential mode (legacy, for Livescore and fallback)."""
        if source == "betano":
            script_path = self.betano_script
            args = self.scraper_args.get("betano", [])
        elif source == "flashscore":
            script_path = self.flashscore_script
            args = list(self.scraper_args.get("flashscore", ["--headless"]))
        elif source == "livescore":
            script_path = self.livescore_script
            args = self.scraper_args.get("livescore", ["--no-proxy"])
        else:
            return {"success": False, "error": f"Unknown source: {source}"}
        
        if not script_path.exists():
            return {"success": False, "error": f"Scraper not found: {script_path}"}
        
        if not self.scrapers_python.exists():
            return {
                "success": False,
                "error": f"Scrapers venv not found: {self.scrapers_python}"
            }
        
        python_exe = str(self.scrapers_python.resolve())
        script_path_str = str(script_path.resolve())
        cmd_parts = [python_exe, script_path_str] + args
        
        self._log("info", f"Executing: {' '.join(cmd_parts)}")
        
        result = self.ingestion.ingest_from_subprocess(
            cmd_parts,
            source,
            timeout=None,
            log_callback=self._log,
            stop_event=self._stop_task_event
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
        self._set_current_domain("betting")  # Betting training
        self._stop_task_event.clear()  # Reset stop flag
        start_time = time.time()
        started_at = datetime.now()
        
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
            
            # Check if stopped before training
            if self._stop_task_event.is_set():
                self._log("info", "Training stopped by user before starting")
                result["stopped"] = True
                return result
            
            # Import train module and run
            from train import train_models
            success, metrics = train_models(self.db, log_callback=self._log)
            
            # Check if stopped after training
            if self._stop_task_event.is_set():
                self._log("info", "Training stopped by user after completion")
                result["stopped"] = True
                return result
            
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
            self._last_training_duration = duration_ms / 1000
            result["duration_seconds"] = self._last_training_duration
            self._log("info", f"Training cycle completed in {duration_ms/1000:.1f}s")
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))
            self._log("error", f"Training failed: {e}")
        
        finally:
            # Store run history before clearing task
            try:
                self._store_run_history("training", started_at, result)
            except Exception:
                pass  # Don't let history storage break the run
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
    
    def run_full_with_betting(self) -> Dict[str, Any]:
        """
        Run full cycle with betting: collection + training + betting.
        
        Returns:
            Combined result dict
        """
        # Store the original task name if we're being called as part of a full_run
        original_task = self._current_task
        original_domain = self._get_current_domain()
        was_full_run = original_task == "full_run"
        if not was_full_run:
            self._current_task = "full_run"
            self._set_current_domain("betting")  # Betting full run
        
        self._log("info", "Starting full cycle with betting...")
        full_run_start = time.time()
        started_at = datetime.now()
        
        try:
            # Temporarily restore full_run task name before each phase
            # (nested tasks will set their own, but we want to restore full_run after)
            collection_result = self.run_collection()
            if was_full_run:
                self._current_task = "full_run"
                self._set_current_domain("betting")
            
            # Log collection completion
            if collection_result.get("success"):
                self._log("success", "Collection phase completed successfully")
            else:
                self._log("warning", "Collection phase completed with errors")
            
            # Check if stopped
            if self._stop_task_event.is_set():
                return {
                    "collection": collection_result,
                    "training": {"success": False, "skipped": True, "reason": "Stopped"},
                    "betting": {"success": False, "skipped": True, "reason": "Stopped"},
                    "success": False,
                    "stopped": True
                }
            
            # Log transition to training
            self._log("info", "=" * 60)
            self._log("info", "Starting Training phase...")
            self._log("info", "=" * 60)
            
            training_result = self.run_training()
            if was_full_run:
                self._current_task = "full_run"
                self._set_current_domain("betting")
            
            # Log training completion
            if training_result.get("success"):
                self._log("success", "Training phase completed successfully")
            else:
                self._log("warning", "Training phase completed with errors")
            
            # Check if stopped
            if self._stop_task_event.is_set():
                return {
                    "collection": collection_result,
                    "training": training_result,
                    "betting": {"success": False, "skipped": True, "reason": "Stopped"},
                    "success": False,
                    "stopped": True
                }
            
            # Log transition to betting
            self._log("info", "=" * 60)
            self._log("info", "Starting Betting phase...")
            self._log("info", "=" * 60)
            
            # For full run, require auto_bet_after_training to be enabled
            betting_result = self.run_betting(require_auto_betting=True)
            if was_full_run:
                self._current_task = "full_run"
                self._set_current_domain("betting")
            
            # Log betting completion
            if betting_result.get("success"):
                if betting_result.get("skipped"):
                    self._log("info", f"Betting phase skipped: {betting_result.get('reason', 'Unknown')}")
                else:
                    self._log("success", "Betting phase completed successfully")
            else:
                self._log("warning", "Betting phase completed with errors")
            
            # Settle any pending bets that now have scores available
            # (bets placed during this run might have scores from collection phase)
            if not self._stop_task_event.is_set():
                self._log("info", "Settling pending bets...")
                settlement_result = self.settlement.settle_pending_bets()
                if settlement_result.get("settled", 0) > 0:
                    self._log("info", f"Settled {settlement_result.get('settled', 0)} bets")
            
            full_run_duration = time.time() - full_run_start
            self._last_full_run_duration = full_run_duration
            self._log("success", f"Full run completed in {full_run_duration/60:.1f} minutes")
            
            return {
                "collection": collection_result,
                "training": training_result,
                "betting": betting_result,
                "success": (
                    collection_result.get("success", False) and 
                    training_result.get("success", False) and
                    betting_result.get("success", False)
                ),
                "duration_seconds": full_run_duration
            }
        finally:
            # Store run history for full run
            try:
                self._store_run_history("full_run", started_at, {
                    "collection": collection_result,
                    "training": training_result,
                    "betting": betting_result,
                    "success": result.get("success", False),
                    "duration_seconds": result.get("duration_seconds"),
                    "stopped": result.get("stopped", False)
                })
            except Exception:
                pass  # Don't let history storage break the run
            # Only clear task if we set it (i.e., we were the top-level caller)
            # If called from trigger_full_run, that function's finally block will clear it
            if not was_full_run:
                self._current_task = None
                self._set_current_domain(original_domain)
            elif was_full_run and original_task != "full_run":
                # Restore original if we overwrote something else
                self._current_task = original_task
                self._set_current_domain(original_domain)
    
    def trigger_full_run(self) -> Dict[str, Any]:
        """Manually trigger full run (collection + training + betting). Runs in background thread."""
        if self._current_task:
            return {"success": False, "error": f"Task already running: {self._current_task}"}
        
        def run_in_background():
            try:
                # Set task status and clear stop event before starting
                self._current_task = "full_run"
                self._stop_task_event.clear()
                self.run_full_with_betting()
            except Exception as e:
                self._log("error", f"Background full run failed: {e}")
            finally:
                # Clear task status when done - ensure this happens even if interrupted
                self._current_task = None
                # Clear stop event to allow future tasks
                self._stop_task_event.clear()
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Full run started in background"}
    
    def start_daemon(self, interval_seconds: int = 21600) -> None:
        """
        Start scheduler in daemon mode (betting automation).
        
        Args:
            interval_seconds: Interval between cycles (default: 6 hours)
        """
        if self._running:
            self._log("warning", "Daemon already running")
            return
        
        self._running = True
        self._stop_event.clear()
        self._set_current_domain("betting")  # Betting daemon
        
        self._log("info", f"Starting daemon mode (interval: {interval_seconds}s)")
        
        while not self._stop_event.is_set():
            try:
                self.run_full_with_betting()
            except Exception as e:
                self._log("error", f"Cycle error: {e}")
            
            # Check if stopped before waiting
            if self._stop_event.is_set():
                break
            
            # Wait for next cycle (with interruptible wait)
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
    
    def start_trading_daemon(self, interval_seconds: int = 3600) -> None:
        """
        Start trading daemon mode (runs full trading cycles).
        
        Args:
            interval_seconds: Interval between cycles (default: 1 hour)
        """
        if self._trading_daemon_running:
            self._log("warning", "Trading daemon already running")
            return
        
        self._trading_daemon_running = True
        self._trading_daemon_stop_event.clear()
        self._set_current_domain("trading")  # Trading daemon
        
        self._log("info", f"[TRADING] Starting trading daemon mode (interval: {interval_seconds}s)")
        
        while not self._trading_daemon_stop_event.is_set():
            try:
                self.run_full_trading_cycle()
            except Exception as e:
                self._log("error", f"[TRADING] Cycle error: {e}")
            
            # Check if stopped before waiting
            if self._trading_daemon_stop_event.is_set():
                break
            
            # Wait for next cycle (with interruptible wait)
            self._trading_daemon_stop_event.wait(interval_seconds)
        
        self._trading_daemon_running = False
        self._log("info", "[TRADING] Trading daemon stopped")
    
    def stop_trading_daemon(self) -> None:
        """Stop trading daemon mode."""
        if not self._trading_daemon_running:
            self._log("warning", "[TRADING] Trading daemon not running")
            return
        
        self._log("info", "[TRADING] Stopping trading daemon...")
        self._trading_daemon_stop_event.set()
    
    def stop_task(self) -> Dict[str, Any]:
        """Stop the currently running task (collection, training, betting, or full_run)."""
        if not self._current_task:
            return {"success": False, "message": "No task is currently running"}
        
        task_name = self._current_task
        self._log("info", f"Stopping {task_name}...")
        self._stop_task_event.set()
        
        # Don't clear _current_task here - let the task's finally block handle it
        # This ensures proper cleanup and prevents race conditions
        
        return {"success": True, "message": f"Stop signal sent to {task_name}"}
    
    def trigger_collection(self) -> Dict[str, Any]:
        """Manually trigger data collection (for dashboard). Runs in background thread."""
        if self._current_task:
            return {"success": False, "error": f"Task already running: {self._current_task}"}
        
        def run_in_background():
            try:
                # Clear stop event before starting (run_collection will set _current_task)
                self._stop_task_event.clear()
                self.run_collection()
            except Exception as e:
                self._log("error", f"Background collection failed: {e}")
            finally:
                # Ensure task is cleared even if run_collection doesn't clear it
                if self._current_task == "collection":
                    self._current_task = None
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Collection started in background"}
    
    def trigger_training(self) -> Dict[str, Any]:
        """Manually trigger training (for dashboard). Runs in background thread."""
        if self._current_task:
            return {"success": False, "error": f"Task already running: {self._current_task}"}
        
        def run_in_background():
            try:
                # Clear stop event before starting (run_training will set _current_task)
                self._stop_task_event.clear()
                self.run_training()
            except Exception as e:
                self._log("error", f"Background training failed: {e}")
            finally:
                # Ensure task is cleared even if run_training doesn't clear it
                if self._current_task == "training":
                    self._current_task = None
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Training started in background"}
    
    # =========================================================================
    # TRADING COLLECTION METHODS
    # =========================================================================
    
    def _get_stock_service(self) -> StockIngestionService:
        """Get or create stock ingestion service."""
        if self._stock_service is None:
            self._stock_service = StockIngestionService(
                self.db,
                log_callback=lambda level, msg: self._log(level, f"[TRADING] {msg}")
            )
        return self._stock_service
    
    def _get_crypto_service(self) -> CryptoIngestionService:
        """Get or create crypto ingestion service."""
        if self._crypto_service is None:
            self._crypto_service = CryptoIngestionService(
                self.db,
                log_callback=lambda level, msg: self._log(level, f"[TRADING] {msg}")
            )
        return self._crypto_service
    
    def run_trading_collection(self) -> Dict[str, Any]:
        """
        Run trading data collection (stocks and crypto).
        
        Collects price data for all symbols in the trading watchlist.
        Separate from betting collection.
        
        Returns:
            Dict with collection results
        """
        self._current_task = "trading_collection"
        self._set_current_domain("trading")  # Trading collection
        self._stop_task_event.clear()
        start_time = time.time()
        started_at = datetime.now()
        
        result = {
            "success": False,
            "stocks": {"collected": 0, "failed": 0, "total_prices": 0},
            "crypto": {"collected": 0, "failed": 0, "total_prices": 0},
            "errors": []
        }
        
        try:
            # Check if trading is enabled
            trading_config = config.TRADING_CONFIG
            if not trading_config.get("enabled", False):
                self._log("info", "[TRADING] Trading is disabled in config")
                result["success"] = True
                result["skipped"] = True
                result["reason"] = "Trading disabled"
                return result
            
            self._log("info", "=" * 60)
            self._log("info", "[TRADING] Starting trading data collection")
            self._log("info", "=" * 60)
            
            # Check if stopped
            if self._stop_task_event.is_set():
                self._log("info", "[TRADING] Collection stopped by user")
                result["stopped"] = True
                return result
            
            # Collect stocks using scraper
            stock_watchlist = trading_config.get("watchlist", {}).get("stocks", [])
            if stock_watchlist:
                self._log("info", f"[TRADING] Collecting {len(stock_watchlist)} stocks...")
                ingestion_service = self._get_ingestion_service()
                
                # Build scraper command - pass watchlist symbols
                api_key = trading_config.get("api_keys", {}).get("alpha_vantage", "")
                cmd = [
                    str(self.scrapers_python),
                    str(self.stocks_script)
                ]
                if api_key:
                    cmd.extend(["--api-key", api_key])
                # Add symbols from watchlist
                if stock_watchlist:
                    cmd.extend(["--symbol"] + stock_watchlist)
                
                # Run scraper and ingest
                stock_ingest_result = ingestion_service.ingest_from_subprocess(
                    cmd,
                    "stocks",
                    timeout=3600,  # 1 hour timeout
                    log_callback=lambda level, msg: self._log(level, f"[STOCKS] {msg}", "trading"),
                    stop_event=self._stop_task_event
                )
                
                # Parse results from ingested data
                if stock_ingest_result.get("success"):
                    # Count successful symbols from ingested data
                    records = stock_ingest_result.get("records", 0)
                    # Rough estimate: assume ~250 trading days per symbol
                    estimated_symbols = max(1, records // 250) if records > 0 else 0
                    result["stocks"]["collected"] = min(estimated_symbols, len(stock_watchlist))
                    result["stocks"]["total_prices"] = records
                    result["stocks"]["failed"] = len(stock_watchlist) - result["stocks"]["collected"]
                else:
                    result["stocks"]["failed"] = len(stock_watchlist)
                    result["errors"].append(f"[STOCKS] {stock_ingest_result.get('error', 'Unknown error')}")
                
                self._log("success", f"[TRADING] Stocks: {result['stocks']['collected']}/{len(stock_watchlist)} collected, {result['stocks']['total_prices']} prices")
            else:
                self._log("info", "[TRADING] No stocks in watchlist")
            
            # Check if stopped
            if self._stop_task_event.is_set():
                self._log("info", "[TRADING] Collection stopped by user after stocks")
                result["stopped"] = True
                return result
            
            # Collect crypto using scraper
            crypto_watchlist = trading_config.get("watchlist", {}).get("crypto", [])
            if crypto_watchlist:
                self._log("info", f"[TRADING] Collecting {len(crypto_watchlist)} cryptos...")
                ingestion_service = self._get_ingestion_service()
                
                # Build scraper command - pass watchlist symbols
                api_key = trading_config.get("api_keys", {}).get("coingecko", "")
                cmd = [
                    str(self.scrapers_python),
                    str(self.crypto_script)
                ]
                if api_key:
                    cmd.extend(["--api-key", api_key])
                # Add symbols from watchlist
                if crypto_watchlist:
                    cmd.extend(["--symbol"] + crypto_watchlist)
                
                # Run scraper and ingest
                crypto_ingest_result = ingestion_service.ingest_from_subprocess(
                    cmd,
                    "crypto",
                    timeout=3600,  # 1 hour timeout
                    log_callback=lambda level, msg: self._log(level, f"[CRYPTO] {msg}", "trading"),
                    stop_event=self._stop_task_event
                )
                
                # Parse results from ingested data
                if crypto_ingest_result.get("success"):
                    # Count successful symbols from ingested data
                    records = crypto_ingest_result.get("records", 0)
                    # Rough estimate: assume ~365 days per symbol
                    estimated_symbols = max(1, records // 365) if records > 0 else 0
                    result["crypto"]["collected"] = min(estimated_symbols, len(crypto_watchlist))
                    result["crypto"]["total_prices"] = records
                    result["crypto"]["failed"] = len(crypto_watchlist) - result["crypto"]["collected"]
                else:
                    result["crypto"]["failed"] = len(crypto_watchlist)
                    result["errors"].append(f"[CRYPTO] {crypto_ingest_result.get('error', 'Unknown error')}")
                
                self._log("success", f"[TRADING] Crypto: {result['crypto']['collected']}/{len(crypto_watchlist)} collected, {result['crypto']['total_prices']} prices")
            else:
                self._log("info", "[TRADING] No crypto in watchlist")
            
            # Determine overall success
            total_collected = result["stocks"]["collected"] + result["crypto"]["collected"]
            total_failed = result["stocks"]["failed"] + result["crypto"]["failed"]
            result["success"] = total_collected > 0 or (total_failed == 0)
            
            duration = time.time() - start_time
            self._last_trading_collection_duration = duration
            self._last_trading_collection = datetime.now().isoformat()
            
            self._log("info", "=" * 60)
            self._log("info", f"[TRADING] Collection complete in {duration:.1f}s")
            self._log("info", f"[TRADING] Total: {total_collected} symbols, {result['stocks']['total_prices'] + result['crypto']['total_prices']} prices")
            self._log("info", "=" * 60)
            
        except Exception as e:
            self._log("error", f"[TRADING] Collection failed: {e}")
            result["errors"].append(str(e))
        finally:
            # Store run history before clearing task
            try:
                self._store_run_history("trading_collection", started_at, result)
            except Exception:
                pass  # Don't let history storage break the run
            self._current_task = None
        
        return result
    
    def trigger_trading_collection(self) -> Dict[str, Any]:
        """Manually trigger trading collection (for dashboard). Runs in background thread."""
        if self._current_task:
            return {"success": False, "error": f"Task already running: {self._current_task}"}
        
        def run_in_background():
            try:
                self._stop_task_event.clear()
                self.run_trading_collection()
            except Exception as e:
                self._log("error", f"[TRADING] Background collection failed: {e}")
            finally:
                if self._current_task == "trading_collection":
                    self._current_task = None
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Trading collection started in background"}
    
    def run_betting(self, require_auto_betting: bool = False) -> Dict[str, Any]:
        """
        Run betting cycle.
        
        Places bets using active models if fake money is enabled.
        If require_auto_betting is True, also checks auto_bet_after_training setting.
        
        Args:
            require_auto_betting: If True, only run if auto_bet_after_training is enabled.
                                Used for automatic betting after training.
                                If False (manual trigger), only checks fake money.
        
        Returns:
            Result dict with betting stats
        """
        self._current_task = "betting"
        self._set_current_domain("betting")  # Betting cycle
        self._stop_task_event.clear()
        start_time = time.time()
        started_at = datetime.now()
        
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
            
            # Check if auto-betting is enabled (only for automatic betting after training)
            if require_auto_betting and not config.AUTO_BET_AFTER_TRAINING:
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
            self._last_betting_duration = duration_ms / 1000
            result["duration_seconds"] = self._last_betting_duration
            self._log("info", f"Betting cycle completed in {duration_ms/1000:.1f}s")
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))
            self._log("error", f"Betting failed: {e}")
        
        finally:
            # Store run history before clearing task
            try:
                self._store_run_history("betting", started_at, result)
            except Exception:
                pass  # Don't let history storage break the run
            self._current_task = None
        
        return result
    
    def set_scraper_workers(self, max_workers_leagues: int = None, max_workers_odds: int = None, max_workers_leagues_playwright: int = None) -> None:
        """Update scraper worker counts.
        
        Args:
            max_workers_leagues: Max parallel workers for league scraping (Betano)
            max_workers_odds: Max parallel workers for odds fetching
            max_workers_leagues_playwright: Max parallel workers for Playwright-based scrapers (FlashScore)
        """
        if max_workers_leagues is not None:
            self.scraper_workers["max_workers_leagues"] = max_workers_leagues
            self._log("info", f"Updated league workers to: {max_workers_leagues}")
        if max_workers_odds is not None:
            self.scraper_workers["max_workers_odds"] = max_workers_odds
            self._log("info", f"Updated odds workers to: {max_workers_odds}")
        if max_workers_leagues_playwright is not None:
            self.scraper_workers["max_workers_leagues_playwright"] = max_workers_leagues_playwright
            self._log("info", f"Updated playwright league workers to: {max_workers_leagues_playwright}")
    
    def trigger_betting(self) -> Dict[str, Any]:
        """Manually trigger betting (for dashboard). Runs in background thread."""
        if self._current_task:
            return {"success": False, "error": f"Task already running: {self._current_task}"}
        
        def run_in_background():
            try:
                # Clear stop event before starting (run_betting will set _current_task)
                self._stop_task_event.clear()
                self.run_betting()
            except Exception as e:
                self._log("error", f"Background betting failed: {e}")
            finally:
                # Ensure task is cleared even if run_betting doesn't clear it
                if self._current_task == "betting":
                    self._current_task = None
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Betting started in background"}
    
    def trigger_backtest(self, train_start: str, test_start: str, test_end: str,
                        period_days: int = 30, ev_threshold: Optional[float] = None) -> Dict[str, Any]:
        """Manually trigger backtesting (for dashboard). Runs in background thread."""
        if self._current_task:
            return {"success": False, "error": f"Task already running: {self._current_task}"}
        
        def run_in_background():
            try:
                from backtesting.backtest import BacktestEngine
                self._log("info", f"Starting backtest: {train_start} to {test_end}")
                engine = BacktestEngine(ev_threshold=ev_threshold)
                result = engine.run_backtest(
                    train_start=train_start,
                    test_start=test_start,
                    test_end=test_end,
                    period_days=period_days
                )
                self._log("success", f"Backtest completed: {result.overall_metrics.get('total_bets', 0)} bets, ROI: {result.overall_metrics.get('roi', 0):.2%}")
            except Exception as e:
                self._log("error", f"Background backtest failed: {e}")
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Backtest started in background"}
    
    # =========================================================================
    # TRADING TRAINING AND CYCLE METHODS
    # =========================================================================
    
    def run_trading_training(self) -> Dict[str, Any]:
        """
        Run trading model training cycle.
        
        Trains models for momentum, swing, and volatility strategies.
        
        Returns:
            Result dict with training stats
        """
        self._current_task = "trading_training"
        self._set_current_domain("trading")  # Trading training
        self._stop_task_event.clear()
        start_time = time.time()
        started_at = datetime.now()
        
        result = {
            "success": False,
            "strategies_trained": 0,
            "has_data": False,
            "errors": []
        }
        
        try:
            # Check if trading is enabled
            trading_config = config.TRADING_CONFIG
            if not trading_config.get("enabled", False):
                self._log("info", "[TRADING] Trading is disabled in config")
                result["success"] = True
                result["skipped"] = True
                result["reason"] = "Trading disabled"
                return result
            
            self._log("info", "=" * 60)
            self._log("info", "[TRADING] Starting trading model training")
            self._log("info", "=" * 60)
            
            # Check if stopped
            if self._stop_task_event.is_set():
                self._log("info", "[TRADING] Training stopped by user")
                result["stopped"] = True
                return result
            
            # Run training
            from train_trading import train_trading_models
            success, metrics = train_trading_models(self.db, log_callback=self._log)
            
            result["success"] = success
            result["metrics"] = metrics
            result["strategies_trained"] = metrics.get("trained_count", 0)
            result["has_data"] = metrics.get("has_data", False)
            
            if success:
                if metrics.get("has_data"):
                    self._log("success", f"[TRADING] Training completed: {result['strategies_trained']} strategies trained")
                else:
                    reason = metrics.get("no_data_reason", "No training data")
                    self._log("warning", f"[TRADING] Training completed but no models trained: {reason}")
            else:
                errors = metrics.get("errors", [])
                error_msg = "; ".join(errors) if errors else "Unknown error"
                self._log("error", f"[TRADING] Training failed: {error_msg}")
                result["errors"].extend(errors)
            
            duration = time.time() - start_time
            result["duration_seconds"] = duration
            self._log("info", f"[TRADING] Training cycle completed in {duration:.1f}s")
            
        except Exception as e:
            self._log("error", f"[TRADING] Training failed: {e}")
            result["errors"].append(str(e))
        finally:
            # Store run history before clearing task
            try:
                self._store_run_history("trading_training", started_at, result)
            except Exception:
                pass  # Don't let history storage break the run
            self._current_task = None
        
        return result
    
    def trigger_trading_training(self) -> Dict[str, Any]:
        """Manually trigger trading training (for dashboard). Runs in background thread."""
        if self._current_task:
            return {"success": False, "error": f"Task already running: {self._current_task}"}
        
        def run_in_background():
            try:
                self._stop_task_event.clear()
                self.run_trading_training()
            except Exception as e:
                self._log("error", f"[TRADING] Background training failed: {e}")
            finally:
                if self._current_task == "trading_training":
                    self._current_task = None
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Trading training started in background"}
    
    def run_trading_cycle(self) -> Dict[str, Any]:
        """
        Run trading cycle (signal generation + execution).
        
        Uses TradingService to find signals and execute trades.
        
        Returns:
            Result dict with cycle stats
        """
        self._current_task = "trading_cycle"
        self._set_current_domain("trading")  # Trading cycle
        self._stop_task_event.clear()
        start_time = time.time()
        started_at = datetime.now()
        
        result = {
            "success": False,
            "signals_found": 0,
            "trades_executed": 0,
            "portfolio_value": 0,
            "errors": []
        }
        
        try:
            # Check if trading is enabled
            trading_config = config.TRADING_CONFIG
            if not trading_config.get("enabled", False):
                self._log("info", "[TRADING] Trading is disabled in config")
                result["success"] = True
                result["skipped"] = True
                result["reason"] = "Trading disabled"
                return result
            
            self._log("info", "=" * 60)
            self._log("info", "[TRADING] Starting trading cycle")
            self._log("info", "=" * 60)
            
            # Check if stopped
            if self._stop_task_event.is_set():
                self._log("info", "[TRADING] Cycle stopped by user")
                result["stopped"] = True
                return result
            
            # Initialize trading service
            from trading.service import TradingService
            trading_service = TradingService(self.db, log_callback=self._log)
            
            # Run trading cycle
            cycle_result = trading_service.run_trading_cycle(
                limit_per_strategy=5,
                max_executions=3
            )
            
            result["success"] = cycle_result.get("success", False)
            result["signals_found"] = cycle_result.get("signals_found", 0)
            result["trades_executed"] = cycle_result.get("signals_executed", 0)
            result["portfolio_value"] = cycle_result.get("portfolio_value", 0)
            result["pnl"] = cycle_result.get("pnl", {})
            
            if cycle_result.get("error"):
                result["errors"].append(cycle_result["error"])
            
            duration = time.time() - start_time
            result["duration_seconds"] = duration
            
            if result["success"]:
                self._log("success", f"[TRADING] Cycle complete: {result['trades_executed']} trades, Portfolio: ${result['portfolio_value']:.2f}")
            else:
                error_msg = "; ".join(result["errors"]) if result["errors"] else "Unknown error"
                self._log("error", f"[TRADING] Cycle failed: {error_msg}")
            
        except Exception as e:
            self._log("error", f"[TRADING] Cycle failed: {e}")
            result["errors"].append(str(e))
        finally:
            # Store run history before clearing task
            try:
                self._store_run_history("trading_cycle", started_at, result)
            except Exception:
                pass  # Don't let history storage break the run
            self._current_task = None
        
        return result
    
    def trigger_trading_cycle(self) -> Dict[str, Any]:
        """Manually trigger trading cycle (for dashboard). Runs in background thread."""
        if self._current_task:
            return {"success": False, "error": f"Task already running: {self._current_task}"}
        
        def run_in_background():
            try:
                self._stop_task_event.clear()
                self.run_trading_cycle()
            except Exception as e:
                self._log("error", f"[TRADING] Background cycle failed: {e}")
            finally:
                if self._current_task == "trading_cycle":
                    self._current_task = None
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Trading cycle started in background"}
    
    def run_full_trading_cycle(self) -> Dict[str, Any]:
        """
        Run full trading cycle: collection + training + cycle.
        
        Returns:
            Combined result dict
        """
        original_task = self._current_task
        original_domain = self._get_current_domain()
        was_full_run = original_task == "trading_full_run"
        if not was_full_run:
            self._current_task = "trading_full_run"
            self._set_current_domain("trading")  # Trading full run
        
        self._log("info", "=" * 60)
        self._log("info", "[TRADING] Starting full cycle (collection + training + cycle)")
        self._log("info", "=" * 60)
        full_run_start = time.time()
        started_at = datetime.now()
        
        try:
            # Phase 1: Collection
            collection_result = self.run_trading_collection()
            if was_full_run:
                self._current_task = "trading_full_run"
                self._set_current_domain("trading")
            
            if collection_result.get("success"):
                self._log("success", "[TRADING] Collection phase completed successfully")
            else:
                self._log("warning", "[TRADING] Collection phase completed with errors")
            
            if self._stop_task_event.is_set():
                return {
                    "collection": collection_result,
                    "training": {"success": False, "skipped": True, "reason": "Stopped"},
                    "cycle": {"success": False, "skipped": True, "reason": "Stopped"},
                    "success": False,
                    "stopped": True
                }
            
            # Phase 2: Training
            self._log("info", "=" * 60)
            self._log("info", "[TRADING] Starting Training phase...")
            self._log("info", "=" * 60)
            
            training_result = self.run_trading_training()
            if was_full_run:
                self._current_task = "trading_full_run"
                self._set_current_domain("trading")
            
            if training_result.get("success"):
                self._log("success", "[TRADING] Training phase completed successfully")
            else:
                self._log("warning", "[TRADING] Training phase completed with errors")
            
            if self._stop_task_event.is_set():
                return {
                    "collection": collection_result,
                    "training": training_result,
                    "cycle": {"success": False, "skipped": True, "reason": "Stopped"},
                    "success": False,
                    "stopped": True
                }
            
            # Phase 3: Cycle
            self._log("info", "=" * 60)
            self._log("info", "[TRADING] Starting Cycle phase...")
            self._log("info", "=" * 60)
            
            cycle_result = self.run_trading_cycle()
            if was_full_run:
                self._current_task = "trading_full_run"
                self._set_current_domain("trading")
            
            if cycle_result.get("success"):
                self._log("success", "[TRADING] Cycle phase completed successfully")
            else:
                self._log("warning", "[TRADING] Cycle phase completed with errors")
            
            full_run_duration = time.time() - full_run_start
            self._log("success", f"[TRADING] Full cycle completed in {full_run_duration/60:.1f} minutes")
            
            return {
                "collection": collection_result,
                "training": training_result,
                "cycle": cycle_result,
                "success": (
                    collection_result.get("success", False) and 
                    training_result.get("success", False) and
                    cycle_result.get("success", False)
                ),
                "duration_seconds": full_run_duration
            }
        finally:
            # Store run history for trading full run
            try:
                self._store_run_history("trading_full_run", started_at, {
                    "collection": collection_result,
                    "training": training_result,
                    "cycle": cycle_result,
                    "success": result.get("success", False),
                    "duration_seconds": result.get("duration_seconds"),
                    "stopped": result.get("stopped", False)
                })
            except Exception:
                pass  # Don't let history storage break the run
            if not was_full_run:
                self._current_task = None
                self._set_current_domain(original_domain)
            elif was_full_run and original_task != "trading_full_run":
                self._current_task = original_task
                self._set_current_domain(original_domain)
    
    def trigger_full_trading_cycle(self) -> Dict[str, Any]:
        """Manually trigger full trading cycle (for dashboard). Runs in background thread."""
        if self._current_task:
            return {"success": False, "error": f"Task already running: {self._current_task}"}
        
        def run_in_background():
            try:
                self._current_task = "trading_full_run"
                self._stop_task_event.clear()
                self.run_full_trading_cycle()
            except Exception as e:
                self._log("error", f"[TRADING] Background full cycle failed: {e}")
            finally:
                if self._current_task == "trading_full_run":
                    self._current_task = None
                self._stop_task_event.clear()
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        return {"success": True, "message": "Full trading cycle started in background"}
