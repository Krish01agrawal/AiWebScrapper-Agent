"""
Health check router with comprehensive system health endpoints.
"""
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.database import get_client
from app.core.gemini import test_gemini_connection
from app.scraper.session import test_scraper_session
from app.scraper.schemas import ScrapedContent, ContentType
from app.agents.schemas import ParsedQuery, BaseQueryResult, QueryCategory
from app.core.config import get_settings
from app.utils.health import get_health_checker, HealthStatus
from app.dependencies import (
    get_query_repository, get_content_repository, get_processed_repository,
    get_analytics_repository, get_database_service
)

router = APIRouter(prefix="/health", tags=["health"])

# Health check timeout settings
HEALTH_CHECK_TIMEOUT = 10  # seconds


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    message: str


class DatabaseHealthResponse(BaseModel):
    """Database health check response model."""
    status: str
    timestamp: datetime
    database: str


class GeminiHealthResponse(BaseModel):
    """Gemini API health check response model."""
    status: str
    timestamp: datetime
    gemini: str


class ScraperHealthResponse(BaseModel):
    """Scraper health check response model."""
    status: str
    timestamp: datetime
    scraper: str
    details: Dict[str, Any]


class ProcessingHealthResponse(BaseModel):
    """Processing health check response model."""
    status: str
    timestamp: datetime
    processing: str
    details: Dict[str, Any]
    agent_tests: Dict[str, Any]
    configuration: Dict[str, Any]
    performance_metrics: Dict[str, Any]


