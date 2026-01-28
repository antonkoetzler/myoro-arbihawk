"""
Base predictor class for betting predictions.
Designed to be extended with specific model implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, Callable
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.calibration import CalibratedClassifierCV

from .calibration import evaluate_calibration, calculate_brier_score, calculate_ece
from .hyperparameter_tuning import HyperparameterTuner
from data.database import Database
import config


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
        save_data = {
            'model': self.model,
            'label_encoder': self.label_encoder,
            'is_trained': self.is_trained,
            'cv_score': getattr(self, 'cv_score', 0.0)
        }
        # Include calibrator if it exists (for backward compatibility)
        if hasattr(self, 'calibrator') and self.calibrator is not None:
            save_data['calibrator'] = self.calibrator
        if hasattr(self, 'calibration_metrics'):
            save_data['calibration_metrics'] = getattr(self, 'calibration_metrics', {})
        if hasattr(self, '_manual_calibration'):
            save_data['_manual_calibration'] = getattr(self, '_manual_calibration', False)
        if hasattr(self, 'hyperparameters') and self.hyperparameters is not None:
            save_data['hyperparameters'] = self.hyperparameters
        if hasattr(self, 'tuning_metrics'):
            save_data['tuning_metrics'] = getattr(self, 'tuning_metrics', {})
        if hasattr(self, 'betting_metrics'):
            save_data['betting_metrics'] = getattr(self, 'betting_metrics', {})
        
        with open(filepath, 'wb') as f:
            pickle.dump(save_data, f)
    
    def load(self, filepath: str) -> None:
        """Load model from file."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.label_encoder = data['label_encoder']
            self.is_trained = data['is_trained']
            self.cv_score = data.get('cv_score', 0.0)
            # Load calibrator if it exists (backward compatible)
            self.calibrator = data.get('calibrator', None)
            self.calibration_metrics = data.get('calibration_metrics', {})
            self._manual_calibration = data.get('_manual_calibration', False)
            self.hyperparameters = data.get('hyperparameters', None)
            self.tuning_metrics = data.get('tuning_metrics', {})
            self.betting_metrics = data.get('betting_metrics', {})


