"""
Production Performance Optimizer
Implements caching, connection pooling, and resource optimization
"""

import os
import time
import functools
import threading
from typing import Dict, Any, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import weakref
import gc

from .logger import get_logger

logger = get_logger(__name__)


class LRUCache:
    """Thread-safe LRU cache implementation"""
    
    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self.cache: Dict[Any, Tuple[Any, float]] = {}
        self.access_times: Dict[Any, float] = {}
        self._lock = threading.RLock()
    
    def get(self, key: Any, default: Any = None) -> Any:
        """Get item from cache"""
        with self._lock:
            if key in self.cache:
                value, _ = self.cache[key]
                self.access_times[key] = time.time()
                return value
            return default
    
    def put(self, key: Any, value: Any, ttl: float = 3600) -> None:
        """Put item in cache with TTL"""
        with self._lock:
            current_time = time.time()
            
            # Remove expired items
            self._cleanup_expired()
            
            # Remove oldest item if cache is full
            if len(self.cache) >= self.maxsize and key not in self.cache:
                oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            self.cache[key] = (value, current_time + ttl)
            self.access_times[key] = current_time
    
    def _cleanup_expired(self) -> None:
        """Remove expired items"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry) in self.cache.items() 
            if current_time > expiry
        ]
        for key in expired_keys:
            del self.cache[key]
            del self.access_times[key]
    
    def clear(self) -> None:
        """Clear cache"""
        with self._lock:
            self.cache.clear()
            self.access_times.clear()


class ConnectionPool:
    """Connection pool for reusing expensive connections"""
    
    def __init__(self, factory: Callable, max_size: int = 10, timeout: float = 30):
        self.factory = factory
        self.max_size = max_size
        self.timeout = timeout
        self.pool = []
        self.active = weakref.WeakSet()
        self._lock = threading.Lock()
        self.created_count = 0
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool"""
        conn = None
        try:
            with self._lock:
                if self.pool:
                    conn = self.pool.pop()
                elif self.created_count < self.max_size:
                    conn = self.factory()
                    self.created_count += 1
                else:
                    # Wait for connection to become available
                    # This is a simplified implementation
                    raise ResourceError("Connection pool exhausted")
                
                self.active.add(conn)
            
            yield conn
            
        finally:
            if conn:
                with self._lock:
                    if conn in self.active:
                        self.active.discard(conn)
                        if len(self.pool) < self.max_size:
                            self.pool.append(conn)
    
    def close_all(self) -> None:
        """Close all connections"""
        with self._lock:
            for conn in list(self.pool):
                try:
                    if hasattr(conn, 'close'):
                        conn.close()
                except Exception:
                    pass
            self.pool.clear()
            self.created_count = 0


class BatchProcessor:
    """Efficient batch processing with configurable concurrency"""
    
    def __init__(self, max_workers: int = 4, batch_size: int = 10):
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def process_items(self, items: list, processor: Callable, progress_callback: Optional[Callable] = None) -> list:
        """Process items in batches with progress tracking"""
        results = []
        total_items = len(items)
        processed_count = 0
        
        # Create batches
        batches = [items[i:i + self.batch_size] for i in range(0, len(items), self.batch_size)]
        
        # Submit batch processing tasks
        future_to_batch = {
            self.executor.submit(self._process_batch, batch, processor): batch
            for batch in batches
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_batch):
            try:
                batch_results = future.result()
                results.extend(batch_results)
                processed_count += len(batch_results)
                
                if progress_callback:
                    progress_callback(processed_count, total_items)
                    
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
                # Continue processing other batches
        
        return results
    
    def _process_batch(self, batch: list, processor: Callable) -> list:
        """Process a single batch of items"""
        results = []
        for item in batch:
            try:
                result = processor(item)
                results.append(result)
            except Exception as e:
                logger.error(f"Item processing error: {e}")
                # Continue processing other items in batch
        return results
    
    def shutdown(self) -> None:
        """Shutdown the executor"""
        self.executor.shutdown(wait=True)


