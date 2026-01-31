"""Tests for settlement fallback: pending bet + score under synthetic ID -> settled."""
import pytest
from data.database import Database
from data.settlement import BetSettlement


class TestSettlementFallback:
    def test_settle_bet_via_teams_and_date_fallback(self, temp_db):
        """Pending bet has Betano fixture_id; score exists only under synthetic ID. Settlement finds score by teams+date."""
        # Fixture (Betano ID) - bet references this
        temp_db.insert_fixture({
            "fixture_id": "79560484",
            "home_team_name": "Spezia",
            "away_team_name": "Sampdoria",
            "start_time": "2025-11-30T14:00:00Z",
            "status": "finished",
        })
        # Score under synthetic ID only (no score row for 79560484)
        synth_id = "flashscore_Spezia_Sampdoria_2025-11-30"
        temp_db.insert_score(synth_id, {
            "home_score": 2,
            "away_score": 1,
            "status": "finished",
        })
        # Place bet on Betano fixture_id
        bet_id = temp_db.insert_bet({
            "fixture_id": "79560484",
            "market_id": "1x2",
            "market_name": "Match Result",
            "outcome_id": "home",
            "outcome_name": "Home",
            "odds": 2.0,
            "stake": 10.0,
            "model_market": "1x2",
        })
        # get_scores("79560484") is empty; fallback should find score by teams+date
        settlement = BetSettlement(db=temp_db)
        result = settlement.settle_bet(bet_id, "79560484")
        assert result is not None
        assert result["result"] == "win"
        assert result["payout"] == 20.0
        # DB updated
        bets = temp_db.get_bet_history()
        bet = bets[bets["id"] == bet_id].iloc[0]
        assert bet["result"] == "win"
        assert bet["payout"] == 20.0

    def test_settle_pending_bets_drops_pending_count(self, temp_db):
        """E2E: run settlement; pending count drops when scores found by fallback."""
        # Two fixtures (Betano IDs), two scores under synthetic IDs only
        for fid, home, away, start in [
            ("f1", "Spezia", "Sampdoria", "2025-11-30T14:00:00Z"),
            ("f2", "Cagliari", "Genoa", "2025-12-01T15:00:00Z"),
        ]:
            temp_db.insert_fixture({
                "fixture_id": fid,
                "home_team_name": home,
                "away_team_name": away,
                "start_time": start,
                "status": "finished",
            })
            synth = f"flashscore_{home}_{away}_{start[:10]}"
            temp_db.insert_score(synth, {"home_score": 1, "away_score": 0, "status": "finished"})
        # Place two pending bets
        temp_db.insert_bet({"fixture_id": "f1", "market_id": "1x2", "market_name": "Match Result", "outcome_id": "home", "outcome_name": "Home", "odds": 2.0, "stake": 10.0})
        temp_db.insert_bet({"fixture_id": "f2", "market_id": "1x2", "market_name": "Match Result", "outcome_id": "home", "outcome_name": "Home", "odds": 2.0, "stake": 10.0})
        pending_before = len(temp_db.get_pending_bets())
        assert pending_before == 2
        settlement = BetSettlement(db=temp_db)
        result = settlement.settle_pending_bets()
        assert result["settled"] == 2
        pending_after = len(temp_db.get_pending_bets())
        assert pending_after == 0
        assert result["total_pending"] == 2
