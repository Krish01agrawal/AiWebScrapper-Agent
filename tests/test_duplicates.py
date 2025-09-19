import pytest
from unittest.mock import Mock, AsyncMock
from app.processing.duplicates import DuplicateDetectionAgent
from app.scraper.schemas import ScrapedContent


class TestDuplicateDetectionAgent:
    """Test cases for DuplicateDetectionAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create a DuplicateDetectionAgent instance for testing."""
        return DuplicateDetectionAgent()
    
    @pytest.fixture
    def sample_contents(self):
        """Create sample ScrapedContent objects for testing."""
        return [
            ScrapedContent(
                url="https://example.com/page1",
                title="Example Page 1",
                content="This is some sample content for testing duplicate detection.",
                content_quality_score=0.8,
                processing_time=1.0,
                content_size_bytes=1024,
                extraction_method="test"
            ),
            ScrapedContent(
                url="https://example.com/page2",
                title="Example Page 2", 
                content="This is different content that should not be a duplicate.",
                content_quality_score=0.7,
                processing_time=1.0,
                content_size_bytes=1024,
                extraction_method="test"
            ),
            ScrapedContent(
                url="https://example.com/page3",  # Different URL
                title="Example Page 3",  # Different title
                content="This is some sample content for testing duplicate detection.",  # Similar content
                content_quality_score=0.6,
                processing_time=1.0,
                content_size_bytes=1024,
                extraction_method="test"
            )
        ]
    
    def test_generate_content_id(self, agent, sample_contents):
        """Test that content ID generation works correctly."""
        content1 = sample_contents[0]
        content2 = sample_contents[1]
        content3 = sample_contents[2]
        
        # Generate IDs
        id1 = agent._generate_content_id(content1)
        id2 = agent._generate_content_id(content2)
        id3 = agent._generate_content_id(content3)
        
        # IDs should be deterministic
        assert id1 == agent._generate_content_id(content1)
        assert id2 == agent._generate_content_id(content2)
        
        # Similar content should have different IDs (different URLs/titles)
        assert id1 != id3
        
        # Different content should have different IDs
        assert id1 != id2
        
        # IDs should be strings
        assert isinstance(id1, str)
        assert isinstance(id2, str)
    
    def test_detect_url_duplicates(self, agent, sample_contents):
        """Test URL-based duplicate detection."""
        duplicates = agent._detect_url_duplicates(sample_contents)
        
        # Should find no URL duplicates (all URLs are different)
        assert len(duplicates) == 0
        
        # Verify that all content has different URLs
        urls = [content.url for content in sample_contents]
        assert len(set(urls)) == len(urls)
    
    @pytest.mark.asyncio
    async def test_combine_duplicate_results(self, agent, sample_contents):
        """Test that duplicate results combination works with generated IDs."""
        # Create some mock duplicate groups
        exact_duplicates = [[
            agent._generate_content_id(sample_contents[0]),
            agent._generate_content_id(sample_contents[2])
        ]]
        
        near_duplicates = []
        url_duplicates = [[
            agent._generate_content_id(sample_contents[0]),
            agent._generate_content_id(sample_contents[2])
        ]]
        
        # Combine results
        results = await agent._combine_duplicate_results(
            sample_contents, exact_duplicates, near_duplicates, url_duplicates
        )
        
        # Should have results for all content
        assert len(results) == len(sample_contents)
        
        # First and third content should have duplicates (similar content)
        content1_id = agent._generate_content_id(sample_contents[0])
        content3_id = agent._generate_content_id(sample_contents[2])
        

        
        # Find the analysis for content1
        content1_analysis = next(r for r in results if r.content_id == content1_id)
        assert content1_analysis.has_duplicates is True
        
        # Find the analysis for content3
        content3_analysis = next(r for r in results if r.content_id == content3_id)
        assert content3_analysis.has_duplicates is True
        
        # Second content should not have duplicates
        content2_id = agent._generate_content_id(sample_contents[1])
        content2_analysis = next(r for r in results if r.content_id == content2_id)
        assert content2_analysis.has_duplicates is False
    
    def test_no_attribute_error_on_scraped_content(self, agent, sample_contents):
        """Test that no AttributeError occurs when accessing ScrapedContent objects."""
        # This test ensures that we don't try to access non-existent content.id
        for content in sample_contents:
            # Should not raise AttributeError
            content_id = agent._generate_content_id(content)
            assert isinstance(content_id, str)
            
            # Verify we can access the fields we actually use
            assert hasattr(content, 'url')
            assert hasattr(content, 'title')
            assert hasattr(content, 'content')
            assert hasattr(content, 'content_quality_score')
            
            # Verify we don't try to access non-existent content.id
            assert not hasattr(content, 'id')
