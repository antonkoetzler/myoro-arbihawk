"""
Value betting engine for identifying profitable bets.
"""

import pandas as pd
from typing import List, Dict, Any
import config
from models.predictor import BettingPredictor
from data.database import Database
from data.features import FeatureEngineer


class ValueBetEngine:
    """Identifies value bets based on expected value calculations."""
    
    def __init__(self, predictor: BettingPredictor, db: Database, ev_threshold: float = None):
        self.predictor = predictor
        self.db = db
        self.feature_engineer = FeatureEngineer(db)
        self.ev_threshold = ev_threshold or config.EV_THRESHOLD
    
    def calculate_ev(self, probability: float, odds: float) -> float:
        """Calculate Expected Value: (Probability × Odds) - 1"""
        return (probability * odds) - 1
    
    def find_value_bets(self, fixture_ids: List[str] = None, 
                       market: str = '1x2',
                       bookmakers: List[str] = None) -> pd.DataFrame:
        """Find value bets for given fixtures."""
        if not self.predictor.is_trained:
            raise ValueError("Predictor must be trained before finding value bets")
        
        # Get fixtures
        if fixture_ids:
            fixtures = self.db.get_fixtures()
            fixtures = fixtures[fixtures['fixture_id'].isin(fixture_ids)]
        else:
            # Get upcoming fixtures
            from datetime import datetime, timedelta
            today = datetime.now().strftime('%Y-%m-%d')
            next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            fixtures = self.db.get_fixtures(from_date=today, to_date=next_week)
        
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
                        ev = self.calculate_ev(probability, odds_value)
                        
                        if ev >= self.ev_threshold:
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

