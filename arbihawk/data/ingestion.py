"""
Data ingestion service for scraper outputs.
Reads JSON from scrapers and stores in database.
"""

import sys
import os
import json
import hashlib
import subprocess
import time
import threading
import queue
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime

from .database import Database
from .validation import DataValidator, ValidationResult


class DataIngestionService:
    """
    Service for ingesting data from scrapers.
    
    Reads JSON from stdin (piped from scrapers) or subprocess execution,
    validates the data, and stores it in the database.
    
    Example usage:
        service = DataIngestionService()
        
        # Ingest from stdin
        result = service.ingest_from_stdin("betano")
        
        # Ingest from subprocess
        result = service.ingest_from_subprocess(
            "python scrapers/src/sportsbooks/betano.py",
            "betano"
        )
    """
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.validator = DataValidator()
    
    def ingest_from_stdin(self, source: str) -> Dict[str, Any]:
        """
        Ingest data from stdin.
        
        Args:
            source: Source identifier ("betano", "flashscore", or "livescore")
            
        Returns:
            Dict with ingestion results
        """
        try:
            json_str = sys.stdin.read()
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read from stdin: {e}",
                "records": 0
            }
        
        return self._ingest_json(json_str, source)
    
    def ingest_from_subprocess(self, command, source: str,
                                args: List[str] = None,
                                timeout: int = 300,
                                log_callback: Optional[Callable[[str, str], None]] = None) -> Dict[str, Any]:
        """
        Execute scraper subprocess and ingest its output.
        Streams output in real-time and logs it via callback.
        
        Args:
            command: Command to execute (str or list of command parts)
            source: Source identifier ("betano", "flashscore", or "livescore")
            args: Additional command arguments (deprecated, use command as list)
            timeout: Timeout in seconds
            log_callback: Optional callback function(log_level, message) for real-time logging
            
        Returns:
            Dict with ingestion results
        """
        # Handle both string commands (legacy) and list commands
        if isinstance(command, str):
            # Legacy: split string command
            full_command = command.split() + (args or [])
            shell = True
        else:
            # New: command is already a list
            full_command = command
            shell = False
        
        try:
            # Use unbuffered output and ensure proper encoding
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            
            # Use Popen to stream output in real-time
            # On Windows, ensure UTF-8 encoding for subprocess
            if sys.platform == 'win32':
                env['PYTHONIOENCODING'] = 'utf-8'
            
            process = subprocess.Popen(
                full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=False,  # Get bytes first, decode manually
                shell=shell,
                env=env,
                bufsize=1  # Line buffered
            )
            
            # Collect all output lines and stream in real-time
            output_lines = []
            json_str = None
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            
            # Read output line by line in real-time
            import threading
            import queue
            
            output_queue = queue.Queue()
            read_complete = threading.Event()
            
            def read_output():
                try:
                    for line_bytes in iter(process.stdout.readline, b''):
                        if line_bytes:
                            # Decode with UTF-8, replace errors
                            try:
                                line = line_bytes.decode('utf-8', errors='replace').rstrip('\n\r')
                                if line:
                                    output_queue.put(line)
                            except Exception as e:
                                output_queue.put(f"DECODE_ERROR: {e}")
                    read_complete.set()
                except Exception as e:
                    output_queue.put(f"READ_ERROR: {e}")
                    read_complete.set()
            
            reader_thread = threading.Thread(target=read_output, daemon=True)
            reader_thread.start()
            
            # Process lines as they come with timeout
            start_time = time.time()
            while True:
                try:
                    # Get line with timeout
                    try:
                        line = output_queue.get(timeout=0.5)
                    except queue.Empty:
                        # Check if process is done and reader is complete
                        if process.poll() is not None and read_complete.is_set():
                            break
                        # Check timeout
                        if time.time() - start_time > timeout:
                            process.kill()
                            raise subprocess.TimeoutExpired(full_command, timeout)
                        continue
                    
                    if line.startswith("READ_ERROR:"):
                        if log_callback:
                            log_callback("error", line)
                        continue
                    
                    if line:
                        output_lines.append(line)
                        stripped = line.strip()
                        clean_line = ansi_escape.sub('', stripped)
                        
                        # Check if this looks like JSON (starts with [ or { and is substantial)
                        if clean_line.startswith('[') or clean_line.startswith('{'):
                            # This might be JSON - verify by trying to parse it
                            try:
                                json.loads(clean_line)
                                # Valid single-line JSON - save it
                                json_str = clean_line
                            except json.JSONDecodeError:
                                # Might be multi-line JSON - accumulate and try parsing
                                # Build candidate from recent lines that look like JSON
                                json_candidate_lines = []
                                for prev_line in reversed(output_lines[-20:]):  # Check last 20 lines
                                    prev_clean = ansi_escape.sub('', prev_line.strip())
                                    if prev_clean.startswith('[') or prev_clean.startswith('{') or \
                                       (json_candidate_lines and (prev_clean.startswith(' ') or prev_clean.startswith('\t') or 
                                        prev_clean.startswith(',') or prev_clean.startswith('"'))):
                                        json_candidate_lines.insert(0, prev_clean)
                                    elif json_candidate_lines:
                                        break
                                
                                if json_candidate_lines:
                                    json_candidate = '\n'.join(json_candidate_lines).strip()
                                    try:
                                        json.loads(json_candidate)
                                        json_str = json_candidate
                                    except json.JSONDecodeError:
                                        # Not complete yet, might be accumulating
                                        pass
                                
                                # Also log it in case it's a log message starting with [
                                if len(clean_line) > 3 and len(clean_line) < 500 and not json_str:
                                    self._process_scraper_line(line, log_callback)
                        else:
                            # Log TUI messages in real-time (skip empty lines and very short lines)
                            if len(clean_line) > 3:
                                self._process_scraper_line(line, log_callback)
                    
                    # Check if reader is done and queue is empty
                    if read_complete.is_set() and output_queue.empty():
                        break
                        
                except subprocess.TimeoutExpired:
                    raise
            
            # Wait for process to complete
            returncode = process.wait(timeout=5)
            
            # If we didn't find JSON yet, look for it in all output
            if not json_str:
                # Look for JSON starting from the end (most likely location)
                for line in reversed(output_lines):
                    stripped = line.strip()
                    # Remove ANSI codes
                    clean_line = ansi_escape.sub('', stripped)
                    # Check if this looks like the start of a JSON array or object
                    if clean_line.startswith('[') or clean_line.startswith('{'):
                        # Verify it's actually valid JSON by attempting to parse
                        try:
                            json.loads(clean_line)
                            json_str = clean_line
                            break
                        except json.JSONDecodeError:
                            # Not valid JSON, continue searching
                            continue
            
            # If we found potential JSON but it has ANSI codes, clean it
            if json_str:
                json_str = ansi_escape.sub('', json_str).strip()
            
            # Final attempt: if still no JSON, try to find and extract JSON from full output
            if not json_str:
                full_output = '\n'.join(output_lines)
                full_output_clean = ansi_escape.sub('', full_output)
                
                # Try to find JSON array or object in the output
                # Look for balanced brackets/braces
                json_str = self._extract_json_from_output(full_output_clean)
            
            if returncode != 0:
                error_msg = '\n'.join(output_lines[-10:])  # Last 10 lines for error
                if log_callback:
                    log_callback("error", f"Scraper exited with code {returncode}")
                return {
                    "success": False,
                    "error": f"Subprocess failed with code {returncode}: {error_msg}",
                    "records": 0
                }
            
            if not json_str or not json_str.strip():
                if log_callback:
                    log_callback("error", "No JSON output from scraper")
                return {
                    "success": False,
                    "error": "No JSON output from scraper",
                    "records": 0
                }
            
        except subprocess.TimeoutExpired:
            if log_callback:
                log_callback("error", f"Scraper timed out after {timeout}s")
            process.kill()
            return {
                "success": False,
                "error": f"Subprocess timed out after {timeout}s",
                "records": 0
            }
        except Exception as e:
            if log_callback:
                log_callback("error", f"Failed to execute scraper: {e}")
            return {
                "success": False,
                "error": f"Failed to execute subprocess: {e}",
                "records": 0
            }
        
        return self._ingest_json(json_str, source)
    
    def _extract_json_from_output(self, output: str) -> Optional[str]:
        """
        Extract valid JSON from output that may contain other text.
        Handles multi-line JSON and mixed TUI output.
        
        Args:
            output: Full output string that may contain JSON mixed with other text
            
        Returns:
            Valid JSON string or None if not found
        """
        # Remove ANSI escape codes first
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_output = ansi_escape.sub('', output)
        
        # Strategy: Find the root/outermost JSON structure
        # Look for all { positions and try to find the one that represents the complete root structure
        
        # Find all potential JSON object starts
        obj_starts = []
        for i, char in enumerate(clean_output):
            if char == '{':
                obj_starts.append(i)
        
        # Try each { position from the end, looking for the root structure
        for obj_start in reversed(obj_starts):
            # Try to extract complete JSON object by finding matching braces
            # Account for braces inside strings
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i in range(obj_start, len(clean_output)):
                char = clean_output[i]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            candidate = clean_output[obj_start:i+1].strip()
                            try:
                                # Validate it's actually valid JSON
                                parsed = json.loads(candidate)
                                # Check if this looks like a root structure (not a nested object)
                                # Root structures have specific top-level keys
                                if isinstance(parsed, dict):
                                    # For match score scrapers, root should have "matches" key
                                    # For betano root objects, should have "league_id" or "fixtures"
                                    # Prioritize structures with known root keys
                                    if "matches" in parsed or "league_id" in parsed or "fixtures" in parsed:
                                        return candidate
                                    # If no known root keys, but it's at the start of output or has many keys, might be root
                                    # But prefer to continue searching for one with known keys
                                elif isinstance(parsed, list) and len(parsed) > 0:
                                    # Betano root is an array - this is definitely root
                                    return candidate
                            except json.JSONDecodeError:
                                pass
                            break
        
        # Try to find JSON array (starts with [)
        array_start = clean_output.rfind('[')
        if array_start != -1:
            bracket_count = 0
            in_string = False
            escape_next = False
            
            for i in range(array_start, len(clean_output)):
                char = clean_output[i]
                
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            candidate = clean_output[array_start:i+1].strip()
                            try:
                                parsed = json.loads(candidate)
                                return candidate
                            except json.JSONDecodeError:
                                pass
                            break
        
        # Last resort: try to find any valid JSON by scanning from end
        # Look for lines that look like JSON start
        lines = clean_output.split('\n')
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith('{') or line.startswith('['):
                # Try to reconstruct JSON from this point to the end
                candidate = '\n'.join(lines[i:]).strip()
                try:
                    parsed = json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    # Try progressively adding more lines
                    for j in range(i + 1, min(i + 50, len(lines))):
                        candidate = '\n'.join(lines[i:j+1]).strip()
                        try:
                            parsed = json.loads(candidate)
                            return candidate
                        except json.JSONDecodeError:
                            continue
        
        return None
    
    def _process_scraper_line(self, line: str, log_callback: Optional[Callable[[str, str], None]]) -> None:
        """Process a line from scraper output and log it appropriately."""
        if not log_callback:
            return
        
        try:
            # Remove ANSI color codes for logging
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_line = ansi_escape.sub('', line.strip())
            
            if not clean_line:
                return
            
            # Determine log level based on Unicode symbols first
            log_level = "info"  # Default
            
            # Check for Unicode symbols and extract log level
            if '✗' in clean_line:
                log_level = "error"
            elif '⚠' in clean_line:
                log_level = "warning"
            elif '✓' in clean_line:
                log_level = "success"
            elif 'ℹ' in clean_line:
                log_level = "info"
            # Then check for bracket prefixes
            elif '[ERROR]' in clean_line.upper():
                log_level = "error"
            elif '[WARNING]' in clean_line.upper() or '[WARN]' in clean_line.upper():
                log_level = "warning"
            elif '[OK]' in clean_line.upper() or '[SUCCESS]' in clean_line.upper():
                log_level = "success"
            elif '[INFO]' in clean_line.upper():
                log_level = "info"
            
            # Remove Unicode symbols from the message
            message = clean_line
            message = message.replace('ℹ', '').replace('✓', '').replace('✗', '').replace('⚠', '')
            
            # Remove all level prefixes from the message to avoid duplication
            # This removes patterns like [INFO], [WARNING], [WARN], [ERROR], [OK], etc.
            message = re.sub(r'\[?(INFO|WARNING|WARN|ERROR|OK|SUCCESS)\]?\s*', '', message, flags=re.IGNORECASE)
            message = message.strip()
            
            # Skip if message is empty after cleanup
            if not message:
                return
            
            log_callback(log_level, message)
        except Exception as e:
            # If logging fails, try to log the error itself (but don't fail completely)
            try:
                log_callback("error", f"Failed to process scraper line: {str(e)}")
            except:
                pass  # Can't log, give up
    
    def ingest_from_file(self, filepath: str, source: str) -> Dict[str, Any]:
        """
        Ingest data from a JSON file.
        
        Args:
            filepath: Path to JSON file
            source: Source identifier ("betano", "flashscore", or "livescore")
            
        Returns:
            Dict with ingestion results
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_str = f.read()
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {e}",
                "records": 0
            }
        
        return self._ingest_json(json_str, source)
    
    def _ingest_json(self, json_str: str, source: str) -> Dict[str, Any]:
        """
        Parse and ingest JSON data.
        
        Args:
            json_str: JSON string
            source: Source identifier
            
        Returns:
            Dict with ingestion results
        """
        # Calculate checksum
        checksum = hashlib.md5(json_str.encode()).hexdigest()
        
        # Parse and validate
        data, validation = self.validator.validate_json_string(json_str, source)
        
        if data is None:
            self.db.insert_ingestion_metadata(
                source=source,
                records_count=0,
                checksum=checksum,
                validation_status="error",
                errors="; ".join(validation.errors)
            )
            return {
                "success": False,
                "error": validation.errors[0] if validation.errors else "Unknown error",
                "records": 0,
                "validation_errors": validation.errors
            }
        
        if not validation.valid:
            self.db.insert_ingestion_metadata(
                source=source,
                records_count=0,
                checksum=checksum,
                validation_status="validation_failed",
                errors="; ".join(validation.errors)
            )
            return {
                "success": False,
                "error": "Validation failed",
                "records": 0,
                "validation_errors": validation.errors,
                "warnings": validation.warnings
            }
        
        # Ingest based on source
        if source == "betano":
            records = self._ingest_betano(data)
        elif source in ["flashscore", "livescore"]:
            records = self._ingest_match_scores(data, source)
        else:
            return {
                "success": False,
                "error": f"Unknown source: {source}",
                "records": 0
            }
        
        # Record ingestion metadata
        self.db.insert_ingestion_metadata(
            source=source,
            records_count=records,
            checksum=checksum,
            validation_status="success",
            errors=None
        )
        
        return {
            "success": True,
            "records": records,
            "checksum": checksum,
            "warnings": validation.warnings
        }
    
    def _ingest_betano(self, data: List[Dict]) -> int:
        """Ingest Betano data into database."""
        total_fixtures = 0
        total_odds = 0
        
        for league in data:
            league_id = league.get("league_id")
            league_name = league.get("league_name")
            fixtures = league.get("fixtures", [])
            
            for fixture in fixtures:
                # Prepare fixture data
                fixture_data = {
                    "fixture_id": str(fixture.get("fixture_id")),
                    "tournament_id": league_id,
                    "tournament_name": league_name,
                    "home_team_id": str(fixture.get("home_team_id", "")),
                    "home_team_name": fixture.get("home_team_name", ""),
                    "away_team_id": str(fixture.get("away_team_id", "")),
                    "away_team_name": fixture.get("away_team_name", ""),
                    "start_time": fixture.get("start_time", ""),
                    "status": fixture.get("status", "scheduled")
                }
                
                # Insert fixture
                self.db.insert_fixture(fixture_data)
                total_fixtures += 1
                
                # Insert odds
                odds = fixture.get("odds", [])
                if odds:
                    odds_data = []
                    for odd in odds:
                        odds_data.append({
                            "fixture_id": fixture_data["fixture_id"],
                            "bookmaker_id": "betano",
                            "bookmaker_name": "Betano",
                            "market_id": str(odd.get("market_id", "")),
                            "market_name": odd.get("market_name", ""),
                            "outcome_id": str(odd.get("outcome_id", "")),
                            "outcome_name": odd.get("outcome_name", ""),
                            "odds_value": odd.get("odds_value", 0)
                        })
                    
                    total_odds += self.db.insert_odds_batch(odds_data)
        
        return total_fixtures
    
    def _ingest_match_scores(self, data: Dict, source: str) -> int:
        """Ingest match score data (Flashscore/Livescore) into database."""
        matches = data.get("matches", [])
        
        # Try to match scores to fixtures immediately during ingestion
        from data.matchers import ScoreMatcher
        matcher = ScoreMatcher(self.db)
        
        scores_inserted = 0
        matched_count = 0
        
        for match in matches:
            # Only process completed matches with scores
            home_score = match.get("home_score")
            away_score = match.get("away_score")
            
            if home_score is None or away_score is None:
                continue
            
            home_team = match.get("home_team_name") or match.get("home_team", "")
            away_team = match.get("away_team_name") or match.get("away_team", "")
            match_time = match.get("start_time") or match.get("match_date", "")
            
            # Try to match to existing fixture
            fixture_id = matcher.match_score(
                home_team=home_team,
                away_team=away_team,
                match_time=match_time
            )
            
            if fixture_id:
                # Matched to existing fixture - use real fixture ID
                score_data = {
                    "fixture_id": fixture_id,
                    "home_score": home_score,
                    "away_score": away_score,
                    "status": "finished"
                }
                self.db.insert_score(fixture_id, score_data)
                matched_count += 1
            else:
                # No match found - store with temp ID for later matching
                match_date = match.get("match_date") or match_time.split('T')[0] if 'T' in match_time else match_time
                temp_fixture_id = f"{source}_{home_team}_{away_team}_{match_date}".replace(" ", "_")
                
                score_data = {
                    "fixture_id": temp_fixture_id,
                    "home_score": home_score,
                    "away_score": away_score,
                    "status": "finished"
                }
                self.db.insert_score(temp_fixture_id, score_data)
            
            scores_inserted += 1
        
        return scores_inserted


def main():
    """CLI entry point for ingestion."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingest data from scrapers')
    parser.add_argument('source', choices=['betano', 'flashscore', 'livescore'],
                        help='Data source')
    parser.add_argument('--file', '-f', type=str,
                        help='Input file path (default: read from stdin)')
    
    args = parser.parse_args()
    
    service = DataIngestionService()
    
    if args.file:
        result = service.ingest_from_file(args.file, args.source)
    else:
        result = service.ingest_from_stdin(args.source)
    
    # Output result as JSON
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
