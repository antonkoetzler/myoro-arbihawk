"""
Base predictor class for betting predictions.
Designed to be extended with specific model implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder


class BasePredictor(ABC):
    """Base class for all prediction models."""
    
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.label_encoder = LabelEncoder()
    
    @abstractmethod
    def train(self, features: pd.DataFrame, labels: pd.Series) -> None:
        """Train the model on historical data."""
        pass
    
    @abstractmethod
    def predict_probabilities(self, features: pd.DataFrame) -> pd.DataFrame:
        """Predict outcome probabilities."""
        pass
    
    @abstractmethod
    def predict(self, features: pd.DataFrame) -> pd.Series:
        """Predict most likely outcome."""
        pass
    
    def save(self, filepath: str) -> None:
        """Save model to file."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'label_encoder': self.label_encoder,
                'is_trained': self.is_trained,
                'cv_score': getattr(self, 'cv_score', 0.0)
            }, f)
    
    def load(self, filepath: str) -> None:
        """Load model from file."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.label_encoder = data['label_encoder']
            self.is_trained = data['is_trained']
            self.cv_score = data.get('cv_score', 0.0)


class BettingPredictor(BasePredictor):
    """Main predictor for betting recommendations using XGBoost."""
    
    def __init__(self, market: str = '1x2'):
        super().__init__()
        self.market = market
        self.model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            eval_metric='mlogloss'
        )
        self.cv_score = 0.0  # Cross-validation score
    
    def train(self, features: pd.DataFrame, labels: pd.Series) -> None:
        """Train the model on historical match data."""
        if len(features) == 0 or len(labels) == 0:
            raise ValueError("Features and labels cannot be empty")
        
        if len(features) != len(labels):
            raise ValueError(f"Features ({len(features)}) and labels ({len(labels)}) must have the same length")
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(labels)
        
        # Train model
        self.model.fit(features, y_encoded)
        
        # Evaluate with cross-validation (adjust cv based on data size)
        n_samples = len(features)
        cv_folds = min(5, max(2, n_samples // 10))  # At least 10 samples per fold
        
        if n_samples >= 10:
            scores = cross_val_score(self.model, features, y_encoded, cv=cv_folds, scoring='accuracy')
            cv_mean = scores.mean()
            cv_std = scores.std()
            print(f"Cross-validation accuracy ({cv_folds}-fold): {cv_mean:.3f} (+/- {cv_std * 2:.3f})")
            self.cv_score = cv_mean
        else:
            print(f"Warning: Too few samples ({n_samples}) for cross-validation. Model trained on all data.")
            # Default score when CV not possible (50% accuracy baseline)
            self.cv_score = 0.5
        
        self.is_trained = True
    
    def predict_probabilities(self, features: pd.DataFrame) -> pd.DataFrame:
        """Predict match outcome probabilities."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        if len(features) == 0:
            return pd.DataFrame()
        
        # Get probability predictions
        proba = self.model.predict_proba(features)
        classes = self.label_encoder.classes_
        
        # Create DataFrame with probabilities
        result = pd.DataFrame(proba, columns=classes, index=features.index)
        
        # Normalize column names based on market
        if self.market == '1x2':
            result.columns = result.columns.map({
                'home_win': 'home_win',
                'draw': 'draw',
                'away_win': 'away_win'
            })
        elif self.market == 'over_under':
            result.columns = result.columns.map({
                'over': 'over',
                'under': 'under'
            })
        elif self.market == 'btts':
            result.columns = result.columns.map({
                'yes': 'btts_yes',
                'no': 'btts_no'
            })
        
        return result
    
    def predict(self, features: pd.DataFrame) -> pd.Series:
        """Predict most likely outcome."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        if len(features) == 0:
            return pd.Series()
        
        predictions = self.model.predict(features)
        return pd.Series(self.label_encoder.inverse_transform(predictions), index=features.index)
    
    def calculate_expected_value(self, probability: float, odds: float) -> float:
        """Calculate Expected Value: (Probability × Odds) - 1"""
        return (probability * odds) - 1

