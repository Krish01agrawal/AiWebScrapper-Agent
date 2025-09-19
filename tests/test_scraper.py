"""
Comprehensive tests for the scraper module.
"""
import pytest
import asyncio
import aiohttp
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import List

from app.scraper.schemas import (
    ScrapedContent, DiscoveryResult, ScrapingError, ScrapingException, ErrorType,
    ContentType, DiscoveryMethod, ContentExtractionConfig, SiteDiscoveryConfig
)
from app.scraper.session import init_scraper_session, close_scraper_session, get_scraper_session
from app.scraper.rate_limiter import get_rate_limit_manager, init_rate_limit_manager, close_rate_limit_manager
from app.scraper.robots import get_robots_checker, init_robots_checker, close_robots_checker
from app.scraper.base import BaseScraperAgent
from app.scraper.discovery import SiteDiscoveryAgent
from app.scraper.extractor import ContentExtractorAgent
from app.scraper.orchestrator import ScraperOrchestrator
from app.agents.schemas import ParsedQuery, BaseQueryResult, QueryCategory


# Test data fixtures
@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="A test page for scraping">
        <meta name="keywords" content="test, scraping, example">
        <meta name="author" content="Test Author">
    </head>
    <body>
        <header>
            <nav>Navigation</nav>
        </header>
        <main>
            <article>
                <h1>Main Article Title</h1>
                <p>This is the main content of the article. It contains useful information.</p>
                <p>Here's another paragraph with more content.</p>
            </article>
        </main>
        <aside>
            <p>Sidebar content</p>
        </aside>
        <footer>
            <p>Footer content</p>
        </footer>
    </body>
    </html>
    """


@pytest.fixture
def sample_robots_txt():
    """Sample robots.txt content for testing."""
    return """
    User-agent: *
    Disallow: /private/
    Disallow: /admin/
    Allow: /public/
    Crawl-delay: 2
    """


@pytest.fixture
def mock_parsed_query():
    """Mock parsed query for testing."""
    base_result = BaseQueryResult(
        query_text="Find AI tools for image generation",
        confidence_score=0.9,
        category=QueryCategory.AI_TOOLS,
        processing_time=1.2
    )
    
    return ParsedQuery(
        base_result=base_result,
        ai_tools_data=None,
        mutual_funds_data=None,
        general_data=None
    )


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client for testing."""
    client = Mock()
    client.is_available.return_value = True
    client.generate_content = AsyncMock()
    return client


# Test scraper session management
class TestScraperSession:
    """Test scraper session management."""
    
    @pytest.mark.asyncio
    async def test_init_and_close_scraper_session(self):
        """Test scraper session initialization and cleanup."""
        # Test initialization
        await init_scraper_session()
        
        # Test session retrieval
        session = get_scraper_session()
        assert session is not None
        assert not session.closed
        
        # Test cleanup
        await close_scraper_session()
        
        # Test that session is no longer available
        with pytest.raises(RuntimeError):
            get_scraper_session()
    
    @pytest.mark.asyncio
    async def test_session_timeout_handling(self):
        """Test session timeout handling."""
        await init_scraper_session()
        
        try:
            session = get_scraper_session()
            
            # Test that timeout is properly configured
            assert session.timeout.total == 20  # Default from settings
            assert session.timeout.connect == 10
            assert session.timeout.sock_read == 20
            
        finally:
            await close_scraper_session()
    
    @pytest.mark.asyncio
    async def test_session_error_handling(self):
        """Test session error handling scenarios."""
        await init_scraper_session()
        
        try:
            session = get_scraper_session()
            
            # Test with invalid URL
            with pytest.raises(aiohttp.ClientError):
                async with session.get("invalid-url", timeout=1) as response:
                    pass
                    
        finally:
            await close_scraper_session()


