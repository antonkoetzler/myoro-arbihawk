"""
Stock data ingestion service.

Fetches stock price data from Alpha Vantage API with yfinance fallback.
Implements rate limiting, caching, and automatic fallback to scraping.
"""

import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import requests_cache
    REQUESTS_CACHE_AVAILABLE = True
except ImportError:
    REQUESTS_CACHE_AVAILABLE = False

from .database import Database
import config


class RateLimiter:
    """
    Rate limiter for API calls.
    
    Tracks calls per minute and per day to respect API limits.
    """
    
    def __init__(self, calls_per_min: int = 5, calls_per_day: int = 25):
        self.calls_per_min = calls_per_min
        self.calls_per_day = calls_per_day
        self._minute_calls: List[float] = []
        self._day_calls: List[float] = []
        self._day_start: Optional[datetime] = None
    
    def can_call(self) -> bool:
        """Check if we can make an API call within rate limits."""
        now = time.time()
        now_dt = datetime.now()
        
        # Reset day counter at midnight
        if self._day_start is None or now_dt.date() != self._day_start.date():
            self._day_calls = []
            self._day_start = now_dt
        
        # Clean up old minute calls
        self._minute_calls = [t for t in self._minute_calls if now - t < 60]
        
        # Check limits
        if len(self._minute_calls) >= self.calls_per_min:
            return False
        if len(self._day_calls) >= self.calls_per_day:
            return False
        
        return True
    
    def record_call(self) -> None:
        """Record that an API call was made."""
        now = time.time()
        now_dt = datetime.now()
        
        # Initialize day start if needed
        if self._day_start is None:
            self._day_start = now_dt
        
        self._minute_calls.append(now)
        self._day_calls.append(now)
    
    def wait_if_needed(self) -> float:
        """Wait if rate limited. Returns seconds waited."""
        if self.can_call():
            return 0.0
        
        now = time.time()
        
        # Check if day limit reached
        if len(self._day_calls) >= self.calls_per_day:
            # Can't wait for day reset - return -1 to indicate fallback needed
            return -1.0
        
        # Wait for minute limit to reset
        if self._minute_calls:
            oldest = min(self._minute_calls)
            wait_time = 60 - (now - oldest) + 0.1  # Add small buffer
            if wait_time > 0:
                time.sleep(wait_time)
                return wait_time
        
        return 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        now = time.time()
        self._minute_calls = [t for t in self._minute_calls if now - t < 60]
        
        return {
            "calls_this_minute": len(self._minute_calls),
            "calls_today": len(self._day_calls),
            "minute_limit": self.calls_per_min,
            "day_limit": self.calls_per_day,
            "can_call": self.can_call()
        }


