"""Query recent errors from database and scheduler."""
import sys
import os
import json
from pathlib import Path
try:
    import urllib.request
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

# Add arbihawk to path
sys.path.insert(0, str(Path(__file__).parent / "arbihawk"))

from arbihawk.data.database import Database
from arbihawk.automation.scheduler import AutomationScheduler

def query_api_errors():
    """Try to query the dashboard API if it's running."""
    if not HAS_URLLIB:
        return None
    try:
        req = urllib.request.Request('http://localhost:8000/api/errors')
        with urllib.request.urlopen(req, timeout=2) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None

def main():
    # Try to get errors from running API first (includes in-memory scheduler logs)
    api_errors = query_api_errors()
    
    # Get ALL ingestion errors from database (not just limit 100)
    db = Database()
    metadata = db.get_ingestion_metadata(limit=1000)  # Get more to catch all errors
    failed = [
        r for r in metadata.to_dict('records') 
        if r.get('validation_status') not in ['success', None]
    ]
    
    # Get log errors - prefer API if available, otherwise from new scheduler instance
    if api_errors:
        errors = api_errors.get('log_errors', [])
        api_ingestion = api_errors.get('ingestion_errors', [])
        print("(Using errors from running dashboard API)")
    else:
        scheduler = AutomationScheduler(db)
        logs = scheduler.get_logs(limit=1000)
        errors = [log for log in logs if log.get('level') == 'error']
        api_ingestion = []
        print("(Dashboard API not running - only showing database errors)")
    
    # Check for duplicates in ingestion errors (same source + same error message)
    seen = set()
    unique_failed = []
    for err in failed:
        key = (err.get('source'), err.get('errors'))
        if key not in seen:
            seen.add(key)
            unique_failed.append(err)
    
    # Combine ingestion errors (API might have fewer, so use database as source of truth)
    all_ingestion_errors = failed if not api_ingestion else api_ingestion
    
    print("=" * 80)
    print("RECENT ERRORS DETECTED")
    print("=" * 80)
    total = len(errors) + len(all_ingestion_errors)
    print(f"\nTotal Errors: {total}")
    print(f"  - Log Errors: {len(errors)}")
    print(f"  - Ingestion Errors: {len(all_ingestion_errors)}")
    if len(failed) != len(unique_failed):
        print(f"    (Note: {len(failed) - len(unique_failed)} duplicates found)")
    print()
    
    if errors:
        print("LOG ERRORS:")
        print("-" * 80)
        for i, err in enumerate(errors, 1):
            print(f"{i}. [{err.get('timestamp', 'N/A')}] {err.get('message', 'N/A')}")
        print()
    
    if all_ingestion_errors:
        print("INGESTION ERRORS:")
        print("-" * 80)
        for i, err in enumerate(all_ingestion_errors, 1):
            source = err.get('source', 'unknown')
            status = err.get('validation_status', 'unknown')
            error_msg = err.get('errors', 'Validation failed')
            ingested_at = err.get('ingested_at', 'N/A')
            print(f"{i}. [{ingested_at}] Source: {source}, Status: {status}")
            print(f"   Error: {error_msg}")
        print()
    
    if not errors and not failed:
        print("No errors found!")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
