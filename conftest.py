"""
Shared pytest fixtures and configuration for the AI Web Scraper test suite.

This module provides common fixtures, markers, and helper functions
that are used across all test files to ensure consistent test setup
and reduce code duplication.
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional
import json
from datetime import datetime, timezone
from bson import ObjectId

# Import application modules
from app.core.config import Settings
from app.agents.schemas import ParsedQuery
from app.scraper.schemas import ScrapedContent
from app.processing.schemas import ProcessedContent


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that don't require external services"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that may require mocked services"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer than 5 seconds"
    )
    config.addinivalue_line(
        "markers", "requires_gemini: Tests that require actual Gemini API access"
    )
    config.addinivalue_line(
        "markers", "requires_mongodb: Tests that require actual MongoDB connection"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and load tests"
    )
    config.addinivalue_line(
        "markers", "smoke: Smoke tests for basic functionality"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically add markers to tests based on their names."""
    for item in items:
        # Add integration marker to tests with 'integration' in name
        if 'integration' in item.name.lower():
            item.add_marker(pytest.mark.integration)
        
        # Add slow marker to tests with 'slow' or 'performance' in name
        if any(keyword in item.name.lower() for keyword in ['slow', 'performance', 'load']):
            item.add_marker(pytest.mark.slow)
        
        # Add unit marker to tests without other markers
        if not any(marker.name in ['integration', 'slow', 'requires_gemini', 'requires_mongodb'] 
                  for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


def pytest_runtest_setup(item):
    """Check for required environment variables before running tests."""
    # Check for Gemini API key requirement
    if item.get_closest_marker('requires_gemini'):
        if not os.getenv('GEMINI_API_KEY'):
            pytest.skip("GEMINI_API_KEY not set - skipping test requiring Gemini API")
    
    # Check for MongoDB requirement
    if item.get_closest_marker('requires_mongodb'):
        if not os.getenv('MONGODB_URI'):
            pytest.skip("MONGODB_URI not set - skipping test requiring MongoDB")


# Removed event_loop fixture to avoid conflict with pytest-asyncio auto mode
# pytest-asyncio with asyncio_mode=auto handles event loop management automatically


@pytest.fixture
def mock_settings():
    """Provide a real Settings instance with test-safe defaults."""
    from app.core.config import Settings
    
    # Create a real Settings instance with test defaults
    test_settings = Settings(
        gemini_api_key="test-api-key",
        mongodb_uri="mongodb://localhost:27017/test",
        mongodb_db="test_db",
        agent_confidence_threshold=0.7,
        agent_timeout_seconds=30,
        parser_timeout_seconds=45,
        categorizer_timeout_seconds=30,
        processor_timeout_seconds=60,
        scraper_concurrency=5,
        scraper_request_timeout_seconds=20,
        scraper_delay_seconds=1.0,
        scraper_user_agent="TestBot/1.0",
        scraper_respect_robots=True,
        scraper_max_retries=3,
        scraper_max_redirects=5,
        scraper_content_size_limit=1048576,  # 1MB
        processing_timeout_seconds=60,
        processing_max_retries=2,
        processing_concurrency=3,
        processing_enable_content_cleaning=True,
        processing_enable_ai_analysis=True,
        processing_enable_summarization=True,
        processing_enable_structured_extraction=True,
        processing_enable_duplicate_detection=True,
        processing_similarity_threshold=0.8,
        processing_min_content_quality_score=0.4,
        processing_max_summary_length=500,
        processing_batch_size=10,
        processing_content_timeout=30,
        processing_max_concurrent_ai_analyses=3,
        processing_memory_threshold_mb=512,
        processing_max_similarity_content_pairs=50,
        processing_max_similarity_batch_size=10,
        database_query_timeout_seconds=30,
        database_max_retries=3,
        database_batch_size=100,
        database_enable_text_search=True,
        database_content_ttl_days=90,
        database_enable_content_ttl=False,
        database_analytics_retention_days=365,
        database_enable_caching=True,
        database_cache_ttl_seconds=3600,
        database_max_content_size_mb=50,
        database_enable_compression=True,
        database_index_background=True,
        database_enable_profiling=False,
        health_agent_test_timeout=5,
        health_processing_test_timeout=8,
        api_request_timeout_seconds=300,
        api_max_query_length=1000,
        api_max_results_per_request=50,
        api_enable_request_logging=True,
        api_enable_analytics_tracking=True,
        api_rate_limit_requests_per_minute=60,
        api_enable_detailed_errors=True,
        api_enable_progress_tracking=True,
        api_default_processing_config=True,
        api_enable_database_storage=True,
        environment="test",
        log_level="INFO",
        debug=True,
        secret_key="test-secret-key",
        allowed_origins=["http://localhost:3000", "http://localhost:8000"],
        api_auth_enabled=False,
        api_keys="",
        api_key_rate_limit_per_minute=120,
        api_public_endpoints=["/health", "/docs", "/redoc", "/openapi.json", "/"],
        cache_enabled=True,
        cache_ttl_seconds=300,
        cache_max_size=1000,
        cache_response_enabled=True,
        log_format="json",
        log_file=None,
        log_max_bytes=10485760,
        log_backup_count=5,
        log_request_body=False,
        log_response_body=False,
        metrics_enabled=True,
        metrics_export_format="prometheus",
        health_check_interval_seconds=60,
        workers=4,
        max_connections=1000,
        trusted_hosts=["*"],
        enable_compression=True
    )
    
    yield test_settings


@pytest.fixture
def global_mock_gemini_client():
    """Create a reusable mock Gemini client with consistent default response."""
    mock_client = AsyncMock()
    
    # Mock successful response as default return value
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "query": "test query",
        "intent": "search",
        "entities": ["test"],
        "confidence": 0.9,
        "domain": "general",
        "category": "information",
        "relevance_score": 0.85,
        "extracted_keywords": ["test", "query"],
        "language": "en",
        "processing_time": 0.5
    })
    
    # Set consistent default return value instead of side_effect
    mock_client.generate_content.return_value = mock_response
    
    return mock_client


