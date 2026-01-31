"""
Trading predictor for stocks and crypto trading strategies.

Implements prediction models for momentum, swing, and volatility breakout strategies.
"""

from typing import Dict, Any, Optional, Tuple, Callable, List
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from xgboost import XGBClassifier, XGBRegressor
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from .predictor import BasePredictor
from .versioning import ModelVersionManager
from .hyperparameter_tuning import TradingHyperparameterTuner
from data.database import Database
import config


class TradingPredictor(BasePredictor):
    """
    Predictor for trading strategies (momentum, swing, volatility breakout).
    
    Supports both classification (direction) and regression (magnitude) predictions.
    
    Example usage:
        predictor = TradingPredictor(strategy='momentum')
        predictor.train(X_train, y_train)
        probs = predictor.predict_probabilities(X_test)
    """
    
    STRATEGIES = ['momentum', 'swing', 'volatility']
    
    def __init__(self, strategy: str = 'swing', enable_calibration: bool = False):
        """
        Initialize trading predictor.
        
        Args:
            strategy: Trading strategy ('momentum', 'swing', 'volatility')
            enable_calibration: Whether to enable probability calibration
        """
        super().__init__()
        
        if strategy not in self.STRATEGIES:
            raise ValueError(f"Strategy must be one of {self.STRATEGIES}")
        
        self.strategy = strategy
        self.enable_calibration = enable_calibration
        
        # Classification model for direction prediction
        self.model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            objective='binary:logistic',
            eval_metric='logloss'
        )
        
        # Regression model for magnitude prediction (optional)
        self.magnitude_model = None
        
        # Metrics storage
        self.cv_score = 0.0
        self.cv_std = 0.0
        self.training_metrics = {}
        self.feature_importance = {}
        self.hyperparameters = None  # Best hyperparameters from tuning
        self.tuning_metrics = {}  # Tuning metrics (best Sharpe, etc.)
        
        # Calibration (optional)
        self.calibrator = None
        self.calibration_metrics = {}
        self._manual_calibration = False
    
    def train(self, features: pd.DataFrame, labels: pd.Series,
              dates: Optional[pd.Series] = None,
              symbols: Optional[pd.Series] = None,
              log_callback: Optional[Callable[[str, str], None]] = None,
              train_magnitude: bool = False,
              magnitude_labels: Optional[pd.Series] = None) -> None:
        """
        Train the model on historical price data.
        
        Args:
            features: Training features from StockFeatureEngineer
            labels: Binary labels (1=up, 0=down for direction; 1=breakout for volatility)
            dates: Timestamps for temporal validation
            symbols: Symbol names for stratified sampling
            log_callback: Optional callback for logging
            train_magnitude: Whether to train magnitude regression model
            magnitude_labels: Actual returns for magnitude prediction
        """
        if len(features) == 0 or len(labels) == 0:
            raise ValueError("Features and labels cannot be empty")
        
        if len(features) != len(labels):
            raise ValueError(f"Features ({len(features)}) and labels ({len(labels)}) must have same length")
        
        if log_callback:
            log_callback("info", f"Training {self.strategy} model with {len(features)} samples...")
        
        # Convert labels to numpy array
        y = labels.values if isinstance(labels, pd.Series) else labels
        
        # Check for hyperparameter tuning configuration
        tuning_config = getattr(config, 'TRADING_HYPERPARAMETER_TUNING_CONFIG', {})
        
        # Hyperparameter tuning (if enabled)
        if tuning_config.get("enabled", False) and dates is not None and len(dates) == len(features):
            tuner = TradingHyperparameterTuner(
                strategy=self.strategy,
                search_space=tuning_config.get("search_space", "small"),
                min_samples=tuning_config.get("min_samples", 300),
                n_trials=tuning_config.get("n_trials"),
                log_callback=log_callback,
                n_jobs=tuning_config.get("n_jobs", 1),
                timeout=tuning_config.get("timeout"),
                early_stopping_patience=tuning_config.get("early_stopping_patience")
            )
            best_params = tuner.tune(features, labels, dates, symbols=symbols)
            
            if best_params:
                # Update model with best hyperparameters
                self.model = XGBClassifier(**best_params)
                self.hyperparameters = best_params
                self.tuning_metrics = {
                    'best_sharpe': tuner.get_best_score(),
                    'n_trials': tuner.n_trials,
                    'search_space': tuner.search_space
                }
                if log_callback:
                    log_callback("info", f"  Using tuned hyperparameters (Sharpe: {tuner.get_best_score():.4f})")
        
        # Split data for validation
        test_size = 0.2
        if dates is not None and len(dates) == len(features):
            # Temporal split - use most recent data for validation
            sorted_indices = np.argsort(dates.values)
            split_idx = int(len(sorted_indices) * (1 - test_size))
            train_idx = sorted_indices[:split_idx]
            val_idx = sorted_indices[split_idx:]
            
            X_train = features.iloc[train_idx].reset_index(drop=True)
            X_val = features.iloc[val_idx].reset_index(drop=True)
            y_train = y[train_idx]
            y_val = y[val_idx]
        else:
            # Random split
            X_train, X_val, y_train, y_val = train_test_split(
                features, y, test_size=test_size, random_state=42
            )
        
        # Train classification model
        self.model.fit(X_train, y_train)
        
        # Evaluate on validation set
        y_pred = self.model.predict(X_val)
        y_proba = self.model.predict_proba(X_val)[:, 1]
        
        accuracy = accuracy_score(y_val, y_pred)
        precision = precision_score(y_val, y_pred, zero_division=0)
        recall = recall_score(y_val, y_pred, zero_division=0)
        f1 = f1_score(y_val, y_pred, zero_division=0)
        
        self.training_metrics = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'samples_train': len(X_train),
            'samples_val': len(X_val),
            'class_balance': {
                'train_positive_rate': y_train.mean(),
                'val_positive_rate': y_val.mean()
            }
        }
        
        if log_callback:
            log_callback("info", f"  Accuracy: {accuracy:.3f}, Precision: {precision:.3f}, "
                                 f"Recall: {recall:.3f}, F1: {f1:.3f}")
        
        # Cross-validation on training set
        n_samples = len(X_train)
        cv_folds = min(5, max(2, n_samples // 20))
        
        if n_samples >= 20:
            scores = cross_val_score(self.model, X_train, y_train, cv=cv_folds, scoring='accuracy')
            self.cv_score = scores.mean()
            self.cv_std = scores.std()
            
            if log_callback:
                log_callback("info", f"  CV Accuracy ({cv_folds}-fold): {self.cv_score:.3f} (+/- {self.cv_std * 2:.3f})")
        else:
            self.cv_score = accuracy
            self.cv_std = 0.0
        
        # Store feature importance
        if hasattr(self.model, 'feature_importances_'):
            self.feature_importance = dict(zip(features.columns, self.model.feature_importances_))
        
        # Train magnitude model if requested
        if train_magnitude and magnitude_labels is not None:
            self._train_magnitude_model(features, magnitude_labels, dates, log_callback)
        
        self.is_trained = True
    
    def _train_magnitude_model(self, features: pd.DataFrame, 
                                magnitude_labels: pd.Series,
                                dates: Optional[pd.Series] = None,
                                log_callback: Optional[Callable[[str, str], None]] = None) -> None:
        """Train regression model for magnitude prediction."""
        if log_callback:
            log_callback("info", "  Training magnitude regression model...")
        
        self.magnitude_model = XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            objective='reg:squarederror'
        )
        
        # Filter out NaN values
        valid_mask = ~magnitude_labels.isnull()
        X = features[valid_mask]
        y = magnitude_labels[valid_mask].values
        
        if len(X) < 20:
            if log_callback:
                log_callback("warning", "  Insufficient data for magnitude model")
            self.magnitude_model = None
            return
        
        # Split and train
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        self.magnitude_model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.magnitude_model.predict(X_val)
        mse = np.mean((y_pred - y_val) ** 2)
        rmse = np.sqrt(mse)
        
        self.training_metrics['magnitude'] = {
            'rmse': rmse,
            'mse': mse
        }
        
        if log_callback:
            log_callback("info", f"  Magnitude model RMSE: {rmse:.4f}")
    
    def predict_probabilities(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Predict outcome probabilities.
        
        Returns:
            DataFrame with columns 'up' and 'down' (or 'breakout' and 'no_breakout' for volatility)
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        if len(features) == 0:
            return pd.DataFrame()
        
        # Get probabilities
        proba = self.model.predict_proba(features)
        
        # Create result DataFrame
        if self.strategy == 'volatility':
            result = pd.DataFrame({
                'no_breakout': proba[:, 0],
                'breakout': proba[:, 1]
            }, index=features.index)
        else:
            result = pd.DataFrame({
                'down': proba[:, 0],
                'up': proba[:, 1]
            }, index=features.index)
        
        return result
    
    def predict(self, features: pd.DataFrame) -> pd.Series:
        """Predict most likely outcome (0 or 1)."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        if len(features) == 0:
            return pd.Series(dtype=int)
        
        predictions = self.model.predict(features)
        return pd.Series(predictions, index=features.index)
    
    def predict_direction(self, features: pd.DataFrame, 
                          threshold: float = 0.5) -> pd.Series:
        """
        Predict direction with configurable threshold.
        
        Args:
            features: Input features
            threshold: Probability threshold for 'up' prediction
            
        Returns:
            Series with 'up' or 'down' (or 'breakout'/'no_breakout' for volatility)
        """
        probs = self.predict_probabilities(features)
        
        if self.strategy == 'volatility':
            up_col = 'breakout'
            up_label = 'breakout'
            down_label = 'no_breakout'
        else:
            up_col = 'up'
            up_label = 'up'
            down_label = 'down'
        
        predictions = probs[up_col].apply(
            lambda p: up_label if p >= threshold else down_label
        )
        return predictions
    
    def predict_magnitude(self, features: pd.DataFrame) -> pd.Series:
        """
        Predict price change magnitude (requires magnitude model to be trained).
        
        Returns:
            Series of predicted percentage changes
        """
        if self.magnitude_model is None:
            raise ValueError("Magnitude model not trained. Set train_magnitude=True during training.")
        
        if len(features) == 0:
            return pd.Series(dtype=float)
        
        predictions = self.magnitude_model.predict(features)
        return pd.Series(predictions, index=features.index)
    
    def get_confidence(self, features: pd.DataFrame) -> pd.Series:
        """
        Get prediction confidence (max probability).
        
        Returns:
            Series of confidence scores (0.5 to 1.0)
        """
        probs = self.predict_probabilities(features)
        return probs.max(axis=1)
    
    def save(self, filepath: str) -> None:
        """Save model to file."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        save_data = {
            'model': self.model,
            'magnitude_model': self.magnitude_model,
            'label_encoder': self.label_encoder,
            'is_trained': self.is_trained,
            'strategy': self.strategy,
            'cv_score': self.cv_score,
            'cv_std': self.cv_std,
            'training_metrics': self.training_metrics,
            'feature_importance': self.feature_importance,
            'calibrator': self.calibrator,
            'calibration_metrics': self.calibration_metrics,
            '_manual_calibration': self._manual_calibration
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(save_data, f)
    
    def load(self, filepath: str) -> None:
        """Load model from file."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.magnitude_model = data.get('magnitude_model')
            self.label_encoder = data['label_encoder']
            self.is_trained = data['is_trained']
            self.strategy = data.get('strategy', 'swing')
            self.cv_score = data.get('cv_score', 0.0)
            self.cv_std = data.get('cv_std', 0.0)
            self.training_metrics = data.get('training_metrics', {})
            self.feature_importance = data.get('feature_importance', {})
            self.calibrator = data.get('calibrator')
            self.calibration_metrics = data.get('calibration_metrics', {})
            self._manual_calibration = data.get('_manual_calibration', False)
    
    def get_top_features(self, n: int = 10) -> List[Tuple[str, float]]:
        """Get top N most important features."""
        if not self.feature_importance:
            return []
        
        sorted_features = sorted(
            self.feature_importance.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        return sorted_features[:n]
    
    def calculate_expected_value(self, probability: float, 
                                  expected_return: float,
                                  risk: float) -> float:
        """
        Calculate Expected Value for a trade signal.
        
        Args:
            probability: Predicted probability of success
            expected_return: Expected return if successful (e.g., 0.05 for 5%)
            risk: Risk/loss if unsuccessful (e.g., 0.02 for 2%)
            
        Returns:
            Expected value of the trade
        """
        ev = (probability * expected_return) - ((1 - probability) * risk)
        return ev
    
    def calculate_risk_reward(self, entry_price: float, 
                               stop_loss: float, 
                               take_profit: float) -> float:
        """
        Calculate risk/reward ratio.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop-loss price
            take_profit: Take-profit price
            
        Returns:
            Risk/reward ratio (reward / risk)
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        
        if risk == 0:
            return 0.0
        
        return reward / risk


class TradingModelManager:
    """
    Manager for trading models with versioning support.
    
    Handles loading/saving models with version tracking.
    """
    
    MODEL_DIR = Path(__file__).parent / 'saved'
    
    def __init__(self, db: Database):
        self.db = db
        self.version_manager = ModelVersionManager(db)
        self._models: Dict[str, TradingPredictor] = {}
    
    def get_model(self, strategy: str, load_best: bool = True) -> Optional[TradingPredictor]:
        """
        Get a trading model for a strategy.
        
        Args:
            strategy: Strategy name ('momentum', 'swing', 'volatility')
            load_best: If True, load the best performing model version
            
        Returns:
            TradingPredictor instance or None if not found
        """
        if strategy in self._models:
            return self._models[strategy]
        
        # Try to load from file
        model_path = self.MODEL_DIR / f'{strategy}_model.pkl'
        
        if model_path.exists():
            predictor = TradingPredictor(strategy=strategy)
            predictor.load(str(model_path))
            self._models[strategy] = predictor
            return predictor
        
        return None
    
    def save_model(self, predictor: TradingPredictor, 
                   metrics: Optional[Dict[str, Any]] = None) -> str:
        """
        Save a trading model with version tracking.
        
        Args:
            predictor: TradingPredictor instance
            metrics: Performance metrics to store
            
        Returns:
            Version ID
        """
        strategy = predictor.strategy
        model_path = self.MODEL_DIR / f'{strategy}_model.pkl'
        
        # Save model file
        predictor.save(str(model_path))
        
        # Record version
        version_metrics = metrics or predictor.training_metrics
        training_samples = version_metrics.get('samples_train', 0) if isinstance(version_metrics, dict) else 0
        version_id = self.version_manager.save_version(
            domain='trading',
            market=strategy,
            model_path=str(model_path),
            training_samples=training_samples,
            cv_score=predictor.cv_score or 0.0,
            performance_metrics=version_metrics,
            activate=True
        )
        
        # Update cache
        self._models[strategy] = predictor
        
        return version_id
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all trading models."""
        status = {}
        
        for strategy in TradingPredictor.STRATEGIES:
            model_path = self.MODEL_DIR / f'{strategy}_model.pkl'
            
            if model_path.exists():
                # Get active version from database
                active_version = self.version_manager.get_active_version(domain='trading', market=strategy)
                
                status[strategy] = {
                    'available': True,
                    'path': str(model_path),
                    'version': active_version.get('version_id') if active_version else None,
                    'cv_score': active_version.get('cv_score') if active_version else None,
                    'created_at': active_version.get('created_at') if active_version else None
                }
            else:
                status[strategy] = {
                    'available': False,
                    'path': str(model_path),
                    'version': None,
                    'cv_score': None,
                    'created_at': None
                }
        
        return status
    
    def invalidate_cache(self) -> None:
        """Clear model cache."""
        self._models = {}
