import time
import asyncio
import weakref
import gc
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import deque
from app.agents.base import BaseAgent
from app.scraper.schemas import ScrapedContent
from app.agents.schemas import ParsedQuery
from app.processing.schemas import (
    ProcessedContent, ProcessingResult, ProcessingConfig, ProcessingError
)
from app.processing.cleaning import ContentCleaningAgent
from app.processing.analysis import AIAnalysisAgent
from app.processing.summarization import SummarizationAgent
from app.processing.extraction import StructuredDataExtractor
from app.processing.duplicates import DuplicateDetectionAgent
from app.core.config import get_settings
from app.core.gemini import GeminiClient
from app.utils.ids import generate_content_id


class ResourceMonitor:
    """Monitor resource usage and detect potential leaks."""
    
    def __init__(self):
        self.resource_snapshots = []
        self.max_snapshots = 10
        self.leak_threshold = 0.1  # 10% increase threshold
    
    def take_snapshot(self):
        """Take a snapshot of current resource usage."""
        import psutil
        process = psutil.Process()
        
        snapshot = {
            'timestamp': time.time(),
            'memory_mb': process.memory_info().rss / (1024 * 1024),
            'cpu_percent': process.cpu_percent(),
            'open_files': len(process.open_files()),
            'threads': process.num_threads(),
            'gc_stats': gc.get_stats()
        }
        
        self.resource_snapshots.append(snapshot)
        
        # Keep only recent snapshots
        if len(self.resource_snapshots) > self.max_snapshots:
            self.resource_snapshots.pop(0)
        
        return snapshot
    
    def detect_potential_leaks(self) -> List[str]:
        """Detect potential resource leaks based on snapshots."""
        if len(self.resource_snapshots) < 2:
            return []
        
        warnings = []
        latest = self.resource_snapshots[-1]
        previous = self.resource_snapshots[-2]
        
        # Check memory growth
        memory_growth = (latest['memory_mb'] - previous['memory_mb']) / previous['memory_mb']
        if memory_growth > self.leak_threshold:
            warnings.append(f"Potential memory leak: {memory_growth:.1%} increase")
        
        # Check file handle growth
        if latest['open_files'] > previous['open_files'] * 1.5:
            warnings.append("Potential file handle leak detected")
        
        # Check thread growth
        if latest['threads'] > previous['threads'] * 1.2:
            warnings.append("Potential thread leak detected")
        
        return warnings


