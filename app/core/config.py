"""
Application configuration using Pydantic Settings.
"""
from typing import List, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = {
        "populate_by_name": True
    }
    
    # MongoDB Configuration
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI"
    )
    mongodb_db: str = Field(
        default="traycer_try",
        description="MongoDB database name"
    )
    
    # MongoDB Connection Pool Settings
    mongodb_max_pool_size: int = Field(
        default=10,
        description="Maximum number of connections in the pool"
    )
    mongodb_min_pool_size: int = Field(
        default=1,
        description="Minimum number of connections in the pool"
    )
    mongodb_max_idle_time_ms: int = Field(
        default=30000,
        description="Maximum time a connection can remain idle in milliseconds"
    )
    mongodb_server_selection_timeout_ms: int = Field(
        default=5000,
        description="Server selection timeout in milliseconds"
    )
    mongodb_connect_timeout_ms: int = Field(
        default=10000,
        description="Connection timeout in milliseconds"
    )
    
    # Google Gemini API
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key (required for AI functionality)"
    )
    
    # Gemini Configuration
    gemini_temperature: float = Field(
        default=0.1,
        description="Temperature for Gemini LLM responses (0.0-1.0)"
    )
    gemini_max_tokens: int = Field(
        default=1000,
        description="Maximum tokens for Gemini responses"
    )
    gemini_max_content_length: int = Field(
        default=4000,
        description="Maximum content length for Gemini API calls in characters"
    )
    gemini_max_similarity_content_length: int = Field(
        default=1000,
        description="Maximum content length for similarity analysis in characters"
    )
    
    # Agent Configuration
    agent_timeout_seconds: int = Field(
        default=30,
        description="Default timeout for agent operations in seconds"
    )
    parser_timeout_seconds: int = Field(
        default=45,
        description="Timeout for natural language parser operations in seconds"
    )
    categorizer_timeout_seconds: int = Field(
        default=30,
        description="Timeout for domain categorizer operations in seconds"
    )
    processor_timeout_seconds: int = Field(
        default=60,
        description="Timeout for query processor operations in seconds"
    )
    agent_max_retries: int = Field(
        default=3,
        description="Maximum retries for failed LLM calls"
    )
    agent_confidence_threshold: float = Field(
        default=0.7,
        description="Confidence threshold for categorization (0.0-1.0)"
    )
    
    # Scraper Configuration
    scraper_concurrency: int = Field(
        default=5,
        description="Maximum concurrent requests for web scraping"
    )
    scraper_request_timeout_seconds: int = Field(
        default=20,
        description="Request timeout for web scraping in seconds"
    )
    scraper_delay_seconds: float = Field(
        default=1.0,
        description="Delay between requests in seconds"
    )
    scraper_user_agent: str = Field(
        default="TrayceAI-Bot/1.0",
        description="User agent string for web scraping"
    )
    scraper_respect_robots: bool = Field(
        default=True,
        description="Whether to respect robots.txt files"
    )
    scraper_max_retries: int = Field(
        default=3,
        description="Maximum retries for failed requests"
    )
    scraper_max_redirects: int = Field(
        default=5,
        description="Maximum redirects to follow"
    )
    scraper_content_size_limit: int = Field(
        default=10485760,
        description="Maximum content size to download in bytes (10MB)"
    )
    
    # Processing Configuration
    processing_timeout_seconds: int = Field(
        default=60,
        description="Overall processing timeout in seconds"
    )
    processing_max_retries: int = Field(
        default=2,
        description="Maximum retries for processing operations"
    )
    processing_concurrency: int = Field(
        default=3,
        description="Parallel processing operations"
    )
    processing_enable_content_cleaning: bool = Field(
        default=True, alias="ENABLE_CONTENT_CLEANING",
        description="Enable content cleaning stage"
    )
    processing_enable_ai_analysis: bool = Field(
        default=True, alias="ENABLE_AI_ANALYSIS",
        description="Enable AI analysis stage"
    )
    processing_enable_summarization: bool = Field(
        default=True, alias="ENABLE_SUMMARIZATION",
        description="Enable summarization stage"
    )
    processing_enable_structured_extraction: bool = Field(
        default=True, alias="ENABLE_STRUCTURED_EXTRACTION",
        description="Enable structured data extraction"
    )
    processing_enable_duplicate_detection: bool = Field(
        default=True, alias="ENABLE_DUPLICATE_DETECTION",
        description="Enable duplicate detection"
    )
    processing_similarity_threshold: float = Field(
        default=0.8, alias="SIMILARITY_THRESHOLD",
        description="Duplicate detection sensitivity"
    )
    processing_min_content_quality_score: float = Field(
        default=0.4, alias="MIN_CONTENT_QUALITY_SCORE",
        description="Minimum quality score for processing"
    )
    processing_max_summary_length: int = Field(
        default=500, alias="MAX_SUMMARY_LENGTH",
        description="Maximum summary length"
    )
    processing_batch_size: int = Field(
        default=10,
        description="Batch processing size"
    )
    processing_content_timeout: int = Field(
        default=30, alias="CONTENT_PROCESSING_TIMEOUT",
        description="Timeout for individual content processing"
    )
    processing_max_concurrent_ai_analyses: int = Field(
        default=3, alias="MAX_CONCURRENT_AI_ANALYSES",
        description="Maximum concurrent AI analysis operations"
    )
    processing_memory_threshold_mb: int = Field(
        default=512, alias="MAX_PROCESSING_MEMORY",
        description="Memory threshold in MB for batch processing"
    )
    processing_max_similarity_content_pairs: int = Field(
        default=50,
        description="Maximum content pairs for similarity analysis"
    )
    processing_max_similarity_batch_size: int = Field(
        default=10,
        description="Maximum batch size for similarity analysis"
    )
    
    # Database Configuration
    database_query_timeout_seconds: int = Field(
        default=30,
        description="Database operation timeouts in seconds"
    )
    database_max_retries: int = Field(
        default=3,
        description="Maximum retries for failed database operations"
    )
    database_batch_size: int = Field(
        default=100,
        description="Batch size for bulk database operations"
    )
    database_enable_text_search: bool = Field(
        default=True,
        description="Enable full-text search features"
    )
    database_content_ttl_days: int = Field(
        default=90,
        description="Automatic content cleanup TTL in days"
    )
    database_analytics_retention_days: int = Field(
        default=365,
        description="Analytics data retention period in days"
    )
    database_enable_caching: bool = Field(
        default=True,
        description="Enable query result caching"
    )
    database_cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache expiration time in seconds"
    )
    database_max_content_size_mb: int = Field(
        default=50,
        description="Maximum individual document size in MB"
    )
    database_enable_compression: bool = Field(
        default=True,
        description="Enable content compression for storage"
    )
    database_index_background: bool = Field(
        default=True,
        description="Create indexes in background mode"
    )
    database_enable_profiling: bool = Field(
        default=False,
        description="Enable query profiling for development"
    )
    
    # Health Check Settings
    health_agent_test_timeout: int = Field(
        default=5,
        description="Timeout for individual agent tests in health checks (seconds)"
    )
    health_processing_test_timeout: int = Field(
        default=8,
        description="Timeout for processing tests in health checks (seconds)"
    )
    
    # Application Settings
    environment: str = Field(
        default="development",
        description="Application environment"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    debug: bool = Field(
        default=True,
        description="Debug mode"
    )
    
    # Security
    secret_key: str = Field(
        default="change_me_in_production",
        description="Secret key for security operations"
    )
    
    # CORS Settings
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Comma-separated list of allowed origins"
    )
    
    # Field validators with consistent error message format
    @field_validator("mongodb_max_pool_size")
    @classmethod
    def validate_mongodb_max_pool_size(cls, v: int) -> int:
        """Validate that MongoDB max pool size is between 1 and 100."""
        if not 1 <= v <= 100:
            raise ValueError("mongodb_max_pool_size must be between 1 and 100")
        return v
    
    @field_validator("mongodb_min_pool_size")
    @classmethod
    def validate_mongodb_min_pool_size(cls, v: int) -> int:
        """Validate that MongoDB min pool size is between 1 and 50."""
        if not 1 <= v <= 50:
            raise ValueError("mongodb_min_pool_size must be between 1 and 50")
        return v
    
    @field_validator("mongodb_max_idle_time_ms")
    @classmethod
    def validate_mongodb_max_idle_time_ms(cls, v: int) -> int:
        """Validate that MongoDB max idle time is between 1000 and 300000 milliseconds."""
        if not 1000 <= v <= 300000:
            raise ValueError("mongodb_max_idle_time_ms must be between 1000 and 300000")
        return v
    
    @field_validator("mongodb_server_selection_timeout_ms")
    @classmethod
    def validate_mongodb_server_selection_timeout_ms(cls, v: int) -> int:
        """Validate that MongoDB server selection timeout is between 1000 and 60000 milliseconds."""
        if not 1000 <= v <= 60000:
            raise ValueError("mongodb_server_selection_timeout_ms must be between 1000 and 60000")
        return v
    
    @field_validator("mongodb_connect_timeout_ms")
    @classmethod
    def validate_mongodb_connect_timeout_ms(cls, v: int) -> int:
        """Validate that MongoDB connect timeout is between 1000 and 60000 milliseconds."""
        if not 1000 <= v <= 60000:
            raise ValueError("mongodb_connect_timeout_ms must be between 1000 and 60000")
        return v
    
    @field_validator("gemini_temperature")
    @classmethod
    def validate_gemini_temperature(cls, v: float) -> float:
        """Validate that Gemini temperature is between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("gemini_temperature must be between 0.0 and 1.0")
        return v
    
    @field_validator("gemini_max_tokens")
    @classmethod
    def validate_gemini_max_tokens(cls, v: int) -> int:
        """Validate that Gemini max tokens is between 100 and 10000."""
        if not 100 <= v <= 10000:
            raise ValueError("gemini_max_tokens must be between 100 and 10000")
        return v
    
    @field_validator("gemini_max_content_length")
    @classmethod
    def validate_gemini_max_content_length(cls, v: int) -> int:
        """Validate that Gemini max content length is between 100 and 10000 characters."""
        if not 100 <= v <= 10000:
            raise ValueError("gemini_max_content_length must be between 100 and 10000")
        return v
    
    @field_validator("gemini_max_similarity_content_length")
    @classmethod
    def validate_gemini_max_similarity_content_length(cls, v: int) -> int:
        """Validate that Gemini max similarity content length is between 100 and 5000 characters."""
        if not 100 <= v <= 5000:
            raise ValueError("gemini_max_similarity_content_length must be between 100 and 5000")
        return v
    
    @field_validator("agent_timeout_seconds")
    @classmethod
    def validate_agent_timeout_seconds(cls, v: int) -> int:
        """Validate that agent timeout is between 5 and 300 seconds."""
        if not 5 <= v <= 300:
            raise ValueError("agent_timeout_seconds must be between 5 and 300")
        return v
    
    @field_validator("parser_timeout_seconds")
    @classmethod
    def validate_parser_timeout_seconds(cls, v: int) -> int:
        """Validate that parser timeout is between 10 and 600 seconds."""
        if not 10 <= v <= 600:
            raise ValueError("parser_timeout_seconds must be between 10 and 600")
        return v
    
    @field_validator("categorizer_timeout_seconds")
    @classmethod
    def validate_categorizer_timeout_seconds(cls, v: int) -> int:
        """Validate that categorizer timeout is between 5 and 300 seconds."""
        if not 5 <= v <= 300:
            raise ValueError("categorizer_timeout_seconds must be between 5 and 300")
        return v
    
    @field_validator("processor_timeout_seconds")
    @classmethod
    def validate_processor_timeout_seconds(cls, v: int) -> int:
        """Validate that processor timeout is between 10 and 600 seconds."""
        if not 10 <= v <= 600:
            raise ValueError("processor_timeout_seconds must be between 10 and 600")
        return v
    
    @field_validator("agent_max_retries")
    @classmethod
    def validate_agent_max_retries(cls, v: int) -> int:
        """Validate that agent max retries is between 0 and 10."""
        if not 0 <= v <= 10:
            raise ValueError("agent_max_retries must be between 0 and 10")
        return v
    
    @field_validator("agent_confidence_threshold")
    @classmethod
    def validate_agent_confidence_threshold(cls, v: float) -> float:
        """Validate that agent confidence threshold is between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("agent_confidence_threshold must be between 0.0 and 1.0")
        return v
    
    @field_validator("scraper_concurrency")
    @classmethod
    def validate_scraper_concurrency(cls, v: int) -> int:
        """Validate that scraper concurrency is between 1 and 20."""
        if not 1 <= v <= 20:
            raise ValueError("scraper_concurrency must be between 1 and 20")
        return v
    
    @field_validator("scraper_request_timeout_seconds")
    @classmethod
    def validate_scraper_request_timeout_seconds(cls, v: int) -> int:
        """Validate that scraper request timeout is between 5 and 120 seconds."""
        if not 5 <= v <= 120:
            raise ValueError("scraper_request_timeout_seconds must be between 5 and 120")
        return v
    
    @field_validator("scraper_delay_seconds")
    @classmethod
    def validate_scraper_delay_seconds(cls, v: float) -> float:
        """Validate that scraper delay is between 0.1 and 10.0 seconds."""
        if not 0.1 <= v <= 10.0:
            raise ValueError("scraper_delay_seconds must be between 0.1 and 10.0")
        return v
    
    @field_validator("scraper_content_size_limit")
    @classmethod
    def validate_content_size_limit(cls, v: int) -> int:
        """Validate that content size limit is between 1MB and 100MB."""
        if not 1048576 <= v <= 104857600:
            raise ValueError("scraper_content_size_limit must be between 1MB and 100MB")
        return v
    
    @field_validator("scraper_max_retries")
    @classmethod
    def validate_scraper_max_retries(cls, v: int) -> int:
        """Validate that scraper max retries is between 0 and 10."""
        if not 0 <= v <= 10:
            raise ValueError("scraper_max_retries must be between 0 and 10")
        return v
    
    @field_validator("scraper_max_redirects")
    @classmethod
    def validate_scraper_max_redirects(cls, v: int) -> int:
        """Validate that scraper max redirects is between 0 and 20."""
        if not 0 <= v <= 20:
            raise ValueError("scraper_max_redirects must be between 0 and 20")
        return v
    
    # Processing configuration validators with consistent format
    @field_validator("processing_timeout_seconds")
    @classmethod
    def validate_processing_timeout_seconds(cls, v: int) -> int:
        """Validate that processing timeout is between 10 and 600 seconds."""
        if not 10 <= v <= 600:
            raise ValueError("processing_timeout_seconds must be between 10 and 600")
        return v
    
    @field_validator("processing_max_retries")
    @classmethod
    def validate_processing_max_retries(cls, v: int) -> int:
        """Validate that processing max retries is between 0 and 10."""
        if not 0 <= v <= 10:
            raise ValueError("processing_max_retries must be between 0 and 10")
        return v
    
    @field_validator("processing_concurrency")
    @classmethod
    def validate_processing_concurrency(cls, v: int) -> int:
        """Validate that processing concurrency is between 1 and 20."""
        if not 1 <= v <= 20:
            raise ValueError("processing_concurrency must be between 1 and 20")
        return v
    
    @field_validator("processing_similarity_threshold")
    @classmethod
    def validate_processing_similarity_threshold(cls, v: float) -> float:
        """Validate that processing similarity threshold is between 0.5 and 0.95."""
        if not 0.5 <= v <= 0.95:
            raise ValueError("processing_similarity_threshold must be between 0.5 and 0.95")
        return v
    
    @field_validator("processing_min_content_quality_score")
    @classmethod
    def validate_processing_min_content_quality_score(cls, v: float) -> float:
        """Validate that processing min content quality score is between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("processing_min_content_quality_score must be between 0.0 and 1.0")
        return v
    
    @field_validator("processing_max_summary_length")
    @classmethod
    def validate_processing_max_summary_length(cls, v: int) -> int:
        """Validate that processing max summary length is between 100 and 2000 characters."""
        if not 100 <= v <= 2000:
            raise ValueError("processing_max_summary_length must be between 100 and 2000")
        return v
    
    @field_validator("processing_batch_size")
    @classmethod
    def validate_processing_batch_size(cls, v: int) -> int:
        """Validate that processing batch size is between 1 and 100."""
        if not 1 <= v <= 100:
            raise ValueError("processing_batch_size must be between 1 and 100")
        return v
    
    @field_validator("processing_content_timeout")
    @classmethod
    def validate_processing_content_timeout(cls, v: int) -> int:
        """Validate that processing content timeout is between 5 and 300 seconds."""
        if not 5 <= v <= 300:
            raise ValueError("processing_content_timeout must be between 5 and 300")
        return v
    
    @field_validator("processing_max_concurrent_ai_analyses")
    @classmethod
    def validate_processing_max_concurrent_ai_analyses(cls, v: int) -> int:
        """Validate that processing max concurrent AI analyses is between 1 and 50."""
        if not 1 <= v <= 50:
            raise ValueError("processing_max_concurrent_ai_analyses must be between 1 and 50")
        return v
    
    @field_validator("processing_memory_threshold_mb")
    @classmethod
    def validate_processing_memory_threshold_mb(cls, v: int) -> int:
        """Validate that processing memory threshold is between 64 and 4096 MB."""
        if not 64 <= v <= 4096:
            raise ValueError("processing_memory_threshold_mb must be between 64 and 4096")
        return v
    
    @field_validator("processing_max_similarity_content_pairs")
    @classmethod
    def validate_processing_max_similarity_content_pairs(cls, v: int) -> int:
        """Validate that processing max similarity content pairs is between 10 and 500."""
        if not 10 <= v <= 500:
            raise ValueError("processing_max_similarity_content_pairs must be between 10 and 500")
        return v
    
    @field_validator("processing_max_similarity_batch_size")
    @classmethod
    def validate_processing_max_similarity_batch_size(cls, v: int) -> int:
        """Validate that processing max similarity batch size is between 2 and 100."""
        if not 2 <= v <= 100:
            raise ValueError("processing_max_similarity_batch_size must be between 2 and 100")
        return v
    
    @field_validator("health_agent_test_timeout")
    @classmethod
    def validate_health_agent_test_timeout(cls, v: int) -> int:
        """Validate that health agent test timeout is between 1 and 30 seconds."""
        if not 1 <= v <= 30:
            raise ValueError("health_agent_test_timeout must be between 1 and 30")
        return v
    
    @field_validator("health_processing_test_timeout")
    @classmethod
    def validate_health_processing_test_timeout(cls, v: int) -> int:
        """Validate that health processing test timeout is between 1 and 60 seconds."""
        if not 1 <= v <= 60:
            raise ValueError("health_processing_test_timeout must be between 1 and 60")
        return v
    
    # Database configuration validators
    @field_validator("database_query_timeout_seconds")
    @classmethod
    def validate_database_query_timeout_seconds(cls, v: int) -> int:
        """Validate that database query timeout is between 5 and 300 seconds."""
        if not 5 <= v <= 300:
            raise ValueError("database_query_timeout_seconds must be between 5 and 300")
        return v
    
    @field_validator("database_max_retries")
    @classmethod
    def validate_database_max_retries(cls, v: int) -> int:
        """Validate that database max retries is between 0 and 10."""
        if not 0 <= v <= 10:
            raise ValueError("database_max_retries must be between 0 and 10")
        return v
    
    @field_validator("database_batch_size")
    @classmethod
    def validate_database_batch_size(cls, v: int) -> int:
        """Validate that database batch size is between 1 and 1000."""
        if not 1 <= v <= 1000:
            raise ValueError("database_batch_size must be between 1 and 1000")
        return v
    
    @field_validator("database_content_ttl_days")
    @classmethod
    def validate_database_content_ttl_days(cls, v: int) -> int:
        """Validate that database content TTL is between 1 and 3650 days."""
        if not 1 <= v <= 3650:
            raise ValueError("database_content_ttl_days must be between 1 and 3650")
        return v
    
    @field_validator("database_analytics_retention_days")
    @classmethod
    def validate_database_analytics_retention_days(cls, v: int) -> int:
        """Validate that database analytics retention is between 30 and 3650 days."""
        if not 30 <= v <= 3650:
            raise ValueError("database_analytics_retention_days must be between 30 and 3650")
        return v
    
    @field_validator("database_cache_ttl_seconds")
    @classmethod
    def validate_database_cache_ttl_seconds(cls, v: int) -> int:
        """Validate that database cache TTL is between 60 and 86400 seconds."""
        if not 60 <= v <= 86400:
            raise ValueError("database_cache_ttl_seconds must be between 60 and 86400")
        return v
    
    @field_validator("database_max_content_size_mb")
    @classmethod
    def validate_database_max_content_size_mb(cls, v: int) -> int:
        """Validate that database max content size is between 1 and 1000 MB."""
        if not 1 <= v <= 1000:
            raise ValueError("database_max_content_size_mb must be between 1 and 1000")
        return v
    
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        """
        Parse comma-separated string from environment variable to list.
        Handles both string and list inputs.
        """
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        else:
            raise ValueError("allowed_origins must be a string or list")
    
    @field_validator("allowed_origins")
    def validate_allowed_origins(cls, v: List[str]) -> List[str]:
        """
        Validates that allowed_origins is a list of strings.
        """
        if not isinstance(v, list):
            raise ValueError("allowed_origins must be a list of strings")
        return v
    
    # Cross-validation between processing settings and existing configurations
    @model_validator(mode='after')
    def validate_processing_configuration_consistency(self):
        """Validate cross-field consistency between processing and other configurations."""
        warnings = []
        
        # Validate timeout relationships
        if self.processing_content_timeout >= self.processing_timeout_seconds:
            warnings.append(
                f"processing_content_timeout ({self.processing_content_timeout}s) should be less than "
                f"processing_timeout_seconds ({self.processing_timeout_seconds}s)"
            )
        
        # Validate concurrency relationships
        if self.processing_max_concurrent_ai_analyses > self.processing_concurrency * 3:
            warnings.append(
                f"processing_max_concurrent_ai_analyses ({self.processing_max_concurrent_ai_analyses}) should not exceed "
                f"processing_concurrency ({self.processing_concurrency}) * 3"
            )
        
        # Validate content length relationships
        if self.processing_max_summary_length > self.gemini_max_content_length:
            warnings.append(
                f"processing_max_summary_length ({self.processing_max_summary_length}) should not exceed "
                f"gemini_max_content_length ({self.gemini_max_content_length})"
            )
        
        if self.gemini_max_similarity_content_length > self.gemini_max_content_length:
            warnings.append(
                f"gemini_max_similarity_content_length ({self.gemini_max_similarity_content_length}) should not exceed "
                f"gemini_max_content_length ({self.gemini_max_content_length})"
            )
        
        # Validate batch size relationships
        if self.processing_batch_size > self.processing_concurrency * 5:
            warnings.append(
                f"processing_batch_size ({self.processing_batch_size}) should not exceed "
                f"processing_concurrency ({self.processing_concurrency}) * 5"
            )
        
        # Validate memory and batch size relationships
        if self.processing_batch_size > self.processing_memory_threshold_mb // 25:
            warnings.append(
                f"processing_batch_size ({self.processing_batch_size}) may be too large for "
                f"processing_memory_threshold_mb ({self.processing_memory_threshold_mb}MB)"
            )
        
        # Validate similarity analysis limits
        if self.processing_max_similarity_content_pairs > self.processing_memory_threshold_mb // 8:
            warnings.append(
                f"processing_max_similarity_content_pairs ({self.processing_max_similarity_content_pairs}) may be too high for "
                f"processing_memory_threshold_mb ({self.processing_memory_threshold_mb}MB)"
            )
        
        # Log warnings if any
        if warnings:
            import logging
            logger = logging.getLogger(__name__)
            for warning in warnings:
                logger.warning(f"Configuration validation warning: {warning}")
        
        return self

    model_config = {
        "populate_by_name": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


# Global settings instance
try:
    settings = Settings()
except Exception as e:
    # Fallback to default settings if loading fails
    import logging
    logging.warning(f"Failed to load settings from environment: {e}")
    
    # Create minimal settings with defaults - extend with all database settings
    class MinimalSettings:
        # Scraper settings
        scraper_concurrency = 5
        scraper_request_timeout_seconds = 20
        scraper_delay_seconds = 1.0
        scraper_user_agent = "TrayceAI-Bot/1.0"
        scraper_respect_robots = True
        scraper_max_retries = 3
        scraper_max_redirects = 5
        scraper_content_size_limit = 10485760
        
        # Gemini settings
        gemini_max_content_length = 4000
        gemini_max_similarity_content_length = 1000
        
        # Processing settings
        processing_max_summary_length = 500
        processing_timeout_seconds = 60
        processing_concurrency = 3
        processing_batch_size = 10
        processing_memory_threshold_mb = 512
        
        # Database settings
        database_query_timeout_seconds = 30
        database_max_retries = 3
        database_batch_size = 100
        database_enable_text_search = True
        database_content_ttl_days = 90
        database_analytics_retention_days = 365
        database_enable_caching = True
        database_cache_ttl_seconds = 3600
        database_max_content_size_mb = 50
        database_enable_compression = True
        database_index_background = True
        database_enable_profiling = False
        
        # Health check settings
        health_agent_test_timeout = 5
        health_processing_test_timeout = 8
    
    settings = MinimalSettings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
