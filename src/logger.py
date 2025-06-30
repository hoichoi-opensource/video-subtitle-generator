"""
Production-grade logging and monitoring system
Structured logging with performance metrics and error tracking
"""

import os
import sys
import json
import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
import time
import traceback
import threading
from dataclasses import dataclass, asdict

from .exceptions import BaseSubtitleError


@dataclass
class LogMetrics:
    """Structured log metrics"""
    timestamp: str
    level: str
    message: str
    module: str
    function: str
    line_number: int
    job_id: Optional[str] = None
    user_id: Optional[str] = None
    duration_ms: Optional[float] = None
    memory_mb: Optional[float] = None
    error_type: Optional[str] = None
    error_code: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Extract context from record
        context = getattr(record, 'context', {})
        job_id = getattr(record, 'job_id', None)
        user_id = getattr(record, 'user_id', None)
        duration_ms = getattr(record, 'duration_ms', None)
        memory_mb = getattr(record, 'memory_mb', None)
        error_type = getattr(record, 'error_type', None)
        error_code = getattr(record, 'error_code', None)
        
        # Create structured log entry
        log_entry = LogMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=record.levelname,
            message=record.getMessage(),
            module=record.module,
            function=record.funcName,
            line_number=record.lineno,
            job_id=job_id,
            user_id=user_id,
            duration_ms=duration_ms,
            memory_mb=memory_mb,
            error_type=error_type,
            error_code=error_code,
            context=context
        )
        
        # Add exception information if present
        if record.exc_info:
            log_entry.context = log_entry.context or {}
            log_entry.context['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(asdict(log_entry), default=str, ensure_ascii=False)


class PerformanceLogger:
    """Performance monitoring and logging"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._timers = {}
        self._counters = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def timer(self, operation: str, job_id: str = None):
        """Context manager for timing operations"""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            end_memory = self._get_memory_usage()
            
            # Log performance metrics
            self.logger.info(
                f"Performance: {operation} completed",
                extra={
                    'job_id': job_id,
                    'duration_ms': duration_ms,
                    'memory_mb': end_memory,
                    'memory_delta_mb': end_memory - start_memory if start_memory else None,
                    'context': {'operation': operation}
                }
            )
            
            # Store metrics
            with self._lock:
                if operation not in self._timers:
                    self._timers[operation] = []
                self._timers[operation].append(duration_ms)
    
    def count(self, event: str, value: int = 1, job_id: str = None):
        """Count events"""
        with self._lock:
            if event not in self._counters:
                self._counters[event] = 0
            self._counters[event] += value
        
        self.logger.debug(
            f"Counter: {event} += {value}",
            extra={
                'job_id': job_id,
                'context': {'event': event, 'value': value, 'total': self._counters[event]}
            }
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self._lock:
            metrics = {
                'timers': {},
                'counters': dict(self._counters)
            }
            
            for operation, times in self._timers.items():
                if times:
                    metrics['timers'][operation] = {
                        'count': len(times),
                        'total_ms': sum(times),
                        'avg_ms': sum(times) / len(times),
                        'min_ms': min(times),
                        'max_ms': max(times)
                    }
            
            return metrics
    
    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            return None


class LoggerManager:
    """Centralized logger management"""
    
    def __init__(self, log_dir: str = "logs", log_level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_level = getattr(logging, log_level.upper())
        
        # Configure root logger
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(self.log_level)
        
        # Clear existing handlers
        self.root_logger.handlers.clear()
        
        # Create formatters
        self.structured_formatter = StructuredFormatter()
        self.console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Setup handlers
        self._setup_handlers()
        
        # Performance logger
        self.performance = PerformanceLogger(self.get_logger('performance'))
        
        # Error tracking
        self.error_counts = {}
        self._error_lock = threading.Lock()
    
    def _setup_handlers(self):
        """Setup logging handlers"""
        # Console handler for development
        if os.getenv('ENVIRONMENT') != 'production':
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(self.console_formatter)
            self.root_logger.addHandler(console_handler)
        
        # File handler for all logs (structured JSON)
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'application.jsonl',
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(self.structured_formatter)
        self.root_logger.addHandler(file_handler)
        
        # Error-only handler
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'errors.jsonl',
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self.structured_formatter)
        self.root_logger.addHandler(error_handler)
        
        # Performance metrics handler
        perf_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'performance.jsonl',
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=3,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(self.structured_formatter)
        
        # Add filter to only log performance-related messages
        perf_handler.addFilter(lambda record: record.name == 'performance')
        self.root_logger.addHandler(perf_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get logger instance"""
        return logging.getLogger(name)
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None, job_id: str = None):
        """Log error with structured information"""
        logger = self.get_logger('error')
        
        # Extract error information
        error_type = type(error).__name__
        error_code = getattr(error, 'error_code', None)
        error_message = str(error)
        
        # Track error counts
        with self._error_lock:
            if error_type not in self.error_counts:
                self.error_counts[error_type] = 0
            self.error_counts[error_type] += 1
        
        # Prepare context
        error_context = context or {}
        if isinstance(error, BaseSubtitleError):
            error_context.update(error.context)
        
        # Log error
        logger.error(
            f"Error occurred: {error_message}",
            extra={
                'job_id': job_id,
                'error_type': error_type,
                'error_code': error_code,
                'context': error_context
            },
            exc_info=error
        )
    
    def log_job_start(self, job_id: str, video_path: str, languages: List[str]):
        """Log job start"""
        logger = self.get_logger('job')
        logger.info(
            f"Job started: {job_id}",
            extra={
                'job_id': job_id,
                'context': {
                    'video_path': video_path,
                    'languages': languages,
                    'stage': 'start'
                }
            }
        )
    
    def log_job_complete(self, job_id: str, output_files: List[str], duration_ms: float):
        """Log job completion"""
        logger = self.get_logger('job')
        logger.info(
            f"Job completed: {job_id}",
            extra={
                'job_id': job_id,
                'duration_ms': duration_ms,
                'context': {
                    'output_files': output_files,
                    'file_count': len(output_files),
                    'stage': 'complete'
                }
            }
        )
    
    def log_stage_progress(self, job_id: str, stage: str, progress: int, message: str = None):
        """Log stage progress"""
        logger = self.get_logger('progress')
        logger.info(
            message or f"Stage {stage}: {progress}%",
            extra={
                'job_id': job_id,
                'context': {
                    'stage': stage,
                    'progress': progress
                }
            }
        )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary for monitoring"""
        with self._error_lock:
            return {
                'total_errors': sum(self.error_counts.values()),
                'error_types': dict(self.error_counts),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for logging system"""
        try:
            # Test log write
            test_logger = self.get_logger('health')
            test_logger.info("Health check")
            
            # Check log directory
            log_files = list(self.log_dir.glob('*.jsonl'))
            
            return {
                'status': 'healthy',
                'log_directory': str(self.log_dir),
                'log_files': len(log_files),
                'error_counts': dict(self.error_counts),
                'performance_metrics': self.performance.get_metrics()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }


# Global logger manager
logger_manager = LoggerManager()


def get_logger(name: str) -> logging.Logger:
    """Get logger instance"""
    return logger_manager.get_logger(name)


def log_performance(operation: str, job_id: str = None):
    """Decorator for performance logging"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with logger_manager.performance.timer(operation, job_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def log_errors(logger_name: str = None, job_id: str = None):
    """Decorator for error logging"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = get_logger(logger_name or func.__module__)
                logger_manager.log_error(e, job_id=job_id)
                raise
        return wrapper
    return decorator