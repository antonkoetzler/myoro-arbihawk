"""One-off: run settlement on configured DB and print numbers. Use --diagnose to see why fallback might not match."""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import config
from data.database import Database
from data.settlement import BetSettlement
from data.match_identity import parse_synthetic_id

def diagnose(db):
    from datetime import datetime as dt
    from data.match_identity import team_similarity, get_aliases_and_min_score
    pending = db.get_pending_bets()
    fixtures = db.get_fixtures(limit=100000)
    fixture_ids = set(fixtures["fixture_id"].astype(str).tolist()) if not fixtures.empty else set()
    now = dt.utcnow().isoformat() + "Z"
    past_pending = 0
    for _, b in pending.iterrows():
        f = db.get_fixture_by_id(str(b["fixture_id"]))
        if f and (f.get("start_time") or "") < now:
            past_pending += 1
    scores_df = db.get_scores()
    synthetic_count = 0
    synthetic_fids = []
    for fid in scores_df["fixture_id"].astype(str):
        if parse_synthetic_id(fid):
            synthetic_count += 1
            synthetic_fids.append(fid)
    pending_with_fixture = sum(1 for _, b in pending.iterrows() if str(b["fixture_id"]) in fixture_ids)
    print(f"Diagnose: {len(pending)} pending ({past_pending} with start_time in past); {pending_with_fixture} have fixture row; {len(scores_df)} scores, {synthetic_count} with synthetic ID")
    aliases, min_score = get_aliases_and_min_score()
    # Prefer past fixtures for diagnosis
    past_bets = []
    for _, bet in pending.iterrows():
        fixture = db.get_fixture_by_id(str(bet["fixture_id"]))
        if fixture and (fixture.get("start_time") or "") < now:
            past_bets.append((bet, fixture))
    sample = past_bets[:3] if past_bets else [(pending.iloc[i], db.get_fixture_by_id(str(pending.iloc[i]["fixture_id"]))) for i in range(min(3, len(pending)))]
    for bet, fixture in sample:
        if not fixture:
            print(f"  bet {bet['id']} fixture_id={bet['fixture_id']}: no fixture row")
            continue
        fid = str(bet["fixture_id"])
        home = fixture.get("home_team_name") or ""
        away = fixture.get("away_team_name") or ""
        start = fixture.get("start_time")
        score = db.find_score_by_teams_and_date(home, away, start)
        print(f"  bet {bet['id']} fixture_id={fid} home={home!r} away={away!r} start={start}: fallback found={score is not None}")
        if score is None and synthetic_fids and start:
            fixture_date = (start[:10] if len(start) >= 10 else start) if start else ""
            best_combined = 0
            best_sid = None
            for sid in synthetic_fids:
                parsed = parse_synthetic_id(sid)
                if not parsed or (fixture_date and parsed.get("date") != fixture_date):
                    continue
                parts = sid.split("_", 1)[1].split("_") if "_" in sid else []
                date_idx = next((j for j in range(len(parts)-1,-1,-1) if len(parts[j])==10 and parts[j][:4].isdigit()), None)
                if date_idx is None or date_idx < 2:
                    continue
                teams_parts = parts[:date_idx]
                for k in range(1, len(teams_parts)):
                    hc = " ".join(teams_parts[:k])
                    ac = " ".join(teams_parts[k:])
                    hs = team_similarity(home, hc, aliases)
                    aws = team_similarity(away, ac, aliases)
                    comb = (hs + aws) / 2
                    if comb > best_combined:
                        best_combined = comb
                        best_sid = sid
            print(f"    same-date synthetic best score={best_combined:.0f} (need {min_score}) example={str(best_sid)[:70] if best_sid else 'none'}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--diagnose", action="store_true", help="Print why fallback might not match")
    args = p.parse_args()
    db_path = config.DB_PATH
    db = Database(db_path)
    if args.diagnose:
        diagnose(db)
        return
    pending_before = db.get_pending_bets()
    n_pending_before = len(pending_before)
    print(f"DB: {db_path}")
    print(f"Pending bets before settlement: {n_pending_before}")
    if n_pending_before == 0:
        print("No pending bets. Nothing to settle.")
        return
    settlement = BetSettlement(db=db)
    result = settlement.settle_pending_bets()
    print(f"Total pending: {result['total_pending']}")
    print(f"Settled: {result['settled']}")
    print(f"Wins: {result['wins']}")
    print(f"Losses: {result['losses']}")
    print(f"Total payout: {result['total_payout']}")
    pending_after = db.get_pending_bets()
    print(f"Pending bets after settlement: {len(pending_after)}")
    if result["results"]:
        for r in result["results"][:5]:
            print(f"  bet_id={r['bet_id']} fixture_id={r['fixture_id']} result={r['result']} payout={r['payout']}")
        if len(result["results"]) > 5:
            print(f"  ... and {len(result['results']) - 5} more")

if __name__ == "__main__":
    main()
