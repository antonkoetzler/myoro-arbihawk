"""
Value betting engine for identifying profitable bets.
"""

import pandas as pd
from typing import List, Dict, Any, Optional, TYPE_CHECKING
import config
from data.database import Database
from data.features import FeatureEngineer

if TYPE_CHECKING:
    from models.predictor import BettingPredictor


class ValueBetEngine:
    """
    Identifies value bets based on expected value calculations.
    
    Uses cached feature computation for efficiency when processing multiple fixtures.
    """
    
    def __init__(self, predictor: 'BettingPredictor', db: Database, ev_threshold: float = None):
        self.predictor = predictor
        self.db = db
        self.feature_engineer = FeatureEngineer(db)
        self.ev_threshold = ev_threshold or config.EV_THRESHOLD
        
        # Pre-load data into cache for efficient feature computation
        self.feature_engineer._load_data()
    
    def calculate_adjusted_implied_probability(self, odds: float, margin: float) -> float:
        """
        Calculate adjusted implied probability accounting for bookmaker margin.
        
        Args:
            odds: Decimal odds from bookmaker
            margin: Bookmaker margin (e.g., 0.05 for 5%)
            
        Returns:
            Adjusted implied probability (true probability after removing margin)
        """
        implied_prob = 1.0 / odds
        # Remove margin proportionally: adjusted = implied / (1 + margin)
        adjusted_implied_prob = implied_prob / (1.0 + margin)
        return adjusted_implied_prob
    
    def calculate_ev(self, probability: float, odds: float, margin: Optional[float] = None) -> float:
        """
        Calculate Expected Value accounting for bookmaker margin.
        
        Args:
            probability: Model's predicted probability
            odds: Decimal odds from bookmaker
            margin: Bookmaker margin (optional, if None uses simple EV calculation)
            
        Returns:
            Expected Value: (probability × odds) - 1, or margin-adjusted EV
        """
        if margin is not None and margin > 0:
            # Calculate adjusted implied probability (true probability)
            adjusted_implied_prob = self.calculate_adjusted_implied_probability(odds, margin)
            # EV = (model_prob - adjusted_implied_prob) × odds
            # This represents the edge we have over the true implied probability
            ev = (probability - adjusted_implied_prob) * odds
        else:
            # Simple EV calculation (backward compatibility)
            ev = (probability * odds) - 1
        return ev
    
    def find_value_bets(self, fixture_ids: List[str] = None, 
                       market: str = '1x2',
                       bookmakers: List[str] = None) -> pd.DataFrame:
        """
        Find value bets for given fixtures.
        
        Uses cached feature computation for efficiency.
        """
        if not self.predictor.is_trained:
            raise ValueError("Predictor must be trained before finding value bets")
        
        # Use cached fixtures if available
        if self.feature_engineer._fixtures_cache is not None:
            fixtures = self.feature_engineer._fixtures_cache.copy()
        else:
            fixtures = self.db.get_fixtures()
        
        # Filter fixtures
        if fixture_ids:
            fixtures = fixtures[fixtures['fixture_id'].isin(fixture_ids)]
        else:
            # Get upcoming fixtures
            from datetime import datetime, timedelta
            today = datetime.now().strftime('%Y-%m-%d')
            next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            fixtures = fixtures[
                (fixtures['start_time'] >= today) & 
                (fixtures['start_time'] <= next_week)
            ]
        
        if len(fixtures) == 0:
            return pd.DataFrame()
        
        value_bets = []
        
        for _, fixture in fixtures.iterrows():
            fixture_id = fixture['fixture_id']
            
            try:
                # Get features
                features = self.feature_engineer.create_features(fixture_id)
                features_df = pd.DataFrame([features])
                
                # Get probabilities
                probabilities = self.predictor.predict_probabilities(features_df)
                
                if len(probabilities) == 0:
                    continue
                
                # Get odds
                odds_query = self.db.get_odds(fixture_id=fixture_id)
                if bookmakers:
                    odds_query = odds_query[odds_query['bookmaker_id'].isin(bookmakers)]
                
                if len(odds_query) == 0:
                    continue
                
                # Check each outcome
                for _, odd_row in odds_query.iterrows():
                    outcome_name = odd_row['outcome_name']
                    odds_value = odd_row['odds_value']
                    bookmaker_name = odd_row['bookmaker_name']
                    market_name = odd_row['market_name']
                    
                    # Map outcome to probability column
                    prob_col = None
                    if market == '1x2':
                        if outcome_name in ['1', 'Home', 'home_win']:
                            prob_col = 'home_win'
                        elif outcome_name in ['X', 'Draw', 'draw']:
                            prob_col = 'draw'
                        elif outcome_name in ['2', 'Away', 'away_win']:
                            prob_col = 'away_win'
                    elif market == 'over_under':
                        if 'over' in outcome_name.lower():
                            prob_col = 'over'
                        elif 'under' in outcome_name.lower():
                            prob_col = 'under'
                    elif market == 'btts':
                        if 'yes' in outcome_name.lower():
                            prob_col = 'btts_yes'
                        elif 'no' in outcome_name.lower():
                            prob_col = 'btts_no'
                    
                    if prob_col and prob_col in probabilities.columns:
                        probability = probabilities[prob_col].iloc[0]
                        
                        # Get margin for this market
                        market_margin = config.BOOKMAKER_MARGINS.get(market, 0.05)  # Default 5% if market not found
                        ev = self.calculate_ev(probability, odds_value, margin=market_margin)
                        
                        if ev >= self.ev_threshold:
                            # Calculate adjusted implied probability for display
                            adjusted_implied_prob = self.calculate_adjusted_implied_probability(
                                odds_value, market_margin
                            )
                            
                            value_bets.append({
                                'fixture_id': fixture_id,
                                'home_team': fixture['home_team_name'],
                                'away_team': fixture['away_team_name'],
                                'start_time': fixture['start_time'],
                                'market': market_name,
                                'outcome': outcome_name,
                                'bookmaker': bookmaker_name,
                                'odds': odds_value,
                                'probability': probability,
                                'implied_probability': 1.0 / odds_value,
                                'adjusted_implied_probability': adjusted_implied_prob,
                                'expected_value': ev,
                                'ev_percentage': ev * 100
                            })
            
            except Exception as e:
                print(f"Error processing fixture {fixture_id}: {e}")
                continue
        
        if len(value_bets) == 0:
            return pd.DataFrame()
        
        result = pd.DataFrame(value_bets)
        result = result.sort_values('expected_value', ascending=False)
        
        return result
    
    def get_recommendations(self, limit: int = 10) -> pd.DataFrame:
        """Get top value bet recommendations."""
        value_bets = self.find_value_bets()
        
        if len(value_bets) == 0:
            return pd.DataFrame()
        
        return value_bets.head(limit)

