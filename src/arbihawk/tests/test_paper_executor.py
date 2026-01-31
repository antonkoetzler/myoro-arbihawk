"""
Tests for paper trading executor.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


class TestPaperTradingExecutor:
    """Tests for PaperTradingExecutor class."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.insert_trade.return_value = 1
        db.open_position.return_value = 1
        db.close_position.return_value = True
        db.update_position_price.return_value = True
        db.get_positions.return_value = pd.DataFrame()
        return db
    
    @pytest.fixture
    def mock_portfolio_manager(self):
        """Create mock portfolio manager."""
        pm = Mock()
        pm.get_balance.return_value = 10000.0
        pm.get_available_cash.return_value = 8500.0
        pm.get_portfolio_value.return_value = 10000.0
        pm.max_position_size = 0.05
        pm.can_open_position.return_value = (True, "OK")
        pm.update_cash_balance = Mock()
        pm.invalidate_cache = Mock()
        pm.get_position.return_value = {
            'id': 1,
            'symbol': 'AAPL',
            'quantity': 10,
            'entry_price': 150.0,
            'current_price': 155.0,
            'direction': 'long'
        }
        return pm
    
    @pytest.fixture
    def executor(self, mock_db, mock_portfolio_manager):
        """Create PaperTradingExecutor instance."""
        from trading.execution import PaperTradingExecutor
        return PaperTradingExecutor(mock_db, mock_portfolio_manager)
    
    def test_initialization(self, executor):
        """Test executor initialization."""
        assert hasattr(executor, 'slippage_min')
        assert hasattr(executor, 'slippage_max')
    
    def test_execute_market_order_buy(self, executor, mock_db, mock_portfolio_manager):
        """Test executing market buy order."""
        result = executor.execute_market_order(
            symbol='AAPL',
            direction='long',
            quantity=10,
            price=150.0,
            asset_type='stock',
            strategy='momentum',
            stop_loss=145.0,
            take_profit=165.0
        )
        
        assert result['status'] == 'filled'
        assert result['symbol'] == 'AAPL'
        mock_portfolio_manager.update_cash_balance.assert_called()
        mock_db.open_position.assert_called()
    
    def test_execute_market_order_rejected(self, executor, mock_portfolio_manager):
        """Test rejected market order."""
        mock_portfolio_manager.can_open_position.return_value = (False, "Insufficient funds")
        
        result = executor.execute_market_order(
            symbol='AAPL',
            direction='long',
            quantity=10,
            price=150.0
        )
        
        assert result['status'] == 'rejected'
        assert "Insufficient funds" in result['reason']
    
    def test_close_position_success(self, executor, mock_db, mock_portfolio_manager):
        """Test closing a position."""
        result = executor.close_position('AAPL', 160.0)
        
        assert result['success'] == True
        assert result['pnl'] > 0  # Profit from 150 to 160
        mock_db.close_position.assert_called()
        mock_db.insert_trade.assert_called()
        mock_portfolio_manager.update_cash_balance.assert_called()
    
    def test_close_position_not_found(self, executor, mock_portfolio_manager):
        """Test closing non-existent position."""
        mock_portfolio_manager.get_position.return_value = None
        
        result = executor.close_position('NONEXISTENT', 100.0)
        
        assert result['success'] == False
    
    def test_close_position_with_loss(self, executor, mock_db, mock_portfolio_manager):
        """Test closing position with loss."""
        mock_portfolio_manager.get_position.return_value = {
            'id': 1,
            'symbol': 'AAPL',
            'quantity': 10,
            'entry_price': 150.0,
            'current_price': 140.0,
            'direction': 'long'
        }
        
        result = executor.close_position('AAPL', 140.0)
        
        assert result['success'] == True
        assert result['pnl'] < 0  # Loss


class TestOrderStatus:
    """Test order status enumeration."""
    
    def test_order_status_values(self):
        """Test OrderStatus enum values."""
        from trading.execution import OrderStatus
        
        assert OrderStatus.PENDING.value == 'pending'
        assert OrderStatus.FILLED.value == 'filled'
        assert OrderStatus.CANCELLED.value == 'cancelled'
        assert OrderStatus.REJECTED.value == 'rejected'
    
    def test_order_type_values(self):
        """Test OrderType enum values."""
        from trading.execution import OrderType
        
        assert OrderType.MARKET.value == 'market'
        assert OrderType.LIMIT.value == 'limit'
        assert OrderType.STOP_LOSS.value == 'stop_loss'
        assert OrderType.TAKE_PROFIT.value == 'take_profit'
