"""
Backtesting engine for temporal validation of betting models.
Implements walk-forward validation to simulate historical betting performance.

Optimized to use vectorized feature computation and data caching.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging

from data.database import Database
from data.features import FeatureEngineer
from models.predictor import BettingPredictor
from engine.value_bet import ValueBetEngine
from testing.bankroll import VirtualBankroll
import config

logger = logging.getLogger(__name__)


class BacktestResult:
    """Results from a backtest run."""
    
    def __init__(self):
        self.periods: List[Dict[str, Any]] = []
        self.overall_metrics: Dict[str, Any] = {}
        self.by_market: Dict[str, Dict[str, Any]] = {}
        self.bets: List[Dict[str, Any]] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary."""
        return {
            "periods": self.periods,
            "overall_metrics": self.overall_metrics,
            "by_market": self.by_market,
            "total_bets": len(self.bets),
            "bets": self.bets[:100]  # Limit to first 100 for summary
        }


class BacktestEngine:
    """
    Backtesting engine for temporal validation of betting models.
    
    Implements walk-forward validation:
    1. Split data into temporal periods
    2. For each test period:
       - Train model on all data before the period
       - Make predictions on test period matches
       - Simulate betting with odds available at prediction time
       - Track results when scores are available
    3. Aggregate performance metrics
    
    Uses cached feature computation for efficiency.
    
    Example:
        engine = BacktestEngine()
        result = engine.run_backtest(
            train_start="2024-01-01",
            test_start="2024-06-01",
            test_end="2024-12-31",
            period_days=30
        )
        print(f"ROI: {result.overall_metrics['roi']:.2%}")
    """
    
    def __init__(self, db: Optional[Database] = None, 
                 ev_threshold: Optional[float] = None,
                 starting_balance: Optional[float] = None):
        """
        Initialize backtest engine.
        
        Args:
            db: Database instance
            ev_threshold: EV threshold for placing bets
            starting_balance: Starting bankroll balance
        """
        self.db = db or Database()
        self.ev_threshold = ev_threshold or config.EV_THRESHOLD
        self.starting_balance = starting_balance or config.FAKE_MONEY_CONFIG.get("starting_balance", 10000)
        self.feature_engineer = FeatureEngineer(self.db)
        
        # Pre-load data into cache
        self.feature_engineer._load_data()
    
    def _split_temporal_periods(self, train_start: str, test_start: str, 
                                test_end: str, period_days: int = 30) -> List[Tuple[str, str]]:
        """
        Split test period into smaller temporal windows.
        
        Args:
            train_start: Start date for training data (ISO format)
            test_start: Start date for test period (ISO format)
            test_end: End date for test period (ISO format)
            period_days: Number of days per test window
            
        Returns:
            List of (period_start, period_end) tuples
        """
        periods = []
        current_start = datetime.fromisoformat(test_start)
        test_end_dt = datetime.fromisoformat(test_end)
        
        while current_start < test_end_dt:
            period_end = min(current_start + timedelta(days=period_days), test_end_dt)
            periods.append((
                current_start.isoformat(),
                period_end.isoformat()
            ))
            current_start = period_end
        
        return periods
    
    def _get_training_data(self, before_date: str, market: str) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Get training data up to a specific date.
        
        Uses cached data from FeatureEngineer for efficiency.
        
        Args:
            before_date: Only use matches before this date
            market: Market type (1x2, over_under, btts)
            
        Returns:
            Tuple of (features, labels)
        """
        # Use cached completed matches from feature engineer
        self.feature_engineer._load_data()
        completed = self.feature_engineer._completed_cache
        
        if completed is None or len(completed) == 0:
            return pd.DataFrame(), pd.Series()
        
        # Filter by date - handle different date formats and timezones
        completed_filtered = completed.copy()
        completed_filtered['start_time_dt'] = pd.to_datetime(completed_filtered['start_time'], errors='coerce', utc=True)
        before_dt = pd.to_datetime(before_date, errors='coerce', utc=True)
        
        # Drop rows where conversion failed
        completed_filtered = completed_filtered.dropna(subset=['start_time_dt'])
        
        if before_dt is not pd.NaT:
            completed_filtered = completed_filtered[completed_filtered['start_time_dt'] < before_dt]
        
        if len(completed_filtered) == 0:
            return pd.DataFrame(), pd.Series()
        
        # Get features from cache (this uses the pre-computed features)
        features_list = []
        labels_list = []
        valid_indices = []
        
        for idx, row in completed_filtered.iterrows():
            try:
                # Use cached create_features - much faster than before
                features = self.feature_engineer.create_features(row['fixture_id'])
                features_list.append(features)
                
                # Create label based on outcome
                home_score = row.get('home_score', 0) or 0
                away_score = row.get('away_score', 0) or 0
                
                if market == '1x2':
                    if home_score > away_score:
                        label = 'home_win'
                    elif home_score == away_score:
                        label = 'draw'
                    else:
                        label = 'away_win'
                elif market == 'over_under':
                    total_goals = home_score + away_score
                    label = 'over' if total_goals > 2.5 else 'under'
                elif market == 'btts':
                    label = 'yes' if home_score > 0 and away_score > 0 else 'no'
                else:
                    label = 'home_win' if home_score > away_score else 'away_win'
                
                labels_list.append(label)
                valid_indices.append(idx)
            except Exception as e:
                logger.warning(f"Error creating features for fixture {row['fixture_id']}: {e}")
                continue
        
        if len(features_list) == 0:
            return pd.DataFrame(), pd.Series()
        
        X = pd.DataFrame(features_list)
        y = pd.Series(labels_list)
        
        return X, y
    
    def _get_test_fixtures(self, period_start: str, period_end: str) -> pd.DataFrame:
        """Get fixtures in test period that have scores (completed matches)."""
        # Use cached data
        self.feature_engineer._load_data()
        completed = self.feature_engineer._completed_cache
        
        if completed is None or len(completed) == 0:
            return pd.DataFrame()
        
        # Filter by date range
        completed_filtered = completed.copy()
        completed_filtered['start_time_dt'] = pd.to_datetime(completed_filtered['start_time'], errors='coerce', utc=True)
        start_dt = pd.to_datetime(period_start, errors='coerce', utc=True)
        end_dt = pd.to_datetime(period_end, errors='coerce', utc=True)
        
        completed_filtered = completed_filtered.dropna(subset=['start_time_dt'])
        
        if start_dt is not pd.NaT and end_dt is not pd.NaT:
            completed_filtered = completed_filtered[
                (completed_filtered['start_time_dt'] >= start_dt) &
                (completed_filtered['start_time_dt'] < end_dt)
            ]
        
        return completed_filtered.drop(columns=['start_time_dt'], errors='ignore')
    
    def _get_odds_at_time(self, fixture_id: str, prediction_time: str, 
                          market: str) -> pd.DataFrame:
        """
        Get odds available at prediction time (before match starts).
        
        Args:
            fixture_id: Fixture ID
            prediction_time: When prediction is made (ISO format)
            market: Market type to filter
            
        Returns:
            DataFrame of odds available at that time
        """
        # Use cached fixtures
        self.feature_engineer._load_data()
        fixtures = self.feature_engineer._fixtures_cache
        
        if fixtures is None or len(fixtures) == 0:
            return pd.DataFrame()
        
        fixture = fixtures[fixtures['fixture_id'] == fixture_id]
        
        if len(fixture) == 0:
            return pd.DataFrame()
        
        match_start = fixture.iloc[0]['start_time']
        
        # Get odds created before prediction time (and before match starts)
        # Use the earlier of prediction_time or match_start
        # ISO format strings are sortable, so we can compare directly
        cutoff_time = min(prediction_time, match_start)
        
        odds = self.db.get_odds(fixture_id=fixture_id, before_date=cutoff_time)
        
        # Filter by market if needed
        if market == '1x2':
            odds = odds[odds['market_id'].isin(['1x2', 'Match Result', 'Full Time Result'])]
        elif market == 'over_under':
            odds = odds[odds['market_name'].str.contains('Over|Under', case=False, na=False)]
        elif market == 'btts':
            odds = odds[odds['market_name'].str.contains('Both Teams|BTTS', case=False, na=False)]
        
        # Get most recent odds for each outcome (in case odds were updated)
        if len(odds) > 0:
            odds = odds.sort_values('created_at', ascending=False)
            # Group by outcome and take first (most recent) - keep all columns
            odds = odds.groupby(['outcome_id', 'outcome_name'], as_index=False).first()
        
        return odds
    
    def _simulate_betting(self, predictor: BettingPredictor, test_fixtures: pd.DataFrame,
                         period_start: str, market: str) -> List[Dict[str, Any]]:
        """
        Simulate betting on test period fixtures.
        
        Uses cached feature computation for efficiency.
        
        Args:
            predictor: Trained predictor model
            test_fixtures: Fixtures to bet on
            period_start: Start of test period (used as prediction time)
            market: Market type
            
        Returns:
            List of bet records
        """
        bets = []
        
        for _, fixture in test_fixtures.iterrows():
            fixture_id = fixture['fixture_id']
            
            try:
                # Get features from cache (respects time ordering via FeatureEngineer)
                features = self.feature_engineer.create_features(fixture_id)
                features_df = pd.DataFrame([features])
                
                # Get probabilities
                probabilities = predictor.predict_probabilities(features_df)
                
                if len(probabilities) == 0:
                    continue
                
                # Get odds available at prediction time
                odds_df = self._get_odds_at_time(fixture_id, period_start, market)
                
                if len(odds_df) == 0:
                    continue
                
                # Check each outcome for value
                for _, odd_row in odds_df.iterrows():
                    outcome_name = odd_row['outcome_name']
                    odds_value = odd_row['odds_value']
                    
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
                        
                        # Get margin for this market and calculate margin-adjusted EV
                        market_margin = config.BOOKMAKER_MARGINS.get(market, 0.05)  # Default 5% if market not found
                        # Calculate adjusted implied probability
                        implied_prob = 1.0 / odds_value
                        adjusted_implied_prob = implied_prob / (1.0 + market_margin)
                        # EV = (model_prob - adjusted_implied_prob) × odds
                        ev = (probability - adjusted_implied_prob) * odds_value
                        
                        if ev >= self.ev_threshold:
                            # Determine actual outcome
                            home_score = fixture.get('home_score', 0) or 0
                            away_score = fixture.get('away_score', 0) or 0
                            
                            # Check if bet won
                            won = False
                            if market == '1x2':
                                if prob_col == 'home_win' and home_score > away_score:
                                    won = True
                                elif prob_col == 'draw' and home_score == away_score:
                                    won = True
                                elif prob_col == 'away_win' and away_score > home_score:
                                    won = True
                            elif market == 'over_under':
                                total_goals = home_score + away_score
                                if prob_col == 'over' and total_goals > 2.5:
                                    won = True
                                elif prob_col == 'under' and total_goals <= 2.5:
                                    won = True
                            elif market == 'btts':
                                if prob_col == 'btts_yes' and home_score > 0 and away_score > 0:
                                    won = True
                                elif prob_col == 'btts_no' and (home_score == 0 or away_score == 0):
                                    won = True
                            
                            bets.append({
                                'fixture_id': fixture_id,
                                'home_team': fixture['home_team_name'],
                                'away_team': fixture['away_team_name'],
                                'start_time': fixture['start_time'],
                                'market': market,
                                'outcome': outcome_name,
                                'odds': odds_value,
                                'probability': probability,
                                'expected_value': ev,
                                'won': won,
                                'home_score': home_score,
                                'away_score': away_score
                            })
            
            except Exception as e:
                logger.warning(f"Error processing fixture {fixture_id} in backtest: {e}")
                continue
        
        return bets
    
    def _calculate_metrics(self, bets: List[Dict[str, Any]], 
                          starting_balance: float) -> Dict[str, Any]:
        """
        Calculate performance metrics from bet results.
        
        Args:
            bets: List of bet records
            starting_balance: Starting bankroll
            
        Returns:
            Dictionary of metrics
        """
        if len(bets) == 0:
            return {
                'total_bets': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'roi': 0.0,
                'profit': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0
            }
        
        bets_df = pd.DataFrame(bets)
        
        # Calculate profit/loss for each bet (assuming fixed stake for simplicity)
        # In real backtest, you'd use actual stake from bankroll strategy
        fixed_stake = config.FAKE_MONEY_CONFIG.get("fixed_stake", 100)
        
        bets_df['stake'] = fixed_stake
        bets_df['payout'] = bets_df.apply(
            lambda row: row['stake'] * row['odds'] if row['won'] else 0,
            axis=1
        )
        bets_df['profit'] = bets_df['payout'] - bets_df['stake']
        
        total_bets = len(bets_df)
        wins = bets_df['won'].sum()
        losses = total_bets - wins
        win_rate = wins / total_bets if total_bets > 0 else 0.0
        
        total_stake = bets_df['stake'].sum()
        total_payout = bets_df['payout'].sum()
        profit = total_payout - total_stake
        roi = profit / total_stake if total_stake > 0 else 0.0
        
        # Calculate cumulative returns for Sharpe and drawdown
        bets_df = bets_df.sort_values('start_time')
        bets_df['cumulative_profit'] = bets_df['profit'].cumsum()
        bets_df['cumulative_return'] = (bets_df['cumulative_profit'] + starting_balance) / starting_balance
        
        # Sharpe ratio (annualized, assuming daily returns)
        returns = bets_df['profit'] / starting_balance
        if len(returns) > 1 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(365)  # Annualized
        else:
            sharpe_ratio = 0.0
        
        # Max drawdown
        cumulative_returns = bets_df['cumulative_return']
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0.0
        
        return {
            'total_bets': total_bets,
            'wins': int(wins),
            'losses': int(losses),
            'win_rate': win_rate,
            'roi': roi,
            'profit': profit,
            'total_stake': total_stake,
            'total_payout': total_payout,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'avg_odds': bets_df['odds'].mean(),
            'avg_probability': bets_df['probability'].mean(),
            'avg_ev': bets_df['expected_value'].mean()
        }
    
    def run_backtest(self, train_start: str, test_start: str, test_end: str,
                    markets: List[str] = None, period_days: int = 30,
                    min_training_samples: int = 50) -> BacktestResult:
        """
        Run backtest with walk-forward validation.
        
        Args:
            train_start: Start date for training data (ISO format)
            test_start: Start date for test period (ISO format)
            test_end: End date for test period (ISO format)
            markets: List of markets to test (default: all)
            period_days: Days per test window
            min_training_samples: Minimum samples required to train model
            
        Returns:
            BacktestResult with performance metrics
        """
        if markets is None:
            markets = ['1x2', 'over_under', 'btts']
        
        result = BacktestResult()
        all_bets = []
        
        # Pre-load data into cache for efficiency
        self.feature_engineer._load_data()
        
        # Pre-compute features for all fixtures (this populates the features cache)
        logger.info("Pre-computing features for all fixtures...")
        self.feature_engineer._compute_all_features_vectorized()
        
        # Split test period into windows
        periods = self._split_temporal_periods(train_start, test_start, test_end, period_days)
        
        logger.info(f"Running backtest: {len(periods)} periods, markets: {markets}")
        
        for period_idx, (period_start, period_end) in enumerate(periods):
            logger.info(f"Period {period_idx + 1}/{len(periods)}: {period_start} to {period_end}")
            
            period_bets = []
            
            for market in markets:
                try:
                    # Get training data up to period start (uses cached features)
                    X_train, y_train = self._get_training_data(period_start, market)
                    
                    if len(X_train) < min_training_samples:
                        logger.warning(f"Insufficient training data for {market}: {len(X_train)} < {min_training_samples}")
                        continue
                    
                    # Train model
                    predictor = BettingPredictor(market=market)
                    predictor.train(X_train, y_train)
                    
                    # Get test fixtures
                    test_fixtures = self._get_test_fixtures(period_start, period_end)
                    
                    if len(test_fixtures) == 0:
                        continue
                    
                    # Simulate betting (uses cached features)
                    bets = self._simulate_betting(predictor, test_fixtures, period_start, market)
                    
                    # Add market info to bets
                    for bet in bets:
                        bet['period_start'] = period_start
                        bet['period_end'] = period_end
                        bet['training_samples'] = len(X_train)
                    
                    period_bets.extend(bets)
                    all_bets.extend(bets)
                    
                except Exception as e:
                    logger.error(f"Error in backtest for {market} period {period_start}: {e}")
                    continue
            
            # Calculate period metrics
            if len(period_bets) > 0:
                period_metrics = self._calculate_metrics(period_bets, self.starting_balance)
                period_metrics['period_start'] = period_start
                period_metrics['period_end'] = period_end
                result.periods.append(period_metrics)
        
        # Calculate overall metrics
        if len(all_bets) > 0:
            result.overall_metrics = self._calculate_metrics(all_bets, self.starting_balance)
            
            # Calculate metrics by market
            for market in markets:
                market_bets = [b for b in all_bets if b['market'] == market]
                if len(market_bets) > 0:
                    result.by_market[market] = self._calculate_metrics(market_bets, self.starting_balance)
            
            result.bets = all_bets
        
        return result
