"""
One-off audit: export sample of pending bets (fixture_id, home, away, start_time)
and scores with synthetic IDs (parsed home, away, date) for side-by-side comparison.
No production code changes. Run from repo root: python .cursor/scripts/audit_settlement_samples.py [--db path]
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Run from repo root; arbihawk package must be on path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARBIHAWK_ROOT = REPO_ROOT / "arbihawk"
for p in (str(ARBIHAWK_ROOT), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(REPO_ROOT)

# Import after path fix
import config  # noqa: E402
from arbihawk.data.database import Database  # noqa: E402

# Synthetic ID format: source_Home_Away_Date (date YYYY-MM-DD)
SYNTHETIC_PREFIXES = ("flashscore_", "livescore_")


def parse_synthetic_id(fixture_id: str):
    """Parse source_Home_Away_Date into source, home, away, date. Returns None if not synthetic."""
    if not fixture_id:
        return None
    for prefix in SYNTHETIC_PREFIXES:
        if fixture_id.startswith(prefix):
            rest = fixture_id[len(prefix) :]
            parts = rest.split("_")
            if len(parts) >= 4:
                # Date is last part (YYYY-MM-DD); home/away can contain underscores
                date_part = parts[-1]
                rest_parts = parts[:-1]
                if len(rest_parts) >= 2:
                    away = rest_parts[-1].replace("_", " ")
                    home = "_".join(rest_parts[:-1]).replace("_", " ")
                    return {"source": prefix.rstrip("_"), "home": home, "away": away, "date": date_part}
            elif len(parts) == 3:
                return {"source": prefix.rstrip("_"), "home": parts[0].replace("_", " "), "away": parts[1].replace("_", " "), "date": parts[2]}
            return None
    return None


def main():
    parser = argparse.ArgumentParser(description="Audit pending bets vs scores (synthetic IDs)")
    parser.add_argument("--db", type=str, default=None, help="Database path (default: config DB_PATH)")
    parser.add_argument("--out", type=str, default=None, help="Output JSON file (default: stdout)")
    args = parser.parse_args()
    db_path = args.db or config.DB_PATH
    db = Database(db_path)

    # Pending bets: join with fixtures for home/away/start_time
    pending = db.get_pending_bets()
    fixtures_df = db.get_fixtures(limit=50000)
    fixture_map = {}
    if not fixtures_df.empty:
        for _, row in fixtures_df.iterrows():
            fixture_map[str(row["fixture_id"])] = {
                "home_team_name": row.get("home_team_name"),
                "away_team_name": row.get("away_team_name"),
                "start_time": row.get("start_time"),
            }

    pending_samples = []
    for _, bet in pending.head(100).iterrows():
        fid = bet.get("fixture_id")
        info = fixture_map.get(str(fid), {})
        pending_samples.append({
            "fixture_id": str(fid),
            "home": info.get("home_team_name"),
            "away": info.get("away_team_name"),
            "start_time": info.get("start_time"),
        })

    # All scores; mark which have synthetic IDs and parse them
    scores_df = db.get_scores()
    score_samples = []
    for _, row in scores_df.iterrows():
        fid = row["fixture_id"]
        parsed = parse_synthetic_id(fid)
        score_samples.append({
            "fixture_id": fid,
            "home_score": int(row["home_score"]) if row.get("home_score") is not None else None,
            "away_score": int(row["away_score"]) if row.get("away_score") is not None else None,
            "is_synthetic": parsed is not None,
            "parsed_home": parsed["home"] if parsed else None,
            "parsed_away": parsed["away"] if parsed else None,
            "parsed_date": parsed["date"] if parsed else None,
        })

    out = {
        "pending_bets_sample": pending_samples,
        "pending_count": len(pending),
        "scores_sample": score_samples[:200],
        "scores_count": len(scores_df),
        "synthetic_score_count": sum(1 for s in score_samples if s["is_synthetic"]),
    }
    json_str = json.dumps(out, indent=2)
    if args.out:
        Path(args.out).write_text(json_str, encoding="utf-8")
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == "__main__":
    main()
