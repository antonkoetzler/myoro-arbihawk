"""
Integration tests for the trading system.

Tests the full workflow from data ingestion through signal generation to execution.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import os


class TestFeatureToSignalIntegration:
    """Test integration from features to signals."""
    
    @pytest.fixture
    def sample_price_data(self):
        """Create comprehensive price data."""
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=300, freq='D')
        
        # Generate trending price data
        trend = np.linspace(100, 150, 300)
        noise = np.random.randn(300) * 3
        close = trend + noise
        
        high = close + np.abs(np.random.randn(300)) * 2
        low = close - np.abs(np.random.randn(300)) * 2
        open_price = close + np.random.randn(300) * 1
        volume = np.random.randint(1000000, 10000000, 300)
        
        return pd.DataFrame({
            'timestamp': dates.strftime('%Y-%m-%d'),
            'symbol': 'AAPL',
            'asset_type': 'stock',
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    def test_feature_pipeline(self, sample_price_data):
        """Test the full feature pipeline."""
        mock_db = Mock()
        mock_db.get_price_history.return_value = sample_price_data
        
        from data.stock_features import StockFeatureEngineer
        engineer = StockFeatureEngineer(mock_db)
        
        # Compute all features
        df = engineer.compute_indicators(sample_price_data)
        df = engineer.compute_momentum_features(df)
        df = engineer.compute_swing_features(df)
        df = engineer.compute_volatility_features(df)
        
        # Verify all expected columns exist
        expected = ['rsi', 'macd', 'sma_20', 'return_1d', 'rsi_oversold', 
                   'bb_squeeze', 'volatility_20d']
        for col in expected:
            assert col in df.columns, f"Missing: {col}"
    
    def test_model_training_workflow(self, sample_price_data):
        """Test model training on real features."""
        mock_db = Mock()
        mock_db.get_price_history.return_value = sample_price_data
        
        from data.stock_features import StockFeatureEngineer
        from models.trading_predictor import TradingPredictor
        
        engineer = StockFeatureEngineer(mock_db)
        
        # Compute features
        df = engineer.compute_indicators(sample_price_data)
        df = engineer.compute_momentum_features(df)
        
        # Create labels
        df['label'] = (df['close'].shift(-1) > df['close']).astype(int)
        df = df.dropna()
        
        # Get feature columns
        feature_cols = ['rsi', 'macd', 'sma_20', 'sma_50', 'return_1d', 'volatility_20d']
        available_cols = [c for c in feature_cols if c in df.columns]
        
        X = df[available_cols]
        y = pd.Series(df['label'].values)
        
        # Train model
        predictor = TradingPredictor(strategy='momentum')
        predictor.train(X, y)
        
        # Test prediction - returns DataFrame with 'up' column
        probs = predictor.predict_probabilities(X.iloc[-5:])
        assert len(probs) == 5
        assert 'up' in probs.columns
        assert (probs['up'] >= 0).all()
        assert (probs['up'] <= 1).all()


class TestPortfolioExecutionIntegration:
    """Test portfolio management and execution integration."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database with realistic state."""
        db = Mock()
        
        # Portfolio state
        db.get_portfolio.return_value = pd.DataFrame({
            'cash_balance': [10000.0],
            'total_value': [10000.0],
            'realized_pnl': [0.0],
            'unrealized_pnl': [0.0]
        })
        
        # No existing positions
        db.get_positions.return_value = pd.DataFrame()
        
        # No existing trades
        db.get_trades.return_value = pd.DataFrame()
        
        # Mock insert methods
        db.insert_portfolio.return_value = 1
        db.insert_trade.return_value = 1
        db.open_position.return_value = 1
        db.close_position.return_value = True
        db.update_position_price.return_value = True
        
        return db
    
    def test_open_position_flow(self, mock_db):
        """Test opening a position through portfolio and executor."""
        with patch('trading.portfolio_manager.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                'portfolio': {'starting_balance': 10000.0, 'cash_reserve': 0.15},
                'position_sizing': {
                    'strategy': 'fixed',
                    'risk_per_trade': 0.02,
                    'max_position_size': 0.20,  # 20% to allow for test
                    'max_positions': 12,
                    'fixed_size': 500.0
                }
            }
            
            from trading.portfolio_manager import PortfolioManager
            from trading.execution import PaperTradingExecutor
            
            pm = PortfolioManager(mock_db)
            executor = PaperTradingExecutor(mock_db, pm)
            
            # Create signal
            signal = {
                'symbol': 'AAPL',
                'asset_type': 'stock',
                'strategy': 'momentum',
                'direction': 'long',
                'entry_price': 150.0,
                'stop_loss': 145.0,
                'take_profit': 165.0
            }
            
            # Calculate position size
            size = pm.calculate_position_size(signal, 150.0)
            assert size > 0
            
            # Check if can open
            can_open, reason = pm.can_open_position('AAPL', size, 150.0)
            # Should pass since we have plenty of balance
            assert can_open, f"Cannot open: {reason}"
            
            # Execute order
            result = executor.execute_market_order(
                symbol='AAPL',
                direction='long',
                quantity=size,
                price=150.0,
                asset_type='stock',
                strategy='momentum',
                stop_loss=145.0,
                take_profit=165.0
            )
            assert result['status'] == 'filled', f"Order rejected: {result.get('reason')}"
    
    def test_close_position_flow(self, mock_db):
        """Test closing a position through executor."""
        with patch('trading.portfolio_manager.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                'portfolio': {'starting_balance': 10000.0, 'cash_reserve': 0.15},
                'position_sizing': {'strategy': 'risk_based', 'risk_per_trade': 0.02,
                                   'max_position_size': 0.05, 'max_positions': 12}
            }
            
            from trading.portfolio_manager import PortfolioManager
            from trading.execution import PaperTradingExecutor
            
            pm = PortfolioManager(mock_db)
            
            # Setup existing position
            mock_db.get_positions.return_value = pd.DataFrame({
                'id': [1],
                'symbol': ['AAPL'],
                'quantity': [10],
                'entry_price': [150.0],
                'current_price': [160.0],
                'direction': ['long'],
                'stop_loss': [145.0],
                'take_profit': [170.0]
            })
            
            executor = PaperTradingExecutor(mock_db, pm)
            
            # Close position
            result = executor.close_position('AAPL', 160.0)
            
            assert result['success'] == True
            assert result['pnl'] > 0  # Profit


