"""
E2E verification that settlement fallback works.

  python verify_settlement_e2e.py              # Seeded DB only (~2s), no network
  python verify_settlement_e2e.py --live       # 1 league Betano + 1 league Flashscore, then settle

Exits 0 with "VERIFICATION PASSED" and numbers on success.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Run from arbihawk package root
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import config
from data.database import Database
from data.settlement import BetSettlement
def _seed_db(db: Database) -> None:
    """Seed a DB with fixtures (Betano-style IDs), scores only under synthetic IDs, and pending bets."""
    # Fixtures that will NOT have a score by fixture_id (we only add scores under synthetic ID)
    fixtures = [
        {"fixture_id": "verify_f1", "home_team_name": "Spezia", "away_team_name": "Sampdoria", "start_time": "2025-11-30T14:00:00Z", "status": "finished"},
        {"fixture_id": "verify_f2", "home_team_name": "Real Madrid", "away_team_name": "Barcelona", "start_time": "2025-12-01T20:00:00Z", "status": "finished"},
    ]
    for f in fixtures:
        db.insert_fixture({
            "fixture_id": f["fixture_id"],
            "home_team_name": f["home_team_name"],
            "away_team_name": f["away_team_name"],
            "start_time": f["start_time"],
            "status": f["status"],
        })
    # Scores ONLY under synthetic IDs (so get_scores(fixture_id) is empty; fallback must find by teams+date)
    scores = [
        ("flashscore_Spezia_Sampdoria_2025-11-30", 2, 1),
        ("flashscore_Real_Madrid_Barcelona_2025-12-01", 1, 0),
    ]
    for fid, hs, aw in scores:
        db.insert_score(fid, {"home_score": hs, "away_score": aw, "status": "finished"})
    # Pending bets on the Betano-style fixture IDs
    for f in fixtures:
        db.insert_bet({
            "fixture_id": f["fixture_id"],
            "market_id": "1x2",
            "market_name": "Match Result",
            "outcome_id": "home",
            "outcome_name": "Home",
            "odds": 2.0,
            "stake": 10.0,
            "model_market": "1x2",
        })


def _run_seeded(db_path: str) -> bool:
    """Use a temp copy of DB (or empty), seed, settle, verify. No network."""
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "verify_settlement.db"
        db = Database(db_path=str(path))
        _seed_db(db)
        pending_before = len(db.get_pending_bets())
        assert pending_before == 2, f"expected 2 pending, got {pending_before}"
        settlement = BetSettlement(db=db)
        result = settlement.settle_pending_bets()
        pending_after = len(db.get_pending_bets())
        print("Seeded verification:")
        print(f"  Pending before: {pending_before}")
        print(f"  Settled: {result['settled']}")
        print(f"  Wins: {result['wins']}, Losses: {result['losses']}")
        print(f"  Total payout: {result['total_payout']}")
        print(f"  Pending after: {pending_after}")
        if result["settled"] >= 2 and pending_after == 0:
            print("VERIFICATION PASSED (seeded): settlement fallback settled 2 bets, 0 pending after.")
            return True
        print("VERIFICATION FAILED (seeded): expected at least 2 settled and 0 pending after.")
        return False


def _run_live(db_path: str) -> bool:
    """Run 1 league Betano + 1 league Flashscore, insert pending bets for fallback-able fixtures, settle."""
    scrapers_dir = ROOT / "scrapers"
    betano_script = scrapers_dir / "src" / "sportsbooks" / "betano.py"
    flashscore_script = scrapers_dir / "src" / "sports_data" / "flashscore.py"
    if sys.platform == "win32":
        py = scrapers_dir / "venv" / "Scripts" / "python.exe"
    else:
        py = scrapers_dir / "venv" / "bin" / "python"
    if not py.exists() or not betano_script.exists():
        print("Live verification skipped: scrapers venv or betano.py not found.")
        return False

    db = Database(db_path=db_path)
    from data.ingestion import DataIngestionService
    ingestion = DataIngestionService(db=db)

    # 1) Betano: 1 league
    print("Running Betano (1 league)...")
    cmd_betano = [str(py), str(betano_script), "--max-leagues", "1"]
    res_betano = ingestion.ingest_from_subprocess(cmd_betano, "betano", timeout=300)
    if not res_betano.get("success"):
        print(f"Betano failed: {res_betano.get('error')}")
        return False
    n_betano = res_betano.get("records", 0)
    print(f"  Betano: {n_betano} records")

    # 2) Flashscore: 1 league (e.g. Premier League)
    if not flashscore_script.exists():
        print("Flashscore script not found; skipping. Run seeded verification for full check.")
        # Still try settlement on existing data
    else:
        print("Running Flashscore (1 league: Premier League)...")
        cmd_fs = [str(py), str(flashscore_script), "--league", "Premier League", "--headless"]
        res_fs = ingestion.ingest_from_subprocess(cmd_fs, "flashscore", timeout=180)
        if res_fs.get("success"):
            print(f"  Flashscore: {res_fs.get('records', 0)} records")
        else:
            print(f"  Flashscore: {res_fs.get('error', 'failed')}")

    # 3) Find fixtures that have no score by ID but have a score by teams+date (fallback-able)
    fixtures_df = db.get_fixtures(limit=5000)
    candidates = []
    no_score_count = 0
    for _, row in fixtures_df.iterrows():
        fid = str(row["fixture_id"])
        if fid.startswith("flashscore_") or fid.startswith("livescore_"):
            continue
        scores_by_id = db.get_scores(fid)
        if len(scores_by_id) > 0:
            continue
        no_score_count += 1
        home = row.get("home_team_name") or ""
        away = row.get("away_team_name") or ""
        start = row.get("start_time")
        score_row = db.find_score_by_teams_and_date(home, away, start)
        if score_row is not None:
            candidates.append((fid, home, away, start))
    print(f"  Fixtures without score by ID: {no_score_count}; fallback-able (same teams+date): {len(candidates)}")
    # 4) Insert pending bets for up to 3 candidates (avoid duplicates)
    existing_pending = db.get_pending_bets()
    existing_fids = set(existing_pending["fixture_id"].astype(str).tolist()) if not existing_pending.empty else set()
    added = 0
    for fid, home, away, start in candidates[:5]:
        if fid in existing_fids:
            continue
        db.insert_bet({
            "fixture_id": fid,
            "market_id": "1x2",
            "market_name": "Match Result",
            "outcome_id": "home",
            "outcome_name": "Home",
            "odds": 2.0,
            "stake": 10.0,
            "model_market": "1x2",
        })
        added += 1
        existing_fids.add(fid)
        if added >= 3:
            break
    if added:
        print(f"  Inserted {added} pending bet(s) for fallback-able fixtures.")

    # 5) Settlement
    pending_before = len(db.get_pending_bets())
    settlement = BetSettlement(db=db)
    result = settlement.settle_pending_bets()
    pending_after = len(db.get_pending_bets())

    print("Live verification:")
    print(f"  Pending before: {pending_before}")
    print(f"  Settled: {result['settled']}")
    print(f"  Wins: {result['wins']}, Losses: {result['losses']}")
    print(f"  Total payout: {result['total_payout']}")
    print(f"  Pending after: {pending_after}")
    if result["settled"] >= 1:
        print("VERIFICATION PASSED (live): at least 1 bet settled (including via fallback).")
        return True
    if len(candidates) == 0 and no_score_count == 0:
        print("VERIFICATION: all fixtures had scores by ID (matcher matched them). Fallback not needed this run.")
    else:
        print("VERIFICATION: no bets settled this run (0 fallback-able fixtures or no pending bets).")
    print("Run without --live for seeded verification: python verify_settlement_e2e.py")
    return False


def main():
    ap = argparse.ArgumentParser(description="E2E verification for settlement fallback")
    ap.add_argument("--live", action="store_true", help="Run limited collection (1 league each) then settle")
    ap.add_argument("--db", type=str, default=None, help="Database path (default: config.DB_PATH)")
    args = ap.parse_args()
    db_path = args.db or config.DB_PATH

    if args.live:
        ok = _run_live(db_path)
    else:
        ok = _run_seeded(db_path)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
