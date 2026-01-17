"""
Training script for Arbihawk betting prediction models.
Trains models for all markets (1x2, over_under, btts).
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from data.database import Database
from data.features import FeatureEngineer
from models import BettingPredictor
import config
from utils.colors import (
    print_header, print_success, print_error, 
    print_warning, print_info, print_step
)


def train_models(db: Optional[Database] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Train prediction models for all markets.
    
    Returns:
        Tuple of (success: bool, metrics: dict)
        - success: True if training completed without errors (even if no data)
        - metrics.has_data: True if at least one model was trained
        - metrics.errors: List of actual errors encountered
    """
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
    
    for market in markets:
        print_info(f"Training {market} market")
        
        # Create training data
        print_step("Creating features...")
        try:
            X, y = feature_engineer.create_training_data(market=market)
        except Exception as e:
            error_msg = f"Error creating features for {market}: {e}"
            print_error(error_msg)
            metrics["markets"][market] = {"error": str(e), "error_type": "feature_creation"}
            actual_errors.append(error_msg)
            continue
        
        if len(X) == 0 or len(y) == 0:
            print_warning(f"No training data available. Skipping...")
            metrics["markets"][market] = {"skipped": True, "reason": "No training data"}
            no_data_count += 1
            continue
        
        print_info(f"Training data: {len(X)} samples, {len(X.columns)} features")
        print_info(f"Label distribution:\n{y.value_counts()}")
        
        # Train model
        print_step("Training model...")
        predictor = BettingPredictor(market=market)
        try:
            predictor.train(X, y)
        except Exception as e:
            error_msg = f"Error training model for {market}: {e}"
            print_error(error_msg)
            metrics["markets"][market] = {"error": str(e), "error_type": "training"}
            actual_errors.append(error_msg)
            continue
        
        # Save model
        model_path = models_dir / f"{market}_model.pkl"
        try:
            predictor.save(str(model_path))
            print_success(f"Model saved to {model_path}")
            trained_count += 1
            
            metrics["markets"][market] = {
                "samples": len(X),
                "features": len(X.columns),
                "model_path": str(model_path),
                "label_distribution": y.value_counts().to_dict()
            }
            metrics["total_samples"] += len(X)
        except Exception as e:
            error_msg = f"Error saving model for {market}: {e}"
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
