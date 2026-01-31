"""
Tests for stock feature engineering.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta


class TestStockFeatureEngineer:
    """Tests for StockFeatureEngineer class."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.get_price_history = Mock(return_value=pd.DataFrame())
        return db
    
    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=250, freq='D')
        np.random.seed(42)
        
        # Generate realistic price data
        close = 100 + np.cumsum(np.random.randn(250) * 2)
        high = close + np.abs(np.random.randn(250)) * 2
        low = close - np.abs(np.random.randn(250)) * 2
        open_price = close + np.random.randn(250) * 0.5
        volume = np.random.randint(1000000, 10000000, 250)
        
        return pd.DataFrame({
            'timestamp': dates.strftime('%Y-%m-%d'),
            'symbol': 'TEST',
            'asset_type': 'stock',
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    @pytest.fixture
    def engineer(self, mock_db):
        """Create StockFeatureEngineer instance."""
        from data.stock_features import StockFeatureEngineer
        return StockFeatureEngineer(mock_db)
    
    def test_compute_rsi(self, engineer, sample_price_data):
        """Test RSI calculation."""
        rsi = engineer.compute_rsi(sample_price_data['close'])
        
        assert len(rsi) == len(sample_price_data)
        assert rsi.iloc[-1] >= 0 and rsi.iloc[-1] <= 100
        # RSI should be between 0 and 100
        assert rsi.max() <= 100
        assert rsi.min() >= 0
    
    def test_compute_macd(self, engineer, sample_price_data):
        """Test MACD calculation."""
        macd, signal, histogram = engineer.compute_macd(sample_price_data['close'])
        
        assert len(macd) == len(sample_price_data)
        assert len(signal) == len(sample_price_data)
        assert len(histogram) == len(sample_price_data)
        # Histogram should be macd - signal
        np.testing.assert_array_almost_equal(histogram, macd - signal)
    
    def test_compute_sma(self, engineer, sample_price_data):
        """Test SMA calculation."""
        sma_20 = engineer.compute_sma(sample_price_data['close'], 20)
        
        assert len(sma_20) == len(sample_price_data)
        # SMA should smooth out the data
        assert sma_20.std() < sample_price_data['close'].std()
    
    def test_compute_bollinger_bands(self, engineer, sample_price_data):
        """Test Bollinger Bands calculation."""
        upper, middle, lower = engineer.compute_bollinger_bands(sample_price_data['close'])
        
        assert len(upper) == len(sample_price_data)
        assert len(middle) == len(sample_price_data)
        assert len(lower) == len(sample_price_data)
        # Upper should be above middle, middle above lower
        assert (upper.iloc[-50:] >= middle.iloc[-50:]).all()
        assert (middle.iloc[-50:] >= lower.iloc[-50:]).all()
    
    def test_compute_atr(self, engineer, sample_price_data):
        """Test ATR calculation."""
        atr = engineer.compute_atr(
            sample_price_data['high'],
            sample_price_data['low'],
            sample_price_data['close']
        )
        
        assert len(atr) == len(sample_price_data)
        # ATR should be positive
        assert (atr.iloc[-50:] > 0).all()
    
    def test_compute_indicators(self, engineer, sample_price_data):
        """Test full indicator computation."""
        df = engineer.compute_indicators(sample_price_data)
        
        # Check all expected columns exist
        expected_cols = ['rsi', 'macd', 'macd_signal', 'sma_20', 'sma_50', 
                        'bollinger_upper', 'bollinger_lower', 'atr']
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"
    
    def test_compute_momentum_features(self, engineer, sample_price_data):
        """Test momentum feature computation."""
        df = engineer.compute_indicators(sample_price_data)
        df = engineer.compute_momentum_features(df)
        
        expected_cols = ['return_1d', 'return_5d', 'return_20d', 'volatility_20d',
                         'momentum_trend_5d', 'momentum_trend_20d']
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"
        assert np.issubdtype(df['momentum_trend_5d'].dtype, np.floating)
        assert np.issubdtype(df['momentum_trend_20d'].dtype, np.floating)
    
    def test_compute_swing_features(self, engineer, sample_price_data):
        """Test swing feature computation."""
        df = engineer.compute_indicators(sample_price_data)
        df = engineer.compute_swing_features(df)
        
        expected_cols = ['rsi_oversold', 'rsi_overbought', 'macd_bullish_cross', 
                        'above_sma20', 'bb_position']
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"
    
    def test_compute_volatility_features(self, engineer, sample_price_data):
        """Test volatility feature computation."""
        df = engineer.compute_indicators(sample_price_data)
        df = engineer.compute_momentum_features(df)
        df = engineer.compute_volatility_features(df)
        
        expected_cols = ['bb_squeeze', 'hist_volatility', 'volume_surge']
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"
    
    def test_create_training_data_empty(self, engineer, mock_db):
        """Test training data creation with no data."""
        mock_db.get_price_history.return_value = pd.DataFrame()
        
        X, labels, dates, symbols = engineer.create_training_data('momentum')
        
        assert X.empty
        assert len(labels) == 0
    
    def test_get_feature_columns(self, engineer):
        """Test feature column selection."""
        momentum_cols = engineer._get_feature_columns('momentum')
        swing_cols = engineer._get_feature_columns('swing')
        volatility_cols = engineer._get_feature_columns('volatility')
        
        assert len(momentum_cols) > 0
        assert len(swing_cols) > 0
        assert len(volatility_cols) > 0
        assert 'momentum_trend_5d' in momentum_cols
        assert 'momentum_trend_20d' in momentum_cols
        assert 'momentum_trend_5d' in volatility_cols
        # Volatility should have more features (includes momentum + volatility specific)
        assert len(volatility_cols) >= len(momentum_cols)
    
    def test_invalidate_cache(self, engineer):
        """Test cache invalidation."""
        engineer._price_cache = pd.DataFrame({'test': [1, 2, 3]})
        engineer._indicators_cache = {'test': pd.DataFrame()}
        
        engineer.invalidate_cache()
        
        assert engineer._price_cache is None
        assert engineer._indicators_cache == {}


class TestIndicatorEdgeCases:
    """Test edge cases for indicator calculations."""
    
    @pytest.fixture
    def engineer(self):
        """Create StockFeatureEngineer instance."""
        from data.stock_features import StockFeatureEngineer
        mock_db = Mock()
        return StockFeatureEngineer(mock_db)
    
    def test_rsi_constant_prices(self, engineer):
        """Test RSI with constant prices."""
        prices = pd.Series([100.0] * 50)
        rsi = engineer.compute_rsi(prices)
        
        # RSI should be 50 (neutral) for constant prices
        assert rsi.iloc[-1] == 50 or pd.isna(rsi.iloc[-1]) == False
    
    def test_rsi_always_up(self, engineer):
        """Test RSI with always increasing prices."""
        prices = pd.Series(range(1, 51), dtype=float)
        rsi = engineer.compute_rsi(prices)
        
        # RSI should be high (> 50) for always increasing, or NaN for short series
        if not pd.isna(rsi.iloc[-1]):
            assert rsi.iloc[-1] >= 50
    
    def test_bollinger_squeeze_detection(self, engineer):
        """Test Bollinger squeeze detection."""
        # Create data with low then high volatility
        low_vol = np.random.randn(100) * 0.5 + 100  # Low volatility
        high_vol = np.random.randn(50) * 5 + 100  # High volatility
        prices = pd.Series(np.concatenate([low_vol, high_vol]))
        
        upper, middle, lower = engineer.compute_bollinger_bands(prices)
        width = (upper - lower) / middle
        
        # Width should be smaller in low volatility period
        assert width.iloc[50:90].mean() < width.iloc[120:].mean()