@pytest.fixture
def global_mock_database():
    """Create a mock AsyncIOMotorDatabase with all required collections."""
    mock_db = AsyncMock()
    
    # Mock collections
    mock_collections = {
        'queries': AsyncMock(),
        'scraped_content': AsyncMock(),
        'processed_content': AsyncMock(),
        'analytics': AsyncMock(),
        'migrations': AsyncMock()
    }
    
    # Configure collection methods
    for collection_name, mock_collection in mock_collections.items():
        mock_collection.insert_one = AsyncMock()
        mock_collection.insert_many = AsyncMock()
        mock_collection.find_one = AsyncMock()
        mock_collection.find = AsyncMock()
        mock_collection.update_one = AsyncMock()
        mock_collection.update_many = AsyncMock()
        mock_collection.delete_one = AsyncMock()
        mock_collection.delete_many = AsyncMock()
        mock_collection.count_documents = AsyncMock()
        mock_collection.aggregate = AsyncMock()
        mock_collection.create_index = AsyncMock()
        mock_collection.list_indexes = AsyncMock()
        mock_collection.drop_index = AsyncMock()
        
        # Set up common return values
        mock_collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        mock_collection.insert_many.return_value = MagicMock(inserted_ids=[ObjectId()])
        mock_collection.find_one.return_value = None
        mock_collection.find.return_value = AsyncMock()
        mock_collection.update_one.return_value = MagicMock(modified_count=1)
        mock_collection.update_many.return_value = MagicMock(modified_count=1)
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)
        mock_collection.delete_many.return_value = MagicMock(deleted_count=1)
        mock_collection.count_documents.return_value = 0
        mock_collection.aggregate.return_value = AsyncMock()
        mock_collection.create_index.return_value = "index_name"
        mock_collection.list_indexes.return_value = AsyncMock()
        mock_collection.drop_index.return_value = None
    
    # Configure database collection access using side_effect
    def get_collection(name):
        return mock_collections.get(name, AsyncMock())
    
    mock_db.__getitem__.side_effect = get_collection
    mock_db.list_collection_names = AsyncMock(return_value=list(mock_collections.keys()))
    
    # Also expose collection attributes directly for compatibility
    mock_db.queries = mock_collections['queries']
    mock_db.scraped_content = mock_collections['scraped_content']
    mock_db.processed_content = mock_collections['processed_content']
    mock_db.analytics = mock_collections['analytics']
    mock_db.migrations = mock_collections['migrations']
    
    return mock_db


