"""
Training script for Arbihawk betting prediction models.
Trains models for all markets (1x2, over_under, btts).
"""

from datetime import datetime, timedelta
from pathlib import Path

from data import DataCollector
from data.database import Database
from data.features import FeatureEngineer
from models import BettingPredictor
import config
from utils.colors import (
    print_header, print_success, print_error, 
    print_warning, print_info, print_step
)


def collect_data():
    """Collect historical data for training."""
    print_header("Data Collection")
    
    collector = DataCollector()
    
    # Get soccer sport ID
    print_step("Getting soccer sport ID...")
    try:
        sport_id = collector.odds_collector.get_soccer_sport_id()
        if not sport_id:
            print_error("Could not find soccer sport ID")
            return False
        print_success(f"Soccer sport ID: {sport_id}")
    except ValueError as e:
        print_error(f"API Error: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error getting sport ID: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Calculate date range (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    from_date = start_date.strftime('%Y-%m-%d')
    to_date = end_date.strftime('%Y-%m-%d')
    
    print_info(f"Collecting fixtures from {from_date} to {to_date}")
    
    # Collect fixtures
    print_step("Collecting fixtures...")
    try:
        fixtures_collected = collector.collect_fixtures(
            sport_id=sport_id,
            from_date=from_date,
            to_date=to_date,
            tournament_ids=None,
            incremental=True
        )
        print_success(f"Collected {fixtures_collected} fixtures")
    except Exception as e:
        print_error(f"Error collecting fixtures: {e}")
        return False
    
    # Collect odds for fixtures (limited to avoid rate limits)
    print_step("Collecting odds (limited to 100 fixtures to avoid rate limits)...")
    try:
        odds_collected = collector.collect_odds_for_fixtures(limit=100)
        print_success(f"Collected odds for {odds_collected} fixtures")
    except Exception as e:
        print_warning(f"Error collecting odds: {e}")
        # Continue even if odds collection fails
    
    # Collect scores for completed matches only
    print_step("Collecting scores for finished fixtures (limited to 100)...")
    try:
        scores_collected = collector.collect_scores_for_fixtures(limit=100)
        print_success(f"Collected scores for {scores_collected} fixtures")
    except Exception as e:
        print_warning(f"Error collecting scores: {e}")
        # Continue even if scores collection fails
    
    return True


def train_models():
    """Train prediction models for all markets."""
    print_header("Model Training")
    
    markets = ['1x2', 'over_under', 'btts']
    db = Database()
    feature_engineer = FeatureEngineer(db)
    
    models_dir = Path(__file__).parent / "models" / "saved"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    trained_count = 0
    
    for market in markets:
        print_info(f"Training {market} market")
        
        # Create training data
        print_step("Creating features...")
        try:
            X, y = feature_engineer.create_training_data(market=market)
        except Exception as e:
            print_error(f"Error creating features: {e}")
            continue
        
        if len(X) == 0 or len(y) == 0:
            print_warning(f"No training data available. Skipping...")
            continue
        
        print_info(f"Training data: {len(X)} samples, {len(X.columns)} features")
        print_info(f"Label distribution:\n{y.value_counts()}")
        
        # Train model
        print_step("Training model...")
        predictor = BettingPredictor(market=market)
        try:
            predictor.train(X, y)
        except Exception as e:
            print_error(f"Error training model: {e}")
            continue
        
        # Save model
        model_path = models_dir / f"{market}_model.pkl"
        try:
            predictor.save(str(model_path))
            print_success(f"Model saved to {model_path}")
            trained_count += 1
        except Exception as e:
            print_error(f"Error saving model: {e}")
            continue
    
    print_success(f"Trained {trained_count}/{len(markets)} models")
    return trained_count > 0


def main():
    """Main training pipeline."""
    print_header("Arbihawk Training Pipeline")
    
    # Collect data
    if not collect_data():
        print_error("\nData collection failed. Exiting.")
        return
    
    # Train models
    if not train_models():
        print_error("\nModel training failed. Exiting.")
        return
    
    print_header("Training Complete!")
    print_success("All models trained successfully!")


if __name__ == "__main__":
    main()

