"""
Tests for crypto data ingestion service.

Tests CoinGecko API integration, rate limiting, and database storage.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from data.database import Database
from data.crypto_ingestion import CryptoIngestionService, CryptoRateLimiter, COINGECKO_ID_MAP


class TestCryptoRateLimiter:
    """Tests for the CryptoRateLimiter class."""
    
    def test_init(self):
        """Test rate limiter initialization."""
        limiter = CryptoRateLimiter(calls_per_min=30)
        assert limiter.calls_per_min == 30
        assert limiter.can_call() is True
    
    def test_record_call(self):
        """Test recording API calls."""
        limiter = CryptoRateLimiter(calls_per_min=30)
        
        limiter.record_call()
        status = limiter.get_status()
        
        assert status["calls_this_minute"] == 1
        assert status["can_call"] is True
    
    def test_minute_limit(self):
        """Test minute rate limit enforcement."""
        limiter = CryptoRateLimiter(calls_per_min=2)
        
        limiter.record_call()
        limiter.record_call()
        
        assert limiter.can_call() is False
    
    def test_get_status(self):
        """Test rate limit status retrieval."""
        limiter = CryptoRateLimiter(calls_per_min=30)
        limiter.record_call()
        
        status = limiter.get_status()
        
        assert "calls_this_minute" in status
        assert "minute_limit" in status
        assert "can_call" in status


class TestCoinGeckoIdMap:
    """Tests for CoinGecko ID mapping."""
    
    def test_common_symbols_mapped(self):
        """Test that common crypto symbols are mapped."""
        assert "BTC" in COINGECKO_ID_MAP
        assert "ETH" in COINGECKO_ID_MAP
        assert "BNB" in COINGECKO_ID_MAP
        assert "SOL" in COINGECKO_ID_MAP
        assert "ADA" in COINGECKO_ID_MAP
    
    def test_btc_mapping(self):
        """Test BTC mapping."""
        assert COINGECKO_ID_MAP["BTC"] == "bitcoin"
    
    def test_eth_mapping(self):
        """Test ETH mapping."""
        assert COINGECKO_ID_MAP["ETH"] == "ethereum"


class TestCryptoIngestionService:
    """Tests for the CryptoIngestionService class."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path=str(db_path))
            yield db
    
    @pytest.fixture
    def service(self, temp_db):
        """Create a CryptoIngestionService instance for testing."""
        with patch('data.crypto_ingestion.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                "enabled": True,
                "watchlist": {"crypto": ["BTC", "ETH"]},
                "api_keys": {"coingecko": ""},
                "rate_limiting": {"coingecko_calls_per_min": 30},
                "historical_backfill_days": 365
            }
            mock_config.DATA_DIR = Path(temp_db.db_path).parent
            
            service = CryptoIngestionService(db=temp_db)
            yield service
    
    def test_init(self, service):
        """Test service initialization."""
        assert service.watchlist == ["BTC", "ETH"]
        assert service.backfill_days == 365
    
    def test_get_coingecko_id_valid(self, service):
        """Test CoinGecko ID lookup for valid symbol."""
        assert service._get_coingecko_id("BTC") == "bitcoin"
        assert service._get_coingecko_id("ETH") == "ethereum"
        assert service._get_coingecko_id("btc") == "bitcoin"  # Case insensitive
    
    def test_get_coingecko_id_invalid(self, service):
        """Test CoinGecko ID lookup for invalid symbol."""
        assert service._get_coingecko_id("INVALID") is None
    
    def test_ingest_to_database(self, service, temp_db):
        """Test database ingestion."""
        crypto_data = {
            "symbol": "BTC",
            "prices": [
                {"timestamp": "2024-01-01", "open": 45000, "high": 46000, "low": 44000, "close": 45500, "volume": 1000000000},
                {"timestamp": "2024-01-02", "open": 45500, "high": 47000, "low": 45000, "close": 46500, "volume": 1100000000}
            ],
            "metadata": {
                "name": "Bitcoin",
                "market_cap": 900000000000
            }
        }
        
        result = service.ingest_to_database(crypto_data)
        
        assert result["metadata_updated"] is True
        assert result["prices_ingested"] == 2
        assert len(result["errors"]) == 0
        
        # Verify database
        cryptos = temp_db.get_crypto(symbol="BTC")
        assert len(cryptos) == 1
        assert cryptos.iloc[0]["name"] == "Bitcoin"
        
        prices = temp_db.get_price_history(symbol="BTC", asset_type="crypto")
        assert len(prices) == 2
    
    @patch('data.crypto_ingestion.requests.Session')
    def test_fetch_price_history_success(self, mock_session_class, service):
        """Test successful price history fetch."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "prices": [
                [1704067200000, 45000.0],  # 2024-01-01
                [1704153600000, 46000.0]   # 2024-01-02
            ],
            "total_volumes": [
                [1704067200000, 1000000000],
                [1704153600000, 1100000000]
            ]
        }
        mock_session.get.return_value = mock_response
        service.session = mock_session
        
        result = service.fetch_price_history("BTC", days=30)
        
        assert result is not None
        assert "prices" in result
    
    @patch('data.crypto_ingestion.requests.Session')
    def test_fetch_price_history_rate_limited(self, mock_session_class, service):
        """Test price history fetch when rate limited."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_session.get.return_value = mock_response
        service.session = mock_session
        
        # Fill up rate limiter
        for _ in range(100):
            service.rate_limiter.record_call()
        
        result = service.fetch_price_history("BTC", days=30)
        
        # Should return None due to rate limit
        assert result is None
    
    def test_collect_symbol_invalid_symbol(self, service):
        """Test collecting an invalid symbol."""
        result = service.collect_symbol("INVALID_SYMBOL_XYZ")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_collect_all_empty_watchlist(self, temp_db):
        """Test collect_all with empty watchlist."""
        with patch('data.crypto_ingestion.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                "enabled": True,
                "watchlist": {"crypto": []},
                "api_keys": {"coingecko": ""},
                "rate_limiting": {},
                "historical_backfill_days": 365
            }
            mock_config.DATA_DIR = Path(temp_db.db_path).parent
            
            service = CryptoIngestionService(db=temp_db)
            result = service.collect_all()
            
            assert result["success"] is True
            assert result["collected"] == 0
    
    def test_get_rate_limit_status(self, service):
        """Test rate limit status retrieval."""
        status = service.get_rate_limit_status()
        
        assert "calls_this_minute" in status
        assert "can_call" in status


