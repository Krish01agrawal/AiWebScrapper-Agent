"""
Main FastAPI application entry point.
"""
import logging
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.core.database import init_client, close_client
from app.core.gemini import init_gemini_client
from app.core.cache import initialize_cache, cleanup_task
from app.core.auth import initialize_api_key_manager
from app.scraper.session import init_scraper_session, close_scraper_session
from app.scraper.rate_limiter import init_rate_limit_manager, close_rate_limit_manager
from app.scraper.robots import init_robots_checker, close_robots_checker
from app.database.indexes import IndexManager
from app.database.migrations import MigrationManager
from app.api.routers import health, scrape, metrics, auth
from app.api.middleware import (
    RequestLoggingMiddleware, ErrorHandlingMiddleware, RequestValidationMiddleware,
    PerformanceMonitoringMiddleware, RateLimitingMiddleware, AuthenticationMiddleware,
)
from app.utils.logging import setup_logging

# Get settings instance
settings = get_settings()

# Configure structured logging
logger = setup_logging(
    log_level=settings.log_level,
    log_file=settings.log_file,
    enable_json=(settings.log_format == "json"),
    max_bytes=settings.log_max_bytes,
    backup_count=settings.log_backup_count
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="AI Web Scraper API",
    description="""
    ## AI-Powered Web Scraping and Content Processing API
    
    This API provides intelligent web scraping capabilities with AI-powered content analysis using Google Gemini.
    
    ### Key Features
    - **Intelligent Web Scraping**: Extract content from websites with respect for robots.txt
    - **AI Content Analysis**: Process and analyze scraped content using Google Gemini
    - **Structured Data Extraction**: Convert unstructured content into structured data
    - **Duplicate Detection**: Identify and filter duplicate content
    - **Content Summarization**: Generate concise summaries of scraped content
    - **Rate Limiting**: Built-in rate limiting to prevent abuse
    - **Caching**: In-memory caching for improved performance
    - **Authentication**: API key-based authentication for secure access
    
    ### Authentication
    Include your API key in the `X-API-Key` header for authenticated requests.
    
    ### Rate Limiting
    - Unauthenticated: 60 requests per minute
    - Authenticated: 120 requests per minute (configurable per key)
    
    ### Documentation
    - Interactive API docs: `/docs`
    - ReDoc documentation: `/redoc`
    - OpenAPI schema: `/openapi.json`
    """,
    version="1.0.0",
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    terms_of_service="https://example.com/terms/",
    debug=settings.debug,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "scraping",
            "description": "Web scraping and content processing operations",
        },
        {
            "name": "monitoring",
            "description": "Health checks and system monitoring",
        },
        {
            "name": "metrics",
            "description": "Performance metrics and analytics",
        },
        {
            "name": "auth",
            "description": "API key management and authentication",
        },
    ]
)

# Configure OpenAPI security scheme
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add API key security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication"
        }
    }
    
    # Apply security to protected routes
    for path_item in openapi_schema["paths"].values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "tags" in operation:
                # Apply to scraping and auth endpoints
                if any(tag in ["scraping", "auth"] for tag in operation.get("tags", [])):
                    operation["security"] = [{"ApiKeyAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add compression middleware if enabled
if settings.enable_compression:
    app.add_middleware(GZipMiddleware, minimum_size=1000)

# Initialize services
cache = None
if settings.cache_enabled:
    cache = initialize_cache(
        max_size=settings.cache_max_size,
        default_ttl=settings.cache_ttl_seconds
    )
api_key_manager = initialize_api_key_manager()

# Store services in app state
app.state.cache = cache
app.state.api_key_manager = api_key_manager

# Add API middleware (order matters - outermost to innermost)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(AuthenticationMiddleware, api_key_manager=api_key_manager)
app.add_middleware(RateLimitingMiddleware)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PerformanceMonitoringMiddleware)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    start_time = time.time()
    logger.info("Starting up FastAPI application...")
    
    try:
        # Initialize caching system
        if cache:
            logger.info("Cache system initialized")
        else:
            logger.info("Cache system disabled")
        
        # Initialize authentication system
        loaded_keys = api_key_manager.load_keys_from_env()
        logger.info(f"Authentication system initialized with {loaded_keys} API keys")
        
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
        
        # Start background tasks
        import asyncio
        asyncio.create_task(cleanup_task())
        logger.info("Background cleanup task started")
        
        # Health check for all services
        logger.info("Performing startup health checks...")
        # Add basic health checks here if needed
        
        startup_duration = time.time() - start_time
        logger.info(f"Application startup completed successfully in {startup_duration:.2f}s")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown."""
    logger.info("Shutting down FastAPI application...")
    
    try:
        # Log cache statistics
        if cache:
            cache_stats = await cache.get_stats()
            logger.info(f"Cache statistics: {cache_stats}")
        else:
            logger.info("Cache system was disabled")
        
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
app.include_router(scrape.router)
app.include_router(metrics.router)
app.include_router(auth.router)


@app.get("/")
async def root():
    """Root endpoint with comprehensive API information."""
    return {
        "message": "Welcome to AI Web Scraper API",
        "version": "1.0.0",
        "environment": settings.environment,
        "features": {
            "authentication": settings.api_auth_enabled,
            "caching": settings.cache_enabled,
            "compression": settings.enable_compression,
            "metrics": settings.metrics_enabled
        },
        "endpoints": {
            "documentation": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "scrape": "/api/v1/scrape"
        },
        "authentication": {
            "enabled": settings.api_auth_enabled,
            "header": "X-API-Key",
            "rate_limit": f"{settings.api_key_rate_limit_per_minute} requests/minute"
        },
        "cache": {
            "enabled": settings.cache_enabled,
            "ttl_seconds": settings.cache_ttl_seconds,
            "max_size": settings.cache_max_size
        }
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
