"""
Validation utilities for API request processing.
"""
import re
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from pydantic import ValidationError

from app.core.config import get_settings


class ValidationException(Exception):
    """Custom validation exception with detailed error messages and recovery suggestions."""
    
    def __init__(self, message: str, field: Optional[str] = None, recovery_suggestions: Optional[List[str]] = None):
        self.message = message
        self.field = field
        self.recovery_suggestions = recovery_suggestions or []
        super().__init__(message)


def validate_query_text(query_text: str) -> str:
    """
    Validate and sanitize query text with length limits, content filtering, and sanitization.
    
    Args:
        query_text: The query text to validate
        
    Returns:
        The sanitized query text
        
    Raises:
        ValidationException: If query text is invalid
    """
    settings = get_settings()
    max_length = getattr(settings, 'api_max_query_length', 1000)
    
    # Check if query text is provided
    if not query_text:
        raise ValidationException(
            "Query text is required and cannot be empty",
            field="query",
            recovery_suggestions=["Provide a non-empty query string"]
        )
    
    # Strip whitespace and normalize
    query_text = query_text.strip()
    
    # Check minimum length
    if len(query_text) < 3:
        raise ValidationException(
            "Query text must be at least 3 characters long",
            field="query",
            recovery_suggestions=["Provide a more descriptive query with at least 3 characters"]
        )
    
    # Check maximum length
    if len(query_text) > max_length:
        raise ValidationException(
            f"Query text must not exceed {max_length} characters (current: {len(query_text)})",
            field="query",
            recovery_suggestions=[f"Shorten your query to under {max_length} characters"]
        )
    
    # Basic content filtering - remove potentially harmful content
    query_text = sanitize_input(query_text)
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'data:text/html',  # Data URLs
        r'vbscript:',  # VBScript URLs
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, query_text, re.IGNORECASE):
            raise ValidationException(
                "Query contains potentially harmful content",
                field="query",
                recovery_suggestions=["Remove script tags and suspicious URLs from your query"]
            )
    
    return query_text


