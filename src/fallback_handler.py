"""
Graceful degradation and fallback mechanisms
Ensures system continues operating even with partial failures
"""

import time
from typing import Dict, List, Any, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass
import threading

from .exceptions import (
    BaseSubtitleError, VertexAIError, CloudStorageError,
    NetworkError, QuotaExceededError, AuthenticationError
)
from .logger import get_logger

logger = get_logger(__name__)


class FallbackStrategy(Enum):
    """Fallback strategy types"""
    SKIP = "skip"
    RETRY_LATER = "retry_later"
    USE_ALTERNATIVE = "use_alternative"
    DEGRADE_QUALITY = "degrade_quality"
    PARTIAL_SUCCESS = "partial_success"


@dataclass
class FallbackAction:
    """Fallback action definition"""
    strategy: FallbackStrategy
    alternative_method: Optional[str] = None
    retry_delay: Optional[int] = None
    quality_level: Optional[str] = None
    max_attempts: int = 1


class GracefulDegradationManager:
    """Manages graceful degradation and fallback strategies"""
    
    def __init__(self):
        self.fallback_strategies: Dict[type, FallbackAction] = {}
        self.alternative_methods: Dict[str, Callable] = {}
        self.partial_results: Dict[str, Any] = {}
        self._lock = threading.Lock()
        
        # Register default fallback strategies
        self._register_default_strategies()
    
    def register_fallback(self, error_type: type, action: FallbackAction):
        """Register fallback strategy for error type"""
        self.fallback_strategies[error_type] = action
        logger.debug(f"Registered fallback for {error_type.__name__}: {action.strategy.value}")
    
    def register_alternative_method(self, name: str, method: Callable):
        """Register alternative method"""
        self.alternative_methods[name] = method
        logger.debug(f"Registered alternative method: {name}")
    
    def _register_default_strategies(self):
        """Register default fallback strategies"""
        # Network errors - retry with delay
        self.register_fallback(
            NetworkError,
            FallbackAction(
                strategy=FallbackStrategy.RETRY_LATER,
                retry_delay=30,
                max_attempts=3
            )
        )
        
        # Quota exceeded - skip and continue
        self.register_fallback(
            QuotaExceededError,
            FallbackAction(
                strategy=FallbackStrategy.SKIP,
                max_attempts=1
            )
        )
        
        # Authentication errors - fail fast
        self.register_fallback(
            AuthenticationError,
            FallbackAction(
                strategy=FallbackStrategy.SKIP,
                max_attempts=1
            )
        )
        
        # General Vertex AI errors - try alternative or skip
        self.register_fallback(
            VertexAIError,
            FallbackAction(
                strategy=FallbackStrategy.USE_ALTERNATIVE,
                alternative_method="simple_transcription",
                max_attempts=2
            )
        )
        
        # Cloud storage errors - retry with exponential backoff
        self.register_fallback(
            CloudStorageError,
            FallbackAction(
                strategy=FallbackStrategy.RETRY_LATER,
                retry_delay=15,
                max_attempts=3
            )
        )
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> FallbackAction:
        """Handle error with appropriate fallback strategy"""
        context = context or {}
        error_type = type(error)
        
        # Find best matching fallback strategy
        fallback = self._find_fallback_strategy(error_type)
        
        if not fallback:
            # Default strategy for unknown errors
            fallback = FallbackAction(strategy=FallbackStrategy.SKIP)
        
        logger.warning(
            f"Applying fallback strategy {fallback.strategy.value} for {error_type.__name__}: {str(error)}",
            extra={'context': context}
        )
        
        return fallback
    
    def _find_fallback_strategy(self, error_type: type) -> Optional[FallbackAction]:
        """Find best matching fallback strategy"""
        # Exact match first
        if error_type in self.fallback_strategies:
            return self.fallback_strategies[error_type]
        
        # Check inheritance hierarchy
        for registered_type, action in self.fallback_strategies.items():
            if issubclass(error_type, registered_type):
                return action
        
        return None
    
    def execute_fallback(self, action: FallbackAction, context: Dict[str, Any] = None) -> Any:
        """Execute fallback action"""
        context = context or {}
        
        try:
            if action.strategy == FallbackStrategy.SKIP:
                return self._handle_skip(context)
            elif action.strategy == FallbackStrategy.RETRY_LATER:
                return self._handle_retry_later(action, context)
            elif action.strategy == FallbackStrategy.USE_ALTERNATIVE:
                return self._handle_use_alternative(action, context)
            elif action.strategy == FallbackStrategy.DEGRADE_QUALITY:
                return self._handle_degrade_quality(action, context)
            elif action.strategy == FallbackStrategy.PARTIAL_SUCCESS:
                return self._handle_partial_success(context)
            else:
                logger.warning(f"Unknown fallback strategy: {action.strategy}")
                return None
                
        except Exception as e:
            logger.error(f"Fallback execution failed: {e}")
            return None
    
    def _handle_skip(self, context: Dict[str, Any]) -> Any:
        """Handle skip strategy"""
        logger.info(f"Skipping operation: {context.get('operation', 'unknown')}")
        
        # Store information about skipped operation
        with self._lock:
            if 'skipped_operations' not in self.partial_results:
                self.partial_results['skipped_operations'] = []
            self.partial_results['skipped_operations'].append(context)
        
        return None
    
    def _handle_retry_later(self, action: FallbackAction, context: Dict[str, Any]) -> Any:
        """Handle retry later strategy"""
        delay = action.retry_delay or 30
        
        logger.info(f"Scheduling retry in {delay} seconds for: {context.get('operation', 'unknown')}")
        
        # Store for later retry (simplified implementation)
        with self._lock:
            if 'retry_queue' not in self.partial_results:
                self.partial_results['retry_queue'] = []
            self.partial_results['retry_queue'].append({
                'context': context,
                'retry_after': time.time() + delay,
                'attempts': context.get('attempts', 0) + 1,
                'max_attempts': action.max_attempts
            })
        
        return None
    
    def _handle_use_alternative(self, action: FallbackAction, context: Dict[str, Any]) -> Any:
        """Handle use alternative strategy"""
        if not action.alternative_method:
            logger.warning("No alternative method specified")
            return self._handle_skip(context)
        
        if action.alternative_method not in self.alternative_methods:
            logger.warning(f"Alternative method not found: {action.alternative_method}")
            return self._handle_skip(context)
        
        try:
            logger.info(f"Using alternative method: {action.alternative_method}")
            alternative_func = self.alternative_methods[action.alternative_method]
            return alternative_func(**context)
        except Exception as e:
            logger.error(f"Alternative method failed: {e}")
            return self._handle_skip(context)
    
    def _handle_degrade_quality(self, action: FallbackAction, context: Dict[str, Any]) -> Any:
        """Handle quality degradation strategy"""
        quality_level = action.quality_level or "low"
        
        logger.info(f"Degrading quality to: {quality_level}")
        
        # Modify context for lower quality processing
        degraded_context = context.copy()
        degraded_context['quality'] = quality_level
        
        # This would be implemented based on specific requirements
        # For example, reducing resolution, changing model, etc.
        
        return degraded_context
    
    def _handle_partial_success(self, context: Dict[str, Any]) -> Any:
        """Handle partial success strategy"""
        logger.info("Accepting partial success")
        
        # Store partial results
        with self._lock:
            if 'partial_successes' not in self.partial_results:
                self.partial_results['partial_successes'] = []
            self.partial_results['partial_successes'].append(context)
        
        return context.get('partial_result')
    
    def get_partial_results(self) -> Dict[str, Any]:
        """Get accumulated partial results"""
        with self._lock:
            return self.partial_results.copy()
    
    def clear_partial_results(self):
        """Clear partial results"""
        with self._lock:
            self.partial_results.clear()
    
    def process_retry_queue(self) -> List[Dict[str, Any]]:
        """Process items in retry queue that are ready"""
        current_time = time.time()
        ready_items = []
        
        with self._lock:
            retry_queue = self.partial_results.get('retry_queue', [])
            remaining_items = []
            
            for item in retry_queue:
                if current_time >= item['retry_after']:
                    if item['attempts'] < item['max_attempts']:
                        ready_items.append(item)
                    else:
                        logger.warning(f"Max retry attempts reached for: {item['context']}")
                else:
                    remaining_items.append(item)
            
            self.partial_results['retry_queue'] = remaining_items
        
        return ready_items