class BettingPredictor(BasePredictor):
    """Main predictor for betting recommendations using XGBoost."""
    
    def __init__(self, market: str = '1x2', enable_calibration: bool = True,
                 calibration_method: str = 'isotonic'):
        """
        Initialize betting predictor.
        
        Args:
            market: Market type ('1x2', 'over_under', 'btts')
            enable_calibration: Whether to enable probability calibration
            calibration_method: Calibration method ('isotonic' or 'platt')
        """
        super().__init__()
        self.market = market
        self.enable_calibration = enable_calibration
        self.calibration_method = calibration_method
        self.model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            objective='multi:softprob',  # Required for multiclass classification
            eval_metric='mlogloss'
        )
        self.cv_score = 0.0  # Cross-validation score
        self.calibrator = None  # Will be set during training if calibration enabled
        self.calibration_metrics = {}  # Brier score, ECE, etc.
        self._manual_calibration = False  # Flag for manual calibration mode
        self.hyperparameters = None  # Best hyperparameters from tuning
        self.tuning_metrics = {}  # Tuning metrics (best score, etc.)
        self.betting_metrics = {}  # Betting performance metrics (ROI, profit, etc.)
    
    def train(self, features: pd.DataFrame, labels: pd.Series,
              dates: Optional[pd.Series] = None,
              fixture_ids: Optional[pd.Series] = None,
              calibration_split: float = 0.2,
              validation_split: float = 0.25,
              log_callback: Optional[Callable[[str, str], None]] = None,
              db: Optional[Database] = None) -> None:
        """
        Train the model on historical match data.
        
        Args:
            features: Training features
            labels: Training labels
            dates: Match dates for temporal splitting (required for hyperparameter tuning and betting evaluation)
            fixture_ids: Optional fixture IDs (for accurate betting evaluation during hyperparameter tuning)
            calibration_split: Fraction of data to use for calibration (default: 0.2)
                              Set to 0 to disable calibration
            validation_split: Fraction of data to use for betting evaluation (default: 0.25, most recent data)
            log_callback: Optional callback for logging
            db: Database instance (required for betting evaluation)
        """
        if len(features) == 0 or len(labels) == 0:
            raise ValueError("Features and labels cannot be empty")
        
        if len(features) != len(labels):
            raise ValueError(f"Features ({len(features)}) and labels ({len(labels)}) must have the same length")
        
        # Hyperparameter tuning (if enabled and dates provided)
        tuning_config = config.HYPERPARAMETER_TUNING_CONFIG
        best_params = None
        
        # IMPORTANT: Default to False - hyperparameter tuning is disabled by default
        # Only enable when explicitly set to True in config
        if tuning_config.get("enabled", False) and dates is not None and len(dates) == len(features):
            tuner = HyperparameterTuner(
                market=self.market,
                search_space=tuning_config.get("search_space", "medium"),
                min_samples=tuning_config.get("min_samples", 300),
                n_trials=tuning_config.get("n_trials"),  # Allow override
                log_callback=log_callback,
                db=db,
                n_jobs=tuning_config.get("n_jobs", 1),  # Default: sequential
                timeout=tuning_config.get("timeout"),  # Optional timeout in seconds
                early_stopping_patience=tuning_config.get("early_stopping_patience")  # Optional early stopping
            )
            best_params = tuner.tune(features, labels, dates, fixture_ids=fixture_ids)
            
            if best_params:
                self.hyperparameters = best_params.copy()
                self.tuning_metrics = {
                    "best_roi": tuner.get_best_score(),
                    "search_space": tuning_config.get("search_space", "medium")
                }
                # Update model with best hyperparameters (ensure required params are included)
                model_params = best_params.copy()
                # Get number of classes (encode labels first to know this)
                y_encoded_temp = self.label_encoder.fit_transform(labels)
                n_classes = len(self.label_encoder.classes_)
                # Ensure num_class is at least 1
                if n_classes < 1:
                    raise ValueError(f"Invalid number of classes: {n_classes}. Must be at least 1.")
                model_params.update({
                    'random_state': 42,
                    'objective': 'multi:softprob',  # Required for multiclass classification
                    'eval_metric': 'mlogloss',
                    'num_class': n_classes  # Required for multiclass
                })
                self.model = XGBClassifier(**model_params)
            else:
                # Tuning was skipped or failed, use defaults
                self.hyperparameters = None
                self.tuning_metrics = {}
                # Ensure default model has num_class set if we can determine it
                # (will be set properly after encoding labels)
        
        # Encode labels (reuse encoder if already fit, otherwise fit it)
        if not hasattr(self.label_encoder, 'classes_') or len(self.label_encoder.classes_) == 0:
            y_encoded = self.label_encoder.fit_transform(labels)
        else:
            # Encoder already fit, just transform
            y_encoded = self.label_encoder.transform(labels)
        
        # Ensure model has num_class set (for default model if tuning was skipped)
        if not hasattr(self.model, 'get_params') or self.model.get_params().get('num_class') is None:
            n_classes = len(self.label_encoder.classes_)
            if n_classes >= 1:
                # Update model params to include num_class
                model_params = self.model.get_params()
                model_params['num_class'] = n_classes
                model_params['objective'] = 'multi:softprob'
                model_params['eval_metric'] = 'mlogloss'
                self.model = XGBClassifier(**model_params)
        
        # Create temporal validation split (most recent data for betting evaluation)
        # This must happen before calibration split to ensure proper temporal ordering
        X_train_full = features
        y_train_full = y_encoded
        dates_train_full = dates if dates is not None else pd.Series([None] * len(features))
        X_val = pd.DataFrame()
        y_val = pd.Series(dtype=y_encoded.dtype)
        dates_val = pd.Series(dtype=dates_train_full.dtype)
        
        use_betting_eval = (db is not None and dates is not None and 
                           len(dates) == len(features) and 
                           validation_split > 0 and len(features) >= 100)
        
        if use_betting_eval:
            # Sort by date and take most recent validation_split fraction
            date_indices = dates_train_full.argsort()
            n_val = max(1, int(len(features) * validation_split))
            val_indices = date_indices[-n_val:]
            train_indices = date_indices[:-n_val]
            
            X_train_full = features.iloc[train_indices].reset_index(drop=True)
            y_train_full = y_encoded[train_indices]
            dates_train_full = dates_train_full.iloc[train_indices].reset_index(drop=True)
            
            X_val = features.iloc[val_indices].reset_index(drop=True)
            y_val = labels.iloc[val_indices].reset_index(drop=True)
            dates_val = dates.iloc[val_indices].reset_index(drop=True)
        
        # Split data for calibration if enabled (from remaining training data)
        use_calibration = self.enable_calibration and calibration_split > 0 and len(X_train_full) >= 50
        if use_calibration:
            X_train, X_cal, y_train_encoded, y_cal_encoded = train_test_split(
                X_train_full, y_train_full,
                test_size=calibration_split,
                random_state=42,
                stratify=y_train_full if len(np.unique(y_train_full)) > 1 else None
            )
        else:
            X_train = X_train_full
            y_train_encoded = y_train_full
            X_cal = None
            y_cal_encoded = None
        
        # Train base model
        self.model.fit(X_train, y_train_encoded)
        
        # Apply calibration if enabled
        if use_calibration and X_cal is not None:
            # Get uncalibrated predictions for calibration set
            y_cal_pred_uncalibrated = self.model.predict_proba(X_cal)
            
            # Try using CalibratedClassifierCV with prefit
            # If that fails (newer sklearn versions), use manual calibration
            try:
                # Try the prefit approach (works in sklearn < 1.6)
                self.calibrator = CalibratedClassifierCV(
                    self.model,
                    method=self.calibration_method,
                    cv='prefit'
                )
                self.calibrator.fit(X_cal, y_cal_encoded)
            except (ValueError, TypeError):
                # Fallback: Use manual calibration per class
                # This is what CalibratedClassifierCV does internally
                from sklearn.isotonic import IsotonicRegression
                from sklearn.linear_model import LogisticRegression
                
                n_classes = len(self.label_encoder.classes_)
                calibrators = []
                
                for class_idx in range(n_classes):
                    # Get probabilities for this class
                    y_class_proba = y_cal_pred_uncalibrated[:, class_idx]
                    # Binary labels: 1 if this class, 0 otherwise
                    y_class_binary = (y_cal_encoded == class_idx).astype(float)
                    
                    # Create and fit calibrator for this class
                    if self.calibration_method == 'isotonic':
                        calibrator = IsotonicRegression(out_of_bounds='clip')
                    else:  # platt
                        calibrator = LogisticRegression()
                    
                    # Fit on calibration data
                    calibrator.fit(y_class_proba.reshape(-1, 1), y_class_binary)
                    calibrators.append(calibrator)
                
                # Store calibrators as a list (we'll use them in predict_probabilities)
                self.calibrator = calibrators
                self._manual_calibration = True
            else:
                self._manual_calibration = False
            
            # Get calibrated predictions
            if self._manual_calibration:
                y_cal_pred_calibrated = self._apply_manual_calibration(y_cal_pred_uncalibrated)
            else:
                y_cal_pred_calibrated = self.calibrator.predict_proba(X_cal)
            
            # Convert to one-hot for metrics
            n_classes = len(self.label_encoder.classes_)
            y_cal_onehot = np.zeros((len(y_cal_encoded), n_classes))
            y_cal_onehot[np.arange(len(y_cal_encoded)), y_cal_encoded] = 1
            
            # Calculate metrics for both uncalibrated and calibrated
            metrics_uncalibrated = evaluate_calibration(y_cal_onehot, y_cal_pred_uncalibrated)
            metrics_calibrated = evaluate_calibration(y_cal_onehot, y_cal_pred_calibrated)
            
            self.calibration_metrics = {
                'uncalibrated': metrics_uncalibrated,
                'calibrated': metrics_calibrated,
                'improvement': {
                    'brier_score': metrics_uncalibrated['brier_score'] - metrics_calibrated['brier_score'],
                    'ece': metrics_uncalibrated['ece'] - metrics_calibrated['ece']
                }
            }
            
            print(f"Calibration metrics (calibrated): Brier={metrics_calibrated['brier_score']:.4f}, ECE={metrics_calibrated['ece']:.4f}")
            print(f"Calibration improvement: Brier={self.calibration_metrics['improvement']['brier_score']:.4f}, ECE={self.calibration_metrics['improvement']['ece']:.4f}")
        else:
            self.calibrator = None
            self.calibration_metrics = {}
            self._manual_calibration = False
        
        # Evaluate with cross-validation (adjust cv based on data size)
        n_samples = len(X_train)
        cv_folds = min(5, max(2, n_samples // 10))  # At least 10 samples per fold
        
        if n_samples >= 10:
            # Use a custom scorer that handles predictions correctly
            from sklearn.metrics import accuracy_score, make_scorer
            
            def accuracy_scorer(y_true, y_pred):
                """Custom accuracy scorer that ensures predictions are class labels."""
                # Ensure y_pred are class labels (not probabilities)
                if y_pred.ndim > 1:
                    # If probabilities, convert to class labels
                    y_pred = np.argmax(y_pred, axis=1)
                # Ensure both are 1D arrays
                y_true = np.asarray(y_true).ravel()
                y_pred = np.asarray(y_pred).ravel()
                return accuracy_score(y_true, y_pred)
            
            custom_scorer = make_scorer(accuracy_scorer)
            
            try:
                scores = cross_val_score(self.model, X_train, y_train_encoded, cv=cv_folds, scoring=custom_scorer)
                # Filter out NaN scores (from failed folds)
                scores = scores[~np.isnan(scores)]
                if len(scores) > 0:
                    cv_mean = scores.mean()
                    cv_std = scores.std()
                    print(f"Cross-validation accuracy ({cv_folds}-fold): {cv_mean:.3f} (+/- {cv_std * 2:.3f})")
                    self.cv_score = cv_mean
                    self.cv_std = cv_std
                    self.cv_folds = len(scores)
                else:
                    # All folds failed
                    print(f"Warning: All cross-validation folds failed. Using default score.")
                    self.cv_score = 0.5
                    self.cv_std = 0.0
                    self.cv_folds = 0
            except Exception as e:
                # If CV fails, log warning and use default
                if log_callback:
                    log_callback("warning", f"Cross-validation failed: {e}. Using default score.")
                else:
                    print(f"Warning: Cross-validation failed: {e}. Using default score.")
                self.cv_score = 0.5
                self.cv_std = 0.0
                self.cv_folds = 0
        else:
            print(f"Warning: Too few samples ({n_samples}) for cross-validation. Model trained on all data.")
            # Default score when CV not possible (50% accuracy baseline)
            self.cv_score = 0.5
            self.cv_std = 0.0
            self.cv_folds = 0
        
        # Evaluate on betting metrics if validation set available
        if use_betting_eval and len(X_val) > 0 and len(y_val) > 0:
            try:
                from .betting_evaluator import BettingEvaluator
                evaluator = BettingEvaluator(
                    db=db,
                    ev_threshold=config.EV_THRESHOLD,
                    market=self.market
                )
                betting_metrics = evaluator.evaluate(
                    predictor=self,
                    X_val=X_val,
                    y_val=y_val,
                    dates=dates_val
                )
                self.betting_metrics = betting_metrics
                
                if log_callback:
                    log_callback("info", 
                        f"Betting evaluation - ROI: {betting_metrics['roi']:.2%}, "
                        f"Profit: ${betting_metrics['profit']:.2f}, "
                        f"Win Rate: {betting_metrics['win_rate']:.2%}, "
                        f"Bets: {betting_metrics['total_bets']}")
                else:
                    print(f"Betting evaluation - ROI: {betting_metrics['roi']:.2%}, "
                          f"Profit: ${betting_metrics['profit']:.2f}, "
                          f"Win Rate: {betting_metrics['win_rate']:.2%}, "
                          f"Bets: {betting_metrics['total_bets']}")
            except Exception as e:
                # If betting evaluation fails, log but don't crash
                if log_callback:
                    log_callback("warning", f"Betting evaluation failed: {e}")
                else:
                    print(f"Warning: Betting evaluation failed: {e}")
                self.betting_metrics = {}
        else:
            self.betting_metrics = {}
        
        self.is_trained = True
    
    def predict_probabilities(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Predict match outcome probabilities.
        
        Uses calibrated probabilities if calibrator is available,
        otherwise falls back to raw model probabilities.
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        if len(features) == 0:
            return pd.DataFrame()
        
        # Get probability predictions (calibrated if available)
        if self.calibrator is not None:
            if self._manual_calibration:
                # Manual calibration: apply calibrators per class
                uncalibrated_proba = self.model.predict_proba(features)
                proba = self._apply_manual_calibration(uncalibrated_proba)
            else:
                # sklearn CalibratedClassifierCV
                proba = self.calibrator.predict_proba(features)
        else:
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
    
    def _apply_manual_calibration(self, uncalibrated_proba: np.ndarray) -> np.ndarray:
        """
        Apply manual calibration per class.
        
        Args:
            uncalibrated_proba: Uncalibrated probabilities [n_samples, n_classes]
        
        Returns:
            Calibrated probabilities [n_samples, n_classes]
        """
        n_samples, n_classes = uncalibrated_proba.shape
        calibrated_proba = np.zeros_like(uncalibrated_proba)
        
        for class_idx in range(n_classes):
            class_proba = uncalibrated_proba[:, class_idx]
            calibrator = self.calibrator[class_idx]
            
            # Apply calibration
            if self.calibration_method == 'isotonic':
                calibrated_class_proba = calibrator.predict(class_proba)
            else:  # platt
                calibrated_class_proba = calibrator.predict_proba(class_proba.reshape(-1, 1))[:, 1]
            
            calibrated_proba[:, class_idx] = calibrated_class_proba
        
        # Renormalize to ensure probabilities sum to 1
        calibrated_proba = calibrated_proba / calibrated_proba.sum(axis=1, keepdims=True)
        
        return calibrated_proba
    
    def calculate_expected_value(self, probability: float, odds: float) -> float:
        """Calculate Expected Value: (Probability × Odds) - 1"""
        return (probability * odds) - 1