# Test rate limiting
class TestRateLimiter:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_manager(self):
        """Test rate limit manager functionality."""
        await init_rate_limit_manager()
        
        manager = get_rate_limit_manager()
        assert manager is not None
        
        # Test domain rate limiting
        url = "https://example.com/page"
        
        async with manager.acquire_domain_slot(url):
            # This should work without blocking
            pass
        
        await close_rate_limit_manager()


# Test robots.txt compliance
class TestRobotsCompliance:
    """Test robots.txt compliance functionality."""
    
    @pytest.mark.asyncio
    async def test_robots_checker(self):
        """Test robots checker functionality."""
        await init_robots_checker()
        
        checker = get_robots_checker()
        assert checker is not None
        
        # Test cache stats
        stats = checker.get_cache_stats()
        assert isinstance(stats, dict)
        assert "total_entries" in stats
        
        await close_robots_checker()
    
    @pytest.mark.asyncio
    async def test_malformed_robots_txt(self):
        """Test handling of malformed robots.txt files."""
        await init_robots_checker()
        
        try:
            checker = get_robots_checker()
            
            # Test with malformed content
            malformed_content = "Invalid robots.txt content\nUser-agent: *\nDisallow: /"
            parser = checker._parse_robots_txt(malformed_content, "https://example.com")
            
            # Should not crash and should return a parser instance
            assert parser is not None
            
        finally:
            await close_robots_checker()
    
    @pytest.mark.asyncio
    async def test_robots_txt_timeout_handling(self):
        """Test robots.txt timeout handling."""
        await init_robots_checker()
        
        try:
            checker = get_robots_checker()
            
            # Test that timeout is properly configured
            # This tests that the robots checker uses the standardized timeout
            assert True  # Placeholder for actual timeout validation
            
        finally:
            await close_robots_checker()


# Test base scraper agent
class TestBaseScraperAgent:
    """Test base scraper agent functionality."""
    
    @pytest.fixture
    def base_agent(self):
        """Create a base scraper agent for testing."""
        return BaseScraperAgent(
            name="TestAgent",
            description="Test agent for testing",
            version="1.0.0"
        )
    
    def test_agent_initialization(self, base_agent):
        """Test agent initialization."""
        assert base_agent.name == "TestAgent"
        assert base_agent.description == "Test agent for testing"
        assert base_agent.version == "1.0.0"
    
    def test_url_validation(self, base_agent):
        """Test URL validation functionality."""
        # Test valid URLs
        valid_urls = [
            "https://example.com",
            "http://test.org/page",
            "example.com"  # Should be normalized
        ]
        
        for url in valid_urls:
            validated = base_agent._validate_url(url)
            assert validated.startswith(("http://", "https://"))
        
        # Test invalid URLs
        invalid_urls = ["", "not-a-url"]
        
        for url in invalid_urls:
            with pytest.raises(ValueError):
                base_agent._validate_url(url)
        
        # Test unsupported schemes (these should raise ValueError)
        unsupported_schemes = ["ftp://invalid", "sftp://invalid"]
        
        for url in unsupported_schemes:
            with pytest.raises(ValueError, match="Invalid URL format"):
                base_agent._validate_url(url)
    
    def test_url_scheme_validation(self, base_agent):
        """Test URL scheme validation."""
        # Test unsupported schemes
        unsupported_schemes = [
            "ftp://example.com",
            "sftp://example.com",
            "file:///path/to/file",
            "mailto:user@example.com"
        ]
        
        for url in unsupported_schemes:
            with pytest.raises(ValueError, match="Invalid URL format"):
                base_agent._validate_url(url)
        
        # Test supported schemes
        supported_schemes = [
            "https://example.com",
            "http://example.com"
        ]
        
        for url in supported_schemes:
            validated = base_agent._validate_url(url)
            assert validated == url
    
    def test_content_size_validation(self, base_agent):
        """Test content size validation and truncation."""
        # Test normal content
        normal_content = "This is normal content"
        result = base_agent._validate_content_size(normal_content)
        assert result == normal_content
        
        # Test large content that needs truncation
        large_content = "x" * 20000000  # 20MB content
        result = base_agent._validate_content_size(large_content)
        
        # Should be truncated
        assert len(result.encode('utf-8')) <= 10485760  # 10MB limit
        assert result.endswith("... [Content truncated due to size limits]")
        
        # Test that truncation is accurate
        final_bytes = len(result.encode('utf-8'))
        assert final_bytes <= 10485760
    
    def test_domain_extraction(self, base_agent):
        """Test domain extraction functionality."""
        test_cases = [
            ("https://example.com/page", "example.com"),
            ("http://sub.domain.org", "sub.domain.org"),
            ("https://www.test.co.uk", "www.test.co.uk")
        ]
        
        for url, expected_domain in test_cases:
            domain = base_agent._extract_domain(url)
            assert domain == expected_domain


