"""Test training flow."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "arbihawk"))

from train import train_models
from data.database import Database
from data.features import FeatureEngineer
from utils.colors import print_header, print_info, print_success, print_warning

def test_training():
    """Test training flow."""
    print_header("Testing Training Flow")
    
    db = Database()
    
    # Check data availability
    fixtures = db.get_fixtures()
    scores = db.get_scores()
    odds = db.get_odds()
    
    print_info(f"Database state:")
    print_info(f"  Fixtures: {len(fixtures)}")
    print_info(f"  Scores: {len(scores)}")
    print_info(f"  Odds: {len(odds)}")
    
    # Check matched data
    matched = fixtures.merge(scores, on='fixture_id', how='inner')
    print_info(f"  Matched fixtures+scores: {len(matched)}")
    
    if len(matched) == 0:
        print_warning("No matched data available for training!")
        return False
    
    # Test feature engineering
    print_info("Testing feature engineering...")
    fe = FeatureEngineer(db)
    X, y = fe.create_training_data('1x2')
    
    print_info(f"Training data: {len(X)} samples, {len(X.columns) if len(X) > 0 else 0} features")
    
    if len(X) == 0:
        print_warning("No training data generated!")
        return False
    
    print_info(f"Label distribution: {y.value_counts().to_dict()}")
    
    # Run training
    print_info("Running training...")
    success, metrics = train_models(db)
    
    print_success(f"Training completed: {success}")
    print_info(f"Metrics: {metrics}")
    
    return success

if __name__ == "__main__":
    success = test_training()
    sys.exit(0 if success else 1)