class ProcessingOrchestrator(BaseAgent):
    """Main processing orchestrator that coordinates all processing agents with proper synchronization and resource management."""
    
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        super().__init__(name="ProcessingOrchestrator", description="Coordinates all processing agents in the pipeline")
        self.logger.info("ProcessingOrchestrator initialized")
        
        # Initialize processing agents
        self.cleaning_agent = ContentCleaningAgent()
        self.ai_analysis_agent = AIAnalysisAgent(gemini_client)
        self.summarization_agent = SummarizationAgent(gemini_client)
        self.extraction_agent = StructuredDataExtractor(gemini_client)
        self.duplicate_agent = DuplicateDetectionAgent(gemini_client)
        
        # Thread-safe collections for shared state
        self._processing_queue = asyncio.Queue()
        self._results_queue = asyncio.Queue()
        self._error_queue = asyncio.Queue()
        
        # Processing state tracking with improved management
        self._active_tasks = set()
        self._processing_lock = asyncio.Lock()
        self._cleanup_in_progress = False
        
        # Resource monitoring
        self._resource_monitor = ResourceMonitor()
        self._startup_snapshot = self._resource_monitor.take_snapshot()
        
        # Register cleanup on object destruction
        weakref.finalize(self, self._final_cleanup)
    
    async def process_scraped_content(
        self, 
        scraped_contents: List[ScrapedContent], 
        query: ParsedQuery,
        config: Optional[ProcessingConfig] = None
    ) -> ProcessingResult:
        """
        Process scraped content through the complete processing pipeline with proper synchronization and resource management.
        
        Args:
            scraped_contents: List of scraped content to process
            query: Original query context for processing
            config: Processing configuration (uses defaults if None)
            
        Returns:
            ProcessingResult with all processed content and analysis
        """
        start_time = time.time()
        
        if not scraped_contents:
            self.logger.warning("No content provided for processing")
            return self._create_empty_result(query, start_time)
        
        if config is None:
            config = ProcessingConfig.from_settings(get_settings())
        
        try:
            self.logger.info(f"Starting processing pipeline for {len(scraped_contents)} content pieces")
            
            # Take resource snapshot before processing
            self._resource_monitor.take_snapshot()
            
            # Step 1: Duplicate detection (if enabled)
            duplicate_analyses = []
            duplicate_analysis_map = {}
            if config.enable_duplicate_detection:
                self.logger.info("Starting duplicate detection")
                try:
                    duplicate_analyses = await self.duplicate_agent.detect_duplicates(scraped_contents, config)
                    # Build efficient mapping for O(1) lookup
                    duplicate_analysis_map = {self._generate_content_id(c): a for c, a in zip(scraped_contents, duplicate_analyses)}
                    self.logger.info("Duplicate detection completed")
                except Exception as e:
                    self.logger.error(f"Duplicate detection failed: {str(e)}")
                    # Continue processing without duplicates
                    duplicate_analyses = []
                    duplicate_analysis_map = {}
                    await self._cleanup_worker_resources("duplicate_detection")
            
            # Step 2: Process content using improved batch processing with synchronization
            processed_contents = []
            processing_errors = []
            
            # Use asyncio.Queue for better task management
            await self._setup_processing_queues(scraped_contents, query, config, duplicate_analysis_map)
            
            # Process content with proper synchronization
            try:
                batch_results = await self._process_content_with_synchronization(config)
                processed_contents.extend(batch_results["successful"])
                processing_errors.extend(batch_results["errors"])
            except Exception as e:
                self.logger.error(f"Content processing failed: {str(e)}")
                await self._cleanup_worker_resources("content_processing")
                raise
            
            # Step 3: Final ranking and filtering
            try:
                final_results = await self._finalize_processing(
                    processed_contents, query, config
                )
            except Exception as e:
                self.logger.error(f"Final processing failed: {str(e)}")
                await self._cleanup_worker_resources("final_processing")
                raise
            
            # Step 4: Create processing result
            total_time = time.time() - start_time
            processing_stats = {
                "total_items": len(scraped_contents),
                "successful": len(final_results),
                "failed": len(processing_errors),
                "duplicates_found": len([d for d in duplicate_analyses if d.duplicate_groups]),
                "processing_time": total_time
            }
            
            # Take final resource snapshot and check for leaks
            final_snapshot = self._resource_monitor.take_snapshot()
            leak_warnings = self._resource_monitor.detect_potential_leaks()
            if leak_warnings:
                self.logger.warning(f"Resource monitoring warnings: {', '.join(leak_warnings)}")
            
            result = ProcessingResult(
                processed_contents=final_results,
                total_processing_time=total_time,
                processing_stats=processing_stats,
                errors=processing_errors,
                query_context=query
            )
            
            # Clear resources after successful processing
            await self._cleanup_processing_resources()
            
            self.logger.info(f"Processing pipeline completed successfully in {total_time:.2f}s")
            return result
            
        except Exception as e:
            total_time = time.time() - start_time
            self.logger.error(f"Processing pipeline failed after {total_time:.2f}s: {str(e)}")
            
            # Ensure cleanup happens even on failure
            await self._cleanup_processing_resources()
            
            # Return error result
            return ProcessingResult(
                processed_contents=[],
                total_processing_time=total_time,
                processing_stats={"total_items": len(scraped_contents), "successful": 0, "failed": len(scraped_contents)},
                errors=[f"Processing failed: {str(e)}"],
                query_context=query
            )
    
    async def execute(self, scraped_contents: List[ScrapedContent], query: ParsedQuery, config: Optional[ProcessingConfig] = None) -> ProcessingResult:
        """Execute the agent's main functionality."""
        if config is None:
            from app.processing.schemas import ProcessingConfig
            config = ProcessingConfig.from_settings(self.settings)
        return await self.process_scraped_content(scraped_contents, query, config)
    
    async def _setup_processing_queues(
        self, 
        scraped_contents: List[ScrapedContent], 
        query: ParsedQuery, 
        config: ProcessingConfig,
        duplicate_analysis_map: Dict[str, Any]
    ):
        """Setup processing queues with content items."""
        for content in scraped_contents:
            await self._processing_queue.put({
                'content': content,
                'query': query,
                'config': config,
                'duplicate_analysis_map': duplicate_analysis_map
            })
    
    async def _process_content_with_synchronization(self, config: ProcessingConfig) -> Dict[str, List]:
        """Process content using asyncio.Queue with proper synchronization."""
        successful = []
        errors = []
        
        # Create worker tasks
        workers = []
        for _ in range(config.concurrency):
            worker = asyncio.create_task(self._content_worker(config))
            workers.append(worker)
            self._active_tasks.add(worker)
        
        # Wait for all content to be processed
        await self._processing_queue.join()
        
        # Cancel remaining workers
        for worker in workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*workers, return_exceptions=True)
        
        # Clear active tasks to ensure clean state for subsequent runs
        self._active_tasks.clear()
        
        # Collect results
        while not self._results_queue.empty():
            try:
                result = self._results_queue.get_nowait()
                if result:
                    successful.append(result)
            except asyncio.QueueEmpty:
                break
        
        # Collect errors
        while not self._error_queue.empty():
            try:
                error = self._error_queue.get_nowait()
                if error:
                    errors.append(error)
            except asyncio.QueueEmpty:
                break
        
        # Also collect errors from failed processing (None results)
        # These are critical failures that should propagate to the result level
        if len(errors) == 0 and len(successful) == 0:
            # All processing failed, add a generic error
            errors.append("All content processing failed")
        
        return {"successful": successful, "errors": errors}
    
    async def _content_worker(self, config: ProcessingConfig):
        """Worker task for processing individual content items."""
        while True:
            try:
                # Get content from queue with timeout
                item = await asyncio.wait_for(
                    self._processing_queue.get(), 
                    timeout=config.content_processing_timeout if hasattr(config, 'content_processing_timeout') else 30
                )
                
                content = item['content']
                query = item['query']
                config = item['config']
                duplicate_analysis_map = item['duplicate_analysis_map']
                
                try:
                    # Process content with timeout protection
                    result = await asyncio.wait_for(
                        self._process_single_content(content, query, config, duplicate_analysis_map),
                        timeout=config.content_processing_timeout if hasattr(config, 'content_processing_timeout') else 30
                    )
                    
                    if result:
                        await self._results_queue.put(result)
                    else:
                        await self._error_queue.put(f"Processing failed: Content {self._generate_content_id(content)} processing returned no result")
                        
                except asyncio.TimeoutError:
                    error_msg = f"Processing failed: Content {self._generate_content_id(content)} processing timed out"
                    await self._error_queue.put(error_msg)
                    self.logger.error(error_msg)
                except Exception as e:
                    error_msg = f"Processing failed: Content {self._generate_content_id(content)} processing failed: {str(e)}"
                    await self._error_queue.put(error_msg)
                    self.logger.error(error_msg)
                finally:
                    # Mark task as done
                    self._processing_queue.task_done()
                    
            except asyncio.TimeoutError:
                # No more content to process
                break
            except asyncio.CancelledError:
                # Worker was cancelled
                break
            except Exception as e:
                self.logger.error(f"Content worker error: {str(e)}")
                break
    
    async def _process_single_content(
        self, 
        content: ScrapedContent, 
        query: ParsedQuery, 
        config: ProcessingConfig,
        duplicate_analysis_map: Dict[str, Any]
    ) -> Optional[ProcessedContent]:
        """Process a single content piece through the pipeline."""
        content_start_time = time.time()
        content_id = self._generate_content_id(content)
        
        try:
            # Find duplicate analysis for this content using O(1) lookup
            duplicate_analysis = duplicate_analysis_map.get(content_id) if duplicate_analysis_map else None
            
            # Step 1: Content cleaning
            cleaned_result = None
            if config.enable_content_cleaning:
                cleaned_result = await self.cleaning_agent.clean_content(content)
                cleaned_text = cleaned_result["cleaned_content"]
            else:
                cleaned_text = content.content
                cleaned_result = {"cleaned_content": content.content, "enhanced_metadata": {}}
            
            # Step 2: AI analysis
            ai_insights = None
            if config.enable_ai_analysis:
                ai_insights = await self.ai_analysis_agent.analyze_content(
                    cleaned_text, query, content.title, content.url
                )
            # Note: ai_insights will be None when AI analysis is disabled
            
            # Step 3: Summarization
            summary = None
            if config.enable_summarization:
                summary = await self.summarization_agent.summarize_content(
                    cleaned_text, query, content.title, config.max_summary_length
                )
            
            # Step 4: Structured data extraction
            structured_data = None
            if config.enable_structured_extraction:
                structured_data = await self.extraction_agent.extract_structured_data(
                    cleaned_text, query, content.title, content.url
                )
            
            # Step 5: Create processed content
            processing_duration = time.time() - content_start_time
            
            # Calculate enhanced quality score
            enhanced_quality = self._calculate_enhanced_quality(
                content.content_quality_score or 0.0, cleaned_result, ai_insights, summary, structured_data
            )
            
            # Check quality threshold
            if enhanced_quality < config.min_content_quality_score:
                self.logger.info(f"Content {content_id} below quality threshold: {enhanced_quality}")
                return None
            
            processed_content = ProcessedContent(
                original_content=content,
                cleaned_content=cleaned_text,
                summary=summary or self._create_fallback_summary(query),
                structured_data=structured_data or self._create_fallback_structured_data(query),
                ai_insights=ai_insights or (self._create_fallback_ai_insights(query) if config.enable_ai_analysis else None),
                duplicate_analysis=duplicate_analysis,
                processing_timestamp=datetime.utcnow(),
                processing_duration=processing_duration,
                enhanced_quality_score=enhanced_quality,
                processing_errors=[]
            )
            
            return processed_content
            
        except Exception as e:
            processing_duration = time.time() - content_start_time
            self.logger.error(f"Failed to process content {content_id}: {str(e)}")
            
            # Push error to error queue for tracking
            try:
                await self._error_queue.put(f"Processing failed: Content {content_id} - {str(e)}")
            except Exception:
                pass  # Don't let error queue errors break processing
            
            # Return fallback processed content only for non-critical errors
            # For critical failures, return None to let errors propagate to result level
            if "AI Analysis failed" in str(e) or "timeout" in str(e).lower():
                return None  # Let error propagate to result level
            
            return self._create_fallback_processed_content(
                content, query, str(e), processing_duration
            )
    
    async def _finalize_processing(
        self, 
        processed_contents: List[ProcessedContent], 
        query: ParsedQuery, 
        config: ProcessingConfig
    ) -> List[ProcessedContent]:
        """Finalize processing with ranking and filtering."""
        if not processed_contents:
            return []
        
        # Filter by quality threshold
        filtered_contents = [
            content for content in processed_contents 
            if content.enhanced_quality_score >= config.min_content_quality_score
        ]
        
        # Sort by enhanced quality score (descending)
        sorted_contents = sorted(
            filtered_contents, 
            key=lambda x: x.enhanced_quality_score, 
            reverse=True
        )
        
        # Apply additional ranking based on query relevance
        ranked_contents = await self._rank_by_relevance(sorted_contents, query)
        
        self.logger.info(f"Finalized processing: {len(ranked_contents)} high-quality results")
        return ranked_contents
    
    async def _rank_by_relevance(
        self, 
        contents: List[ProcessedContent], 
        query: ParsedQuery
    ) -> List[ProcessedContent]:
        """Rank contents by relevance to the query."""
        # Create a copy of contents with ranking scores for sorting
        ranked_contents = []
        for content in contents:
            ranking_score = content.enhanced_quality_score
            if content.ai_insights:
                # Combine quality score with relevance score
                relevance_boost = content.ai_insights.relevance_score * 0.3
                ranking_score = min(1.0, ranking_score + relevance_boost)
            
            # Create a tuple for sorting: (content, ranking_score)
            ranked_contents.append((content, ranking_score))
        
        # Sort by ranking score and return original content objects
        ranked_contents.sort(key=lambda x: x[1], reverse=True)
        return [content for content, _ in ranked_contents]
    
    def _calculate_enhanced_quality(
        self, 
        original_score: float, 
        cleaned_result: Dict[str, Any], 
        ai_insights: Optional[Any], 
        summary: Optional[Any], 
        structured_data: Optional[Any]
    ) -> float:
        """Calculate enhanced quality score based on processing results."""
        base_score = original_score
        
        # Boost from cleaning
        if cleaned_result and "enhanced_metadata" in cleaned_result:
            enhanced_metadata = cleaned_result["enhanced_metadata"]
            if "enhanced_quality_score" in enhanced_metadata:
                cleaning_boost = enhanced_metadata["enhanced_quality_score"] * 0.2
                base_score += cleaning_boost
        
        # Boost from AI insights
        if ai_insights:
            ai_boost = (ai_insights.information_accuracy + ai_insights.source_reliability) * 0.15
            base_score += ai_boost
        
        # Boost from summary quality
        if summary:
            summary_boost = summary.confidence_score * 0.1
            base_score += summary_boost
        
        # Boost from structured data
        if structured_data and structured_data.confidence_scores:
            avg_confidence = sum(structured_data.confidence_scores.values()) / len(structured_data.confidence_scores)
            extraction_boost = avg_confidence * 0.1
            base_score += extraction_boost
        
        return min(1.0, max(0.0, base_score))
    
    def _create_fallback_summary(self, query: ParsedQuery):
        """Create fallback summary when summarization fails."""
        from app.processing.schemas import ContentSummary
        
        return ContentSummary(
            executive_summary=f"Content related to {query.base_result.query_text}",
            key_points=[f"Content covers {query.base_result.query_text} topics"],
            detailed_summary=f"This content appears to be related to {query.base_result.query_text}.",
            main_topics=[query.base_result.query_text],
            sentiment="neutral",
            confidence_score=0.3
        )
    
    def _create_fallback_structured_data(self, query: ParsedQuery):
        """Create fallback structured data when extraction fails."""
        from app.processing.schemas import StructuredData
        
        return StructuredData(
            entities=[],
            key_value_pairs={"extraction_failed": True},
            categories=[query.base_result.category.value],
            confidence_scores={"extraction_failed": 0.1},
            tables=[],
            measurements=[]
        )
    
    def _create_fallback_ai_insights(self, query: ParsedQuery):
        """Create fallback AI insights when analysis fails."""
        from app.processing.schemas import AIInsights
        
        return AIInsights(
            themes=[f"Content related to {query.base_result.query_text}"],
            relevance_score=0.5,
            quality_metrics={"readability": 0.5, "information_density": 0.5, "coherence": 0.5},
            recommendations=["Content analysis unavailable"],
            credibility_indicators={"analysis_failed": True},
            information_accuracy=0.5,
            source_reliability=0.5
        )
    
    def _create_fallback_processed_content(
        self, 
        content: ScrapedContent, 
        query: ParsedQuery, 
        error_message: str, 
        processing_duration: float
    ):
        """Create fallback processed content when processing fails."""
        return ProcessedContent(
            original_content=content,
            cleaned_content=content.content,
            summary=self._create_fallback_summary(query),
            structured_data=self._create_fallback_structured_data(query),
            ai_insights=self._create_fallback_ai_insights(query),
            duplicate_analysis=None,
            processing_timestamp=datetime.utcnow(),
            processing_duration=processing_duration,
            enhanced_quality_score=(content.content_quality_score or 0.0) * 0.5,  # Reduce quality due to failure
            processing_errors=[error_message]
        )
    
    def _create_empty_result(self, query: ParsedQuery, start_time: float) -> ProcessingResult:
        """Create empty result when no content is provided."""
        return ProcessingResult(
            processed_contents=[],
            total_processing_time=time.time() - start_time,
            processing_stats={"total_items": 0, "successful": 0, "failed": 0},
            errors=["No content provided for processing"],
            query_context=query
        )
    
    async def _cleanup_processing_resources(self):
        """Clear processing queues, cancel active tasks, and reset shared state with improved resource management."""
        if self._cleanup_in_progress:
            self.logger.debug("Cleanup already in progress, skipping")
            return
        
        self._cleanup_in_progress = True
        self.logger.info("Cleaning up processing resources")
        
        try:
            # Cancel all active tasks with comprehensive state handling
            await self._cancel_all_tasks()
            
            # Clear all queues with robust error handling
            await self._clear_queue_safely(self._processing_queue, "processing")
            await self._clear_queue_safely(self._results_queue, "results")
            await self._clear_queue_safely(self._error_queue, "error")
            
            # Reset shared state with simplified lock management
            await self._reset_shared_state()
            
            # Force garbage collection
            collected = gc.collect()
            if collected > 0:
                self.logger.debug(f"Garbage collection freed {collected} objects")
            
            # Take cleanup snapshot
            self._resource_monitor.take_snapshot()
            
            self.logger.info("Processing resources cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during resource cleanup: {str(e)}")
        finally:
            self._cleanup_in_progress = False
    
    async def _cancel_all_tasks(self):
        """Cancel all active tasks with comprehensive state handling."""
        if not self._active_tasks:
            return
        
        self.logger.info(f"Cancelling {len(self._active_tasks)} active tasks")
        
        # Group tasks by state for better handling
        running_tasks = []
        done_tasks = []
        cancelled_tasks = []
        
        for task in self._active_tasks:
            if task.done():
                if task.cancelled():
                    cancelled_tasks.append(task)
                else:
                    done_tasks.append(task)
            else:
                running_tasks.append(task)
        
        # Remove finished tasks immediately
        self._active_tasks.difference_update(done_tasks)
        self._active_tasks.difference_update(cancelled_tasks)
        
        # Cancel running tasks first
        if running_tasks:
            for task in running_tasks:
                task.cancel()
            
            # Wait for cancellation with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*running_tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("Some tasks did not cancel within timeout")
            except Exception as e:
                self.logger.warning(f"Error during task cancellation: {str(e)}")
        
        # Clear all remaining tasks
        self._active_tasks.clear()
    
    async def wait_for_cleanup(self, timeout: float = 2.0):
        """Wait for all active tasks to complete cleanup."""
        if not self._active_tasks:
            return
        
        start_time = time.time()
        while self._active_tasks and (time.time() - start_time) < timeout:
            # Remove finished tasks
            finished_tasks = {task for task in self._active_tasks if task.done()}
            self._active_tasks.difference_update(finished_tasks)
            
            if self._active_tasks:
                await asyncio.sleep(0.1)
        
        if self._active_tasks:
            self.logger.warning(f"Cleanup timeout reached, {len(self._active_tasks)} tasks still active")
            # Force cleanup
            self._active_tasks.clear()
    
    async def _clear_queue_safely(self, queue: asyncio.Queue, queue_name: str):
        """Safely clear a queue without calling task_done() - only workers should call task_done()."""
        try:
            # Get all items from the queue for logging
            items = []
            while True:
                try:
                    item = queue.get_nowait()
                    items.append(item)
                except asyncio.QueueEmpty:
                    break
            
            # Log drained items but don't call task_done() - only workers should do that
            self.logger.debug(f"Drained {len(items)} items from {queue_name} queue")
            
        except Exception as e:
            self.logger.error(f"Error clearing {queue_name} queue: {str(e)}")
    
    async def _reset_shared_state(self):
        """Reset shared state with simplified and robust lock management."""
        try:
            # Simplified lock management - just check if we can acquire it
            if hasattr(self, '_processing_lock'):
                try:
                    # Try to acquire the lock with a very short timeout
                    acquired = await asyncio.wait_for(
                        self._processing_lock.acquire(), 
                        timeout=0.01
                    )
                    if acquired:
                        # We acquired it, so release it immediately
                        self._processing_lock.release()
                        self.logger.debug("Processing lock reset during cleanup")
                    else:
                        # Lock is held by another task, this is normal during cleanup
                        self.logger.debug("Processing lock held by another task during cleanup")
                except asyncio.TimeoutError:
                    # Lock is held by another task, this is normal
                    self.logger.debug("Processing lock held by another task during cleanup")
                except Exception as e:
                    self.logger.error(f"Error managing processing lock during cleanup: {str(e)}")
            
            # Reset other shared state variables
            if hasattr(self, '_active_tasks'):
                self._active_tasks.clear()
            
        except Exception as e:
            self.logger.error(f"Error resetting shared state: {str(e)}")
    
    async def _cleanup_worker_resources(self, worker_name: str):
        """Clean up resources for a specific worker when it encounters errors."""
        try:
            self.logger.info(f"Cleaning up resources for {worker_name}")
            
            # Cancel any active tasks for this worker
            worker_tasks = [task for task in self._active_tasks 
                          if hasattr(task, '_worker_name') and task._worker_name == worker_name]
            
            for task in worker_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=1.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
                    except Exception as e:
                        self.logger.warning(f"Error during {worker_name} task cancellation: {str(e)}")
            
            # Force garbage collection for this worker
            gc.collect()
            
            self.logger.info(f"Resources cleaned up for {worker_name}")
            
        except Exception as e:
            self.logger.error(f"Error during {worker_name} resource cleanup: {str(e)}")
    
    def _final_cleanup(self):
        """Final cleanup when the orchestrator is being destroyed."""
        try:
            # This runs when the object is being garbage collected
            if hasattr(self, '_active_tasks') and self._active_tasks:
                self.logger.warning(f"ProcessingOrchestrator destroyed with {len(self._active_tasks)} active tasks")
            
            # Take final resource snapshot
            if hasattr(self, '_resource_monitor'):
                self._resource_monitor.take_snapshot()
                leak_warnings = self._resource_monitor.detect_potential_leaks()
                if leak_warnings:
                    self.logger.warning(f"Final resource monitoring warnings: {', '.join(leak_warnings)}")
                    
        except Exception as e:
            # Log but don't raise during finalization
            pass

    def _generate_content_id(self, content: ScrapedContent) -> str:
        """Generate a deterministic ID for content based on URL and title."""
        return generate_content_id(content.url, content.title)
