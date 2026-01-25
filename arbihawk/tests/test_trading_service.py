"""
Tests for trading service.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


class TestTradingService:
    """Tests for TradingService class."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.get_price_history.return_value = pd.DataFrame()
        db.get_positions.return_value = pd.DataFrame()
        db.get_trades.return_value = pd.DataFrame()
        db.get_portfolio.return_value = pd.DataFrame({
            'cash_balance': [10000.0],
            'total_value': [10000.0]
        })
        return db
    
    @pytest.fixture
    def service(self, mock_db):
        """Create TradingService instance."""
        with patch('trading.service.PortfolioManager') as mock_pm:
            mock_pm.return_value.get_balance.return_value = 10000.0
            mock_pm.return_value.get_portfolio_value.return_value = 10000.0
            mock_pm.return_value.get_positions.return_value = pd.DataFrame()
            mock_pm.return_value.get_pnl.return_value = {'realized': 0, 'unrealized': 0, 'total': 0}
            mock_pm.return_value.get_performance_metrics.return_value = {'roi': 0}
            mock_pm.return_value.get_performance_by_strategy.return_value = {}
            
            with patch('trading.service.PaperTradingExecutor') as mock_exec:
                mock_exec.return_value.check_stop_loss_take_profit.return_value = []
                mock_exec.return_value.update_position_prices.return_value = None
                
                with patch('trading.service.TradingModelManager') as mock_mm:
                    mock_mm.return_value.get_active_model.return_value = None
                    
                    from trading.service import TradingService
                    return TradingService(mock_db)
    
    def test_initialization(self, service):
        """Test service initialization."""
        assert service is not None
    
    def test_get_portfolio_status(self, service):
        """Test getting portfolio status."""
        status = service.get_portfolio_summary()
        
        assert isinstance(status, dict)
    
    def test_get_performance(self, service):
        """Test getting performance metrics."""
        metrics = service.get_performance()
        
        assert isinstance(metrics, dict)


class TestTradingServiceIntegration:
    """Integration tests for TradingService."""
    
    @pytest.fixture
    def full_service(self):
        """Create service with minimal mocking."""
        mock_db = Mock()
        mock_db.get_price_history.return_value = pd.DataFrame()
        mock_db.get_positions.return_value = pd.DataFrame()
        mock_db.get_trades.return_value = pd.DataFrame()
        mock_db.get_portfolio.return_value = pd.DataFrame({
            'cash_balance': [10000.0],
            'total_value': [10000.0]
        })
        
        with patch('trading.service.TradingModelManager') as mock_mm:
            mock_mm.return_value.get_active_model.return_value = None
            
            from trading.service import TradingService
            return TradingService(mock_db)
    
    def test_full_workflow_no_crash(self, full_service):
        """Test that full workflow doesn't crash."""
        # Get summary
        status = full_service.get_portfolio_summary()
        assert status is not None
        
        # Get performance
        perf = full_service.get_performance()
        assert isinstance(perf, dict)
