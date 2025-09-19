"""
Main scraper orchestrator that coordinates discovery and extraction.
"""
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from app.agents.base import BaseAgent
from app.agents.schemas import ParsedQuery
from app.scraper.discovery import SiteDiscoveryAgent
from app.scraper.extractor import ContentExtractorAgent
from app.scraper.schemas import ScrapedContent, DiscoveryResult, ScrapingError
from app.core.config import settings

logger = logging.getLogger(__name__)


class ScraperOrchestrator(BaseAgent):
    """Main orchestrator for web scraping workflows."""
    
    def __init__(
        self,
        name: str = "ScraperOrchestrator",
        description: str = "Coordinates web scraping discovery and extraction workflows",
        version: str = "1.0.0",
        gemini_client: Optional[Any] = None,
        settings: Optional[Any] = None,
        discovery_agent: Optional[SiteDiscoveryAgent] = None,
        extractor_agent: Optional[ContentExtractorAgent] = None
    ):
        super().__init__(name, description, version, gemini_client, settings)
        self.discovery_agent = discovery_agent or SiteDiscoveryAgent(gemini_client=gemini_client)
        self.extractor_agent = extractor_agent or ContentExtractorAgent(gemini_client=gemini_client)
        # Use global settings instead of optional parameter
        self._semaphore = asyncio.Semaphore(settings.scraper_concurrency)
    
    async def execute(self, parsed_query: ParsedQuery) -> List[ScrapedContent]:
        """Execute the complete scraping workflow for a parsed query."""
        start_time = time.time()
        
        try:
            logger.info(f"Starting scraping workflow for query: {parsed_query.base_result.query_text}")
            
            # Step 1: Discover relevant sites
            discovered_sites = await self._discover_sites(parsed_query)
            if not discovered_sites:
                logger.warning("No sites discovered for the query")
                return []
            
            logger.info(f"Discovered {len(discovered_sites)} sites for scraping")
            
            # Step 2: Extract content from discovered sites
            scraped_contents = await self._extract_content_from_sites(discovered_sites, parsed_query)
            
            # Step 3: Post-process and rank results
            final_results = await self._post_process_results(scraped_contents, parsed_query)
            
            processing_time = time.time() - start_time
            logger.info(f"Scraping workflow completed in {processing_time:.2f}s. "
                       f"Successfully scraped {len(final_results)} sites.")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Scraping workflow failed: {e}")
            raise
    
    async def _discover_sites(self, parsed_query: ParsedQuery) -> List[DiscoveryResult]:
        """Discover relevant sites for the query."""
        try:
            return await self.discovery_agent.execute(parsed_query)
        except Exception as e:
            logger.error(f"Site discovery failed: {e}")
            raise
    
    async def _extract_content_from_sites(self, discovered_sites: List[DiscoveryResult], parsed_query: ParsedQuery) -> List[ScrapedContent]:
        """Extract content from discovered sites with concurrency control."""
        scraped_contents = []
        failed_sites = []
        error_patterns = {}
        
        # Create tasks for concurrent extraction with proper semaphore control
        tasks = []
        for site in discovered_sites:
            task = asyncio.create_task(
                self._extract_single_site(site, parsed_query)
            )
            tasks.append(task)
        
        # Execute tasks without holding semaphore for the entire batch
        # Each individual task will acquire the semaphore as needed
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results with enhanced error handling
        for i, result in enumerate(results):
            site = discovered_sites[i]
            if isinstance(result, Exception):
                # Categorize and track error patterns
                error_type = type(result).__name__
                error_message = str(result)
                
                if error_type not in error_patterns:
                    error_patterns[error_type] = {
                        'count': 0,
                        'sites': [],
                        'examples': []
                    }
                
                error_patterns[error_type]['count'] += 1
                error_patterns[error_type]['sites'].append(str(site.url))
                if len(error_patterns[error_type]['examples']) < 3:  # Keep up to 3 examples
                    error_patterns[error_type]['examples'].append(error_message)
                
                # Log detailed error information
                logger.warning(
                    f"Failed to extract content from {site.url}: {error_type}: {error_message}",
                    extra={
                        'site_url': str(site.url),
                        'error_type': error_type,
                        'error_message': error_message,
                        'site_category': site.category,
                        'discovery_method': site.discovery_method.value
                    }
                )
                
                failed_sites.append({
                    'site': site,
                    'error_type': error_type,
                    'error_message': error_message,
                    'retry_count': 0  # Track retry attempts
                })
            else:
                scraped_contents.append(result)
        
        # Log comprehensive summary with error analysis
        logger.info(
            f"Content extraction completed: {len(scraped_contents)} successful, {len(failed_sites)} failed",
            extra={
                'success_count': len(scraped_contents),
                'failure_count': len(failed_sites),
                'error_patterns': error_patterns,
                'total_sites': len(discovered_sites),
                'success_rate': len(scraped_contents) / len(discovered_sites) if discovered_sites else 0
            }
        )
        
        # Log error pattern analysis for debugging
        if error_patterns:
            logger.info(f"Error pattern analysis: {error_patterns}")
        
        return scraped_contents
    
    async def _extract_single_site(self, site: DiscoveryResult, parsed_query: ParsedQuery) -> ScrapedContent:
        """Extract content from a single site with error handling."""
        # Acquire semaphore to limit concurrent extraction operations
        async with self._semaphore:
            try:
                # Add relevance score from discovery
                extraction_options = {
                    "relevance_score": site.relevance_score,
                    "query_category": parsed_query.base_result.category.value,
                    "query_text": parsed_query.base_result.query_text
                }
                
                # Extract content
                scraped_content = await self.extractor_agent.execute(
                    str(site.url),
                    extraction_options=extraction_options
                )
                
                # Update relevance score and add discovery metadata
                scraped_content.relevance_score = site.relevance_score
                scraped_content.content_quality_score = self._calculate_enhanced_quality_score(
                    scraped_content, site, parsed_query
                )
                
                return scraped_content
                
            except Exception as e:
                logger.error(f"Failed to extract content from {site.url}: {e}")
                raise
    
    def _calculate_enhanced_quality_score(self, scraped_content: ScrapedContent, site: DiscoveryResult, parsed_query: ParsedQuery) -> float:
        """Calculate enhanced quality score considering discovery and extraction factors."""
        base_score = scraped_content.content_quality_score or 0.5
        
        # Boost score based on discovery relevance
        discovery_boost = site.relevance_score * 0.2
        
        # Boost score based on content type relevance
        content_type_boost = 0.0
        if site.category == parsed_query.base_result.category.value:
            content_type_boost = 0.1
        
        # Boost score based on discovery method
        method_boost = 0.0
        if site.discovery_method.value == "llm_generated":
            method_boost = 0.05
        elif site.discovery_method.value == "rule_based":
            method_boost = 0.03
        
        # Boost score based on content length
        length_boost = 0.0
        if scraped_content.content_size_bytes > 5000:
            length_boost = 0.05
        elif scraped_content.content_size_bytes > 2000:
            length_boost = 0.03
        
        # Calculate final score
        final_score = base_score + discovery_boost + content_type_boost + method_boost + length_boost
        
        # Ensure score is within bounds
        return min(max(final_score, 0.0), 1.0)
    
    async def _post_process_results(self, scraped_contents: List[ScrapedContent], parsed_query: ParsedQuery) -> List[ScrapedContent]:
        """Post-process scraped content for final results."""
        if not scraped_contents:
            return []
        
        # Remove duplicates based on content similarity
        deduplicated = self._deduplicate_content(scraped_contents)
        
        # Rank by quality and relevance
        ranked = self._rank_content(deduplicated, parsed_query)
        
        # Apply final filtering
        filtered = self._filter_results(ranked, parsed_query)
        
        return filtered
    
    def _deduplicate_content(self, scraped_contents: List[ScrapedContent]) -> List[ScrapedContent]:
        """Remove duplicate content based on similarity."""
        if len(scraped_contents) <= 1:
            return scraped_contents
        
        # Simple deduplication based on domain and content similarity
        unique_contents = []
        seen_domains = set()
        
        for content in scraped_contents:
            domain = urlparse(str(content.url)).netloc.lower()
            
            # Check if we already have content from this domain
            if domain in seen_domains:
                # Keep the one with higher quality score
                existing = next(c for c in unique_contents if urlparse(str(c.url)).netloc.lower() == domain)
                if content.content_quality_score > existing.content_quality_score:
                    unique_contents.remove(existing)
                    unique_contents.append(content)
            else:
                seen_domains.add(domain)
                unique_contents.append(content)
        
        return unique_contents
    
    def _rank_content(self, scraped_contents: List[ScrapedContent], parsed_query: ParsedQuery) -> List[ScrapedContent]:
        """Rank content by quality and relevance."""
        # Calculate combined score for ranking
        for content in scraped_contents:
            combined_score = self._calculate_combined_score(content, parsed_query)
            # Store the combined score temporarily (we'll use it for ranking)
            content._combined_score = combined_score
        
        # Sort by combined score (descending)
        ranked = sorted(scraped_contents, key=lambda x: x._combined_score, reverse=True)
        
        # Clean up temporary attribute
        for content in ranked:
            delattr(content, '_combined_score')
        
        return ranked
    
    def _calculate_combined_score(self, content: ScrapedContent, parsed_query: ParsedQuery) -> float:
        """Calculate combined score for ranking."""
        # Base score from content quality
        quality_score = content.content_quality_score or 0.5
        
        # Relevance score
        relevance_score = content.relevance_score or 0.5
        
        # Content type relevance
        type_relevance = 0.5
        if content.content_type.value == "article":
            type_relevance = 0.8
        elif content.content_type.value == "documentation":
            type_relevance = 0.7
        
        # Query category match
        category_match = 0.5
        if content.content_type.value == parsed_query.base_result.category.value:
            category_match = 0.9
        
        # Calculate weighted average
        combined_score = (
            quality_score * 0.3 +
            relevance_score * 0.4 +
            type_relevance * 0.2 +
            category_match * 0.1
        )
        
        return combined_score
    
    def _filter_results(self, ranked_contents: List[ScrapedContent], parsed_query: ParsedQuery) -> List[ScrapedContent]:
        """Apply final filtering to results."""
        filtered = []
        
        for content in ranked_contents:
            # Skip content that's too short
            if content.content_size_bytes < 500:
                continue
            
            # Skip content with very low quality
            if content.content_quality_score and content.content_quality_score < 0.3:
                continue
            
            # Skip content with very low relevance
            if content.relevance_score and content.relevance_score < 0.2:
                continue
            
            filtered.append(content)
        
        return filtered
    
    async def scrape_single_url(self, url: str, extraction_options: Optional[Dict[str, Any]] = None) -> ScrapedContent:
        """Scrape content from a single URL."""
        try:
            logger.info(f"Scraping single URL: {url}")
            
            scraped_content = await self.extractor_agent.execute(url, extraction_options)
            
            logger.info(f"Single URL scraping completed for {url}")
            return scraped_content
            
        except Exception as e:
            logger.error(f"Single URL scraping failed for {url}: {e}")
            raise
    
    async def get_scraping_stats(self) -> Dict[str, Any]:
        """Get statistics about the scraping workflow."""
        return {
            "orchestrator_info": self.get_info(),
            "discovery_agent_info": self.discovery_agent.get_info(),
            "extractor_agent_info": self.extractor_agent.get_info(),
            "concurrency_limit": settings.scraper_concurrency,
            "rate_limiting_enabled": True,
            "robots_compliance_enabled": settings.scraper_respect_robots
        }
    
    async def _cleanup_resources(self) -> None:
        """Clean up resources used by this orchestrator."""
        # Clean up discovery and extractor agents
        await self.discovery_agent._cleanup_resources()
        await self.extractor_agent._cleanup_resources()
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information with orchestrator-specific details."""
        info = super().get_info()
        info.update({
            "scraper_type": "orchestrator",
            "workflow_stages": [
                "site_discovery",
                "content_extraction",
                "post_processing"
            ],
            "concurrency_control": True,
            "deduplication": True,
            "quality_ranking": True,
            "sub_agents": [
                self.discovery_agent.name,
                self.extractor_agent.name
            ]
        })
        return info
