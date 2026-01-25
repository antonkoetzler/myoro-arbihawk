"""
Tests for stock data ingestion service.

Tests API integration, yfinance fallback, rate limiting, and database storage.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from data.database import Database
from data.stock_ingestion import StockIngestionService, RateLimiter


class TestRateLimiter:
    """Tests for the RateLimiter class."""
    
    def test_init(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(calls_per_min=5, calls_per_day=25)
        assert limiter.calls_per_min == 5
        assert limiter.calls_per_day == 25
        assert limiter.can_call() is True
    
    def test_record_call(self):
        """Test recording API calls."""
        limiter = RateLimiter(calls_per_min=5, calls_per_day=25)
        
        limiter.record_call()
        status = limiter.get_status()
        
        assert status["calls_this_minute"] == 1
        assert status["calls_today"] == 1
        assert status["can_call"] is True
    
    def test_minute_limit(self):
        """Test minute rate limit enforcement."""
        limiter = RateLimiter(calls_per_min=2, calls_per_day=100)
        
        limiter.record_call()
        limiter.record_call()
        
        assert limiter.can_call() is False
        
        status = limiter.get_status()
        assert status["calls_this_minute"] == 2
    
    def test_day_limit(self):
        """Test daily rate limit enforcement."""
        limiter = RateLimiter(calls_per_min=100, calls_per_day=3)
        
        limiter.record_call()
        limiter.record_call()
        limiter.record_call()
        
        assert limiter.can_call() is False
        
        status = limiter.get_status()
        assert status["calls_today"] == 3
    
    def test_get_status(self):
        """Test rate limit status retrieval."""
        limiter = RateLimiter(calls_per_min=5, calls_per_day=25)
        limiter.record_call()
        
        status = limiter.get_status()
        
        assert "calls_this_minute" in status
        assert "calls_today" in status
        assert "minute_limit" in status
        assert "day_limit" in status
        assert "can_call" in status


class TestStockIngestionService:
    """Tests for the StockIngestionService class."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path=str(db_path))
            yield db
    
    @pytest.fixture
    def service(self, temp_db):
        """Create a StockIngestionService instance for testing."""
        with patch('data.stock_ingestion.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                "enabled": True,
                "watchlist": {"stocks": ["AAPL", "MSFT"]},
                "api_keys": {"alpha_vantage": "test_key"},
                "rate_limiting": {
                    "alpha_vantage_calls_per_min": 5,
                    "alpha_vantage_calls_per_day": 25
                },
                "scraping_fallback": {"enabled": True},
                "historical_backfill_days": 365
            }
            mock_config.DATA_DIR = Path(temp_db.db_path).parent
            
            service = StockIngestionService(db=temp_db)
            yield service
    
    def test_init(self, service):
        """Test service initialization."""
        assert service.api_key == "test_key"
        assert service.watchlist == ["AAPL", "MSFT"]
        assert service.backfill_days == 365
    
    def test_check_api_key_present(self, service):
        """Test API key check when key is present."""
        assert service.check_api_key() is True
    
    def test_check_api_key_missing(self, temp_db):
        """Test API key check when key is missing."""
        with patch('data.stock_ingestion.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                "enabled": True,
                "watchlist": {"stocks": []},
                "api_keys": {"alpha_vantage": ""},
                "rate_limiting": {},
                "scraping_fallback": {"enabled": True},
                "historical_backfill_days": 365
            }
            mock_config.DATA_DIR = Path(temp_db.db_path).parent
            
            service = StockIngestionService(db=temp_db)
            assert service.check_api_key() is False
    
    @patch('data.stock_ingestion.requests_cache', None)
    @patch('data.stock_ingestion.REQUESTS_CACHE_AVAILABLE', False)
    def test_fetch_via_yfinance(self, temp_db):
        """Test yfinance fallback fetching."""
        with patch('data.stock_ingestion.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                "enabled": True,
                "watchlist": {"stocks": ["AAPL"]},
                "api_keys": {"alpha_vantage": ""},
                "rate_limiting": {},
                "scraping_fallback": {"enabled": True},
                "historical_backfill_days": 30
            }
            mock_config.DATA_DIR = Path(temp_db.db_path).parent
            
            service = StockIngestionService(db=temp_db)
            
            # Mock yfinance
            with patch('data.stock_ingestion.yf') as mock_yf:
                mock_ticker = MagicMock()
                mock_yf.Ticker.return_value = mock_ticker
                
                # Create mock history DataFrame
                import pandas as pd
                mock_history = pd.DataFrame({
                    'Open': [150.0, 151.0],
                    'High': [152.0, 153.0],
                    'Low': [149.0, 150.0],
                    'Close': [151.0, 152.0],
                    'Volume': [1000000, 1100000]
                }, index=pd.to_datetime(['2024-01-01', '2024-01-02']))
                
                mock_ticker.history.return_value = mock_history
                mock_ticker.info = {
                    'longName': 'Apple Inc.',
                    'sector': 'Technology',
                    'industry': 'Consumer Electronics',
                    'marketCap': 3000000000000,
                    'exchange': 'NASDAQ'
                }
                
                result = service.fetch_via_yfinance("AAPL", period="1mo")
                
                assert result is not None
                assert result["symbol"] == "AAPL"
                assert len(result["prices"]) == 2
                assert result["source"] == "yfinance"
                assert result["metadata"]["name"] == "Apple Inc."
    
    def test_ingest_to_database(self, service, temp_db):
        """Test database ingestion."""
        stock_data = {
            "symbol": "TEST",
            "prices": [
                {"timestamp": "2024-01-01", "open": 100, "high": 105, "low": 99, "close": 104, "volume": 1000000},
                {"timestamp": "2024-01-02", "open": 104, "high": 106, "low": 103, "close": 105, "volume": 1100000}
            ],
            "metadata": {
                "name": "Test Company",
                "sector": "Technology",
                "industry": "Software",
                "market_cap": 1000000000,
                "exchange": "NYSE"
            }
        }
        
        result = service.ingest_to_database(stock_data)
        
        assert result["metadata_updated"] is True
        assert result["prices_ingested"] == 2
        assert len(result["errors"]) == 0
        
        # Verify database
        stocks = temp_db.get_stocks(symbol="TEST")
        assert len(stocks) == 1
        assert stocks.iloc[0]["name"] == "Test Company"
        
        prices = temp_db.get_price_history(symbol="TEST", asset_type="stock")
        assert len(prices) == 2
    
    def test_collect_symbol_with_fallback(self, service):
        """Test symbol collection with fallback to yfinance."""
        with patch.object(service, 'fetch_stock_data') as mock_fetch:
            mock_fetch.return_value = {
                "symbol": "AAPL",
                "prices": [{"timestamp": "2024-01-01", "open": 150, "high": 152, "low": 149, "close": 151, "volume": 1000000}],
                "metadata": {"name": "Apple Inc."},
                "source": "yfinance"
            }
            
            result = service.collect_symbol("AAPL")
            
            assert result["success"] is True
            assert result["source"] == "yfinance"
            assert result["prices_ingested"] == 1
    
    def test_collect_all_empty_watchlist(self, temp_db):
        """Test collect_all with empty watchlist."""
        with patch('data.stock_ingestion.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                "enabled": True,
                "watchlist": {"stocks": []},
                "api_keys": {"alpha_vantage": "test_key"},
                "rate_limiting": {},
                "scraping_fallback": {"enabled": True},
                "historical_backfill_days": 365
            }
            mock_config.DATA_DIR = Path(temp_db.db_path).parent
            
            service = StockIngestionService(db=temp_db)
            result = service.collect_all()
            
            assert result["success"] is True
            assert result["collected"] == 0
    
    def test_get_rate_limit_status(self, service):
        """Test rate limit status retrieval."""
        status = service.get_rate_limit_status()
        
        assert "calls_this_minute" in status
        assert "calls_today" in status
        assert "can_call" in status