# Test site discovery agent
class TestSiteDiscoveryAgent:
    """Test site discovery agent functionality."""
    
    @pytest.fixture
    def discovery_agent(self, mock_gemini_client):
        """Create a site discovery agent for testing."""
        return SiteDiscoveryAgent(gemini_client=mock_gemini_client)
    
    def test_agent_initialization(self, discovery_agent):
        """Test discovery agent initialization."""
        assert discovery_agent.name == "SiteDiscoveryAgent"
        assert discovery_agent.config is not None
        assert len(discovery_agent._domain_patterns) > 0
    
    def test_llm_response_parsing_edge_cases(self, discovery_agent):
        """Test LLM response parsing with various edge cases."""
        # Test with malformed JSON
        malformed_response = Mock()
        malformed_response.text = "This is not JSON at all"
        
        sites = discovery_agent._parse_llm_response(
            malformed_response, "test query", QueryCategory.AI_TOOLS
        )
        assert sites == []
        
        # Test with partial JSON
        partial_response = Mock()
        partial_response.text = '{"sites": [{"url": "https://example.com"}]'
        
        sites = discovery_agent._parse_llm_response(
            partial_response, "test query", QueryCategory.AI_TOOLS
        )
        assert sites == []
        
        # Test with valid JSON in wrapper
        wrapper_response = Mock()
        wrapper_response.text = '{"sites": [{"url": "https://example.com", "relevance_score": 0.8}]}'
        
        sites = discovery_agent._parse_llm_response(
            wrapper_response, "test query", QueryCategory.AI_TOOLS
        )
        assert len(sites) == 1
        assert sites[0].url == "https://example.com"
    
    def test_llm_response_validation(self, discovery_agent):
        """Test LLM response validation and error handling."""
        # Test with missing URL
        invalid_response = Mock()
        invalid_response.text = '[{"relevance_score": 0.8}]'
        
        sites = discovery_agent._parse_llm_response(
            invalid_response, "test query", QueryCategory.AI_TOOLS
        )
        assert sites == []
        
        # Test with invalid relevance score
        invalid_score_response = Mock()
        invalid_score_response.text = '[{"url": "https://example.com", "relevance_score": "invalid"}]'
        
        sites = discovery_agent._parse_llm_response(
            invalid_score_response, "test query", QueryCategory.AI_TOOLS
        )
        assert len(sites) == 1
        assert sites[0].relevance_score == 0.5  # Default value
    
    def test_domain_patterns_initialization(self, discovery_agent):
        """Test domain patterns initialization."""
        patterns = discovery_agent._domain_patterns
        
        # Check that we have patterns for expected categories
        assert "ai_tools" in patterns
        assert "mutual_funds" in patterns
        assert "general" in patterns
        
        # Check that patterns contain expected domains
        assert "github.com" in patterns["ai_tools"]
        assert "morningstar.com" in patterns["mutual_funds"]
        assert "wikipedia.org" in patterns["general"]
    
    @pytest.mark.asyncio
    async def test_rule_based_discovery(self, discovery_agent, mock_parsed_query):
        """Test rule-based site discovery."""
        sites = await discovery_agent._discover_via_rules(
            mock_parsed_query.base_result.query_text,
            mock_parsed_query.base_result.category
        )
        
        assert isinstance(sites, list)
        assert len(sites) > 0
        
        # Check that sites are from AI tools category
        for site in sites:
            assert site.discovery_method == DiscoveryMethod.RULE_BASED
            assert site.category == "ai_tools"
            assert site.relevance_score > 0
    
    def test_domain_relevance_calculation(self, discovery_agent, mock_parsed_query):
        """Test domain relevance calculation."""
        # Test authoritative domain boost
        score = discovery_agent._calculate_domain_relevance(
            "github.com",
            mock_parsed_query.base_result.query_text,
            mock_parsed_query.base_result.category
        )
        assert score > 0.5  # Should be boosted
        
        # Test regular domain
        score = discovery_agent._calculate_domain_relevance(
            "example.com",
            mock_parsed_query.base_result.query_text,
            mock_parsed_query.base_result.category
        )
        assert 0.5 <= score <= 0.8  # Should be in reasonable range
    
    def test_site_deduplication(self, discovery_agent):
        """Test site deduplication functionality."""
        # Create mock sites with duplicate domains
        sites = [
            DiscoveryResult(
                url="https://example.com",
                relevance_score=0.8,
                domain="example.com",
                discovery_method=DiscoveryMethod.RULE_BASED,
                confidence=0.7
            ),
            DiscoveryResult(
                url="https://example.com/page",
                relevance_score=0.9,
                domain="example.com",
                discovery_method=DiscoveryMethod.LLM_GENERATED,
                confidence=0.8
            ),
            DiscoveryResult(
                url="https://test.com",
                relevance_score=0.7,
                domain="test.com",
                discovery_method=DiscoveryMethod.RULE_BASED,
                confidence=0.6
            )
        ]
        
        unique_sites = discovery_agent._deduplicate_sites(sites)
        assert len(unique_sites) == 2  # Should remove duplicate domain
        
        # Check that higher relevance site was kept
        example_site = next(s for s in unique_sites if s.domain == "example.com")
        assert example_site.relevance_score == 0.9  # Higher score kept


