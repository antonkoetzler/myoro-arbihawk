"""
Test suite for betting flow.
Tests bet placement, settlement, and bankroll tracking.
"""
import pytest
from data.database import Database
from testing.bankroll import VirtualBankroll
from datetime import datetime


class TestBettingFlow:
    """Test betting placement and settlement."""
    
    def test_bet_placement(self, temp_db):
        """Test placing a bet."""
        # Create a fixture first
        temp_db.insert_fixture({
            "fixture_id": "test_fixture_bet",
            "home_team_name": "Team A",
            "away_team_name": "Team B",
            "start_time": "2025-01-20T15:00:00Z",
            "status": "scheduled"
        })
        
        # Place a bet
        bet_id = temp_db.insert_bet({
            "fixture_id": "test_fixture_bet",
            "market_id": "1x2",
            "market_name": "Match Result",
            "outcome_id": "home",
            "outcome_name": "Home",
            "odds": 2.5,
            "stake": 10.0,
            "model_market": "1x2"
        })
        
        assert bet_id is not None
        
        # Verify bet exists
        bets = temp_db.get_bet_history(limit=1)
        assert len(bets) == 1
        assert bets.iloc[0]["id"] == bet_id
        assert bets.iloc[0]["result"] == "pending"
        assert bets.iloc[0]["stake"] == 10.0
    
    def test_bet_settlement(self, temp_db):
        """Test settling a bet."""
        # Create fixture and place bet
        temp_db.insert_fixture({
            "fixture_id": "test_fixture_settle",
            "home_team_name": "Team A",
            "away_team_name": "Team B",
            "start_time": "2025-01-20T15:00:00Z",
            "status": "finished"
        })
        
        bet_id = temp_db.insert_bet({
            "fixture_id": "test_fixture_settle",
            "market_id": "1x2",
            "market_name": "Match Result",
            "outcome_id": "home",
            "outcome_name": "Home",
            "odds": 2.5,
            "stake": 10.0,
            "model_market": "1x2"
        })
        
        # Settle as win
        temp_db.settle_bet(bet_id, "win", 25.0)
        
        # Verify settlement
        bets = temp_db.get_bet_history()
        bet = bets[bets["id"] == bet_id].iloc[0]
        assert bet["result"] == "win"
        assert bet["payout"] == 25.0
        assert bet["settled_at"] is not None
    
    def test_bankroll_tracking(self, temp_db):
        """Test bankroll statistics tracking."""
        bankroll = VirtualBankroll(db=temp_db)
        
        # Create fixture and place multiple bets
        temp_db.insert_fixture({
            "fixture_id": "test_fixture_bankroll",
            "home_team_name": "Team A",
            "away_team_name": "Team B",
            "start_time": "2025-01-20T15:00:00Z",
            "status": "finished"
        })
        
        # Place and settle bets
        bet1 = temp_db.insert_bet({
            "fixture_id": "test_fixture_bankroll",
            "market_id": "1x2",
            "market_name": "Match Result",
            "outcome_id": "home",
            "outcome_name": "Home",
            "odds": 2.0,
            "stake": 10.0,
            "model_market": "1x2"
        })
        temp_db.settle_bet(bet1, "win", 20.0)
        
        bet2 = temp_db.insert_bet({
            "fixture_id": "test_fixture_bankroll",
            "market_id": "1x2",
            "market_name": "Match Result",
            "outcome_id": "away",
            "outcome_name": "Away",
            "odds": 3.0,
            "stake": 10.0,
            "model_market": "1x2"
        })
        temp_db.settle_bet(bet2, "loss", 0.0)
        
        # Check bankroll stats
        stats = temp_db.get_bankroll_stats()
        assert stats["total_bets"] == 2
        assert stats["settled_bets"] == 2
        assert stats["wins"] == 1
        assert stats["losses"] == 1
        assert stats["total_stake"] == 20.0
        assert stats["total_payout"] == 20.0
        assert stats["profit"] == 0.0
        assert stats["win_rate"] == 0.5
