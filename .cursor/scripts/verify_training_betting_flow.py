#!/usr/bin/env python3
"""
Verify training and betting flows after fixes.
Runs run_training() then run_betting(), captures logs, checks for fixed warnings.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src" / "arbihawk"))

from data.database import Database

# Capture log messages
log_entries = []


def log_capture(level: str, message: str, domain: str = ""):
    log_entries.append({"level": level, "message": message, "domain": domain})
    print(f"[{level.upper()}] [{domain}] {message}")


def main():
    from automation.scheduler import AutomationScheduler
    import config
    from pathlib import Path

    print("=" * 60)
    print("Verifying Training + Betting Flow (on debug DB)")
    print("=" * 60)

    BASE_DIR = Path(config.__file__).parent
    prod_path = BASE_DIR / "data" / "arbihawk.db"
    debug_path = BASE_DIR / "data" / "arbihawk_debug.db"

    if prod_path.exists():
        print("\n--- Syncing prod -> debug DB ---\n")
        db = Database(db_path=str(debug_path))
        sync_result = db.sync_from_production(str(prod_path))
        print(f"Sync: {sync_result.get('total_copied', 0)} records copied")
    else:
        print("\n(Production DB not found; using existing debug DB)\n")
        db = Database(db_path=str(debug_path))

    scheduler = AutomationScheduler(db=db)
    scheduler.set_log_callback(log_capture)

    # 1. Run training
    print("\n--- Running Training ---\n")
    training_result = scheduler.run_training()

    training_ok = training_result.get("success", False)
    has_data = training_result.get("has_data", False)
    markets_trained = training_result.get("markets_trained", 0)

    # Check for fixed warnings (should NOT appear)
    bad_warnings = [
        "Predictor must be trained before evaluation",
        "Profitability checking enabled but no betting metrics available",
    ]
    found_bad = [w for w in bad_warnings if any(w in e["message"] for e in log_entries)]
    if found_bad:
        print("\n[FAIL] These warnings should be gone after fix:")
        for w in found_bad:
            print(f"  - {w}")
    else:
        print("\n[OK] No 'Predictor must be trained' or 'no betting metrics' warnings.")

    print(f"\nTraining result: success={training_ok}, has_data={has_data}, markets_trained={markets_trained}")

    # 2. Run betting
    print("\n--- Running Betting ---\n")
    betting_result = scheduler.run_betting(require_auto_betting=False)

    betting_ok = betting_result.get("success", False)
    skipped = betting_result.get("skipped", False)
    reason = betting_result.get("reason", "")
    bets_placed = betting_result.get("bets_placed", 0)

    print(f"\nBetting result: success={betting_ok}, skipped={skipped}, reason={reason}, bets_placed={bets_placed}")

    # 3. Settlement log check (full run would do this; we can run settle_pending_bets once)
    print("\n--- Settlement (dry check) ---\n")
    settlement_result = scheduler.settlement.settle_pending_bets()
    total_pending = settlement_result.get("total_pending", 0)
    settled = settlement_result.get("settled", 0)
    print(f"Pending bets: {total_pending}, Settled this run: {settled}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    if found_bad:
        print("FAIL: Old warnings still present.")
        return 1
    if not training_ok:
        print("FAIL: Training did not report success.")
        return 1
    if not betting_ok and not skipped:
        print("FAIL: Betting failed (and was not skipped).")
        return 1
    print("PASS: Training and betting flows completed; fixed warnings are gone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
