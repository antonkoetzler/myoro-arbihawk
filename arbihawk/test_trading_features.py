"""Test script for trading temporal features and hyperparameter tuning."""
from data.stock_features import StockFeatureEngineer
from data.database import Database
import pandas as pd
import numpy as np

def test_temporal_features():
    """Test temporal features in trading."""
    print("=" * 60)
    print("Testing Trading Temporal Features")
    print("=" * 60)
    
    db = Database()
    fe = StockFeatureEngineer(db)
    
    # Test 1: Temporal feature extraction
    print("\nTest 1: Temporal feature extraction")
    result = fe._get_temporal_features('2024-01-15T15:30:00')
    print(f"  Monday 3:30 PM: {result}")
    assert result['day_of_week'] == 0.0, "Should be Monday (0)"
    assert result['is_weekend'] == 0.0, "Should not be weekend"
    assert result['month'] == 1.0, "Should be January (1)"
    assert result['day_of_month'] == 15.0, "Should be day 15"
    print("  PASSED")
    
    result2 = fe._get_temporal_features('2024-01-20T20:00:00')
    print(f"  Saturday 8:00 PM: {result2}")
    assert result2['day_of_week'] == 5.0, "Should be Saturday (5)"
    assert result2['is_weekend'] == 1.0, "Should be weekend"
    print("  PASSED")
    
    # Test 2: Invalid date handling
    print("\nTest 2: Invalid date handling")
    result3 = fe._get_temporal_features('invalid-date')
    print(f"  Invalid date: {result3}")
    assert result3['day_of_week'] == 0.0, "Should return default"
    assert result3['is_weekend'] == 0.0, "Should return default"
    print("  PASSED")
    
    # Test 3: Feature columns include temporal features
    print("\nTest 3: Feature columns include temporal features")
    momentum_cols = fe._get_feature_columns('momentum')
    swing_cols = fe._get_feature_columns('swing')
    volatility_cols = fe._get_feature_columns('volatility')
    
    temporal_features = ['day_of_week', 'is_weekend', 'month', 'day_of_month']
    for feat in temporal_features:
        assert feat in momentum_cols, f"{feat} missing from momentum features"
        assert feat in swing_cols, f"{feat} missing from swing features"
        assert feat in volatility_cols, f"{feat} missing from volatility features"
    
    print(f"  Momentum features: {len(momentum_cols)} (expected: 33)")
    print(f"  Swing features: {len(swing_cols)} (expected: 39)")
    print(f"  Volatility features: {len(volatility_cols)} (expected: 41)")
    assert len(momentum_cols) == 33, f"Expected 33 momentum features, got {len(momentum_cols)}"
    assert len(swing_cols) == 39, f"Expected 39 swing features, got {len(swing_cols)}"
    assert len(volatility_cols) == 41, f"Expected 41 volatility features, got {len(volatility_cols)}"
    print("  PASSED")
    
    # Test 4: Temporal features in indicator computation
    print("\nTest 4: Temporal features in indicator computation")
    test_df = pd.DataFrame({
        'timestamp': ['2024-01-15', '2024-01-16', '2024-01-17'],
        'open': [100.0, 101.0, 102.0],
        'high': [105.0, 106.0, 107.0],
        'low': [99.0, 100.0, 101.0],
        'close': [103.0, 104.0, 105.0],
        'volume': [1000000, 1100000, 1200000]
    })
    
    df_with_indicators = fe.compute_indicators(test_df)
    
    assert 'day_of_week' in df_with_indicators.columns, "day_of_week missing"
    assert 'is_weekend' in df_with_indicators.columns, "is_weekend missing"
    assert 'month' in df_with_indicators.columns, "month missing"
    assert 'day_of_month' in df_with_indicators.columns, "day_of_month missing"
    
    print(f"  Temporal features present: {all(f in df_with_indicators.columns for f in temporal_features)}")
    print(f"  Sample values:")
    print(f"    day_of_week: {df_with_indicators['day_of_week'].tolist()}")
    print(f"    is_weekend: {df_with_indicators['is_weekend'].tolist()}")
    print(f"    month: {df_with_indicators['month'].tolist()}")
    print(f"    day_of_month: {df_with_indicators['day_of_month'].tolist()}")
    print("  PASSED")
    
    print("\n" + "=" * 60)
    print("All temporal feature tests PASSED!")
    print("=" * 60)

def test_hyperparameter_tuning_import():
    """Test that hyperparameter tuning can be imported and initialized."""
    print("\n" + "=" * 60)
    print("Testing Hyperparameter Tuning Import")
    print("=" * 60)
    
    try:
        from models.hyperparameter_tuning import TradingHyperparameterTuner
        print("\nTest 1: Import TradingHyperparameterTuner")
        print("  PASSED")
        
        print("\nTest 2: Initialize tuner")
        tuner = TradingHyperparameterTuner(
            strategy='momentum',
            search_space='small',
            n_trials=5
        )
        assert tuner.strategy == 'momentum', "Strategy should be momentum"
        assert tuner.search_space == 'small', "Search space should be small"
        assert tuner.n_trials == 5, "n_trials should be 5"
        print("  PASSED")
        
        print("\nTest 3: Get search space")
        import optuna
        study = optuna.create_study()
        trial = study.ask()
        params = tuner._get_search_space(trial)
        assert 'n_estimators' in params, "n_estimators should be in params"
        assert 'max_depth' in params, "max_depth should be in params"
        assert 'learning_rate' in params, "learning_rate should be in params"
        print(f"  Search space params: {list(params.keys())}")
        print("  PASSED")
        
        print("\n" + "=" * 60)
        print("All hyperparameter tuning import tests PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    test_temporal_features()
    test_hyperparameter_tuning_import()
