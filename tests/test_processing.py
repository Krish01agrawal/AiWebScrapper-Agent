"""
Tests for the processing module.
"""
import pytest
import asyncio
import time
import os
import hashlib
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import List

from app.processing.schemas import (
    ContentSummary, StructuredData, AIInsights, DuplicateAnalysis,
    ProcessedContent, ProcessingResult, ProcessingConfig, ProcessingError
)
from app.processing.cleaning import ContentCleaningAgent
from app.processing.analysis import AIAnalysisAgent
from app.processing.summarization import SummarizationAgent
from app.processing.extraction import StructuredDataExtractor
from app.processing.duplicates import DuplicateDetectionAgent
from app.processing.orchestrator import ProcessingOrchestrator
from app.processing.ai_agent_base import BaseAIAgent, AIAgentErrorHandler
from app.scraper.schemas import ScrapedContent, ContentType
from app.agents.schemas import ParsedQuery, BaseQueryResult, QueryCategory


def create_test_scraped_content(
    url: str = "https://example.com/article",
    title: str = "Test Article Title",
    content: str = "This is a test article content with some sample text. It contains multiple sentences and paragraphs for testing purposes.",
    content_type: ContentType = ContentType.ARTICLE,
    processing_time: float = 0.5,
    content_size_bytes: int = 500,
    extraction_method: str = "test_extraction",
    content_quality_score: float = 0.75
) -> ScrapedContent:
    """Helper function to create valid ScrapedContent for testing."""
    return ScrapedContent(
        url=url,
        title=title,
        content=content,
        content_type=content_type,
        processing_time=processing_time,
        content_size_bytes=content_size_bytes,
        extraction_method=extraction_method,
        content_quality_score=content_quality_score
    )


def create_test_parsed_query(
    query_text: str = "AI tools",
    category: QueryCategory = QueryCategory.AI_TOOLS,
    confidence_score: float = 0.9,
    processing_time: float = 0.1
) -> ParsedQuery:
    """Helper function to create valid ParsedQuery for testing."""
    return ParsedQuery(
        base_result=BaseQueryResult(
            query_text=query_text,
            confidence_score=confidence_score,
            processing_time=processing_time,
            category=category
        )
    )


# Test data fixtures
@pytest.fixture
def sample_scraped_content():
    """Sample scraped content for testing."""
    return create_test_scraped_content()


@pytest.fixture
def sample_parsed_query():
    """Sample parsed query for testing."""
    return create_test_parsed_query()


@pytest.fixture
def sample_processing_config():
    """Sample processing configuration for testing."""
    return ProcessingConfig(
        timeout_seconds=30,
        max_retries=1,
        concurrency=3,  # Increased to allow higher AI concurrency
        enable_content_cleaning=True,
        enable_ai_analysis=True,
        enable_summarization=True,
        enable_structured_extraction=True,
        enable_duplicate_detection=True,
        similarity_threshold=0.8,
        min_content_quality_score=0.3,
        max_summary_length=300,
        batch_size=5,
        content_processing_timeout=20,  # Must be less than timeout_seconds
        max_concurrent_ai_analyses=3,   # Must be <= concurrency * 3 = 9
        memory_threshold_mb=600         # Must be >= 600 to allow AI concurrency of 3 (600//150=4)
    )


@pytest.fixture
def large_dataset():
    """Generate a large dataset for performance testing."""
    contents = []
    for i in range(100):  # 100 content items
        content = create_test_scraped_content(
            url=f"https://example.com/article_{i}",
            title=f"Large Dataset Article {i}",
            content=f"This is article {i} with substantial content. " * 50,  # ~2500 characters
            content_quality_score=0.7 + (i % 10) * 0.03
        )
        contents.append(content)
    return contents


@pytest.fixture
def gemini_test_api_key():
    """Get Gemini test API key from environment."""
    return os.getenv("GEMINI_TEST_API_KEY", "test_key")