@router.get("/", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check endpoint."""
    try:
        health_checker = get_health_checker()
        health_status = await health_checker.check_all()
        
        # Return appropriate HTTP status code based on health
        if health_status["status"] == HealthStatus.UNHEALTHY:
            return JSONResponse(
                content=health_status,
                status_code=503
            )
        elif health_status["status"] == HealthStatus.DEGRADED:
            return JSONResponse(
                content=health_status,
                status_code=200
            )
        else:
            return health_status
    
    except Exception as e:
        return JSONResponse(
            content={
                "status": HealthStatus.UNHEALTHY,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "uptime_seconds": 0
            },
            status_code=503
        )


@router.get("/live")
async def liveness_probe() -> Dict[str, Any]:
    """Kubernetes liveness probe endpoint."""
    try:
        health_checker = get_health_checker()
        is_alive = await health_checker.liveness_check()
        
        return {
            "status": "alive" if is_alive else "dead",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        return JSONResponse(
            content={
                "status": "dead",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            },
            status_code=503
        )


@router.get("/ready")
async def readiness_probe() -> Dict[str, Any]:
    """Kubernetes readiness probe endpoint."""
    try:
        health_checker = get_health_checker()
        is_ready = await health_checker.readiness_check()
        
        if not is_ready:
            return JSONResponse(
                content={
                    "status": "not_ready",
                    "message": "Service not ready",
                    "timestamp": datetime.utcnow().isoformat()
                },
                status_code=503
            )
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        return JSONResponse(
            content={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            },
            status_code=503
        )


@router.get("/components")
async def component_health() -> Dict[str, Any]:
    """Detailed health check for each component."""
    try:
        health_checker = get_health_checker()
        health_status = await health_checker.check_all()
        
        return {
            "overall_status": health_status["status"],
            "components": health_status["components"],
            "timestamp": health_status["timestamp"]
        }
    
    except Exception as e:
        return JSONResponse(
            content={
                "overall_status": HealthStatus.UNHEALTHY,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )


@router.get("/database")
async def database_health() -> Dict[str, Any]:
    """Detailed database health check."""
    try:
        health_checker = get_health_checker()
        db_health = await health_checker.check_database()
        
        return {
            "status": db_health.status,
            "response_time_ms": db_health.response_time_ms,
            "details": db_health.details,
            "message": db_health.message,
            "timestamp": db_health.last_check.isoformat()
        }
    
    except Exception as e:
        return JSONResponse(
            content={
                "status": HealthStatus.UNHEALTHY,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )


@router.get("/cache")
async def cache_health() -> Dict[str, Any]:
    """Cache system health and statistics."""
    try:
        health_checker = get_health_checker()
        cache_health = await health_checker.check_cache()
        
        return {
            "status": cache_health.status,
            "response_time_ms": cache_health.response_time_ms,
            "statistics": cache_health.details,
            "message": cache_health.message,
            "timestamp": cache_health.last_check.isoformat()
        }
    
    except Exception as e:
        return JSONResponse(
            content={
                "status": HealthStatus.UNHEALTHY,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )


@router.get("/system")
async def system_health() -> Dict[str, Any]:
    """System resource health check."""
    try:
        health_checker = get_health_checker()
        system_health = health_checker.check_system_resources()
        
        return {
            "status": system_health.status,
            "resources": system_health.details,
            "message": system_health.message,
            "timestamp": system_health.last_check.isoformat()
        }
    
    except Exception as e:
        return JSONResponse(
            content={
                "status": HealthStatus.UNHEALTHY,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )


@router.get("/db", response_model=DatabaseHealthResponse)
async def database_health_check() -> DatabaseHealthResponse:
    """Database health check endpoint."""
    try:
        # Test MongoDB connectivity
        client = get_client()
        await asyncio.wait_for(client.admin.command('ping'), timeout=HEALTH_CHECK_TIMEOUT)
        
        return DatabaseHealthResponse(
            status="ok",
            timestamp=datetime.utcnow(),
            database="connected"
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Database health check timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database health check failed: {str(e)}"
        )


@router.get("/gemini", response_model=GeminiHealthResponse)
async def gemini_health_check() -> GeminiHealthResponse:
    """Gemini API health check endpoint."""
    try:
        # Test Gemini API connectivity
        is_connected = await asyncio.wait_for(test_gemini_connection(), timeout=HEALTH_CHECK_TIMEOUT)
        
        if is_connected:
            return GeminiHealthResponse(
                status="ok",
                timestamp=datetime.utcnow(),
                gemini="connected"
            )
        else:
            raise HTTPException(
                status_code=503,
                detail="Gemini API health check failed"
            )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Gemini API health check timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Gemini API health check failed: {str(e)}"
        )


@router.get("/scraper", response_model=ScraperHealthResponse)
async def scraper_health_check() -> ScraperHealthResponse:
    """Scraper health check endpoint."""
    try:
        # Test scraper session availability and basic connectivity
        is_healthy = await asyncio.wait_for(test_scraper_session(), timeout=HEALTH_CHECK_TIMEOUT)
        
        if is_healthy:
            return ScraperHealthResponse(
                status="ok",
                timestamp=datetime.utcnow(),
                scraper="connected",
                details={
                    "session_test": "passed",
                    "http_client": "available",
                    "connectivity": "verified"
                }
            )
        else:
            raise HTTPException(
                status_code=503,
                detail="Scraper health check failed"
            )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Scraper health check timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Scraper health check failed: {str(e)}"
        )


@router.get("/processing", response_model=ProcessingHealthResponse)
async def processing_health_check() -> ProcessingHealthResponse:
    """Processing pipeline health check endpoint with comprehensive agent testing."""
    try:
        settings = get_settings()
        processing_timeout = getattr(settings, 'health_processing_test_timeout', 8)
        return await asyncio.wait_for(
            _perform_processing_health_check(), 
            timeout=processing_timeout
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="Processing health check timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Processing health check failed: {str(e)}"
        )


async def _perform_processing_health_check() -> ProcessingHealthResponse:
    """Perform comprehensive processing health check with agent functional tests."""
    from app.dependencies import (
    get_processing_orchestrator,
    get_content_cleaning_agent,
    get_ai_analysis_agent,
    get_summarization_agent,
    get_structured_data_extractor,
    get_duplicate_detection_agent
)
    from app.agents.schemas import ParsedQuery
    from app.scraper.schemas import ScrapedContent
    from app.core.config import get_settings
    
    start_time = time.time()
    settings = get_settings()
    
    # Test processing orchestrator availability with graceful degradation
    try:
        orchestrator = await get_processing_orchestrator()
        orchestrator_status = "available"
    except Exception as e:
        orchestrator_status = "degraded"
        # Continue with health check using individual agent tests
    
    # Perform lightweight functional tests for each agent
    agent_tests = await _test_processing_agents()
    
    # Validate configuration settings
    configuration = await _validate_processing_configuration(settings)
    
    # Check resource availability
    resource_availability = await _check_resource_availability()
    
    # Calculate performance metrics
    performance_metrics = {
        "health_check_duration_ms": round((time.time() - start_time) * 1000, 2),
        "agent_test_count": len(agent_tests),
        "successful_tests": sum(1 for test in agent_tests.values() if test.get("status") == "passed"),
        "failed_tests": sum(1 for test in agent_tests.values() if test.get("status") == "failed")
    }
    
    # Determine overall pipeline status
    pipeline_status = "ready" if all([
        test.get("status") == "passed" for test in agent_tests.values()
    ]) else "degraded"
    
    # Set overall status based on orchestrator and agent tests
    overall_status = "healthy" if pipeline_status == "ready" and orchestrator_status == "available" else "degraded"
    
    return ProcessingHealthResponse(
        status="ok",
        timestamp=datetime.utcnow(),
        processing=orchestrator_status,
        details={
            "pipeline": pipeline_status,
            "orchestrator": orchestrator_status,
            "resource_availability": resource_availability,
            "overall_status": overall_status
        },
        agent_tests=agent_tests,
        configuration=configuration,
        performance_metrics=performance_metrics
    )


async def _test_processing_agents() -> Dict[str, Any]:
    """Perform lightweight functional tests for each processing agent."""
    settings = get_settings()
    agent_timeout = getattr(settings, 'health_agent_test_timeout', 5)
    agent_tests = {}
    
    # Test Content Cleaning Agent
    try:
        cleaning_agent = await get_content_cleaning_agent()
        test_content = ScrapedContent(
            url="http://test.com",
            title="Test Content",
            content="This is a test content with <html> tags and extra   spaces.",
            content_type=ContentType.GENERAL,
            processing_time=0.1,
            content_size_bytes=100,
            extraction_method="test_extraction"
        )
        cleaned_content = await asyncio.wait_for(
            cleaning_agent.clean_content(test_content),
            timeout=agent_timeout
        )
        
        agent_tests["content_cleaning"] = {
            "status": "passed",
            "test_type": "functional",
            "input": test_content,
            "output": cleaned_content,
            "processing_time_ms": 0  # Will be updated if timing is available
        }
    except Exception as e:
        agent_tests["content_cleaning"] = {
            "status": "failed",
            "test_type": "functional",
            "error": str(e),
            "processing_time_ms": 0
        }
    
    # Test AI Analysis Agent (lightweight test)
    try:
        ai_agent = await get_ai_analysis_agent()
        test_query = ParsedQuery(
            base_result=BaseQueryResult(
                query_text="test query",
                confidence_score=1.0,
                processing_time=0.1,
                category=QueryCategory.GENERAL
            )
        )
        test_content = "This is a test content for AI analysis."
        
        # Only test if Gemini client is available
        if hasattr(ai_agent, 'gemini_client') and ai_agent.gemini_client:
            insights = await asyncio.wait_for(
                ai_agent.analyze_content(test_content, test_query),
                timeout=agent_timeout
            )
            
            agent_tests["ai_analysis"] = {
                "status": "passed",
                "test_type": "functional",
                "input_length": len(test_content),
                "output_confidence": getattr(insights, 'confidence_score', 0.0),
                "processing_time_ms": 0
            }
        else:
            agent_tests["ai_analysis"] = {
                "status": "skipped",
                "test_type": "functional",
                "reason": "Gemini client not available",
                "processing_time_ms": 0
            }
    except Exception as e:
        agent_tests["ai_analysis"] = {
            "status": "failed",
            "test_type": "functional",
            "error": str(e),
            "processing_time_ms": 0
        }
    
    # Test Summarization Agent (lightweight test)
    try:
        summary_agent = await get_summarization_agent()
        test_query = ParsedQuery(
            base_result=BaseQueryResult(
                query_text="test query",
                confidence_score=1.0,
                processing_time=0.1,
                category=QueryCategory.GENERAL
            )
        )
        test_content = "This is a test content for summarization testing."
        
        if hasattr(summary_agent, 'gemini_client') and summary_agent.gemini_client:
            summary = await asyncio.wait_for(
                summary_agent.summarize_content(test_content, test_query, max_length=100),
                timeout=agent_timeout
            )
            
            agent_tests["summarization"] = {
                "status": "passed",
                "test_type": "functional",
                "input_length": len(test_content),
                "output_length": len(summary.detailed_summary),
                "processing_time_ms": 0
            }
        else:
            agent_tests["summarization"] = {
                "status": "skipped",
                "test_type": "functional",
                "reason": "Gemini client not available",
                "processing_time_ms": 0
            }
    except Exception as e:
        agent_tests["summarization"] = {
            "status": "failed",
            "test_type": "functional",
            "error": str(e),
            "processing_time_ms": 0
        }
    
    # Test Structured Data Extractor
    try:
        extraction_agent = await get_structured_data_extractor()
        test_content = "Product: Test Product, Price: $99.99, Category: Electronics"
        test_query = ParsedQuery(
            base_result=BaseQueryResult(
                query_text="test query",
                confidence_score=1.0,
                processing_time=0.1,
                category=QueryCategory.GENERAL
            )
        )
        
        structured_data = await asyncio.wait_for(
            extraction_agent.extract_structured_data(test_content, test_query),
            timeout=agent_timeout
        )
        
        agent_tests["structured_extraction"] = {
            "status": "passed",
            "test_type": "functional",
            "input_length": len(test_content),
            "entities_found": len(structured_data.entities),
            "key_value_pairs": len(structured_data.key_value_pairs),
            "processing_time_ms": 0
        }
    except Exception as e:
        agent_tests["structured_extraction"] = {
            "status": "failed",
            "test_type": "functional",
            "error": str(e),
            "processing_time_ms": 0
        }
    
    # Test Duplicate Detection Agent (lightweight test)
    try:
        duplicate_agent = await get_duplicate_detection_agent()
        test_contents = [
            ScrapedContent(
                url="http://test1.com",
                title="Test Content 1",
                content="This is test content for duplicate detection.",
                content_type=ContentType.GENERAL,
                processing_time=0.1,
                content_size_bytes=100,
                extraction_method="test_extraction"
            ),
            ScrapedContent(
                url="http://test2.com",
                title="Test Content 2",
                content="This is different test content.",
                content_type=ContentType.GENERAL,
                processing_time=0.1,
                content_size_bytes=100,
                extraction_method="test_extraction"
            )
        ]
        
        duplicate_analyses = await asyncio.wait_for(
            duplicate_agent.detect_duplicates(test_contents),
            timeout=agent_timeout
        )
        
        agent_tests["duplicate_detection"] = {
            "status": "passed",
            "test_type": "functional",
            "input_count": len(test_contents),
            "output_count": len(duplicate_analyses),
            "processing_time_ms": 0
        }
    except Exception as e:
        agent_tests["duplicate_detection"] = {
            "status": "failed",
            "test_type": "functional",
            "error": str(e),
            "processing_time_ms": 0
        }
    
    return agent_tests


async def _validate_processing_configuration(settings) -> Dict[str, Any]:
    """Validate processing configuration settings."""
    config_validation = {
        "status": "passed",
        "checks": {},
        "warnings": []
    }
    
    # Check timeout configurations
    if hasattr(settings, 'processing_timeout_seconds') and hasattr(settings, 'processing_content_timeout'):
        if settings.processing_timeout_seconds <= settings.processing_content_timeout:
            config_validation["warnings"].append(
                "processing_timeout_seconds should be greater than processing_content_timeout"
            )
    
    # Check concurrency configurations
    if hasattr(settings, 'processing_concurrency') and hasattr(settings, 'processing_max_concurrent_ai_analyses'):
        if settings.processing_max_concurrent_ai_analyses > settings.processing_concurrency * 3:
            config_validation["warnings"].append(
                "processing_max_concurrent_ai_analyses may be too high relative to processing_concurrency"
            )
    
    # Check memory configurations
    if hasattr(settings, 'processing_memory_threshold_mb') and hasattr(settings, 'processing_batch_size'):
        if settings.processing_batch_size > settings.processing_memory_threshold_mb // 25:
            config_validation["warnings"].append(
                "processing_batch_size may be too large for available memory threshold"
            )
    
    # Check content length configurations
    if hasattr(settings, 'gemini_max_content_length') and hasattr(settings, 'processing_max_summary_length'):
        if settings.processing_max_summary_length > settings.gemini_max_content_length:
            config_validation["warnings"].append(
                "processing_max_summary_length should not exceed gemini_max_content_length"
            )
    
    # Update status if warnings exist
    if config_validation["warnings"]:
        config_validation["status"] = "warning"
    
    # Add configuration summary
    config_validation["summary"] = {
        "timeout_seconds": getattr(settings, 'processing_timeout_seconds', 'not_set'),
        "concurrency": getattr(settings, 'processing_concurrency', 'not_set'),
        "batch_size": getattr(settings, 'processing_batch_size', 'not_set'),
        "memory_threshold_mb": getattr(settings, 'processing_memory_threshold_mb', 'not_set'),
        "max_summary_length": getattr(settings, 'processing_max_summary_length', 'not_set')
    }
    
    return config_validation


async def _check_resource_availability() -> Dict[str, Any]:
    """Check system resource availability."""
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        return {
            "memory": {
                "available_mb": round(memory.available / (1024 * 1024), 2),
                "used_percent": round(memory.percent, 2),
                "total_mb": round(memory.total / (1024 * 1024), 2)
            },
            "cpu": {
                "usage_percent": round(cpu_percent, 2),
                "core_count": psutil.cpu_count()
            },
            "disk": {
                "available_gb": round(psutil.disk_usage('/').free / (1024**3), 2)
            }
        }
    except ImportError:
        return {
            "status": "unavailable",
            "reason": "psutil not available"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/database/collections")
async def database_collections_health_check():
    """Database collections health check endpoint."""
    try:
        # Test all collections exist and are accessible
        client = get_client()
        database = client[get_settings().mongodb_db]
        
        collections_status = {}
        required_collections = [
            "queries", "content", "processed_content", 
            "query_sessions", "analytics", "migrations"
        ]
        
        existing_collections = await database.list_collection_names()
        
        for collection_name in required_collections:
            if collection_name in existing_collections:
                collection = database[collection_name]
                count = await collection.count_documents({})
                collections_status[collection_name] = {
                    "exists": True,
                    "document_count": count,
                    "accessible": True
                }
            else:
                collections_status[collection_name] = {
                    "exists": False,
                    "document_count": 0,
                    "accessible": False
                }
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow(),
            "collections": collections_status,
            "total_collections": len(existing_collections),
            "required_collections": len(required_collections)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database collections health check failed: {str(e)}"
        )


@router.get("/database/indexes")
async def database_indexes_health_check():
    """Database indexes health check endpoint."""
    try:
        from app.database.indexes import IndexManager
        
        index_manager = IndexManager()
        index_status = await index_manager.get_index_status()
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow(),
            "index_status": index_status
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database indexes health check failed: {str(e)}"
        )


@router.get("/database/operations")
async def database_operations_health_check():
    """Database operations health check endpoint."""
    try:
        # Test basic CRUD operations on each repository
        repositories_status = {}
        
        # Test Query Repository
        try:
            query_repo = await get_query_repository()
            health_check = await query_repo.health_check()
            repositories_status["queries"] = health_check
        except Exception as e:
            repositories_status["queries"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Test Content Repository
        try:
            content_repo = await get_content_repository()
            health_check = await content_repo.health_check()
            repositories_status["content"] = health_check
        except Exception as e:
            repositories_status["content"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Test Processed Repository
        try:
            processed_repo = await get_processed_repository()
            health_check = await processed_repo.health_check()
            repositories_status["processed_content"] = health_check
        except Exception as e:
            repositories_status["processed_content"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Test Analytics Repository
        try:
            analytics_repo = await get_analytics_repository()
            health_check = await analytics_repo.health_check()
            repositories_status["analytics"] = health_check
        except Exception as e:
            repositories_status["analytics"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Test Database Service
        try:
            db_service = await get_database_service()
            health_check = await db_service.get_system_health()
            repositories_status["database_service"] = health_check
        except Exception as e:
            repositories_status["database_service"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Determine overall status
        overall_status = "healthy"
        for repo_name, status in repositories_status.items():
            if status.get("status") != "healthy":
                overall_status = "degraded"
                break
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow(),
            "overall_status": overall_status,
            "repositories": repositories_status,
            "performance_metrics": {
                "total_repositories": len(repositories_status),
                "healthy_repositories": sum(1 for s in repositories_status.values() if s.get("status") == "healthy"),
                "unhealthy_repositories": sum(1 for s in repositories_status.values() if s.get("status") != "healthy")
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database operations health check failed: {str(e)}"
        )
