"""
Betting service for automated bet placement using trained models.
"""

from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import logging

from data.database import Database
from models.predictor import BettingPredictor
from models.versioning import ModelVersionManager
from engine.value_bet import ValueBetEngine
from testing.bankroll import VirtualBankroll
import config


logger = logging.getLogger(__name__)


class BettingService:
    """
    Service for placing bets based on model predictions.
    
    Loads active models, finds value bets, and places them via VirtualBankroll.
    """
    
    def __init__(self, db: Optional[Database] = None, bankroll: Optional[VirtualBankroll] = None, log_callback: Optional[Callable[[str, str], None]] = None):
        """
        Initialize betting service.
        
        Args:
            db: Database instance
            bankroll: VirtualBankroll instance
        """
        self.db = db or Database()
        self.bankroll = bankroll or VirtualBankroll(self.db)
        self.version_manager = ModelVersionManager(self.db)
        self.log_callback = log_callback
    
    def place_bets_for_all_models(self, limit_per_model: int = 10) -> Dict[str, Any]:
        """
        Place bets for all active models.
        
        Args:
            limit_per_model: Maximum bets to place per model
            
        Returns:
            Dict with summary of bets placed
        """
        markets = ['1x2', 'over_under', 'btts']
        results = {
            "success": True,
            "total_bets_placed": 0,
            "total_stake": 0.0,
            "by_model": {},
            "errors": []
        }
        
        if self.log_callback:
            self.log_callback("info", f"Processing {len(markets)} models for betting...")
        
        for market in markets:
            try:
                model_result = self.place_bets_for_model(market, limit=limit_per_model)
                results["by_model"][market] = model_result
                results["total_bets_placed"] += model_result.get("bets_placed", 0)
                results["total_stake"] += model_result.get("total_stake", 0.0)
                
                if not model_result.get("success", False):
                    results["errors"].append(f"{market}: {model_result.get('error', 'Unknown error')}")
            except Exception as e:
                error_msg = f"Error placing bets for {market}: {str(e)}"
                if self.log_callback:
                    self.log_callback("error", error_msg)
                else:
                    logger.error(error_msg, exc_info=True)
                results["errors"].append(error_msg)
                results["by_model"][market] = {
                    "success": False,
                    "error": str(e),
                    "bets_placed": 0,
                    "total_stake": 0.0
                }
        
        if len(results["errors"]) > 0:
            results["success"] = False
        
        if self.log_callback:
            if results["total_bets_placed"] > 0:
                self.log_callback("success", f"✓ Betting complete: {results['total_bets_placed']} total bets placed, ${results['total_stake']:.2f} total stake")
            else:
                self.log_callback("info", "Betting complete: No bets placed")
        
        return results
    
    def place_bets_for_model(self, market: str, limit: int = 10) -> Dict[str, Any]:
        """
        Place bets for a specific model market.
        
        Args:
            market: Market type (1x2, over_under, btts)
            limit: Maximum number of bets to place
            
        Returns:
            Dict with betting results
        """
        result = {
            "success": False,
            "market": market,
            "bets_placed": 0,
            "total_stake": 0.0,
            "bet_ids": [],
            "error": None
        }
        
        try:
            if self.log_callback:
                self.log_callback("info", f"Processing {market} market...")
            
            # Get active model version
            active_version = self.version_manager.get_active_version(market)
            if not active_version:
                result["error"] = f"No active model found for {market}"
                if self.log_callback:
                    self.log_callback("warning", f"No active model found for {market}")
                return result
            
            model_path = active_version.get('model_path')
            if not model_path or not Path(model_path).exists():
                result["error"] = f"Model file not found: {model_path}"
                if self.log_callback:
                    self.log_callback("error", result["error"])
                return result
            
            # Load model
            if self.log_callback:
                self.log_callback("info", f"-> Loading model from {model_path}")
            predictor = BettingPredictor(market=market)
            predictor.load(model_path)
            
            if not predictor.is_trained:
                result["error"] = f"Model for {market} is not trained"
                if self.log_callback:
                    self.log_callback("error", result["error"])
                return result
            
            # Create value bet engine
            if self.log_callback:
                self.log_callback("info", f"-> Finding value bets (EV threshold: {config.EV_THRESHOLD})...")
            engine = ValueBetEngine(predictor, self.db, ev_threshold=config.EV_THRESHOLD)
            
            # Find value bets - map market names
            # ValueBetEngine expects market names like '1x2', 'over_under', 'btts'
            value_bets = engine.find_value_bets(market=market)
            
            if len(value_bets) == 0:
                result["success"] = True
                result["error"] = "No value bets found"
                if self.log_callback:
                    self.log_callback("info", f"No value bets found for {market}")
                return result
            
            if self.log_callback:
                self.log_callback("info", f"Found {len(value_bets)} value bets, limiting to top {limit}")
            
            # Limit to top N bets
            value_bets = value_bets.head(limit)
            
            # Place bets
            if self.log_callback:
                self.log_callback("info", f"-> Placing bets...")
            bets_placed = 0
            total_stake = 0.0
            bet_ids = []
            
            for idx, bet_row in value_bets.iterrows():
                try:
                    # Get confidence from probability
                    confidence = bet_row.get('probability', 0.5)
                    
                    # Calculate stake before placing (to track it)
                    stake = self.bankroll.calculate_stake(bet_row['odds'], confidence)
                    if stake <= 0 or stake > self.bankroll.balance:
                        if self.log_callback:
                            self.log_callback("warning", f"Skipping bet (stake: ${stake:.2f}, balance: ${self.bankroll.balance:.2f})")
                        continue
                    
                    # Place bet
                    bet_id = self.bankroll.place_bet(
                        fixture_id=bet_row['fixture_id'],
                        market_id=bet_row.get('market', ''),
                        market_name=bet_row.get('market', ''),
                        outcome_id=bet_row.get('outcome', ''),
                        outcome_name=bet_row.get('outcome', ''),
                        odds=bet_row['odds'],
                        confidence=confidence,
                        model_market=market
                    )
                    
                    if bet_id:
                        bets_placed += 1
                        total_stake += stake
                        bet_ids.append(bet_id)
                        if self.log_callback:
                            outcome = bet_row.get('outcome', 'unknown')
                            self.log_callback("info", f"  ✓ Placed bet #{bet_id}: {outcome} @ {bet_row['odds']:.2f} odds, ${stake:.2f} stake")
                except Exception as e:
                    if self.log_callback:
                        self.log_callback("warning", f"Failed to place bet: {e}")
                    else:
                        logger.warning(f"Failed to place bet for {bet_row.get('fixture_id')}: {e}")
                    continue
            
            result["success"] = True
            result["bets_placed"] = bets_placed
            result["total_stake"] = total_stake
            result["bet_ids"] = bet_ids
            
            if self.log_callback:
                if bets_placed > 0:
                    self.log_callback("success", f"✓ {market}: {bets_placed} bets placed, ${total_stake:.2f} total stake")
                else:
                    self.log_callback("info", f"{market}: No bets placed")
            
        except Exception as e:
            result["error"] = str(e)
            if self.log_callback:
                self.log_callback("error", f"Error processing {market}: {e}")
            else:
                logger.error(f"Error in place_bets_for_model for {market}: {e}", exc_info=True)
        
        return result
