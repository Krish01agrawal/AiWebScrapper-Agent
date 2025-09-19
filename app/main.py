"""
Main FastAPI application entry point.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_client, close_client
from app.core.gemini import init_gemini_client
from app.scraper.session import init_scraper_session, close_scraper_session
from app.scraper.rate_limiter import init_rate_limit_manager, close_rate_limit_manager
from app.scraper.robots import init_robots_checker, close_robots_checker
from app.database.indexes import IndexManager
from app.database.migrations import MigrationManager
from app.api.routers import health

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Traycer Try API",
    description="AI-powered web scraping and content processing API",
    version="1.0.0",
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting up FastAPI application...")
    
    try:
        # Initialize MongoDB client
        await init_client()
        logger.info("MongoDB client initialized")
        
        # Initialize database indexes and migrations
        try:
            # Apply database migrations
            migration_manager = MigrationManager()
            await migration_manager.apply_migrations()
            logger.info("Database migrations applied successfully")
            
            # Create database indexes
            index_manager = IndexManager()
            await index_manager.create_all_indexes()
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.warning(f"Database initialization failed: {e}")
            # Continue startup even if database initialization fails
            logger.warning("Continuing startup without full database initialization")
        
        # Initialize Gemini client
        gemini_client = init_gemini_client()
        if gemini_client:
            logger.info("Gemini client initialized")
        else:
            logger.warning("Gemini client initialization failed")
        
        # Initialize scraper services
        await init_scraper_session()
        logger.info("Scraper session initialized")
        
        await init_rate_limit_manager()
        logger.info("Rate limit manager initialized")
        
        await init_robots_checker()
        logger.info("Robots checker initialized")
            
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown."""
    logger.info("Shutting down FastAPI application...")
    
    try:
        # Close scraper services
        await close_robots_checker()
        logger.info("Robots checker closed")
        
        await close_rate_limit_manager()
        logger.info("Rate limit manager closed")
        
        await close_scraper_session()
        logger.info("Scraper session closed")
        
        # Close MongoDB client
        await close_client()
        logger.info("MongoDB client closed")
        
        logger.info("Application shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Include routers
app.include_router(health.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Traycer Try API",
        "version": "1.0.0",
        "environment": settings.environment
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
