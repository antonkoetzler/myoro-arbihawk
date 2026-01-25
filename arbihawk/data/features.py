"""
Feature engineering for match data.

Optimized implementation using data caching to avoid redundant database queries.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Callable, Tuple
from datetime import datetime
from .database import Database


class FeatureEngineer:
    """
    Extracts features from stored match data.
    
    Optimized for batch processing by caching data to avoid redundant DB queries.
    """
    
    # Default values for missing features
    DEFAULT_WIN_RATE = 0.5
    DEFAULT_AVG_GOALS = 1.0
    DEFAULT_FORM_POINTS = 0.0
    DEFAULT_HOME_ODDS = 2.0
    DEFAULT_DRAW_ODDS = 3.0
    DEFAULT_AWAY_ODDS = 2.0
    
    def __init__(self, db: Database):
        self.db = db
        # Cache for data
        self._fixtures_cache: Optional[pd.DataFrame] = None
        self._scores_cache: Optional[pd.DataFrame] = None
        self._odds_cache: Optional[pd.DataFrame] = None
        self._completed_cache: Optional[pd.DataFrame] = None
        # Cache for pre-computed features (indexed by fixture_id)
        self._features_cache: Optional[pd.DataFrame] = None
        # Pre-computed indexes for faster lookups
        self._team_match_index: Optional[Dict[str, pd.DataFrame]] = None
        self._odds_by_fixture: Optional[Dict[str, pd.DataFrame]] = None
    
    def _load_data(self) -> None:
        """Load all data into cache if not already loaded."""
        if self._fixtures_cache is None:
            self._fixtures_cache = self.db.get_fixtures()
        if self._scores_cache is None:
            self._scores_cache = self.db.get_scores()
        if self._odds_cache is None:
            self._odds_cache = self.db.get_odds()
        if self._completed_cache is None and self._fixtures_cache is not None and self._scores_cache is not None:
            if len(self._fixtures_cache) > 0 and len(self._scores_cache) > 0:
                self._completed_cache = self._fixtures_cache.merge(
                    self._scores_cache, on='fixture_id', how='inner'
                ).sort_values('start_time').reset_index(drop=True)
            else:
                self._completed_cache = pd.DataFrame()
        
        # Build odds index by fixture_id (fast using groupby)
        if self._odds_by_fixture is None and self._odds_cache is not None and len(self._odds_cache) > 0:
            self._odds_by_fixture = {
                fixture_id: group for fixture_id, group in self._odds_cache.groupby('fixture_id')
            }
        
        # Note: Team match index is built on-demand per team to avoid slow upfront cost
        if self._team_match_index is None:
            self._team_match_index = {}
    
    def invalidate_cache(self) -> None:
        """Invalidate all cached data. Call when new data is ingested."""
        self._fixtures_cache = None
        self._scores_cache = None
        self._odds_cache = None
        self._completed_cache = None
        self._features_cache = None
        self._team_match_index = None
        self._odds_by_fixture = None
    
    def _get_team_form_from_cache(self, team_id: str, before_date: str, matches: int = 5) -> Dict[str, float]:
        """Get team form using cached data (vectorized with lazy-indexed lookups)."""
        completed = self._completed_cache
        if completed is None or len(completed) == 0:
            return {
                'win_rate': self.DEFAULT_WIN_RATE,
                'avg_goals_scored': self.DEFAULT_AVG_GOALS,
                'avg_goals_conceded': self.DEFAULT_AVG_GOALS,
                'form_points': self.DEFAULT_FORM_POINTS
            }
        
        # Build team index lazily on first access
        if self._team_match_index is not None and team_id not in self._team_match_index:
            self._team_match_index[team_id] = completed[
                (completed['home_team_id'] == team_id) | (completed['away_team_id'] == team_id)
            ]
        
        # Use pre-computed team index
        if self._team_match_index is not None and team_id in self._team_match_index:
            team_data = self._team_match_index[team_id]
            team_matches = team_data[team_data['start_time'] < before_date].tail(matches)
        else:
            mask = ((completed['home_team_id'] == team_id) | (completed['away_team_id'] == team_id)) & \
                   (completed['start_time'] < before_date)
            team_matches = completed.loc[mask].tail(matches)
        
        n = len(team_matches)
        if n == 0:
            return {
                'win_rate': self.DEFAULT_WIN_RATE,
                'avg_goals_scored': self.DEFAULT_AVG_GOALS,
                'avg_goals_conceded': self.DEFAULT_AVG_GOALS,
                'form_points': self.DEFAULT_FORM_POINTS
            }
        
        # Vectorized calculations
        is_home = (team_matches['home_team_id'] == team_id).values
        home_scores = team_matches['home_score'].fillna(0).values.astype(int)
        away_scores = team_matches['away_score'].fillna(0).values.astype(int)
        
        team_scores = np.where(is_home, home_scores, away_scores)
        opp_scores = np.where(is_home, away_scores, home_scores)
        
        wins = np.sum(team_scores > opp_scores)
        draws = np.sum(team_scores == opp_scores)
        goals_scored = np.sum(team_scores)
        goals_conceded = np.sum(opp_scores)
        points = wins * 3 + draws
        
        return {
            'win_rate': wins / n,
            'avg_goals_scored': goals_scored / n,
            'avg_goals_conceded': goals_conceded / n,
            'form_points': points / n
        }
    
    def _get_h2h_from_cache(self, home_team_id: str, away_team_id: str, before_date: str) -> Dict[str, float]:
        """Get head-to-head stats using cached data (vectorized)."""
        completed = self._completed_cache
        
        if completed is None or len(completed) == 0:
            return {
                'home_wins': 0,
                'draws': 0,
                'away_wins': 0,
                'home_avg_goals': 1.0,
                'away_avg_goals': 1.0
            }
        
        mask = (((completed['home_team_id'] == home_team_id) & (completed['away_team_id'] == away_team_id)) |
                ((completed['home_team_id'] == away_team_id) & (completed['away_team_id'] == home_team_id))) & \
               (completed['start_time'] < before_date)
        h2h_matches = completed.loc[mask]
        
        n = len(h2h_matches)
        if n == 0:
            return {
                'home_wins': 0,
                'draws': 0,
                'away_wins': 0,
                'home_avg_goals': 1.0,
                'away_avg_goals': 1.0
            }
        
        # Vectorized calculations
        is_home_first = (h2h_matches['home_team_id'] == home_team_id).values
        home_scores = h2h_matches['home_score'].fillna(0).values.astype(int)
        away_scores = h2h_matches['away_score'].fillna(0).values.astype(int)
        
        # From perspective of home_team_id
        h_goals = np.where(is_home_first, home_scores, away_scores)
        a_goals = np.where(is_home_first, away_scores, home_scores)
        
        home_wins = int(np.sum(h_goals > a_goals))
        draws = int(np.sum(h_goals == a_goals))
        away_wins = int(np.sum(h_goals < a_goals))
        
        return {
            'home_wins': home_wins,
            'draws': draws,
            'away_wins': away_wins,
            'home_avg_goals': np.sum(h_goals) / n,
            'away_avg_goals': np.sum(a_goals) / n
        }
    
    def _get_home_away_perf_from_cache(self, team_id: str, before_date: str, is_home: bool) -> Dict[str, float]:
        """Get home/away performance using cached data (vectorized with lazy-indexed lookups)."""
        completed = self._completed_cache
        if completed is None or len(completed) == 0:
            return {
                'win_rate': self.DEFAULT_WIN_RATE,
                'avg_goals_scored': self.DEFAULT_AVG_GOALS,
                'avg_goals_conceded': self.DEFAULT_AVG_GOALS
            }
        
        # Build team index lazily on first access
        if self._team_match_index is not None and team_id not in self._team_match_index:
            self._team_match_index[team_id] = completed[
                (completed['home_team_id'] == team_id) | (completed['away_team_id'] == team_id)
            ]
        
        # Use pre-computed team index
        if self._team_match_index is not None and team_id in self._team_match_index:
            team_data = self._team_match_index[team_id]
            if is_home:
                team_matches = team_data[
                    (team_data['home_team_id'] == team_id) & (team_data['start_time'] < before_date)
                ]
            else:
                team_matches = team_data[
                    (team_data['away_team_id'] == team_id) & (team_data['start_time'] < before_date)
                ]
        else:
            if is_home:
                mask = (completed['home_team_id'] == team_id) & (completed['start_time'] < before_date)
            else:
                mask = (completed['away_team_id'] == team_id) & (completed['start_time'] < before_date)
            team_matches = completed.loc[mask]
        
        n = len(team_matches)
        if n == 0:
            return {
                'win_rate': self.DEFAULT_WIN_RATE,
                'avg_goals_scored': self.DEFAULT_AVG_GOALS,
                'avg_goals_conceded': self.DEFAULT_AVG_GOALS
            }
        
        # Vectorized calculations
        home_scores = team_matches['home_score'].fillna(0).values.astype(int)
        away_scores = team_matches['away_score'].fillna(0).values.astype(int)
        
        if is_home:
            team_scores = home_scores
            opp_scores = away_scores
        else:
            team_scores = away_scores
            opp_scores = home_scores
        
        wins = np.sum(team_scores > opp_scores)
        
        return {
            'win_rate': wins / n,
            'avg_goals_scored': np.sum(team_scores) / n,
            'avg_goals_conceded': np.sum(opp_scores) / n
        }
    
    def _get_odds_from_cache(self, fixture_id: str) -> Dict[str, float]:
        """Get odds features using cached data (with pre-indexed lookups)."""
        # Use pre-computed odds index if available
        if self._odds_by_fixture is not None:
            fixture_odds = self._odds_by_fixture.get(fixture_id)
            if fixture_odds is None or len(fixture_odds) == 0:
                return {
                    'avg_home_odds': self.DEFAULT_HOME_ODDS,
                    'avg_draw_odds': self.DEFAULT_DRAW_ODDS,
                    'avg_away_odds': self.DEFAULT_AWAY_ODDS,
                    'odds_spread': 0.0
                }
        else:
            odds = self._odds_cache
            if odds is None or len(odds) == 0:
                return {
                    'avg_home_odds': self.DEFAULT_HOME_ODDS,
                    'avg_draw_odds': self.DEFAULT_DRAW_ODDS,
                    'avg_away_odds': self.DEFAULT_AWAY_ODDS,
                    'odds_spread': 0.0
                }
            fixture_odds = odds[odds['fixture_id'] == fixture_id]
            if len(fixture_odds) == 0:
                return {
                    'avg_home_odds': self.DEFAULT_HOME_ODDS,
                    'avg_draw_odds': self.DEFAULT_DRAW_ODDS,
                    'avg_away_odds': self.DEFAULT_AWAY_ODDS,
                    'odds_spread': 0.0
                }
        
        # Use vectorized isin for outcome filtering
        outcome_names = fixture_odds['outcome_name'].values
        odds_values = fixture_odds['odds_value'].values
        
        home_mask = np.isin(outcome_names, ['1', 'Home', 'home_win'])
        draw_mask = np.isin(outcome_names, ['X', 'Draw', 'draw'])
        away_mask = np.isin(outcome_names, ['2', 'Away', 'away_win'])
        
        home_vals = odds_values[home_mask]
        draw_vals = odds_values[draw_mask]
        away_vals = odds_values[away_mask]
        
        avg_home = np.mean(home_vals) if len(home_vals) > 0 else self.DEFAULT_HOME_ODDS
        avg_draw = np.mean(draw_vals) if len(draw_vals) > 0 else self.DEFAULT_DRAW_ODDS
        avg_away = np.mean(away_vals) if len(away_vals) > 0 else self.DEFAULT_AWAY_ODDS
        max_home = np.max(home_vals) if len(home_vals) > 0 else self.DEFAULT_HOME_ODDS
        min_home = np.min(home_vals) if len(home_vals) > 0 else self.DEFAULT_HOME_ODDS
        
        return {
            'avg_home_odds': avg_home,
            'avg_draw_odds': avg_draw,
            'avg_away_odds': avg_away,
            'odds_spread': max_home - min_home
        }
    
    def create_features(self, fixture_id: str) -> pd.Series:
        """
        Create feature vector for a single fixture.
        
        Uses cached data for efficiency.
        
        Args:
            fixture_id: The fixture ID to create features for
            
        Returns:
            pd.Series with feature values
        """
        # Ensure data is loaded
        self._load_data()
        
        # Look up in features cache if available
        if self._features_cache is not None and fixture_id in self._features_cache.index:
            return self._features_cache.loc[fixture_id]
        
        # Get fixture info
        fixtures = self._fixtures_cache
        
        if fixtures is None or len(fixtures) == 0:
            raise ValueError(f"No fixtures in database")
        
        fixture = fixtures[fixtures['fixture_id'] == fixture_id]
        
        if len(fixture) == 0:
            raise ValueError(f"Fixture {fixture_id} not found")
        
        fixture = fixture.iloc[0]
        start_time = fixture['start_time']
        home_team_id = fixture['home_team_id']
        away_team_id = fixture['away_team_id']
        
        # Compute features using cached data
        home_form = self._get_team_form_from_cache(home_team_id, start_time)
        away_form = self._get_team_form_from_cache(away_team_id, start_time)
        h2h = self._get_h2h_from_cache(home_team_id, away_team_id, start_time)
        home_perf = self._get_home_away_perf_from_cache(home_team_id, start_time, is_home=True)
        away_perf = self._get_home_away_perf_from_cache(away_team_id, start_time, is_home=False)
        odds_feat = self._get_odds_from_cache(fixture_id)
        
        # Combine all features
        features = {
            'home_win_rate': home_form['win_rate'],
            'home_avg_goals_scored': home_form['avg_goals_scored'],
            'home_avg_goals_conceded': home_form['avg_goals_conceded'],
            'home_form_points': home_form['form_points'],
            'away_win_rate': away_form['win_rate'],
            'away_avg_goals_scored': away_form['avg_goals_scored'],
            'away_avg_goals_conceded': away_form['avg_goals_conceded'],
            'away_form_points': away_form['form_points'],
            'h2h_home_wins': h2h['home_wins'],
            'h2h_draws': h2h['draws'],
            'h2h_away_wins': h2h['away_wins'],
            'h2h_home_avg_goals': h2h['home_avg_goals'],
            'h2h_away_avg_goals': h2h['away_avg_goals'],
            'home_home_win_rate': home_perf['win_rate'],
            'home_home_avg_goals': home_perf['avg_goals_scored'],
            'away_away_win_rate': away_perf['win_rate'],
            'away_away_avg_goals': away_perf['avg_goals_scored'],
            'avg_home_odds': odds_feat['avg_home_odds'],
            'avg_draw_odds': odds_feat['avg_draw_odds'],
            'avg_away_odds': odds_feat['avg_away_odds'],
            'odds_spread': odds_feat['odds_spread']
        }
        
        return pd.Series(features)
    
    def create_training_data(self, log_callback: Optional[Callable[[str, str], None]] = None) -> Tuple[pd.DataFrame, Dict[str, pd.Series], pd.Series, pd.Series]:
        """
        Create training dataset with features and labels for all markets.
        
        This method computes features once and generates labels for all markets 
        (1x2, over_under, btts) in one pass.
        
        Features are computed using cached data to avoid redundant DB queries.
        
        Returns:
            Tuple of (X, labels, dates, fixture_ids) where:
            - X: DataFrame of features (indexed by position, fixture_id dropped)
            - labels: Dict mapping market name to Series of labels
            - dates: Series of match start times (for temporal splitting)
            - fixture_ids: Series of fixture IDs (for betting evaluation)
        """
        self._load_data()
        completed = self._completed_cache
        
        if completed is None or len(completed) == 0:
            return pd.DataFrame(), {}, pd.Series(), pd.Series()
        
        total_matches = len(completed)
        
        if log_callback:
            log_callback("info", f"  Computing features for {total_matches} matches...")
        
        features_list = []
        dates_list = []
        fixture_ids_list = []
        home_scores = []
        away_scores = []
        
        # Log progress every 10% or every 500 matches
        log_interval = max(1, min(500, total_matches // 10))
        
        for idx, (_, row) in enumerate(completed.iterrows(), 1):
            try:
                features = self.create_features(row['fixture_id'])
                features_list.append(features)
                dates_list.append(row['start_time'])
                fixture_ids_list.append(row['fixture_id'])
                home_scores.append(row.get('home_score', 0) or 0)
                away_scores.append(row.get('away_score', 0) or 0)
                
                # Log progress
                if log_callback and (idx % log_interval == 0 or idx == total_matches):
                    progress_pct = (idx / total_matches) * 100
                    log_callback("info", f"  Processing features: {idx}/{total_matches} ({progress_pct:.1f}%)")
                    
            except Exception as e:
                import logging
                logging.warning(f"Error creating features for fixture {row['fixture_id']}: {e}")
                continue
        
        if len(features_list) == 0:
            return pd.DataFrame(), {}, pd.Series(), pd.Series()
        
        X = pd.DataFrame(features_list)
        dates = pd.Series(dates_list)
        fixture_ids = pd.Series(fixture_ids_list)
        home_scores = pd.Series(home_scores)
        away_scores = pd.Series(away_scores)
        
        # Generate labels for all markets
        if log_callback:
            log_callback("info", "  -> Generating labels for all markets...")
        
        labels = {}
        
        # 1x2 labels
        labels['1x2'] = pd.Series(
            np.where(home_scores > away_scores, 'home_win',
                    np.where(home_scores == away_scores, 'draw', 'away_win'))
        )
        
        # Over/Under labels
        total_goals = home_scores + away_scores
        labels['over_under'] = pd.Series(
            np.where(total_goals > 2.5, 'over', 'under')
        )
        
        # BTTS labels
        labels['btts'] = pd.Series(
            np.where((home_scores > 0) & (away_scores > 0), 'yes', 'no')
        )
        
        if log_callback:
            log_callback("info", f"  Training data ready: {len(X)} samples, {len(X.columns)} features, 3 markets")
        
        return X, labels, dates, fixture_ids
    
    # Legacy method signatures for backward compatibility
    def get_team_form(self, team_id: str, before_date: str, matches: int = 5) -> Dict[str, float]:
        """Get team form (legacy method, uses cache)."""
        self._load_data()
        return self._get_team_form_from_cache(team_id, before_date, matches)
    
    def get_head_to_head(self, home_team_id: str, away_team_id: str, before_date: str) -> Dict[str, float]:
        """Get head-to-head statistics (legacy method, uses cache)."""
        self._load_data()
        return self._get_h2h_from_cache(home_team_id, away_team_id, before_date)
    
    def get_home_away_performance(self, team_id: str, before_date: str, is_home: bool) -> Dict[str, float]:
        """Get team's home or away performance (legacy method, uses cache)."""
        self._load_data()
        return self._get_home_away_perf_from_cache(team_id, before_date, is_home)
    
    def get_odds_features(self, fixture_id: str, market_id: str = '1x2') -> Dict[str, float]:
        """Get odds features for a fixture (legacy method, uses cache)."""
        self._load_data()
        return self._get_odds_from_cache(fixture_id)
