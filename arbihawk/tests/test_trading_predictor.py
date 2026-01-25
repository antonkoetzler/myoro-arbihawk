"""
Tests for trading predictor model.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


class TestTradingPredictor:
    """Tests for TradingPredictor class."""
    
    @pytest.fixture
    def predictor(self):
        """Create TradingPredictor instance."""
        from models.trading_predictor import TradingPredictor
        return TradingPredictor(strategy='momentum')
    
    @pytest.fixture
    def training_data(self):
        """Create sample training data."""
        np.random.seed(42)
        n_samples = 500
        
        X = pd.DataFrame({
            'rsi': np.random.uniform(20, 80, n_samples),
            'macd': np.random.randn(n_samples) * 2,
            'macd_signal': np.random.randn(n_samples) * 2,
            'sma_20': np.random.uniform(95, 105, n_samples),
            'sma_50': np.random.uniform(95, 105, n_samples),
            'return_1d': np.random.randn(n_samples) * 0.02,
            'return_5d': np.random.randn(n_samples) * 0.05,
            'volatility_20d': np.random.uniform(0.01, 0.05, n_samples),
            'volume_change': np.random.randn(n_samples) * 0.3,
            'atr': np.random.uniform(1, 5, n_samples)
        })
        
        # Create labels based on features (for realistic prediction)
        y = pd.Series((X['return_1d'] > 0).astype(int))  # 1 for up, 0 for down
        
        return X, y
    
    def test_initialization(self, predictor):
        """Test predictor initialization."""
        assert predictor.strategy == 'momentum'
        assert predictor.model is not None  # XGBClassifier is initialized
    
    def test_train(self, predictor, training_data):
        """Test model training."""
        X, y = training_data
        
        predictor.train(X, y)
        
        assert predictor.model is not None
    
    def test_predict_probabilities_returns_dataframe(self, predictor, training_data):
        """Test probability predictions return DataFrame."""
        X, y = training_data
        predictor.train(X, y)
        
        # Test on subset
        test_X = X.iloc[:10]
        probs = predictor.predict_probabilities(test_X)
        
        assert isinstance(probs, pd.DataFrame)
        assert 'up' in probs.columns
        assert len(probs) == 10
    
    def test_predict_direction(self, predictor, training_data):
        """Test direction predictions."""
        X, y = training_data
        predictor.train(X, y)
        
        test_X = X.iloc[:10]
        directions = predictor.predict(test_X)
        
        assert len(directions) == 10
    
    def test_feature_importance(self, predictor, training_data):
        """Test feature importance extraction."""
        X, y = training_data
        predictor.train(X, y)
        
        importance = predictor.feature_importance
        
        assert isinstance(importance, dict)
    
    def test_save_and_load(self, predictor, training_data, tmp_path):
        """Test model save and load."""
        X, y = training_data
        predictor.train(X, y)
        
        # Save
        save_path = tmp_path / "test_model.pkl"
        predictor.save(str(save_path))
        
        # Load into new instance
        from models.trading_predictor import TradingPredictor
        new_predictor = TradingPredictor(strategy='momentum')
        new_predictor.load(str(save_path))
        
        # Predictions should work
        test_X = X.iloc[:5]
        loaded_preds = new_predictor.predict_probabilities(test_X)
        assert len(loaded_preds) == 5
    
    def test_different_strategies(self, training_data):
        """Test all three strategies can be trained."""
        from models.trading_predictor import TradingPredictor
        
        X, y = training_data
        
        for strategy in ['momentum', 'swing', 'volatility']:
            predictor = TradingPredictor(strategy=strategy)
            predictor.train(X, y)
            
            assert predictor.strategy == strategy


class TestModelMetrics:
    """Test model evaluation metrics."""
    
    @pytest.fixture
    def trained_predictor(self):
        """Create a trained predictor."""
        from models.trading_predictor import TradingPredictor
        
        np.random.seed(42)
        X = pd.DataFrame({
            'rsi': np.random.uniform(20, 80, 300),
            'macd': np.random.randn(300) * 2,
            'return_1d': np.random.randn(300) * 0.02,
            'volatility': np.random.uniform(0.01, 0.05, 300)
        })
        y = pd.Series((X['return_1d'] > 0).astype(int))
        
        predictor = TradingPredictor(strategy='momentum')
        predictor.train(X, y)
        
        return predictor, X, y
    
    def test_accuracy_reasonable(self, trained_predictor):
        """Test that model achieves reasonable accuracy."""
        predictor, X, y = trained_predictor
        
        from sklearn.metrics import accuracy_score
        preds = predictor.predict(X)
        accuracy = accuracy_score(y, preds)
        
        # Should be better than random (50%)
        assert accuracy > 0.4
    
    def test_probability_output(self, trained_predictor):
        """Test that probabilities are in valid range."""
        predictor, X, y = trained_predictor
        
        probs = predictor.predict_probabilities(X)
        
        # Probabilities should be in [0, 1]
        assert (probs['up'] >= 0).all()
        assert (probs['up'] <= 1).all()
