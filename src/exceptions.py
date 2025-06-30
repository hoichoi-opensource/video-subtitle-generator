"""
Custom exceptions for Video Subtitle Generator
Production-grade error handling with detailed error information
"""

from typing import Dict, Any, Optional
import traceback
from datetime import datetime


class BaseSubtitleError(Exception):
    """Base exception for all subtitle generation errors"""
    
    def __init__(self, message: str, error_code: str = None, context: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.timestamp = datetime.utcnow().isoformat()
        self.traceback = traceback.format_exc()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging"""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp,
            'traceback': self.traceback
        }


class ConfigurationError(BaseSubtitleError):
    """Configuration-related errors"""
    pass


class ValidationError(BaseSubtitleError):
    """Input validation errors"""
    pass


class VideoProcessingError(BaseSubtitleError):
    """Video processing and chunking errors"""
    pass


class CloudStorageError(BaseSubtitleError):
    """Google Cloud Storage related errors"""
    pass


class VertexAIError(BaseSubtitleError):
    """Vertex AI related errors"""
    pass


class SubtitleGenerationError(BaseSubtitleError):
    """Subtitle generation specific errors"""
    pass


class NetworkError(BaseSubtitleError):
    """Network and connectivity errors"""
    pass


class ResourceError(BaseSubtitleError):
    """Resource exhaustion errors (memory, disk, etc.)"""
    pass


class AuthenticationError(BaseSubtitleError):
    """Authentication and authorization errors"""
    pass


class QuotaExceededError(BaseSubtitleError):
    """API quota and rate limit errors"""
    pass


class RetryableError(BaseSubtitleError):
    """Errors that can be retried"""
    
    def __init__(self, message: str, retry_after: int = None, max_retries: int = 3, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        self.max_retries = max_retries


class NonRetryableError(BaseSubtitleError):
    """Errors that should not be retried"""
    pass


# Error categories for different handling strategies
RETRYABLE_ERRORS = (
    NetworkError,
    CloudStorageError,
    QuotaExceededError,
    RetryableError
)

NON_RETRYABLE_ERRORS = (
    ConfigurationError,
    ValidationError,
    AuthenticationError,
    NonRetryableError
)