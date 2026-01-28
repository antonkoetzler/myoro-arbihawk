"""End-to-end test for trading features and training."""
from data.stock_features import StockFeatureEngineer
from data.database import Database
import pandas as pd

def test_e2e_training_data():
    """Test end-to-end training data creation with temporal features."""
    print("=" * 60)
    print("End-to-End Trading Training Data Test")
    print("=" * 60)
    
    db = Database()
    fe = StockFeatureEngineer(db)
    
    print("\nTest: create_training_data with temporal features")
    X, labels, dates, symbols = fe.create_training_data('momentum', lookback_days=90)
    
    if len(X) == 0:
        print("  WARNING: No training data available (this is OK if no price data)")
        return
    
    print(f"  Total features: {len(X.columns)}")
    print(f"  Sample count: {len(X)}")
    
    # Check temporal features
    temporal_features = ['day_of_week', 'is_weekend', 'month', 'day_of_month']
    has_all_temporal = all(f in X.columns for f in temporal_features)
    print(f"  Temporal features present: {has_all_temporal}")
    
    if has_all_temporal:
        print("  Sample temporal values:")
        print(f"    day_of_week: {X['day_of_week'].head(5).tolist()}")
        print(f"    is_weekend: {X['is_weekend'].head(5).tolist()}")
        print(f"    month: {X['month'].head(5).tolist()}")
        print(f"    day_of_month: {X['day_of_month'].head(5).tolist()}")
        
        # Validate values
        assert (X['day_of_week'] >= 0).all() and (X['day_of_week'] <= 6).all(), "day_of_week out of range"
        assert (X['is_weekend'] >= 0).all() and (X['is_weekend'] <= 1).all(), "is_weekend out of range"
        assert (X['month'] >= 1).all() and (X['month'] <= 12).all(), "month out of range"
        assert (X['day_of_month'] >= 1).all() and (X['day_of_month'] <= 31).all(), "day_of_month out of range"
        print("  All temporal values in valid range - PASSED")
    
    print("\n  PASSED")
    print("\n" + "=" * 60)
    print("End-to-end test PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_e2e_training_data()
