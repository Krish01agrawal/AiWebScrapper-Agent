"""
Analytics and session management repository for tracking usage patterns and performance metrics.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.core.database import get_database
from app.core.config import settings
from app.database.models import QuerySessionDocument, AnalyticsDocument, DocumentStatus
from app.database.utils import apply_query_timeout, run_with_timeout_and_retries

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """Repository class for analytics and session operations."""
    
    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize repository with database connection."""
        self.database = database or get_database()
        self.sessions_collection: AsyncIOMotorCollection = self.database.query_sessions
        self.analytics_collection: AsyncIOMotorCollection = self.database.analytics
    
    async def create_session(self, session_id: str, user_id: Optional[str] = None,
                           user_agent: Optional[str] = None, ip_address: Optional[str] = None,
                           referrer: Optional[str] = None) -> QuerySessionDocument:
        """Initialize query sessions."""
        try:
            session_doc = QuerySessionDocument(
                session_id=session_id,
                user_id=user_id,
                user_agent=user_agent,
                ip_address=ip_address,
                referrer=referrer,
                status=DocumentStatus.PENDING
            )
            
            # Prepare document for insertion
            doc_data = session_doc.model_dump(by_alias=True, exclude={"id"})
            doc_data["created_at"] = datetime.utcnow()
            doc_data["updated_at"] = datetime.utcnow()
            
            # Insert document with timeout/retry
            result = await run_with_timeout_and_retries(
                lambda: self.sessions_collection.insert_one(doc_data),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            session_doc.id = result.inserted_id
            
            logger.info(f"Session created successfully with ID: {result.inserted_id}")
            return session_doc
            
        except DuplicateKeyError as e:
            logger.error(f"Duplicate session key error: {e}")
            raise ValueError("Session with this identifier already exists")
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to create session in database")
        except Exception as e:
            logger.error(f"Unexpected error creating session: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def update_session(self, session_id: str, **updates) -> bool:
        """Track session progress and metrics."""
        try:
            update_data = {
                "updated_at": datetime.utcnow()
            }
            
            # Add provided updates - whitelist fields using model_fields
            allowed_fields = QuerySessionDocument.model_fields
            for key, value in updates.items():
                if key in allowed_fields:
                    update_data[key] = value
            
            result = await run_with_timeout_and_retries(
                lambda: self.sessions_collection.update_one(
                    {"session_id": session_id},
                    {"$set": update_data}
                ),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            if result.modified_count > 0:
                logger.info(f"Session {session_id} updated successfully")
                return True
            else:
                logger.warning(f"No session found with ID {session_id} to update")
                return False
                
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to update session in database")
        except Exception as e:
            logger.error(f"Unexpected error updating session: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def end_session(self, session_id: str) -> bool:
        """End session and calculate final metrics."""
        try:
            # Get current session data
            session_doc = await run_with_timeout_and_retries(
                lambda: self.sessions_collection.find_one({"session_id": session_id}),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            if not session_doc:
                logger.warning(f"No session found with ID {session_id}")
                return False
            
            # Calculate duration
            start_time = session_doc["start_time"]
            end_time = datetime.utcnow()
            duration_seconds = (end_time - start_time).total_seconds()
            
            # Calculate average query time
            avg_query_time = None
            if session_doc.get("query_count", 0) > 0:
                avg_query_time = session_doc.get("total_processing_time", 0.0) / session_doc["query_count"]
            
            # Update session with end data
            update_data = {
                "end_time": end_time,
                "duration_seconds": duration_seconds,
                "average_query_time": avg_query_time,
                "status": DocumentStatus.COMPLETED,
                "updated_at": datetime.utcnow()
            }
            
            result = await run_with_timeout_and_retries(
                lambda: self.sessions_collection.update_one(
                    {"session_id": session_id},
                    {"$set": update_data}
                ),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            if result.modified_count > 0:
                logger.info(f"Session {session_id} ended successfully")
                return True
            else:
                logger.warning(f"Failed to end session {session_id}")
                return False
                
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to end session in database")
        except Exception as e:
            logger.error(f"Unexpected error ending session: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_session_analytics(self, session_id: str) -> Optional[QuerySessionDocument]:
        """Detailed session analysis."""
        try:
            doc = await run_with_timeout_and_retries(
                lambda: self.sessions_collection.find_one({"session_id": session_id}),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            if doc:
                return QuerySessionDocument(**doc)
            return None
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to get session analytics from database")
        except Exception as e:
            logger.error(f"Unexpected error getting session analytics: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_usage_statistics(self, start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Application-wide metrics."""
        try:
            # Build date filter
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            
            filter_dict = {}
            if date_filter:
                filter_dict["start_time"] = date_filter
            
            # Aggregate usage statistics
            pipeline = [
                {"$match": filter_dict},
                {"$group": {
                    "_id": None,
                    "total_sessions": {"$sum": 1},
                    "unique_users": {"$addToSet": "$user_id"},
                    "total_queries": {"$sum": "$query_count"},
                    "successful_queries": {"$sum": "$successful_queries"},
                    "failed_queries": {"$sum": "$failed_queries"},
                    "total_processing_time": {"$sum": "$total_processing_time"},
                    "total_content_scraped": {"$sum": "$total_content_scraped"},
                    "total_content_processed": {"$sum": "$total_content_processed"},
                    "avg_session_duration": {"$avg": "$duration_seconds"},
                    "avg_quality_score": {"$avg": "$average_quality_score"},
                    "avg_relevance_score": {"$avg": "$average_relevance_score"}
                }}
            ]
            
            aggregation = self.sessions_collection.aggregate(pipeline)
            aggregation = apply_query_timeout(aggregation)
            result = await aggregation.to_list(length=1)
            if result:
                stats = result[0]
                del stats["_id"]  # Remove MongoDB internal field
                stats["unique_users"] = len([uid for uid in stats["unique_users"] if uid is not None])
                return stats
            else:
                return {
                    "total_sessions": 0,
                    "unique_users": 0,
                    "total_queries": 0,
                    "successful_queries": 0,
                    "failed_queries": 0,
                    "total_processing_time": 0.0,
                    "total_content_scraped": 0,
                    "total_content_processed": 0,
                    "avg_session_duration": 0.0,
                    "avg_quality_score": 0.0,
                    "avg_relevance_score": 0.0
                }
                
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to get usage statistics from database")
        except Exception as e:
            logger.error(f"Unexpected error getting usage statistics: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def track_performance_metrics(self, session_data: Dict[str, Any]) -> AnalyticsDocument:
        """System performance monitoring."""
        try:
            # Create analytics document for the time period
            now = datetime.utcnow()
            period_start = now.replace(minute=0, second=0, microsecond=0)  # Hourly aggregation
            period_end = period_start + timedelta(hours=1)
            
            # Check if analytics document already exists for this period
            existing = await run_with_timeout_and_retries(
                lambda: self.analytics_collection.find_one({
                    "period_start": period_start,
                    "period_end": period_end,
                    "period_type": "hourly"
                }),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            if existing:
                # Update existing document
                analytics_doc = AnalyticsDocument(**existing)
            else:
                # Create new analytics document
                analytics_doc = AnalyticsDocument(
                    period_start=period_start,
                    period_end=period_end,
                    period_type="hourly"
                )
            
            # Update metrics with session data
            analytics_doc.total_queries += session_data.get("query_count", 0)
            analytics_doc.successful_queries += session_data.get("successful_queries", 0)
            analytics_doc.failed_queries += session_data.get("failed_queries", 0)
            analytics_doc.total_content_scraped += session_data.get("total_content_scraped", 0)
            analytics_doc.total_content_processed += session_data.get("total_content_processed", 0)
            analytics_doc.total_processing_time += session_data.get("total_processing_time", 0.0)
            
            # Update unique users and sessions
            if session_data.get("user_id"):
                analytics_doc.unique_users = len(set(
                    await self.sessions_collection.distinct("user_id", {
                        "start_time": {"$gte": period_start, "$lt": period_end}
                    })
                ))
            
            analytics_doc.unique_sessions = await self.sessions_collection.count_documents({
                "start_time": {"$gte": period_start, "$lt": period_end}
            })
            
            # Save or update analytics document
            doc_data = analytics_doc.model_dump(by_alias=True, exclude={"id"})
            doc_data["updated_at"] = datetime.utcnow()
            
            if existing:
                await run_with_timeout_and_retries(
                    lambda: self.analytics_collection.update_one(
                        {"_id": existing["_id"]},
                        {"$set": doc_data}
                    ),
                    timeout_s=settings.database_query_timeout_seconds,
                    retries=settings.database_max_retries,
                )
                analytics_doc.id = existing["_id"]
            else:
                doc_data["created_at"] = datetime.utcnow()
                result = await run_with_timeout_and_retries(
                    lambda: self.analytics_collection.insert_one(doc_data),
                    timeout_s=settings.database_query_timeout_seconds,
                    retries=settings.database_max_retries,
                )
                analytics_doc.id = result.inserted_id
            
            logger.info(f"Performance metrics tracked for period {period_start}")
            return analytics_doc
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to track performance metrics in database")
        except Exception as e:
            logger.error(f"Unexpected error tracking performance metrics: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_popular_sessions(self, days: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """Identifying trending sessions."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Aggregate popular queries from sessions - sort by query_count directly
            pipeline = [
                {"$match": {"start_time": {"$gte": cutoff_date}}},
                {"$group": {
                    "_id": "$session_id",
                    "session_queries": {"$sum": "$query_count"},
                    "avg_quality": {"$avg": "$average_quality_score"},
                    "total_processing_time": {"$sum": "$total_processing_time"}
                }},
                {"$sort": {"session_queries": -1}},
                {"$limit": limit}
            ]
            
            aggregation = self.sessions_collection.aggregate(pipeline)
            aggregation = apply_query_timeout(aggregation)
            result = await aggregation.to_list(length=limit)
            return result
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to get popular queries from database")
        except Exception as e:
            logger.error(f"Unexpected error getting popular queries: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def get_content_quality_metrics(self, start_date: Optional[datetime] = None,
                                         end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Quality analysis."""
        try:
            # Build date filter
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            
            filter_dict = {}
            if date_filter:
                filter_dict["start_time"] = date_filter
            
            # Aggregate quality metrics
            pipeline = [
                {"$match": filter_dict},
                {"$group": {
                    "_id": None,
                    "avg_quality_score": {"$avg": "$average_quality_score"},
                    "avg_relevance_score": {"$avg": "$average_relevance_score"},
                    "quality_distribution": {
                        "$push": {
                            "quality": "$average_quality_score",
                            "relevance": "$average_relevance_score"
                        }
                    },
                    "total_sessions": {"$sum": 1}
                }}
            ]
            
            aggregation = self.sessions_collection.aggregate(pipeline)
            aggregation = apply_query_timeout(aggregation)
            result = await aggregation.to_list(length=1)
            if result:
                stats = result[0]
                del stats["_id"]  # Remove MongoDB internal field
                
                # Calculate quality distribution
                quality_dist = {"high": 0, "medium": 0, "low": 0}
                relevance_dist = {"high": 0, "medium": 0, "low": 0}
                
                for item in stats.get("quality_distribution", []):
                    quality = item.get("quality", 0)
                    relevance = item.get("relevance", 0)
                    
                    if quality >= 0.7:
                        quality_dist["high"] += 1
                    elif quality >= 0.4:
                        quality_dist["medium"] += 1
                    else:
                        quality_dist["low"] += 1
                    
                    if relevance >= 0.7:
                        relevance_dist["high"] += 1
                    elif relevance >= 0.4:
                        relevance_dist["medium"] += 1
                    else:
                        relevance_dist["low"] += 1
                
                stats["quality_distribution"] = quality_dist
                stats["relevance_distribution"] = relevance_dist
                return stats
            else:
                return {
                    "avg_quality_score": 0.0,
                    "avg_relevance_score": 0.0,
                    "quality_distribution": {"high": 0, "medium": 0, "low": 0},
                    "relevance_distribution": {"high": 0, "medium": 0, "low": 0},
                    "total_sessions": 0
                }
                
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to get content quality metrics from database")
        except Exception as e:
            logger.error(f"Unexpected error getting content quality metrics: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def generate_reports(self, report_type: str, start_date: datetime,
                             end_date: datetime) -> Dict[str, Any]:
        """Automated reporting."""
        try:
            if report_type == "daily":
                return await self._generate_daily_report(start_date, end_date)
            elif report_type == "weekly":
                return await self._generate_weekly_report(start_date, end_date)
            elif report_type == "monthly":
                return await self._generate_monthly_report(start_date, end_date)
            else:
                raise ValueError(f"Unsupported report type: {report_type}")
                
        except Exception as e:
            logger.error(f"Unexpected error generating reports: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def _generate_daily_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate daily analytics report."""
        try:
            # Get daily analytics data
            cursor = self.analytics_collection.find({
                "period_start": {"$gte": start_date, "$lt": end_date},
                "period_type": "daily"
            })
            cursor = apply_query_timeout(cursor)
            analytics_data = await cursor.to_list(length=None)
            
            # Aggregate daily data
            total_queries = sum(doc["total_queries"] for doc in analytics_data)
            total_sessions = sum(doc["unique_sessions"] for doc in analytics_data)
            
            # Compute distinct users across the period via query on query_sessions
            distinct_users_cursor = self.sessions_collection.find({
                "start_time": {"$gte": start_date, "$lt": end_date},
                "user_id": {"$ne": None}
            }).distinct("user_id")
            distinct_users_cursor = apply_query_timeout(distinct_users_cursor)
            distinct_users = await distinct_users_cursor.to_list(length=None)
            total_users = len(distinct_users)
            
            return {
                "report_type": "daily",
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "total_queries": total_queries,
                "total_sessions": total_sessions,
                "total_users": total_users,
                "daily_breakdown": analytics_data,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            raise RuntimeError(f"Failed to generate daily report: {str(e)}")
    
    async def _generate_weekly_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate weekly analytics report."""
        try:
            # Aggregate weekly data from daily analytics
            pipeline = [
                {"$match": {
                    "period_start": {"$gte": start_date, "$lt": end_date},
                    "period_type": "daily"
                }},
                {"$group": {
                    "_id": None,
                    "total_queries": {"$sum": "$total_queries"},
                    "total_sessions": {"$sum": "$unique_sessions"},
                    "total_users": {"$addToSet": "$unique_users"},
                    "avg_quality": {"$avg": "$average_content_quality"},
                    "total_processing_time": {"$sum": "$total_processing_time"}
                }}
            ]
            
            aggregation = self.analytics_collection.aggregate(pipeline)
            aggregation = apply_query_timeout(aggregation)
            result = await aggregation.to_list(length=1)
            
            if result:
                stats = result[0]
                del stats["_id"]
                return {
                    "report_type": "weekly",
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    **stats,
                    "generated_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "report_type": "weekly",
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "total_queries": 0,
                    "total_sessions": 0,
                    "total_users": 0,
                    "avg_quality": 0.0,
                    "total_processing_time": 0.0,
                    "generated_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            raise RuntimeError(f"Failed to generate weekly report: {str(e)}")
    
    async def _generate_monthly_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate monthly analytics report."""
        try:
            # Similar to weekly but with monthly aggregation
            pipeline = [
                {"$match": {
                    "period_start": {"$gte": start_date, "$lt": end_date},
                    "period_type": {"$in": ["daily", "weekly"]}
                }},
                {"$group": {
                    "_id": None,
                    "total_queries": {"$sum": "$total_queries"},
                    "total_sessions": {"$sum": "$unique_sessions"},
                    "total_users": {"$addToSet": "$unique_users"},
                    "avg_quality": {"$avg": "$average_content_quality"},
                    "total_processing_time": {"$sum": "$total_processing_time"},
                    "category_breakdown": {"$mergeObjects": "$category_breakdown"},
                    "domain_breakdown": {"$mergeObjects": "$domain_breakdown"}
                }}
            ]
            
            aggregation = self.analytics_collection.aggregate(pipeline)
            aggregation = apply_query_timeout(aggregation)
            result = await aggregation.to_list(length=1)
            
            if result:
                stats = result[0]
                del stats["_id"]
                return {
                    "report_type": "monthly",
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    **stats,
                    "generated_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "report_type": "monthly",
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "total_queries": 0,
                    "total_sessions": 0,
                    "total_users": 0,
                    "avg_quality": 0.0,
                    "total_processing_time": 0.0,
                    "category_breakdown": {},
                    "domain_breakdown": {},
                    "generated_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error generating monthly report: {e}")
            raise RuntimeError(f"Failed to generate monthly report: {str(e)}")
    
    async def cleanup_old_analytics(self, days_old: int = 365) -> int:
        """Data retention policies and cleanup procedures."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Clean up old sessions
            sessions_result = await run_with_timeout_and_retries(
                lambda: self.sessions_collection.delete_many({
                    "start_time": {"$lt": cutoff_date},
                    "status": "completed"
                }),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            # Clean up old analytics (keep only daily and weekly for long term)
            analytics_result = await run_with_timeout_and_retries(
                lambda: self.analytics_collection.delete_many({
                    "period_start": {"$lt": cutoff_date},
                    "period_type": "hourly"
                }),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            total_deleted = sessions_result.deleted_count + analytics_result.deleted_count
            logger.info(f"Cleaned up {total_deleted} old analytics records")
            return total_deleted
            
        except OperationFailure as e:
            logger.error(f"Database operation failed: {e}")
            raise RuntimeError("Failed to cleanup old analytics from database")
        except Exception as e:
            logger.error(f"Unexpected error cleaning up analytics: {e}")
            raise RuntimeError(f"Unexpected error: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on analytics collections."""
        try:
            # Test basic operations
            start_time = datetime.utcnow()
            
            # Count documents in both collections
            sessions_count = await self.sessions_collection.count_documents({})
            analytics_count = await self.analytics_collection.count_documents({})
            
            # Test find operations
            sample_session = await run_with_timeout_and_retries(
                lambda: self.sessions_collection.find_one({}),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            sample_analytics = await run_with_timeout_and_retries(
                lambda: self.analytics_collection.find_one({}),
                timeout_s=settings.database_query_timeout_seconds,
                retries=settings.database_max_retries,
            )
            
            # Test index status
            sessions_indexes = await self.sessions_collection.list_indexes().to_list(length=None)
            analytics_indexes = await self.analytics_collection.list_indexes().to_list(length=None)
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "sessions_count": sessions_count,
                "analytics_count": analytics_count,
                "has_sample_sessions": sample_session is not None,
                "has_sample_analytics": sample_analytics is not None,
                "sessions_index_count": len(sessions_indexes),
                "analytics_index_count": len(analytics_indexes),
                "response_time_seconds": response_time,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Analytics repository health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
