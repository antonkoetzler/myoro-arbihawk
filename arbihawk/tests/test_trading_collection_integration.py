"""
Integration tests for trading data collection.

Tests the full collection cycle, scheduler integration, and domain separation.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import threading
import time

from data.database import Database
from data.stock_ingestion import StockIngestionService
from data.crypto_ingestion import CryptoIngestionService
from automation.scheduler import AutomationScheduler
import config


class TestTradingCollectionIntegration:
    """Integration tests for trading collection."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path=str(db_path))
            yield db
    
    @pytest.fixture
    def mock_config(self, temp_db):
        """Create mock config for testing."""
        with patch('config.TRADING_CONFIG', {
            "enabled": True,
            "watchlist": {
                "stocks": ["AAPL"],
                "crypto": ["BTC"]
            },
            "api_keys": {
                "alpha_vantage": "",  # No key - force fallback
                "coingecko": ""
            },
            "rate_limiting": {
                "alpha_vantage_calls_per_min": 5,
                "alpha_vantage_calls_per_day": 25,
                "coingecko_calls_per_min": 30
            },
            "scraping_fallback": {"enabled": True},
            "historical_backfill_days": 30
        }):
            yield
    
    def test_scheduler_has_trading_methods(self, temp_db):
        """Test that scheduler has trading collection methods."""
        scheduler = AutomationScheduler(db=temp_db)
        
        assert hasattr(scheduler, 'run_trading_collection')
        assert hasattr(scheduler, 'trigger_trading_collection')
        assert callable(scheduler.run_trading_collection)
        assert callable(scheduler.trigger_trading_collection)
    
    def test_scheduler_status_includes_trading(self, temp_db):
        """Test that scheduler status includes trading info."""
        scheduler = AutomationScheduler(db=temp_db)
        status = scheduler.get_status()
        
        assert "last_trading_collection" in status
        assert "last_trading_collection_duration_seconds" in status
    
    def test_trading_collection_disabled(self, temp_db):
        """Test trading collection when disabled in config."""
        with patch('config.TRADING_CONFIG', {"enabled": False}):
            scheduler = AutomationScheduler(db=temp_db)
            result = scheduler.run_trading_collection()
            
            assert result["success"] is True
            assert result.get("skipped") is True
            assert result.get("reason") == "Trading disabled"
    
    def test_trading_collection_with_mocked_services(self, temp_db):
        """Test trading collection with mocked ingestion services."""
        with patch('config.TRADING_CONFIG', {
            "enabled": True,
            "watchlist": {
                "stocks": ["AAPL"],
                "crypto": ["BTC"]
            },
            "api_keys": {"alpha_vantage": "", "coingecko": ""},
            "rate_limiting": {},
            "scraping_fallback": {"enabled": True},
            "historical_backfill_days": 30
        }):
            scheduler = AutomationScheduler(db=temp_db)
            
            # Mock the services
            with patch.object(scheduler, '_get_stock_service') as mock_stock:
                with patch.object(scheduler, '_get_crypto_service') as mock_crypto:
                    mock_stock_service = MagicMock()
                    mock_crypto_service = MagicMock()
                    
                    mock_stock_service.collect_all.return_value = {
                        "collected": 1,
                        "failed": 0,
                        "total_prices": 100,
                        "errors": []
                    }
                    mock_crypto_service.collect_all.return_value = {
                        "collected": 1,
                        "failed": 0,
                        "total_prices": 50,
                        "errors": []
                    }
                    
                    mock_stock.return_value = mock_stock_service
                    mock_crypto.return_value = mock_crypto_service
                    
                    result = scheduler.run_trading_collection()
                    
                    assert result["success"] is True
                    assert result["stocks"]["collected"] == 1
                    assert result["crypto"]["collected"] == 1
    
    def test_trigger_trading_collection_background(self, temp_db):
        """Test that trigger_trading_collection runs in background."""
        with patch('config.TRADING_CONFIG', {"enabled": False}):
            scheduler = AutomationScheduler(db=temp_db)
            
            result = scheduler.trigger_trading_collection()
            
            assert result["success"] is True
            assert "background" in result.get("message", "").lower()
            # Allow background thread to finish so temp_db teardown can delete the file (Windows)
            time.sleep(0.5)
    
    def test_trigger_trading_collection_busy(self, temp_db):
        """Test trigger_trading_collection when another trading task is running."""
        scheduler = AutomationScheduler(db=temp_db)
        scheduler._current_task = "trading_collection"  # Trading task running
        
        result = scheduler.trigger_trading_collection()
        
        assert result["success"] is False
        assert "already running" in result.get("error", "").lower()

    def test_run_full_with_betting_early_return_finally_no_crash(self, temp_db):
        """Test that run_full_with_betting finally block does not crash on early return (run_result defined)."""
        scheduler = AutomationScheduler(db=temp_db)
        scheduler._stop_task_event.clear()

        def stop_after_collection():
            scheduler._stop_task_event.set()
            return {"success": True, "records": 0}

        with patch.object(scheduler, 'run_collection', side_effect=stop_after_collection):
            result = scheduler.run_full_with_betting()

        assert result is not None
        assert result.get("stopped") is True
        assert "collection" in result
        assert "training" in result
        assert result["training"].get("skipped") is True
        assert "betting" in result
        assert result["betting"].get("skipped") is True
        assert "duration_seconds" in result


