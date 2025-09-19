"""
Database operations for processed content and results management.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.core.database import get_database
from app.core.config import settings
from app.database.models import ProcessedContentDocument
from app.database.utils import apply_query_timeout, run_with_timeout_and_retries

logger = logging.getLogger(__name__)


class ProcessedContentRepository:
    """Repository class for processed content document operations."""
    
    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize repository with database connection."""
        self.database = database or get_database()
        self.collection: AsyncIOMotorCollection = self.database.processed_content
    
    async def save_processed_content(self, processed_doc: ProcessedContentDocument) -> ProcessedContentDocument:
        """Save processed content with validation and relationship management."""
        try:
            # Prepare document for insertion
            doc_data = processed_doc.model_dump(by_alias=True, exclude={"id"})
            doc_data["created_at"] = datetime.utcnow()
            doc_data["updated_at"] = datetime.utcnow()
            
            # Insert document with timeout/retry
            result = await run_with_timeout_and_retries(
                lambda: self.collection.insert_one(doc_data),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            processed_doc.id = result.inserted_id
            
            logger.info(f"Processed content saved successfully with ID: {result.inserted_id}")
            return processed_doc
            
        except DuplicateKeyError as e:
            logger.error(f"Duplicate processed content key error: {e}")
            raise ValueError("Processed content with this identifier already exists")
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to save processed content to database")
        except Exception as e:
            logger.error(f"Unexpected error saving processed content: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_processed_by_query(self, query_id: ObjectId, limit: int = 50, 
                                   skip: int = 0) -> List[ProcessedContentDocument]:
        """Retrieve processed results by query."""
        try:
            cursor = self.collection.find(
                {"query_id": query_id}
            ).sort("processing_timestamp", -1).skip(skip).limit(limit)
            
            cursor = apply_query_timeout(cursor)
            docs = await cursor.to_list(length=limit)
            return [ProcessedContentDocument(**doc) for doc in docs]
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to retrieve processed content by query from database")
        except Exception as e:
            logger.error(f"Unexpected error retrieving processed content by query: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_processing_history(self, original_content_id: ObjectId, 
                                   limit: int = 10) -> List[ProcessedContentDocument]:
        """Track processing evolution for content."""
        try:
            cursor = self.collection.find(
                {"original_content_id": original_content_id}
            ).sort("processing_timestamp", -1).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [ProcessedContentDocument(**doc) for doc in docs]
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to retrieve processing history from database")
        except Exception as e:
            logger.error(f"Unexpected error retrieving processing history: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def search_processed_content(self, search_text: str, 
                                    min_quality_score: Optional[float] = None,
                                    processing_version: Optional[str] = None,
                                    limit: int = 20, skip: int = 0) -> List[ProcessedContentDocument]:
        """Semantic search capabilities for processed content."""
        try:
            # Build search filter
            filter_dict = {}
            
            # Text search on cleaned content and summary
            if search_text:
                filter_dict["$text"] = {"$search": search_text}
            
            # Quality score filter
            if min_quality_score is not None:
                filter_dict["enhanced_quality_score"] = {"$gte": min_quality_score}
            
            # Processing version filter
            if processing_version:
                filter_dict["processing_version"] = processing_version
            
            # Execute search
            cursor = self.collection.find(filter_dict).sort("enhanced_quality_score", -1).skip(skip).limit(limit)
            cursor = apply_query_timeout(cursor)
            docs = await cursor.to_list(length=limit)
            return [ProcessedContentDocument(**doc) for doc in docs]
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to search processed content in database")
        except Exception as e:
            logger.error(f"Unexpected error searching processed content: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_similar_content(self, content_id: ObjectId, 
                                similarity_threshold: float = 0.8,
                                limit: int = 10) -> List[Dict[str, Any]]:
        """Leverage duplicate analysis data for similarity search with schema-safe handling."""
        try:
            # Validate input parameters
            if not isinstance(content_id, ObjectId):
                logger.warning(f"Invalid content_id type: {type(content_id)}")
                return []
            
            if not 0.0 <= similarity_threshold <= 1.0:
                logger.warning(f"Invalid similarity_threshold: {similarity_threshold}")
                return []
            
            if limit <= 0:
                logger.warning(f"Invalid limit: {limit}")
                return []
            
            # Get the content's duplicate analysis
            content_doc = await run_with_timeout_and_retries(
                lambda: self.collection.find_one({"_id": content_id}),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            if not content_doc:
                logger.info(f"No content found with ID: {content_id}")
                return []
            
            # Validate duplicate_analysis structure
            duplicate_analysis = content_doc.get("duplicate_analysis")
            if not duplicate_analysis:
                logger.info(f"No duplicate analysis found for content: {content_id}")
                return []
            
            if not isinstance(duplicate_analysis, dict):
                logger.warning(f"Invalid duplicate_analysis type: {type(duplicate_analysis)}")
                return []
            
            if not duplicate_analysis.get("has_duplicates", False):
                logger.info(f"No duplicates found for content: {content_id}")
                return []
            
            # Safely extract duplicate groups
            duplicate_groups = duplicate_analysis.get("duplicate_groups", [])
            if not isinstance(duplicate_groups, list):
                logger.warning(f"Invalid duplicate_groups type: {type(duplicate_groups)}")
                return []
            
            # Get similar content based on duplicate groups
            similar_ids = []
            for i, group in enumerate(duplicate_groups):
                if not isinstance(group, list):
                    logger.warning(f"Invalid duplicate group {i} type: {type(group)}")
                    continue
                
                # Convert all IDs to ObjectId for consistent comparison
                group_object_ids = []
                for j, id_val in enumerate(group):
                    try:
                        if isinstance(id_val, str):
                            group_object_ids.append(ObjectId(id_val))
                        elif isinstance(id_val, ObjectId):
                            group_object_ids.append(id_val)
                        else:
                            logger.warning(f"Invalid ID type in group {i}, position {j}: {type(id_val)}")
                            continue
                    except Exception as e:
                        logger.warning(f"Failed to convert ID in group {i}, position {j}: {e}")
                        continue
                
                if content_id in group_object_ids:
                    similar_ids.extend([id for id in group_object_ids if id != content_id])
            
            if not similar_ids:
                logger.info(f"No similar content found for: {content_id}")
                return []
            
            # Retrieve similar content with timeout
            cursor = self.collection.find(
                {"_id": {"$in": similar_ids}}
            ).limit(limit)
            cursor = apply_query_timeout(cursor)
            docs = await cursor.to_list(length=limit)
            
            # Safely extract similarity scores
            similarity_scores = duplicate_analysis.get("similarity_scores", {})
            if not isinstance(similarity_scores, dict):
                logger.warning(f"Invalid similarity_scores type: {type(similarity_scores)}")
                similarity_scores = {}
            
            result = []
            for doc in docs:
                try:
                    doc_id = doc["_id"]
                    # Try both string and ObjectId keys for similarity scores
                    doc_id_str = str(doc_id)
                    similarity_score = similarity_scores.get(doc_id_str, similarity_scores.get(doc_id, 0.0))
                    
                    # Validate similarity score
                    if not isinstance(similarity_score, (int, float)):
                        logger.warning(f"Invalid similarity score type for {doc_id}: {type(similarity_score)}")
                        similarity_score = 0.0
                    
                    if similarity_score >= similarity_threshold:
                        result.append({
                            "content": ProcessedContentDocument(**doc),
                            "similarity_score": float(similarity_score)
                        })
                except Exception as e:
                    logger.warning(f"Failed to process similar content document: {e}")
                    continue
            
            logger.info(f"Found {len(result)} similar content items for {content_id}")
            return result
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to get similar content from database")
        except Exception as e:
            logger.error(f"Unexpected error getting similar content: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def cache_processed_results(self, cache_key: str, 
                                   processed_doc: ProcessedContentDocument,
                                   ttl_seconds: int = 3600) -> bool:
        """Performance optimization through caching."""
        try:
            # Add cache metadata
            processed_doc.cache_key = cache_key
            
            # Set TTL for cache
            doc_data = processed_doc.model_dump(by_alias=True, exclude={"id"})
            doc_data["created_at"] = datetime.utcnow()
            doc_data["updated_at"] = datetime.utcnow()
            doc_data["expires_at"] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            
            # Insert with TTL
            result = await run_with_timeout_and_retries(
                lambda: self.collection.insert_one(doc_data),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            logger.info(f"Processed content cached with key: {cache_key}")
            return True
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to cache processed results in database")
        except Exception as e:
            logger.error(f"Unexpected error caching processed results: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_cached_results(self, cache_key: str) -> Optional[ProcessedContentDocument]:
        """Retrieve cached processed results."""
        try:
            doc = await run_with_timeout_and_retries(
                lambda: self.collection.find_one({
                    "cache_key": cache_key,
                    "expires_at": {"$gt": datetime.utcnow()}
                }),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            if doc:
                return ProcessedContentDocument(**doc)
            return None
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to get cached results from database")
        except Exception as e:
            logger.error(f"Unexpected error getting cached results: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_analytics_data(self, start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None,
                               processing_version: Optional[str] = None) -> Dict[str, Any]:
        """Processing performance metrics."""
        try:
            # Build filter
            filter_dict = {}
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                filter_dict["processing_timestamp"] = date_filter
            
            if processing_version:
                filter_dict["processing_version"] = processing_version
            
            # Aggregate analytics
            pipeline = [
                {"$match": filter_dict},
                {"$group": {
                    "_id": None,
                    "total_processed": {"$sum": 1},
                    "avg_processing_duration": {"$avg": "$processing_duration"},
                    "avg_quality_score": {"$avg": "$enhanced_quality_score"},
                    "total_processing_time": {"$sum": "$processing_duration"},
                    "avg_memory_usage": {"$avg": "$memory_usage_mb"},
                    "avg_cpu_time": {"$avg": "$cpu_time_seconds"},
                    "error_count": {"$sum": {"$size": "$processing_errors"}},
                    "processing_versions": {"$addToSet": "$processing_version"}
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
                    "total_processed": 0,
                    "avg_processing_duration": 0.0,
                    "avg_quality_score": 0.0,
                    "total_processing_time": 0.0,
                    "avg_memory_usage": 0.0,
                    "avg_cpu_time": 0.0,
                    "error_count": 0,
                    "processing_versions": []
                }
                
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to get analytics data from database")
        except Exception as e:
            logger.error(f"Unexpected error getting analytics data: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def archive_old_results(self, days_old: int = 180) -> int:
        """Data lifecycle management for old processed results."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Archive old results by moving to archive collection
            cursor = self.collection.find({
                "processing_timestamp": {"$lt": cutoff_date}
            })
            cursor = apply_query_timeout(cursor)
            old_docs = await cursor.to_list(length=None)
            
            if old_docs:
                # Insert into archive collection
                archive_collection = self.database.processed_content_archive
                await run_with_timeout_and_retries(
                    lambda: archive_collection.insert_many(old_docs),
                    timeout_s=settings.database_query_timeout_seconds,
                    retries=settings.database_max_retries,
                )
                
                # Remove from main collection
                result = await run_with_timeout_and_retries(
                    lambda: self.collection.delete_many({
                        "processing_timestamp": {"$lt": cutoff_date}
                    }),
                    timeout_s=settings.database_query_timeout_seconds,
                    retries=settings.database_max_retries,
                )
                
                logger.info(f"Archived {result.deleted_count} old processed results")
                return result.deleted_count
            else:
                return 0
                
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to archive old results in database")
        except Exception as e:
            logger.error(f"Unexpected error archiving old results: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_processing_errors(self, limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
        """Get content with processing errors for analysis."""
        try:
            cursor = self.collection.find(
                {"processing_errors": {"$ne": []}}
            ).sort("processing_timestamp", -1).skip(skip).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [
                {
                    "id": doc["_id"],
                    "original_content_id": doc["original_content_id"],
                    "processing_errors": doc["processing_errors"],
                    "processing_timestamp": doc["processing_timestamp"],
                    "processing_version": doc.get("processing_version", "unknown")
                }
                for doc in docs
            ]
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to get processing errors from database")
        except Exception as e:
            logger.error(f"Unexpected error getting processing errors: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_quality_distribution(self) -> Dict[str, int]:
        """Get distribution of quality scores for analysis."""
        try:
            pipeline = [
                {"$group": {
                    "_id": {
                        "$switch": {
                            "branches": [
                                {"case": {"$lt": ["$enhanced_quality_score", 0.3]}, "then": "low"},
                                {"case": {"$lt": ["$enhanced_quality_score", 0.7]}, "then": "medium"},
                                {"case": {"$gte": ["$enhanced_quality_score", 0.7]}, "then": "high"}
                            ],
                            "default": "unknown"
                        }
                    },
                    "count": {"$sum": 1}
                }},
                {"$group": {
                    "_id": None,
                    "distribution": {"$push": {"quality": "$_id", "count": "$count"}}
                }}
            ]
            
            aggregation = self.collection.aggregate(pipeline)
            aggregation = apply_query_timeout(aggregation)
            result = await aggregation.to_list(length=1)
            if result:
                distribution = {}
                for item in result[0]["distribution"]:
                    distribution[item["quality"]] = item["count"]
                return distribution
            else:
                return {"low": 0, "medium": 0, "high": 0, "unknown": 0}
                
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to get quality distribution from database")
        except Exception as e:
            logger.error(f"Unexpected error getting quality distribution: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def update_processing_metadata(self, content_id: ObjectId, 
                                      metadata: Dict[str, Any]) -> bool:
        """Update processing metadata for content."""
        try:
            result = await run_with_timeout_and_retries(
                lambda: self.collection.update_one(
                    {"_id": content_id},
                    {
                        "$set": {
                            "processing_metadata": metadata,
                            "updated_at": datetime.utcnow()
                        }
                    }
                ),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            if result.modified_count > 0:
                logger.info(f"Processing metadata updated for content {content_id}")
                return True
            else:
                logger.warning(f"No processed content found with ID {content_id} to update")
                return False
                
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to update processing metadata in database")
        except Exception as e:
            logger.error(f"Unexpected error updating processing metadata: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on processed content collection."""
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
            indexes = await self.collection.list_indexes().to_list(length=None)
            
            # Test aggregation
            analytics = await self.get_analytics_data()
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "document_count": count,
                "has_sample_data": sample_doc is not None,
                "index_count": len(indexes),
                "total_processed": analytics.get("total_processed", 0),
                "avg_quality_score": analytics.get("avg_quality_score", 0.0),
                "response_time_seconds": response_time,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Processed content repository health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
