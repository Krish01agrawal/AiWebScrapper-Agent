"""
Shared dependency functions for FastAPI application.
"""
from typing import Annotated, Any, Optional
from functools import lru_cache
from fastapi import Depends, Request, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
import google.generativeai as genai

from app.core.database import get_database
from app.core.gemini import get_gemini_model, GeminiClient
from app.core.cache import InMemoryCache, get_cache
from app.core.auth import APIKeyManager, get_api_key_manager, APIKey
from app.agents.processor import QueryProcessor
from app.agents.parsers import NaturalLanguageParser
from app.agents.categorizer import DomainCategorizer
from app.scraper.session import get_scraper_session
from app.scraper.discovery import SiteDiscoveryAgent
from app.scraper.extractor import ContentExtractorAgent
from app.scraper.orchestrator import ScraperOrchestrator

# Processing dependencies
from app.processing.cleaning import ContentCleaningAgent
from app.processing.analysis import AIAnalysisAgent
from app.processing.summarization import SummarizationAgent
from app.processing.extraction import StructuredDataExtractor
from app.processing.duplicates import DuplicateDetectionAgent
from app.processing.orchestrator import ProcessingOrchestrator

# Database dependencies
from app.database.repositories.queries import QueryRepository
from app.database.repositories.content import ScrapedContentRepository
from app.database.repositories.processed import ProcessedContentRepository
from app.database.repositories.analytics import AnalyticsRepository
from app.database.service import DatabaseService

# Services dependencies
from app.services.orchestration import WorkflowOrchestrator


@lru_cache(maxsize=1)
def get_cached_gemini_client() -> GeminiClient:
    """Get cached GeminiClient instance to avoid creating new clients per request."""
    return GeminiClient()