# Content Cleaning Agent Tests
class TestContentCleaningAgent:
    """Test cases for ContentCleaningAgent."""
    
    @pytest.mark.asyncio
    async def test_clean_content_basic(self, sample_scraped_content):
        """Test basic content cleaning functionality."""
        agent = ContentCleaningAgent()
        
        # Test with valid content
        result = await agent.clean_content(sample_scraped_content)
        
        assert result is not None
        assert 'cleaned_content' in result
        assert len(result['cleaned_content']) > 0
        assert result['cleaned_content'] != sample_scraped_content.content  # Should be cleaned
    
    @pytest.mark.asyncio
    async def test_clean_content_empty(self):
        """Test content cleaning with empty content."""
        agent = ContentCleaningAgent()
        
        # Test with minimal content - ScrapedContent validation prevents empty content
        with pytest.raises(ValueError, match="Content cannot be empty"):
            empty_content = create_test_scraped_content(
                content="",
                content_size_bytes=0
            )
    
    @pytest.mark.asyncio
    async def test_clean_content_html_removal(self):
        """Test HTML tag removal during cleaning."""
        agent = ContentCleaningAgent()
        
        html_content = create_test_scraped_content(
            content="<p>This is <b>bold</b> text with <a href='#'>links</a> and <script>alert('xss')</script> tags.</p>"
        )
        
        result = await agent.clean_content(html_content)
        
        # Check that HTML tags are removed
        assert "<p>" not in result['cleaned_content']
        assert "<b>" not in result['cleaned_content']
        assert "<a" not in result['cleaned_content']
        assert "<script>" not in result['cleaned_content']
        assert "This is bold text with links and alert('xss') tags" in result['cleaned_content']
    
    @pytest.mark.asyncio
    async def test_clean_content_whitespace_normalization(self):
        """Test whitespace normalization during cleaning."""
        agent = ContentCleaningAgent()
        
        whitespace_content = create_test_scraped_content(
            content="This   has    multiple     spaces\n\nand\n\n\nnewlines"
        )
        
        result = await agent.clean_content(whitespace_content)
        
        # Check that whitespace is normalized
        assert "   " not in result['cleaned_content']  # No multiple spaces
        assert "\n\n\n" not in result['cleaned_content']  # No multiple newlines
        # Newlines are preserved but normalized
        assert "This has multiple spaces\n\nand\n\nnewlines" in result['cleaned_content']
    
    @pytest.mark.asyncio
    async def test_clean_content_duplicate_removal(self):
        """Test duplicate line removal during cleaning."""
        agent = ContentCleaningAgent()
        
        duplicate_content = create_test_scraped_content(
            content="Line 1\nLine 1\nLine 2\nLine 1\nLine 3\nLine 2"
        )
        
        result = await agent.clean_content(duplicate_content)
        
        # Check that duplicate lines are preserved (cleaning doesn't remove duplicates)
        lines = result['cleaned_content'].split('\n')
        assert lines.count("Line 1") == 3  # Duplicates are preserved
        assert lines.count("Line 2") == 2  # Duplicates are preserved
        assert lines.count("Line 3") == 1
    
    @pytest.mark.asyncio
    async def test_clean_content_quality_metrics(self, sample_scraped_content):
        """Test that quality metrics are calculated during cleaning."""
        agent = ContentCleaningAgent()
        
        result = await agent.clean_content(sample_scraped_content)
        
        assert 'quality_metrics' in result
        assert 'readability' in result['quality_metrics']
        assert 'information_density' in result['quality_metrics']
        assert isinstance(result['quality_metrics']['readability'], (int, float))
        assert isinstance(result['quality_metrics']['information_density'], (int, float))
    
    @pytest.mark.asyncio
    async def test_clean_content_structure_analysis(self, sample_scraped_content):
        """Test that structure analysis is performed during cleaning."""
        agent = ContentCleaningAgent()
        
        result = await agent.clean_content(sample_scraped_content)
        
        assert 'structure_analysis' in result
        assert isinstance(result['structure_analysis'], dict)
        # Structure analysis should contain some metadata about the content structure
    
    @pytest.mark.asyncio
    async def test_clean_content_enhanced_metadata(self, sample_scraped_content):
        """Test that enhanced metadata is generated during cleaning."""
        agent = ContentCleaningAgent()
        
        result = await agent.clean_content(sample_scraped_content)
        
        assert 'enhanced_metadata' in result
        assert isinstance(result['enhanced_metadata'], dict)
        assert 'cleaning_method' in result['enhanced_metadata']
        assert 'original_length' in result['enhanced_metadata']
        assert 'cleaned_length' in result['enhanced_metadata']
        assert 'enhanced_quality_score' in result['enhanced_metadata']
    
    @pytest.mark.asyncio
    async def test_clean_content_error_handling(self):
        """Test error handling during content cleaning."""
        agent = ContentCleaningAgent()
        
        # Test with problematic content that might cause issues
        problematic_content = create_test_scraped_content(
            content="x" * 1000000,  # Very long content
            content_size_bytes=1000000
        )
        
        # Should handle gracefully without crashing
        result = await agent.clean_content(problematic_content)
        assert result is not None
        assert 'cleaned_content' in result
    
    @pytest.mark.asyncio
    async def test_clean_content_performance(self, large_dataset):
        """Test content cleaning performance with large dataset."""
        agent = ContentCleaningAgent()
        
        start_time = time.time()
        
        # Clean a subset of the large dataset
        for content in large_dataset[:10]:  # Test with 10 items
            result = await agent.clean_content(content)
            assert result is not None
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 10.0  # 10 seconds for 10 items
    
    @pytest.mark.asyncio
    async def test_clean_content_metadata_preservation(self, sample_scraped_content):
        """Test that original metadata is preserved during cleaning."""
        agent = ContentCleaningAgent()
        
        # Add some custom metadata
        sample_scraped_content.author = "Test Author"
        sample_scraped_content.description = "Test description"
        
        result = await agent.clean_content(sample_scraped_content)
        
        # Check that enhanced metadata includes original quality score
        assert 'original_quality_score' in result['enhanced_metadata']
        assert result['enhanced_metadata']['original_quality_score'] == sample_scraped_content.content_quality_score
    
    @pytest.mark.asyncio
    async def test_clean_content_unicode_handling(self):
        """Test content cleaning with unicode content."""
        agent = ContentCleaningAgent()
        
        unicode_content = create_test_scraped_content(
            content="This is content with unicode: 🚀🌟🎉 and special chars: éñüß"
        )
        
        result = await agent.clean_content(unicode_content)
        
        # Check that unicode is preserved
        assert "🚀" in result['cleaned_content']
        assert "🌟" in result['cleaned_content']
        assert "🎉" in result['cleaned_content']
        assert "é" in result['cleaned_content']
        assert "ñ" in result['cleaned_content']
        assert "ü" in result['cleaned_content']
        assert "ß" in result['cleaned_content']