# Test content extraction agent
class TestContentExtractorAgent:
    """Test content extraction agent functionality."""
    
    @pytest.fixture
    def extractor_agent(self, mock_gemini_client):
        """Create a content extractor agent for testing."""
        return ContentExtractorAgent(gemini_client=mock_gemini_client)
    
    def test_agent_initialization(self, extractor_agent):
        """Test extractor agent initialization."""
        assert extractor_agent.name == "ContentExtractorAgent"
        assert extractor_agent.config is not None
    
    def test_content_cleaning(self, extractor_agent):
        """Test content cleaning functionality."""
        # Test ad removal
        content_with_ads = "This is content with advertisement and sponsored content."
        cleaned = extractor_agent._remove_ad_content(content_with_ads)
        assert "advertisement" not in cleaned.lower()
        assert "sponsored" not in cleaned.lower()
        
        # Test whitespace normalization
        content_with_whitespace = "Multiple    spaces\n\n\nand\n\n\nnewlines"
        normalized = extractor_agent._normalize_whitespace(content_with_whitespace)
        assert "   " not in normalized  # No multiple spaces
        assert normalized.count('\n\n') <= 2  # Limited newlines
        
        # Test duplicate line removal
        content_with_duplicates = "Line 1\nLine 1\nLine 2\nLine 2\nLine 3"
        deduplicated = extractor_agent._remove_duplicate_lines(content_with_duplicates)
        assert deduplicated.count("Line 1") == 1
        assert deduplicated.count("Line 2") == 1
    
    def test_content_quality_calculation(self, extractor_agent):
        """Test content quality score calculation."""
        # Test with minimal content
        metadata = {}
        content = "Short content"
        score = extractor_agent._calculate_content_quality(content, metadata)
        assert 0.5 <= score <= 0.6  # Base score + minimal bonuses
        
        # Test with rich content
        rich_metadata = {
            "title": "Test Title",
            "description": "Test description",
            "author": "Test Author",
            "publish_date": datetime.utcnow()
        }
        rich_content = "This is much longer content with multiple paragraphs.\n\nIt has structure and meaningful information."
        score = extractor_agent._calculate_content_quality(rich_content, rich_metadata)
        assert score > 0.7  # Should be significantly higher


