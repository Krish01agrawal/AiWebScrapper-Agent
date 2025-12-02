"""
Database service layer that orchestrates all database operations and provides high-level interfaces.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.config import settings
from app.database.repositories.queries import QueryRepository
from app.database.repositories.content import ScrapedContentRepository
from app.database.repositories.processed import ProcessedContentRepository
from app.database.repositories.analytics import AnalyticsRepository
from app.database.models import (
    QueryDocument, ScrapedContentDocument, ProcessedContentDocument,
    QuerySessionDocument, AnalyticsDocument, DocumentStatus,
    convert_parsed_query_to_document, convert_scraped_content_to_document,
    convert_processed_content_to_document
)
from app.agents.schemas import ParsedQuery
from app.scraper.schemas import ScrapedContent
from app.processing.schemas import ProcessedContent

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service class that coordinates all repository operations."""
    
    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize service with database connection and repositories."""
        self.database = database if database is not None else get_database()
        self.query_repo = QueryRepository(self.database)
        self.content_repo = ScrapedContentRepository(self.database)
        self.processed_repo = ProcessedContentRepository(self.database)
        self.analytics_repo = AnalyticsRepository(self.database)
    
    async def process_and_store_query(self, parsed_query: ParsedQuery, 
                                    session_id: Optional[str] = None,
                                    user_id: Optional[str] = None) -> Tuple[QueryDocument, str]:
        """Handle the complete query storage workflow."""
        try:
            # Convert ParsedQuery to QueryDocument using helper function
            query_doc = convert_parsed_query_to_document(
                parsed_query,
                session_id=session_id,
                user_id=user_id,
                status="pending"
            )
            
            # Save query
            saved_query = await self.query_repo.save_query(query_doc)
            
            # Create or update session
            if session_id:
                await self._update_session_for_query(session_id, user_id, saved_query.id)
            
            logger.info(f"Query processed and stored with ID: {saved_query.id}")
            return saved_query, session_id or "no_session"
            
        except Exception as e:
            logger.error(f"Failed to process and store query: {e}")
            raise RuntimeError(f"Query processing failed: {str(e)}")
    
    async def store_scraping_results(self, scraped_content_list: List[ScrapedContent], 
                                   query_id: ObjectId, session_id: Optional[str] = None) -> Tuple[List[ScrapedContentDocument], Dict[str, ObjectId]]:
        """Batch storage of scraped content."""
        try:
            # Convert ScrapedContent to ScrapedContentDocument using helper function
            content_docs = []
            for content in scraped_content_list:
                content_doc = convert_scraped_content_to_document(
                    content,
                    query_id=query_id,
                    session_id=session_id
                )
                content_docs.append(content_doc)
            
            # Bulk save content
            saved_content = await self.content_repo.bulk_save_content(content_docs)
            
            # Update query with result count
            await self.query_repo.update_query_status(
                query_id, 
                DocumentStatus.PROCESSING, 
                result_count=len(saved_content)
            )
            
            # Update session metrics
            if session_id:
                await self._update_session_content_metrics(session_id, len(saved_content))
            
            # Create mapping from ScrapedContent to ObjectId for processed content linking
            content_id_mapping = {}
            for doc in saved_content:
                if doc.id is not None:
                    content_id_mapping[doc.url] = doc.id
                elif doc.duplicate_of is not None:
                    content_id_mapping[doc.url] = doc.duplicate_of
            
            logger.info(f"Stored {len(saved_content)} scraped content items for query {query_id}")
            return saved_content, content_id_mapping
            
        except Exception as e:
            logger.error(f"Failed to store scraping results: {e}")
            raise RuntimeError(f"Scraping results storage failed: {str(e)}")
    
    async def store_processing_results(self, processed_content_list: List[ProcessedContent], 
                                     query_id: ObjectId, content_id_mapping: Dict[str, ObjectId],
                                     session_id: Optional[str] = None) -> List[ProcessedContentDocument]:
        """Processed content storage."""
        try:
            # Convert ProcessedContent to ProcessedContentDocument
            processed_docs = []
            unresolved_items = []
            
            for content in processed_content_list:
                # Try to resolve original_content_id using multiple strategies
                original_content_id = None
                
                # Strategy 1: Direct original_content_id if provided
                if content.original_content_id:
                    try:
                        if isinstance(content.original_content_id, str):
                            original_content_id = ObjectId(content.original_content_id)
                        else:
                            original_content_id = content.original_content_id
                    except Exception as e:
                        logger.warning(f"Invalid original_content_id format: {content.original_content_id}, error: {e}")
                
                # Strategy 2: Resolve via original_url using content_id_mapping
                if original_content_id is None and content.original_url:
                    original_content_id = content_id_mapping.get(content.original_url)
                
                # Strategy 3: Resolve via original_content.url if available
                if original_content_id is None and hasattr(content, 'original_content') and content.original_content.url:
                    original_content_id = content_id_mapping.get(str(content.original_content.url))
                
                # If still no mapping found, handle gracefully
                if original_content_id is None:
                    unresolved_items.append({
                        'content_id': getattr(content, 'id', 'unknown'),
                        'original_url': getattr(content, 'original_url', 'unknown'),
                        'original_content_url': getattr(content.original_content, 'url', 'unknown') if hasattr(content, 'original_content') else 'unknown'
                    })
                    logger.warning(f"No original content ID found for processed content. Skipping persistence.")
                    continue
                
                processed_doc = convert_processed_content_to_document(
                    content,
                    original_content_id=original_content_id,
                    query_id=query_id,
                    session_id=session_id
                )
                processed_docs.append(processed_doc)
            
            # Save processed content
            saved_processed = []
            processing_errors = []
            
            for doc in processed_docs:
                try:
                    saved_doc = await self.processed_repo.save_processed_content(doc)
                    saved_processed.append(saved_doc)
                except Exception as e:
                    logger.error(f"Failed to save processed content: {e}")
                    processing_errors.append(f"Failed to save processed content: {str(e)}")
            
            # Add unresolved items to processing errors
            if unresolved_items:
                error_msg = f"Failed to resolve original content IDs for {len(unresolved_items)} items: {unresolved_items}"
                processing_errors.append(error_msg)
                logger.error(error_msg)
            
            # Update query status based on processing results
            if not processing_errors:
                status = DocumentStatus.COMPLETED
            elif len(saved_processed) > 0:
                status = DocumentStatus.COMPLETED_WITH_ERRORS
            else:
                status = DocumentStatus.FAILED
            
            await self.query_repo.update_query_status(
                query_id, 
                status, 
                result_count=len(saved_processed)
            )
            
            # Update session metrics
            if session_id:
                await self._update_session_processing_metrics(session_id, len(saved_processed))
            
            logger.info(f"Stored {len(saved_processed)} processed content items for query {query_id}")
            if processing_errors:
                logger.warning(f"Processing completed with {len(processing_errors)} errors")
            
            return saved_processed
            
        except Exception as e:
            logger.error(f"Failed to store processing results: {e}")
            raise RuntimeError(f"Processing results storage failed: {str(e)}")
    
    async def get_query_results(self, query_id: ObjectId) -> Dict[str, Any]:
        """Retrieve complete query results with all related data."""
        try:
            # Try to get cached results first if caching is enabled
            if settings.database_enable_caching:
                cache_key = f"query_results_{query_id}"
                cached_processed = await self.processed_repo.get_cached_results(cache_key)
                if cached_processed:
                    logger.info(f"Retrieved cached results for query {query_id}")
                    # Get query and content (these are usually smaller and don't need caching)
                    query = await self.query_repo.get_query_by_id(query_id)
                    content = await self.content_repo.get_content_by_query(query_id)
                    
                    return {
                        "query": query,
                        "scraped_content": content,
                        "processed_content": [cached_processed],
                        "session_analytics": None,
                        "total_content_count": len(content),
                        "total_processed_count": 1,
                        "cached": True
                    }
            
            # Get query
            query = await self.query_repo.get_query_by_id(query_id)
            if not query:
                raise ValueError(f"Query {query_id} not found")
            
            # Get scraped content
            content = await self.content_repo.get_content_by_query(query_id)
            
            # Get processed content
            processed = await self.processed_repo.get_processed_by_query(query_id)
            
            # Get session analytics if available
            session_analytics = None
            if query.session_id:
                session_analytics = await self.analytics_repo.get_session_analytics(query.session_id)
            
            result = {
                "query": query,
                "scraped_content": content,
                "processed_content": processed,
                "session_analytics": session_analytics,
                "total_content_count": len(content),
                "total_processed_count": len(processed),
                "cached": False
            }
            
            # Cache the processed results if caching is enabled
            if settings.database_enable_caching and processed:
                cache_key = f"query_results_{query_id}"
                # CACHING STRATEGY: We cache only the first processed result for performance.
                # This is a trade-off between cache efficiency and completeness. For multi-item
                # results, consider implementing a compact summary/ID list cache or expanding
                # cache_processed_results() to handle multiple documents.
                if processed:
                    await self.processed_repo.cache_processed_results(
                        cache_key, 
                        processed[0], 
                        settings.database_cache_ttl_seconds
                    )
                    logger.info(f"Cached results for query {query_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get query results: {e}")
            raise RuntimeError(f"Query results retrieval failed: {str(e)}")
    
    async def search_historical_data(self, search_text: str, 
                                   content_type: Optional[str] = None,
                                   category: Optional[str] = None,
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None,
                                   limit: int = 20) -> Dict[str, Any]:
        """Cross-collection searches."""
        try:
            results = {}
            
            # Search queries with date range filtering
            queries = await self.query_repo.search_queries(
                search_text, category=category, limit=limit,
                start_date=start_date, end_date=end_date
            )
            results["queries"] = queries
            
            # Search content with date range filtering
            content = await self.content_repo.search_content(
                search_text, content_type=content_type, limit=limit,
                start_date=start_date, end_date=end_date
            )
            results["content"] = content
            
            # Search processed content with date range filtering
            processed = await self.processed_repo.search_processed_content(
                search_text, limit=limit, start_date=start_date, end_date=end_date
            )
            results["processed_content"] = processed
            
            # Add metadata
            results["metadata"] = {
                "search_text": search_text,
                "content_type_filter": content_type,
                "category_filter": category,
                "date_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                },
                "limit": limit,
                "total_results": len(queries) + len(content) + len(processed)
            }
            
            logger.info(f"Historical search completed: {results['metadata']['total_results']} results")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search historical data: {e}")
            raise RuntimeError(f"Historical data search failed: {str(e)}")
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """Data lifecycle management."""
        try:
            cleanup_results = {}
            
            # Cleanup old queries
            queries_cleaned = await self.query_repo.cleanup_old_queries(
                settings.database_content_ttl_days
            )
            cleanup_results["queries"] = queries_cleaned
            
            # Cleanup old content
            content_cleaned = await self.content_repo.cleanup_old_content(
                settings.database_content_ttl_days
            )
            cleanup_results["content"] = content_cleaned
            
            # Archive old processed results
            processed_archived = await self.processed_repo.archive_old_results(
                settings.database_analytics_retention_days
            )
            cleanup_results["processed_content"] = processed_archived
            
            # Cleanup old analytics
            analytics_cleaned = await self.analytics_repo.cleanup_old_analytics(
                settings.database_analytics_retention_days
            )
            cleanup_results["analytics"] = analytics_cleaned
            
            total_cleaned = sum(cleanup_results.values())
            logger.info(f"Data cleanup completed: {total_cleaned} items cleaned")
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            raise RuntimeError(f"Data cleanup failed: {str(e)}")
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Database health monitoring."""
        try:
            health_status = {
                "overall_status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "components": {}
            }
            
            # Check each repository
            repositories = {
                "queries": self.query_repo,
                "content": self.content_repo,
                "processed_content": self.processed_repo,
                "analytics": self.analytics_repo
            }
            
            for name, repo in repositories.items():
                try:
                    component_health = await repo.health_check()
                    health_status["components"][name] = component_health
                    
                    if component_health.get("status") != "healthy":
                        health_status["overall_status"] = "degraded"
                        
                except Exception as e:
                    health_status["components"][name] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
                    health_status["overall_status"] = "unhealthy"
            
            # Add system metrics
            health_status["metrics"] = await self._get_system_metrics()
            
            return health_status
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return {
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _update_session_for_query(self, session_id: str, user_id: Optional[str], query_id: ObjectId):
        """Update session with new query."""
        try:
            # Check if session exists
            existing_session = await self.analytics_repo.get_session_analytics(session_id)
            
            if existing_session:
                # Update existing session
                await self.analytics_repo.update_session(
                    session_id,
                    query_count=existing_session.query_count + 1,
                    total_processing_time=existing_session.total_processing_time + 0.0  # Will be updated later
                )
            else:
                # Create new session
                await self.analytics_repo.create_session(
                    session_id, user_id=user_id
                )
                
        except Exception as e:
            logger.warning(f"Failed to update session {session_id}: {e}")
    
    async def _update_session_content_metrics(self, session_id: str, content_count: int):
        """Update session with content metrics."""
        try:
            session = await self.analytics_repo.get_session_analytics(session_id)
            if session:
                await self.analytics_repo.update_session(
                    session_id,
                    total_content_scraped=session.total_content_scraped + content_count
                )
        except Exception as e:
            logger.warning(f"Failed to update session content metrics: {e}")
    
    async def _update_session_processing_metrics(self, session_id: str, processed_count: int):
        """Update session with processing metrics."""
        try:
            session = await self.analytics_repo.get_session_analytics(session_id)
            if session:
                await self.analytics_repo.update_session(
                    session_id,
                    total_content_processed=session.total_content_processed + processed_count,
                    successful_queries=session.successful_queries + 1
                )
        except Exception as e:
            logger.warning(f"Failed to update session processing metrics: {e}")
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics."""
        try:
            # Get usage statistics
            usage_stats = await self.analytics_repo.get_usage_statistics()
            
            # Get content statistics
            content_stats = await self.content_repo.get_content_stats()
            
            # Get processing analytics
            processing_analytics = await self.processed_repo.get_analytics_data()
            
            return {
                "usage": usage_stats,
                "content": content_stats,
                "processing": processing_analytics,
                "database_size_mb": await self._get_database_size()
            }
            
        except Exception as e:
            logger.warning(f"Failed to get system metrics: {e}")
            return {"error": str(e)}
    
    async def _get_database_size(self) -> float:
        """Get approximate database size in MB."""
        try:
            stats = await self.database.command("dbStats")
            return stats.get("dataSize", 0) / (1024 * 1024)
        except Exception as e:
            logger.warning(f"Failed to get database size: {e}")
            return 0.0
    
    async def create_session(self, session_id: str, user_id: Optional[str] = None,
                           user_agent: Optional[str] = None, ip_address: Optional[str] = None,
                           referrer: Optional[str] = None) -> QuerySessionDocument:
        """Create a new query session."""
        try:
            return await self.analytics_repo.create_session(
                session_id, user_id, user_agent, ip_address, referrer
            )
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise RuntimeError(f"Session creation failed: {str(e)}")
    
    async def end_session(self, session_id: str) -> bool:
        """End a query session."""
        try:
            return await self.analytics_repo.end_session(session_id)
        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            raise RuntimeError(f"Session ending failed: {str(e)}")
    
    async def get_analytics_report(self, report_type: str, start_date: datetime, 
                                 end_date: datetime) -> Dict[str, Any]:
        """Generate analytics reports."""
        try:
            return await self.analytics_repo.generate_reports(report_type, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to generate analytics report: {e}")
            raise RuntimeError(f"Analytics report generation failed: {str(e)}")
    
    async def get_popular_sessions(self, days: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """Get popular sessions."""
        try:
            return await self.analytics_repo.get_popular_sessions(days, limit)
        except Exception as e:
            logger.error(f"Failed to get popular sessions: {e}")
            raise RuntimeError(f"Popular sessions retrieval failed: {str(e)}")
    
    async def get_quality_metrics(self, start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get content quality metrics."""
        try:
            return await self.analytics_repo.get_content_quality_metrics(start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to get quality metrics: {e}")
            raise RuntimeError(f"Quality metrics retrieval failed: {str(e)}")
    
    async def track_performance_metrics(self, session_data: Dict[str, Any]) -> AnalyticsDocument:
        """Track system performance metrics."""
        try:
            return await self.analytics_repo.track_performance_metrics(session_data)
        except Exception as e:
            logger.error(f"Failed to track performance metrics: {e}")
            raise RuntimeError(f"Performance tracking failed: {str(e)}")