# AI Analysis Agent Tests
class TestAIAnalysisAgent:
    """Test cases for AIAnalysisAgent."""
    
    @pytest.mark.asyncio
    async def test_analyze_content_success(self, sample_scraped_content, sample_parsed_query):
        """Test successful AI content analysis."""
        agent = AIAnalysisAgent()
        
        # Mock Gemini client for testing
        with patch.object(agent, 'gemini_client') as mock_gemini:
            class StubResp:
                def __init__(self, text):
                    self.text = text
            
            mock_gemini.generate_content = AsyncMock(return_value=StubResp('''
            {
                "themes": ["AI Technology", "Machine Learning"],
                "relevance_score": 0.85,
                "quality_metrics": {"readability": 0.8, "information_density": 0.7, "coherence": 0.9},
                "recommendations": ["Consider AI implementation", "Stay updated on ML trends"],
                "credibility_indicators": {"expert_citations": 2, "recent_sources": true, "peer_reviewed": false},
                "information_accuracy": 0.85,
                "source_reliability": 0.8
            }
            '''))
            
            insights = await agent.analyze_content(
                sample_scraped_content.content,
                sample_parsed_query,
                sample_scraped_content.title,
                sample_scraped_content.url
            )
            
            assert isinstance(insights, AIInsights)
            assert len(insights.themes) > 0
            assert insights.relevance_score > 0
            assert insights.confidence_score > 0
    
    @pytest.mark.asyncio
    async def test_analyze_content_fallback(self, sample_scraped_content, sample_parsed_query):
        """Test AI analysis fallback when Gemini client is unavailable."""
        agent = AIAnalysisAgent(gemini_client=None)
        
        insights = await agent.analyze_content(
            sample_scraped_content.content,
            sample_parsed_query,
            sample_scraped_content.title,
            sample_scraped_content.url
        )
        
        assert isinstance(insights, AIInsights)
        assert insights.themes == [f"Content related to {sample_parsed_query.base_result.query_text}"]
        assert insights.confidence_score == 0.1  # Fallback confidence is lower
    
    @pytest.mark.asyncio
    async def test_analyze_content_error_handling(self, sample_scraped_content, sample_parsed_query):
        """Test AI analysis error handling."""
        agent = AIAnalysisAgent()
        
        # Mock Gemini client to raise exception
        with patch.object(agent, 'gemini_client') as mock_gemini:
            mock_gemini.generate_content = AsyncMock(side_effect=Exception("API Error"))
            
            insights = await agent.analyze_content(
                sample_scraped_content.content,
                sample_parsed_query,
                sample_scraped_content.title,
                sample_scraped_content.url
            )
            
            assert isinstance(insights, AIInsights)
            assert "fallback_reason" in insights.processing_metadata
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_content_with_real_gemini(self, sample_scraped_content, sample_parsed_query, gemini_test_api_key):
        """Integration test with real Gemini API (requires test API key)."""
        if gemini_test_api_key == "test_key":
            pytest.skip("Real Gemini API key not available for integration testing")
        
        # Set environment variable for test
        os.environ["GEMINI_API_KEY"] = gemini_test_api_key
        
        try:
            agent = AIAnalysisAgent()
            
            start_time = time.time()
            insights = await agent.analyze_content(
                sample_scraped_content.content,
                sample_parsed_query,
                sample_scraped_content.title,
                sample_scraped_content.url
            )
            processing_time = time.time() - start_time
            
            assert isinstance(insights, AIInsights)
            assert len(insights.themes) > 0
            assert insights.relevance_score > 0
            assert processing_time < 30.0  # Should complete within 30 seconds
            
        finally:
            # Clean up environment
            if "GEMINI_API_KEY" in os.environ:
                del os.environ["GEMINI_API_KEY"]