class TestSignalToTradeIntegration:
    """Test signal generation to trade execution."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mocked database."""
        mock_db = Mock()
        mock_db.get_price_history.return_value = pd.DataFrame()
        mock_db.get_positions.return_value = pd.DataFrame()
        mock_db.get_trades.return_value = pd.DataFrame()
        mock_db.get_portfolio.return_value = pd.DataFrame({
            'cash_balance': [10000.0],
            'total_value': [10000.0]
        })
        return mock_db
    
    def test_signal_engine_creation(self, mock_db):
        """Test signal engine can be created."""
        from engine.trade_signal import TradeSignalEngine
        
        engine = TradeSignalEngine(db=mock_db)
        
        assert engine is not None
        assert engine.db is mock_db


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""
    
    def test_complete_trading_day_simulation(self):
        """Simulate a complete trading day."""
        # This test verifies the system doesn't crash during a full day simulation
        np.random.seed(42)
        
        mock_db = Mock()
        
        # Initial state
        mock_db.get_portfolio.return_value = pd.DataFrame({
            'cash_balance': [10000.0],
            'total_value': [10000.0],
            'realized_pnl': [0.0],
            'unrealized_pnl': [0.0]
        })
        mock_db.get_positions.return_value = pd.DataFrame()
        mock_db.get_trades.return_value = pd.DataFrame()
        mock_db.insert_portfolio.return_value = 1
        mock_db.insert_trade.return_value = 1
        mock_db.open_position.return_value = 1
        
        # Generate price data
        dates = pd.date_range(start='2024-01-01', periods=300, freq='D')
        close = 100 + np.cumsum(np.random.randn(300) * 2)
        
        mock_db.get_price_history.return_value = pd.DataFrame({
            'timestamp': dates.strftime('%Y-%m-%d'),
            'symbol': 'AAPL',
            'asset_type': 'stock',
            'open': close + np.random.randn(300),
            'high': close + np.abs(np.random.randn(300)) * 2,
            'low': close - np.abs(np.random.randn(300)) * 2,
            'close': close,
            'volume': np.random.randint(1000000, 10000000, 300)
        })
        
        with patch('trading.service.TradingModelManager') as mock_mm:
            mock_model = Mock()
            mock_model.is_trained = True
            mock_model.predict_probabilities.return_value = pd.DataFrame({'up': [0.6]})
            mock_mm.return_value.get_active_model.return_value = mock_model
            
            from trading.service import TradingService
            
            service = TradingService(mock_db)
            
            # Run trading cycle
            result = service.run_trading_cycle()
            
            assert result is not None