class TestCryptoIngestionIntegration:
    """Integration tests for crypto ingestion."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path=str(db_path))
            yield db
    
    def test_parse_market_chart_data(self, temp_db):
        """Test parsing CoinGecko market chart response."""
        with patch('data.crypto_ingestion.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                "enabled": True,
                "watchlist": {"crypto": ["BTC"]},
                "api_keys": {"coingecko": ""},
                "rate_limiting": {},
                "historical_backfill_days": 365
            }
            mock_config.DATA_DIR = Path(temp_db.db_path).parent
            
            service = CryptoIngestionService(db=temp_db)
            
            # Mock CoinGecko response
            api_data = {
                "prices": [
                    [1704067200000, 45000.0],
                    [1704153600000, 46000.0]
                ],
                "total_volumes": [
                    [1704067200000, 1000000000],
                    [1704153600000, 1100000000]
                ]
            }
            
            coin_info = {
                "name": "Bitcoin",
                "market_data": {
                    "market_cap": {"usd": 900000000000}
                }
            }
            
            result = service._parse_market_chart_data("BTC", api_data, coin_info)
            
            assert result["symbol"] == "BTC"
            assert len(result["prices"]) == 2
            assert result["metadata"]["name"] == "Bitcoin"
            assert result["source"] == "coingecko"
    
    def test_full_ingestion_with_mocked_api(self, temp_db):
        """Test full ingestion flow with mocked API."""
        with patch('data.crypto_ingestion.config') as mock_config:
            mock_config.TRADING_CONFIG = {
                "enabled": True,
                "watchlist": {"crypto": ["BTC"]},
                "api_keys": {"coingecko": ""},
                "rate_limiting": {"coingecko_calls_per_min": 30},
                "historical_backfill_days": 30
            }
            mock_config.DATA_DIR = Path(temp_db.db_path).parent
            
            service = CryptoIngestionService(db=temp_db)
            
            # Mock fetch_crypto_data
            with patch.object(service, 'fetch_crypto_data') as mock_fetch:
                mock_fetch.return_value = {
                    "symbol": "BTC",
                    "prices": [
                        {"timestamp": "2024-01-01", "open": 45000, "high": 46000, "low": 44000, "close": 45500, "volume": 1000000000}
                    ],
                    "metadata": {"name": "Bitcoin", "market_cap": 900000000000},
                    "source": "coingecko"
                }
                
                result = service.collect_all()
                
                assert result["collected"] == 1
                assert result["total_prices"] >= 1
                
                # Verify in database
                cryptos = temp_db.get_crypto()
                assert len(cryptos) == 1
