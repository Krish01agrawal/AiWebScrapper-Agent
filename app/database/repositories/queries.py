"""
Database operations for query management following async patterns.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.core.database import get_database
from app.core.config import settings
from app.database.models import QueryDocument, DocumentStatus
from app.database.utils import apply_query_timeout, run_with_timeout_and_retries

logger = logging.getLogger(__name__)


class QueryRepository:
    """Repository class for query document operations."""
    
    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize repository with database connection."""
        self.database = database or get_database()
        self.collection: AsyncIOMotorCollection = self.database.queries
    
    async def save_query(self, query_doc: QueryDocument) -> QueryDocument:
        """Save parsed query with proper validation."""
        try:
            # Prepare document for insertion
            doc_data = query_doc.model_dump(by_alias=True, exclude={"id"})
            doc_data["created_at"] = datetime.utcnow()
            doc_data["updated_at"] = datetime.utcnow()
            
            # Insert document with timeout/retry
            result = await run_with_timeout_and_retries(
                lambda: self.collection.insert_one(doc_data),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            query_doc.id = result.inserted_id
            
            logger.info(f"Query saved successfully with ID: {result.inserted_id}")
            return query_doc
            
        except DuplicateKeyError as e:
            logger.error(f"Duplicate query key error: {e}")
            raise ValueError("Query with this identifier already exists")
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to save query to database")
        except Exception as e:
            logger.error(f"Unexpected error saving query: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_query_by_id(self, query_id: ObjectId) -> Optional[QueryDocument]:
        """Retrieve specific query by ID."""
        try:
            doc = await run_with_timeout_and_retries(
                lambda: self.collection.find_one({"_id": query_id}),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            if doc:
                return QueryDocument(**doc)
            return None
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to retrieve query from database")
        except Exception as e:
            logger.error(f"Unexpected error retrieving query: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_queries_by_session(self, session_id: str, limit: int = 50, skip: int = 0) -> List[QueryDocument]:
        """Retrieve queries by session with pagination."""
        try:
            cursor = self.collection.find(
                {"session_id": session_id}
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            cursor = apply_query_timeout(cursor)
            docs = await cursor.to_list(length=limit)
            return [QueryDocument(**doc) for doc in docs]
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to retrieve queries from database")
        except Exception as e:
            logger.error(f"Unexpected error retrieving queries: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_recent_queries(self, limit: int = 20, skip: int = 0, 
                               user_id: Optional[str] = None) -> List[QueryDocument]:
        """Get recent queries with pagination support."""
        try:
            filter_dict = {}
            if user_id:
                filter_dict["user_id"] = user_id
            
            cursor = self.collection.find(filter_dict).sort("created_at", -1).skip(skip).limit(limit)
            cursor = apply_query_timeout(cursor)
            docs = await cursor.to_list(length=limit)
            return [QueryDocument(**doc) for doc in docs]
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to retrieve recent queries from database")
        except Exception as e:
            logger.error(f"Unexpected error retrieving recent queries: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def update_query_status(self, query_id: ObjectId, status: Union[DocumentStatus, str], 
                                 execution_time: Optional[float] = None,
                                 result_count: Optional[int] = None,
                                 quality_score: Optional[float] = None) -> bool:
        """Update query execution progress."""
        try:
            # Normalize status input - accept both DocumentStatus enum and string
            if isinstance(status, str):
                # Validate string status against enum values
                valid_statuses = [s.value for s in DocumentStatus]
                if status not in valid_statuses:
                    raise ValueError(f"Invalid status '{status}'. Must be one of: {valid_statuses}")
                status_value = status
            else:
                status_value = status.value
            
            update_data = {
                "status": status_value,
                "updated_at": datetime.utcnow()
            }
            
            if execution_time is not None:
                update_data["execution_time"] = execution_time
            if result_count is not None:
                update_data["result_count"] = result_count
            if quality_score is not None:
                update_data["quality_score"] = quality_score
            
            result = await run_with_timeout_and_retries(
                lambda: self.collection.update_one(
                    {"_id": query_id},
                    {"$set": update_data}
                ),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            if result.modified_count > 0:
                logger.info(f"Query {query_id} status updated to {status_value}")
                return True
            else:
                logger.warning(f"No query found with ID {query_id} to update")
                return False
                
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to update query status in database")
        except Exception as e:
            logger.error(f"Unexpected error updating query status: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def search_queries(self, search_text: str, category: Optional[str] = None,
                           user_id: Optional[str] = None, limit: int = 20, 
                           skip: int = 0, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> List[QueryDocument]:
        """Search queries with text search and filtering capabilities."""
        try:
            # Build search filter
            filter_dict = {}
            
            # Text search on query text
            if search_text:
                filter_dict["$text"] = {"$search": search_text}
            
            # Category filter
            if category:
                filter_dict["base_result.category"] = category
            
            # User filter
            if user_id:
                filter_dict["user_id"] = user_id
            
            # Date filters
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                filter_dict["created_at"] = date_filter
            
            # Execute search
            cursor = self.collection.find(filter_dict).sort("created_at", -1).skip(skip).limit(limit)
            cursor = apply_query_timeout(cursor)
            docs = await cursor.to_list(length=limit)
            return [QueryDocument(**doc) for doc in docs]
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to search queries in database")
        except Exception as e:
            logger.error(f"Unexpected error searching queries: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_query_statistics(self, start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get query statistics and analytics."""
        try:
            # Build date filter
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            
            filter_dict = {}
            if date_filter:
                filter_dict["created_at"] = date_filter
            
            # Aggregate statistics
            pipeline = [
                {"$match": filter_dict},
                {"$group": {
                    "_id": None,
                    "total_queries": {"$sum": 1},
                    "successful_queries": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
                    "failed_queries": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
                    "avg_execution_time": {"$avg": "$execution_time"},
                    "avg_quality_score": {"$avg": "$quality_score"},
                    "total_execution_time": {"$sum": "$execution_time"}
                }}
            ]
            
            aggregation = self.collection.aggregate(pipeline)
            aggregation = apply_query_timeout(aggregation)
            result = await aggregation.to_list(length=1)
            if result:
                stats = result[0]
                del stats["_id"]  # Remove MongoDB internal field
                return stats
            else:
                return {
                    "total_queries": 0,
                    "successful_queries": 0,
                    "failed_queries": 0,
                    "avg_execution_time": 0.0,
                    "avg_quality_score": 0.0,
                    "total_execution_time": 0.0
                }
                
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to get query statistics from database")
        except Exception as e:
            logger.error(f"Unexpected error getting query statistics: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def cleanup_old_queries(self, days_old: int = 90) -> int:
        """Clean up old queries based on retention policy."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            result = await run_with_timeout_and_retries(
                lambda: self.collection.delete_many({
                    "created_at": {"$lt": cutoff_date},
                    "status": {"$in": ["completed", "failed"]}
                }),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            logger.info(f"Cleaned up {result.deleted_count} old queries")
            return result.deleted_count
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to cleanup old queries from database")
        except Exception as e:
            logger.error(f"Unexpected error cleaning up queries: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_queries_by_category(self, category: str, limit: int = 20, 
                                    skip: int = 0) -> List[QueryDocument]:
        """Get queries filtered by category."""
        try:
            cursor = self.collection.find(
                {"base_result.category": category}
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            cursor = apply_query_timeout(cursor)
            docs = await cursor.to_list(length=limit)
            return [QueryDocument(**doc) for doc in docs]
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to retrieve queries by category from database")
        except Exception as e:
            logger.error(f"Unexpected error retrieving queries by category: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_popular_queries(self, limit: int = 10, days: int = 30) -> List[Dict[str, Any]]:
        """Get most popular queries based on frequency."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            pipeline = [
                {"$match": {"created_at": {"$gte": cutoff_date}}},
                {"$group": {
                    "_id": "$base_result.query_text",
                    "count": {"$sum": 1},
                    "avg_quality_score": {"$avg": "$quality_score"},
                    "avg_execution_time": {"$avg": "$execution_time"},
                    "last_executed": {"$max": "$created_at"}
                }},
                {"$sort": {"count": -1}},
                {"$limit": limit}
            ]
            
            aggregation = self.collection.aggregate(pipeline)
            aggregation = apply_query_timeout(aggregation)
            result = await aggregation.to_list(length=limit)
            return result
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to get popular queries from database")
        except Exception as e:
            logger.error(f"Unexpected error getting popular queries: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on query collection."""
        try:
            # Test basic operations
            start_time = datetime.utcnow()
            
            # Count documents
            count = await self.collection.count_documents({})
            
            # Test find operation
            sample_doc = await run_with_timeout_and_retries(
                lambda: self.collection.find_one({}),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            # Test index status
            indexes = await self.collection.list_indexes().to_list(length=1000)
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "document_count": count,
                "has_sample_data": sample_doc is not None,
                "index_count": len(indexes),
                "response_time_seconds": response_time,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Query repository health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
