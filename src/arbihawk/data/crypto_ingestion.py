"""
Crypto data ingestion service.

Fetches cryptocurrency price data from CoinGecko API.
Implements rate limiting, caching, and error handling.
"""

import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

try:
    import requests_cache
    REQUESTS_CACHE_AVAILABLE = True
except ImportError:
    REQUESTS_CACHE_AVAILABLE = False

from .database import Database
import config


# CoinGecko symbol to ID mapping (common cryptos)
COINGECKO_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "LTC": "litecoin",
    "ETC": "ethereum-classic",
    "XLM": "stellar",
    "ALGO": "algorand",
    "VET": "vechain",
    "FIL": "filecoin",
    "TRX": "tron"
}


class CryptoRateLimiter:
    """
    Rate limiter for CoinGecko API calls.
    
    CoinGecko free tier: ~10-50 calls/minute (varies).
    We use a conservative 10 calls/min limit to avoid rate limiting.
    """
    
    def __init__(self, calls_per_min: int = 10):
        self.calls_per_min = calls_per_min
        self._calls: List[float] = []
    
    def can_call(self) -> bool:
        """Check if we can make an API call within rate limits."""
        now = time.time()
        self._calls = [t for t in self._calls if now - t < 60]
        return len(self._calls) < self.calls_per_min
    
    def record_call(self) -> None:
        """Record that an API call was made."""
        self._calls.append(time.time())
    
    def wait_if_needed(self) -> float:
        """Wait if rate limited. Returns seconds waited."""
        if self.can_call():
            return 0.0
        
        now = time.time()
        if self._calls:
            oldest = min(self._calls)
            wait_time = 60 - (now - oldest) + 1.0  # Add 1s buffer
            if wait_time > 0:
                time.sleep(wait_time)
                return wait_time
        
        return 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        now = time.time()
        self._calls = [t for t in self._calls if now - t < 60]
        
        return {
            "calls_this_minute": len(self._calls),
            "minute_limit": self.calls_per_min,
            "can_call": self.can_call()
        }