class MemoryOptimizer:
    """Memory usage optimization utilities"""
    
    @staticmethod
    def cached_property(func):
        """Cached property decorator with weak references"""
        cache_attr = f'_cached_{func.__name__}'
        
        @functools.wraps(func)
        def wrapper(self):
            if not hasattr(self, cache_attr):
                setattr(self, cache_attr, func(self))
            return getattr(self, cache_attr)
        
        return property(wrapper)
    
    @staticmethod
    def memory_efficient_generator(items: list, chunk_size: int = 1000):
        """Generator that yields items in chunks to reduce memory usage"""
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]
            # Force garbage collection after each chunk
            gc.collect()
    
    @staticmethod
    def optimize_memory_usage():
        """Force garbage collection and optimize memory"""
        # Clear unreferenced objects
        collected = gc.collect()
        
        # Get memory statistics if available
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            logger.info(f"Memory optimization: collected {collected} objects, "
                       f"RSS: {memory_info.rss / 1024 / 1024:.1f}MB")
        except ImportError:
            logger.info(f"Memory optimization: collected {collected} objects")
    
    @staticmethod
    @contextmanager
    def memory_limit_context(max_mb: int = 1024):
        """Context manager to monitor memory usage"""
        try:
            import psutil
            process = psutil.Process()
            start_memory = process.memory_info().rss / 1024 / 1024
            
            yield
            
            end_memory = process.memory_info().rss / 1024 / 1024
            memory_used = end_memory - start_memory
            
            if memory_used > max_mb:
                logger.warning(f"Memory usage exceeded limit: {memory_used:.1f}MB > {max_mb}MB")
                MemoryOptimizer.optimize_memory_usage()
        except ImportError:
            # psutil not available, just yield
            yield


class FileSystemOptimizer:
    """File system operation optimizations"""
    
    @staticmethod
    def efficient_file_copy(src: str, dst: str, chunk_size: int = 1024 * 1024) -> None:
        """Memory-efficient file copying"""
        with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
            while True:
                chunk = fsrc.read(chunk_size)
                if not chunk:
                    break
                fdst.write(chunk)
    
    @staticmethod
    def batch_file_operations(operations: list, max_workers: int = 4) -> list:
        """Execute file operations in parallel"""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(op) for op in operations]
            results = []
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"File operation error: {e}")
                    results.append(None)
            
            return results


class NetworkOptimizer:
    """Network operation optimizations"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.5):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    def with_retry(self, operation: Callable, *args, **kwargs):
        """Execute operation with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = (self.backoff_factor ** attempt)
                    logger.warning(f"Operation failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Operation failed after {self.max_retries + 1} attempts: {e}")
        
        raise last_exception


# Global optimizers
_cache = LRUCache(maxsize=256)
_memory_optimizer = MemoryOptimizer()
_fs_optimizer = FileSystemOptimizer()
_network_optimizer = NetworkOptimizer()


def memoize(ttl: float = 3600):
    """Memoization decorator with TTL"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = (func.__name__, str(args), str(sorted(kwargs.items())))
            
            # Try to get from cache
            result = _cache.get(key)
            if result is not None:
                return result
            
            # Calculate and cache result
            result = func(*args, **kwargs)
            _cache.put(key, result, ttl)
            return result
        
        return wrapper
    return decorator


def profile_performance(func):
    """Performance profiling decorator"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = None
        
        try:
            import psutil
            process = psutil.Process()
            start_memory = process.memory_info().rss / 1024 / 1024
        except ImportError:
            pass
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            
            if start_memory:
                try:
                    end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    memory_delta = end_memory - start_memory
                    logger.info(f"Performance: {func.__name__} took {execution_time:.2f}s, "
                               f"memory delta: {memory_delta:+.1f}MB")
                except:
                    logger.info(f"Performance: {func.__name__} took {execution_time:.2f}s")
            else:
                logger.info(f"Performance: {func.__name__} took {execution_time:.2f}s")
    
    return wrapper


# Export optimized versions
__all__ = [
    'LRUCache', 'ConnectionPool', 'BatchProcessor', 'MemoryOptimizer',
    'FileSystemOptimizer', 'NetworkOptimizer', 'memoize', 'profile_performance'
]