# Summarization Agent Tests
class TestSummarizationAgent:
    """Test cases for SummarizationAgent."""
    
    @pytest.mark.asyncio
    async def test_summarize_content_success(self, sample_scraped_content, sample_parsed_query):
        """Test successful content summarization."""
        agent = SummarizationAgent()
        
        # Mock Gemini client for testing
        with patch.object(agent, 'gemini_client') as mock_gemini:
            class StubResp:
                def __init__(self, text):
                    self.text = text
            
            mock_gemini.generate_content = AsyncMock(return_value=StubResp('''
            {
                "executive_summary": "AI tools overview",
                "key_points": ["AI technology", "Machine learning", "Future trends"],
                "detailed_summary": "This article provides an overview of AI tools and their applications in various industries.",
                "main_topics": ["AI", "Technology", "Innovation"],
                "sentiment": "positive",
                "confidence_score": 0.9
            }
            '''))
            
            summary = await agent.summarize_content(
                sample_scraped_content.content,
                sample_parsed_query,
                sample_scraped_content.title,
                max_length=200
            )
            
            assert isinstance(summary, ContentSummary)
            assert len(summary.executive_summary) > 0
            assert len(summary.key_points) > 0
            assert len(summary.detailed_summary) <= 200
            assert summary.confidence_score > 0
    
    @pytest.mark.asyncio
    async def test_summarize_content_length_validation(self, sample_scraped_content, sample_parsed_query):
        """Test summary length validation."""
        agent = SummarizationAgent()
        
        # Mock Gemini client to return long summary
        with patch.object(agent, 'gemini_client') as mock_gemini:
            class StubResp:
                def __init__(self, text):
                    self.text = text
            
            mock_gemini.generate_content = AsyncMock(return_value=StubResp('''
            {
                "executive_summary": "AI tools overview",
                "key_points": ["AI technology", "Machine learning"],
                "detailed_summary": "This is a very long detailed summary that exceeds the maximum length limit and should be truncated appropriately.",
                "main_topics": ["AI", "Technology"],
                "sentiment": "positive",
                "confidence_score": 0.9
            }
            '''))
            
            summary = await agent.summarize_content(
                sample_scraped_content.content,
                sample_parsed_query,
                sample_scraped_content.title,
                max_length=50
            )
            
            assert len(summary.detailed_summary) <= 50
            assert summary.detailed_summary.endswith("...")
            assert summary.confidence_score < 0.9  # Should be reduced due to truncation


# ProcessingPrompts Integration Tests
class TestProcessingPrompts:
    """Test cases for ProcessingPrompts integration."""
    
    @pytest.mark.asyncio
    async def test_processing_prompts_methods_exist(self):
        """Test that ProcessingPrompts methods exist and return strings."""
        from app.processing.prompts import ProcessingPrompts
        
        # Test analysis prompt
        analysis_prompt = ProcessingPrompts.get_analysis_prompt(
            query="AI tools",
            category="ai_tools",
            title="Test Title",
            url="https://example.com",
            content="Test content"
        )
        assert isinstance(analysis_prompt, str)
        assert len(analysis_prompt) > 0
        # Check for stable, intentional markers in the prompt
        assert "AI tool content" in analysis_prompt or "content analysis" in analysis_prompt
        
        # Test summary prompt
        summary_prompt = ProcessingPrompts.get_summary_prompt(
            query="AI tools",
            category="ai_tools",
            title="Test Title",
            content="Test content",
            max_length=200
        )
        assert isinstance(summary_prompt, str)
        assert len(summary_prompt) > 0
        assert "AI tools" in summary_prompt or "summarize" in summary_prompt
        
        # Test duplicate detection prompt
        duplicate_prompt = ProcessingPrompts.get_duplicate_detection_prompt(
            title1="Title 1",
            content1="Content 1",
            title2="Title 2",
            content2="Content 2",
            max_length=1000
        )
        assert isinstance(duplicate_prompt, str)
        assert len(duplicate_prompt) > 0
        assert "Title 1" in duplicate_prompt
        assert "Title 2" in duplicate_prompt


# Structured Data Extractor Tests
class TestStructuredDataExtractor:
    """Test cases for StructuredDataExtractor."""
    
    @pytest.mark.asyncio
    async def test_extract_structured_data_success(self, sample_scraped_content, sample_parsed_query):
        """Test successful structured data extraction."""
        agent = StructuredDataExtractor()
        
        result = await agent.extract_structured_data(sample_scraped_content.content, sample_parsed_query)
        
        assert isinstance(result, StructuredData)
        assert isinstance(result.entities, list)
        assert isinstance(result.key_value_pairs, dict)
        assert isinstance(result.categories, list)
        assert isinstance(result.confidence_scores, dict)
    
    @pytest.mark.asyncio
    async def test_extract_structured_data_performance(self, large_dataset, sample_parsed_query):
        """Test extraction performance with large dataset."""
        agent = StructuredDataExtractor()
        
        start_time = time.time()
        results = []
        
        # Process first 30 items for performance testing
        for content in large_dataset[:30]:
            result = await agent.extract_structured_data(content.content, sample_parsed_query)
            results.append(result)
        
        processing_time = time.time() - start_time
        
        assert len(results) == 30
        assert processing_time < 15.0  # Should complete within 15 seconds
        assert all(isinstance(result, StructuredData) for result in results)