@pytest.fixture
def skip_if_no_gemini():
    """Skip test if GEMINI_API_KEY is not set."""
    if not os.getenv('GEMINI_API_KEY'):
        pytest.skip("GEMINI_API_KEY not set")


@pytest.fixture
def skip_if_no_mongodb():
    """Skip test if MongoDB is not available."""
    if not os.getenv('MONGODB_URI'):
        pytest.skip("MONGODB_URI not set")


# Helper Functions

def create_mock_parsed_query(
    query: str = "test query",
    intent: str = "search",
    entities: list = None,
    confidence: float = 0.9,
    domain: str = "general",
    category: str = "information",
    relevance_score: float = 0.85,
    extracted_keywords: list = None,
    language: str = "en",
    processing_time: float = 0.5
) -> ParsedQuery:
    """Factory function to create ParsedQuery objects for testing."""
    return ParsedQuery(
        query=query,
        intent=intent,
        entities=entities or ["test"],
        confidence=confidence,
        domain=domain,
        category=category,
        relevance_score=relevance_score,
        extracted_keywords=extracted_keywords or ["test", "query"],
        language=language,
        processing_time=processing_time,
        created_at=datetime.now(timezone.utc)
    )


def create_mock_scraped_content(
    url: str = "https://example.com",
    title: str = "Test Title",
    content: str = "Test content",
    metadata: Dict[str, Any] = None,
    quality_score: float = 0.8,
    content_hash: str = "test_hash",
    scraped_at: datetime = None
) -> ScrapedContent:
    """Factory function to create ScrapedContent objects for testing."""
    return ScrapedContent(
        url=url,
        title=title,
        content=content,
        metadata=metadata or {"description": "Test description"},
        quality_score=quality_score,
        content_hash=content_hash,
        scraped_at=scraped_at or datetime.now(timezone.utc)
    )


def create_mock_processed_content(
    query_id: str = "test_query_id",
    scraped_content_id: str = "test_content_id",
    summary: str = "Test summary",
    analysis: Dict[str, Any] = None,
    structured_data: Dict[str, Any] = None,
    processing_time: float = 1.0,
    processed_at: datetime = None
) -> ProcessedContent:
    """Factory function to create ProcessedContent objects for testing."""
    return ProcessedContent(
        query_id=query_id,
        scraped_content_id=scraped_content_id,
        summary=summary,
        analysis=analysis or {"sentiment": "positive", "confidence": 0.8},
        structured_data=structured_data or {"entities": ["test"], "categories": ["general"]},
        processing_time=processing_time,
        processed_at=processed_at or datetime.now(timezone.utc)
    )


# Additional utility fixtures

@pytest.fixture
def global_mock_aiohttp_session():
    """Mock aiohttp ClientSession for HTTP requests."""
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="<html>Test content</html>")
    mock_response.headers = {"content-type": "text/html"}
    mock_response.url = "https://example.com"
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.post.return_value.__aenter__.return_value = mock_response
    mock_session.close = AsyncMock()
    return mock_session


@pytest.fixture
def global_mock_redis_client():
    """Mock Redis client for caching tests."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.exists = AsyncMock(return_value=False)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.close = AsyncMock()
    return mock_redis


@pytest.fixture
def sample_html_content():
    """Provide sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="Test description">
    </head>
    <body>
        <h1>Main Heading</h1>
        <p>This is a test paragraph with some content.</p>
        <div class="content">
            <h2>Subheading</h2>
            <p>More content here.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_json_response():
    """Provide sample JSON response for testing."""
    return {
        "status": "success",
        "data": {
            "query": "test query",
            "results": [
                {
                    "url": "https://example.com",
                    "title": "Test Result",
                    "snippet": "Test snippet",
                    "relevance_score": 0.9
                }
            ],
            "total_results": 1,
            "processing_time": 0.5
        },
        "metadata": {
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0"
        }
    }
