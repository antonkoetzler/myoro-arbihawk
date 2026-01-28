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
                 db: Optional[Database] = None,
                 n_jobs: int = 1,
                 timeout: Optional[float] = None,
                 early_stopping_patience: Optional[int] = None):
        """
        Initialize hyperparameter tuner.
        
        Args:
            market: Market type ('1x2', 'over_under', 'btts')
            search_space: Size of search space ('small', 'medium', 'large')
            min_samples: Minimum samples required for tuning
            n_trials: Number of Optuna trials (None = auto based on search_space)
            log_callback: Optional callback for logging
            db: Database instance (required for betting evaluation)
            n_jobs: Number of parallel jobs (1 = sequential, -1 = all CPUs)
            timeout: Maximum time in seconds (None = no timeout)
            early_stopping_patience: Stop if no improvement in last N trials (None = disabled)
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
        self.n_jobs = n_jobs
        self.timeout = timeout
        self.early_stopping_patience = early_stopping_patience
        
        # Set n_trials based on search_space if not specified (reduced for performance)
        if n_trials is None:
            if search_space == 'small':
                n_trials = 15  # Reduced from 20
            elif search_space == 'medium':
                n_trials = 30  # Reduced from 50
            else:  # large
                n_trials = 60  # Reduced from 100
        self.n_trials = n_trials
        
        # Track consecutive zero-bet trials for warning
        self._consecutive_zero_bet_trials = 0
    
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
        
        # Get number of classes from label encoder (fit on all data)
        n_classes = len(label_encoder.classes_)
        if n_classes < 1:
            # Invalid number of classes, return very negative value
            return -1.0
        
        # Temporal cross-validation
        splitter = TemporalSplitter(n_splits=5, test_size=0.2)
        rois = []
        total_bets = 0
        split_details = []
        early_exit = False
        
        # Log trial start for better visibility
        if self.log_callback:
            self.log_callback("info", f"Trial {trial.number}: Starting evaluation...")
        
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
            
            # Encode labels using the pre-fitted encoder
            y_train_encoded = label_encoder.transform(y_train)
            
            # Check that training set has all classes (required for XGBoost)
            # XGBoost requires all classes from 0 to n_classes-1 to be present in training data
            unique_classes = np.unique(y_train_encoded)
            expected_classes = np.arange(n_classes)
            
            if len(unique_classes) < n_classes or not np.all(np.isin(expected_classes, unique_classes)):
                # Training set doesn't have all classes - skip this split
                if self.log_callback:
                    self.log_callback("warning", 
                        f"Trial {trial.number} split {split_idx}: Training set missing classes "
                        f"(has {unique_classes.tolist()}, need {expected_classes.tolist()}). Skipping.")
                continue
            
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
                # Use original y_test (not encoded) for betting evaluator
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
                
                # Report intermediate value after each split for incremental pruning
                # Use negative ROI (since Optuna minimizes, this maximizes ROI)
                trial.report(-roi, split_idx)
                
                # Check if trial should be pruned based on intermediate results
                if trial.should_prune():
                    if self.log_callback:
                        self.log_callback("info",
                            f"Trial {trial.number} split {split_idx}: Pruned by pruner (ROI: {roi*100:+.2f}%, Bets: {bets_count})")
                    trial.set_user_attr('total_bets', total_bets)
                    trial.set_user_attr('split_details', split_details)
                    trial.set_user_attr('early_exit', True)
                    trial.set_user_attr('mean_roi', np.mean(rois) if rois else 0.0)
                    raise optuna.TrialPruned()
                
                # Early exit: If first split has 0 bets, prune immediately (before other splits)
                # This saves significant time when no value bets are found
                if split_idx == 1 and bets_count == 0:
                    if self.log_callback:
                        self.log_callback("warning",
                            f"Trial {trial.number} split 1: No value bets found (0 bets). "
                            f"Pruning trial immediately to save time. "
                            f"This may indicate EV threshold ({config.EV_THRESHOLD:.1%}) too high or insufficient odds data.")
                    early_exit = True
                    # Record this split for logging purposes
                    trial.set_user_attr('total_bets', 0)
                    trial.set_user_attr('split_details', split_details)
                    trial.set_user_attr('early_exit', True)
                    trial.set_user_attr('mean_roi', 0.0)
                    # Prune the trial - this will stop evaluation and mark it as pruned
                    raise optuna.TrialPruned()
            except optuna.TrialPruned:
                # Re-raise pruning exceptions
                raise
            except Exception as e:
                # If evaluation fails, log and use a very negative ROI to discourage this trial
                if self.log_callback:
                    self.log_callback("warning", 
                        f"Trial {trial.number} split {split_idx} evaluation failed: {e}")
                roi = -1.0
                rois.append(roi)
                split_details.append({
                    'split': split_idx,
                    'roi': roi,
                    'bets': 0,
                    'error': str(e)
                })
                # Report the bad value for pruning
                trial.report(-roi, split_idx)
                if trial.should_prune():
                    raise optuna.TrialPruned()
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
        trial.set_user_attr('early_exit', early_exit)
        
        # Track consecutive zero-bet trials (only if trial completed, not pruned)
        if total_bets == 0:
            self._consecutive_zero_bet_trials += 1
            if self.log_callback:
                self.log_callback("warning", 
                    f"Trial {trial.number}: No value bets found across all splits (ROI=0.0%). "
                    f"This may indicate EV threshold ({config.EV_THRESHOLD:.1%}) too high or insufficient odds data.")
            
            # Warn if multiple consecutive trials have 0 bets
            if self._consecutive_zero_bet_trials >= 3 and self.log_callback:
                self.log_callback("warning",
                    f"WARNING: {self._consecutive_zero_bet_trials} consecutive trials with 0 bets. "
                    f"This suggests a systemic issue. Possible causes: "
                    f"1) EV threshold ({config.EV_THRESHOLD:.1%}) is too high, "
                    f"2) Missing odds data in database, "
                    f"3) Model predictions are too conservative. "
                    f"Consider checking odds data availability or lowering EV threshold.")
        else:
            # Reset counter when we find bets
            self._consecutive_zero_bet_trials = 0
        
        # Final report (though we already reported incrementally)
        # This ensures the final value is recorded
        trial.report(-mean_roi, len(rois))
        
        # Final pruning check (though unlikely to prune here if we got this far)
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
        
        # Encode labels - fit on ALL data to ensure all classes are known
        label_encoder = LabelEncoder()
        y_encoded = label_encoder.fit_transform(y)
        
        # Verify we have valid classes
        n_classes = len(label_encoder.classes_)
        if n_classes < 1:
            self._log("error", 
                     f"Invalid number of classes after encoding: {n_classes}. Cannot proceed with tuning.")
            return None
        
        # Create fixture_ids if not provided (fallback for backward compatibility)
        if fixture_ids is None:
            fixture_ids = pd.Series([None] * len(X))
            self._log("warning", "No fixture_ids provided. Betting evaluation may be less accurate.")
        
        # Validate odds data availability before starting
        # Check if we have odds data for at least some fixtures
        if fixture_ids is not None and len(fixture_ids) > 0:
            valid_fixture_ids = fixture_ids.dropna()
            if len(valid_fixture_ids) > 0:
                # Sample a few fixture IDs to check for odds
                sample_ids = valid_fixture_ids.head(min(10, len(valid_fixture_ids)))
                odds_available = 0
                for fid in sample_ids:
                    odds = self.db.get_odds(fixture_id=fid)
                    if len(odds) > 0:
                        odds_available += 1
                
                if odds_available == 0:
                    self._log("warning",
                        f"No odds data found for sampled fixtures. "
                        f"Hyperparameter tuning may result in 0 bets for all trials. "
                        f"Consider running data collection first.")
                elif odds_available < len(sample_ids) * 0.5:
                    self._log("warning",
                        f"Limited odds data available ({odds_available}/{len(sample_ids)} sampled fixtures have odds). "
                        f"Some trials may have 0 bets.")
            else:
                self._log("warning",
                    f"All fixture_ids are None/NaN. Betting evaluation will use date-based matching, "
                    f"which may be less accurate and could result in 0 bets.")
        
        # Reset consecutive zero-bet counter at start of tuning
        self._consecutive_zero_bet_trials = 0
        
        # Warn about time (estimate based on trials and parallelization)
        # Ensure n_jobs is at least 1 for calculation
        effective_n_jobs = max(1, abs(self.n_jobs)) if self.n_jobs != -1 else 1  # -1 means all CPUs, estimate as 1 for time calc
        estimated_minutes = (self.n_trials * 3) / effective_n_jobs  # ~3 min per trial
        if self.timeout and self.timeout > 0:
            estimated_minutes = min(estimated_minutes, self.timeout / 60)
        
        self._log("info", 
                 f"Starting hyperparameter tuning ({self.search_space} search space, {self.n_trials} trials)...")
        if self.n_jobs == -1:
            self._log("info", "Using all available CPUs for parallel processing")
        elif self.n_jobs > 1:
            self._log("info", f"Using {self.n_jobs} parallel workers")
        if self.early_stopping_patience:
            self._log("info", f"Early stopping enabled (patience: {self.early_stopping_patience} trials)")
        if self.timeout and self.timeout > 0:
            self._log("info", f"Timeout: {self.timeout/60:.1f} minutes")
        self._log("warning", 
                 f"Estimated time: ~{estimated_minutes:.0f} minutes. Progress will be logged periodically.")
        
        try:
            # Create Optuna study (minimize negative ROI = maximize ROI)
            # Use MedianPruner with lower startup trials for faster pruning
            # n_startup_trials: number of trials before pruning starts (lower = prune sooner)
            # n_warmup_steps: minimum steps before pruning (1 = can prune after first split)
            study = optuna.create_study(
                direction='minimize',  # Minimize negative ROI (maximizes ROI)
                study_name=f'hyperparameter_tuning_{self.market}',
                pruner=optuna.pruners.MedianPruner(n_startup_trials=3, n_warmup_steps=1)
            )
            
            # Track best ROI for early stopping
            best_roi_history = []
            trials_since_improvement = 0
            
            # Custom callback to log trial progress and handle early stopping
            def trial_callback(study: optuna.Study, trial: optuna.Trial) -> None:
                """Log trial completion with formatted output and check early stopping."""
                nonlocal best_roi_history, trials_since_improvement
                
                trial_num = trial.number
                
                # Handle pruned trials - log briefly and skip detailed logging
                if trial.state == optuna.trial.TrialState.PRUNED:
                    early_exit = trial.user_attrs.get('early_exit', False)
                    total_bets = trial.user_attrs.get('total_bets', 0)
                    if early_exit and total_bets == 0:
                        # Already logged when pruned, just skip
                        return
                    elif early_exit:
                        # Pruned for other reason, log briefly
                        self._log("info", f"Trial {trial_num + 1}/{self.n_trials}: Pruned (Bets: {total_bets})")
                        return
                    else:
                        # Pruned by pruner, log briefly
                        self._log("info", f"Trial {trial_num + 1}/{self.n_trials}: Pruned by pruner")
                        return
                
                # Only log completed trials (not pruned)
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
                
                # Get best trial so far (only from completed trials)
                completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
                if len(completed_trials) > 0:
                    best_trial = min(completed_trials, key=lambda t: t.value)
                    best_roi = -best_trial.value
                    best_trial_num = best_trial.number
                else:
                    best_trial = None
                    best_roi = 0.0
                    best_trial_num = -1
                
                # Track best ROI history for early stopping
                if len(best_roi_history) == 0 or best_roi > best_roi_history[-1]:
                    best_roi_history.append(best_roi)
                    trials_since_improvement = 0
                else:
                    trials_since_improvement += 1
                
                # Calculate progress percentage
                completed_trials = len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])
                progress_pct = ((trial_num + 1) / self.n_trials) * 100
                
                # Log trial completion with progress
                roi_pct = mean_roi * 100
                # Format ROI with sign
                roi_str = f"{roi_pct:+.2f}%" if roi_pct != 0.0 else "0.00%"
                
                # Only log if trial has bets (skip 0-bet completed trials to reduce noise)
                if total_bets > 0:
                    self._log("info", 
                        f"Trial {trial_num + 1}/{self.n_trials} ({progress_pct:.0f}%) | "
                        f"ROI: {roi_str} | "
                        f"Bets: {total_bets} | "
                        f"Params: {params_str}")
                else:
                    # Log briefly for 0-bet completed trials (should be rare if pruning works)
                    self._log("warning",
                        f"Trial {trial_num + 1}/{self.n_trials}: Completed with 0 bets (ROI: {roi_str})")
                
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
                
                # Early stopping check
                if (self.early_stopping_patience is not None and 
                    trials_since_improvement >= self.early_stopping_patience and
                    trial_num >= 5):  # Require at least 5 trials before early stopping
                    self._log("warning",
                        f"Early stopping: No improvement in last {trials_since_improvement} trials. "
                        f"Best ROI: {best_roi*100:+.2f}%")
                    study.stop()
            
            # Run optimization with callback
            # Ensure n_jobs is valid (Optuna accepts -1 for all CPUs, or positive integer)
            effective_n_jobs = self.n_jobs if self.n_jobs == -1 or self.n_jobs > 0 else 1
            effective_timeout = self.timeout if self.timeout and self.timeout > 0 else None
            
            study.optimize(
                lambda trial: self._objective(trial, X, y, dates, fixture_ids, label_encoder),
                n_trials=self.n_trials,
                timeout=effective_timeout,
                n_jobs=effective_n_jobs,
                show_progress_bar=False,  # We'll log manually
                callbacks=[trial_callback]
            )
            
            # Get best parameters (handle case where all trials were pruned)
            try:
                if len(study.trials) == 0:
                    self._log("warning", "No trials completed. All trials may have been pruned.")
                    return None
                
                # Find best completed trial (not pruned)
                completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
                if len(completed_trials) == 0:
                    self._log("warning", 
                        "No completed trials. All trials were pruned. "
                        "This likely indicates all hyperparameter combinations resulted in 0 bets. "
                        "Consider: 1) Lowering EV threshold, 2) Running data collection, 3) Checking odds data availability.")
                    return None
                
                # Get best trial from completed ones
                best_trial = min(completed_trials, key=lambda t: t.value)
                self.best_params = best_trial.params.copy()
                # best_value is negative ROI, so convert back to positive
                self.best_score = -best_trial.value  # Convert back to positive ROI
            except Exception as e:
                self._log("error", f"Failed to get best parameters: {e}")
                return None
            
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


class TradingHyperparameterTuner:
    """
    Hyperparameter tuning for trading prediction models using Optuna.
    Optimizes for Sharpe ratio with temporal cross-validation.
    """
    
    def __init__(self, strategy: str, search_space: str = 'medium',
                 min_samples: int = 300, n_trials: Optional[int] = None,
                 log_callback: Optional[Callable[[str, str], None]] = None,
                 n_jobs: int = 1,
                 timeout: Optional[float] = None,
                 early_stopping_patience: Optional[int] = None):
        """
        Initialize trading hyperparameter tuner.
        
        Args:
            strategy: Trading strategy ('momentum', 'swing', 'volatility')
            search_space: Size of search space ('small', 'medium', 'large')
            min_samples: Minimum samples required for tuning
            n_trials: Number of Optuna trials (None = auto based on search_space)
            log_callback: Optional callback for logging
            n_jobs: Number of parallel jobs (1 = sequential, -1 = all CPUs)
            timeout: Maximum time in seconds (None = no timeout)
            early_stopping_patience: Stop if no improvement in last N trials (None = disabled)
        """
        self.strategy = strategy
        self.search_space = search_space
        self.min_samples = min_samples
        self.log_callback = log_callback
        self.best_params = None
        self.best_score = None
        self.n_jobs = n_jobs
        self.timeout = timeout
        self.early_stopping_patience = early_stopping_patience
        
        # Set n_trials based on search_space if not specified
        if n_trials is None:
            if search_space == 'small':
                n_trials = 15
            elif search_space == 'medium':
                n_trials = 30
            else:  # large
                n_trials = 60
        self.n_trials = n_trials
    
    def _log(self, level: str, message: str):
        """Log a message."""
        if self.log_callback:
            self.log_callback(level, message)
        else:
            print(f"[{level.upper()}] {message}")
    
    def _get_search_space(self, trial: optuna.Trial) -> Dict[str, Any]:
        """Get hyperparameter search space for this trial."""
        if self.search_space == 'small':
            return {
                'n_estimators': trial.suggest_int('n_estimators', 50, 200, step=50),
                'max_depth': trial.suggest_int('max_depth', 3, 7),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
                'subsample': trial.suggest_float('subsample', 0.7, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.7, 1.0)
            }
        elif self.search_space == 'medium':
            return {
                'n_estimators': trial.suggest_int('n_estimators', 50, 250, step=25),
                'max_depth': trial.suggest_int('max_depth', 3, 8),
                'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.3, log=True),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 7),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.5),
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
    
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate Sharpe ratio from returns series."""
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        return returns.mean() / returns.std() if returns.std() > 0 else 0.0
    
    def _objective(self, trial: optuna.Trial, X: pd.DataFrame, y: pd.Series,
                   dates: pd.Series, symbols: Optional[pd.Series] = None) -> float:
        """
        Optuna objective function: maximize Sharpe ratio (returns negative Sharpe since Optuna minimizes).
        
        Args:
            trial: Optuna trial
            X: Features
            y: Labels (binary: 1=up, 0=down)
            dates: Timestamps for temporal splitting
            symbols: Symbol names (optional)
            
        Returns:
            Negative Sharpe ratio (to minimize, which maximizes Sharpe)
        """
        # Get hyperparameters for this trial
        params = self._get_search_space(trial)
        params.update({
            'random_state': 42,
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            'verbosity': 0
        })
        
        # Temporal cross-validation
        splitter = TemporalSplitter(n_splits=5, test_size=0.2)
        sharpe_ratios = []
        split_details = []
        
        for split_idx, (train_idx, test_idx) in enumerate(splitter.split(X, y, groups=dates), 1):
            # Split data
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            dates_test = dates.iloc[test_idx]
            
            # Check minimum samples
            if len(X_train) < self.min_samples or len(X_test) < 10:
                continue
            
            # Train model
            model = XGBClassifier(**params)
            model.fit(X_train, y_train)
            
            # Predict probabilities
            y_proba = model.predict_proba(X_test)[:, 1]
            
            # Calculate returns based on predictions
            # For simplicity, assume we take positions when probability > 0.5
            # Returns = (actual_direction - 0.5) * 2 * prediction_confidence
            # This approximates trading returns
            predicted_direction = (y_proba > 0.5).astype(int)
            actual_direction = y_test.values
            
            # Calculate returns: correct prediction = positive return, wrong = negative
            # Use prediction confidence (probability) as position size
            returns = np.where(
                predicted_direction == actual_direction,
                y_proba * 0.02,  # 2% return for correct prediction (scaled by confidence)
                -y_proba * 0.01  # -1% return for wrong prediction (scaled by confidence)
            )
            
            returns_series = pd.Series(returns)
            sharpe = self._calculate_sharpe_ratio(returns_series)
            sharpe_ratios.append(sharpe)
            
            split_details.append({
                'split': split_idx,
                'sharpe': sharpe,
                'test_samples': len(X_test),
                'accuracy': (predicted_direction == actual_direction).mean()
            })
            
            # Report intermediate value
            trial.report(-sharpe, split_idx)
            
            # Check if trial should be pruned
            if trial.should_prune():
                raise optuna.TrialPruned()
        
        if len(sharpe_ratios) == 0:
            return -1.0  # Very negative if no valid splits
        
        # Average Sharpe ratio across splits
        avg_sharpe = np.mean(sharpe_ratios)
        return -avg_sharpe  # Negative because Optuna minimizes
    
    def tune(self, X: pd.DataFrame, y: pd.Series, dates: pd.Series,
             symbols: Optional[pd.Series] = None) -> Optional[Dict[str, Any]]:
        """
        Run hyperparameter tuning.
        
        Args:
            X: Features
            y: Labels
            dates: Timestamps for temporal splitting
            symbols: Symbol names (optional)
            
        Returns:
            Best hyperparameters found, or None if tuning failed
        """
        if len(X) < self.min_samples:
            self._log("warning", 
                     f"Insufficient samples ({len(X)} < {self.min_samples}). Skipping hyperparameter tuning.")
            return None
        
        try:
            self._log("info", 
                     f"Starting hyperparameter tuning for {self.strategy} strategy "
                     f"({self.n_trials} trials, {self.search_space} search space)...")
            
            # Create study
            study = optuna.create_study(
                direction='minimize',  # We return negative Sharpe, so minimize = maximize Sharpe
                pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=2)
            )
            
            # Add early stopping callback if enabled
            callbacks = []
            if self.early_stopping_patience is not None:
                callbacks.append(
                    optuna.study.MaxTrialsCallback(
                        self.n_trials,
                        mode='min'
                    )
                )
            
            # Run optimization
            study.optimize(
                lambda trial: self._objective(trial, X, y, dates, symbols),
                n_trials=self.n_trials,
                n_jobs=self.n_jobs,
                timeout=self.timeout,
                callbacks=callbacks,
                show_progress_bar=False
            )
            
            if len(study.trials) == 0:
                self._log("warning", "No trials completed. Using default hyperparameters.")
                return None
            
            # Get best parameters
            self.best_params = study.best_params
            self.best_score = -study.best_value  # Convert back to positive Sharpe
            
            self._log("info", 
                     f"Hyperparameter tuning completed. Best Sharpe ratio: {self.best_score:.4f}")
            
            # Format best hyperparameters
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
        """Get best Sharpe ratio achieved during tuning."""
        return self.best_score