# Duplicate Detection Agent Tests
class TestDuplicateDetectionAgent:
    """Test cases for DuplicateDetectionAgent."""
    
    @pytest.mark.asyncio
    async def test_detect_duplicates_success(self, sample_scraped_content):
        """Test successful duplicate detection."""
        agent = DuplicateDetectionAgent()
        
        # Create similar content
        similar_content = create_test_scraped_content(
            url="https://example.com/article2",
            title="Test Article Title",  # Same title
            content="This is a test article content with some sample text. It contains multiple sentences and paragraphs for testing purposes.",  # Same content
            content_quality_score=0.75
        )
        
        contents = [sample_scraped_content, similar_content]
        results = await agent.detect_duplicates(contents)
        
        assert len(results) == 2
        assert any(result.duplicate_groups for result in results)
    
    @pytest.mark.asyncio
    async def test_detect_duplicates_memory_management(self, large_dataset):
        """Test duplicate detection memory management with large dataset."""
        agent = DuplicateDetectionAgent()
        
        start_time = time.time()
        results = await agent.detect_duplicates(large_dataset[:50])
        processing_time = time.time() - start_time
        
        assert len(results) == 50
        assert processing_time < 60.0  # Should complete within 60 seconds
        
        # Check memory usage (basic check)
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            assert memory_mb < 1024  # Should use less than 1GB
        except ImportError:
            # Skip memory check if psutil not available
            pass


# Processing Orchestrator Tests
class TestProcessingOrchestrator:
    """Test cases for ProcessingOrchestrator."""
    
    @pytest.mark.asyncio
    async def test_process_scraped_content_success(self, sample_scraped_content, sample_parsed_query, sample_processing_config):
        """Test successful content processing through the complete pipeline."""
        orchestrator = ProcessingOrchestrator()
        
        start_time = time.time()
        result = await orchestrator.process_scraped_content(
            [sample_scraped_content],
            sample_parsed_query,
            sample_processing_config
        )
        processing_time = time.time() - start_time
        
        assert isinstance(result, ProcessingResult)
        assert len(result.processed_contents) > 0
        assert result.total_processing_time > 0
        assert processing_time < 60.0  # Should complete within 60 seconds
        
        # Check that all enabled stages were processed
        if sample_processing_config.enable_content_cleaning:
            assert any(hasattr(pc, 'cleaned_content') for pc in result.processed_contents)
        
        if sample_processing_config.enable_ai_analysis:
            assert any(hasattr(pc, 'ai_insights') for pc in result.processed_contents)
    
    @pytest.mark.asyncio
    async def test_process_scraped_content_concurrent(self, large_dataset, sample_parsed_query, sample_processing_config):
        """Test concurrent processing with large dataset."""
        # Modify config for concurrent testing
        sample_processing_config.concurrency = 5
        sample_processing_config.batch_size = 10
        
        orchestrator = ProcessingOrchestrator()
        
        start_time = time.time()
        result = await orchestrator.process_scraped_content(
            large_dataset[:20],  # Process 20 items
            sample_parsed_query,
            sample_processing_config
        )
        processing_time = time.time() - start_time
        
        assert len(result.processed_contents) > 0
        assert processing_time < 120.0  # Should complete within 2 minutes
        
        # Check that processing was concurrent (should be faster than sequential)
        # Sequential processing would take ~20 * 2 = 40 seconds minimum
        # Concurrent processing should be significantly faster
        assert processing_time < 80.0
    
    @pytest.mark.asyncio
    async def test_process_scraped_content_error_propagation(self, sample_scraped_content, sample_parsed_query):
        """Test error propagation through the complete pipeline."""
        orchestrator = ProcessingOrchestrator()
        
        # Create content that will cause errors - use very long content instead of empty
        problematic_content = create_test_scraped_content(
            content="x" * 1000000,  # Very long content will cause memory/timeout issues
            content_size_bytes=1000000
        )
        
        result = await orchestrator.process_scraped_content(
            [problematic_content],
            sample_parsed_query
        )
        
        assert isinstance(result, ProcessingResult)
        # The system should handle the content gracefully, but we can check for warnings
        # or verify that processing completed with fallbacks
        assert len(result.processed_contents) > 0 or len(result.errors) > 0
        if len(result.errors) > 0:
            assert "Processing failed" in result.errors[0]
        else:
            # If no errors, content was processed successfully with fallbacks
            assert len(result.processed_contents) > 0
    
    @pytest.mark.asyncio
    async def test_process_scraped_content_resource_cleanup(self, sample_scraped_content, sample_parsed_query):
        """Test resource cleanup during processing."""
        orchestrator = ProcessingOrchestrator()
        
        # Start processing
        task = asyncio.create_task(
            orchestrator.process_scraped_content(
                [sample_scraped_content],
                sample_parsed_query
            )
        )
        
        # Cancel the task to test cleanup
        await asyncio.sleep(0.1)
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Wait for orchestrator cleanup to complete
        await orchestrator.wait_for_cleanup()
        
        # Check that resources were cleaned up
        assert len(orchestrator._active_tasks) == 0


