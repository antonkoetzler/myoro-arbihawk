"""
Tests for portfolio manager.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


class TestPortfolioManager:
    """Tests for PortfolioManager class."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        
        # Default returns
        db.get_portfolio.return_value = pd.DataFrame({
            'cash_balance': [10000.0],
            'total_value': [10000.0],
            'realized_pnl': [0.0],
            'unrealized_pnl': [0.0]
        })
        db.get_positions.return_value = pd.DataFrame()
        db.get_trades.return_value = pd.DataFrame()
        db.insert_portfolio.return_value = 1
        
        return db
    
    @pytest.fixture
    def manager(self, mock_db):
        """Create PortfolioManager instance."""
        with patch('trading.portfolio_manager.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                'portfolio': {
                    'starting_balance': 10000.0,
                    'cash_reserve': 0.15
                },
                'position_sizing': {
                    'strategy': 'risk_based',
                    'risk_per_trade': 0.02,
                    'max_position_size': 0.05,
                    'max_positions': 12,
                    'fixed_size': 500.0
                }
            }
            from trading.portfolio_manager import PortfolioManager
            return PortfolioManager(mock_db)
    
    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager.starting_balance == 10000.0
        assert manager.cash_reserve_ratio == 0.15
        assert manager.max_positions == 12
    
    def test_get_balance(self, manager, mock_db):
        """Test getting balance."""
        balance = manager.get_balance()
        
        assert balance == 10000.0
        mock_db.get_portfolio.assert_called()
    
    def test_get_balance_empty_initializes(self, manager, mock_db):
        """Test that empty portfolio is initialized."""
        mock_db.get_portfolio.return_value = pd.DataFrame()
        
        manager._cash_balance = None  # Reset cache
        
        # Should initialize and return starting balance
        balance = manager.get_balance()
        
        mock_db.insert_portfolio.assert_called()
    
    def test_get_positions(self, manager, mock_db):
        """Test getting positions."""
        mock_db.get_positions.return_value = pd.DataFrame({
            'id': [1, 2],
            'symbol': ['AAPL', 'MSFT'],
            'quantity': [10, 5],
            'entry_price': [150.0, 300.0],
            'current_price': [155.0, 295.0],
            'direction': ['long', 'long']
        })
        
        positions = manager.get_positions()
        
        assert len(positions) == 2
    
    def test_get_position_by_symbol(self, manager, mock_db):
        """Test getting specific position."""
        mock_db.get_positions.return_value = pd.DataFrame({
            'id': [1],
            'symbol': ['AAPL'],
            'quantity': [10],
            'entry_price': [150.0],
            'current_price': [155.0],
            'direction': ['long'],
            'stop_loss': [145.0],
            'take_profit': [165.0],
            'unrealized_pnl': [50.0],
            'asset_type': ['stock'],
            'strategy': ['momentum']
        })
        
        position = manager.get_position('AAPL')
        
        assert position is not None
        assert position['symbol'] == 'AAPL'
        assert position['quantity'] == 10
        assert position['entry_price'] == 150.0
    
    def test_get_position_not_found(self, manager, mock_db):
        """Test getting non-existent position."""
        mock_db.get_positions.return_value = pd.DataFrame()
        
        position = manager.get_position('NONEXISTENT')
        
        assert position is None
    
    def test_get_portfolio_value_no_positions(self, manager, mock_db):
        """Test portfolio value with no positions."""
        value = manager.get_portfolio_value()
        
        assert value == 10000.0
    
    def test_get_portfolio_value_with_positions(self, manager, mock_db):
        """Test portfolio value with positions."""
        mock_db.get_positions.return_value = pd.DataFrame({
            'id': [1],
            'symbol': ['AAPL'],
            'quantity': [10],
            'entry_price': [150.0],
            'current_price': [160.0],
            'direction': ['long']
        })
        
        value = manager.get_portfolio_value()
        
        # 10000 cash + (10 * 160) position value = 11600
        assert value == 11600.0
    
    def test_get_pnl(self, manager, mock_db):
        """Test P&L calculation."""
        mock_db.get_trades.return_value = pd.DataFrame({
            'pnl': [50.0, -20.0, 100.0]
        })
        mock_db.get_positions.return_value = pd.DataFrame({
            'id': [1],
            'symbol': ['AAPL'],
            'quantity': [10],
            'entry_price': [150.0],
            'current_price': [155.0],
            'direction': ['long']
        })
        
        pnl = manager.get_pnl()
        
        assert pnl['realized'] == 130.0  # 50 - 20 + 100
        assert pnl['unrealized'] == 50.0  # (155 - 150) * 10
        assert pnl['total'] == 180.0
    
    def test_get_available_cash(self, manager, mock_db):
        """Test available cash calculation."""
        available = manager.get_available_cash()
        
        # 10000 - (10000 * 0.15) = 8500
        assert available == 8500.0
    
    def test_calculate_position_size_fixed(self, manager):
        """Test fixed position sizing."""
        manager.sizing_strategy = 'fixed'
        manager.fixed_size = 500.0
        
        signal = {'entry_price': 100.0}
        size = manager.calculate_position_size(signal, current_price=100.0)
        
        # Should be $500 worth = 5 shares
        assert size == 5.0
    
    def test_calculate_position_size_percentage(self, manager):
        """Test percentage position sizing."""
        manager.sizing_strategy = 'percentage'
        manager.risk_per_trade = 0.02  # 2%
        
        signal = {'entry_price': 100.0}
        size = manager.calculate_position_size(signal, current_price=100.0)
        
        # 2% of $10000 = $200, $200 / $100 = 2 shares
        assert size == 2.0
    
    def test_calculate_position_size_risk_based(self, manager):
        """Test risk-based position sizing."""
        manager.sizing_strategy = 'risk_based'
        manager.risk_per_trade = 0.02  # 2%
        
        signal = {
            'entry_price': 100.0,
            'stop_loss': 95.0  # $5 risk per share
        }
        size = manager.calculate_position_size(signal, current_price=100.0)
        
        # Risk amount = 2% of $10000 = $200
        # $5 risk per share, so $200 / $5 = 40 shares max
        # But max position size is 5% = $500, so $500 / $100 = 5 shares
        assert size <= 5.0
    
    def test_calculate_position_size_max_positions_reached(self, manager, mock_db):
        """Test that position size is 0 when max positions reached."""
        mock_db.get_positions.return_value = pd.DataFrame({
            'id': list(range(12)),
            'symbol': [f'SYM{i}' for i in range(12)],
            'quantity': [10] * 12,
            'entry_price': [100.0] * 12,
            'current_price': [100.0] * 12,
            'direction': ['long'] * 12
        })
        
        size = manager.calculate_position_size({}, current_price=100.0)
        
        assert size == 0.0
    
    def test_can_open_position_success(self, manager, mock_db):
        """Test successful position opening check."""
        mock_db.get_positions.return_value = pd.DataFrame()
        
        can_open, reason = manager.can_open_position('AAPL', 5, 100.0)
        
        assert can_open == True
        assert reason == "OK"
    
    def test_can_open_position_existing(self, manager, mock_db):
        """Test rejection due to existing position."""
        mock_db.get_positions.return_value = pd.DataFrame({
            'id': [1],
            'symbol': ['AAPL'],
            'quantity': [10],
            'entry_price': [150.0]
        })
        
        can_open, reason = manager.can_open_position('AAPL', 5, 100.0)
        
        assert can_open == False
        assert "Already have" in reason
    
    def test_can_open_position_insufficient_funds(self, manager, mock_db):
        """Test rejection due to insufficient funds."""
        mock_db.get_positions.return_value = pd.DataFrame()
        
        can_open, reason = manager.can_open_position('AAPL', 1000, 100.0)
        
        assert can_open == False
        assert "Insufficient funds" in reason
    
    def test_can_open_position_too_large(self, manager, mock_db):
        """Test rejection due to position too large."""
        mock_db.get_positions.return_value = pd.DataFrame()
        manager.max_position_size = 0.01  # 1%
        
        can_open, reason = manager.can_open_position('AAPL', 10, 150.0)
        
        assert can_open == False
        assert "too large" in reason
    
    def test_update_cash_balance(self, manager, mock_db):
        """Test updating cash balance."""
        manager._cash_balance = 10000.0
        
        manager.update_cash_balance(-500.0)
        
        assert manager._cash_balance == 9500.0
        mock_db.insert_portfolio.assert_called()
    
    def test_update_cash_balance_negative_raises(self, manager):
        """Test that negative balance raises error."""
        manager._cash_balance = 100.0
        
        with pytest.raises(ValueError, match="Cannot reduce balance below 0"):
            manager.update_cash_balance(-500.0)
    
    def test_record_portfolio_snapshot(self, manager, mock_db):
        """Test recording portfolio snapshot."""
        record_id = manager.record_portfolio_snapshot()
        
        mock_db.insert_portfolio.assert_called()
        assert record_id == 1
    
    def test_get_performance_metrics_empty(self, manager, mock_db):
        """Test metrics with no trades."""
        mock_db.get_trades.return_value = pd.DataFrame()
        
        metrics = manager.get_performance_metrics()
        
        assert metrics['total_trades'] == 0
        assert metrics['win_rate'] == 0.0
        assert metrics['roi'] == 0.0
    
    def test_get_performance_metrics_with_trades(self, manager, mock_db):
        """Test metrics with trades."""
        mock_db.get_trades.return_value = pd.DataFrame({
            'pnl': [100.0, -50.0, 200.0, -30.0, 80.0]
        })
        
        metrics = manager.get_performance_metrics()
        
        assert metrics['total_trades'] == 5
        assert metrics['winning_trades'] == 3
        assert metrics['losing_trades'] == 2
        assert metrics['win_rate'] == 0.6
        assert metrics['profit'] == 300.0
    
    def test_get_performance_by_strategy(self, manager, mock_db):
        """Test performance breakdown by strategy."""
        mock_db.get_trades.return_value = pd.DataFrame({
            'strategy': ['momentum', 'momentum', 'swing', 'swing'],
            'pnl': [100.0, -50.0, 200.0, -30.0]
        })
        
        by_strategy = manager.get_performance_by_strategy()
        
        assert 'momentum' in by_strategy
        assert 'swing' in by_strategy
        assert by_strategy['momentum']['total_trades'] == 2
        assert by_strategy['swing']['profit'] == 170.0
    
    def test_invalidate_cache(self, manager):
        """Test cache invalidation."""
        manager._cash_balance = 5000.0
        manager._positions_cache = pd.DataFrame()
        
        manager.invalidate_cache()
        
        assert manager._cash_balance is None
        assert manager._positions_cache is None
