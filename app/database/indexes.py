"""
Comprehensive MongoDB indexing strategy for optimal query performance.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import OperationFailure

from app.core.database import get_database
from app.core.config import settings

logger = logging.getLogger(__name__)


class IndexManager:
    """Manager class for managing all database indexes."""
    
    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize index manager with database connection."""
        self.database = database if database is not None else get_database()
        self.collections = {
            "queries": self.database.queries,
            "content": self.database.content,
            "processed_content": self.database.processed_content,
            "processed_cache": self.database.processed_cache,
            "query_sessions": self.database.query_sessions,
            "analytics": self.database.analytics
        }
    
    async def create_all_indexes(self) -> Dict[str, Any]:
        """Set up indexes for all collections."""
        results = {}
        
        try:
            # Create indexes for each collection
            results["queries"] = await self._create_query_indexes()
            results["content"] = await self._create_content_indexes()
            results["processed_content"] = await self._create_processed_content_indexes()
            results["processed_cache"] = await self._create_processed_cache_indexes()
            results["query_sessions"] = await self._create_session_indexes()
            results["analytics"] = await self._create_analytics_indexes()
            
            logger.info("All database indexes created successfully")
            return results
            
        except Exception as e:
            logger.error(f"Failed to create database indexes: {e}")
            raise RuntimeError(f"Index creation failed: {str(e)}")
    
    async def _create_query_indexes(self) -> List[str]:
        """Create indexes for queries collection."""
        collection = self.collections["queries"]
        indexes = []
        
        try:
            # Session and user indexes
            # Note: background parameter is ignored in MongoDB 4.2+ but kept for compatibility
            bg = settings.database_index_background
            indexes.append(await collection.create_index("session_id", background=bg))
            indexes.append(await collection.create_index("user_id", background=bg))
            
            # Category and status indexes
            indexes.append(await collection.create_index("base_result.category", background=bg))
            indexes.append(await collection.create_index("status", background=bg))
            
            # Timestamp indexes
            indexes.append(await collection.create_index("created_at", background=bg))
            indexes.append(await collection.create_index("updated_at", background=bg))
            
            # Text search index
            if settings.database_enable_text_search:
                indexes.append(await collection.create_index([
                    ("base_result.query_text", "text"),
                    ("suggestions", "text")
                ], background=bg))
            
            # Compound indexes for common query patterns
            indexes.append(await collection.create_index([
                ("session_id", 1),
                ("created_at", -1)
            ], background=bg))
            
            indexes.append(await collection.create_index([
                ("user_id", 1),
                ("created_at", -1)
            ], background=bg))
            
            indexes.append(await collection.create_index([
                ("base_result.category", 1),
                ("status", 1),
                ("created_at", -1)
            ], background=bg))
            
            # Quality and performance indexes
            indexes.append(await collection.create_index("quality_score", background=bg))
            indexes.append(await collection.create_index("execution_time", background=bg))
            
            logger.info(f"Created {len(indexes)} indexes for queries collection")
            return indexes
            
        except OperationFailure as e:
            logger.error(f"Failed to create query indexes: {e}")
            raise RuntimeError(f"Query index creation failed: {str(e)}")
    
    async def _create_content_indexes(self) -> List[str]:
        """Create indexes for content collection."""
        collection = self.collections["content"]
        indexes = []
        
        try:
            # Note: background parameter is ignored in MongoDB 4.2+ but kept for compatibility
            bg = settings.database_index_background
            # Query and session indexes
            indexes.append(await collection.create_index("query_id", background=bg))
            indexes.append(await collection.create_index("session_id", background=bg))
            
            # Content type and quality indexes
            indexes.append(await collection.create_index("content_type", background=bg))
            indexes.append(await collection.create_index("content_quality_score", background=bg))
            indexes.append(await collection.create_index("relevance_score", background=bg))
            
            # Timestamp indexes
            indexes.append(await collection.create_index("timestamp", background=bg))
            indexes.append(await collection.create_index("created_at", background=bg))
            indexes.append(await collection.create_index("indexed_at", background=bg))
            
            # Text search index
            if settings.database_enable_text_search:
                indexes.append(await collection.create_index([
                    ("title", "text"),
                    ("content", "text"),
                    ("description", "text")
                ], background=bg))
            
            # Deduplication indexes
            indexes.append(await collection.create_index("content_hash", unique=True, background=bg))
            indexes.append(await collection.create_index("duplicate_of", background=bg))
            
            # Compound indexes for common patterns
            indexes.append(await collection.create_index([
                ("query_id", 1),
                ("timestamp", -1)
            ], background=bg))
            
            indexes.append(await collection.create_index([
                ("content_type", 1),
                ("content_quality_score", -1)
            ], background=bg))
            
            indexes.append(await collection.create_index([
                ("session_id", 1),
                ("timestamp", -1)
            ], background=bg))
            
            # Domain extraction index
            indexes.append(await collection.create_index([
                ("url", 1),
                ("timestamp", -1)
            ], background=bg))
            
            # TTL index for automatic cleanup
            # POLICY: We rely on ScrapedContentRepository.cleanup_old_content() for duplicates only
            # to avoid dangling references from processed documents. The global TTL on content.timestamp
            # is disabled to prevent automatic deletion of originals that are referenced by processed docs.
            # Instead, we use DATABASE_ANALYTICS_RETENTION_DAYS and archiving in ProcessedContentRepository
            # to ensure processed docs are archived/removed before originals can expire.
            # if settings.database_content_ttl_days > 0:
            #     indexes.append(await collection.create_index(
            #         "timestamp",
            #         expireAfterSeconds=settings.database_content_ttl_days * 24 * 60 * 60,
            #         background=bg
            #     ))
            
            logger.info(f"Created {len(indexes)} indexes for content collection")
            return indexes
            
        except OperationFailure as e:
            logger.error(f"Failed to create content indexes: {e}")
            raise RuntimeError(f"Content index creation failed: {str(e)}")
    
    async def _create_processed_content_indexes(self) -> List[str]:
        """Create indexes for processed content collection."""
        collection = self.collections["processed_content"]
        indexes = []
        
        try:
            # Note: background parameter is ignored in MongoDB 4.2+ but kept for compatibility
            bg = settings.database_index_background
            # Reference indexes
            indexes.append(await collection.create_index("original_content_id", background=bg))
            indexes.append(await collection.create_index("query_id", background=bg))
            indexes.append(await collection.create_index("session_id", background=bg))
            
            # Processing metadata indexes
            indexes.append(await collection.create_index("processing_timestamp", background=bg))
            indexes.append(await collection.create_index("processing_version", background=bg))
            indexes.append(await collection.create_index("enhanced_quality_score", background=bg))
            
            # Performance indexes
            indexes.append(await collection.create_index("processing_duration", background=bg))
            indexes.append(await collection.create_index("memory_usage_mb", background=bg))
            indexes.append(await collection.create_index("cpu_time_seconds", background=bg))
            
            # Cache index
            indexes.append(await collection.create_index("cache_key", background=bg))
            
            # Text search index
            if settings.database_enable_text_search:
                indexes.append(await collection.create_index([
                    ("cleaned_content", "text"),
                    ("summary.executive_summary", "text"),
                    ("summary.key_points", "text")
                ], background=bg))
            
            # Compound indexes for common patterns
            indexes.append(await collection.create_index([
                ("query_id", 1),
                ("processing_timestamp", -1)
            ], background=bg))
            
            indexes.append(await collection.create_index([
                ("enhanced_quality_score", -1),
                ("processing_timestamp", -1)
            ], background=bg))
            
            indexes.append(await collection.create_index([
                ("original_content_id", 1),
                ("processing_timestamp", -1)
            ], background=bg))
            
            # Error tracking index
            indexes.append(await collection.create_index([
                ("processing_errors", 1),
                ("processing_timestamp", -1)
            ], background=bg))
            
            # TTL index for cache expiration
            if settings.database_cache_ttl_seconds > 0:
                indexes.append(await collection.create_index(
                    "expires_at",
                    expireAfterSeconds=0,  # TTL is set in document
                    background=bg
                ))
            
            logger.info(f"Created {len(indexes)} indexes for processed content collection")
            return indexes
            
        except OperationFailure as e:
            logger.error(f"Failed to create processed content indexes: {e}")
            raise RuntimeError(f"Processed content index creation failed: {str(e)}")
    
    async def _create_processed_cache_indexes(self) -> List[str]:
        """Create indexes for processed cache collection."""
        collection = self.collections["processed_cache"]
        indexes = []
        
        try:
            # Note: background parameter is ignored in MongoDB 4.2+ but kept for compatibility
            bg = settings.database_index_background
            
            # Cache key index (unique)
            indexes.append(await collection.create_index("cache_key", unique=True, background=bg))
            
            # TTL index for cache expiration
            if settings.database_cache_ttl_seconds > 0:
                indexes.append(await collection.create_index(
                    "expires_at",
                    expireAfterSeconds=0,  # TTL is set in document
                    background=bg
                ))
            
            # Reference indexes for cache lookup
            indexes.append(await collection.create_index("original_content_id", background=bg))
            indexes.append(await collection.create_index("query_id", background=bg))
            
            # Timestamp indexes
            indexes.append(await collection.create_index("created_at", background=bg))
            indexes.append(await collection.create_index("updated_at", background=bg))
            
            logger.info(f"Created {len(indexes)} indexes for processed cache collection")
            return indexes
            
        except OperationFailure as e:
            logger.error(f"Failed to create processed cache indexes: {e}")
            raise RuntimeError(f"Processed cache index creation failed: {str(e)}")
    
    async def _create_session_indexes(self) -> List[str]:
        """Create indexes for query sessions collection."""
        collection = self.collections["query_sessions"]
        indexes = []
        
        try:
            # Note: background parameter is ignored in MongoDB 4.2+ but kept for compatibility
            bg = settings.database_index_background
            # Primary indexes
            indexes.append(await collection.create_index("session_id", unique=True, background=bg))
            indexes.append(await collection.create_index("user_id", background=bg))
            
            # Time-based indexes
            indexes.append(await collection.create_index("start_time", background=bg))
            indexes.append(await collection.create_index("end_time", background=bg))
            indexes.append(await collection.create_index("duration_seconds", background=bg))
            
            # Status and metrics indexes
            indexes.append(await collection.create_index("status", background=bg))
            indexes.append(await collection.create_index("query_count", background=bg))
            indexes.append(await collection.create_index("average_quality_score", background=bg))
            indexes.append(await collection.create_index("average_relevance_score", background=bg))
            
            # Compound indexes for analytics
            indexes.append(await collection.create_index([
                ("start_time", -1),
                ("status", 1)
            ], background=bg))
            
            indexes.append(await collection.create_index([
                ("user_id", 1),
                ("start_time", -1)
            ], background=bg))
            
            indexes.append(await collection.create_index([
                ("status", 1),
                ("start_time", -1)
            ], background=bg))
            
            # Performance analytics index
            indexes.append(await collection.create_index([
                ("total_processing_time", -1),
                ("start_time", -1)
            ], background=bg))
            
            logger.info(f"Created {len(indexes)} indexes for query sessions collection")
            return indexes
            
        except OperationFailure as e:
            logger.error(f"Failed to create session indexes: {e}")
            raise RuntimeError(f"Session index creation failed: {str(e)}")
    
    async def _create_analytics_indexes(self) -> List[str]:
        """Create indexes for analytics collection."""
        collection = self.collections["analytics"]
        indexes = []
        
        try:
            # Note: background parameter is ignored in MongoDB 4.2+ but kept for compatibility
            bg = settings.database_index_background
            # Time period indexes
            indexes.append(await collection.create_index("period_start", background=bg))
            indexes.append(await collection.create_index("period_end", background=bg))
            indexes.append(await collection.create_index("period_type", background=bg))
            
            # Compound time period index
            indexes.append(await collection.create_index([
                ("period_start", 1),
                ("period_end", 1),
                ("period_type", 1)
            ], unique=True, background=bg))
            
            # Metrics indexes
            indexes.append(await collection.create_index("total_queries", background=bg))
            indexes.append(await collection.create_index("total_sessions", background=bg))
            indexes.append(await collection.create_index("unique_users", background=bg))
            
            # Quality indexes
            indexes.append(await collection.create_index("average_content_quality", background=bg))
            indexes.append(await collection.create_index("average_processing_time", background=bg))
            
            # Performance indexes
            indexes.append(await collection.create_index("peak_concurrent_queries", background=bg))
            indexes.append(await collection.create_index("total_processing_time", background=bg))
            
            # Time-series analytics index
            indexes.append(await collection.create_index([
                ("period_type", 1),
                ("period_start", -1)
            ], background=bg))
            
            # Category and domain breakdown indexes
            indexes.append(await collection.create_index("category_breakdown", background=bg))
            indexes.append(await collection.create_index("domain_breakdown", background=bg))
            
            # TTL index for analytics retention
            if settings.database_analytics_retention_days > 0:
                indexes.append(await collection.create_index(
                    "period_start",
                    expireAfterSeconds=settings.database_analytics_retention_days * 24 * 60 * 60,
                    background=bg
                ))
            
            logger.info(f"Created {len(indexes)} indexes for analytics collection")
            return indexes
            
        except OperationFailure as e:
            logger.error(f"Failed to create analytics indexes: {e}")
            raise RuntimeError(f"Analytics index creation failed: {str(e)}")
    
    async def get_index_status(self) -> Dict[str, Any]:
        """Index monitoring and optimization utilities."""
        status = {}
        
        try:
            for collection_name, collection in self.collections.items():
                indexes = await collection.list_indexes().to_list(length=1000)
                
                # Get index statistics
                index_stats = []
                try:
                    stats_result = await collection.aggregate([{"$indexStats": {}}]).to_list(None)
                    # Ensure stats_result is a list and each stat has proper structure
                    if isinstance(stats_result, list):
                        stats_dict = {stat.get("name", "unknown"): stat for stat in stats_result if isinstance(stat, dict)}
                    else:
                        stats_dict = {}
                except Exception as e:
                    logger.warning(f"Could not get index stats for {collection_name}: {e}")
                    stats_dict = {}
                
                for index in indexes:
                    # Ensure stats is always a dict, even if index stats are missing
                    index_stat_data = stats_dict.get(index["name"], {})
                    if not isinstance(index_stat_data, dict):
                        index_stat_data = {}
                    
                    index_stat = {
                        "name": index["name"],
                        "key": index["key"],
                        "unique": index.get("unique", False),
                        "background": index.get("background", False),
                        "expireAfterSeconds": index.get("expireAfterSeconds"),
                        "stats": index_stat_data
                    }
                    index_stats.append(index_stat)
                
                status[collection_name] = {
                    "index_count": len(indexes),
                    "indexes": index_stats
                }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get index status: {e}")
            raise RuntimeError(f"Index status retrieval failed: {str(e)}")
    
    async def optimize_indexes(self) -> Dict[str, Any]:
        """Optimize indexes based on usage patterns."""
        results = {}
        
        try:
            for collection_name, collection in self.collections.items():
                # Get collection stats
                stats = await collection.database.command("collStats", collection.name)
                
                # Check for unused indexes
                try:
                    index_stats_result = await collection.aggregate([{"$indexStats": {}}]).to_list(None)
                    unused_indexes = []
                    
                    for stat in index_stats_result:
                        if stat.get("accesses", {}).get("ops", 0) == 0:
                            unused_indexes.append(stat["name"])
                except Exception as e:
                    logger.warning(f"Could not get index stats for {collection_name}: {e}")
                    unused_indexes = []
                
                results[collection_name] = {
                    "collection_size_mb": stats.get("size", 0) / (1024 * 1024),
                    "document_count": stats.get("count", 0),
                    "index_size_mb": stats.get("totalIndexSize", 0) / (1024 * 1024),
                    "unused_indexes": unused_indexes,
                    "optimization_recommendations": []
                }
                
                # Add optimization recommendations
                if unused_indexes:
                    results[collection_name]["optimization_recommendations"].append(
                        f"Consider removing unused indexes: {', '.join(unused_indexes)}"
                    )
                
                if stats.get("totalIndexSize", 0) > stats.get("size", 0) * 2:
                    results[collection_name]["optimization_recommendations"].append(
                        "Index size is large compared to collection size - consider index optimization"
                    )
            
            logger.info("Index optimization analysis completed")
            return results
            
        except Exception as e:
            logger.error(f"Failed to optimize indexes: {e}")
            raise RuntimeError(f"Index optimization failed: {str(e)}")
    
    async def drop_unused_indexes(self, collection_name: str, index_names: List[str]) -> bool:
        """Drop unused indexes to free up space."""
        try:
            if collection_name not in self.collections:
                raise ValueError(f"Unknown collection: {collection_name}")
            
            collection = self.collections[collection_name]
            
            for index_name in index_names:
                try:
                    await collection.drop_index(index_name)
                    logger.info(f"Dropped unused index {index_name} from {collection_name}")
                except Exception as e:
                    logger.warning(f"Failed to drop index {index_name}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to drop unused indexes: {e}")
            raise RuntimeError(f"Index dropping failed: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all indexes."""
        try:
            start_time = datetime.utcnow()
            
            # Check if all collections exist and have indexes
            health_status = {}
            total_indexes = 0
            
            for collection_name, collection in self.collections.items():
                try:
                    indexes = await collection.list_indexes().to_list(length=1000)
                    health_status[collection_name] = {
                        "status": "healthy",
                        "index_count": len(indexes),
                        "indexes": [idx["name"] for idx in indexes]
                    }
                    total_indexes += len(indexes)
                except Exception as e:
                    health_status[collection_name] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            return {
                "status": "healthy" if all(
                    status.get("status") == "healthy" 
                    for status in health_status.values()
                ) else "unhealthy",
                "total_indexes": total_indexes,
                "collections": health_status,
                "response_time_seconds": response_time,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Index health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