class CryptoIngestionService:
    """
    Service for ingesting cryptocurrency price data.
    
    Uses CoinGecko API (free tier, no API key required).
    Implements rate limiting and caching.
    
    Example usage:
        service = CryptoIngestionService()
        result = service.collect_all()
    """
    
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, db: Optional[Database] = None,
                 log_callback: Optional[Callable[[str, str], None]] = None):
        self.db = db or Database()
        self._log_callback = log_callback
        
        # Load config
        trading_config = config.TRADING_CONFIG
        self.api_key = trading_config.get("api_keys", {}).get("coingecko", "")
        self.watchlist = trading_config.get("watchlist", {}).get("crypto", [])
        self.backfill_days = trading_config.get("historical_backfill_days", 365)
        
        # Rate limiting - use conservative limit to avoid rate limiting
        rate_config = trading_config.get("rate_limiting", {})
        self.rate_limiter = CryptoRateLimiter(
            calls_per_min=rate_config.get("coingecko_calls_per_min", 10)
        )
        
        # Setup session with optional caching
        if REQUESTS_CACHE_AVAILABLE:
            cache_path = Path(config.DATA_DIR) / "cache" / "crypto_api_cache"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.session = requests_cache.CachedSession(
                str(cache_path),
                expire_after=1800,  # 30 min cache (crypto is more volatile)
                allowable_methods=['GET']
            )
        else:
            self.session = requests.Session()
        
        # Set headers
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "Arbihawk Trading Bot"
        })
        
        # Add API key to headers if provided
        if self.api_key:
            self.session.headers["x-cg-demo-api-key"] = self.api_key
    
    def _log(self, level: str, message: str) -> None:
        """Log a message."""
        if self._log_callback:
            self._log_callback(level, f"[CRYPTO] {message}")
        else:
            print(f"[{level.upper()}] [CRYPTO] {message}")
    
    def _get_coingecko_id(self, symbol: str) -> Optional[str]:
        """Get CoinGecko ID for a symbol."""
        return COINGECKO_ID_MAP.get(symbol.upper())
    
    def fetch_price_history(self, symbol: str, days: int = 365) -> Optional[Dict[str, Any]]:
        """
        Fetch price history from CoinGecko API.
        
        Args:
            symbol: Crypto symbol (e.g., "BTC")
            days: Number of days of history (max 365 for free tier with daily granularity)
            
        Returns:
            Dict with price data or None on failure
        """
        coin_id = self._get_coingecko_id(symbol)
        if not coin_id:
            self._log("error", f"Unknown crypto symbol: {symbol}. Supported symbols: {', '.join(sorted(COINGECKO_ID_MAP.keys()))}")
            return None
        
        # Check rate limits
        wait_result = self.rate_limiter.wait_if_needed()
        if wait_result > 0:
            self._log("info", f"Rate limited, waited {wait_result:.1f}s")
        
        # CoinGecko market_chart endpoint
        url = f"{self.COINGECKO_BASE_URL}/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": min(days, 365),  # Max 365 for daily granularity
            "interval": "daily"
        }
        
        # Retry logic with exponential backoff
        max_retries = 5
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                self.rate_limiter.record_call()
                
                if response.status_code == 429:
                    # Rate limited - wait longer and retry
                    delay = min((2 ** attempt) * (2 + attempt), 60)  # Cap at 60s
                    self._log("warning", f"Rate limited for {symbol}, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    # Clear recent calls to reset rate limiter state
                    self.rate_limiter._calls = [t for t in self.rate_limiter._calls if time.time() - t > 60]
                    continue
                
                if response.status_code != 200:
                    self._log("error", f"API error for {symbol}: HTTP {response.status_code}")
                    return None
                
                data = response.json()
                
                if "prices" not in data:
                    self._log("warning", f"No price data for {symbol}")
                    return None
                
                return data
                
            except requests.RequestException as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = (2 ** attempt) * (0.5 + 0.5 * (attempt / max_retries))
                    self._log("warning", f"Request failed for {symbol}: {e}. Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                continue
            except Exception as e:
                self._log("error", f"Unexpected error fetching {symbol}: {e}")
                return None
        
        if last_error:
            self._log("error", f"All {max_retries} attempts failed for {symbol}: {last_error}")
        return None
    
    def fetch_coin_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch coin metadata from CoinGecko API.
        
        Args:
            symbol: Crypto symbol (e.g., "BTC")
            
        Returns:
            Dict with coin info or None on failure
        """
        coin_id = self._get_coingecko_id(symbol)
        if not coin_id:
            return None
        
        # Check rate limits
        wait_result = self.rate_limiter.wait_if_needed()
        if wait_result > 0:
            self._log("info", f"Rate limited, waited {wait_result:.1f}s")
        
        url = f"{self.COINGECKO_BASE_URL}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false"
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            self.rate_limiter.record_call()
            
            if response.status_code != 200:
                return None
            
            return response.json()
            
        except Exception as e:
            self._log("error", f"Failed to fetch info for {symbol}: {e}")
            return None
    
    def _parse_market_chart_data(self, symbol: str, data: Dict[str, Any],
                                  coin_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse CoinGecko market_chart response into our standard format."""
        prices = data.get("prices", [])
        volumes = data.get("total_volumes", [])
        
        # Create volume lookup by timestamp
        volume_map = {v[0]: v[1] for v in volumes}
        
        price_data = []
        for price_point in prices:
            timestamp_ms = price_point[0]
            close_price = price_point[1]
            
            # Convert timestamp to date string
            date = datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d")
            
            # CoinGecko market_chart only provides close prices
            # We'll use close for OHLC (single daily data point)
            price_data.append({
                "timestamp": date,
                "open": close_price,  # Use close as open (approximate)
                "high": close_price,  # Use close as high (approximate)
                "low": close_price,   # Use close as low (approximate)
                "close": close_price,
                "volume": volume_map.get(timestamp_ms)
            })
        
        # Remove duplicates (keep latest for each day)
        seen_dates = {}
        for price in price_data:
            seen_dates[price["timestamp"]] = price
        price_data = sorted(seen_dates.values(), key=lambda x: x["timestamp"])
        
        # Build metadata
        metadata = {
            "name": symbol,
            "market_cap": None
        }
        
        if coin_info:
            metadata["name"] = coin_info.get("name", symbol)
            market_data = coin_info.get("market_data", {})
            if market_data:
                metadata["market_cap"] = market_data.get("market_cap", {}).get("usd")
        
        return {
            "symbol": symbol,
            "prices": price_data,
            "metadata": metadata,
            "source": "coingecko"
        }
    
    def fetch_ohlc_data(self, symbol: str, days: int = 365) -> Optional[Dict[str, Any]]:
        """
        Fetch OHLC data from CoinGecko API.
        
        Note: OHLC endpoint is limited to certain day ranges.
        
        Args:
            symbol: Crypto symbol (e.g., "BTC")
            days: Number of days (1, 7, 14, 30, 90, 180, 365, max)
            
        Returns:
            Dict with OHLC data or None on failure
        """
        coin_id = self._get_coingecko_id(symbol)
        if not coin_id:
            return None
        
        # Check rate limits
        self.rate_limiter.wait_if_needed()
        
        # OHLC endpoint
        url = f"{self.COINGECKO_BASE_URL}/coins/{coin_id}/ohlc"
        params = {
            "vs_currency": "usd",
            "days": days
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            self.rate_limiter.record_call()
            
            if response.status_code != 200:
                return None
            
            ohlc_data = response.json()
            
            if not ohlc_data:
                return None
            
            # Parse OHLC: [timestamp, open, high, low, close]
            price_data = []
            for ohlc in ohlc_data:
                if len(ohlc) >= 5:
                    timestamp_ms, open_p, high_p, low_p, close_p = ohlc[:5]
                    date = datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d")
                    price_data.append({
                        "timestamp": date,
                        "open": open_p,
                        "high": high_p,
                        "low": low_p,
                        "close": close_p,
                        "volume": None  # OHLC endpoint doesn't include volume
                    })
            
            # Remove duplicates
            seen_dates = {}
            for price in price_data:
                seen_dates[price["timestamp"]] = price
            price_data = sorted(seen_dates.values(), key=lambda x: x["timestamp"])
            
            return {
                "symbol": symbol,
                "prices": price_data,
                "source": "coingecko_ohlc"
            }
            
        except Exception as e:
            self._log("error", f"OHLC fetch failed for {symbol}: {e}")
            return None
    
    def fetch_crypto_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch crypto data with best available method.
        
        Args:
            symbol: Crypto symbol
            
        Returns:
            Dict with crypto data or None on failure
        """
        self._log("info", f"Fetching {symbol} from CoinGecko")
        
        # Try market_chart first (more complete data)
        data = self.fetch_price_history(symbol, days=self.backfill_days)
        
        if data:
            # Try to get coin info for metadata
            coin_info = None
            if self.rate_limiter.can_call():
                coin_info = self.fetch_coin_info(symbol)
            
            return self._parse_market_chart_data(symbol, data, coin_info)
        
        # Fallback to OHLC endpoint
        self._log("info", f"Trying OHLC endpoint for {symbol}")
        ohlc_data = self.fetch_ohlc_data(symbol)
        
        if ohlc_data:
            ohlc_data["metadata"] = {"name": symbol, "market_cap": None}
            return ohlc_data
        
        return None
    
    def ingest_to_database(self, crypto_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store crypto data in database.
        
        Args:
            crypto_data: Dict with symbol, prices, metadata
            
        Returns:
            Dict with ingestion results
        """
        symbol = crypto_data["symbol"]
        prices = crypto_data.get("prices", [])
        metadata = crypto_data.get("metadata", {})
        
        result = {
            "symbol": symbol,
            "prices_ingested": 0,
            "metadata_updated": False,
            "errors": []
        }
        
        try:
            # Insert/update crypto metadata
            self.db.insert_crypto({
                "symbol": symbol,
                "name": metadata.get("name", symbol),
                "market_cap": metadata.get("market_cap")
            })
            result["metadata_updated"] = True
            
        except Exception as e:
            result["errors"].append(f"Metadata error: {e}")
        
        # Insert price history
        try:
            if prices:
                count = self.db.insert_price_history_batch([
                    {
                        "symbol": symbol,
                        "asset_type": "crypto",
                        **price
                    }
                    for price in prices
                ])
                result["prices_ingested"] = count
                
        except Exception as e:
            result["errors"].append(f"Price history error: {e}")
        
        return result
    
    def collect_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Collect data for a single symbol.
        
        Args:
            symbol: Crypto symbol
            
        Returns:
            Dict with collection results
        """
        result = {
            "symbol": symbol,
            "success": False,
            "source": None,
            "prices_ingested": 0,
            "error": None
        }
        
        try:
            # Fetch data
            data = self.fetch_crypto_data(symbol)
            
            if not data:
                result["error"] = "Failed to fetch data"
                return result
            
            result["source"] = data.get("source", "unknown")
            
            # Ingest to database
            ingestion_result = self.ingest_to_database(data)
            result["prices_ingested"] = ingestion_result["prices_ingested"]
            
            if ingestion_result["errors"]:
                result["error"] = "; ".join(ingestion_result["errors"])
            else:
                result["success"] = True
                
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def collect_all(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Collect data for all symbols in watchlist.
        
        Args:
            symbols: Optional list of symbols (defaults to watchlist)
            
        Returns:
            Dict with collection results
        """
        symbols = symbols or self.watchlist
        
        if not symbols:
            self._log("warning", "No crypto symbols to collect")
            return {"success": True, "collected": 0, "errors": []}
        
        self._log("info", f"Starting crypto collection for {len(symbols)} symbols")
        
        results = {
            "success": True,
            "collected": 0,
            "failed": 0,
            "total_prices": 0,
            "errors": [],
            "details": []
        }
        
        for i, symbol in enumerate(symbols):
            self._log("info", f"Collecting {symbol} ({i+1}/{len(symbols)})")
            
            result = self.collect_symbol(symbol)
            results["details"].append(result)
            
            if result["success"]:
                results["collected"] += 1
                results["total_prices"] += result["prices_ingested"]
                self._log("success", f"[OK] {symbol}: {result['prices_ingested']} prices")
            else:
                results["failed"] += 1
                results["errors"].append(f"{symbol}: {result['error']}")
                self._log("error", f"[FAIL] {symbol}: {result['error']}")
            
            # Longer delay between symbols to avoid rate limiting
            if i < len(symbols) - 1:
                time.sleep(2.0)  # 2 second delay between symbols
        
        if results["failed"] > 0:
            results["success"] = results["collected"] > 0
        
        self._log("info", f"Crypto collection complete: {results['collected']}/{len(symbols)} symbols, {results['total_prices']} prices")
        
        return results
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        return self.rate_limiter.get_status()