# Database dependency
def get_db() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance."""
    try:
        return get_database()
    except RuntimeError:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database is not initialized")


# Gemini client dependency
async def get_gemini() -> genai.GenerativeModel | None:
    """Get Gemini AI model instance."""
    model = get_gemini_model()
    if not model:
        return None
    return model


# GeminiClient dependency
async def get_gemini_client() -> GeminiClient:
    """Get cached GeminiClient instance."""
    client = get_cached_gemini_client()
    if not client.is_available():
        from fastapi import HTTPException
        raise HTTPException(503, "Gemini client not available. Check API key configuration.")
    return client


# Agent dependencies
async def get_query_processor() -> QueryProcessor:
    """Get QueryProcessor instance."""
    try:
        gemini_client = await get_gemini_client()
        return QueryProcessor(gemini_client)
    except RuntimeError as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503, 
            detail=f"Query processor unavailable: {str(e)}"
        )


async def get_nl_parser() -> NaturalLanguageParser:
    """Get NaturalLanguageParser instance."""
    try:
        gemini_client = await get_gemini_client()
        return NaturalLanguageParser(gemini_client)
    except RuntimeError as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503, 
            detail=f"Natural language parser unavailable: {str(e)}"
        )


async def get_categorizer() -> DomainCategorizer:
    """Get DomainCategorizer instance."""
    try:
        gemini_client = await get_gemini_client()
        return DomainCategorizer(gemini_client)
    except RuntimeError as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503, 
            detail=f"Domain categorizer unavailable: {str(e)}"
        )


# Scraper dependencies
async def get_scraper_session_dep():
    """Get scraper session dependency."""
    try:
        return get_scraper_session()
    except RuntimeError as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Scraper session unavailable: {str(e)}"
        )


async def get_site_discovery_agent() -> SiteDiscoveryAgent:
    """Get SiteDiscoveryAgent instance."""
    try:
        gemini_client = await get_gemini_client()
        return SiteDiscoveryAgent(gemini_client=gemini_client)
    except RuntimeError as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Site discovery agent unavailable: {str(e)}"
        )


async def get_content_extractor_agent() -> ContentExtractorAgent:
    """Get ContentExtractorAgent instance."""
    try:
        gemini_client = await get_gemini_client()
        return ContentExtractorAgent(gemini_client=gemini_client)
    except RuntimeError as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Content extractor agent unavailable: {str(e)}"
        )


async def get_scraper_orchestrator() -> ScraperOrchestrator:
    """Get ScraperOrchestrator instance."""
    try:
        gemini_client = await get_gemini_client()
        return ScraperOrchestrator(gemini_client=gemini_client)
    except RuntimeError as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Scraper orchestrator unavailable: {str(e)}"
        )


# Processing dependencies
async def get_content_cleaning_agent() -> ContentCleaningAgent:
    """Get ContentCleaningAgent instance."""
    try:
        return ContentCleaningAgent()
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Content cleaning agent unavailable: {str(e)}"
        )


async def get_ai_analysis_agent() -> AIAnalysisAgent:
    """Get AIAnalysisAgent instance."""
    try:
        gemini_client = await get_gemini_client()
        return AIAnalysisAgent(gemini_client=gemini_client)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"AI analysis agent unavailable: {str(e)}"
        )


async def get_summarization_agent() -> SummarizationAgent:
    """Get SummarizationAgent instance."""
    try:
        gemini_client = await get_gemini_client()
        return SummarizationAgent(gemini_client=gemini_client)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Summarization agent unavailable: {str(e)}"
        )


async def get_structured_data_extractor() -> StructuredDataExtractor:
    """Get StructuredDataExtractor instance."""
    try:
        gemini_client = await get_gemini_client()
        return StructuredDataExtractor(gemini_client=gemini_client)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Structured data extractor unavailable: {str(e)}"
        )


async def get_duplicate_detection_agent() -> DuplicateDetectionAgent:
    """Get DuplicateDetectionAgent instance."""
    try:
        gemini_client = await get_gemini_client()
        return DuplicateDetectionAgent(gemini_client=gemini_client)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Duplicate detection agent unavailable: {str(e)}"
        )


async def get_processing_orchestrator() -> ProcessingOrchestrator:
    """Get ProcessingOrchestrator instance."""
    try:
        gemini_client = await get_gemini_client()
        return ProcessingOrchestrator(gemini_client=gemini_client)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Processing orchestrator unavailable: {str(e)}"
        )


# Database dependencies
async def get_query_repository() -> QueryRepository:
    """Get QueryRepository instance."""
    try:
        database = get_db()
        return QueryRepository(database)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Query repository unavailable: {str(e)}"
        )


async def get_content_repository() -> ScrapedContentRepository:
    """Get ScrapedContentRepository instance."""
    try:
        database = get_db()
        return ScrapedContentRepository(database)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Content repository unavailable: {str(e)}"
        )


async def get_processed_repository() -> ProcessedContentRepository:
    """Get ProcessedContentRepository instance."""
    try:
        database = get_db()
        return ProcessedContentRepository(database)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Processed repository unavailable: {str(e)}"
        )


async def get_analytics_repository() -> AnalyticsRepository:
    """Get AnalyticsRepository instance."""
    try:
        database = get_db()
        return AnalyticsRepository(database)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Analytics repository unavailable: {str(e)}"
        )


async def get_database_service() -> DatabaseService:
    """Get DatabaseService instance."""
    try:
        database = get_db()
        return DatabaseService(database)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Database service unavailable: {str(e)}"
        )


# Type aliases for dependency injection
DatabaseDep = Annotated[AsyncIOMotorDatabase, Depends(get_db)]
GeminiDep = Annotated[genai.GenerativeModel | None, Depends(get_gemini)]
GeminiClientDep = Annotated[GeminiClient, Depends(get_gemini_client)]
QueryProcessorDep = Annotated[QueryProcessor, Depends(get_query_processor)]
NLParserDep = Annotated[NaturalLanguageParser, Depends(get_nl_parser)]
CategorizerDep = Annotated[DomainCategorizer, Depends(get_categorizer)]

# Scraper type aliases
ScraperSessionDep = Annotated[Any, Depends(get_scraper_session_dep)]
SiteDiscoveryDep = Annotated[SiteDiscoveryAgent, Depends(get_site_discovery_agent)]
ContentExtractorDep = Annotated[ContentExtractorAgent, Depends(get_content_extractor_agent)]
ScraperOrchestratorDep = Annotated[ScraperOrchestrator, Depends(get_scraper_orchestrator)]

# Processing type aliases
ContentCleaningDep = Annotated[ContentCleaningAgent, Depends(get_content_cleaning_agent)]
AIAnalysisDep = Annotated[AIAnalysisAgent, Depends(get_ai_analysis_agent)]
SummarizationDep = Annotated[SummarizationAgent, Depends(get_summarization_agent)]
StructuredExtractionDep = Annotated[StructuredDataExtractor, Depends(get_structured_data_extractor)]
DuplicateDetectionDep = Annotated[DuplicateDetectionAgent, Depends(get_duplicate_detection_agent)]
ProcessingOrchestratorDep = Annotated[ProcessingOrchestrator, Depends(get_processing_orchestrator)]

# Database type aliases
QueryRepositoryDep = Annotated[QueryRepository, Depends(get_query_repository)]
ContentRepositoryDep = Annotated[ScrapedContentRepository, Depends(get_content_repository)]
ProcessedRepositoryDep = Annotated[ProcessedContentRepository, Depends(get_processed_repository)]
AnalyticsRepositoryDep = Annotated[AnalyticsRepository, Depends(get_analytics_repository)]
DatabaseServiceDep = Annotated[DatabaseService, Depends(get_database_service)]


async def get_workflow_orchestrator() -> WorkflowOrchestrator:
    """Get WorkflowOrchestrator instance with all required dependencies."""
    try:
        query_processor = await get_query_processor()
        scraper_orchestrator = await get_scraper_orchestrator()
        processing_orchestrator = await get_processing_orchestrator()
        database_service = await get_database_service()
        
        return WorkflowOrchestrator(
            query_processor=query_processor,
            scraper_orchestrator=scraper_orchestrator,
            processing_orchestrator=processing_orchestrator,
            database_service=database_service
        )
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Workflow orchestrator unavailable: {str(e)}"
        )


# Services type aliases
WorkflowOrchestratorDep = Annotated[WorkflowOrchestrator, Depends(get_workflow_orchestrator)]


# Cache dependencies
def get_cache_dep(request: Request) -> Optional[InMemoryCache]:
    """Get cache instance from application state."""
    return getattr(request.app.state, "cache", None)


def get_api_key_manager_dep(request: Request) -> Optional[APIKeyManager]:
    """Get API key manager from application state."""
    return getattr(request.app.state, "api_key_manager", None)


async def get_current_api_key(request: Request) -> Optional[APIKey]:
    """Get current authenticated API key from request state."""
    return getattr(request.state, "api_key", None)


def require_permission(permission: str):
    """Create dependency that requires specific permission."""
    async def check_permission(api_key: Optional[APIKey] = Depends(get_current_api_key)):
        if not api_key:
            raise HTTPException(status_code=401, detail="Authentication required")
        if not api_key.check_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission}' required"
            )
        return api_key
    return check_permission


async def check_rate_limit(request: Request, api_key: Optional[APIKey] = Depends(get_current_api_key)):
    """Check rate limit for current request."""
    manager = getattr(request.app.state, "api_key_manager", None)
    if not manager:
        return
    
    if api_key:
        if not manager.check_rate_limit(api_key.key_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        manager.record_request(api_key.key_id)
    else:
        # Use IP-based rate limiting for unauthenticated requests
        client_ip = request.client.host if request.client else "unknown"
        # This would need to be implemented in the rate limiting middleware
        pass


# Type aliases for new dependencies
CacheDep = Annotated[Optional[InMemoryCache], Depends(get_cache_dep)]
APIKeyManagerDep = Annotated[Optional[APIKeyManager], Depends(get_api_key_manager_dep)]
CurrentAPIKeyDep = Annotated[Optional[APIKey], Depends(get_current_api_key)]


# Export all dependencies
__all__ = [
    # Database dependencies
    "DatabaseDep", "GeminiDep", "GeminiClientDep",
    # Agent dependencies
    "QueryProcessorDep", "NLParserDep", "CategorizerDep",
    # Scraper dependencies
    "ScraperSessionDep", "SiteDiscoveryDep", "ContentExtractorDep", "ScraperOrchestratorDep",
    # Processing dependencies
    "ContentCleaningDep", "AIAnalysisDep", "SummarizationDep", "StructuredExtractionDep",
    "DuplicateDetectionDep", "ProcessingOrchestratorDep",
    # Database repository dependencies
    "QueryRepositoryDep", "ContentRepositoryDep", "ProcessedRepositoryDep",
    "AnalyticsRepositoryDep", "DatabaseServiceDep",
    # Service dependencies
    "WorkflowOrchestratorDep",
    # New dependencies
    "CacheDep", "APIKeyManagerDep", "CurrentAPIKeyDep",
    # Dependency functions
    "get_cache_dep", "get_api_key_manager_dep", "get_current_api_key",
    "require_permission", "check_rate_limit"
]
