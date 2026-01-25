"""
End-to-end integration tests.
Tests complete flows from ingestion to betting.
"""
import json
import pytest
from data.ingestion import DataIngestionService
from data.database import Database
from testing.bankroll import VirtualBankroll


class TestEndToEndFlow:
    """Test complete end-to-end flows."""
    
    def test_complete_ingestion_to_betting_flow(self, temp_db):
        """Test complete flow: ingestion -> fixture creation -> bet placement."""
        service = DataIngestionService(db=temp_db)
        
        # Ingest Betano data
        betano_data = [{
            "league_id": 1,
            "league_name": "Test League",
            "fixtures": [{
                "fixture_id": "e2e_fixture_1",
                "home_team_id": "1",
                "home_team_name": "Team A",
                "away_team_id": "2",
                "away_team_name": "Team B",
                "start_time": "2025-01-25T15:00:00Z",
                "status": "scheduled",
                "odds": [{
                    "market_id": "1x2",
                    "market_name": "Match Result",
                    "outcome_id": "home",
                    "outcome_name": "Home",
                    "odds_value": 2.0
                }]
            }]
        }]
        
        json_str = json.dumps(betano_data)
        result = service._ingest_json(json_str, "betano")
        assert result["success"] is True
        
        # Verify fixture and odds exist
        fixtures = temp_db.get_fixtures()
        assert len(fixtures) == 1
        
        odds = temp_db.get_odds(fixture_id="e2e_fixture_1")
        assert len(odds) == 1
        
        # Place a bet
        bet_id = temp_db.insert_bet({
            "fixture_id": "e2e_fixture_1",
            "market_id": "1x2",
            "market_name": "Match Result",
            "outcome_id": "home",
            "outcome_name": "Home",
            "odds": 2.0,
            "stake": 10.0,
            "model_market": "1x2"
        })
        
        assert bet_id is not None
        
        # Verify bet exists
        bets = temp_db.get_bet_history()
        assert len(bets) == 1
        assert bets.iloc[0]["fixture_id"] == "e2e_fixture_1"
    
    def test_score_matching_and_settlement_flow(self, temp_db):
        """Test flow: score ingestion -> matching -> bet settlement."""
        service = DataIngestionService(db=temp_db)
        
        # First, create a fixture (simulating Betano ingestion)
        temp_db.insert_fixture({
            "fixture_id": "e2e_match_fixture",
            "home_team_name": "Manchester United",
            "away_team_name": "Liverpool",
            "start_time": "2025-01-25T15:00:00Z",
            "status": "scheduled"
        })
        
        # Place a bet
        bet_id = temp_db.insert_bet({
            "fixture_id": "e2e_match_fixture",
            "market_id": "1x2",
            "market_name": "Match Result",
            "outcome_id": "home",
            "outcome_name": "Home",
            "odds": 2.5,
            "stake": 10.0,
            "model_market": "1x2"
        })
        
        # Ingest score (simulating FlashScore ingestion)
        score_data = {
            "matches": [{
                "home_team_name": "Manchester United",
                "away_team_name": "Liverpool",
                "home_score": 2,
                "away_score": 1,
                "start_time": "2025-01-25T15:00:00Z",
                "match_date": "2025-01-25"
            }]
        }
        
        json_str = json.dumps(score_data)
        result = service._ingest_json(json_str, "flashscore")
        assert result["success"] is True
        
        # Score should match to existing fixture
        scores = temp_db.get_scores("e2e_match_fixture")
        assert len(scores) == 1
        assert scores.iloc[0]["home_score"] == 2
        assert scores.iloc[0]["away_score"] == 1
        
        # Settle the bet (home won)
        temp_db.settle_bet(bet_id, "win", 25.0)
        
        # Verify settlement
        bets = temp_db.get_bet_history()
        bet = bets[bets["id"] == bet_id].iloc[0]
        assert bet["result"] == "win"
        assert bet["payout"] == 25.0
