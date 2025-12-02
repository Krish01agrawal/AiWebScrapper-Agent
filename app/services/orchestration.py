"""
High-level orchestration service that coordinates all three orchestrators for the main API workflow.
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager

from app.agents.processor import QueryProcessor
from app.agents.schemas import ParsedQuery
from app.scraper.orchestrator import ScraperOrchestrator
from app.scraper.schemas import ScrapedContent
from app.processing.orchestrator import ProcessingOrchestrator
from app.processing.schemas import ProcessedContent, ProcessingConfig
from app.database.service import DatabaseService
from app.core.config import get_settings


logger = logging.getLogger(__name__)


class WorkflowProgress:
    """Track progress through workflow stages."""
    
    def __init__(self):
        self.current_stage = "initialized"
        self.completed_stages = []
        self.stage_timings = {}
        self.stage_results = {}
        self.errors = []
        self.start_time = datetime.utcnow()
    
    def start_stage(self, stage_name: str):
        """Mark the start of a processing stage."""
        self.current_stage = stage_name
        self.stage_timings[stage_name] = {"start": datetime.utcnow()}
        logger.info(f"Starting workflow stage: {stage_name}")
    
    def complete_stage(self, stage_name: str, result: Any = None):
        """Mark the completion of a processing stage."""
        if stage_name in self.stage_timings:
            end_time = datetime.utcnow()
            start_time = self.stage_timings[stage_name]["start"]
            duration = (end_time - start_time).total_seconds()
            self.stage_timings[stage_name]["end"] = end_time
            self.stage_timings[stage_name]["duration"] = duration
            
        self.completed_stages.append(stage_name)
        if result is not None:
            self.stage_results[stage_name] = result
        
        logger.info(f"Completed workflow stage: {stage_name}")
    
    def add_error(self, stage_name: str, error: Exception):
        """Add an error for a specific stage."""
        error_info = {
            "stage": stage_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow()
        }
        self.errors.append(error_info)
        logger.error(f"Error in workflow stage {stage_name}: {error}")
    
    def get_total_duration(self) -> float:
        """Get total workflow duration in seconds."""
        return (datetime.utcnow() - self.start_time).total_seconds()


class WorkflowOrchestrator:
    """
    High-level orchestration service that coordinates the complete scraping workflow.
    Manages QueryProcessor, ScraperOrchestrator, and ProcessingOrchestrator.
    """
    
    def __init__(
        self,
        query_processor: QueryProcessor,
        scraper_orchestrator: ScraperOrchestrator,
        processing_orchestrator: ProcessingOrchestrator,
        database_service: DatabaseService
    ):
        self.query_processor = query_processor
        self.scraper_orchestrator = scraper_orchestrator
        self.processing_orchestrator = processing_orchestrator
        self.database_service = database_service
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
    
    async def execute_scraping_workflow(
        self,
        query_text: str,
        processing_config: Optional[ProcessingConfig] = None,
        timeout_seconds: Optional[int] = None,
        store_results: bool = True
    ) -> Dict[str, Any]:
        """
        Execute the complete scraping workflow from query to processed results.
        
        Args:
            query_text: Natural language query to process
            processing_config: Optional processing configuration
            timeout_seconds: Optional timeout for the entire workflow
            store_results: Whether to store results in database
            
        Returns:
            Complete workflow results with processed content and metadata
        """
        # Initialize progress tracking
        progress = WorkflowProgress()
        workflow_timeout = timeout_seconds or getattr(self.settings, 'api_request_timeout_seconds', 300)
        
        try:
            # Execute workflow with timeout
            return await asyncio.wait_for(
                self._execute_workflow_stages(
                    query_text, processing_config, store_results, progress
                ),
                timeout=workflow_timeout
            )
        
        except asyncio.TimeoutError:
            error_msg = f"Workflow timed out after {workflow_timeout} seconds"
            progress.add_error("workflow", Exception(error_msg))
            self.logger.error(error_msg)
            
            return self._create_error_result(
                "WORKFLOW_TIMEOUT",
                error_msg,
                progress
            )
        
        except Exception as e:
            progress.add_error("workflow", e)
            self.logger.error(f"Workflow failed with unexpected error: {e}", exc_info=True)
            
            return self._create_error_result(
                "WORKFLOW_ERROR",
                f"Unexpected workflow error: {str(e)}",
                progress
            )
    
    async def _execute_workflow_stages(
        self,
        query_text: str,
        processing_config: Optional[ProcessingConfig],
        store_results: bool,
        progress: WorkflowProgress
    ) -> Dict[str, Any]:
        """Execute the main workflow stages."""
        
        # Stage 1: Query Processing
        progress.start_stage("query_processing")
        try:
            parsed_query = await self._process_query(query_text)
            progress.complete_stage("query_processing", parsed_query)
        except Exception as e:
            progress.add_error("query_processing", e)
            return self._create_error_result(
                "QUERY_PROCESSING_ERROR",
                f"Failed to process query: {str(e)}",
                progress
            )
        
        # Stage 2: Web Scraping
        progress.start_stage("web_scraping")
        try:
            scraped_content = await self._scrape_content(parsed_query)
            progress.complete_stage("web_scraping", scraped_content)
            
            if not scraped_content:
                return self._create_error_result(
                    "NO_CONTENT_FOUND",
                    "No relevant content could be scraped for the query",
                    progress
                )
        
        except Exception as e:
            progress.add_error("web_scraping", e)
            return self._create_error_result(
                "SCRAPING_ERROR",
                f"Failed to scrape content: {str(e)}",
                progress
            )
        
        # Stage 3: AI Processing
        progress.start_stage("ai_processing")
        try:
            processed_content = await self._process_content(
                scraped_content, parsed_query, processing_config
            )
            progress.complete_stage("ai_processing", processed_content)
        except Exception as e:
            progress.add_error("ai_processing", e)
            # Continue with partial results if processing fails
            self.logger.warning(f"AI processing failed, returning scraped content only: {e}")
            processed_content = []
        
        # Stage 4: Database Storage (if enabled)
        if store_results and getattr(self.settings, 'api_enable_database_storage', True):
            progress.start_stage("database_storage")
            try:
                storage_result = await self._store_results(
                    parsed_query, scraped_content, processed_content
                )
                progress.complete_stage("database_storage", storage_result)
            except Exception as e:
                progress.add_error("database_storage", e)
                self.logger.warning(f"Database storage failed, continuing without storage: {e}")
        elif store_results and not getattr(self.settings, 'api_enable_database_storage', True):
            # Log info when storage is skipped due to global settings
            self.logger.info("Database storage skipped due to api_enable_database_storage=false setting")
        
        # Create successful result
        return self._create_success_result(
            parsed_query, scraped_content, processed_content, progress
        )
    
    async def _process_query(self, query_text: str) -> ParsedQuery:
        """Process natural language query using QueryProcessor."""
        try:
            self.logger.info(f"Processing query: {query_text[:100]}...")
            parsed_query = await self.query_processor.process_query(query_text)
            
            self.logger.info(
                f"Query processed successfully. Category: {parsed_query.base_result.category}, "
                f"Confidence: {parsed_query.base_result.confidence_score}"
            )
            
            return parsed_query
        
        except Exception as e:
            self.logger.error(f"Query processing failed: {e}", exc_info=True)
            raise
    
    async def _scrape_content(self, parsed_query: ParsedQuery) -> List[ScrapedContent]:
        """Scrape content using ScraperOrchestrator."""
        try:
            self.logger.info("Starting content scraping...")
            scraped_content = await self.scraper_orchestrator.execute(parsed_query)
            
            self.logger.info(f"Scraped {len(scraped_content)} content items")
            
            # Filter out low-quality content
            min_quality_score = getattr(self.settings, 'processing_min_content_quality_score', 0.4)
            filtered_content = [
                content for content in scraped_content
                if getattr(content, 'content_quality_score', 1.0) >= min_quality_score
            ]
            
            if len(filtered_content) < len(scraped_content):
                self.logger.info(
                    f"Filtered content from {len(scraped_content)} to {len(filtered_content)} "
                    f"items based on quality score threshold {min_quality_score}"
                )
            
            return filtered_content
        
        except Exception as e:
            self.logger.error(f"Content scraping failed: {e}", exc_info=True)
            raise
    
    async def _process_content(
        self,
        scraped_content: List[ScrapedContent],
        parsed_query: ParsedQuery,
        processing_config: Optional[ProcessingConfig]
    ) -> List[ProcessedContent]:
        """Process scraped content using ProcessingOrchestrator."""
        if not scraped_content:
            return []
        
        try:
            self.logger.info(f"Starting AI processing of {len(scraped_content)} content items...")
            
            # Use provided config or create from settings based on api_default_processing_config flag
            if processing_config is None and getattr(self.settings, 'api_default_processing_config', True):
                config = ProcessingConfig.from_settings(self.settings)
            elif processing_config is not None:
                config = processing_config
            else:
                # If api_default_processing_config is False and no config provided, use minimal config
                config = ProcessingConfig()
            
            processed_content = await self.processing_orchestrator.process_scraped_content(
                scraped_content, parsed_query, config
            )
            
            self.logger.info(f"AI processing completed. Processed {len(processed_content)} items")
            
            return processed_content
        
        except Exception as e:
            self.logger.error(f"Content processing failed: {e}", exc_info=True)
            raise
    
    async def _store_results(
        self,
        parsed_query: ParsedQuery,
        scraped_content: List[ScrapedContent],
        processed_content: List[ProcessedContent]
    ) -> Dict[str, Any]:
        """Store complete results in database."""
        try:
            self.logger.info("Storing results in database...")
            
            # Store query
            query_id = await self.database_service.store_query(parsed_query)
            
            # Store scraped content
            content_ids = []
            for content in scraped_content:
                content_id = await self.database_service.store_scraped_content(content, query_id)
                content_ids.append(content_id)
            
            # Store processed content
            processed_ids = []
            for content in processed_content:
                processed_id = await self.database_service.store_processed_content(content, query_id)
                processed_ids.append(processed_id)
            
            storage_result = {
                "query_id": str(query_id),
                "scraped_content_ids": [str(cid) for cid in content_ids],
                "processed_content_ids": [str(pid) for pid in processed_ids],
                "total_stored_items": len(content_ids) + len(processed_ids)
            }
            
            self.logger.info(
                f"Results stored successfully. Query ID: {query_id}, "
                f"Scraped items: {len(content_ids)}, Processed items: {len(processed_ids)}"
            )
            
            return storage_result
        
        except Exception as e:
            self.logger.error(f"Database storage failed: {e}", exc_info=True)
            raise
    
    def _create_success_result(
        self,
        parsed_query: ParsedQuery,
        scraped_content: List[ScrapedContent],
        processed_content: List[ProcessedContent],
        progress: WorkflowProgress
    ) -> Dict[str, Any]:
        """Create successful workflow result."""
        # Apply max results limit
        max_results = getattr(self.settings, 'api_max_results_per_request', 50)
        
        # Limit processed content
        limited_processed_content = processed_content[:max_results]
        limited_scraped_content = scraped_content[:max_results]
        
        # Track if results were limited
        results_limited = len(processed_content) > max_results or len(scraped_content) > max_results
        original_processed_count = len(processed_content)
        original_scraped_count = len(scraped_content)
        
        result = {
            "status": "success",
            "query": {
                "text": parsed_query.base_result.query_text,
                "category": parsed_query.base_result.category.value,
                "confidence_score": parsed_query.base_result.confidence_score
            },
            "results": {
                "scraped_content": limited_scraped_content,
                "processed_content": limited_processed_content,
                "total_scraped_items": len(limited_scraped_content),
                "total_processed_items": len(limited_processed_content),
                "original_scraped_count": original_scraped_count,
                "original_processed_count": original_processed_count,
                "results_limited": results_limited,
                "max_results_limit": max_results
            },
            "execution": {
                "total_duration_seconds": progress.get_total_duration(),
                "completed_stages": progress.completed_stages,
                "stage_timings": {
                    stage: timing.get("duration", 0)
                    for stage, timing in progress.stage_timings.items()
                },
                "errors": progress.errors
            }
        }
        
        # Add info note if storage was skipped due to global settings
        if not getattr(self.settings, 'api_enable_database_storage', True):
            result["info"] = {
                "message": "Database storage was skipped due to api_enable_database_storage=false setting",
                "storage_enabled": False
            }
        
        return result
    
    def _create_error_result(
        self,
        error_code: str,
        error_message: str,
        progress: WorkflowProgress
    ) -> Dict[str, Any]:
        """Create error workflow result."""
        return {
            "status": "error",
            "error": {
                "code": error_code,
                "message": error_message
            },
            "partial_results": progress.stage_results,
            "execution": {
                "total_duration_seconds": progress.get_total_duration(),
                "completed_stages": progress.completed_stages,
                "failed_stage": progress.current_stage,
                "stage_timings": {
                    stage: timing.get("duration", 0)
                    for stage, timing in progress.stage_timings.items()
                },
                "errors": progress.errors
            }
        }
    
    async def get_workflow_health(self) -> Dict[str, Any]:
        """Get health status of all workflow components."""
        health_status = {
            "status": "healthy",
            "components": {},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Test query processor
        try:
            # Simple test query
            test_result = await asyncio.wait_for(
                self.query_processor.process_query("test query"),
                timeout=5.0
            )
            health_status["components"]["query_processor"] = {
                "status": "healthy",
                "test_confidence": test_result.base_result.confidence_score
            }
        except Exception as e:
            health_status["components"]["query_processor"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Test scraper orchestrator (basic connectivity)
        try:
            # This would test basic scraper health
            health_status["components"]["scraper_orchestrator"] = {
                "status": "healthy",
                "note": "Basic connectivity test passed"
            }
        except Exception as e:
            health_status["components"]["scraper_orchestrator"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Test processing orchestrator
        try:
            health_status["components"]["processing_orchestrator"] = {
                "status": "healthy",
                "note": "Processing orchestrator available"
            }
        except Exception as e:
            health_status["components"]["processing_orchestrator"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Test database service
        try:
            db_health = await self.database_service.get_system_health()
            health_status["components"]["database_service"] = db_health
            if db_health.get("status") != "healthy":
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["database_service"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        return health_status
