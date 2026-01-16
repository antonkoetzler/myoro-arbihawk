"""
Bet settlement service for evaluating completed bets.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd

from .database import Database


class BetSettlement:
    """
    Evaluates completed bets against actual scores.
    
    Determines win/loss for various market types and updates
    the database with settlement status.
    
    Example usage:
        settlement = BetSettlement()
        
        # Settle all pending bets
        results = settlement.settle_pending_bets()
        print(f"Settled {results['settled']} bets")
    """
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
    
    def evaluate_1x2(self, home_score: int, away_score: int,
                     outcome_name: str) -> bool:
        """
        Evaluate 1x2 (match result) bet.
        
        Args:
            home_score: Home team score
            away_score: Away team score
            outcome_name: Bet outcome (e.g., "1", "X", "2", "home", "draw", "away")
            
        Returns:
            True if bet won, False otherwise
        """
        outcome_lower = outcome_name.lower()
        
        # Home win
        if outcome_lower in ["1", "home", "home_win", "home win"]:
            return home_score > away_score
        
        # Draw
        if outcome_lower in ["x", "draw"]:
            return home_score == away_score
        
        # Away win
        if outcome_lower in ["2", "away", "away_win", "away win"]:
            return home_score < away_score
        
        return False
    
    def evaluate_over_under(self, home_score: int, away_score: int,
                            outcome_name: str, threshold: float = 2.5) -> bool:
        """
        Evaluate over/under bet.
        
        Args:
            home_score: Home team score
            away_score: Away team score
            outcome_name: Bet outcome (e.g., "over", "under", "over 2.5")
            threshold: Goals threshold (default 2.5)
            
        Returns:
            True if bet won, False otherwise
        """
        total_goals = home_score + away_score
        outcome_lower = outcome_name.lower()
        
        # Extract threshold from outcome name if present
        import re
        threshold_match = re.search(r'[\d.]+', outcome_name)
        if threshold_match:
            threshold = float(threshold_match.group())
        
        if "over" in outcome_lower:
            return total_goals > threshold
        
        if "under" in outcome_lower:
            return total_goals < threshold
        
        return False
    
    def evaluate_btts(self, home_score: int, away_score: int,
                      outcome_name: str) -> bool:
        """
        Evaluate Both Teams To Score bet.
        
        Args:
            home_score: Home team score
            away_score: Away team score
            outcome_name: Bet outcome (e.g., "yes", "no")
            
        Returns:
            True if bet won, False otherwise
        """
        both_scored = home_score > 0 and away_score > 0
        outcome_lower = outcome_name.lower()
        
        if outcome_lower in ["yes", "sim", "btts yes"]:
            return both_scored
        
        if outcome_lower in ["no", "não", "nao", "btts no"]:
            return not both_scored
        
        return False
    
    def evaluate_bet(self, home_score: int, away_score: int,
                     market_name: str, outcome_name: str) -> Optional[bool]:
        """
        Evaluate a bet based on market type.
        
        Args:
            home_score: Home team score
            away_score: Away team score
            market_name: Market name/type
            outcome_name: Bet outcome
            
        Returns:
            True if won, False if lost, None if market type unknown
        """
        market_lower = market_name.lower() if market_name else ""
        
        # 1x2 / Match Result
        if any(x in market_lower for x in ["1x2", "match result", "resultado", "full time"]):
            return self.evaluate_1x2(home_score, away_score, outcome_name)
        
        # Over/Under
        if any(x in market_lower for x in ["over", "under", "gols", "goals", "total"]):
            return self.evaluate_over_under(home_score, away_score, outcome_name)
        
        # Both Teams To Score
        if any(x in market_lower for x in ["btts", "both teams", "ambas marcam", "ambos marcam"]):
            return self.evaluate_btts(home_score, away_score, outcome_name)
        
        # Double Chance
        if "double chance" in market_lower or "dupla chance" in market_lower:
            return self._evaluate_double_chance(home_score, away_score, outcome_name)
        
        return None
    
    def _evaluate_double_chance(self, home_score: int, away_score: int,
                                outcome_name: str) -> bool:
        """Evaluate double chance bet."""
        outcome_lower = outcome_name.lower()
        
        # 1X = Home or Draw
        if "1x" in outcome_lower or ("home" in outcome_lower and "draw" in outcome_lower):
            return home_score >= away_score
        
        # X2 = Draw or Away
        if "x2" in outcome_lower or ("draw" in outcome_lower and "away" in outcome_lower):
            return home_score <= away_score
        
        # 12 = Home or Away (no draw)
        if "12" in outcome_lower:
            return home_score != away_score
        
        return False
    
    def settle_bet(self, bet_id: int, fixture_id: str) -> Optional[Dict[str, Any]]:
        """
        Settle a single bet.
        
        Args:
            bet_id: Bet ID from bet_history
            fixture_id: Fixture ID to get score
            
        Returns:
            Settlement result dict or None if couldn't settle
        """
        # Get bet details
        bets = self.db.get_bet_history()
        bet = bets[bets['id'] == bet_id]
        
        if len(bet) == 0:
            return None
        
        bet = bet.iloc[0]
        
        # Get score
        scores = self.db.get_scores(fixture_id)
        if len(scores) == 0:
            return None
        
        score = scores.iloc[0]
        home_score = score.get('home_score')
        away_score = score.get('away_score')
        
        if home_score is None or away_score is None:
            return None
        
        # Evaluate bet
        won = self.evaluate_bet(
            home_score=home_score,
            away_score=away_score,
            market_name=bet.get('market_name', ''),
            outcome_name=bet.get('outcome_name', '')
        )
        
        if won is None:
            return None
        
        # Calculate payout
        stake = bet['stake']
        odds = bet['odds']
        
        if won:
            result = 'win'
            payout = stake * odds
        else:
            result = 'loss'
            payout = 0
        
        # Update database
        self.db.settle_bet(bet_id, result, payout)
        
        return {
            "bet_id": bet_id,
            "fixture_id": fixture_id,
            "result": result,
            "stake": stake,
            "odds": odds,
            "payout": payout,
            "profit": payout - stake
        }
    
    def settle_pending_bets(self) -> Dict[str, Any]:
        """
        Settle all pending bets that have scores available.
        
        Returns:
            Dict with settlement results
        """
        pending = self.db.get_pending_bets()
        
        if len(pending) == 0:
            return {
                "total_pending": 0,
                "settled": 0,
                "wins": 0,
                "losses": 0,
                "total_payout": 0,
                "results": []
            }
        
        settled = 0
        wins = 0
        losses = 0
        total_payout = 0
        results = []
        
        for _, bet in pending.iterrows():
            result = self.settle_bet(bet['id'], bet['fixture_id'])
            
            if result:
                settled += 1
                total_payout += result['payout']
                results.append(result)
                
                if result['result'] == 'win':
                    wins += 1
                else:
                    losses += 1
        
        return {
            "total_pending": len(pending),
            "settled": settled,
            "wins": wins,
            "losses": losses,
            "total_payout": total_payout,
            "results": results
        }
    
    def get_settlement_stats(self) -> Dict[str, Any]:
        """Get overall settlement statistics."""
        return self.db.get_bankroll_stats()
