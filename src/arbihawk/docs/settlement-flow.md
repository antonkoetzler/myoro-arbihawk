# Settlement flow (score–fixture matching)

## Full flow after implementation

1. **Sync prod → debug** (optional, for testing)
   - API or script: `Database(debug_path).sync_from_production(prod_path)` copies fixtures, scores, bet_history, etc. from production to debug DB.

2. **Run settlement**
   - Via scheduler (full run includes settlement after training/betting) or directly:
   - `BetSettlement(db).settle_pending_bets()`
   - For each pending bet: look up score by bet’s `fixture_id`. If none (e.g. score stored under synthetic ID), **fallback**: get fixture by `get_fixture_by_id`, then `find_score_by_teams_and_date(home, away, start_time)` using the central match-identity layer to match against scores with synthetic IDs (`flashscore_Home_Away_Date`). If a score is found, evaluate win/loss and call `db.settle_bet(...)`.

3. **Check Bet History**
   - More bets should move from pending to win/loss as they are matched to scores (by fixture_id or by teams+date fallback).

4. **Optional: full collection then settlement again**
   - Run full collection (Betano + Flashscore). Matcher uses central `match_identity` and config `matching_min_match_score`; when it finds a fixture, the score is stored under the Betano `fixture_id`. When it doesn’t, the score is stored under a synthetic ID via `match_identity.synthetic_id(...)`.
   - Run settlement again: bets whose scores are under synthetic IDs are still settled via the teams+date fallback.

## Components

- **match_identity** (`data/match_identity.py`): `normalize_team_name`, `team_similarity`, `same_match`, `synthetic_id`, `parse_synthetic_id`; aliases/min_score from config.
- **Config**: `config/team_aliases.json` (aliases, `matching_min_match_score` default 75); `config.py` loads `TEAM_ALIASES`, `MATCHING_MIN_MATCH_SCORE`.
- **DB**: `get_fixture_by_id`, `find_score_by_teams_and_date` (scores with synthetic IDs parsed and matched via `same_match`).
- **Settlement**: In `settle_bet`, when `get_scores(fixture_id)` is empty, fallback: fixture → find score by teams+date → evaluate and settle.
- **Matcher**: Uses `match_identity` and config threshold; logs "no fixtures in window" vs "best score X below threshold".
- **Ingestion**: Builds synthetic ID with `match_identity.synthetic_id(...)` when score doesn’t match a fixture.

## Audit script

- `.cursor/scripts/audit_settlement_samples.py`: exports sample pending bets (fixture_id, home, away, start_time) and scores with synthetic IDs (parsed home, away, date) for side-by-side comparison. Run: `python .cursor/scripts/audit_settlement_samples.py [--db path] [--out file.json]`.