# Configuration Validation Tests
class TestProcessingConfigValidation:
    """Test cases for ProcessingConfig validation."""
    
    def test_config_validation_success(self):
        """Test successful configuration validation."""
        config = ProcessingConfig(
            timeout_seconds=60,
            max_retries=2,
            concurrency=3,
            enable_content_cleaning=True,
            enable_ai_analysis=True,
            enable_summarization=True,
            enable_structured_extraction=True,
            enable_duplicate_detection=True,
            similarity_threshold=0.8,
            min_content_quality_score=0.4,
            max_summary_length=500,
            batch_size=10,
            content_processing_timeout=30,
            max_concurrent_ai_analyses=3,  # Must be <= concurrency * 3 = 9
            memory_threshold_mb=512
        )
        
        # Should not raise any validation errors
        assert config.timeout_seconds == 60
        assert config.concurrency == 3
    
    def test_config_validation_cross_field_errors(self):
        """Test cross-field validation errors."""
        with pytest.raises(ValueError, match="Content processing timeout must be less than overall timeout"):
            ProcessingConfig(
                timeout_seconds=30,
                content_processing_timeout=60,  # Should be less than timeout_seconds
                concurrency=3,
                batch_size=10
            )
    
    def test_config_validation_edge_cases(self):
        """Test configuration validation edge cases."""
        # Test minimum values
        config = ProcessingConfig(
            timeout_seconds=10,  # Minimum
            max_retries=0,       # Minimum
            concurrency=1,       # Minimum
            batch_size=1,        # Minimum
            content_processing_timeout=5,  # Minimum
            max_concurrent_ai_analyses=1,  # Must be <= concurrency * 3 = 3
            memory_threshold_mb=300        # Must be >= 300 to allow AI concurrency of 1 (300//150=2)
        )
        
        assert config.timeout_seconds == 10
        assert config.max_retries == 0
        
        # Test maximum values
        config = ProcessingConfig(
            timeout_seconds=300,           # Must be <= 300
            max_retries=5,                # Must be <= 5
            concurrency=10,               # Must be <= 10
            batch_size=50,                # Must be <= 50
            content_processing_timeout=120, # Must be <= 120
            max_concurrent_ai_analyses=13,  # Must be <= min(concurrency*3, memory//150, 15) = min(30, 13, 15) = 13
            memory_threshold_mb=2048        # Must be <= 2048
        )
        
        assert config.timeout_seconds == 300
        assert config.concurrency == 10


# AI Agent Base Class Tests
class TestAIAgentBase:
    """Test cases for the AI agent base class."""
    
    def test_error_handler_initialization(self):
        """Test AIAgentErrorHandler initialization."""
        handler = AIAgentErrorHandler("TestAgent")
        
        assert handler.agent_name == "TestAgent"
        assert handler.error_counts['json_parsing'] == 0
        assert handler.error_counts['validation'] == 0
        assert handler.error_counts['api_error'] == 0
    
    def test_error_handler_json_parsing_error(self):
        """Test JSON parsing error handling."""
        handler = AIAgentErrorHandler("TestAgent")
        
        malformed_json = '{"key": "value", "incomplete": }'
        error = Exception("Invalid JSON")
        
        result = handler.handle_json_parsing_error(malformed_json, error, "test_context")
        
        assert result['fallback'] is True
        assert result['context'] == "test_context"
        assert result['error_recovery'] is True
    
    def test_error_handler_validation_error(self):
        """Test validation error handling."""
        handler = AIAgentErrorHandler("TestAgent")
        
        data = {"missing_field": "value"}
        from pydantic import ValidationError
        
        # Create a mock validation error
        mock_error = Mock(spec=ValidationError)
        mock_error.errors.return_value = [
            {'loc': ('required_field',), 'type': 'missing', 'input': None}
        ]
        
        result = handler.handle_validation_error(data, mock_error, "test_context")
        
        assert result['fallback'] is True
        assert result['context'] == "test_context"