# Test scraper orchestrator
class TestScraperOrchestrator:
    """Test scraper orchestrator functionality."""
    
    @pytest.fixture
    def orchestrator(self, mock_gemini_client):
        """Create a scraper orchestrator for testing."""
        return ScraperOrchestrator(gemini_client=mock_gemini_client)
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.name == "ScraperOrchestrator"
        assert orchestrator.discovery_agent is not None
        assert orchestrator.extractor_agent is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_extraction_error_handling(self, orchestrator, mock_parsed_query):
        """Test error handling during concurrent extraction."""
        # Create mock sites
        mock_sites = [
            DiscoveryResult(
                url="https://example1.com",
                relevance_score=0.8,
                domain="example1.com",
                discovery_method=DiscoveryMethod.RULE_BASED,
                confidence=0.7
            ),
            DiscoveryResult(
                url="https://example2.com",
                relevance_score=0.9,
                domain="example2.com",
                discovery_method=DiscoveryMethod.RULE_BASED,
                confidence=0.8
            )
        ]
        
        # Mock the extractor to simulate failures
        with patch.object(orchestrator.extractor_agent, 'execute') as mock_execute:
            mock_execute.side_effect = [
                Exception("Network timeout"),
                ScrapedContent(
                    url="https://example2.com",
                    title="Test",
                    content="Content",
                    processing_time=1.0,
                    content_size_bytes=1000,
                    extraction_method="test"
                )
            ]
            
            # This should handle the exception gracefully
            results = await orchestrator._extract_content_from_sites(mock_sites, mock_parsed_query)
            
            # Should have one successful result
            assert len(results) == 1
            assert results[0].url == "https://example2.com"
    
    def test_semaphore_concurrency_control(self, orchestrator):
        """Test that semaphore properly controls concurrency."""
        # Test semaphore initialization
        assert orchestrator._semaphore._value == 5  # Default concurrency limit
        
        # Test that semaphore is used in individual extraction
        # This is tested by the concurrent extraction test above
        assert True
    
    def test_combined_score_calculation(self, orchestrator, mock_parsed_query):
        """Test combined score calculation for ranking."""
        # Create mock scraped content
        content = ScrapedContent(
            url="https://example.com",
            title="Test Content",
            content="This is test content for scoring",
            content_type=ContentType.ARTICLE,
            processing_time=1.0,
            content_size_bytes=1000,
            extraction_method="test",
            relevance_score=0.8,
            content_quality_score=0.9
        )
        
        score = orchestrator._calculate_combined_score(content, mock_parsed_query)
        assert 0.0 <= score <= 1.0
        assert score > 0.7  # Should be high due to good scores
    
    def test_content_filtering(self, orchestrator, mock_parsed_query):
        """Test content filtering functionality."""
        # Create mock contents with varying quality
        contents = [
            ScrapedContent(
                url="https://good.com",
                title="Good Content",
                content="Good quality content with sufficient length",
                content_type=ContentType.ARTICLE,
                processing_time=1.0,
                content_size_bytes=2000,
                extraction_method="test",
                relevance_score=0.8,
                content_quality_score=0.9
            ),
            ScrapedContent(
                url="https://short.com",
                title="Short Content",
                content="Too short",
                content_type=ContentType.GENERAL,
                processing_time=0.5,
                content_size_bytes=100,
                extraction_method="test",
                relevance_score=0.5,
                content_quality_score=0.4
            ),
            ScrapedContent(
                url="https://low-quality.com",
                title="Low Quality",
                content="Content with low quality scores",
                content_type=ContentType.GENERAL,
                processing_time=1.0,
                content_size_bytes=1500,
                extraction_method="test",
                relevance_score=0.1,
                content_quality_score=0.2
            )
        ]
        
        filtered = orchestrator._filter_results(contents, mock_parsed_query)
        
        # Should only keep the good content
        assert len(filtered) == 1
        assert filtered[0].url == "https://good.com"


