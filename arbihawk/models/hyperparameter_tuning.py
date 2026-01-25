"""
Hyperparameter tuning for betting prediction models using Optuna.
Optimizes for ROI/profitability with temporal cross-validation.
"""

import optuna
import optuna.logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Callable, Tuple
from datetime import datetime
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import BaseCrossValidator
from xgboost import XGBClassifier

from .calibration import calculate_brier_score
from .betting_evaluator import BettingEvaluator
from data.database import Database
import config

# Suppress Optuna's default logging (we'll use our own)
optuna.logging.set_verbosity(optuna.logging.WARNING)


class TemporalSplitter(BaseCrossValidator):
    """
    Custom cross-validator that splits data temporally (by match date).
    Ensures training data is always from before test data.
    """
    
    def __init__(self, n_splits: int = 5, test_size: float = 0.2):
        """
        Initialize temporal splitter.
        
        Args:
            n_splits: Number of splits (folds)
            test_size: Fraction of data to use for testing in each split
        """
        self.n_splits = n_splits
        self.test_size = test_size
    
    def split(self, X, y=None, groups=None):
        """
        Generate temporal splits.
        
        Args:
            X: Feature matrix
            y: Labels
            groups: Match dates (Series or array with same length as X)
        """
        if groups is None:
            raise ValueError("TemporalSplitter requires dates in 'groups' parameter")
        
        n_samples = len(X)
        dates = groups.values if hasattr(groups, 'values') else np.array(groups)
        
        # Convert dates to timestamps if they're strings
        if dates.dtype == object:
            try:
                dates = pd.to_datetime(dates).values
            except:
                pass
        
        # Sort by date and get original indices
        date_indices = np.argsort(dates)
        
        # Calculate split points
        test_samples_per_split = max(1, int(n_samples * self.test_size))
        
        for i in range(self.n_splits):
            # Calculate test range (from end, moving backwards)
            test_start_idx = n_samples - test_samples_per_split * (i + 1)
            test_end_idx = n_samples - test_samples_per_split * i
            
            if test_start_idx < 0:
                test_start_idx = 0
            
            if test_end_idx <= test_start_idx:
                continue
            
            # Get indices for this split (using original indices)
            test_indices = date_indices[test_start_idx:test_end_idx]
            train_indices = date_indices[:test_start_idx]
            
            if len(train_indices) == 0 or len(test_indices) == 0:
                continue
            
            yield train_indices, test_indices
    
    def get_n_splits(self, X=None, y=None, groups=None):
        """Return number of splits."""
        return self.n_splits


