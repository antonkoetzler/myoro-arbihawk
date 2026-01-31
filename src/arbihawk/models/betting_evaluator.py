"""
Betting evaluator for evaluating models on profitability metrics.
Simulates betting on validation sets to calculate ROI, profit, Sharpe ratio, etc.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime

# Import pd for notna check
pd = pd

from data.database import Database
from engine.value_bet import ValueBetEngine
import config

if TYPE_CHECKING:
    from models.predictor import BettingPredictor


class BettingEvaluator:
    """
    Evaluates models on betting-specific metrics by simulating betting on validation sets.
    
    Calculates:
    - ROI (Return on Investment)
    - Profit/Loss
    - Sharpe Ratio
    - Win Rate
    - Total Bets
    
    Example:
        evaluator = BettingEvaluator(db, ev_threshold=0.07, market='1x2')
        metrics = evaluator.evaluate(
            predictor=predictor,
            X_val=X_val,
            y_val=y_val,
            dates=dates
        )
        print(f"ROI: {metrics['roi']:.2%}")
    """
    
    def __init__(self, db: Database, ev_threshold: float, market: str):
        """
        Initialize betting evaluator.
        
        Args:
            db: Database instance
            ev_threshold: Expected value threshold for placing bets
            market: Market type ('1x2', 'over_under', 'btts')
        """
        self.db = db
        self.ev_threshold = ev_threshold
        self.market = market
        self.value_bet_engine = None  # Will be set when predictor is available
        self.fixed_stake = config.FAKE_MONEY_CONFIG.get("fixed_stake", 100)
    
    def _get_fixtures_for_dates(self, dates: pd.Series) -> pd.DataFrame:
        """
        Get fixtures corresponding to validation dates.
        
        Args:
            dates: Series of match start times (ISO format)
            
        Returns:
            DataFrame of fixtures with fixture_id, home_score, away_score
        """
        if len(dates) == 0:
            return pd.DataFrame()
        
        # Get all fixtures and scores
        fixtures = self.db.get_fixtures()
        scores = self.db.get_scores()
        
        if len(fixtures) == 0 or len(scores) == 0:
            return pd.DataFrame()
        
        # Merge to get completed matches
        completed = fixtures.merge(scores, on='fixture_id', how='inner')
        
        if len(completed) == 0:
            return pd.DataFrame()
        
        # Convert dates to datetime for matching
        completed['start_time_dt'] = pd.to_datetime(completed['start_time'], errors='coerce', utc=True)
        dates_dt = pd.to_datetime(dates, errors='coerce', utc=True)
        
        # Filter to matches with matching dates (within tolerance)
        # Use merge on date to find matching fixtures
        completed = completed.dropna(subset=['start_time_dt'])
        
        # Create a date-only column for matching (ignore time component)
        completed['date_only'] = completed['start_time_dt'].dt.date
        dates_date_only = dates_dt.dt.date
        
        # Match by date (this is approximate - ideally we'd have fixture_ids)
        # For now, we'll match by date and hope there's only one match per date
        # This is a limitation - ideally fixture_ids would be passed in
        matched_fixtures = []
        for date_val in dates_date_only:
            matches = completed[completed['date_only'] == date_val]
            if len(matches) > 0:
                # Take first match if multiple (not ideal but works)
                matched_fixtures.append(matches.iloc[0])
        
        if len(matched_fixtures) == 0:
            return pd.DataFrame()
        
        result = pd.DataFrame(matched_fixtures)
        result = result.drop(columns=['start_time_dt', 'date_only'], errors='ignore')
        
        return result
    
    def _get_odds_at_time(self, fixture_id: str, prediction_time: str) -> pd.DataFrame:
        """
        Get odds available at prediction time (before match starts).
        
        Args:
            fixture_id: Fixture ID
            prediction_time: When prediction is made (ISO format)
            
        Returns:
            DataFrame of odds available at that time
        """
        # Get fixture to know match start time
        fixtures = self.db.get_fixtures()
        fixture = fixtures[fixtures['fixture_id'] == fixture_id]
        
        if len(fixture) == 0:
            return pd.DataFrame()
        
        match_start = fixture.iloc[0]['start_time']
        
        # Always filter odds by match start time to ensure we only use pre-match odds
        # This is critical for accurate backtesting - we can't use odds scraped after match completion
        try:
            match_start_dt = pd.to_datetime(match_start, utc=True)
            prediction_dt = pd.to_datetime(prediction_time, utc=True) if prediction_time else None
            
            # Always use match start as cutoff to ensure we only get pre-match odds
            # Use the earlier of prediction_time or match_start to be safe
            cutoff_time = min(prediction_time, match_start) if prediction_time else match_start
            odds = self.db.get_odds(fixture_id=fixture_id, before_date=cutoff_time)
        except:
            # Fallback: try to filter by match_start if available, otherwise get all (not ideal)
            try:
                odds = self.db.get_odds(fixture_id=fixture_id, before_date=match_start)
            except:
                odds = self.db.get_odds(fixture_id=fixture_id)
        
        # Filter by market
        if self.market == '1x2':
            # Try multiple market_id formats and market_name patterns
            odds = odds[
                odds['market_id'].isin(['1x2', '1X2', 'HOME_DRAW_AWAY', 'Match Result', 'Full Time Result']) |
                odds['market_name'].str.contains('1X2|1x2|Match Result|Full Time Result', case=False, na=False)
            ]
        elif self.market == 'over_under':
            odds = odds[
                odds['market_id'].isin(['OVER_UNDER', 'over_under']) |
                odds['market_name'].str.contains('Over|Under', case=False, na=False)
            ]
        elif self.market == 'btts':
            odds = odds[
                odds['market_id'].isin(['BOTH_TEAMS_TO_SCORE', 'btts', 'BTTS']) |
                odds['market_name'].str.contains('Both Teams|BTTS', case=False, na=False)
            ]
        
        # Get most recent odds for each outcome
        if len(odds) > 0:
            odds = odds.sort_values('created_at', ascending=False)
            odds = odds.groupby(['outcome_id', 'outcome_name'], as_index=False).first()
        
        return odds
    
    def _map_outcome_to_prob_col(self, outcome_name: str) -> Optional[str]:
        """Map outcome name to probability column name."""
        if self.market == '1x2':
            if outcome_name in ['1', 'Home', 'home_win']:
                return 'home_win'
            elif outcome_name in ['X', 'Draw', 'draw']:
                return 'draw'
            elif outcome_name in ['2', 'Away', 'away_win']:
                return 'away_win'
        elif self.market == 'over_under':
            if 'over' in outcome_name.lower():
                return 'over'
            elif 'under' in outcome_name.lower():
                return 'under'
        elif self.market == 'btts':
            if 'yes' in outcome_name.lower():
                return 'btts_yes'
            elif 'no' in outcome_name.lower():
                return 'btts_no'
        
        return None
    
    def _check_bet_won(self, prob_col: str, home_score: int, away_score: int) -> bool:
        """Check if a bet won based on actual scores."""
        if self.market == '1x2':
            if prob_col == 'home_win' and home_score > away_score:
                return True
            elif prob_col == 'draw' and home_score == away_score:
                return True
            elif prob_col == 'away_win' and away_score > home_score:
                return True
        elif self.market == 'over_under':
            total_goals = home_score + away_score
            if prob_col == 'over' and total_goals > 2.5:
                return True
            elif prob_col == 'under' and total_goals <= 2.5:
                return True
        elif self.market == 'btts':
            if prob_col == 'btts_yes' and home_score > 0 and away_score > 0:
                return True
            elif prob_col == 'btts_no' and (home_score == 0 or away_score == 0):
                return True
        
        return False
    
    def evaluate(self, predictor: 'BettingPredictor',
                 X_val: pd.DataFrame, y_val: pd.Series,
                 dates: pd.Series,
                 fixture_ids: Optional[pd.Series] = None) -> Dict[str, float]:
        """
        Evaluate model on betting metrics by simulating betting on validation set.
        
        Args:
            predictor: Trained predictor model
            X_val: Validation features
            y_val: Validation labels (actual outcomes)
            dates: Match dates (ISO format)
            fixture_ids: Optional fixture IDs (if not provided, will try to match by date)
            
        Returns:
            Dictionary with betting metrics:
            - roi: Return on investment (as decimal, e.g., 0.15 for 15%)
            - profit: Total profit/loss
            - sharpe_ratio: Sharpe ratio (annualized)
            - win_rate: Win rate (0-1)
            - total_bets: Number of bets placed
            - total_stake: Total amount staked
        """
        if not predictor.is_trained:
            raise ValueError("Predictor must be trained before evaluation")
        
        if len(X_val) == 0 or len(y_val) == 0:
            return {
                'roi': 0.0,
                'profit': 0.0,
                'sharpe_ratio': 0.0,
                'win_rate': 0.0,
                'total_bets': 0,
                'total_stake': 0.0
            }
        
        # Get predictions
        probabilities = predictor.predict_probabilities(X_val)
        
        if len(probabilities) == 0:
            return {
                'roi': 0.0,
                'profit': 0.0,
                'sharpe_ratio': 0.0,
                'win_rate': 0.0,
                'total_bets': 0,
                'total_stake': 0.0
            }
        
        # Get fixtures for validation set
        if fixture_ids is not None and len(fixture_ids) == len(X_val):
            # Use provided fixture IDs - build completed in same order as X_val
            fixtures = self.db.get_fixtures()
            scores = self.db.get_scores()
            all_completed = fixtures.merge(scores, on='fixture_id', how='inner')
            
            # Build completed DataFrame in same order as X_val using fixture_ids
            completed_rows = []
            for fid in fixture_ids:
                if pd.notna(fid):
                    match = all_completed[all_completed['fixture_id'] == fid]
                    if len(match) > 0:
                        completed_rows.append(match.iloc[0])
            
            if len(completed_rows) > 0:
                completed = pd.DataFrame(completed_rows)
            else:
                completed = pd.DataFrame()
        else:
            # Try to match by dates (less accurate)
            fixtures = self._get_fixtures_for_dates(dates)
            if len(fixtures) == 0:
                # Fallback: try to get all completed matches and match by index
                all_fixtures = self.db.get_fixtures()
                all_scores = self.db.get_scores()
                completed = all_fixtures.merge(all_scores, on='fixture_id', how='inner')
                # Sort by date and take last N matches (where N = len(X_val))
                completed = completed.sort_values('start_time')
                completed = completed.tail(len(X_val))
            else:
                completed = fixtures
        
        if len(completed) == 0:
            return {
                'roi': 0.0,
                'profit': 0.0,
                'sharpe_ratio': 0.0,
                'win_rate': 0.0,
                'total_bets': 0,
                'total_stake': 0.0
            }
        
        # Build mapping from fixture_id to X_val index for proper alignment
        fixture_to_idx = {}
        if fixture_ids is not None and len(fixture_ids) == len(X_val):
            for idx, fid in enumerate(fixture_ids):
                if pd.notna(fid):
                    fixture_to_idx[fid] = idx
        
        # Reset indices
        completed = completed.reset_index(drop=True)
        probabilities = probabilities.reset_index(drop=True)
        
        # Simulate betting
        bets = []
        market_margin = config.BOOKMAKER_MARGINS.get(self.market, 0.05)
        
        for completed_idx in range(len(completed)):
            try:
                fixture_id = completed.iloc[completed_idx]['fixture_id']
                home_score = completed.iloc[completed_idx].get('home_score', 0) or 0
                away_score = completed.iloc[completed_idx].get('away_score', 0) or 0
                match_date = completed.iloc[completed_idx]['start_time']
                
                # Get the correct X_val index for this fixture
                if fixture_id in fixture_to_idx:
                    x_val_idx = fixture_to_idx[fixture_id]
                else:
                    # Fallback: use completed_idx if mapping not available
                    x_val_idx = completed_idx
                
                # Ensure index is within bounds
                if x_val_idx >= len(probabilities):
                    continue
                
                # Get odds for this fixture (before match start)
                odds_df = self._get_odds_at_time(fixture_id, match_date)
                
                if len(odds_df) == 0:
                    continue
                
                # Get probabilities for this match
                match_probs = probabilities.iloc[x_val_idx]
                
                # Check each outcome for value
                for _, odd_row in odds_df.iterrows():
                    outcome_name = odd_row['outcome_name']
                    odds_value = odd_row['odds_value']
                    
                    # Map outcome to probability column
                    prob_col = self._map_outcome_to_prob_col(outcome_name)
                    
                    if prob_col and prob_col in match_probs.index:
                        probability = match_probs[prob_col]
                        
                        # Calculate EV using ValueBetEngine logic
                        implied_prob = 1.0 / odds_value
                        adjusted_implied_prob = implied_prob / (1.0 + market_margin)
                        ev = (probability - adjusted_implied_prob) * odds_value
                        
                        if ev >= self.ev_threshold:
                            # Check if bet won
                            won = self._check_bet_won(prob_col, home_score, away_score)
                            
                            bets.append({
                                'fixture_id': fixture_id,
                                'outcome': outcome_name,
                                'odds': odds_value,
                                'probability': probability,
                                'expected_value': ev,
                                'won': won,
                                'stake': self.fixed_stake,
                                'payout': self.fixed_stake * odds_value if won else 0,
                                'profit': (self.fixed_stake * odds_value if won else 0) - self.fixed_stake
                            })
            
            except Exception as e:
                # Skip fixtures with errors
                continue
        
        if len(bets) == 0:
            return {
                'roi': 0.0,
                'profit': 0.0,
                'sharpe_ratio': 0.0,
                'win_rate': 0.0,
                'total_bets': 0,
                'total_stake': 0.0
            }
        
        # Calculate metrics
        bets_df = pd.DataFrame(bets)
        
        total_bets = len(bets_df)
        total_stake = bets_df['stake'].sum()
        total_payout = bets_df['payout'].sum()
        profit = total_payout - total_stake
        roi = profit / total_stake if total_stake > 0 else 0.0
        
        wins = bets_df['won'].sum()
        win_rate = wins / total_bets if total_bets > 0 else 0.0
        
        # Calculate Sharpe ratio (annualized, assuming daily returns)
        returns = bets_df['profit'] / self.fixed_stake  # Normalize by stake
        if len(returns) > 1 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(365)  # Annualized
        else:
            sharpe_ratio = 0.0
        
        return {
            'roi': roi,
            'profit': profit,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'total_bets': total_bets,
            'total_stake': total_stake
        }
