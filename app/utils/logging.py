"""
Structured logging utility module with JSON formatting, log rotation, and contextual logging capabilities.
"""

import logging
import json
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON-structured logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger_name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line_number": record.lineno,
        }
        
        # Add optional context fields from extra
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'session_id'):
            log_entry["session_id"] = record.session_id
        if hasattr(record, 'api_key_id'):
            log_entry["api_key_id"] = record.api_key_id
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add any additional fields from record
        for key, value in record.__dict__.items():
            if key not in log_entry and not key.startswith('_'):
                try:
                    json.dumps(value)  # Test if value is JSON serializable
                    log_entry[key] = value
                except (TypeError, ValueError):
                    log_entry[key] = str(value)
        
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_json: bool = True,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up structured logging with console and optional file output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        enable_json: Whether to use JSON formatting
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    
    Returns:
        Configured logger instance
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Create file handler if specified
    handlers = [console_handler]
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        handlers.append(file_handler)
    
    # Apply formatter
    if enable_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    for handler in handlers:
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance with specified name.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding contextual information to logs."""
    
    def __init__(self, **kwargs):
        """Initialize with context fields."""
        self.context = kwargs
        self.adapter = None
    
    def __enter__(self):
        """Enter context and create logger adapter."""
        logger = logging.getLogger()
        self.adapter = logging.LoggerAdapter(logger, self.context)
        return self.adapter
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        self.adapter = None


def log_exception(logger: logging.Logger, exception: Exception, context: Optional[Dict[str, Any]] = None):
    """
    Log exception with full traceback and context.
    
    Args:
        logger: Logger instance
        exception: Exception to log
        context: Optional context information
    """
    extra = context or {}
    logger.error(
        f"Exception occurred: {str(exception)}",
        exc_info=True,
        extra=extra
    )


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration: float,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log performance metrics.
    
    Args:
        logger: Logger instance
        operation: Operation name
        duration: Duration in seconds
        metadata: Optional metadata
    """
    extra = metadata or {}
    extra.update({
        "operation": operation,
        "duration_seconds": duration,
        "duration_ms": duration * 1000
    })
    
    logger.info(
        f"Performance: {operation} completed in {duration:.3f}s",
        extra=extra
    )


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration: float,
    request_id: Optional[str] = None,
    api_key_id: Optional[str] = None,
    **kwargs
):
    """
    Log API request details.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration: Request duration in seconds
        request_id: Optional request ID
        api_key_id: Optional API key ID
        **kwargs: Additional context
    """
    extra = kwargs.copy()
    extra.update({
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_seconds": duration,
        "duration_ms": duration * 1000
    })
    
    if request_id:
        extra["request_id"] = request_id
    if api_key_id:
        extra["api_key_id"] = api_key_id
    
    logger.info(
        f"API Request: {method} {path} -> {status_code} ({duration:.3f}s)",
        extra=extra
    )
