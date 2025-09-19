"""
MongoDB connection management using Motor async driver.
"""
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

# Global client variable
client: Optional[AsyncIOMotorClient] = None

logger = logging.getLogger(__name__)


async def init_client() -> None:
    """Initialize MongoDB client on startup."""
    global client
    
    try:
        # Create client with connection pooling settings
        client = AsyncIOMotorClient(
            settings.mongodb_uri,
            maxPoolSize=settings.mongodb_max_pool_size,
            minPoolSize=settings.mongodb_min_pool_size,
            maxIdleTimeMS=settings.mongodb_max_idle_time_ms,
            serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
            connectTimeoutMS=settings.mongodb_connect_timeout_ms
        )
        
        # Test connection with ping
        await client.admin.command('ping')
        logger.info("MongoDB client initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB client: {e}")
        raise


async def close_client() -> None:
    """Close MongoDB client on shutdown."""
    global client
    
    if client:
        try:
            client.close()
            logger.info("MongoDB client closed successfully")
        except Exception as e:
            logger.error(f"Error closing MongoDB client: {e}")
        finally:
            client = None


def get_client() -> AsyncIOMotorClient:
    """Get the global MongoDB client."""
    if client is None:
        raise RuntimeError("MongoDB client not initialized. Call init_client() first.")
    return client


def get_database():
    """Get the configured MongoDB database."""
    return get_client()[settings.mongodb_db]
