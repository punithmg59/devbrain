"""
Structured logging configuration for DevBrain production readiness.

Provides consistent, structured logging across all services with correlation IDs,
performance tracking, and error context.
"""

import logging
import time
import uuid
from contextlib import contextmanager
from typing import Optional, Dict, Any
from functools import wraps


class StructuredLogger:
    """
    Structured logger with correlation IDs and context tracking.
    
    Provides consistent logging format across all services with:
    - Correlation IDs for request tracing
    - Performance tracking
    - Structured context
    - Error context
    """
    
    def __init__(self, name: str):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name (typically __name__)
        """
        self.logger = logging.getLogger(name)
        self._correlation_id: Optional[str] = None
        self._context: Dict[str, Any] = {}
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for request tracing."""
        self._correlation_id = correlation_id
    
    def add_context(self, key: str, value: Any):
        """Add context to all log messages."""
        self._context[key] = value
    
    def clear_context(self):
        """Clear all context."""
        self._context.clear()
    
    def _format_message(self, message: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """Format message with correlation ID and context."""
        parts = []
        
        if self._correlation_id:
            parts.append(f"[correlation_id={self._correlation_id}]")
        
        if self._context:
            context_str = ", ".join(f"{k}={v}" for k, v in self._context.items())
            parts.append(f"[{context_str}]")
        
        if extra:
            extra_str = ", ".join(f"{k}={v}" for k, v in extra.items())
            parts.append(f"[{extra_str}]")
        
        if parts:
            return f"{' '.join(parts)} {message}"
        return message
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(self._format_message(message, kwargs))
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(self._format_message(message, kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(self._format_message(message, kwargs))
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(self._format_message(message, kwargs))
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(self._format_message(message, kwargs))
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(self._format_message(message, kwargs))


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)


@contextmanager
def log_context(logger: StructuredLogger, **context):
    """
    Context manager for adding temporary logging context.
    
    Args:
        logger: StructuredLogger instance
        **context: Context key-value pairs
        
    Example:
        with log_context(logger, repo_id="123", user_id="456"):
            logger.info("Processing request")
    """
    old_context = logger._context.copy()
    
    for key, value in context.items():
        logger.add_context(key, value)
    
    try:
        yield
    finally:
        logger._context = old_context


def log_performance(logger: StructuredLogger, operation: str):
    """
    Decorator to log function performance.
    
    Args:
        logger: StructuredLogger instance
        operation: Operation name for logging
        
    Example:
        @log_performance(logger, "database_query")
        def fetch_data():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            correlation_id = str(uuid.uuid4())
            logger.set_correlation_id(correlation_id)
            
            try:
                logger.info(f"{operation} started")
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000
                logger.info(f"{operation} completed", elapsed_ms=f"{elapsed_ms:.2f}ms")
                return result
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                logger.error(f"{operation} failed", error=str(e), elapsed_ms=f"{elapsed_ms:.2f}ms")
                raise
            finally:
                logger.set_correlation_id(None)
        
        return wrapper
    return decorator


def configure_structured_logging():
    """
    Configure structured logging for the application.
    
    Sets up consistent formatting and handlers for all loggers.
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if needed)
    # file_handler = logging.FileHandler('devbrain.log')
    # file_handler.setLevel(logging.DEBUG)
    # file_handler.setFormatter(formatter)
    # root_logger.addHandler(file_handler)
    
    logging.info("Structured logging configured")