class TestDomainSeparation:
    """Tests for domain separation between betting and trading."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path=str(db_path))
            yield db
    
    def test_separate_tables_for_trading(self, temp_db):
        """Test that trading data is stored in separate tables."""
        # Insert stock data
        temp_db.insert_stock({
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "sector": "Technology"
        })
        
        # Insert crypto data
        temp_db.insert_crypto({
            "symbol": "BTC",
            "name": "Bitcoin"
        })
        
        # Verify separate retrieval
        stocks = temp_db.get_stocks()
        cryptos = temp_db.get_crypto()
        
        assert len(stocks) == 1
        assert len(cryptos) == 1
        assert stocks.iloc[0]["symbol"] == "AAPL"
        assert cryptos.iloc[0]["symbol"] == "BTC"
    
    def test_price_history_asset_type_separation(self, temp_db):
        """Test that price history separates by asset type."""
        # Insert stock price
        temp_db.insert_price_history("AAPL", "stock", {
            "timestamp": "2024-01-01",
            "open": 150, "high": 152, "low": 149, "close": 151, "volume": 1000000
        })
        
        # Insert crypto price
        temp_db.insert_price_history("BTC", "crypto", {
            "timestamp": "2024-01-01",
            "open": 45000, "high": 46000, "low": 44000, "close": 45500, "volume": 1000000000
        })
        
        # Verify separation by asset type
        stock_prices = temp_db.get_price_history(asset_type="stock")
        crypto_prices = temp_db.get_price_history(asset_type="crypto")
        
        assert len(stock_prices) == 1
        assert len(crypto_prices) == 1
        assert stock_prices.iloc[0]["symbol"] == "AAPL"
        assert crypto_prices.iloc[0]["symbol"] == "BTC"


class TestLoggingDomainSeparation:
    """Tests for logging domain separation."""
    
    def test_trading_log_prefix(self):
        """Test that trading logs include [TRADING] prefix."""
        logs = []
        
        def log_callback(level, message):
            logs.append({"level": level, "message": message})
        
        with patch('data.stock_ingestion.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                "enabled": True,
                "watchlist": {"stocks": []},
                "api_keys": {"alpha_vantage": ""},
                "rate_limiting": {},
                "scraping_fallback": {"enabled": True},
                "historical_backfill_days": 365
            }
            mock_config.DATA_DIR = Path("/tmp")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                db = Database(db_path=str(Path(tmpdir) / "test.db"))
                service = StockIngestionService(db=db, log_callback=log_callback)
                
                # Trigger a log message
                service._log("info", "Test message")
                
                assert len(logs) == 1
                assert "[STOCKS]" in logs[0]["message"]
    
    def test_crypto_log_prefix(self):
        """Test that crypto logs include [CRYPTO] prefix."""
        logs = []
        
        def log_callback(level, message):
            logs.append({"level": level, "message": message})
        
        with patch('data.crypto_ingestion.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                "enabled": True,
                "watchlist": {"crypto": []},
                "api_keys": {"coingecko": ""},
                "rate_limiting": {},
                "historical_backfill_days": 365
            }
            mock_config.DATA_DIR = Path("/tmp")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                db = Database(db_path=str(Path(tmpdir) / "test.db"))
                service = CryptoIngestionService(db=db, log_callback=log_callback)
                
                # Trigger a log message
                service._log("info", "Test message")
                
                assert len(logs) == 1
                assert "[CRYPTO]" in logs[0]["message"]


class TestConfigurationValidation:
    """Tests for configuration validation."""
    
    def test_trading_config_loaded(self):
        """Test that TRADING_CONFIG is loaded from config module."""
        assert hasattr(config, 'TRADING_CONFIG')
        assert isinstance(config.TRADING_CONFIG, dict)
    
    def test_trading_config_has_required_keys(self):
        """Test that TRADING_CONFIG has required keys."""
        trading_config = config.TRADING_CONFIG
        
        assert "enabled" in trading_config
        assert "watchlist" in trading_config
        assert "api_keys" in trading_config
        assert "rate_limiting" in trading_config
        assert "scraping_fallback" in trading_config
    
    def test_watchlist_structure(self):
        """Test watchlist has stocks and crypto lists."""
        watchlist = config.TRADING_CONFIG.get("watchlist", {})
        
        assert "stocks" in watchlist
        assert "crypto" in watchlist
        assert isinstance(watchlist["stocks"], list)
        assert isinstance(watchlist["crypto"], list)


class TestErrorHandling:
    """Tests for error handling in trading collection."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path=str(db_path))
            yield db
    
    def test_collection_continues_on_partial_failure(self, temp_db):
        """Test that collection continues even if some symbols fail (partial success)."""
        with patch('config.TRADING_CONFIG', {
            "enabled": True,
            "watchlist": {
                "stocks": ["VALID", "INVALID"],
                "crypto": []
            },
            "api_keys": {"alpha_vantage": ""},
            "rate_limiting": {},
            "scraping_fallback": {"enabled": True},
            "historical_backfill_days": 30
        }):
            scheduler = AutomationScheduler(db=temp_db)
            
            # Scheduler uses ingestion_service.ingest_from_subprocess, not stock service
            with patch.object(scheduler, '_get_ingestion_service') as mock_get_ingestion:
                mock_ingestion = MagicMock()
                mock_ingestion.ingest_from_subprocess.return_value = {
                    "success": True,
                    "records": 300,
                    "error": None
                }
                mock_get_ingestion.return_value = mock_ingestion
                
                result = scheduler.run_trading_collection()
                
                # Partial success (1+ symbol collected) should still be success
                assert result["success"] is True
                assert result["stocks"]["collected"] == 1
                assert result["stocks"]["failed"] == 1
    
    def test_collection_handles_service_exception(self, temp_db):
        """Test that collection handles service exceptions gracefully."""
        with patch('config.TRADING_CONFIG', {
            "enabled": True,
            "watchlist": {"stocks": ["AAPL"], "crypto": []},
            "api_keys": {},
            "rate_limiting": {},
            "scraping_fallback": {"enabled": True},
            "historical_backfill_days": 30
        }):
            scheduler = AutomationScheduler(db=temp_db)
            
            with patch.object(scheduler, '_get_stock_service') as mock_stock:
                mock_service = MagicMock()
                mock_service.collect_all.side_effect = Exception("Test exception")
                mock_stock.return_value = mock_service
                
                result = scheduler.run_trading_collection()
                
                # Should handle exception gracefully
                assert "errors" in result
