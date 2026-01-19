"""
Virtual bankroll system for testing bot performance.
Tracks fake bets and calculates ROI without risking real money.
"""

import math
from typing import Dict, Any, List, Optional
from datetime import datetime

from data.database import Database
import config


class VirtualBankroll:
    """
    Virtual bankroll for testing betting strategies.
    
    Manages fake money balance, places bets on recommendations,
    and tracks performance over time.
    
    Bet Sizing Strategies:
    - **Fixed**: Bet same amount every time (safest)
    - **Percentage**: Bet X% of current bankroll
    - **Kelly**: Optimal bet sizing based on edge
    - **Unit**: Bet 1-3 units based on confidence
    
    Example usage:
        bankroll = VirtualBankroll()
        
        # Place a bet
        bet_id = bankroll.place_bet(
            fixture_id="123",
            market_id="1x2",
            market_name="Match Result",
            outcome_id="home",
            outcome_name="Home Win",
            odds=2.10,
            confidence=0.55
        )
        
        # Get stats
        stats = bankroll.get_stats()
        print(f"ROI: {stats['roi']:.2%}")
    """
    
    def __init__(self, db: Optional[Database] = None,
                 starting_balance: Optional[float] = None,
                 strategy: Optional[str] = None):
        """
        Initialize virtual bankroll.
        
        Args:
            db: Database instance
            starting_balance: Starting balance (from config if not provided)
            strategy: Bet sizing strategy (from config if not provided)
        """
        self.db = db or Database()
        
        fake_money_config = config.FAKE_MONEY_CONFIG
        
        self.starting_balance = starting_balance or fake_money_config.get("starting_balance", 10000)
        self.strategy = strategy or fake_money_config.get("bet_sizing_strategy", "fixed")
        
        # Strategy parameters from config
        self.fixed_stake = fake_money_config.get("fixed_stake", 100)
        self.percentage_stake = fake_money_config.get("percentage_stake", 0.02)
        self.unit_size_percentage = fake_money_config.get("unit_size_percentage", 0.01)
        
        # Track current balance
        self._balance = None
    
    @property
    def balance(self) -> float:
        """Get current balance."""
        if self._balance is None:
            self._balance = self._calculate_balance()
        return self._balance
    
    def _calculate_balance(self) -> float:
        """Calculate current balance from bet history."""
        stats = self.db.get_bankroll_stats()
        
        total_stake = stats.get("total_stake", 0)
        total_payout = stats.get("total_payout", 0)
        
        return self.starting_balance - total_stake + total_payout
    
    def refresh_balance(self) -> float:
        """Refresh balance from database."""
        self._balance = self._calculate_balance()
        return self._balance
    
    def calculate_stake(self, odds: float, confidence: float = 0.5) -> float:
        """
        Calculate stake based on strategy.
        
        Args:
            odds: Bet odds
            confidence: Model confidence (0-1)
            
        Returns:
            Stake amount
        """
        current_balance = self.balance
        
        if self.strategy == "fixed":
            return min(self.fixed_stake, current_balance)
        
        elif self.strategy == "percentage":
            return current_balance * self.percentage_stake
        
        elif self.strategy == "kelly":
            return self._kelly_stake(odds, confidence, current_balance)
        
        elif self.strategy == "unit":
            return self._unit_stake(confidence, current_balance)
        
        else:
            # Default to fixed
            return min(self.fixed_stake, current_balance)
    
    def _kelly_stake(self, odds: float, confidence: float,
                     balance: float) -> float:
        """
        Calculate Kelly criterion stake.
        
        Kelly formula: f* = (bp - q) / b
        where:
            f* = fraction of bankroll to bet
            b = decimal odds - 1
            p = probability of winning
            q = probability of losing (1 - p)
        """
        if odds <= 1 or confidence <= 0:
            return 0
        
        b = odds - 1  # Net odds
        p = confidence
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b
        
        # Use fractional Kelly (1/4) for safety
        kelly_fraction *= 0.25
        
        # Don't bet negative or more than 10% of bankroll
        kelly_fraction = max(0, min(kelly_fraction, 0.10))
        
        return balance * kelly_fraction
    
    def _unit_stake(self, confidence: float, balance: float) -> float:
        """
        Calculate unit-based stake.
        
        1 unit = 1% of bankroll
        Bet 1-3 units based on confidence
        """
        unit_size = balance * self.unit_size_percentage
        
        if confidence >= 0.65:
            units = 3
        elif confidence >= 0.55:
            units = 2
        else:
            units = 1
        
        return unit_size * units
    
    def place_bet(self, fixture_id: str, market_id: str, market_name: str,
                  outcome_id: str, outcome_name: str, odds: float,
                  confidence: float = 0.5, model_market: Optional[str] = None) -> Optional[int]:
        """
        Place a virtual bet.
        
        Args:
            fixture_id: Fixture ID
            market_id: Market ID
            market_name: Market name
            outcome_id: Outcome ID
            outcome_name: Outcome name
            odds: Bet odds
            confidence: Model confidence
            model_market: Model market type (1x2, over_under, btts) for tracking
            
        Returns:
            Bet ID or None if bet couldn't be placed
        """
        stake = self.calculate_stake(odds, confidence)
        
        if stake <= 0:
            return None
        
        if stake > self.balance:
            stake = self.balance
        
        if stake <= 0:
            return None
        
        bet_data = {
            "fixture_id": fixture_id,
            "market_id": market_id,
            "market_name": market_name,
            "outcome_id": outcome_id,
            "outcome_name": outcome_name,
            "odds": odds,
            "stake": stake,
            "model_market": model_market
        }
        
        bet_id = self.db.insert_bet(bet_data)
        
        # Refresh balance
        self._balance = None
        
        return bet_id
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get bankroll statistics with per-model breakdown.
        
        Returns:
            Dict with performance stats including per-model breakdown
        """
        stats = self.db.get_bankroll_stats()
        
        current_balance = self.balance
        profit = current_balance - self.starting_balance
        
        # Get per-model stats
        by_model = {}
        for market in ['1x2', 'over_under', 'btts']:
            model_stats = self.db.get_bankroll_stats_by_model(market)
            if model_stats.get("total_bets", 0) > 0:
                by_model[market] = model_stats
        
        return {
            "starting_balance": self.starting_balance,
            "current_balance": current_balance,
            "profit": profit,
            "roi": profit / self.starting_balance if self.starting_balance > 0 else 0,
            "total_bets": stats.get("total_bets", 0),
            "settled_bets": stats.get("settled_bets", 0),
            "pending_bets": stats.get("pending_bets", 0),
            "wins": stats.get("wins", 0),
            "losses": stats.get("losses", 0),
            "win_rate": stats.get("win_rate", 0),
            "total_stake": stats.get("total_stake", 0),
            "total_payout": stats.get("total_payout", 0),
            "strategy": self.strategy,
            "by_model": by_model
        }
    
    def get_stats_by_model(self, market: str) -> Dict[str, Any]:
        """
        Get bankroll statistics for a specific model market.
        
        Args:
            market: Model market type (1x2, over_under, btts)
            
        Returns:
            Dict with performance stats for the model
        """
        stats = self.db.get_bankroll_stats_by_model(market)
        
        current_balance = self.balance
        profit = current_balance - self.starting_balance
        
        return {
            "market": market,
            "starting_balance": self.starting_balance,
            "current_balance": current_balance,
            "profit": profit,
            "roi": profit / self.starting_balance if self.starting_balance > 0 else 0,
            "total_bets": stats.get("total_bets", 0),
            "settled_bets": stats.get("settled_bets", 0),
            "pending_bets": stats.get("pending_bets", 0),
            "wins": stats.get("wins", 0),
            "losses": stats.get("losses", 0),
            "win_rate": stats.get("win_rate", 0),
            "total_stake": stats.get("total_stake", 0),
            "total_payout": stats.get("total_payout", 0),
            "strategy": self.strategy
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate detailed performance report.
        
        Returns:
            Dict with comprehensive stats
        """
        stats = self.get_stats()
        
        # Get recent bets
        bets = self.db.get_bet_history(limit=1000)
        
        report = {
            **stats,
            "report_time": datetime.now().isoformat(),
        }
        
        if len(bets) > 0:
            # Calculate additional metrics
            settled = bets[bets['result'] != 'pending']
            
            if len(settled) > 0:
                report["avg_odds"] = settled['odds'].mean()
                report["avg_stake"] = settled['stake'].mean()
                report["avg_payout"] = settled[settled['result'] == 'win']['payout'].mean() if len(settled[settled['result'] == 'win']) > 0 else 0
                
                # Calculate profit by market
                profit_by_market = {}
                for market in settled['market_name'].unique():
                    market_bets = settled[settled['market_name'] == market]
                    market_profit = market_bets['payout'].sum() - market_bets['stake'].sum()
                    profit_by_market[market] = market_profit
                
                report["profit_by_market"] = profit_by_market
        
        return report
    
    def reset(self) -> None:
        """Reset bankroll (for testing purposes - clears bet history)."""
        # Note: This doesn't actually clear the database, just resets balance
        self._balance = self.starting_balance
