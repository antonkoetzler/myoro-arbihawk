"""
Tests for trade signal engine.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


class TestTradeSignalEngine:
    """Tests for TradeSignalEngine class."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.get_price_history.return_value = pd.DataFrame({
            'symbol': ['AAPL'],
            'asset_type': ['stock'],
            'close': [150.0],
            'high': [152.0],
            'low': [148.0],
            'open': [149.0],
            'volume': [1000000],
            'timestamp': ['2024-01-01']
        })
        return db
    
    @pytest.fixture
    def mock_predictor(self):
        """Create mock predictor."""
        predictor = Mock()
        predictor.predict_probabilities.return_value = pd.DataFrame({'up': [0.75]})
        predictor.is_trained = True
        return predictor
    
    @pytest.fixture
    def engine(self, mock_db, mock_predictor):
        """Create TradeSignalEngine instance."""
        with patch('engine.trade_signal.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                'watchlist': {'stocks': ['AAPL'], 'crypto': ['BTC-USD']},
                'strategies': {
                    'momentum': {'min_confidence': 0.6, 'min_risk_reward': 2.0},
                    'swing': {'min_confidence': 0.65, 'min_risk_reward': 2.0},
                    'volatility': {'min_confidence': 0.65, 'min_risk_reward': 2.0}
                }
            }
            from engine.trade_signal import TradeSignalEngine
            return TradeSignalEngine(
                db=mock_db,
                momentum_predictor=mock_predictor,
                swing_predictor=mock_predictor,
                volatility_predictor=mock_predictor
            )
    
    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine is not None
        assert engine.momentum_predictor is not None
    
    def test_calculate_risk_reward(self, engine):
        """Test risk/reward calculation."""
        rr = engine.calculate_risk_reward(
            entry=100.0,
            stop_loss=96.0,
            take_profit=112.0,
            direction='long'
        )
        
        # Risk is 4, reward is 12, so R:R is 3:1
        assert rr == pytest.approx(3.0)
    
    def test_calculate_risk_reward_short(self, engine):
        """Test risk/reward calculation for short."""
        rr = engine.calculate_risk_reward(
            entry=100.0,
            stop_loss=104.0,
            take_profit=88.0,
            direction='short'
        )
        
        # Risk is 4, reward is 12, so R:R is 3:1
        assert rr == pytest.approx(3.0)
    
    def test_calculate_risk_reward_zero_risk(self, engine):
        """Test risk/reward with zero risk."""
        rr = engine.calculate_risk_reward(
            entry=100.0,
            stop_loss=100.0,  # Same as entry
            take_profit=110.0,
            direction='long'
        )
        
        assert rr == 0.0
    
    def test_calculate_ev(self, engine):
        """Test expected value calculation."""
        ev = engine.calculate_ev(
            probability=0.6,
            expected_return=0.10,  # 10%
            risk=0.05  # 5%
        )
        
        # EV = 0.6 * 0.10 - 0.4 * 0.05 = 0.06 - 0.02 = 0.04
        assert ev == pytest.approx(0.04)
    
    def test_find_momentum_signals_returns_dataframe(self, engine):
        """Test momentum signals returns DataFrame."""
        with patch.object(engine.feature_engineer, 'compute_features_for_symbol') as mock_features:
            mock_features.return_value = {
                'rsi': 45.0,
                'macd': 1.5,
                'atr': 3.0,
                'return_20d': 0.05
            }
            
            signals = engine.find_momentum_signals(symbols=['AAPL'])
            
            assert isinstance(signals, pd.DataFrame)
    
    def test_find_all_signals_returns_dataframe(self, engine):
        """Test all signals returns DataFrame."""
        with patch.object(engine, 'find_momentum_signals') as mock_mom:
            with patch.object(engine, 'find_swing_signals') as mock_swing:
                with patch.object(engine, 'find_volatility_signals') as mock_vol:
                    mock_mom.return_value = pd.DataFrame()
                    mock_swing.return_value = pd.DataFrame()
                    mock_vol.return_value = pd.DataFrame()
                    
                    signals = engine.find_all_signals()
                    
                    assert isinstance(signals, pd.DataFrame)
    
    def test_no_predictor_returns_empty(self, mock_db):
        """Test that missing predictor returns empty DataFrame."""
        with patch('engine.trade_signal.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                'watchlist': {'stocks': ['AAPL'], 'crypto': []},
                'strategies': {}
            }
            from engine.trade_signal import TradeSignalEngine
            
            engine = TradeSignalEngine(
                db=mock_db,
                momentum_predictor=None,
                swing_predictor=None,
                volatility_predictor=None
            )
            
            signals = engine.find_momentum_signals()
            
            assert isinstance(signals, pd.DataFrame)
            assert signals.empty


class TestSignalCalculations:
    """Test signal calculation utilities."""
    
    @pytest.fixture
    def engine(self):
        """Create basic engine for calculation tests."""
        mock_db = Mock()
        with patch('engine.trade_signal.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                'watchlist': {'stocks': [], 'crypto': []},
                'strategies': {}
            }
            from engine.trade_signal import TradeSignalEngine
            return TradeSignalEngine(db=mock_db)
    
    def test_ev_positive_when_good_odds(self, engine):
        """Test EV is positive when probability favors reward."""
        ev = engine.calculate_ev(
            probability=0.7,
            expected_return=0.10,
            risk=0.05
        )
        assert ev > 0
    
    def test_ev_negative_when_bad_odds(self, engine):
        """Test EV is negative when probability doesn't favor reward."""
        ev = engine.calculate_ev(
            probability=0.3,
            expected_return=0.05,
            risk=0.10
        )
        assert ev < 0
    
    def test_risk_reward_long_profit(self, engine):
        """Test risk/reward for profitable long."""
        rr = engine.calculate_risk_reward(
            entry=100.0,
            stop_loss=95.0,
            take_profit=115.0,
            direction='long'
        )
        # Risk: 5, Reward: 15, R:R = 3.0
        assert rr == pytest.approx(3.0)
    
    def test_risk_reward_short_profit(self, engine):
        """Test risk/reward for profitable short."""
        rr = engine.calculate_risk_reward(
            entry=100.0,
            stop_loss=105.0,
            take_profit=85.0,
            direction='short'
        )
        # Risk: 5, Reward: 15, R:R = 3.0
        assert rr == pytest.approx(3.0)