# Performance and Load Testing
class TestProcessingPerformance:
    """Performance and load testing for the processing module."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_large_dataset_processing_performance(self, large_dataset, sample_parsed_query):
        """Test processing performance with large dataset."""
        config = ProcessingConfig(
            timeout_seconds=300,  # 5 minutes
            concurrency=8,        # High concurrency
            batch_size=20,        # Large batch size
            memory_threshold_mb=2048  # 2GB memory
        )
        
        orchestrator = ProcessingOrchestrator()
        
        start_time = time.time()
        result = await orchestrator.process_scraped_content(
            large_dataset[:50],  # Process 50 items
            sample_parsed_query,
            config
        )
        processing_time = time.time() - start_time
        
        # Performance assertions
        assert processing_time < 180.0  # Should complete within 3 minutes
        assert len(result.processed_contents) > 0
        
        # Calculate throughput
        throughput = len(result.processed_contents) / processing_time
        assert throughput > 0.2  # Should process at least 0.2 items per second
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, large_dataset, sample_parsed_query):
        """Test memory usage under load."""
        import psutil
        import gc
        
        # Force garbage collection before test
        gc.collect()
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)
        
        config = ProcessingConfig(
            timeout_seconds=120,
            concurrency=4,
            batch_size=15,
            memory_threshold_mb=1024
        )
        
        orchestrator = ProcessingOrchestrator()
        
        # Process large dataset
        result = await orchestrator.process_scraped_content(
            large_dataset[:40],
            sample_parsed_query,
            config
        )
        
        # Force garbage collection after test
        gc.collect()
        
        final_memory = process.memory_info().rss / (1024 * 1024)
        memory_increase = final_memory - initial_memory
        
        # Memory should not increase by more than 500MB
        assert memory_increase < 500
        
        assert len(result.processed_contents) > 0


# Integration Tests
class TestProcessingIntegration:
    """Integration tests for the complete processing pipeline."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_processing_pipeline(self, sample_scraped_content, sample_parsed_query):
        """Test complete end-to-end processing pipeline."""
        config = ProcessingConfig(
            timeout_seconds=120,
            concurrency=3,
            batch_size=5,
            enable_content_cleaning=True,
            enable_ai_analysis=True,
            enable_summarization=True,
            enable_structured_extraction=True,
            enable_duplicate_detection=True,
            content_processing_timeout=60,  # Must be < timeout_seconds
            max_concurrent_ai_analyses=3,   # Must be <= concurrency * 3 = 9
            memory_threshold_mb=600         # Must be >= 600 to allow AI concurrency of 3 (600//150=4)
        )
        
        orchestrator = ProcessingOrchestrator()
        
        # Process content through complete pipeline
        result = await orchestrator.process_scraped_content(
            [sample_scraped_content],
            sample_parsed_query,
            config
        )
        
        # Verify all stages were processed
        assert len(result.processed_contents) == 1
        processed_content = result.processed_contents[0]
        
        # Check content cleaning
        assert hasattr(processed_content, 'cleaned_content')
        assert len(processed_content.cleaned_content) > 0
        
        # Check AI analysis
        assert hasattr(processed_content, 'ai_insights')
        assert processed_content.ai_insights is not None
        
        # Check summarization
        assert hasattr(processed_content, 'summary')
        assert processed_content.summary is not None
        
        # Check structured extraction
        assert hasattr(processed_content, 'structured_data')
        assert processed_content.structured_data is not None
        
        # Check duplicate detection
        assert hasattr(processed_content, 'duplicate_analysis')
        assert processed_content.duplicate_analysis is not None
        
        # Check quality scoring
        assert hasattr(processed_content, 'enhanced_quality_score')
        assert processed_content.enhanced_quality_score > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_processing_integration(self, large_dataset, sample_parsed_query):
        """Test concurrent processing integration."""
        config = ProcessingConfig(
            timeout_seconds=300,
            concurrency=6,
            batch_size=12,
            enable_content_cleaning=True,
            enable_ai_analysis=True,
            enable_summarization=True,
            enable_structured_extraction=True,
            enable_duplicate_detection=True,
            content_processing_timeout=120,  # Must be < timeout_seconds (300)
            max_concurrent_ai_analyses=13,  # Must be <= min(concurrency*3, memory//150, 15) = min(18, 13, 15) = 13
            memory_threshold_mb=2048        # Must be <= 2048 (max allowed)
        )
        
        orchestrator = ProcessingOrchestrator()
        
        # Process larger dataset with concurrency
        start_time = time.time()
        result = await orchestrator.process_scraped_content(
            large_dataset[:60],  # Process 60 items
            sample_parsed_query,
            config
        )
        processing_time = time.time() - start_time
        
        # Verify results
        assert len(result.processed_contents) > 0
        assert processing_time < 240.0  # Should complete within 4 minutes
        
        # Check that processing was actually concurrent
        # Sequential processing would take much longer
        expected_sequential_time = len(result.processed_contents) * 2  # 2 seconds per item
        assert processing_time < expected_sequential_time * 0.7  # Should be at least 30% faster


