"""
Retry utilities for API calls with exponential backoff.
"""

import time
import random
from typing import TypeVar, Callable, Optional, Any
from functools import wraps

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
        jitter: Whether to add random jitter to delay
        exceptions: Tuple of exceptions to catch and retry on
        on_retry: Optional callback(attempt, exception, delay) called before each retry
        
    Returns:
        Decorated function
        
    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def fetch_data():
            return requests.get(url)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt >= max_retries:
                        # No more retries
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    
                    # Add jitter if enabled
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt + 1, e, delay)
                    
                    time.sleep(delay)
            
            # Raise the last exception if all retries failed
            if last_exception:
                raise last_exception
            return None  # type: ignore
        
        return wrapper
    return decorator


def retry_api_call(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    log_callback: Optional[Callable[[str, str], None]] = None
) -> Optional[T]:
    """
    Retry an API call with exponential backoff.
    
    Args:
        func: Function to call
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        log_callback: Optional logging callback(level, message)
        
    Returns:
        Result of func or None on failure
    """
    import requests
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except requests.RequestException as e:
            last_exception = e
            
            if attempt >= max_retries:
                break
            
            delay = base_delay * (2 ** attempt) * (0.5 + random.random())
            
            if log_callback:
                log_callback("warning", f"API call failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay:.1f}s")
            
            time.sleep(delay)
        except Exception as e:
            # Non-retryable error
            if log_callback:
                log_callback("error", f"Non-retryable error: {e}")
            raise
    
    if log_callback and last_exception:
        log_callback("error", f"All {max_retries + 1} attempts failed: {last_exception}")
    
    return None


class RetryableAPIClient:
    """
    Base class for API clients with retry support.
    
    Provides common retry functionality for API calls.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._log_callback = log_callback
    
    def _log(self, level: str, message: str) -> None:
        """Log a message."""
        if self._log_callback:
            self._log_callback(level, message)
        else:
            print(f"[{level.upper()}] {message}")
    
    def _retry_request(
        self,
        request_func: Callable[[], T],
        context: str = "API call"
    ) -> Optional[T]:
        """
        Execute a request with retry logic.
        
        Args:
            request_func: Function that makes the request
            context: Description for logging
            
        Returns:
            Result or None on failure
        """
        import requests
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return request_func()
            except requests.RequestException as e:
                last_exception = e
                
                if attempt >= self.max_retries:
                    break
                
                delay = min(
                    self.base_delay * (2 ** attempt) * (0.5 + random.random()),
                    self.max_delay
                )
                
                self._log(
                    "warning",
                    f"{context} failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                    f"Retrying in {delay:.1f}s"
                )
                
                time.sleep(delay)
            except Exception as e:
                # Non-retryable error
                self._log("error", f"{context} non-retryable error: {e}")
                return None
        
        if last_exception:
            self._log("error", f"{context} failed after {self.max_retries + 1} attempts: {last_exception}")
        
        return None