class StockIngestionService:
    """
    Service for ingesting stock price data.
    
    Uses Alpha Vantage API as primary source with yfinance fallback.
    Implements rate limiting, caching, and automatic fallback.
    
    Example usage:
        service = StockIngestionService()
        result = service.collect_all()
    """
    
    ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, db: Optional[Database] = None, 
                 log_callback: Optional[Callable[[str, str], None]] = None):
        self.db = db or Database()
        self._log_callback = log_callback
        
        # Load config
        trading_config = config.TRADING_CONFIG
        self.api_key = trading_config.get("api_keys", {}).get("alpha_vantage", "")
        self.watchlist = trading_config.get("watchlist", {}).get("stocks", [])
        self.backfill_days = trading_config.get("historical_backfill_days", 365)
        self.scraping_fallback_enabled = trading_config.get("scraping_fallback", {}).get("enabled", True)
        
        # Rate limiting
        rate_config = trading_config.get("rate_limiting", {})
        self.rate_limiter = RateLimiter(
            calls_per_min=rate_config.get("alpha_vantage_calls_per_min", 5),
            calls_per_day=rate_config.get("alpha_vantage_calls_per_day", 25)
        )
        
        # Setup session with optional caching
        if REQUESTS_CACHE_AVAILABLE:
            cache_path = Path(config.DATA_DIR) / "cache" / "stock_api_cache"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.session = requests_cache.CachedSession(
                str(cache_path),
                expire_after=3600,  # 1 hour cache
                allowable_methods=['GET']
            )
        else:
            self.session = requests.Session()
        
        # Track fallback usage
        self._using_fallback = False
        self._fallback_reason = ""
    
    def _log(self, level: str, message: str) -> None:
        """Log a message."""
        if self._log_callback:
            self._log_callback(level, f"[STOCKS] {message}")
        else:
            print(f"[{level.upper()}] [STOCKS] {message}")
    
    def check_api_key(self) -> bool:
        """Check if API key is configured."""
        if not self.api_key:
            self._log("warning", "Alpha Vantage API key not configured - using scraping fallback")
            return False
        return True
    
    def fetch_price_history_api(self, symbol: str, outputsize: str = "full") -> Optional[Dict[str, Any]]:
        """
        Fetch price history from Alpha Vantage API.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            outputsize: "compact" (100 days) or "full" (20+ years)
            
        Returns:
            Dict with price data or None on failure
        """
        if not self.api_key:
            return None
        
        # Check rate limits
        wait_result = self.rate_limiter.wait_if_needed()
        if wait_result < 0:
            self._log("warning", f"Daily API limit reached for {symbol}")
            return None
        elif wait_result > 0:
            self._log("info", f"Rate limited, waited {wait_result:.1f}s")
        
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": self.api_key
        }
        
        # Retry logic with exponential backoff
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(self.ALPHA_VANTAGE_BASE_URL, params=params, timeout=30)
                self.rate_limiter.record_call()
                
                if response.status_code == 429:
                    # Rate limited - wait and retry
                    delay = (2 ** attempt) * (0.5 + 0.5 * (attempt / max_retries))
                    self._log("warning", f"Rate limited for {symbol}, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                
                if response.status_code != 200:
                    self._log("error", f"API error for {symbol}: HTTP {response.status_code}")
                    return None
                
                data = response.json()
                
                # Check for API errors
                if "Error Message" in data:
                    self._log("error", f"API error for {symbol}: {data['Error Message']}")
                    return None
                
                if "Note" in data:
                    # Rate limit message from API - treat as rate limit
                    delay = (2 ** attempt) * 2
                    self._log("warning", f"API rate limit message for {symbol}: {data['Note'][:50]}... Retrying in {delay:.1f}s")
                    time.sleep(delay)
                    continue
                
                if "Time Series (Daily)" not in data:
                    self._log("warning", f"No time series data for {symbol}")
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
    
    def fetch_company_overview_api(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch company overview (fundamental data) from Alpha Vantage API.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            
        Returns:
            Dict with company data or None on failure
        """
        if not self.api_key:
            return None
        
        # Check rate limits
        wait_result = self.rate_limiter.wait_if_needed()
        if wait_result < 0:
            return None
        
        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
            "apikey": self.api_key
        }
        
        try:
            response = self.session.get(self.ALPHA_VANTAGE_BASE_URL, params=params, timeout=30)
            self.rate_limiter.record_call()
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if not data or "Symbol" not in data:
                return None
            
            return data
            
        except Exception as e:
            self._log("error", f"Failed to fetch overview for {symbol}: {e}")
            return None
    
    def fetch_via_yfinance(self, symbol: str, period: str = "1y") -> Optional[Dict[str, Any]]:
        """
        Fetch price history using yfinance (Yahoo Finance scraping).
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            period: Period string ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
            
        Returns:
            Dict with price data or None on failure
        """
        if not YFINANCE_AVAILABLE:
            self._log("error", "yfinance not installed - cannot use scraping fallback")
            return None
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Get historical data
            hist = ticker.history(period=period)
            
            if hist.empty:
                self._log("warning", f"No yfinance data for {symbol}")
                return None
            
            # Get company info
            try:
                info = ticker.info
            except Exception:
                info = {}
            
            # Convert to our format
            price_data = []
            for date, row in hist.iterrows():
                price_data.append({
                    "timestamp": date.strftime("%Y-%m-%d"),
                    "open": float(row["Open"]) if row["Open"] else None,
                    "high": float(row["High"]) if row["High"] else None,
                    "low": float(row["Low"]) if row["Low"] else None,
                    "close": float(row["Close"]) if row["Close"] else None,
                    "volume": float(row["Volume"]) if row["Volume"] else None
                })
            
            return {
                "symbol": symbol,
                "prices": price_data,
                "metadata": {
                    "name": info.get("longName", info.get("shortName", symbol)),
                    "sector": info.get("sector", ""),
                    "industry": info.get("industry", ""),
                    "market_cap": info.get("marketCap"),
                    "exchange": info.get("exchange", "")
                },
                "source": "yfinance"
            }
            
        except Exception as e:
            self._log("error", f"yfinance error for {symbol}: {e}")
            return None
    
    def _parse_alpha_vantage_data(self, symbol: str, data: Dict[str, Any], 
                                   overview: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse Alpha Vantage response into our standard format."""
        time_series = data.get("Time Series (Daily)", {})
        
        price_data = []
        for date_str, values in time_series.items():
            price_data.append({
                "timestamp": date_str,
                "open": float(values.get("1. open", 0)),
                "high": float(values.get("2. high", 0)),
                "low": float(values.get("3. low", 0)),
                "close": float(values.get("4. close", 0)),
                "volume": float(values.get("5. volume", 0))
            })
        
        # Sort by date (oldest first)
        price_data.sort(key=lambda x: x["timestamp"])
        
        # Build metadata
        metadata = {
            "name": symbol,
            "sector": "",
            "industry": "",
            "market_cap": None,
            "exchange": ""
        }
        
        if overview:
            metadata["name"] = overview.get("Name", symbol)
            metadata["sector"] = overview.get("Sector", "")
            metadata["industry"] = overview.get("Industry", "")
            metadata["exchange"] = overview.get("Exchange", "")
            try:
                metadata["market_cap"] = float(overview.get("MarketCapitalization", 0))
            except (ValueError, TypeError):
                pass
        
        return {
            "symbol": symbol,
            "prices": price_data,
            "metadata": metadata,
            "source": "alpha_vantage"
        }
    
    def fetch_stock_data(self, symbol: str, use_fallback: bool = True) -> Optional[Dict[str, Any]]:
        """
        Fetch stock data with automatic fallback.
        
        Args:
            symbol: Stock symbol
            use_fallback: Whether to use yfinance fallback on API failure
            
        Returns:
            Dict with stock data or None on failure
        """
        # Try Alpha Vantage API first
        if self.api_key and self.rate_limiter.can_call():
            self._log("info", f"Fetching {symbol} from Alpha Vantage API")
            data = self.fetch_price_history_api(symbol)
            
            if data:
                # Try to get company overview (optional, may fail due to rate limits)
                overview = None
                if self.rate_limiter.can_call():
                    overview = self.fetch_company_overview_api(symbol)
                
                return self._parse_alpha_vantage_data(symbol, data, overview)
        
        # Fallback to yfinance
        if use_fallback and self.scraping_fallback_enabled:
            self._log("info", f"Using yfinance fallback for {symbol}")
            self._using_fallback = True
            self._fallback_reason = "API unavailable or rate limited"
            return self.fetch_via_yfinance(symbol)
        
        return None
    
    def ingest_to_database(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store stock data in database.
        
        Args:
            stock_data: Dict with symbol, prices, metadata
            
        Returns:
            Dict with ingestion results
        """
        symbol = stock_data["symbol"]
        prices = stock_data.get("prices", [])
        metadata = stock_data.get("metadata", {})
        
        result = {
            "symbol": symbol,
            "prices_ingested": 0,
            "metadata_updated": False,
            "errors": []
        }
        
        try:
            # Insert/update stock metadata
            self.db.insert_stock({
                "symbol": symbol,
                "name": metadata.get("name", symbol),
                "sector": metadata.get("sector", ""),
                "industry": metadata.get("industry", ""),
                "market_cap": metadata.get("market_cap"),
                "exchange": metadata.get("exchange", "")
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
                        "asset_type": "stock",
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
            symbol: Stock symbol
            
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
            data = self.fetch_stock_data(symbol)
            
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
            self._log("warning", "No symbols to collect")
            return {"success": True, "collected": 0, "errors": []}
        
        # Check API key
        has_api_key = self.check_api_key()
        if not has_api_key and not self.scraping_fallback_enabled:
            self._log("error", "No API key and scraping fallback disabled")
            return {"success": False, "collected": 0, "errors": ["No data source available"]}
        
        self._log("info", f"Starting stock collection for {len(symbols)} symbols")
        
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
                self._log("success", f"✓ {symbol}: {result['prices_ingested']} prices ({result['source']})")
            else:
                results["failed"] += 1
                results["errors"].append(f"{symbol}: {result['error']}")
                self._log("error", f"✗ {symbol}: {result['error']}")
        
        if results["failed"] > 0:
            results["success"] = results["collected"] > 0  # Partial success is still success
        
        self._log("info", f"Stock collection complete: {results['collected']}/{len(symbols)} symbols, {results['total_prices']} prices")
        
        return results
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        return self.rate_limiter.get_status()
