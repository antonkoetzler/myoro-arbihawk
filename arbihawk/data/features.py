"""
Feature engineering for match data.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
from .database import Database


class FeatureEngineer:
    """Extracts features from stored match data."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_team_form(self, team_id: str, before_date: str, matches: int = 5) -> Dict[str, float]:
        """Get team form (last N matches) before a date."""
        # Get recent matches for the team
        fixtures = self.db.get_fixtures(to_date=before_date)
        scores = self.db.get_scores()
        
        # Filter matches involving this team
        team_matches = fixtures[
            (fixtures['home_team_id'] == team_id) | 
            (fixtures['away_team_id'] == team_id)
        ].merge(scores, on='fixture_id', how='inner')
        
        # Sort by date and take last N
        team_matches = team_matches.sort_values('start_time').tail(matches)
        
        if len(team_matches) == 0:
            return {
                'win_rate': 0.5,
                'avg_goals_scored': 1.0,
                'avg_goals_conceded': 1.0,
                'form_points': 0.0
            }
        
        wins = 0
        goals_scored = 0
        goals_conceded = 0
        points = 0
        
        for _, match in team_matches.iterrows():
            is_home = match['home_team_id'] == team_id
            home_score = match.get('home_score', 0) or 0
            away_score = match.get('away_score', 0) or 0
            
            if is_home:
                team_score = home_score
                opp_score = away_score
            else:
                team_score = away_score
                opp_score = home_score
            
            goals_scored += team_score
            goals_conceded += opp_score
            
            if team_score > opp_score:
                wins += 1
                points += 3
            elif team_score == opp_score:
                points += 1
        
        n = len(team_matches)
        return {
            'win_rate': wins / n if n > 0 else 0.5,
            'avg_goals_scored': goals_scored / n if n > 0 else 1.0,
            'avg_goals_conceded': goals_conceded / n if n > 0 else 1.0,
            'form_points': points / n if n > 0 else 0.0
        }
    
    def get_head_to_head(self, home_team_id: str, away_team_id: str,
                        before_date: str) -> Dict[str, float]:
        """Get head-to-head statistics."""
        fixtures = self.db.get_fixtures(to_date=before_date)
        scores = self.db.get_scores()
        
        # Get matches between these teams
        h2h_matches = fixtures[
            ((fixtures['home_team_id'] == home_team_id) & 
             (fixtures['away_team_id'] == away_team_id)) |
            ((fixtures['home_team_id'] == away_team_id) & 
             (fixtures['away_team_id'] == home_team_id))
        ].merge(scores, on='fixture_id', how='inner')
        
        if len(h2h_matches) == 0:
            return {
                'home_wins': 0,
                'draws': 0,
                'away_wins': 0,
                'home_avg_goals': 1.0,
                'away_avg_goals': 1.0
            }
        
        home_wins = 0
        draws = 0
        away_wins = 0
        home_goals = 0
        away_goals = 0
        
        for _, match in h2h_matches.iterrows():
            home_score = match.get('home_score', 0) or 0
            away_score = match.get('away_score', 0) or 0
            
            is_home_first = match['home_team_id'] == home_team_id
            
            if is_home_first:
                h_score = home_score
                a_score = away_score
            else:
                h_score = away_score
                a_score = home_score
            
            home_goals += h_score
            away_goals += a_score
            
            if h_score > a_score:
                home_wins += 1
            elif h_score == a_score:
                draws += 1
            else:
                away_wins += 1
        
        n = len(h2h_matches)
        return {
            'home_wins': home_wins,
            'draws': draws,
            'away_wins': away_wins,
            'home_avg_goals': home_goals / n if n > 0 else 1.0,
            'away_avg_goals': away_goals / n if n > 0 else 1.0
        }
    
    def get_home_away_performance(self, team_id: str, before_date: str,
                                  is_home: bool) -> Dict[str, float]:
        """Get team's home or away performance."""
        fixtures = self.db.get_fixtures(to_date=before_date)
        scores = self.db.get_scores()
        
        if is_home:
            team_matches = fixtures[fixtures['home_team_id'] == team_id]
        else:
            team_matches = fixtures[fixtures['away_team_id'] == team_id]
        
        team_matches = team_matches.merge(scores, on='fixture_id', how='inner')
        
        if len(team_matches) == 0:
            return {
                'win_rate': 0.5,
                'avg_goals_scored': 1.0,
                'avg_goals_conceded': 1.0
            }
        
        wins = 0
        goals_scored = 0
        goals_conceded = 0
        
        for _, match in team_matches.iterrows():
            home_score = match.get('home_score', 0) or 0
            away_score = match.get('away_score', 0) or 0
            
            if is_home:
                team_score = home_score
                opp_score = away_score
            else:
                team_score = away_score
                opp_score = home_score
            
            goals_scored += team_score
            goals_conceded += opp_score
            
            if team_score > opp_score:
                wins += 1
        
        n = len(team_matches)
        return {
            'win_rate': wins / n if n > 0 else 0.5,
            'avg_goals_scored': goals_scored / n if n > 0 else 1.0,
            'avg_goals_conceded': goals_conceded / n if n > 0 else 1.0
        }
    
    def get_odds_features(self, fixture_id: str, market_id: str = '1x2') -> Dict[str, float]:
        """Get odds features for a fixture."""
        odds = self.db.get_odds(fixture_id=fixture_id, market_id=market_id)
        
        if len(odds) == 0:
            return {
                'avg_home_odds': 2.0,
                'avg_draw_odds': 3.0,
                'avg_away_odds': 2.0,
                'max_home_odds': 2.0,
                'min_home_odds': 2.0
            }
        
        # Filter by outcome (assuming standard naming)
        home_odds = odds[odds['outcome_name'].isin(['1', 'Home', 'home_win'])]
        draw_odds = odds[odds['outcome_name'].isin(['X', 'Draw', 'draw'])]
        away_odds = odds[odds['outcome_name'].isin(['2', 'Away', 'away_win'])]
        
        return {
            'avg_home_odds': home_odds['odds_value'].mean() if len(home_odds) > 0 else 2.0,
            'avg_draw_odds': draw_odds['odds_value'].mean() if len(draw_odds) > 0 else 3.0,
            'avg_away_odds': away_odds['odds_value'].mean() if len(away_odds) > 0 else 2.0,
            'max_home_odds': home_odds['odds_value'].max() if len(home_odds) > 0 else 2.0,
            'min_home_odds': home_odds['odds_value'].min() if len(home_odds) > 0 else 2.0
        }
    
    def create_features(self, fixture_id: str) -> pd.Series:
        """Create feature vector for a fixture."""
        fixtures = self.db.get_fixtures()
        fixture = fixtures[fixtures['fixture_id'] == fixture_id]
        
        if len(fixture) == 0:
            raise ValueError(f"Fixture {fixture_id} not found")
        
        fixture = fixture.iloc[0]
        start_time = fixture['start_time']
        home_team_id = fixture['home_team_id']
        away_team_id = fixture['away_team_id']
        
        # Team form
        home_form = self.get_team_form(home_team_id, start_time)
        away_form = self.get_team_form(away_team_id, start_time)
        
        # Head-to-head
        h2h = self.get_head_to_head(home_team_id, away_team_id, start_time)
        
        # Home/away performance
        home_perf = self.get_home_away_performance(home_team_id, start_time, is_home=True)
        away_perf = self.get_home_away_performance(away_team_id, start_time, is_home=False)
        
        # Odds features
        odds_feat = self.get_odds_features(fixture_id)
        
        # Combine all features
        features = {
            # Home team form
            'home_win_rate': home_form['win_rate'],
            'home_avg_goals_scored': home_form['avg_goals_scored'],
            'home_avg_goals_conceded': home_form['avg_goals_conceded'],
            'home_form_points': home_form['form_points'],
            
            # Away team form
            'away_win_rate': away_form['win_rate'],
            'away_avg_goals_scored': away_form['avg_goals_scored'],
            'away_avg_goals_conceded': away_form['avg_goals_conceded'],
            'away_form_points': away_form['form_points'],
            
            # Head-to-head
            'h2h_home_wins': h2h['home_wins'],
            'h2h_draws': h2h['draws'],
            'h2h_away_wins': h2h['away_wins'],
            'h2h_home_avg_goals': h2h['home_avg_goals'],
            'h2h_away_avg_goals': h2h['away_avg_goals'],
            
            # Home/away performance
            'home_home_win_rate': home_perf['win_rate'],
            'home_home_avg_goals': home_perf['avg_goals_scored'],
            'away_away_win_rate': away_perf['win_rate'],
            'away_away_avg_goals': away_perf['avg_goals_scored'],
            
            # Odds
            'avg_home_odds': odds_feat['avg_home_odds'],
            'avg_draw_odds': odds_feat['avg_draw_odds'],
            'avg_away_odds': odds_feat['avg_away_odds'],
            'odds_spread': odds_feat['max_home_odds'] - odds_feat['min_home_odds']
        }
        
        return pd.Series(features)
    
    def create_training_data(self, market: str = '1x2') -> tuple:
        """Create training dataset with features and labels."""
        fixtures = self.db.get_fixtures()
        scores = self.db.get_scores()
        
        if len(fixtures) == 0 or len(scores) == 0:
            return pd.DataFrame(), pd.Series()
        
        # Get fixtures with scores (completed matches)
        completed = fixtures.merge(scores, on='fixture_id', how='inner')
        
        if len(completed) == 0:
            return pd.DataFrame(), pd.Series()
        
        features_list = []
        labels_list = []
        
        for _, row in completed.iterrows():
            try:
                features = self.create_features(row['fixture_id'])
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
            except Exception as e:
                print(f"Error creating features for fixture {row['fixture_id']}: {e}")
                continue
        
        if len(features_list) == 0:
            return pd.DataFrame(), pd.Series()
        
        X = pd.DataFrame(features_list)
        y = pd.Series(labels_list)
        
        return X, y

