"""
Pydantic schemas for scraper data structures.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator
from datetime import datetime


class DiscoveryMethod(str, Enum):
    """Enumeration of site discovery methods."""
    LLM_GENERATED = "llm_generated"
    RULE_BASED = "rule_based"
    SEARCH_ENGINE = "search_engine"
    USER_PROVIDED = "user_provided"
    REFERRAL = "referral"


class ContentType(str, Enum):
    """Enumeration of content types."""
    ARTICLE = "article"
    PRODUCT_PAGE = "product_page"
    DOCUMENTATION = "documentation"
    BLOG_POST = "blog_post"
    NEWS_ARTICLE = "news_article"
    GENERAL = "general"


class ErrorType(str, Enum):
    """Enumeration of scraping error types."""
    HTTP_ERROR = "http_error"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    PARSE_ERROR = "parse_error"
    ROBOTS_DISALLOWED = "robots_disallowed"
    RATE_LIMITED = "rate_limited"
    CONTENT_TOO_LARGE = "content_too_large"
    UNKNOWN = "unknown"


class ScrapedContent(BaseModel):
    """Schema for scraped content from websites."""
    url: HttpUrl = Field(..., description="Source URL of the scraped content")
    title: Optional[str] = Field(None, description="Page title")
    content: str = Field(..., description="Main content text")
    content_type: ContentType = Field(default=ContentType.GENERAL, description="Type of content")
    
    # Metadata
    author: Optional[str] = Field(None, description="Content author")
    publish_date: Optional[datetime] = Field(None, description="Publication date")
    description: Optional[str] = Field(None, description="Page description")
    keywords: Optional[List[str]] = Field(None, description="Page keywords")
    
    # Media and links
    images: Optional[List[Dict[str, str]]] = Field(None, description="List of images with alt text and URLs")
    links: Optional[List[Dict[str, str]]] = Field(None, description="List of links with text and URLs")
    
    # Processing info
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the content was scraped")
    processing_time: float = Field(..., ge=0.0, description="Time taken to scrape in seconds")
    content_size_bytes: int = Field(..., ge=0, description="Size of scraped content in bytes")
    
    # Quality metrics
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relevance score for the query")
    content_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Quality score of the content")
    
    # Extraction info
    extraction_method: str = Field(..., description="Method used to extract content")
    fallback_used: bool = Field(default=False, description="Whether fallback extraction was used")
    
    @validator("content")
    def validate_content_not_empty(cls, v):
        """Ensure content is not empty."""
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()
    
    @validator("content_size_bytes")
    def validate_content_size(cls, v):
        """Ensure content size is reasonable."""
        if v > 104857600:  # 100MB
            raise ValueError("Content size too large")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://example.com/article",
                "title": "Sample Article Title",
                "content": "This is the main content of the article...",
                "content_type": "article",
                "author": "John Doe",
                "publish_date": "2024-01-01T12:00:00Z",
                "description": "A sample article description",
                "keywords": ["sample", "article", "example"],
                "images": [{"url": "https://example.com/image.jpg", "alt": "Sample image"}],
                "links": [{"url": "https://example.com/link", "text": "Sample link"}],
                "timestamp": "2024-01-01T12:00:00Z",
                "processing_time": 2.5,
                "content_size_bytes": 2048,
                "relevance_score": 0.85,
                "content_quality_score": 0.9,
                "extraction_method": "beautifulsoup_primary",
                "fallback_used": False
            }
        }
    }


class DiscoveryResult(BaseModel):
    """Schema for site discovery results."""
    url: HttpUrl = Field(..., description="Discovered website URL")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score for the query")
    domain: str = Field(..., description="Domain of the discovered site")
    discovery_method: DiscoveryMethod = Field(..., description="Method used to discover the site")
    
    # Additional metadata
    title: Optional[str] = Field(None, description="Site title if available")
    description: Optional[str] = Field(None, description="Site description if available")
    category: Optional[str] = Field(None, description="Site category")
    
    # Discovery context
    query_terms: Optional[List[str]] = Field(None, description="Query terms that led to this discovery")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the discovery")
    
    # Timestamp
    discovered_at: datetime = Field(default_factory=datetime.utcnow, description="When the site was discovered")
    
    @validator("domain")
    def extract_domain_from_url(cls, v, values):
        """Extract domain from URL if not provided."""
        if "url" in values:
            from urllib.parse import urlparse
            parsed = urlparse(str(values["url"]))
            return parsed.netloc.lower()
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://example.com",
                "relevance_score": 0.9,
                "domain": "example.com",
                "discovery_method": "llm_generated",
                "title": "Example Website",
                "description": "A sample website for demonstration",
                "category": "technology",
                "query_terms": ["AI tools", "machine learning"],
                "confidence": 0.85,
                "discovered_at": "2024-01-01T12:00:00Z"
            }
        }
    }


class ScrapingRequest(BaseModel):
    """Schema for scraping request input validation."""
    url: HttpUrl = Field(..., description="URL to scrape")
    extraction_options: Optional[Dict[str, Any]] = Field(None, description="Custom extraction options")
    retry_settings: Optional[Dict[str, Any]] = Field(None, description="Retry configuration")
    timeout_seconds: Optional[int] = Field(None, ge=5, le=120, description="Custom timeout for this request")
    
    # Content preferences
    include_images: bool = Field(default=True, description="Whether to extract images")
    include_links: bool = Field(default=True, description="Whether to extract links")
    max_content_length: Optional[int] = Field(None, ge=1000, le=104857600, description="Maximum content length to extract")
    
    # Processing options
    clean_html: bool = Field(default=True, description="Whether to clean HTML tags from content")
    extract_metadata: bool = Field(default=True, description="Whether to extract metadata")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://example.com/article",
                "extraction_options": {"prefer_article_tags": True},
                "retry_settings": {"max_retries": 2},
                "timeout_seconds": 30,
                "include_images": True,
                "include_links": True,
                "max_content_length": 10000,
                "clean_html": True,
                "extract_metadata": True
            }
        }
    }


class ScrapingError(BaseModel):
    """Schema for structured error reporting."""
    error_type: ErrorType = Field(..., description="Type of error that occurred")
    message: str = Field(..., description="Human-readable error message")
    url: HttpUrl = Field(..., description="URL that caused the error")
    
    # Error details
    status_code: Optional[int] = Field(None, description="HTTP status code if applicable")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts made")
    max_retries: int = Field(default=3, description="Maximum retry attempts allowed")
    
    # Context
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the error occurred")
    processing_time: Optional[float] = Field(None, ge=0.0, description="Time spent before error occurred")
    
    # Technical details
    exception_type: Optional[str] = Field(None, description="Python exception type if applicable")
    exception_details: Optional[str] = Field(None, description="Additional exception details")
    
    # Recovery suggestions
    can_retry: bool = Field(default=True, description="Whether the request can be retried")
    suggested_delay: Optional[float] = Field(None, description="Suggested delay before retry in seconds")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error_type": "http_error",
                "message": "Page not found",
                "url": "https://example.com/404",
                "status_code": 404,
                "retry_count": 1,
                "max_retries": 3,
                "timestamp": "2024-01-01T12:00:00Z",
                "processing_time": 1.5,
                "exception_type": "aiohttp.ClientResponseError",
                "can_retry": False,
                "suggested_delay": None
            }
        }
    }


class ScrapingException(Exception):
    """Exception class that can be raised, containing a ScrapingError model."""
    
    def __init__(self, error: ScrapingError):
        self.error = error
        super().__init__(error.message)
    
    def __str__(self):
        return f"{self.error.error_type.value}: {self.error.message} for {self.error.url}"


class ContentExtractionConfig(BaseModel):
    """Schema for configurable content extraction parameters."""
    # Primary extraction strategy
    prefer_article_tags: bool = Field(default=True, description="Prefer article tags for content")
    prefer_main_content: bool = Field(default=True, description="Prefer main content areas")
    
    # Fallback strategies
    enable_json_ld: bool = Field(default=True, description="Enable JSON-LD structured data extraction")
    enable_open_graph: bool = Field(default=True, description="Enable Open Graph meta tag extraction")
    enable_generic_extraction: bool = Field(default=True, description="Enable generic text extraction")
    
    # Content filtering
    min_content_length: int = Field(default=100, description="Minimum content length to consider valid")
    max_content_length: int = Field(default=10485760, description="Maximum content length to extract")
    
    # HTML cleaning
    remove_ads: bool = Field(default=True, description="Remove advertisement content")
    remove_navigation: bool = Field(default=True, description="Remove navigation elements")
    remove_footers: bool = Field(default=True, description="Remove footer content")
    
    # Text processing
    normalize_whitespace: bool = Field(default=True, description="Normalize whitespace in content")
    remove_duplicate_lines: bool = Field(default=True, description="Remove duplicate lines")
    
    # Media extraction
    include_images: bool = Field(default=True, description="Whether to extract images")
    include_links: bool = Field(default=True, description="Whether to extract links")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "prefer_article_tags": True,
                "prefer_main_content": True,
                "enable_json_ld": True,
                "enable_open_graph": True,
                "enable_generic_extraction": True,
                "min_content_length": 100,
                "max_content_length": 10485760,
                "remove_ads": True,
                "remove_navigation": True,
                "remove_footers": True,
                "normalize_whitespace": True,
                "remove_duplicate_lines": True
            }
        }
    }


class SiteDiscoveryConfig(BaseModel):
    """Schema for discovery agent configuration."""
    # Discovery strategies
    enable_llm_discovery: bool = Field(default=True, description="Enable LLM-powered site discovery")
    enable_rule_based_discovery: bool = Field(default=True, description="Enable rule-based discovery")
    enable_search_engine: bool = Field(default=False, description="Enable search engine integration")
    
    # LLM configuration
    llm_temperature: float = Field(default=0.3, ge=0.0, le=1.0, description="Temperature for LLM discovery")
    max_discovery_results: int = Field(default=20, ge=1, le=100, description="Maximum number of sites to discover")
    
    # Rule-based discovery
    domain_patterns: Optional[Dict[str, List[str]]] = Field(None, description="Domain patterns for different categories")
    trusted_domains: Optional[List[str]] = Field(None, description="List of trusted domains to prioritize")
    
    # Quality filtering
    min_relevance_score: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum relevance score for discovery")
    max_domain_age_days: Optional[int] = Field(None, description="Maximum age of domains to consider")
    
    # Rate limiting
    discovery_delay_seconds: float = Field(default=0.5, ge=0.1, le=5.0, description="Delay between discovery requests")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "enable_llm_discovery": True,
                "enable_rule_based_discovery": True,
                "enable_search_engine": False,
                "llm_temperature": 0.3,
                "max_discovery_results": 20,
                "domain_patterns": {
                    "ai_tools": ["producthunt.com", "github.com"],
                    "mutual_funds": ["morningstar.com", "vanguard.com"]
                },
                "trusted_domains": ["example.com", "trusted-site.com"],
                "min_relevance_score": 0.3,
                "max_domain_age_days": 3650,
                "discovery_delay_seconds": 0.5
            }
        }
    }