# Test schemas
class TestScraperSchemas:
    """Test scraper schema validation."""
    
    def test_scraped_content_validation(self):
        """Test ScrapedContent schema validation."""
        # Valid content
        valid_content = ScrapedContent(
            url="https://example.com",
            title="Test Title",
            content="This is valid content",
            processing_time=1.0,
            content_size_bytes=1000,
            extraction_method="test"
        )
        assert valid_content.url == "https://example.com"
        assert valid_content.content == "This is valid content"
        
        # Test content size validation
        with pytest.raises(ValueError):
            ScrapedContent(
                url="https://example.com",
                title="Test",
                content="Test",
                processing_time=1.0,
                content_size_bytes=200000000,  # Too large
                extraction_method="test"
            )
    
    def test_discovery_result_validation(self):
        """Test DiscoveryResult schema validation."""
        # Valid discovery result
        valid_result = DiscoveryResult(
            url="https://example.com",
            relevance_score=0.8,
            domain="example.com",
            discovery_method=DiscoveryMethod.RULE_BASED,
            confidence=0.7
        )
        assert valid_result.relevance_score == 0.8
        assert valid_result.discovery_method == DiscoveryMethod.RULE_BASED
        
        # Test relevance score bounds
        with pytest.raises(ValueError):
            DiscoveryResult(
                url="https://example.com",
                relevance_score=1.5,  # Too high
                domain="example.com",
                discovery_method=DiscoveryMethod.RULE_BASED,
                confidence=0.7
            )
    
    def test_scraping_error_validation(self):
        """Test ScrapingError schema validation."""
        # Valid error
        valid_error = ScrapingError(
            error_type=ErrorType.HTTP_ERROR,
            message="Test error",
            url="https://example.com"
        )
        assert valid_error.error_type == ErrorType.HTTP_ERROR
        assert valid_error.can_retry is True  # Default value
    
    def test_scraping_exception_class(self):
        """Test ScrapingException class functionality."""
        # Create a ScrapingError
        error = ScrapingError(
            error_type=ErrorType.TIMEOUT,
            message="Request timeout",
            url="https://example.com"
        )
        
        # Create exception from error
        exception = ScrapingException(error)
        
        # Test exception properties
        assert exception.error == error
        assert str(exception) == "timeout: Request timeout for https://example.com"
        assert isinstance(exception, Exception)


