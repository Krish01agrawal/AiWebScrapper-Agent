"""
Comprehensive tests for the database module.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

from app.database.models import (
    QueryDocument, ScrapedContentDocument, ProcessedContentDocument,
    QuerySessionDocument, AnalyticsDocument, DocumentStatus
)
from app.database.repositories.queries import QueryRepository
from app.database.repositories.content import ScrapedContentRepository
from app.database.repositories.processed import ProcessedContentRepository
from app.database.repositories.analytics import AnalyticsRepository
from app.database.service import DatabaseService
from app.database.indexes import IndexManager
from app.database.migrations import MigrationManager


@pytest.fixture
def mock_database():
    """Mock database for testing."""
    mock_db = AsyncMock(spec=AsyncIOMotorDatabase)
    mock_db.queries = AsyncMock(spec=AsyncIOMotorCollection)
    mock_db.content = AsyncMock(spec=AsyncIOMotorCollection)
    mock_db.processed_content = AsyncMock(spec=AsyncIOMotorCollection)
    mock_db.processed_cache = AsyncMock(spec=AsyncIOMotorCollection)
    mock_db.query_sessions = AsyncMock(spec=AsyncIOMotorCollection)
    mock_db.analytics = AsyncMock(spec=AsyncIOMotorCollection)
    mock_db.migrations = AsyncMock(spec=AsyncIOMotorCollection)
    return mock_db


@pytest.fixture
def sample_query_document():
    """Sample query document for testing."""
    return QueryDocument(
        base_result={
            "query_text": "test query",
            "confidence_score": 0.95,
            "timestamp": datetime.utcnow(),
            "processing_time": 1.2,
            "category": "ai_tools"
        },
        session_id="test_session",
        user_id="test_user",
        status=DocumentStatus.PENDING
    )


@pytest.fixture
def sample_content_document():
    """Sample content document for testing."""
    return ScrapedContentDocument(
        url="https://example.com/test",
        title="Test Content",
        content="This is test content",
        content_type="article",
        processing_time=2.5,
        content_size_bytes=1024,
        extraction_method="test_extraction"
    )


@pytest.fixture
def sample_processed_document():
    """Sample processed document for testing."""
    return ProcessedContentDocument(
        original_content_id=ObjectId(),
        cleaned_content="Cleaned test content",
        summary={
            "executive_summary": "Test summary",
            "key_points": ["Point 1", "Point 2"],
            "detailed_summary": "Detailed test summary",
            "main_topics": ["Topic 1"],
            "sentiment": "positive",
            "confidence_score": 0.9
        },
        structured_data={
            "entities": [],
            "key_value_pairs": {},
            "categories": ["Test"],
            "confidence_scores": {},
            "tables": [],
            "measurements": []
        },
        processing_duration=3.0,
        enhanced_quality_score=0.85,
        processing_errors=[]
    )


class TestQueryRepository:
    """Test QueryRepository functionality."""
    
    @pytest.mark.asyncio
    async def test_save_query_success(self, mock_database, sample_query_document):
        """Test successful query saving."""
        # Setup mock
        mock_database.queries.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        # Test
        repo = QueryRepository(mock_database)
        result = await repo.save_query(sample_query_document)
        
        # Assertions
        assert result.id is not None
        mock_database.queries.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_query_by_id_success(self, mock_database, sample_query_document):
        """Test successful query retrieval by ID."""
        # Setup mock
        query_id = ObjectId()
        mock_database.queries.find_one.return_value = sample_query_document.model_dump(by_alias=True)
        
        # Test
        repo = QueryRepository(mock_database)
        result = await repo.get_query_by_id(query_id)
        
        # Assertions
        assert result is not None
        assert isinstance(result, QueryDocument)
        mock_database.queries.find_one.assert_called_once_with({"_id": query_id})
    
    @pytest.mark.asyncio
    async def test_get_query_by_id_not_found(self, mock_database):
        """Test query retrieval when not found."""
        # Setup mock
        mock_database.queries.find_one.return_value = None
        
        # Test
        repo = QueryRepository(mock_database)
        result = await repo.get_query_by_id(ObjectId())
        
        # Assertions
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_query_status_success(self, mock_database):
        """Test successful query status update."""
        # Setup mock
        mock_database.queries.update_one.return_value = MagicMock(modified_count=1)
        
        # Test
        repo = QueryRepository(mock_database)
        result = await repo.update_query_status(
            ObjectId(), 
            DocumentStatus.COMPLETED, 
            execution_time=10.5
        )
        
        # Assertions
        assert result is True
        mock_database.queries.update_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_queries_success(self, mock_database, sample_query_document):
        """Test successful query search."""
        # Setup mock
        mock_database.queries.find.return_value.to_list.return_value = [
            sample_query_document.model_dump(by_alias=True)
        ]
        
        # Test
        repo = QueryRepository(mock_database)
        results = await repo.search_queries("test query")
        
        # Assertions
        assert len(results) == 1
        assert isinstance(results[0], QueryDocument)
    
    @pytest.mark.asyncio
    async def test_get_query_statistics_success(self, mock_database):
        """Test successful query statistics retrieval."""
        # Setup mock
        mock_database.queries.aggregate.return_value.to_list.return_value = [{
            "total_queries": 10,
            "successful_queries": 8,
            "failed_queries": 2,
            "avg_execution_time": 5.5,
            "avg_quality_score": 0.85,
            "total_execution_time": 55.0
        }]
        
        # Test
        repo = QueryRepository(mock_database)
        stats = await repo.get_query_statistics()
        
        # Assertions
        assert stats["total_queries"] == 10
        assert stats["successful_queries"] == 8
        assert stats["failed_queries"] == 2
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_database):
        """Test successful health check."""
        # Setup mock
        mock_database.queries.count_documents.return_value = 100
        mock_database.queries.find_one.return_value = {"_id": ObjectId()}
        mock_database.queries.list_indexes.return_value.to_list.return_value = [
            {"name": "index1"}, {"name": "index2"}
        ]
        
        # Test
        repo = QueryRepository(mock_database)
        health = await repo.health_check()
        
        # Assertions
        assert health["status"] == "healthy"
        assert health["document_count"] == 100
        assert health["index_count"] == 2


class TestScrapedContentRepository:
    """Test ScrapedContentRepository functionality."""
    
    @pytest.mark.asyncio
    async def test_save_scraped_content_success(self, mock_database, sample_content_document):
        """Test successful content saving."""
        # Setup mock
        mock_database.content.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        mock_database.content.find_one.return_value = None  # No duplicates
        
        # Test
        repo = ScrapedContentRepository(mock_database)
        result = await repo.save_scraped_content(sample_content_document)
        
        # Assertions
        assert result.id is not None
        assert result.content_hash is not None
        mock_database.content.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bulk_save_content_success(self, mock_database, sample_content_document):
        """Test successful bulk content saving."""
        # Setup mock
        mock_database.content.insert_many.return_value = MagicMock(inserted_ids=[ObjectId(), ObjectId()])
        mock_database.content.find.return_value.to_list.return_value = []  # No duplicates
        
        # Test
        repo = ScrapedContentRepository(mock_database)
        content_docs = [sample_content_document, sample_content_document]
        results = await repo.bulk_save_content(content_docs)
        
        # Assertions
        assert len(results) == 2
        mock_database.content.insert_many.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_content_by_query_success(self, mock_database, sample_content_document):
        """Test successful content retrieval by query."""
        # Setup mock
        mock_database.content.find.return_value.to_list.return_value = [
            sample_content_document.model_dump(by_alias=True)
        ]
        
        # Test
        repo = ScrapedContentRepository(mock_database)
        results = await repo.get_content_by_query(ObjectId())
        
        # Assertions
        assert len(results) == 1
        assert isinstance(results[0], ScrapedContentDocument)
    
    @pytest.mark.asyncio
    async def test_search_content_success(self, mock_database, sample_content_document):
        """Test successful content search."""
        # Setup mock
        mock_database.content.find.return_value.to_list.return_value = [
            sample_content_document.model_dump(by_alias=True)
        ]
        
        # Test
        repo = ScrapedContentRepository(mock_database)
        results = await repo.search_content("test content")
        
        # Assertions
        assert len(results) == 1
        assert isinstance(results[0], ScrapedContentDocument)
    
    @pytest.mark.asyncio
    async def test_get_content_stats_success(self, mock_database):
        """Test successful content statistics retrieval."""
        # Setup mock
        mock_database.content.aggregate.return_value.to_list.return_value = [{
            "total_content": 50,
            "total_size_bytes": 1024000,
            "avg_processing_time": 2.5,
            "avg_quality_score": 0.8,
            "avg_relevance_score": 0.75,
            "unique_domains": ["example.com", "test.com"],
            "content_types": ["article", "blog_post"]
        }]
        
        # Test
        repo = ScrapedContentRepository(mock_database)
        stats = await repo.get_content_stats()
        
        # Assertions
        assert stats["total_content"] == 50
        assert stats["total_size_bytes"] == 1024000
        assert stats["unique_domains"] == 2
    
    @pytest.mark.asyncio
    async def test_cross_url_duplicate_detection(self, mock_database):
        """Test cross-URL duplicate detection with normalized content hashing."""
        # Setup mock
        mock_database.content.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        mock_database.content.find_one.return_value = None  # No existing content initially
        
        # Test
        repo = ScrapedContentRepository(mock_database)
        
        # Create two content documents with same content but different URLs
        content1 = ScrapedContentDocument(
            url="https://example.com/article?ref=social",
            title="Test Article",
            content="This is the same content with extra spaces   and different case.",
            content_type="article",
            processing_time=2.5,
            content_size_bytes=1024,
            extraction_method="test_extraction"
        )
        
        content2 = ScrapedContentDocument(
            url="https://example.com/article?utm_source=email",
            title="Different Title",
            content="THIS IS THE SAME CONTENT WITH EXTRA SPACES AND DIFFERENT CASE.",
            content_type="article",
            processing_time=2.5,
            content_size_bytes=1024,
            extraction_method="test_extraction"
        )
        
        # Save first content
        result1 = await repo.save_scraped_content(content1)
        
        # Mock finding existing content for second save
        mock_database.content.find_one.return_value = result1.model_dump(by_alias=True)
        
        # Save second content - should be detected as duplicate
        result2 = await repo.save_scraped_content(content2)
        
        # Assertions
        assert result1.content_hash == result2.content_hash  # Same hash due to normalization
        assert result2.duplicate_of == result1.id  # Second content marked as duplicate


class TestProcessedContentRepository:
    """Test ProcessedContentRepository functionality."""
    
    @pytest.mark.asyncio
    async def test_save_processed_content_success(self, mock_database, sample_processed_document):
        """Test successful processed content saving."""
        # Setup mock
        mock_database.processed_content.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        # Test
        repo = ProcessedContentRepository(mock_database)
        result = await repo.save_processed_content(sample_processed_document)
        
        # Assertions
        assert result.id is not None
        mock_database.processed_content.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_processed_by_query_success(self, mock_database, sample_processed_document):
        """Test successful processed content retrieval by query."""
        # Setup mock
        mock_database.processed_content.find.return_value.to_list.return_value = [
            sample_processed_document.model_dump(by_alias=True)
        ]
        
        # Test
        repo = ProcessedContentRepository(mock_database)
        results = await repo.get_processed_by_query(ObjectId())
        
        # Assertions
        assert len(results) == 1
        assert isinstance(results[0], ProcessedContentDocument)
    
    @pytest.mark.asyncio
    async def test_search_processed_content_success(self, mock_database, sample_processed_document):
        """Test successful processed content search."""
        # Setup mock
        mock_database.processed_content.find.return_value.to_list.return_value = [
            sample_processed_document.model_dump(by_alias=True)
        ]
        
        # Test
        repo = ProcessedContentRepository(mock_database)
        results = await repo.search_processed_content("test content")
        
        # Assertions
        assert len(results) == 1
        assert isinstance(results[0], ProcessedContentDocument)
    
    @pytest.mark.asyncio
    async def test_get_analytics_data_success(self, mock_database):
        """Test successful analytics data retrieval."""
        # Setup mock
        mock_database.processed_content.aggregate.return_value.to_list.return_value = [{
            "total_processed": 25,
            "avg_processing_duration": 3.5,
            "avg_quality_score": 0.82,
            "total_processing_time": 87.5,
            "avg_memory_usage": 45.2,
            "avg_cpu_time": 2.1,
            "error_count": 2,
            "processing_versions": ["1.0"]
        }]
        
        # Test
        repo = ProcessedContentRepository(mock_database)
        analytics = await repo.get_analytics_data()
        
        # Assertions
        assert analytics["total_processed"] == 25
        assert analytics["avg_processing_duration"] == 3.5
        assert analytics["avg_quality_score"] == 0.82

    @pytest.mark.asyncio
    async def test_cache_round_trip_with_extra_fields(self, mock_database, sample_processed_document):
        """Test cache round-trip with extra fields like expires_at and cache_key."""
        from datetime import datetime, timedelta
        
        # Setup mock for caching
        mock_database.processed_cache.update_one.return_value = MagicMock(upserted_id=ObjectId())
        
        # Setup mock for cache retrieval
        cached_doc_data = sample_processed_document.model_dump(by_alias=True)
        cached_doc_data["cache_key"] = "test_cache_key"
        cached_doc_data["expires_at"] = datetime.utcnow() + timedelta(hours=1)
        mock_database.processed_cache.find_one.return_value = cached_doc_data
        
        # Test caching
        repo = ProcessedContentRepository(mock_database)
        cache_success = await repo.cache_processed_results("test_cache_key", sample_processed_document, 3600)
        assert cache_success is True
        
        # Test cache retrieval
        cached_result = await repo.get_cached_results("test_cache_key")
        
        # Assertions - should handle extra fields gracefully
        assert cached_result is not None
        assert isinstance(cached_result, ProcessedContentDocument)
        assert cached_result.cache_key == "test_cache_key"
        assert cached_result.expires_at is not None


class TestAnalyticsRepository:
    """Test AnalyticsRepository functionality."""
    
    @pytest.mark.asyncio
    async def test_create_session_success(self, mock_database):
        """Test successful session creation."""
        # Setup mock
        mock_database.query_sessions.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        # Test
        repo = AnalyticsRepository(mock_database)
        result = await repo.create_session("test_session", "test_user")
        
        # Assertions
        assert result.id is not None
        assert result.session_id == "test_session"
        assert result.user_id == "test_user"
        mock_database.query_sessions.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_session_success(self, mock_database):
        """Test successful session update."""
        # Setup mock
        mock_database.query_sessions.update_one.return_value = MagicMock(modified_count=1)
        
        # Test
        repo = AnalyticsRepository(mock_database)
        result = await repo.update_session("test_session", query_count=5)
        
        # Assertions
        assert result is True
        mock_database.query_sessions.update_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_end_session_success(self, mock_database):
        """Test successful session ending."""
        # Setup mock
        mock_database.query_sessions.find_one.return_value = {
            "start_time": datetime.utcnow() - timedelta(minutes=30),
            "query_count": 5,
            "total_processing_time": 25.0
        }
        mock_database.query_sessions.update_one.return_value = MagicMock(modified_count=1)
        
        # Test
        repo = AnalyticsRepository(mock_database)
        result = await repo.end_session("test_session")
        
        # Assertions
        assert result is True
        mock_database.query_sessions.update_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_usage_statistics_success(self, mock_database):
        """Test successful usage statistics retrieval."""
        # Setup mock
        mock_database.query_sessions.aggregate.return_value.to_list.return_value = [{
            "total_sessions": 100,
            "unique_users": ["user1", "user2"],
            "total_queries": 500,
            "successful_queries": 450,
            "failed_queries": 50,
            "total_processing_time": 2500.0,
            "total_content_scraped": 1000,
            "total_content_processed": 950,
            "avg_session_duration": 300.0,
            "avg_quality_score": 0.85,
            "avg_relevance_score": 0.82
        }]
        
        # Test
        repo = AnalyticsRepository(mock_database)
        stats = await repo.get_usage_statistics()
        
        # Assertions
        assert stats["total_sessions"] == 100
        assert stats["unique_users"] == 2
        assert stats["total_queries"] == 500


class TestDatabaseService:
    """Test DatabaseService functionality."""
    
    @pytest.mark.asyncio
    async def test_process_and_store_query_success(self, mock_database):
        """Test successful query processing and storage."""
        # Setup mocks
        mock_database.queries.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        mock_database.query_sessions.find_one.return_value = None  # No existing session
        mock_database.query_sessions.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        # Test
        service = DatabaseService(mock_database)
        
        # Create a mock ParsedQuery
        from app.agents.schemas import ParsedQuery, BaseQueryResult, QueryCategory
        parsed_query = ParsedQuery(
            base_result=BaseQueryResult(
                query_text="test query",
                confidence_score=0.95,
                processing_time=1.2,
                category=QueryCategory.GENERAL
            )
        )
        
        result = await service.process_and_store_query(parsed_query, "test_session", "test_user")
        
        # Assertions
        assert len(result) == 2  # Returns (query_doc, session_id)
        assert isinstance(result[0], QueryDocument)
        assert result[1] == "test_session"
    
    @pytest.mark.asyncio
    async def test_get_system_health_success(self, mock_database):
        """Test successful system health check."""
        # Setup mocks for all repositories
        mock_database.queries.count_documents.return_value = 100
        mock_database.queries.find_one.return_value = {"_id": ObjectId()}
        mock_database.queries.list_indexes.return_value.to_list.return_value = []
        
        mock_database.content.count_documents.return_value = 200
        mock_database.content.find_one.return_value = {"_id": ObjectId()}
        mock_database.content.list_indexes.return_value.to_list.return_value = []
        
        mock_database.processed_content.count_documents.return_value = 150
        mock_database.processed_content.find_one.return_value = {"_id": ObjectId()}
        mock_database.processed_content.list_indexes.return_value.to_list.return_value = []
        
        mock_database.query_sessions.count_documents.return_value = 50
        mock_database.query_sessions.find_one.return_value = {"_id": ObjectId()}
        mock_database.query_sessions.list_indexes.return_value.to_list.return_value = []
        
        mock_database.analytics.count_documents.return_value = 25
        mock_database.analytics.find_one.return_value = {"_id": ObjectId()}
        mock_database.analytics.list_indexes.return_value.to_list.return_value = []
        
        # Mock aggregation results
        mock_database.query_sessions.aggregate.return_value.to_list.return_value = []
        mock_database.content.aggregate.return_value.to_list.return_value = []
        mock_database.processed_content.aggregate.return_value.to_list.return_value = []
        
        # Mock database stats
        mock_database.command.return_value = {"dataSize": 1024000}
        
        # Test
        service = DatabaseService(mock_database)
        health = await service.get_system_health()
        
        # Assertions
        assert health["overall_status"] == "healthy"
        assert "components" in health
        assert "metrics" in health


class TestIndexManager:
    """Test IndexManager functionality."""
    
    @pytest.mark.asyncio
    async def test_create_all_indexes_success(self, mock_database):
        """Test successful index creation."""
        # Setup mocks
        mock_database.queries.create_index.return_value = "index1"
        mock_database.content.create_index.return_value = "index2"
        mock_database.processed_content.create_index.return_value = "index3"
        mock_database.query_sessions.create_index.return_value = "index4"
        mock_database.analytics.create_index.return_value = "index5"
        
        # Test
        index_manager = IndexManager(mock_database)
        results = await index_manager.create_all_indexes()
        
        # Assertions
        assert "queries" in results
        assert "content" in results
        assert "processed_content" in results
        assert "query_sessions" in results
        assert "analytics" in results
    
    @pytest.mark.asyncio
    async def test_get_index_status_success(self, mock_database):
        """Test successful index status retrieval."""
        # Setup mocks
        mock_database.queries.list_indexes.return_value.to_list.return_value = [
            {"name": "index1", "key": {"field": 1}},
            {"name": "index2", "key": {"field2": 1}}
        ]
        mock_database.content.list_indexes.return_value.to_list.return_value = [
            {"name": "index3", "key": {"field3": 1}}
        ]
        mock_database.processed_content.list_indexes.return_value.to_list.return_value = []
        mock_database.query_sessions.list_indexes.return_value.to_list.return_value = []
        mock_database.analytics.list_indexes.return_value.to_list.return_value = []
        
        # Mock index stats aggregation
        mock_database.queries.aggregate.return_value.to_list.return_value = [
            {"name": "index1", "accesses": {"ops": 100}},
            {"name": "index2", "accesses": {"ops": 50}}
        ]
        mock_database.content.aggregate.return_value.to_list.return_value = [
            {"name": "index3", "accesses": {"ops": 75}}
        ]
        
        # Test
        index_manager = IndexManager(mock_database)
        status = await index_manager.get_index_status()
        
        # Assertions
        assert "queries" in status
        assert "content" in status
        assert status["queries"]["index_count"] == 2
        assert status["content"]["index_count"] == 1

    @pytest.mark.asyncio
    async def test_get_index_status_missing_indexstats(self, mock_database):
        """Test index status retrieval when $indexStats is not available."""
        # Setup mocks
        mock_database.queries.list_indexes.return_value.to_list.return_value = [
            {"name": "index1", "key": {"field": 1}},
            {"name": "index2", "key": {"field2": 1}}
        ]
        mock_database.content.list_indexes.return_value.to_list.return_value = []
        mock_database.processed_content.list_indexes.return_value.to_list.return_value = []
        mock_database.query_sessions.list_indexes.return_value.to_list.return_value = []
        mock_database.analytics.list_indexes.return_value.to_list.return_value = []
        
        # Mock $indexStats aggregation to raise exception (server compatibility issue)
        mock_database.queries.aggregate.side_effect = Exception("$indexStats not supported")
        
        # Test
        index_manager = IndexManager(mock_database)
        status = await index_manager.get_index_status()
        
        # Assertions - should handle missing $indexStats gracefully
        assert "queries" in status
        assert status["queries"]["index_count"] == 2
        # Stats should be empty dict when $indexStats fails
        for index in status["queries"]["indexes"]:
            assert isinstance(index["stats"], dict)
            assert index["stats"] == {}  # Should be empty when stats unavailable


class TestMigrationManager:
    """Test MigrationManager functionality."""
    
    @pytest.mark.asyncio
    async def test_apply_migrations_success(self, mock_database):
        """Test successful migration application."""
        # Setup mocks
        mock_database.migrations.find_one.return_value = None  # No existing migrations
        mock_database.migrations.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        
        # Mock collection creation
        mock_database.create_collection.return_value = None
        mock_database.list_collection_names.return_value = []
        
        # Mock index creation
        mock_database.queries.create_index.return_value = "index1"
        mock_database.content.create_index.return_value = "index2"
        mock_database.processed_content.create_index.return_value = "index3"
        mock_database.query_sessions.create_index.return_value = "index4"
        mock_database.analytics.create_index.return_value = "index5"
        
        # Test
        migration_manager = MigrationManager(mock_database)
        results = await migration_manager.apply_migrations()
        
        # Assertions
        assert len(results) > 0
        assert all("version" in migration for migration in results)
    
    @pytest.mark.asyncio
    async def test_get_migration_status_success(self, mock_database):
        """Test successful migration status retrieval."""
        # Setup mock
        mock_database.migrations.find_one.return_value = {"version": "005"}
        
        # Test
        migration_manager = MigrationManager(mock_database)
        status = await migration_manager.get_migration_status()
        
        # Assertions
        assert status == "005"
    
    @pytest.mark.asyncio
    async def test_validate_schema_success(self, mock_database):
        """Test successful schema validation."""
        # Setup mock
        mock_database.list_collection_names.return_value = [
            "queries", "content", "processed_content", 
            "query_sessions", "analytics", "migrations"
        ]
        
        # Mock index listing
        mock_database.queries.list_indexes.return_value.to_list.return_value = []
        mock_database.content.list_indexes.return_value.to_list.return_value = []
        mock_database.processed_content.list_indexes.return_value.to_list.return_value = []
        mock_database.query_sessions.list_indexes.return_value.to_list.return_value = []
        mock_database.analytics.list_indexes.return_value.to_list.return_value = []
        
        # Mock migration status
        mock_database.migrations.find.return_value.to_list.return_value = []
        
        # Test
        migration_manager = MigrationManager(mock_database)
        validation = await migration_manager.validate_schema()
        
        # Assertions
        assert "collections" in validation
        assert "indexes" in validation
        assert "migrations" in validation
        assert len(validation["collections"]["missing"]) == 0


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self, mock_database):
        """Test handling of database connection errors."""
        # Setup mock to raise exception
        mock_database.queries.insert_one.side_effect = Exception("Connection failed")
        
        # Test
        repo = QueryRepository(mock_database)
        
        with pytest.raises(RuntimeError, match="Unexpected error"):
            await repo.save_query(QueryDocument(
                base_result={"query_text": "test", "confidence_score": 0.9, "processing_time": 1.0, "category": "general"},
                session_id="test_session"
            ))
    
    @pytest.mark.asyncio
    async def test_duplicate_key_error(self, mock_database):
        """Test handling of duplicate key errors."""
        from pymongo.errors import DuplicateKeyError
        
        # Setup mock to raise DuplicateKeyError
        mock_database.queries.insert_one.side_effect = DuplicateKeyError("Duplicate key")
        
        # Test
        repo = QueryRepository(mock_database)
        
        with pytest.raises(ValueError, match="Query with this identifier already exists"):
            await repo.save_query(QueryDocument(
                base_result={"query_text": "test", "confidence_score": 0.9, "processing_time": 1.0, "category": "general"},
                session_id="test_session"
            ))
    
    @pytest.mark.asyncio
    async def test_operation_failure_error(self, mock_database):
        """Test handling of operation failure errors."""
        from pymongo.errors import OperationFailure
        
        # Setup mock to raise OperationFailure
        mock_database.queries.find_one.side_effect = OperationFailure("Operation failed")
        
        # Test
        repo = QueryRepository(mock_database)
        
        with pytest.raises(RuntimeError, match="Failed to retrieve query from database"):
            await repo.get_query_by_id(ObjectId())


class TestPerformance:
    """Test performance-related functionality."""
    
    @pytest.mark.asyncio
    async def test_bulk_operations_performance(self, mock_database, sample_content_document):
        """Test bulk operations performance."""
        # Setup mock
        mock_database.content.insert_many.return_value = AsyncMock(inserted_ids=[ObjectId() for _ in range(100)])
        mock_database.content.find.return_value.to_list.return_value = []  # No duplicates
        
        # Test
        repo = ScrapedContentRepository(mock_database)
        content_docs = [sample_content_document for _ in range(100)]
        
        start_time = datetime.utcnow()
        results = await repo.bulk_save_content(content_docs)
        end_time = datetime.utcnow()
        
        # Assertions
        assert len(results) == 100
        assert (end_time - start_time).total_seconds() < 1.0  # Should be fast
        mock_database.content.insert_many.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_performance(self, mock_database, sample_query_document):
        """Test search operations performance."""
        # Setup mock
        mock_database.queries.find.return_value.to_list.return_value = [
            sample_query_document.model_dump(by_alias=True) for _ in range(50)
        ]
        
        # Test
        repo = QueryRepository(mock_database)
        
        start_time = datetime.utcnow()
        results = await repo.search_queries("test query", limit=50)
        end_time = datetime.utcnow()
        
        # Assertions
        assert len(results) == 50
        assert (end_time - start_time).total_seconds() < 0.5  # Should be fast


# Integration tests
class TestDatabaseIntegration:
    """Integration tests for database components."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_query_processing(self, mock_database):
        """Test end-to-end query processing workflow."""
        # Setup mocks for complete workflow
        mock_database.queries.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        mock_database.content.insert_many.return_value = MagicMock(inserted_ids=[ObjectId(), ObjectId()])
        mock_database.processed_content.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        mock_database.query_sessions.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        mock_database.query_sessions.find_one.return_value = None
        mock_database.query_sessions.update_one.return_value = MagicMock(modified_count=1)
        
        # Mock aggregation results
        mock_database.content.aggregate.return_value.to_list.return_value = []
        mock_database.processed_content.aggregate.return_value.to_list.return_value = []
        mock_database.query_sessions.aggregate.return_value.to_list.return_value = []
        
        # Mock database stats
        mock_database.command.return_value = {"dataSize": 1024000}
        
        # Test
        service = DatabaseService(mock_database)
        
        # Create mock data
        from app.agents.schemas import ParsedQuery, BaseQueryResult, QueryCategory
        from app.scraper.schemas import ScrapedContent, ContentType
        from app.processing.schemas import ProcessedContent, ContentSummary, StructuredData
        
        parsed_query = ParsedQuery(
            base_result=BaseQueryResult(
                query_text="test query",
                confidence_score=0.95,
                processing_time=1.2,
                category=QueryCategory.GENERAL
            )
        )
        
        scraped_content = ScrapedContent(
            url="https://example.com/test",
            title="Test Content",
            content="This is test content",
            content_type=ContentType.ARTICLE,
            processing_time=2.5,
            content_size_bytes=1024,
            extraction_method="test_extraction"
        )
        
        processed_content = ProcessedContent(
            original_content=scraped_content,
            cleaned_content="Cleaned test content",
            summary=ContentSummary(
                executive_summary="Test summary",
                key_points=["Point 1", "Point 2"],
                detailed_summary="Detailed test summary",
                main_topics=["Topic 1"],
                sentiment="positive",
                confidence_score=0.9
            ),
            structured_data=StructuredData(
                entities=[],
                key_value_pairs={},
                categories=["Test"],
                confidence_scores={},
                tables=[],
                measurements=[]
            ),
            processing_duration=3.0,
            enhanced_quality_score=0.85,
            processing_errors=[]
        )
        
        # Execute workflow
        query_doc, session_id = await service.process_and_store_query(parsed_query, "test_session")
        content_docs, content_id_mapping = await service.store_scraping_results([scraped_content], query_doc.id, session_id)
        processed_docs = await service.store_processing_results([processed_content], query_doc.id, content_id_mapping, session_id)
        
        # Assertions
        assert query_doc.id is not None
        assert len(content_docs) == 1
        assert len(processed_docs) == 1
        assert session_id == "test_session"
