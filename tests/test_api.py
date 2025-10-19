"""
Comprehensive tests for the API endpoints following existing test patterns.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.services.orchestration import WorkflowOrchestrator
from app.agents.schemas import ParsedQuery, BaseQueryResult, QueryCategory
from app.scraper.schemas import ScrapedContent, ContentType
from app.processing.schemas import ProcessedContent, ContentSummary, StructuredData, AIInsights
from app.api.routers.scrape import ScrapeRequest
from app.utils.validation import ValidationException
from app.dependencies import get_workflow_orchestrator


# Test fixtures
@pytest.fixture
def client():
    """Create test client for API testing."""
    return TestClient(app)


@pytest.fixture
def mock_workflow_orchestrator():
    """Create mock workflow orchestrator for testing."""
    mock = AsyncMock(spec=WorkflowOrchestrator)
    return mock


@pytest.fixture
def sample_parsed_query():
    """Create sample parsed query for testing."""
    return ParsedQuery(
        base_result=BaseQueryResult(
            query_text="Find AI tools for image generation",
            confidence_score=0.95,
            processing_time=1.2,
            category=QueryCategory.AI_TOOLS
        )
    )


@pytest.fixture
def sample_scraped_content():
    """Create sample scraped content for testing."""
    return [
        ScrapedContent(
            url="https://example.com/ai-tool",
            title="Best AI Image Generator",
            content="This is a comprehensive guide to AI image generation tools...",
            content_type=ContentType.ARTICLE,
            processing_time=2.5,
            content_size_bytes=2048,
            extraction_method="beautifulsoup_primary",
            relevance_score=0.9,
            content_quality_score=0.85
        )
    ]


@pytest.fixture
def sample_processed_content(sample_scraped_content):
    """Create sample processed content for testing."""
    return [
        ProcessedContent(
            original_content=sample_scraped_content[0],
            cleaned_content="Cleaned content about AI image generation tools...",
            summary=ContentSummary(
                executive_summary="AI image generation tools overview",
                key_points=["Various AI tools available", "Different pricing models"],
                detailed_summary="Detailed analysis of AI image generation tools...",
                main_topics=["AI", "Image Generation", "Tools"],
                sentiment="positive",
                confidence_score=0.92
            ),
            structured_data=StructuredData(),
            ai_insights=AIInsights(
                themes=["AI Technology", "Image Generation"],
                relevance_score=0.87,
                quality_metrics={"readability": 0.75, "information_density": 0.82},
                recommendations=["Consider AI tools for creative projects"],
                credibility_indicators={"expert_citations": 3, "recent_sources": True},
                information_accuracy=0.88,
                source_reliability=0.85
            ),
            processing_duration=3.2,
            enhanced_quality_score=0.89
        )
    ]


@pytest.fixture
def sample_workflow_result(sample_parsed_query, sample_scraped_content, sample_processed_content):
    """Create sample workflow result for testing."""
    return {
        "status": "success",
        "query": {
            "text": sample_parsed_query.base_result.query_text,
            "category": sample_parsed_query.base_result.category.value,
            "confidence_score": sample_parsed_query.base_result.confidence_score
        },
        "results": {
            "scraped_content": sample_scraped_content,
            "processed_content": sample_processed_content,
            "total_scraped_items": len(sample_scraped_content),
            "total_processed_items": len(sample_processed_content)
        },
        "execution": {
            "total_duration_seconds": 15.7,
            "completed_stages": ["query_processing", "web_scraping", "ai_processing", "database_storage"],
            "stage_timings": {
                "query_processing": 1.2,
                "web_scraping": 8.5,
                "ai_processing": 4.8,
                "database_storage": 1.2
            },
            "errors": []
        }
    }


class TestScrapeEndpoint:
    """Test cases for the main scrape endpoint."""
    
    @pytest.mark.asyncio
    async def test_successful_scrape_request(self, client, mock_workflow_orchestrator, sample_workflow_result):
        """Test successful scrape request with valid input."""
        # Mock the workflow orchestrator
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = sample_workflow_result
        
        # Override the dependency
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={
                    "query": "Find AI tools for image generation",
                    "store_results": True
                }
            )
        finally:
            # Clear the override
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["status"] == "success"
        assert "timestamp" in data
        assert "query" in data
        assert "results" in data
        assert "analytics" in data
        assert "execution_metadata" in data
        
        # Verify query information
        assert data["query"]["text"] == "Find AI tools for image generation"
        assert data["query"]["category"] == "ai_tools"
        assert data["query"]["confidence_score"] == 0.95
        
        # Verify results
        assert "total_items" in data["results"]
        assert "processed_items" in data["results"]
        assert "success_rate" in data["results"]
    
    @pytest.mark.asyncio
    async def test_scrape_with_processing_config(self, client, mock_workflow_orchestrator, sample_workflow_result):
        """Test scrape request with custom processing configuration."""
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = sample_workflow_result
        
        # Override the dependency
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={
                    "query": "Find mutual funds with low fees",
                    "processing_config": {
                        "enable_ai_analysis": True,
                        "enable_summarization": True,
                        "max_summary_length": 300,
                        "concurrency": 2
                    },
                    "timeout_seconds": 180,
                    "store_results": True
                }
            )
        finally:
            # Clear the override
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify that the workflow was called with the correct parameters
        mock_workflow_orchestrator.execute_scraping_workflow.assert_called_once()
        call_args = mock_workflow_orchestrator.execute_scraping_workflow.call_args
        assert call_args[1]["query_text"] == "Find mutual funds with low fees"
        assert call_args[1]["timeout_seconds"] == 180
        assert call_args[1]["store_results"] is True
    
    def test_invalid_query_validation(self, client):
        """Test validation errors for invalid query input."""
        # Empty query
        response = client.post(
            "/api/v1/scrape",
            json={"query": ""}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        
        # Query too short
        response = client.post(
            "/api/v1/scrape",
            json={"query": "AI"}
        )
        assert response.status_code == 400
        
        # Query too long
        long_query = "A" * 1001  # Exceeds default max length
        response = client.post(
            "/api/v1/scrape",
            json={"query": long_query}
        )
        assert response.status_code == 400
    
    def test_invalid_processing_config_validation(self, client):
        """Test validation errors for invalid processing configuration."""
        response = client.post(
            "/api/v1/scrape",
            json={
                "query": "Find AI tools",
                "processing_config": {
                    "timeout_seconds": 5,  # Too low
                    "concurrency": 20,     # Too high
                    "invalid_key": "invalid_value"
                }
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
    
    def test_invalid_timeout_validation(self, client):
        """Test validation for invalid timeout values."""
        # Timeout too low
        response = client.post(
            "/api/v1/scrape",
            json={
                "query": "Find AI tools",
                "timeout_seconds": 10  # Below minimum of 30
            }
        )
        assert response.status_code == 422  # Pydantic validation error
        
        # Timeout too high
        response = client.post(
            "/api/v1/scrape",
            json={
                "query": "Find AI tools",
                "timeout_seconds": 700  # Above maximum of 600
            }
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_workflow_timeout_error(self, client, mock_workflow_orchestrator):
        """Test handling of workflow timeout errors."""
        # Mock timeout error
        timeout_result = {
            "status": "error",
            "error": {
                "code": "WORKFLOW_TIMEOUT",
                "message": "Workflow timed out after 300 seconds"
            },
            "execution": {
                "total_duration_seconds": 300.0,
                "completed_stages": ["query_processing", "web_scraping"],
                "failed_stage": "ai_processing",
                "stage_timings": {
                    "query_processing": 1.2,
                    "web_scraping": 298.8
                },
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = timeout_result
        
        # Override the dependency
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "Find AI tools for complex analysis"}
            )
        finally:
            # Clear the override
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "WORKFLOW_TIMEOUT"
        assert "execution_metadata" in data
    
    @pytest.mark.asyncio
    async def test_no_content_found_error(self, client, mock_workflow_orchestrator):
        """Test handling when no content is found for a query."""
        no_content_result = {
            "status": "error",
            "error": {
                "code": "NO_CONTENT_FOUND",
                "message": "No relevant content could be scraped for the query"
            },
            "execution": {
                "total_duration_seconds": 25.3,
                "completed_stages": ["query_processing", "web_scraping"],
                "failed_stage": "web_scraping",
                "stage_timings": {
                    "query_processing": 1.2,
                    "web_scraping": 24.1
                },
                "errors": []
            },
            "partial_results": {}
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = no_content_result
        
        # Override the dependency
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "Very obscure topic with no online content"}
            )
        finally:
            # Clear the override
            app.dependency_overrides.clear()
        
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "NO_CONTENT_FOUND"
    
    @pytest.mark.asyncio
    async def test_workflow_orchestrator_unavailable(self, client):
        """Test handling when workflow orchestrator is unavailable."""
        # Override the dependency to raise a 503 HTTPException
        def raise_503():
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail="Service unavailable")
        
        app.dependency_overrides[get_workflow_orchestrator] = raise_503
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "Find AI tools"}
            )
        finally:
            # Clear the override
            app.dependency_overrides.clear()
        
        assert response.status_code == 503
    
    def test_malformed_json_request(self, client):
        """Test handling of malformed JSON requests."""
        response = client.post(
            "/api/v1/scrape",
            data="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client):
        """Test handling of requests with missing required fields."""
        response = client.post(
            "/api/v1/scrape",
            json={}  # Missing required 'query' field
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_request_with_metadata(self, client, mock_workflow_orchestrator, sample_workflow_result):
        """Test scrape request with metadata tracking."""
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = sample_workflow_result
        
        # Override the dependency
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={
                    "query": "Find AI tools",
                    "metadata": {
                        "request_id": "test_req_123",
                        "session_id": "test_session_456",
                        "additional_context": {"source": "test_suite"}
                    }
                }
            )
        finally:
            # Clear the override
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == "test_req_123"
    
    @pytest.mark.asyncio
    async def test_partial_success_handling(self, client, mock_workflow_orchestrator, sample_scraped_content):
        """Test handling of partial success scenarios."""
        # Mock partial success result (scraping succeeded, processing partially failed)
        partial_result = {
            "status": "success",
            "query": {
                "text": "Find AI tools",
                "category": "ai_tools",
                "confidence_score": 0.95
            },
            "results": {
                "scraped_content": sample_scraped_content,
                "processed_content": [],  # Processing failed
                "total_scraped_items": len(sample_scraped_content),
                "total_processed_items": 0
            },
            "execution": {
                "total_duration_seconds": 30.5,
                "completed_stages": ["query_processing", "web_scraping"],
                "stage_timings": {
                    "query_processing": 1.2,
                    "web_scraping": 29.3
                },
                "errors": ["AI processing failed due to timeout"]
            }
        }
        
        mock_workflow_orchestrator.execute_scraping_workflow.return_value = partial_result
        
        # Override the dependency
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "Find AI tools"}
            )
        finally:
            # Clear the override
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["warnings"]) > 0  # Should have warnings about processing failures


class TestScrapeHealthEndpoint:
    """Test cases for the scrape health check endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client, mock_workflow_orchestrator):
        """Test successful health check."""
        health_status = {
            "status": "healthy",
            "components": {
                "query_processor": {"status": "healthy"},
                "scraper_orchestrator": {"status": "healthy"},
                "processing_orchestrator": {"status": "healthy"},
                "database_service": {"status": "healthy"}
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        mock_workflow_orchestrator.get_workflow_health.return_value = health_status
        
        # Override the dependency
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.get("/api/v1/scrape/health")
        finally:
            # Clear the override
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, client, mock_workflow_orchestrator):
        """Test health check with degraded services."""
        health_status = {
            "status": "degraded",
            "components": {
                "query_processor": {"status": "healthy"},
                "scraper_orchestrator": {"status": "unhealthy", "error": "Connection failed"},
                "processing_orchestrator": {"status": "healthy"},
                "database_service": {"status": "healthy"}
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        mock_workflow_orchestrator.get_workflow_health.return_value = health_status
        
        # Override the dependency
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.get("/api/v1/scrape/health")
        finally:
            # Clear the override
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client, mock_workflow_orchestrator):
        """Test health check failure."""
        mock_workflow_orchestrator.get_workflow_health.side_effect = Exception("Health check failed")
        
        # Override the dependency
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_workflow_orchestrator
        
        try:
            response = client.get("/api/v1/scrape/health")
        finally:
            # Clear the override
            app.dependency_overrides.clear()
        
        assert response.status_code == 503


class TestValidationUtils:
    """Test cases for validation utilities."""
    
    def test_validate_query_text_success(self):
        """Test successful query text validation."""
        from app.utils.validation import validate_query_text
        
        valid_queries = [
            "Find AI tools for image generation",
            "Best mutual funds for retirement",
            "How to learn machine learning?"
        ]
        
        for query in valid_queries:
            result = validate_query_text(query)
            assert result == query.strip()
    
    def test_validate_query_text_failures(self):
        """Test query text validation failures."""
        from app.utils.validation import validate_query_text, ValidationException
        
        invalid_queries = [
            "",  # Empty
            "  ",  # Whitespace only
            "AI",  # Too short
            "A" * 1001,  # Too long
            "<script>alert('xss')</script>Find AI tools",  # Suspicious content
        ]
        
        for query in invalid_queries:
            with pytest.raises(ValidationException):
                validate_query_text(query)
    
    def test_validate_processing_config_success(self):
        """Test successful processing config validation."""
        from app.utils.validation import validate_processing_config
        
        valid_configs = [
            {},  # Empty config
            {"enable_ai_analysis": True},
            {"timeout_seconds": 120, "concurrency": 3},
            {"max_summary_length": 300, "batch_size": 5}
        ]
        
        for config in valid_configs:
            result = validate_processing_config(config)
            assert isinstance(result, dict)
    
    def test_validate_processing_config_failures(self):
        """Test processing config validation failures."""
        from app.utils.validation import validate_processing_config, ValidationException
        
        invalid_configs = [
            {"unknown_key": "value"},  # Unknown key
            {"timeout_seconds": 5},    # Too low
            {"concurrency": 20},       # Too high
            {"enable_ai_analysis": "yes"},  # Wrong type
        ]
        
        for config in invalid_configs:
            with pytest.raises(ValidationException):
                validate_processing_config(config)


class TestResponseUtils:
    """Test cases for response formatting utilities."""
    
    def test_format_success_response(self):
        """Test successful response formatting."""
        from app.utils.response import format_success_response
        
        data = {"results": [1, 2, 3]}
        response = format_success_response(data, "Test successful")
        
        assert response["status"] == "success"
        assert response["message"] == "Test successful"
        assert response["data"] == data
        assert "timestamp" in response
    
    def test_format_error_response(self):
        """Test error response formatting."""
        from app.utils.response import format_error_response
        from app.api.schemas import ErrorDetail
        
        error_detail = ErrorDetail(
            error_code="TEST_ERROR",
            message="Test error message",
            recovery_suggestions=["Try again"]
        )
        
        response = format_error_response(
            error_code="TEST_ERROR",
            message="Test failed",
            details=[error_detail],
            status_code=400
        )
        
        assert response["status"] == "error"
        assert response["error"]["code"] == "TEST_ERROR"
        assert response["error"]["message"] == "Test failed"
        assert response["error"]["http_status"] == 400
        assert len(response["error"]["details"]) == 1
    
    def test_calculate_response_metrics(self):
        """Test response metrics calculation."""
        from app.utils.response import calculate_response_metrics
        from datetime import datetime, timedelta
        
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=5.5)
        stages_timing = {"stage1": 2000, "stage2": 3500}
        
        metadata = calculate_response_metrics(
            start_time=start_time,
            end_time=end_time,
            stages_timing=stages_timing,
            processed_items=10,
            successful_items=8
        )
        
        assert metadata.execution_time_ms == 5500.0
        assert metadata.start_time == start_time
        assert metadata.end_time == end_time
        assert metadata.stages_timing == stages_timing
        assert metadata.performance_metrics["success_rate"] == 0.8


# Integration tests
class TestAPIIntegration:
    """Integration tests for the complete API workflow."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_scrape_workflow(self, client):
        """Test complete end-to-end scrape workflow with mocked dependencies."""
        # This test would require more complex mocking of all dependencies
        # For now, we'll test that the endpoint structure is correct
        
        # Mock all the dependencies that would be called
        mock_instance = AsyncMock()
        mock_instance.execute_scraping_workflow.return_value = {
            "status": "success",
            "query": {"text": "test", "category": "general", "confidence_score": 0.8},
            "results": {"scraped_content": [], "processed_content": [], "total_scraped_items": 0, "total_processed_items": 0},
            "execution": {"total_duration_seconds": 1.0, "completed_stages": [], "stage_timings": {}, "errors": []}
        }
        
        # Override the dependency
        app.dependency_overrides[get_workflow_orchestrator] = lambda: mock_instance
        
        try:
            response = client.post(
                "/api/v1/scrape",
                json={"query": "test query"}
            )
        finally:
            # Clear the override
            app.dependency_overrides.clear()
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "query" in data
        assert "results" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
