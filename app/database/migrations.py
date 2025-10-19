"""
Database migration and schema management utilities for handling database schema evolution.
"""
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import OperationFailure

from app.core.database import get_database
from app.core.config import settings

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manager class for managing database schema changes."""
    
    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize migration manager with database connection."""
        self.database = database or get_database()
        self.migrations_collection: AsyncIOMotorCollection = self.database.migrations
        self.migrations: List[Dict[str, Any]] = []
        self._load_migrations()
    
    def _load_migrations(self):
        """Load available migrations."""
        self.migrations = [
            {
                "version": "001",
                "name": "initial_schema",
                "description": "Create initial database schema and collections",
                "up": self._migration_001_initial_schema,
                "down": self._migration_001_initial_schema_down
            },
            {
                "version": "002",
                "name": "add_text_search_indexes",
                "description": "Add full-text search indexes to collections",
                "up": self._migration_002_add_text_search_indexes,
                "down": self._migration_002_add_text_search_indexes_down
            },
            {
                "version": "003",
                "name": "add_ttl_indexes",
                "description": "Add TTL indexes for automatic data cleanup",
                "up": self._migration_003_add_ttl_indexes,
                "down": self._migration_003_add_ttl_indexes_down
            },
            {
                "version": "004",
                "name": "add_compound_indexes",
                "description": "Add compound indexes for improved query performance",
                "up": self._migration_004_add_compound_indexes,
                "down": self._migration_004_add_compound_indexes_down
            },
            {
                "version": "005",
                "name": "add_analytics_collections",
                "description": "Add analytics and session tracking collections",
                "up": self._migration_005_add_analytics_collections,
                "down": self._migration_005_add_analytics_collections_down
            }
        ]
    
    async def create_migration(self, version: str, name: str, description: str,
                              up_function: callable, down_function: callable) -> Dict[str, Any]:
        """Generate new migration scripts."""
        try:
            migration = {
                "version": version,
                "name": name,
                "description": description,
                "up": up_function,
                "down": down_function,
                "created_at": datetime.utcnow(),
                "applied_at": None
            }
            
            # Add to migrations list
            self.migrations.append(migration)
            
            logger.info(f"Created migration {version}: {name}")
            return migration
            
        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            raise RuntimeError(f"Migration creation failed: {str(e)}")
    
    async def apply_migrations(self, target_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute pending migrations."""
        try:
            # Get current schema version
            current_version = await self.get_migration_status()
            
            # Determine which migrations to apply
            migrations_to_apply = []
            for migration in self.migrations:
                if migration["version"] > current_version:
                    if target_version and migration["version"] > target_version:
                        break
                    migrations_to_apply.append(migration)
            
            applied_migrations = []
            
            for migration in migrations_to_apply:
                try:
                    logger.info(f"Applying migration {migration['version']}: {migration['name']}")
                    
                    # Execute migration
                    await migration["up"]()
                    
                    # Record migration
                    await self._record_migration(migration, "applied")
                    
                    applied_migrations.append(migration)
                    logger.info(f"Successfully applied migration {migration['version']}")
                    
                except Exception as e:
                    logger.error(f"Failed to apply migration {migration['version']}: {e}")
                    # Rollback applied migrations
                    await self._rollback_migrations(applied_migrations)
                    raise RuntimeError(f"Migration {migration['version']} failed: {str(e)}")
            
            logger.info(f"Applied {len(applied_migrations)} migrations successfully")
            return applied_migrations
            
        except Exception as e:
            logger.error(f"Failed to apply migrations: {e}")
            raise RuntimeError(f"Migration application failed: {str(e)}")
    
    async def rollback_migration(self, version: str) -> bool:
        """Revert changes if needed."""
        try:
            # Find migration
            migration = next((m for m in self.migrations if m["version"] == version), None)
            if not migration:
                raise ValueError(f"Migration {version} not found")
            
            # Check if migration was applied
            migration_record = await self.migrations_collection.find_one({"version": version})
            if not migration_record:
                logger.warning(f"Migration {version} was not applied")
                return False
            
            logger.info(f"Rolling back migration {version}: {migration['name']}")
            
            # Execute rollback
            await migration["down"]()
            
            # Remove migration record
            await self.migrations_collection.delete_one({"version": version})
            
            logger.info(f"Successfully rolled back migration {version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback migration {version}: {e}")
            raise RuntimeError(f"Migration rollback failed: {str(e)}")
    
    async def get_migration_status(self) -> str:
        """Check current schema version."""
        try:
            # Get the latest applied migration
            latest_migration = await self.migrations_collection.find_one(
                {}, sort=[("version", -1)]
            )
            
            if latest_migration:
                return latest_migration["version"]
            else:
                return "000"  # No migrations applied
                
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            raise RuntimeError(f"Migration status check failed: {str(e)}")
    
    async def _record_migration(self, migration: Dict[str, Any], status: str):
        """Record migration in database."""
        try:
            migration_record = {
                "version": migration["version"],
                "name": migration["name"],
                "description": migration["description"],
                "status": status,
                "applied_at": datetime.utcnow(),
                "created_at": migration.get("created_at", datetime.utcnow())
            }
            
            await self.migrations_collection.insert_one(migration_record)
            
        except Exception as e:
            logger.error(f"Failed to record migration: {e}")
            raise RuntimeError(f"Migration recording failed: {str(e)}")
    
    async def _rollback_migrations(self, migrations: List[Dict[str, Any]]):
        """Rollback a list of migrations."""
        for migration in reversed(migrations):
            try:
                await migration["down"]()
                await self.migrations_collection.delete_one({"version": migration["version"]})
                logger.info(f"Rolled back migration {migration['version']}")
            except Exception as e:
                logger.error(f"Failed to rollback migration {migration['version']}: {e}")
    
    # Migration implementations
    async def _migration_001_initial_schema(self):
        """Create initial database schema and collections."""
        try:
            # Create collections
            collections = [
                "queries", "content", "processed_content", "processed_cache",
                "query_sessions", "analytics", "migrations"
            ]
            
            for collection_name in collections:
                if collection_name not in await self.database.list_collection_names():
                    await self.database.create_collection(collection_name)
                    logger.info(f"Created collection: {collection_name}")
            
            # Create basic indexes
            await self._create_basic_indexes()
            
        except Exception as e:
            logger.error(f"Migration 001 failed: {e}")
            raise
    
    async def _migration_001_initial_schema_down(self):
        """Rollback initial schema creation."""
        try:
            # Drop collections (be careful in production!)
            collections = [
                "queries", "content", "processed_content", "processed_cache",
                "query_sessions", "analytics"
            ]
            
            for collection_name in collections:
                if collection_name in await self.database.list_collection_names():
                    await self.database.drop_collection(collection_name)
                    logger.info(f"Dropped collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Migration 001 rollback failed: {e}")
            raise
    
    async def _migration_002_add_text_search_indexes(self):
        """Add full-text search indexes to collections."""
        try:
            if not settings.database_enable_text_search:
                logger.info("Text search disabled, skipping text indexes")
                return
            
            # Add text indexes
            text_indexes = {
                "queries": [
                    [("base_result.query_text", "text"), ("suggestions", "text")]
                ],
                "content": [
                    [("title", "text"), ("content", "text"), ("description", "text")]
                ],
                "processed_content": [
                    [("cleaned_content", "text"), ("summary.executive_summary", "text"), ("summary.key_points", "text")]
                ]
            }
            
            for collection_name, indexes in text_indexes.items():
                collection = self.database[collection_name]
                for index in indexes:
                    try:
                        await collection.create_index(index, background=True)
                        logger.info(f"Created text index on {collection_name}: {index}")
                    except Exception as e:
                        logger.warning(f"Failed to create text index on {collection_name}: {e}")
            
        except Exception as e:
            logger.error(f"Migration 002 failed: {e}")
            raise
    
    async def _migration_002_add_text_search_indexes_down(self):
        """Rollback text search indexes."""
        try:
            # Drop text indexes
            collections = ["queries", "content", "processed_content"]
            
            for collection_name in collections:
                collection = self.database[collection_name]
                indexes = await collection.list_indexes().to_list(length=1000)
                
                for index in indexes:
                    if index.get("key", {}).get("_fts") == "text":
                        try:
                            await collection.drop_index(index["name"])
                            logger.info(f"Dropped text index: {index['name']}")
                        except Exception as e:
                            logger.warning(f"Failed to drop text index: {e}")
            
        except Exception as e:
            logger.error(f"Migration 002 rollback failed: {e}")
            raise
    
    async def _migration_003_add_ttl_indexes(self):
        """Add TTL indexes for automatic data cleanup."""
        try:
            # TTL indexes for automatic cleanup
            ttl_indexes = {}
            
            # Only add content TTL if enabled
            if settings.database_content_ttl_days > 0 and getattr(settings, 'database_enable_content_ttl', False):
                ttl_indexes["content"] = {
                    "field": "timestamp",
                    "expire_after_seconds": settings.database_content_ttl_days * 24 * 60 * 60
                }
            
            # Always add analytics TTL
            ttl_indexes["analytics"] = {
                "field": "period_start",
                "expire_after_seconds": settings.database_analytics_retention_days * 24 * 60 * 60
            }
            
            for collection_name, config in ttl_indexes.items():
                collection = self.database[collection_name]
                try:
                    await collection.create_index(
                        config["field"],
                        expireAfterSeconds=config["expire_after_seconds"],
                        background=True
                    )
                    logger.info(f"Created TTL index on {collection_name}: {config['field']}")
                except Exception as e:
                    logger.warning(f"Failed to create TTL index on {collection_name}: {e}")
            
        except Exception as e:
            logger.error(f"Migration 003 failed: {e}")
            raise
    
    async def _migration_003_add_ttl_indexes_down(self):
        """Rollback TTL indexes."""
        try:
            collections = ["content", "analytics"]
            
            for collection_name in collections:
                collection = self.database[collection_name]
                indexes = await collection.list_indexes().to_list(length=1000)
                
                for index in indexes:
                    if index.get("expireAfterSeconds"):
                        try:
                            await collection.drop_index(index["name"])
                            logger.info(f"Dropped TTL index: {index['name']}")
                        except Exception as e:
                            logger.warning(f"Failed to drop TTL index: {e}")
            
        except Exception as e:
            logger.error(f"Migration 003 rollback failed: {e}")
            raise
    
    async def _migration_004_add_compound_indexes(self):
        """Add compound indexes for improved query performance."""
        try:
            # Compound indexes for common query patterns
            compound_indexes = {
                "queries": [
                    [("session_id", 1), ("created_at", -1)],
                    [("user_id", 1), ("created_at", -1)],
                    [("base_result.category", 1), ("status", 1), ("created_at", -1)]
                ],
                "content": [
                    [("query_id", 1), ("timestamp", -1)],
                    [("content_type", 1), ("content_quality_score", -1)],
                    [("session_id", 1), ("timestamp", -1)]
                ],
                "processed_content": [
                    [("query_id", 1), ("processing_timestamp", -1)],
                    [("enhanced_quality_score", -1), ("processing_timestamp", -1)],
                    [("original_content_id", 1), ("processing_timestamp", -1)]
                ],
                "query_sessions": [
                    [("start_time", -1), ("status", 1)],
                    [("user_id", 1), ("start_time", -1)],
                    [("status", 1), ("start_time", -1)]
                ],
                "analytics": [
                    [("period_start", 1), ("period_end", 1), ("period_type", 1)],
                    [("period_type", 1), ("period_start", -1)]
                ]
            }
            
            for collection_name, indexes in compound_indexes.items():
                collection = self.database[collection_name]
                for index in indexes:
                    try:
                        await collection.create_index(index, background=True)
                        logger.info(f"Created compound index on {collection_name}: {index}")
                    except Exception as e:
                        logger.warning(f"Failed to create compound index on {collection_name}: {e}")
            
        except Exception as e:
            logger.error(f"Migration 004 failed: {e}")
            raise
    
    async def _migration_004_add_compound_indexes_down(self):
        """Rollback compound indexes."""
        try:
            collections = ["queries", "content", "processed_content", "query_sessions", "analytics"]
            
            for collection_name in collections:
                collection = self.database[collection_name]
                indexes = await collection.list_indexes().to_list(length=1000)
                
                for index in indexes:
                    # Drop compound indexes (those with multiple fields)
                    if len(index.get("key", {})) > 1 and index["name"] != "_id_":
                        try:
                            await collection.drop_index(index["name"])
                            logger.info(f"Dropped compound index: {index['name']}")
                        except Exception as e:
                            logger.warning(f"Failed to drop compound index: {e}")
            
        except Exception as e:
            logger.error(f"Migration 004 rollback failed: {e}")
            raise
    
    async def _migration_005_add_analytics_collections(self):
        """Add analytics and session tracking collections."""
        try:
            # Create analytics-specific collections
            analytics_collections = [
                "processed_content_archive",
                "migration_history"
            ]
            
            for collection_name in analytics_collections:
                if collection_name not in await self.database.list_collection_names():
                    await self.database.create_collection(collection_name)
                    logger.info(f"Created analytics collection: {collection_name}")
            
            # Add analytics-specific indexes
            await self._create_analytics_indexes()
            
        except Exception as e:
            logger.error(f"Migration 005 failed: {e}")
            raise
    
    async def _migration_005_add_analytics_collections_down(self):
        """Rollback analytics collections."""
        try:
            analytics_collections = [
                "processed_content_archive",
                "migration_history"
            ]
            
            for collection_name in analytics_collections:
                if collection_name in await self.database.list_collection_names():
                    await self.database.drop_collection(collection_name)
                    logger.info(f"Dropped analytics collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Migration 005 rollback failed: {e}")
            raise
    
    async def _create_basic_indexes(self):
        """Create basic indexes for all collections."""
        try:
            basic_indexes = {
                "queries": ["session_id", "user_id", "created_at", "status"],
                "content": ["url", "query_id", "timestamp", "content_type"],
                "processed_content": ["original_content_id", "query_id", "processing_timestamp"],
                "query_sessions": ["session_id", "user_id", "start_time", "status"],
                "analytics": ["period_start", "period_end", "period_type"]
            }
            
            for collection_name, fields in basic_indexes.items():
                collection = self.database[collection_name]
                for field in fields:
                    try:
                        await collection.create_index(field, background=True)
                        logger.info(f"Created basic index on {collection_name}: {field}")
                    except Exception as e:
                        logger.warning(f"Failed to create basic index on {collection_name}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to create basic indexes: {e}")
            raise
    
    async def _create_analytics_indexes(self):
        """Create analytics-specific indexes."""
        try:
            analytics_indexes = {
                "processed_content_archive": ["original_content_id", "processing_timestamp"],
                "migration_history": ["version", "applied_at"]
            }
            
            for collection_name, fields in analytics_indexes.items():
                collection = self.database[collection_name]
                for field in fields:
                    try:
                        await collection.create_index(field, background=True)
                        logger.info(f"Created analytics index on {collection_name}: {field}")
                    except Exception as e:
                        logger.warning(f"Failed to create analytics index on {collection_name}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to create analytics indexes: {e}")
            raise
    
    async def validate_schema(self) -> Dict[str, Any]:
        """Schema validation utilities to ensure data integrity."""
        try:
            validation_results = {}
            
            # Check if all required collections exist
            required_collections = [
                "queries", "content", "processed_content", "processed_cache",
                "query_sessions", "analytics", "migrations"
            ]
            
            existing_collections = await self.database.list_collection_names()
            validation_results["collections"] = {
                "required": required_collections,
                "existing": existing_collections,
                "missing": [c for c in required_collections if c not in existing_collections]
            }
            
            # Check indexes for each collection
            validation_results["indexes"] = {}
            for collection_name in existing_collections:
                collection = self.database[collection_name]
                indexes = await collection.list_indexes().to_list(length=1000)
                validation_results["indexes"][collection_name] = {
                    "count": len(indexes),
                    "indexes": [idx["name"] for idx in indexes]
                }
            
            # Check migration status
            validation_results["migrations"] = {
                "current_version": await self.get_migration_status(),
                "applied_migrations": await self.migrations_collection.find().to_list(length=1000)
            }
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            raise RuntimeError(f"Schema validation failed: {str(e)}")
    
    async def backup_before_migration(self, migration_version: str) -> str:
        """Backup creation before applying migrations."""
        try:
            backup_name = f"backup_before_migration_{migration_version}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # Create backup of all collections
            backup_data = {}
            for collection_name in await self.database.list_collection_names():
                collection = self.database[collection_name]
                documents = await collection.find().to_list(length=1000)
                backup_data[collection_name] = documents
            
            # Store backup (in production, this should be stored externally)
            backup_collection = self.database.backups
            await backup_collection.insert_one({
                "backup_name": backup_name,
                "migration_version": migration_version,
                "created_at": datetime.utcnow(),
                "data": backup_data
            })
            
            logger.info(f"Created backup: {backup_name}")
            return backup_name
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise RuntimeError(f"Backup creation failed: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on migration system."""
        try:
            start_time = datetime.utcnow()
            
            # Check migrations collection
            migration_count = await self.migrations_collection.count_documents({})
            
            # Check current version
            current_version = await self.get_migration_status()
            
            # Check if all required collections exist
            required_collections = [
                "queries", "content", "processed_content", "processed_cache",
                "query_sessions", "analytics", "migrations"
            ]
            existing_collections = await self.database.list_collection_names()
            missing_collections = [c for c in required_collections if c not in existing_collections]
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            return {
                "status": "healthy" if not missing_collections else "degraded",
                "current_version": current_version,
                "applied_migrations": migration_count,
                "missing_collections": missing_collections,
                "response_time_seconds": response_time,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Migration health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