class HyperparameterTuner:
    """
    Hyperparameter tuning using Optuna with temporal cross-validation.
    Optimizes for ROI/profitability (betting performance).
    """
    
    def __init__(self, market: str, search_space: str = 'medium',
                 min_samples: int = 300, n_trials: Optional[int] = None,
                 log_callback: Optional[Callable[[str, str], None]] = None,
                 db: Optional[Database] = None):
        """
        Initialize hyperparameter tuner.
        
        Args:
            market: Market type ('1x2', 'over_under', 'btts')
            search_space: Size of search space ('small', 'medium', 'large')
            min_samples: Minimum samples required for tuning
            n_trials: Number of Optuna trials (None = auto based on search_space)
            log_callback: Optional callback for logging
            db: Database instance (required for betting evaluation)
        """
        self.market = market
        self.search_space = search_space
        self.min_samples = min_samples
        self.log_callback = log_callback
        self.db = db or Database()
        self.best_params = None
        self.best_score = None
        self.betting_evaluator = BettingEvaluator(
            db=self.db,
            ev_threshold=config.EV_THRESHOLD,
            market=market
        )
        
        # Set n_trials based on search_space if not specified
        if n_trials is None:
            if search_space == 'small':
                n_trials = 20
            elif search_space == 'medium':
                n_trials = 50
            else:  # large
                n_trials = 100
        self.n_trials = n_trials
    
    def _log(self, level: str, message: str):
        """Log a message."""
        if self.log_callback:
            self.log_callback(level, message)
        else:
            print(f"[{level.upper()}] {message}")
    
    def _get_search_space(self, trial: optuna.Trial) -> Dict[str, Any]:
        """
        Define hyperparameter search space based on size.
        
        Args:
            trial: Optuna trial object
            
        Returns:
            Dictionary of hyperparameters
        """
        if self.search_space == 'small':
            return {
                'n_estimators': trial.suggest_int('n_estimators', 50, 200, step=50),
                'max_depth': trial.suggest_int('max_depth', 4, 8, step=2),
                'learning_rate': trial.suggest_float('learning_rate', 0.05, 0.15, step=0.05),
                'subsample': trial.suggest_float('subsample', 0.8, 1.0, step=0.1),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.8, 1.0, step=0.1)
            }
        elif self.search_space == 'medium':
            return {
                'n_estimators': trial.suggest_int('n_estimators', 50, 200, step=25),
                'max_depth': trial.suggest_int('max_depth', 3, 8),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
                'subsample': trial.suggest_float('subsample', 0.7, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.7, 1.0),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 7),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.0),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 2.0)
            }
        else:  # large
            return {
                'n_estimators': trial.suggest_int('n_estimators', 50, 300, step=25),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.3, log=True),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 2.0),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 3.0),
                'gamma': trial.suggest_float('gamma', 0.0, 1.0)
            }
    
    def _objective(self, trial: optuna.Trial, X: pd.DataFrame, y: pd.Series,
                   dates: pd.Series, fixture_ids: pd.Series, label_encoder: LabelEncoder) -> float:
        """
        Optuna objective function: maximize ROI (returns negative ROI since Optuna minimizes).
        
        Args:
            trial: Optuna trial
            X: Features
            y: Labels
            dates: Match dates for temporal splitting
            label_encoder: Label encoder
            
        Returns:
            Negative ROI (to minimize, which maximizes ROI)
        """
        # Get hyperparameters for this trial
        params = self._get_search_space(trial)
        params.update({
            'random_state': 42,
            'objective': 'multi:softprob',  # Required for multiclass classification
            'eval_metric': 'mlogloss',
            'verbosity': 0  # Suppress XGBoost output
        })
        
        # Temporal cross-validation
        splitter = TemporalSplitter(n_splits=5, test_size=0.2)
        rois = []
        total_bets = 0
        split_details = []
        
        for split_idx, (train_idx, test_idx) in enumerate(splitter.split(X, y, groups=dates), 1):
            # Split data
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            dates_test = dates.iloc[test_idx]
            if fixture_ids is not None and len(fixture_ids) > 0:
                fixture_ids_test = fixture_ids.iloc[test_idx]
                # Filter out None/NaN values - if all are None/NaN, set to None
                if fixture_ids_test.isna().all():
                    fixture_ids_test = None
            else:
                fixture_ids_test = None
            
            # Encode labels
            y_train_encoded = label_encoder.transform(y_train)
            
            # Get number of classes for multiclass objective
            n_classes = len(label_encoder.classes_)
            params_with_classes = params.copy()
            params_with_classes['num_class'] = n_classes
            
            # Create and train predictor with trial hyperparameters
            from .predictor import BettingPredictor
            predictor = BettingPredictor(market=self.market, enable_calibration=False)
            predictor.model = XGBClassifier(**params_with_classes)
            predictor.label_encoder = label_encoder
            predictor.model.fit(X_train, y_train_encoded)
            predictor.is_trained = True
            
            # Evaluate on betting metrics
            try:
                metrics = self.betting_evaluator.evaluate(
                    predictor=predictor,
                    X_val=X_test,
                    y_val=y_test,
                    dates=dates_test,
                    fixture_ids=fixture_ids_test
                )
                roi = metrics.get('roi', 0.0)
                bets_count = metrics.get('total_bets', 0)
                profit = metrics.get('profit', 0.0)
                win_rate = metrics.get('win_rate', 0.0)
                rois.append(roi)
                total_bets += bets_count
                split_details.append({
                    'split': split_idx,
                    'roi': roi,
                    'bets': bets_count,
                    'profit': profit,
                    'win_rate': win_rate,
                    'test_samples': len(X_test)
                })
            except Exception as e:
                # If evaluation fails, log and use a very negative ROI to discourage this trial
                if self.log_callback:
                    self.log_callback("warning", 
                        f"Trial {trial.number} split {split_idx} evaluation failed: {e}")
                rois.append(-1.0)
                split_details.append({
                    'split': split_idx,
                    'roi': -1.0,
                    'bets': 0,
                    'error': str(e)
                })
                continue
        
        if len(rois) == 0:
            # No valid evaluations, return very negative value
            if self.log_callback:
                self.log_callback("warning", 
                    f"Trial {trial.number}: No valid evaluations, skipping")
            return -1.0
        
        # Return negative mean ROI (since Optuna minimizes, this maximizes ROI)
        mean_roi = np.mean(rois)
        
        # Store trial details for logging
        trial.set_user_attr('mean_roi', mean_roi)
        trial.set_user_attr('total_bets', total_bets)
        trial.set_user_attr('split_details', split_details)
        
        # Log warning if no bets were placed (ROI will be 0.0)
        if total_bets == 0 and self.log_callback:
            self.log_callback("warning", 
                f"Trial {trial.number}: No value bets found (ROI=0.0%). "
                f"This may indicate EV threshold too high or insufficient odds data.")
        
        # Report intermediate value for pruning
        trial.report(-mean_roi, 0)  # Report negative for pruning logic
        
        # Check for pruning
        if trial.should_prune():
            raise optuna.TrialPruned()
        
        return -mean_roi
    
    def tune(self, X: pd.DataFrame, y: pd.Series, dates: pd.Series, fixture_ids: Optional[pd.Series] = None) -> Optional[Dict[str, Any]]:
        """
        Run hyperparameter tuning.
        
        Args:
            X: Features
            y: Labels
            dates: Match dates
            fixture_ids: Optional fixture IDs (for accurate betting evaluation)
            
        Returns:
            Best hyperparameters dict, or None if tuning failed/skipped
        """
        # Check minimum samples
        if len(X) < self.min_samples:
            self._log("warning", 
                     f"Insufficient data for hyperparameter tuning ({len(X)} < {self.min_samples}). "
                     f"Using default hyperparameters.")
            return None
        
        # Encode labels
        label_encoder = LabelEncoder()
        y_encoded = label_encoder.fit_transform(y)
        
        # Create fixture_ids if not provided (fallback for backward compatibility)
        if fixture_ids is None:
            fixture_ids = pd.Series([None] * len(X))
            self._log("warning", "No fixture_ids provided. Betting evaluation may be less accurate.")
        
        # Warn about time
        self._log("info", 
                 f"Starting hyperparameter tuning ({self.search_space} search space, {self.n_trials} trials)...")
        self._log("warning", 
                 f"This may take 30-60 minutes. Progress will be logged periodically.")
        
        try:
            # Create Optuna study (minimize negative ROI = maximize ROI)
            study = optuna.create_study(
                direction='minimize',  # Minimize negative ROI (maximizes ROI)
                study_name=f'hyperparameter_tuning_{self.market}',
                pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=10)
            )
            
            # Custom callback to log trial progress
            def trial_callback(study: optuna.Study, trial: optuna.Trial) -> None:
                """Log trial completion with formatted output."""
                trial_num = trial.number
                mean_roi = trial.user_attrs.get('mean_roi', 0.0)
                total_bets = trial.user_attrs.get('total_bets', 0)
                split_details = trial.user_attrs.get('split_details', [])
                
                # Format hyperparameters nicely (only show key ones)
                key_params = {
                    'n_estimators': trial.params.get('n_estimators'),
                    'max_depth': trial.params.get('max_depth'),
                    'learning_rate': round(trial.params.get('learning_rate', 0), 4)
                }
                if 'subsample' in trial.params:
                    key_params['subsample'] = round(trial.params['subsample'], 3)
                if 'colsample_bytree' in trial.params:
                    key_params['colsample_bytree'] = round(trial.params['colsample_bytree'], 3)
                
                # Format key params as readable string
                params_str = ', '.join([f"{k}={v}" for k, v in key_params.items()])
                
                # Get best trial so far
                best_trial = study.best_trial
                best_roi = -best_trial.value if best_trial else 0.0
                best_trial_num = best_trial.number if best_trial else 0
                
                # Calculate progress percentage
                progress_pct = ((trial_num + 1) / self.n_trials) * 100
                
                # Log trial completion with progress
                roi_pct = mean_roi * 100
                # Format ROI with sign
                roi_str = f"{roi_pct:+.2f}%" if roi_pct != 0.0 else "0.00%"
                self._log("info", 
                    f"Trial {trial_num + 1}/{self.n_trials} ({progress_pct:.0f}%) | "
                    f"ROI: {roi_str} | "
                    f"Bets: {total_bets} | "
                    f"Params: {params_str}")
                
                # Log if this is a new best
                if trial_num == best_trial_num:
                    if trial_num == 0:
                        # First trial - log that it's the baseline
                        self._log("info", 
                            f"  >> Baseline trial (ROI: {best_roi*100:+.2f}%)")
                    elif abs(mean_roi - best_roi) > 1e-6:
                        # Actually improved (not just same value)
                        self._log("info", 
                            f"  >> New best! ROI improved to {best_roi*100:+.2f}%")
                    # If same value, don't log "new best" (all trials have same ROI)
            
            # Run optimization with callback
            study.optimize(
                lambda trial: self._objective(trial, X, y, dates, fixture_ids, label_encoder),
                n_trials=self.n_trials,
                show_progress_bar=False,  # We'll log manually
                callbacks=[trial_callback]
            )
            
            # Get best parameters
            self.best_params = study.best_params.copy()
            # best_value is negative ROI, so convert back to positive
            self.best_score = -study.best_value  # Convert back to positive ROI
            
            # Log results
            self._log("success", 
                     f"Hyperparameter tuning completed. Best ROI: {self.best_score:.2%}")
            
            # Format best hyperparameters nicely
            best_params_formatted = []
            for key in ['n_estimators', 'max_depth', 'learning_rate', 'subsample', 
                       'colsample_bytree', 'min_child_weight', 'reg_alpha', 'reg_lambda', 'gamma']:
                if key in self.best_params:
                    value = self.best_params[key]
                    if isinstance(value, float):
                        value = round(value, 4)
                    best_params_formatted.append(f"{key}={value}")
            
            self._log("info", 
                     f"Best hyperparameters: {', '.join(best_params_formatted)}")
            
            return self.best_params
            
        except Exception as e:
            self._log("error", 
                     f"Hyperparameter tuning failed: {e}. Using default hyperparameters.")
            return None
    
    def get_best_params(self) -> Optional[Dict[str, Any]]:
        """Get best hyperparameters found during tuning."""
        return self.best_params
    
    def get_best_score(self) -> Optional[float]:
        """Get best ROI achieved during tuning."""
        return self.best_score
