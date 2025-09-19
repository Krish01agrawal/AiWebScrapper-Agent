"""
Database operations for scraped content management.
"""
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.core.database import get_database
from app.core.config import settings
from app.database.models import ScrapedContentDocument
from app.database.utils import apply_query_timeout, run_with_timeout_and_retries

logger = logging.getLogger(__name__)


class ScrapedContentRepository:
    """Repository class for scraped content document operations."""
    
    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize repository with database connection."""
        self.database = database or get_database()
        self.collection: AsyncIOMotorCollection = self.database.content
    
    def _generate_content_hash(self, content: str, url: str) -> str:
        """Generate hash for content deduplication."""
        content_to_hash = f"{url}:{content.strip()}"
        return hashlib.sha256(content_to_hash.encode('utf-8')).hexdigest()
    
    async def save_scraped_content(self, content_doc: ScrapedContentDocument) -> ScrapedContentDocument:
        """Save scraped content with deduplication logic."""
        try:
            # Generate content hash for deduplication
            content_hash = self._generate_content_hash(content_doc.content, content_doc.url)
            content_doc.content_hash = content_hash
            
            # Check for existing content with same hash
            existing = await run_with_timeout_and_retries(
                lambda: self.collection.find_one({"content_hash": content_hash}),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            if existing:
                logger.info(f"Duplicate content found for URL: {content_doc.url}")
                content_doc.duplicate_of = existing["_id"]
                content_doc.id = existing["_id"]
                return content_doc
            
            # Prepare document for insertion
            doc_data = content_doc.model_dump(by_alias=True, exclude={"id"})
            doc_data["created_at"] = datetime.utcnow()
            doc_data["updated_at"] = datetime.utcnow()
            
            # Insert document with timeout/retry
            result = await run_with_timeout_and_retries(
                lambda: self.collection.insert_one(doc_data),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            content_doc.id = result.inserted_id
            
            logger.info(f"Content saved successfully with ID: {result.inserted_id}")
            return content_doc
            
        except DuplicateKeyError as e:
            logger.error(f"Duplicate content key error: {e}")
            raise ValueError("Content with this identifier already exists")
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to save content to database")
        except Exception as e:
            logger.error(f"Unexpected error saving content: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def bulk_save_content(self, content_docs: List[ScrapedContentDocument]) -> List[ScrapedContentDocument]:
        """Efficient batch operations for multiple content items."""
        try:
            if not content_docs:
                return []
            
            # Prepare documents for bulk insertion
            docs_to_insert = []
            for content_doc in content_docs:
                # Generate content hash
                content_hash = self._generate_content_hash(content_doc.content, content_doc.url)
                content_doc.content_hash = content_hash
                
                doc_data = content_doc.model_dump(by_alias=True, exclude={"id"})
                doc_data["created_at"] = datetime.utcnow()
                doc_data["updated_at"] = datetime.utcnow()
                docs_to_insert.append(doc_data)
            
            # Check for duplicates in batch
            content_hashes = [doc["content_hash"] for doc in docs_to_insert]
            existing_docs = await run_with_timeout_and_retries(
                lambda: self.collection.find(
                    {"content_hash": {"$in": content_hashes}}
                ).to_list(length=None),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            existing_hashes = {doc["content_hash"]: doc["_id"] for doc in existing_docs}
            
            # Mark duplicates and filter out existing content
            filtered_docs = []
            for i, doc_data in enumerate(docs_to_insert):
                if doc_data["content_hash"] in existing_hashes:
                    content_docs[i].duplicate_of = existing_hashes[doc_data["content_hash"]]
                    logger.info(f"Duplicate content found for URL: {doc_data['url']}")
                else:
                    filtered_docs.append(doc_data)
            
            # Insert only new content with timeout/retry
            if filtered_docs:
                result = await run_with_timeout_and_retries(
                    lambda: self.collection.insert_many(filtered_docs),
                    timeout_s=settings.database_query_timeout_seconds,
                    retries=settings.database_max_retries,
                )
                
                # Update IDs for successfully inserted documents
                inserted_count = 0
                for i, content_doc in enumerate(content_docs):
                    if content_doc.duplicate_of is None:
                        content_doc.id = result.inserted_ids[inserted_count]
                        inserted_count += 1
            
            logger.info(f"Bulk save completed: {len(filtered_docs)} new, {len(content_docs) - len(filtered_docs)} duplicates")
            return content_docs
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to bulk save content to database")
        except Exception as e:
            logger.error(f"Unexpected error bulk saving content: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_content_by_query(self, query_id: ObjectId, limit: int = 50, 
                                 skip: int = 0) -> List[ScrapedContentDocument]:
        """Retrieve content associated with specific queries."""
        try:
            cursor = self.collection.find(
                {"query_id": query_id}
            ).sort("timestamp", -1).skip(skip).limit(limit)
            
            cursor = apply_query_timeout(cursor)
            docs = await cursor.to_list(length=limit)
            return [ScrapedContentDocument(**doc) for doc in docs]
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to retrieve content by query from database")
        except Exception as e:
            logger.error(f"Unexpected error retrieving content by query: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_content_by_url(self, url: str) -> Optional[ScrapedContentDocument]:
        """URL-based retrieval and duplicate detection."""
        try:
            doc = await run_with_timeout_and_retries(
                lambda: self.collection.find_one({"url": url}),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            if doc:
                return ScrapedContentDocument(**doc)
            return None
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to retrieve content by URL from database")
        except Exception as e:
            logger.error(f"Unexpected error retrieving content by URL: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def search_content(self, search_text: str, content_type: Optional[str] = None,
                           domain: Optional[str] = None, limit: int = 20, 
                           skip: int = 0) -> List[ScrapedContentDocument]:
        """Full-text search capabilities."""
        try:
            # Build search filter
            filter_dict = {}
            
            # Text search
            if search_text:
                filter_dict["$text"] = {"$search": search_text}
            
            # Content type filter
            if content_type:
                filter_dict["content_type"] = content_type
            
            # Domain filter
            if domain:
                filter_dict["url"] = {"$regex": f".*{domain}.*", "$options": "i"}
            
            # Execute search
            cursor = self.collection.find(filter_dict).sort("timestamp", -1).skip(skip).limit(limit)
            cursor = apply_query_timeout(cursor)
            docs = await cursor.to_list(length=limit)
            return [ScrapedContentDocument(**doc) for doc in docs]
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to search content in database")
        except Exception as e:
            logger.error(f"Unexpected error searching content: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_content_stats(self, query_id: Optional[ObjectId] = None,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get analytics and reporting data."""
        try:
            # Build filter
            filter_dict = {}
            if query_id:
                filter_dict["query_id"] = query_id
            
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                filter_dict["timestamp"] = date_filter
            
            # Aggregate statistics
            pipeline = [
                {"$match": filter_dict},
                {"$set": {
                    "domain": {
                        "$regexFind": {
                            "input": "$url",
                            "regex": "https?://([^/]+)"
                        }
                    }
                }},
                {"$group": {
                    "_id": None,
                    "total_content": {"$sum": 1},
                    "total_size_bytes": {"$sum": "$content_size_bytes"},
                    "avg_processing_time": {"$avg": "$processing_time"},
                    "avg_quality_score": {"$avg": "$content_quality_score"},
                    "avg_relevance_score": {"$avg": "$relevance_score"},
                    "unique_domains": {"$addToSet": "$domain.match"},
                    "content_types": {"$addToSet": "$content_type"}
                }}
            ]
            
            aggregation = self.collection.aggregate(pipeline)
            aggregation = apply_query_timeout(aggregation)
            result = await aggregation.to_list(length=1)
            if result:
                stats = result[0]
                del stats["_id"]  # Remove MongoDB internal field
                stats["unique_domains"] = len(stats.get("unique_domains", []))
                return stats
            else:
                return {
                    "total_content": 0,
                    "total_size_bytes": 0,
                    "avg_processing_time": 0.0,
                    "avg_quality_score": 0.0,
                    "avg_relevance_score": 0.0,
                    "unique_domains": 0,
                    "content_types": []
                }
                
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to get content statistics from database")
        except Exception as e:
            logger.error(f"Unexpected error getting content statistics: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def cleanup_old_content(self, days_old: int = 90) -> int:
        """Data lifecycle management for old content."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            result = await run_with_timeout_and_retries(
                lambda: self.collection.delete_many({
                    "timestamp": {"$lt": cutoff_date},
                    "duplicate_of": {"$ne": None}  # Only delete duplicates, keep originals
                }),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            logger.info(f"Cleaned up {result.deleted_count} old content items")
            return result.deleted_count
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to cleanup old content from database")
        except Exception as e:
            logger.error(f"Unexpected error cleaning up content: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_content_by_domain(self, domain: str, limit: int = 20, 
                                  skip: int = 0) -> List[ScrapedContentDocument]:
        """Get content filtered by domain."""
        try:
            cursor = self.collection.find(
                {"url": {"$regex": f".*{domain}.*", "$options": "i"}}
            ).sort("timestamp", -1).skip(skip).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [ScrapedContentDocument(**doc) for doc in docs]
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to retrieve content by domain from database")
        except Exception as e:
            logger.error(f"Unexpected error retrieving content by domain: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_duplicate_groups(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get groups of duplicate content."""
        try:
            pipeline = [
                {"$match": {"duplicate_of": {"$ne": None}}},
                {"$group": {
                    "_id": "$duplicate_of",
                    "duplicates": {"$push": {
                        "id": "$_id",
                        "url": "$url",
                        "title": "$title",
                        "timestamp": "$timestamp"
                    }},
                    "count": {"$sum": 1}
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
            raise RuntimeError("Failed to get duplicate groups from database")
        except Exception as e:
            logger.error(f"Unexpected error getting duplicate groups: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def update_content_quality(self, content_id: ObjectId, 
                                   quality_score: float, relevance_score: Optional[float] = None) -> bool:
        """Update content quality metrics."""
        try:
            update_data = {
                "content_quality_score": quality_score,
                "updated_at": datetime.utcnow()
            }
            
            if relevance_score is not None:
                update_data["relevance_score"] = relevance_score
            
            result = await run_with_timeout_and_retries(
                lambda: self.collection.update_one(
                    {"_id": content_id},
                    {"$set": update_data}
                ),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            if result.modified_count > 0:
                logger.info(f"Content {content_id} quality updated")
                return True
            else:
                logger.warning(f"No content found with ID {content_id} to update")
                return False
                
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to update content quality in database")
        except Exception as e:
            logger.error(f"Unexpected error updating content quality: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_content_by_quality_range(self, min_quality: float, max_quality: float,
                                         limit: int = 20, skip: int = 0) -> List[ScrapedContentDocument]:
        """Get content within quality score range."""
        try:
            cursor = self.collection.find({
                "content_quality_score": {"$gte": min_quality, "$lte": max_quality}
            }).sort("content_quality_score", -1).skip(skip).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [ScrapedContentDocument(**doc) for doc in docs]
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to retrieve content by quality range from database")
        except Exception as e:
            logger.error(f"Unexpected error retrieving content by quality range: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on content collection."""
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
            stats = await self.get_content_stats()
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "document_count": count,
                "has_sample_data": sample_doc is not None,
                "index_count": len(indexes),
                "total_content_size_mb": stats.get("total_size_bytes", 0) / (1024 * 1024),
                "response_time_seconds": response_time,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Content repository health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
