"""
Production-grade retry mechanism with exponential backoff
Handles transient failures with intelligent retry strategies
"""

import asyncio
import time
import random
from typing import Callable, Any, Optional, Type, Tuple, List, Dict
from functools import wraps
import logging
from datetime import datetime, timedelta

from .exceptions import (
    BaseSubtitleError, RetryableError, NonRetryableError, 
    RETRYABLE_ERRORS, NON_RETRYABLE_ERRORS,
    NetworkError, CloudStorageError, QuotaExceededError
)


logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        backoff_multiplier: float = 1.0
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.backoff_multiplier = backoff_multiplier
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        if attempt <= 0:
            return 0
        
        # Exponential backoff
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay *= self.backoff_multiplier
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            delay += random.uniform(0, delay * 0.1)
        
        return min(delay, self.max_delay)


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
            else:
                raise NonRetryableError(
                    f"Circuit breaker is OPEN. Too many failures. Try again after {self.recovery_timeout}s",
                    context={
                        'failure_count': self.failure_count,
                        'last_failure': self.last_failure_time,
                        'state': self.state
                    }
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'


class RetryHandler:
    """Advanced retry handler with multiple strategies"""
    
    def __init__(self):
        self.circuit_breakers = {}
        self.retry_configs = {
            'default': RetryConfig(),
            'network': RetryConfig(max_attempts=5, base_delay=2.0, max_delay=120.0),
            'storage': RetryConfig(max_attempts=4, base_delay=1.5, max_delay=90.0),
            'ai': RetryConfig(max_attempts=3, base_delay=3.0, max_delay=180.0),
            'quota': RetryConfig(max_attempts=2, base_delay=60.0, max_delay=300.0)
        }
    
    def get_circuit_breaker(self, key: str) -> CircuitBreaker:
        """Get or create circuit breaker for given key"""
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = CircuitBreaker()
        return self.circuit_breakers[key]
    
    def retry(
        self,
        func: Callable,
        *args,
        retry_config: str = 'default',
        circuit_breaker_key: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Execute function with retry logic"""
        config = self.retry_configs.get(retry_config, self.retry_configs['default'])
        
        # Get circuit breaker if specified
        circuit_breaker = None
        if circuit_breaker_key:
            circuit_breaker = self.get_circuit_breaker(circuit_breaker_key)
        
        last_exception = None
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                logger.debug(f"Attempt {attempt}/{config.max_attempts} for {func.__name__}")
                
                # Use circuit breaker if available
                if circuit_breaker:
                    return circuit_breaker.call(func, *args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except Exception as e:
                last_exception = e
                
                # Check if error is retryable
                if not self._is_retryable_error(e):
                    logger.warning(f"Non-retryable error in {func.__name__}: {e}")
                    raise
                
                # Log attempt failure
                logger.warning(f"Attempt {attempt} failed for {func.__name__}: {e}")
                
                # Don't wait after last attempt
                if attempt < config.max_attempts:
                    delay = config.calculate_delay(attempt)
                    logger.info(f"Retrying {func.__name__} in {delay:.2f}s")
                    time.sleep(delay)
        
        # All attempts failed
        logger.error(f"All {config.max_attempts} attempts failed for {func.__name__}")
        raise last_exception
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if error should be retried"""
        # Check if it's explicitly non-retryable
        if isinstance(error, NON_RETRYABLE_ERRORS):
            return False
        
        # Check if it's explicitly retryable
        if isinstance(error, RETRYABLE_ERRORS):
            return True
        
        # Check for common retryable error patterns
        error_msg = str(error).lower()
        retryable_patterns = [
            'timeout', 'connection', 'network', 'temporary',
            'rate limit', 'quota', 'throttle', 'busy',
            'unavailable', 'service error', '502', '503', '504'
        ]
        
        return any(pattern in error_msg for pattern in retryable_patterns)


# Global retry handler instance
retry_handler = RetryHandler()


def with_retry(
    retry_config: str = 'default',
    circuit_breaker_key: Optional[str] = None
):
    """Decorator for adding retry behavior to functions"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return retry_handler.retry(
                func,
                *args,
                retry_config=retry_config,
                circuit_breaker_key=circuit_breaker_key,
                **kwargs
            )
        return wrapper
    
    return decorator


def with_async_retry(
    retry_config: str = 'default',
    circuit_breaker_key: Optional[str] = None
):
    """Decorator for adding retry behavior to async functions"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            config = retry_handler.retry_configs.get(retry_config, retry_handler.retry_configs['default'])
            
            # Get circuit breaker if specified
            circuit_breaker = None
            if circuit_breaker_key:
                circuit_breaker = retry_handler.get_circuit_breaker(circuit_breaker_key)
            
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    logger.debug(f"Async attempt {attempt}/{config.max_attempts} for {func.__name__}")
                    
                    # Use circuit breaker if available
                    if circuit_breaker:
                        # Note: Circuit breaker doesn't directly support async, 
                        # so we implement the logic here
                        if circuit_breaker.state == 'OPEN':
                            if circuit_breaker._should_attempt_reset():
                                circuit_breaker.state = 'HALF_OPEN'
                            else:
                                raise NonRetryableError(
                                    f"Circuit breaker is OPEN for {func.__name__}",
                                    context={'state': circuit_breaker.state}
                                )
                        
                        try:
                            result = await func(*args, **kwargs)
                            circuit_breaker._on_success()
                            return result
                        except Exception as e:
                            circuit_breaker._on_failure()
                            raise
                    else:
                        return await func(*args, **kwargs)
                        
                except Exception as e:
                    last_exception = e
                    
                    # Check if error is retryable
                    if not retry_handler._is_retryable_error(e):
                        logger.warning(f"Non-retryable error in async {func.__name__}: {e}")
                        raise
                    
                    # Log attempt failure
                    logger.warning(f"Async attempt {attempt} failed for {func.__name__}: {e}")
                    
                    # Don't wait after last attempt
                    if attempt < config.max_attempts:
                        delay = config.calculate_delay(attempt)
                        logger.info(f"Retrying async {func.__name__} in {delay:.2f}s")
                        await asyncio.sleep(delay)
            
            # All attempts failed
            logger.error(f"All {config.max_attempts} async attempts failed for {func.__name__}")
            raise last_exception
        
        return wrapper
    
    return decorator


class RateLimiter:
    """Rate limiter to prevent quota exhaustion"""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls = []
    
    def acquire(self) -> float:
        """Acquire permission to make a call, returns delay if needed"""
        now = time.time()
        
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]
        
        if len(self.calls) >= self.calls_per_minute:
            # Need to wait
            oldest_call = min(self.calls)
            delay = 60 - (now - oldest_call) + 0.1  # Add small buffer
            return max(0, delay)
        
        # Can make call immediately
        self.calls.append(now)
        return 0
    
    def wait_if_needed(self):
        """Block until rate limit allows next call"""
        delay = self.acquire()
        if delay > 0:
            logger.info(f"Rate limiting: waiting {delay:.2f}s")
            time.sleep(delay)


# Global rate limiters for different services
rate_limiters = {
    'vertex_ai': RateLimiter(calls_per_minute=30),  # Conservative limit
    'storage': RateLimiter(calls_per_minute=100),
    'default': RateLimiter(calls_per_minute=60)
}