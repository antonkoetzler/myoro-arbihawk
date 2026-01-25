"""
Training script for Arbihawk betting prediction models.
Trains models for all markets (1x2, over_under, btts).

Optimized to compute features once and reuse for all markets.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, Callable

from data.database import Database
from data.features import FeatureEngineer
from models import BettingPredictor
import config
from utils.colors import (
    print_header, print_success, print_error, 
    print_warning, print_info, print_step
)


def train_models(db: Optional[Database] = None, log_callback: Optional[Callable[[str, str], None]] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Train prediction models for all markets.
    
    Features are computed once and reused for all markets (1x2, over_under, btts).
    
    Returns:
        Tuple of (success: bool, metrics: dict)
        - success: True if training completed without errors (even if no data)
        - metrics.has_data: True if at least one model was trained
        - metrics.errors: List of actual errors encountered
    """
    if log_callback:
        log_callback("info", "=" * 60)
        log_callback("info", "Model Training")
        log_callback("info", "=" * 60)
    else:
        print_header("Model Training")
    
    markets = ['1x2', 'over_under', 'btts']
    db = db or Database()
    feature_engineer = FeatureEngineer(db)
    
    models_dir = Path(__file__).parent / "models" / "saved"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    trained_count = 0
    no_data_count = 0
    actual_errors = []  # Track actual errors (exceptions, failures) vs no-data situations
    
    metrics = {
        "trained_at": datetime.now().isoformat(),
        "markets": {},
        "total_samples": 0,
        "has_data": False,  # Will be True if any models were trained
        "errors": [],  # List of actual error messages
        "no_data_reason": None  # Explanation if no data available
    }
    
    # Compute features ONCE for all markets (vectorized)
    if log_callback:
        log_callback("info", "Creating features for all markets (vectorized)...")
    else:
        print_step("Creating features for all markets (vectorized)...")
    
    try:
        X, labels, dates, fixture_ids = feature_engineer.create_training_data(log_callback=log_callback)
    except Exception as e:
        error_msg = f"Error creating features: {e}"
        if log_callback:
            log_callback("error", error_msg)
        else:
            print_error(error_msg)
        metrics["errors"].append(error_msg)
        return False, metrics
    
    if len(X) == 0 or len(labels) == 0:
        if log_callback:
            log_callback("warning", "No training data available. Skipping all markets...")
        else:
            print_warning("No training data available. Skipping all markets...")
        metrics["no_data_reason"] = "No completed matches with scores available for training"
        return True, metrics
    
    if log_callback:
        log_callback("info", f"Features computed: {len(X)} samples, {len(X.columns)} features")
    else:
        print_info(f"Features computed: {len(X)} samples, {len(X.columns)} features")
    
    # Train each market using shared features
    for market in markets:
        if log_callback:
            log_callback("info", f"Training {market} market")
        else:
            print_info(f"Training {market} market")
        
        # Get labels for this market
        if market not in labels:
            if log_callback:
                log_callback("warning", f"No labels for {market} market. Skipping...")
            else:
                print_warning(f"No labels for {market} market. Skipping...")
            metrics["markets"][market] = {"skipped": True, "reason": "No labels"}
            no_data_count += 1
            continue
        
        y = labels[market]
        
        if len(y) == 0:
            if log_callback:
                log_callback("warning", f"No training data available for {market}. Skipping...")
            else:
                print_warning(f"No training data available for {market}. Skipping...")
            metrics["markets"][market] = {"skipped": True, "reason": "No training data"}
            no_data_count += 1
            continue
        
        if log_callback:
            log_callback("info", f"Training data: {len(X)} samples, {len(X.columns)} features")
        else:
            print_info(f"Training data: {len(X)} samples, {len(X.columns)} features")
        
        label_dist_str = str(y.value_counts())
        if log_callback:
            log_callback("info", f"Label distribution:\n{label_dist_str}")
        else:
            print_info(f"Label distribution:\n{label_dist_str}")
        
        # Train model
        if log_callback:
            log_callback("info", "-> Training model...")
        else:
            print_step("Training model...")
        predictor = BettingPredictor(market=market)
        try:
            predictor.train(X, y, dates=dates, fixture_ids=fixture_ids, log_callback=log_callback, db=db)
            # Get CV score from predictor (defaults to 0.5 if not available)
            cv_score = getattr(predictor, 'cv_score', 0.5)
            cv_std = getattr(predictor, 'cv_std', 0.0)
            cv_folds = getattr(predictor, 'cv_folds', 5)
            if log_callback:
                log_callback("info", f"Cross-validation accuracy ({cv_folds}-fold): {cv_score:.3f} (+/- {cv_std * 2:.3f})")
            
            # Get betting metrics if available
            betting_metrics = getattr(predictor, 'betting_metrics', {})
            if betting_metrics:
                if log_callback:
                    log_callback("info", 
                        f"Betting metrics - ROI: {betting_metrics.get('roi', 0):.2%}, "
                        f"Profit: ${betting_metrics.get('profit', 0):.2f}, "
                        f"Win Rate: {betting_metrics.get('win_rate', 0):.2%}, "
                        f"Sharpe: {betting_metrics.get('sharpe_ratio', 0):.2f}, "
                        f"Bets: {betting_metrics.get('total_bets', 0)}")
                else:
                    print_info(f"Betting metrics - ROI: {betting_metrics.get('roi', 0):.2%}, "
                              f"Profit: ${betting_metrics.get('profit', 0):.2f}, "
                              f"Win Rate: {betting_metrics.get('win_rate', 0):.2%}, "
                              f"Sharpe: {betting_metrics.get('sharpe_ratio', 0):.2f}, "
                              f"Bets: {betting_metrics.get('total_bets', 0)}")
        except Exception as e:
            error_msg = f"Error training model for {market}: {e}"
            if log_callback:
                log_callback("error", error_msg)
            else:
                print_error(error_msg)
            metrics["markets"][market] = {"error": str(e), "error_type": "training"}
            actual_errors.append(error_msg)
            continue
        
        # Save model
        model_path = models_dir / f"{market}_model.pkl"
        try:
            predictor.save(str(model_path))
            if log_callback:
                log_callback("success", f"Model saved to {model_path}")
            else:
                print_success(f"Model saved to {model_path}")
            trained_count += 1
            
            # Get CV score from predictor (defaults to 0.5 if not available)
            cv_score = getattr(predictor, 'cv_score', 0.5)
            
            # Save to versioning system
            from models.versioning import ModelVersionManager
            version_manager = ModelVersionManager(db)
            
            # Get calibration metrics if available
            calibration_metrics = getattr(predictor, 'calibration_metrics', {})
            
            # Build performance metrics including calibration, hyperparameters, and betting metrics
            performance_metrics = {
                "features": len(X.columns),
                "label_distribution": y.value_counts().to_dict()
            }
            
            # Add calibration metrics if available
            if calibration_metrics:
                if 'calibrated' in calibration_metrics:
                    performance_metrics['brier_score'] = calibration_metrics['calibrated'].get('brier_score')
                    performance_metrics['ece'] = calibration_metrics['calibrated'].get('ece')
                if 'improvement' in calibration_metrics:
                    performance_metrics['calibration_improvement'] = calibration_metrics['improvement']
            
            # Add hyperparameter tuning results if available
            hyperparameters = getattr(predictor, 'hyperparameters', None)
            tuning_metrics = getattr(predictor, 'tuning_metrics', {})
            if hyperparameters:
                performance_metrics['hyperparameters'] = hyperparameters
                performance_metrics['tuning_metrics'] = tuning_metrics
            
            # Add betting metrics if available
            betting_metrics = getattr(predictor, 'betting_metrics', {})
            if betting_metrics:
                performance_metrics['betting_metrics'] = betting_metrics
            
            version_id = version_manager.save_version(
                domain='betting',
                market=market,
                model_path=str(model_path),
                training_samples=len(X),
                cv_score=cv_score,
                performance_metrics=performance_metrics,
                activate=True
            )
            if log_callback:
                log_callback("info", f"Model version {version_id} saved and activated")
            else:
                print_info(f"Model version {version_id} saved and activated")
            
            # Get calibration metrics if available
            calibration_metrics = getattr(predictor, 'calibration_metrics', {})
            
            metrics["markets"][market] = {
                "samples": len(X),
                "features": len(X.columns),
                "model_path": str(model_path),
                "version_id": version_id,
                "cv_score": cv_score,
                "label_distribution": y.value_counts().to_dict(),
                "calibration_metrics": calibration_metrics,
                "betting_metrics": betting_metrics
            }
            metrics["total_samples"] += len(X)
        except Exception as e:
            error_msg = f"Error saving model for {market}: {e}"
            if log_callback:
                log_callback("error", error_msg)
            else:
                print_error(error_msg)
            metrics["markets"][market] = {"error": str(e), "error_type": "save"}
            actual_errors.append(error_msg)
            continue
    
    # Determine success - success means no actual errors occurred
    # (not having data is NOT an error, it's just a warning condition)
    success = len(actual_errors) == 0
    has_data = trained_count > 0
    
    metrics["trained_count"] = trained_count
    metrics["total_markets"] = len(markets)
    metrics["has_data"] = has_data
    metrics["errors"] = actual_errors
    
    # Set no_data_reason if applicable
    if no_data_count == len(markets):
        metrics["no_data_reason"] = "No completed matches with scores available for training"
    elif no_data_count > 0:
        metrics["no_data_reason"] = f"{no_data_count} markets skipped due to insufficient data"
    
    if log_callback:
        log_callback("success", f"Trained {trained_count}/{len(markets)} models")
    else:
        print_success(f"Trained {trained_count}/{len(markets)} models")
    return success, metrics


def main():
    """Main training pipeline."""
    print_header("Arbihawk Training Pipeline")
    
    # Check if we have data
    db = Database()
    fixtures = db.get_fixtures()
    scores = db.get_scores()
    
    if len(fixtures) == 0:
        print_warning("No fixtures in database. Please run data collection first.")
        print_info("Use: python -m automation.runner --mode=collect")
        return 1
    
    if len(scores) == 0:
        print_warning("No scores in database. Models require completed matches.")
        print_info("Use: python -m automation.runner --mode=collect")
        return 1
    
    print_info(f"Found {len(fixtures)} fixtures and {len(scores)} scores")
    
    # Train models
    success, metrics = train_models(db)
    
    if not success:
        print_error("\nModel training failed. Exiting.")
        return 1
    
    print_header("Training Complete!")
    print_success("All models trained successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