def validate_processing_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate processing configuration with constraint checking.
    
    Args:
        config: Processing configuration dictionary
        
    Returns:
        Validated and normalized configuration
        
    Raises:
        ValidationException: If configuration is invalid
    """
    if not config:
        return {}
    
    # Define valid configuration keys and their constraints
    valid_keys = {
        'timeout_seconds': {'type': int, 'min': 10, 'max': 600},
        'max_retries': {'type': int, 'min': 0, 'max': 5},
        'concurrency': {'type': int, 'min': 1, 'max': 10},
        'enable_content_cleaning': {'type': bool},
        'enable_ai_analysis': {'type': bool},
        'enable_summarization': {'type': bool},
        'enable_structured_extraction': {'type': bool},
        'enable_duplicate_detection': {'type': bool},
        'similarity_threshold': {'type': float, 'min': 0.5, 'max': 0.95},
        'min_content_quality_score': {'type': float, 'min': 0.0, 'max': 1.0},
        'max_summary_length': {'type': int, 'min': 100, 'max': 2000},
        'batch_size': {'type': int, 'min': 1, 'max': 50}
    }
    
    validated_config = {}
    
    for key, value in config.items():
        if key not in valid_keys:
            raise ValidationException(
                f"Unknown configuration key: {key}",
                field=f"processing_config.{key}",
                recovery_suggestions=[f"Remove '{key}' or use one of: {', '.join(valid_keys.keys())}"]
            )
        
        constraints = valid_keys[key]
        expected_type = constraints['type']
        
        # Type validation
        if not isinstance(value, expected_type):
            raise ValidationException(
                f"Configuration '{key}' must be of type {expected_type.__name__}, got {type(value).__name__}",
                field=f"processing_config.{key}",
                recovery_suggestions=[f"Provide a {expected_type.__name__} value for '{key}'"]
            )
        
        # Range validation for numeric types
        if expected_type in (int, float):
            if 'min' in constraints and value < constraints['min']:
                raise ValidationException(
                    f"Configuration '{key}' must be at least {constraints['min']}, got {value}",
                    field=f"processing_config.{key}",
                    recovery_suggestions=[f"Set '{key}' to at least {constraints['min']}"]
                )
            
            if 'max' in constraints and value > constraints['max']:
                raise ValidationException(
                    f"Configuration '{key}' must be at most {constraints['max']}, got {value}",
                    field=f"processing_config.{key}",
                    recovery_suggestions=[f"Set '{key}' to at most {constraints['max']}"]
                )
        
        validated_config[key] = value
    
    # Cross-validation checks
    if 'concurrency' in validated_config and 'batch_size' in validated_config:
        if validated_config['batch_size'] > validated_config['concurrency'] * 5:
            raise ValidationException(
                "Batch size should not exceed concurrency * 5 for optimal performance",
                field="processing_config",
                recovery_suggestions=["Reduce batch_size or increase concurrency"]
            )
    
    return validated_config


def sanitize_input(text: str) -> str:
    """
    Sanitize input text to prevent injection attacks.
    
    Args:
        text: Input text to sanitize
        
    Returns:
        Sanitized text
    """
    if not text:
        return text
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Remove or escape HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove potentially harmful characters
    text = re.sub(r'[^\w\s\-.,!?:;()\[\]{}@#$%&*+=|\\/"\'`~]', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def validate_url_list(urls: List[str]) -> List[str]:
    """
    Validate optional URL lists in requests.
    
    Args:
        urls: List of URLs to validate
        
    Returns:
        List of validated URLs
        
    Raises:
        ValidationException: If any URL is invalid
    """
    if not urls:
        return []
    
    if len(urls) > 50:
        raise ValidationException(
            "URL list cannot contain more than 50 URLs",
            field="urls",
            recovery_suggestions=["Reduce the number of URLs to 50 or fewer"]
        )
    
    validated_urls = []
    
    for i, url in enumerate(urls):
        if not isinstance(url, str):
            raise ValidationException(
                f"URL at index {i} must be a string",
                field=f"urls[{i}]",
                recovery_suggestions=["Provide URLs as strings"]
            )
        
        url = url.strip()
        
        if not url:
            continue  # Skip empty URLs
        
        # Basic URL validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValidationException(
                    f"Invalid URL format at index {i}: {url}",
                    field=f"urls[{i}]",
                    recovery_suggestions=["Provide valid URLs with scheme (http/https) and domain"]
                )
            
            if parsed.scheme not in ('http', 'https'):
                raise ValidationException(
                    f"URL at index {i} must use http or https scheme: {url}",
                    field=f"urls[{i}]",
                    recovery_suggestions=["Use http:// or https:// URLs only"]
                )
            
            validated_urls.append(url)
            
        except Exception as e:
            raise ValidationException(
                f"Invalid URL at index {i}: {str(e)}",
                field=f"urls[{i}]",
                recovery_suggestions=["Provide a valid URL format"]
            )
    
    return validated_urls


def check_rate_limits(client_ip: str, endpoint: str = "scrape") -> bool:
    """
    Basic rate limiting validation (placeholder for future implementation).
    
    Args:
        client_ip: Client IP address
        endpoint: API endpoint being accessed
        
    Returns:
        True if request is within rate limits
        
    Raises:
        ValidationException: If rate limit is exceeded
    """
    # TODO: Implement actual rate limiting with Redis or in-memory store
    # For now, this is a placeholder that always returns True
    
    settings = get_settings()
    rate_limit = getattr(settings, 'api_rate_limit_requests_per_minute', 60)
    
    # This would normally check against a rate limiting store
    # For now, we'll just validate the inputs
    if not client_ip:
        return True  # Skip rate limiting if IP is not available
    
    # Placeholder logic - in production this would check actual request counts
    return True


def validate_request_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate request metadata.
    
    Args:
        metadata: Request metadata dictionary
        
    Returns:
        Validated metadata
        
    Raises:
        ValidationException: If metadata is invalid
    """
    if not metadata:
        return {}
    
    validated_metadata = {}
    
    # Validate specific metadata fields
    if 'request_id' in metadata:
        request_id = metadata['request_id']
        if not isinstance(request_id, str) or len(request_id) > 100:
            raise ValidationException(
                "request_id must be a string with maximum length of 100",
                field="metadata.request_id",
                recovery_suggestions=["Provide a valid request ID string"]
            )
        validated_metadata['request_id'] = sanitize_input(request_id)
    
    if 'session_id' in metadata:
        session_id = metadata['session_id']
        if not isinstance(session_id, str) or len(session_id) > 100:
            raise ValidationException(
                "session_id must be a string with maximum length of 100",
                field="metadata.session_id",
                recovery_suggestions=["Provide a valid session ID string"]
            )
        validated_metadata['session_id'] = sanitize_input(session_id)
    
    if 'additional_context' in metadata:
        context = metadata['additional_context']
        if not isinstance(context, dict):
            raise ValidationException(
                "additional_context must be a dictionary",
                field="metadata.additional_context",
                recovery_suggestions=["Provide additional context as a dictionary"]
            )
        # Limit context size
        if len(str(context)) > 1000:
            raise ValidationException(
                "additional_context is too large (max 1000 characters when serialized)",
                field="metadata.additional_context",
                recovery_suggestions=["Reduce the size of additional context data"]
            )
        validated_metadata['additional_context'] = context
    
    return validated_metadata