class TestStockIngestionIntegration:
    """Integration tests for stock ingestion."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path=str(db_path))
            yield db
    
    def test_full_ingestion_flow_with_mock_yfinance(self, temp_db):
        """Test full ingestion flow using mocked yfinance."""
        with patch('data.stock_ingestion.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                "enabled": True,
                "watchlist": {"stocks": ["AAPL"]},
                "api_keys": {"alpha_vantage": ""},  # No API key - force fallback
                "rate_limiting": {},
                "scraping_fallback": {"enabled": True},
                "historical_backfill_days": 30
            }
            mock_config.DATA_DIR = Path(temp_db.db_path).parent
            
            with patch('data.stock_ingestion.yf') as mock_yf:
                mock_ticker = MagicMock()
                mock_yf.Ticker.return_value = mock_ticker
                
                import pandas as pd
                mock_history = pd.DataFrame({
                    'Open': [150.0],
                    'High': [152.0],
                    'Low': [149.0],
                    'Close': [151.0],
                    'Volume': [1000000]
                }, index=pd.to_datetime(['2024-01-01']))
                
                mock_ticker.history.return_value = mock_history
                mock_ticker.info = {'longName': 'Apple Inc.'}
                
                service = StockIngestionService(db=temp_db)
                result = service.collect_all()
                
                assert result["collected"] == 1
                assert result["total_prices"] >= 1
                
                # Verify in database
                stocks = temp_db.get_stocks()
                assert len(stocks) == 1