class RobustProcessor:
    """Wrapper for robust processing with fallback handling"""
    
    def __init__(self, degradation_manager: GracefulDegradationManager):
        self.degradation_manager = degradation_manager
    
    def process_with_fallback(
        self,
        operation_func: Callable,
        operation_name: str,
        context: Dict[str, Any] = None,
        required: bool = True
    ) -> tuple[Any, bool]:
        """
        Process operation with fallback handling
        Returns: (result, success)
        """
        context = context or {}
        context['operation'] = operation_name
        
        try:
            result = operation_func(**context)
            return result, True
            
        except Exception as error:
            logger.warning(f"Operation {operation_name} failed: {error}")
            
            if required:
                # Try fallback for required operations
                fallback_action = self.degradation_manager.handle_error(error, context)
                fallback_result = self.degradation_manager.execute_fallback(fallback_action, context)
                
                if fallback_result is not None:
                    return fallback_result, True
                else:
                    return None, False
            else:
                # For non-required operations, gracefully skip
                logger.info(f"Skipping non-required operation: {operation_name}")
                return None, True
    
    def process_batch_with_fallback(
        self,
        items: List[Any],
        operation_func: Callable,
        operation_name: str,
        min_success_rate: float = 0.5
    ) -> tuple[List[Any], float]:
        """
        Process batch of items with fallback handling
        Returns: (results, success_rate)
        """
        results = []
        successes = 0
        
        for i, item in enumerate(items):
            context = {
                'operation': operation_name,
                'item_index': i,
                'item': item
            }
            
            result, success = self.process_with_fallback(
                operation_func,
                f"{operation_name}_{i}",
                context,
                required=False
            )
            
            results.append(result)
            if success and result is not None:
                successes += 1
        
        success_rate = successes / len(items) if items else 0
        
        if success_rate < min_success_rate:
            logger.warning(
                f"Batch success rate {success_rate:.2%} below minimum {min_success_rate:.2%}"
            )
        
        return results, success_rate


# Global instances
degradation_manager = GracefulDegradationManager()
robust_processor = RobustProcessor(degradation_manager)


def get_degradation_manager() -> GracefulDegradationManager:
    """Get global degradation manager instance"""
    return degradation_manager


def get_robust_processor() -> RobustProcessor:
    """Get global robust processor instance"""
    return robust_processor


def with_fallback(operation_name: str, required: bool = True):
    """Decorator for adding fallback handling to functions"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            context = {'args': args, 'kwargs': kwargs}
            
            def operation_func(**ctx):
                return func(*ctx['args'], **ctx['kwargs'])
            
            result, success = robust_processor.process_with_fallback(
                operation_func,
                operation_name,
                context,
                required
            )
            
            if not success and required:
                raise RuntimeError(f"Operation {operation_name} failed and no fallback succeeded")
            
            return result
        
        return wrapper
    return decorator