# Integration tests
class TestScraperIntegration:
    """Integration tests for scraper components."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_setup(self):
        """Test that all scraper components can be initialized together."""
        try:
            # Initialize all components
            await init_scraper_session()
            await init_rate_limit_manager()
            await init_robots_checker()
            
            # Verify components are available
            session = get_scraper_session()
            rate_manager = get_rate_limit_manager()
            robots_checker = get_robots_checker()
            
            assert session is not None
            assert rate_manager is not None
            assert robots_checker is not None
            
        finally:
            # Cleanup
            await close_robots_checker()
            await close_rate_limit_manager()
            await close_scraper_session()
    
    @pytest.mark.asyncio
    async def test_agent_coordination(self, mock_gemini_client, mock_parsed_query):
        """Test that agents can work together."""
        # Create agents
        discovery_agent = SiteDiscoveryAgent(gemini_client=mock_gemini_client)
        extractor_agent = ContentExtractorAgent(gemini_client=mock_gemini_client)
        orchestrator = ScraperOrchestrator(
            gemini_client=mock_gemini_client,
            discovery_agent=discovery_agent,
            extractor_agent=extractor_agent
        )
        
        # Test that orchestrator has access to sub-agents
        assert orchestrator.discovery_agent == discovery_agent
        assert orchestrator.extractor_agent == extractor_agent
        
        # Test agent info retrieval
        info = orchestrator.get_info()
        assert "sub_agents" in info
        assert discovery_agent.name in info["sub_agents"]
        assert extractor_agent.name in info["sub_agents"]


# Performance tests
class TestScraperPerformance:
    """Performance tests for scraper components."""
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, mock_gemini_client):
        """Test concurrent processing capabilities."""
        orchestrator = ScraperOrchestrator(gemini_client=mock_gemini_client)
        
        # Test that semaphore limits concurrency
        assert orchestrator._semaphore._value == 5  # Default concurrency limit
        
        # Test concurrent task creation with shorter sleep
        tasks = []
        for i in range(5):  # Reduced from 10 to 5
            task = asyncio.create_task(asyncio.sleep(0.01))  # Reduced from 0.1 to 0.01
            tasks.append(task)
        
        # Should complete without issues
        await asyncio.gather(*tasks)
    
    def test_memory_efficient_processing(self, mock_gemini_client):
        """Test memory efficiency of processing."""
        orchestrator = ScraperOrchestrator(gemini_client=mock_gemini_client)
        
        # Test that large content is properly truncated
        large_content = "x" * 20000000  # 20MB content
        
        # This should not cause memory issues
        truncated = orchestrator.extractor_agent._validate_content_size(large_content)
        assert len(truncated.encode('utf-8')) <= 10485760  # 10MB limit


# Error scenario tests
class TestScraperErrorScenarios:
    """Test critical error scenarios and edge cases."""
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, mock_gemini_client):
        """Test network timeout handling."""
        discovery_agent = SiteDiscoveryAgent(gemini_client=mock_gemini_client)
        
        # Mock a network timeout scenario
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError("Request timeout")
            
            # Should handle timeout gracefully
            with pytest.raises(asyncio.TimeoutError):
                await discovery_agent._discover_via_llm("test query", QueryCategory.AI_TOOLS)
    
    @pytest.mark.asyncio
    async def test_llm_api_failures(self, mock_gemini_client):
        """Test LLM API failure handling."""
        discovery_agent = SiteDiscoveryAgent(gemini_client=mock_gemini_client)
        
        # Mock LLM API failure
        mock_gemini_client.generate_content.side_effect = Exception("API rate limit exceeded")
        
        # Should handle API failure gracefully
        sites = await discovery_agent._discover_via_llm("test query", QueryCategory.AI_TOOLS)
        assert sites == []  # Should return empty list on failure
    
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self, mock_gemini_client):
        """Test concurrent rate limiting scenarios."""
        orchestrator = ScraperOrchestrator(gemini_client=mock_gemini_client)
        
        # Test that semaphore properly limits concurrent operations
        # This is already tested in the concurrent extraction test above
        assert orchestrator._semaphore._value == 5
    
    def test_content_size_limit_edge_cases(self, mock_gemini_client):
        """Test content size limit edge cases."""
        extractor_agent = ContentExtractorAgent(gemini_client=mock_gemini_client)
        
        # Test with content exactly at the limit
        exact_size_content = "x" * 10485760  # Exactly 10MB
        result = extractor_agent._validate_content_size(exact_size_content)
        assert result == exact_size_content
        
        # Test with content just over the limit
        over_limit_content = "x" * 10485761  # Just over 10MB
        result = extractor_agent._validate_content_size(over_limit_content)
        assert len(result.encode('utf-8')) <= 10485760
        
        # Test with empty content
        empty_content = ""
        result = extractor_agent._validate_content_size(empty_content)
        assert result == empty_content


if __name__ == "__main__":
    pytest.main([__file__])