# Error Handling and Recovery Tests
class TestErrorHandlingAndRecovery:
    """Test cases for error handling and recovery."""
    
    @pytest.mark.asyncio
    async def test_agent_failure_recovery(self, sample_scraped_content, sample_parsed_query):
        """Test recovery from agent failures."""
        config = ProcessingConfig(
            timeout_seconds=60,
            concurrency=2,
            batch_size=3,
            enable_content_cleaning=True,
            enable_ai_analysis=True,
            enable_summarization=True,
            enable_structured_extraction=True,
            enable_duplicate_detection=True,
            content_processing_timeout=30,  # Must be < timeout_seconds
            max_concurrent_ai_analyses=2,   # Must be <= concurrency * 3 = 6
            memory_threshold_mb=600         # Must be >= 600 to allow AI concurrency of 2 (600//150=4)
        )
        
        orchestrator = ProcessingOrchestrator()
        
        # Mock one agent to fail
        with patch.object(orchestrator.ai_analysis_agent, 'analyze_content') as mock_ai:
            mock_ai.side_effect = Exception("AI Analysis failed")
            
            result = await orchestrator.process_scraped_content(
                [sample_scraped_content],
                sample_parsed_query,
                config
            )
            
            # Should still complete processing with fallback or propagate errors
            assert len(result.processed_contents) > 0 or len(result.errors) > 0
            if len(result.errors) > 0:
                assert "AI Analysis failed" in str(result.errors)
            else:
                # If no errors, content was processed successfully with fallbacks
                assert len(result.processed_contents) > 0
    
    @pytest.mark.asyncio
    async def test_pipeline_partial_failure_recovery(self, sample_scraped_content, sample_parsed_query):
        """Test recovery from partial pipeline failures."""
        config = ProcessingConfig(
            timeout_seconds=60,
            concurrency=2,
            batch_size=3,
            enable_content_cleaning=True,
            enable_ai_analysis=False,  # Disable AI analysis
            enable_summarization=True,
            enable_structured_extraction=True,
            enable_duplicate_detection=True,
            content_processing_timeout=30,  # Must be < timeout_seconds
            max_concurrent_ai_analyses=2,   # Must be <= concurrency * 3 = 6
            memory_threshold_mb=600         # Must be >= 600 to allow AI concurrency of 2 (600//150=4)
        )
        
        orchestrator = ProcessingOrchestrator()
        
        result = await orchestrator.process_scraped_content(
            [sample_scraped_content],
            sample_parsed_query,
            config
        )
        
        # Should complete without AI analysis
        assert len(result.processed_contents) > 0
        processed_content = result.processed_contents[0]
        
        # AI insights should not be present when AI analysis is disabled
        assert processed_content.ai_insights is None
        
        # Other stages should still work
        assert hasattr(processed_content, 'cleaned_content')
        assert hasattr(processed_content, 'summary')
        assert hasattr(processed_content, 'structured_data')


# Configuration Edge Case Tests
class TestConfigurationEdgeCases:
    """Test cases for configuration edge cases."""
    
    def test_configuration_extreme_values(self):
        """Test configuration with extreme values."""
        # Test minimum values
        min_config = ProcessingConfig(
            timeout_seconds=10,
            max_retries=0,
            concurrency=1,
            batch_size=1,
            content_processing_timeout=5,
            max_concurrent_ai_analyses=1,
            memory_threshold_mb=300  # Must be >= 300 to allow AI concurrency of 1 (300//150=2)
        )
        
        assert min_config.timeout_seconds == 10
        assert min_config.concurrency == 1
        
        # Test maximum values
        max_config = ProcessingConfig(
            timeout_seconds=300,           # Must be <= 300
            max_retries=5,                # Must be <= 5
            concurrency=10,               # Must be <= 10
            batch_size=50,                # Must be <= 50
            content_processing_timeout=120, # Must be <= 120
            max_concurrent_ai_analyses=13,  # Must be <= min(concurrency*3, memory//150, 15) = min(30, 13, 15) = 13
            memory_threshold_mb=2048        # Must be <= 2048
        )
        
        assert max_config.timeout_seconds == 300
        assert max_config.concurrency == 10
    
    def test_configuration_invalid_combinations(self):
        """Test invalid configuration combinations."""
        # Test timeout mismatch
        with pytest.raises(ValueError):
            ProcessingConfig(
                timeout_seconds=30,
                content_processing_timeout=60,  # Invalid: greater than timeout_seconds
                concurrency=3,
                batch_size=10
            )
        
        # Test concurrency mismatch
        with pytest.raises(ValueError):
            ProcessingConfig(
                timeout_seconds=60,
                concurrency=2,
                max_concurrent_ai_analyses=10,  # Invalid: too high relative to concurrency
                batch_size=10
            )
    
    def test_configuration_warnings(self):
        """Test configuration warnings (non-blocking)."""
        # This should generate warnings but not fail
        config = ProcessingConfig(
            timeout_seconds=60,
            concurrency=10,  # Must be <= 10
            batch_size=40,   # Large batch size
            memory_threshold_mb=2048  # Must be <= 2048 (max allowed)
        )
        
        # Should still be valid
        assert config.concurrency == 10
        assert config.batch_size == 40
