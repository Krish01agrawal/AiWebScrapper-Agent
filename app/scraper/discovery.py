"""
Intelligent site discovery agent using Gemini LLM and rule-based strategies.
"""
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import json

from app.core.config import settings
from app.scraper.base import BaseScraperAgent
from app.scraper.schemas import DiscoveryResult, DiscoveryMethod, SiteDiscoveryConfig
from app.agents.schemas import ParsedQuery, QueryCategory

logger = logging.getLogger(__name__)


class SiteDiscoveryAgent(BaseScraperAgent):
    """Agent for intelligent site discovery using LLM and rule-based strategies."""
    
    def __init__(
        self,
        name: str = "SiteDiscoveryAgent",
        description: str = "Discovers relevant websites for queries using AI and rules",
        version: str = "1.0.0",
        gemini_client: Optional[Any] = None,
        settings: Optional[Any] = None,
        config: Optional[SiteDiscoveryConfig] = None
    ):
        super().__init__(name, description, version, gemini_client, settings)
        self.config = config or SiteDiscoveryConfig()
        self._domain_patterns = self._initialize_domain_patterns()
    
    def _initialize_domain_patterns(self) -> Dict[str, List[str]]:
        """Initialize domain patterns for different query categories."""
        # Scraper-friendly test sites that allow scraping
        scraper_friendly_sites = [
            "httpbin.org",  # Known scraper-friendly test site
            "example.com",  # RFC example domain
            "httpstat.us",  # HTTP status code testing
            "jsonplaceholder.typicode.com",  # JSON API for testing
        ]
        
        default_patterns = {
            "ai_tools": [
                "producthunt.com", "github.com", "alternativeto.net", "saashub.com",
                "g2.com", "capterra.com", "techcrunch.com", "venturebeat.com"
            ] + scraper_friendly_sites,
            "mutual_funds": [
                "morningstar.com", "vanguard.com", "investor.vanguard.com", "fidelity.com", 
                "schwab.com", "tdameritrade.com", "etrade.com", "yahoo.com/finance", 
                "marketwatch.com", "investopedia.com", "nerdwallet.com", "bankrate.com",
                "thebalance.com", "forbes.com/investing", "bloomberg.com", "reuters.com/finance"
            ],
            "general": [
                "wikipedia.org", "reddit.com", "stackoverflow.com", "quora.com",
                "medium.com", "dev.to", "hashnode.dev", "substack.com"
            ] + scraper_friendly_sites,
            "documentation": scraper_friendly_sites + [
                "docs.python.org", "developer.mozilla.org", "www.w3.org"
            ],
            "tutorial": scraper_friendly_sites + [
                "www.w3schools.com", "www.tutorialspoint.com"
            ]
        }
        
        # Merge with custom patterns if provided
        if self.config.domain_patterns:
            for category, patterns in self.config.domain_patterns.items():
                if category in default_patterns:
                    default_patterns[category].extend(patterns)
                else:
                    default_patterns[category] = patterns
        
        return default_patterns
    
    async def execute(self, parsed_query: ParsedQuery) -> List[DiscoveryResult]:
        """Execute site discovery for a parsed query."""
        start_time = time.time()
        
        try:
            logger.info(f"Starting site discovery for query: {parsed_query.base_result.query_text}")
            
            # Get query category and text
            category = parsed_query.base_result.category
            query_text = parsed_query.base_result.query_text
            
            # Discover sites using multiple strategies
            discovered_sites = []
            
            # 1. LLM-powered discovery
            if self.config.enable_llm_discovery and self.gemini_client and self.gemini_client.is_available():
                try:
                    llm_sites = await self._discover_via_llm(query_text, category)
                    discovered_sites.extend(llm_sites)
                    logger.info(f"LLM discovery found {len(llm_sites)} sites")
                except Exception as e:
                    logger.warning(f"LLM discovery failed: {e}")
            
            # 2. Rule-based discovery
            if self.config.enable_rule_based_discovery:
                rule_sites = await self._discover_via_rules(query_text, category)
                discovered_sites.extend(rule_sites)
                logger.info(f"Rule-based discovery found {len(rule_sites)} sites")
            
            # 3. Search engine discovery (placeholder for future implementation)
            if self.config.enable_search_engine:
                search_sites = await self._discover_via_search(query_text, category)
                discovered_sites.extend(search_sites)
                logger.info(f"Search engine discovery found {len(search_sites)} sites")
            
            # Deduplicate and rank results
            unique_sites = self._deduplicate_sites(discovered_sites)
            ranked_sites = self._rank_sites(unique_sites, query_text, category)
            
            # Apply quality filtering
            filtered_sites = [
                site for site in ranked_sites 
                if site.relevance_score >= self.config.min_relevance_score
            ]
            
            # Limit results
            final_sites = filtered_sites[:self.config.max_discovery_results]
            
            processing_time = time.time() - start_time
            logger.info(f"Site discovery completed in {processing_time:.2f}s. Found {len(final_sites)} sites.")
            
            return final_sites
            
        except Exception as e:
            logger.error(f"Site discovery failed: {e}")
            raise
    
    async def _discover_via_llm(self, query_text: str, category: QueryCategory) -> List[DiscoveryResult]:
        """Discover sites using Gemini LLM."""
        try:
            # Create a prompt for site discovery
            prompt = self._create_discovery_prompt(query_text, category)
            
            # Generate content with LLM
            response = await self.gemini_client.generate_content(
                prompt,
                generation_config={
                    "temperature": self.config.llm_temperature,
                    "max_output_tokens": 2000
                }
            )
            
            # Parse LLM response
            sites = self._parse_llm_response(response, query_text, category)
            
            return sites
            
        except Exception as e:
            logger.error(f"LLM discovery failed: {e}")
            return []
    
    def _create_discovery_prompt(self, query_text: str, category: QueryCategory) -> str:
        """Create a prompt for LLM site discovery."""
        category_description = {
            QueryCategory.AI_TOOLS: "AI tools, machine learning, and artificial intelligence",
            QueryCategory.MUTUAL_FUNDS: "mutual funds, investment, and financial services",
            QueryCategory.GENERAL: "general information and resources"
        }.get(category, "general information")
        
        # Add specific instructions based on category
        if category == QueryCategory.MUTUAL_FUNDS:
            specific_instructions = """
            CRITICAL: For mutual fund queries, prioritize these types of sites:
            - Financial services companies (Vanguard, Fidelity, Schwab, etc.)
            - Investment research platforms (Morningstar, Investopedia, etc.)
            - Financial news sites (MarketWatch, Yahoo Finance, etc.)
            - Brokerage platforms (TD Ameritrade, E*TRADE, etc.)
            DO NOT include general knowledge sites like Wikipedia, developer communities, or test APIs.
            """
        elif category == QueryCategory.AI_TOOLS:
            specific_instructions = """
            CRITICAL: For AI tools queries, prioritize:
            - Product directories (ProductHunt, AlternativeTo, etc.)
            - Tech news sites (TechCrunch, VentureBeat, etc.)
            - GitHub repositories and developer tools
            - AI platform websites
            DO NOT include general knowledge sites or unrelated content.
            """
        else:
            specific_instructions = """
            Focus on authoritative sources relevant to the specific query topic.
            Avoid generic sites like Wikipedia homepage, developer communities, or test APIs unless they directly answer the query.
            """
        
        prompt = f"""
        You are a web research assistant. Find relevant websites for the following query about {category_description}.
        
        Query: "{query_text}"
        
        {specific_instructions}
        
        Please provide a JSON response with an array of websites. For each website, include:
        - url: The website URL (must be a real, accessible URL)
        - title: Website title or name
        - description: Brief description of what the site offers
        - relevance_score: Score from 0.0 to 1.0 indicating relevance to the query (be strict - only high relevance sites should score >0.7)
        - category: The type of website (e.g., "tool", "platform", "news", "documentation", "financial_service")
        
        IMPORTANT RULES:
        1. Only include sites that DIRECTLY relate to the query topic
        2. Prioritize authoritative, reliable sources
        3. Exclude donation pages, generic homepages, or irrelevant content
        4. For financial queries, prioritize financial services and investment sites
        5. Return 5-10 highly relevant sites, not generic ones
        
        Return only the JSON array, no additional text.
        
        Example format:
        [
            {{
                "url": "https://example.com",
                "title": "Example Site",
                "description": "A useful resource for...",
                "relevance_score": 0.9,
                "category": "tool"
            }}
        ]
        """
        
        return prompt
    
    def _parse_llm_response(self, response: Any, query_text: str, category: QueryCategory) -> List[DiscoveryResult]:
        """Parse LLM response into DiscoveryResult objects with robust JSON extraction."""
        try:
            # Extract text from response
            if hasattr(response, 'text'):
                response_text = response.text
            else:
                response_text = str(response)
            
            # Clean and normalize response text
            response_text = response_text.strip()
            
            # Try multiple JSON extraction strategies
            sites_data = None
            
            # Strategy 1: Look for JSON array markers
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start != -1 and json_end > json_start:
                try:
                    json_text = response_text[json_start:json_end]
                    sites_data = json.loads(json_text)
                    logger.debug("Successfully extracted JSON using array markers")
                except json.JSONDecodeError as e:
                    logger.debug(f"JSON extraction using array markers failed: {e}")
            
            # Strategy 2: Look for JSON object markers if array failed
            if sites_data is None:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    try:
                        json_text = response_text[json_start:json_end]
                        parsed = json.loads(json_text)
                        # Check if it's a wrapper object containing sites
                        if 'sites' in parsed and isinstance(parsed['sites'], list):
                            sites_data = parsed['sites']
                            logger.debug("Successfully extracted JSON using object wrapper")
                        elif 'results' in parsed and isinstance(parsed['results'], list):
                            sites_data = parsed['results']
                            logger.debug("Successfully extracted JSON using results wrapper")
                        elif 'data' in parsed and isinstance(parsed['data'], list):
                            sites_data = parsed['data']
                            logger.debug("Successfully extracted JSON using data wrapper")
                        elif 'websites' in parsed and isinstance(parsed['websites'], list):
                            sites_data = parsed['websites']
                            logger.debug("Successfully extracted JSON using websites wrapper")
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON extraction using object markers failed: {e}")
            
            # Strategy 3: Enhanced regex pattern to handle nested JSON objects
            if sites_data is None:
                import re
                # Look for patterns like [{"url": "...", ...}] with better handling of nested structures
                # This pattern handles nested quotes and braces more robustly
                json_pattern = r'\[\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\s*\]'
                matches = re.findall(json_pattern, response_text, re.DOTALL)
                
                if matches:
                    try:
                        # Try each match
                        for match in matches:
                            try:
                                sites_data = json.loads(match)
                                logger.debug("Successfully extracted JSON using enhanced regex pattern")
                                break
                            except json.JSONDecodeError:
                                continue
                    except Exception as e:
                        logger.debug(f"Enhanced regex JSON extraction failed: {e}")
            
            # Strategy 4: Try to extract individual JSON objects and combine them
            if sites_data is None:
                import re
                # Look for individual JSON objects that might be separated by newlines or other text
                json_object_pattern = r'\{\s*"[^"]+"\s*:\s*[^}]+\}'
                matches = re.findall(json_object_pattern, response_text, re.DOTALL)
                
                if matches:
                    try:
                        # Try to parse each object individually
                        potential_sites = []
                        for match in matches:
                            try:
                                site_data = json.loads(match)
                                if 'url' in site_data:  # Only include if it has a URL
                                    potential_sites.append(site_data)
                            except json.JSONDecodeError:
                                continue
                        
                        if potential_sites:
                            sites_data = potential_sites
                            logger.debug(f"Successfully extracted {len(potential_sites)} individual JSON objects")
                    except Exception as e:
                        logger.debug(f"Individual JSON object extraction failed: {e}")
            
            # Strategy 5: Try to fix common JSON formatting issues
            if sites_data is None:
                try:
                    # Remove common LLM response artifacts
                    cleaned_response = response_text
                    
                    # Remove markdown code blocks
                    cleaned_response = re.sub(r'```json\s*', '', cleaned_response)
                    cleaned_response = re.sub(r'```\s*$', '', cleaned_response)
                    
                    # Remove explanatory text before/after JSON
                    cleaned_response = re.sub(r'^.*?\[', '[', cleaned_response, flags=re.DOTALL)
                    cleaned_response = re.sub(r'\].*$', ']', cleaned_response, flags=re.DOTALL)
                    
                    # Try to parse the cleaned response
                    sites_data = json.loads(cleaned_response)
                    logger.debug("Successfully extracted JSON after cleaning response")
                except (json.JSONDecodeError, Exception) as e:
                    logger.debug(f"JSON extraction after cleaning failed: {e}")
            
            # If all strategies failed, log the response for debugging
            if sites_data is None:
                logger.warning(f"Failed to extract JSON from LLM response. Response preview: {response_text[:200]}...")
                return []
            
            # Validate that we have a list of site data
            if not isinstance(sites_data, list):
                logger.warning(f"Expected list of sites, got {type(sites_data)}")
                return []
            
            # Convert to DiscoveryResult objects with enhanced error handling
            sites = []
            for i, site_data in enumerate(sites_data):
                try:
                    # Validate required fields
                    if not isinstance(site_data, dict):
                        logger.warning(f"Site data at index {i} is not a dictionary: {type(site_data)}")
                        continue
                    
                    url = site_data.get('url')
                    if not url:
                        logger.warning(f"Site data at index {i} missing URL")
                        continue
                    
                    # Validate and normalize relevance score
                    relevance_score = site_data.get('relevance_score', 0.5)
                    try:
                        relevance_score = float(relevance_score)
                        relevance_score = max(0.0, min(1.0, relevance_score))  # Clamp to [0, 1]
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid relevance_score for {url}: {relevance_score}, using default 0.5")
                        relevance_score = 0.5
                    
                    site = DiscoveryResult(
                        url=url,
                        relevance_score=relevance_score,
                        domain=self._extract_domain(url),
                        discovery_method=DiscoveryMethod.LLM_GENERATED,
                        title=site_data.get('title'),
                        description=site_data.get('description'),
                        category=site_data.get('category'),
                        query_terms=[query_text],
                        confidence=min(relevance_score, 1.0)
                    )
                    sites.append(site)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse site data at index {i}: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(sites)} sites from LLM response")
            return sites
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return []
    
    async def _discover_via_rules(self, query_text: str, category: QueryCategory) -> List[DiscoveryResult]:
        """Discover sites using rule-based patterns."""
        sites = []
        
        # Get relevant domain patterns for the category
        category_key = category.value
        if category_key in self._domain_patterns:
            domains = self._domain_patterns[category_key]
            
            for domain in domains:
                try:
                    # Create a basic URL
                    url = f"https://{domain}"
                    
                    # Calculate relevance score based on domain relevance
                    relevance_score = self._calculate_domain_relevance(domain, query_text, category)
                    
                    site = DiscoveryResult(
                        url=url,
                        relevance_score=relevance_score,
                        domain=domain,
                        discovery_method=DiscoveryMethod.RULE_BASED,
                        category=category_key,
                        query_terms=[query_text],
                        confidence=0.7  # Rule-based discoveries have moderate confidence
                    )
                    sites.append(site)
                    
                except Exception as e:
                    logger.warning(f"Failed to create rule-based site for {domain}: {e}")
                    continue
        
        return sites
    
    async def _discover_via_search(self, query_text: str, category: QueryCategory) -> List[DiscoveryResult]:
        """Discover sites using search engine integration (placeholder)."""
        # This is a placeholder for future search engine integration
        # For now, return an empty list
        logger.debug("Search engine discovery not yet implemented")
        return []
    
    def _calculate_domain_relevance(self, domain: str, query_text: str, category: QueryCategory) -> float:
        """Calculate relevance score for a domain based on query and category."""
        base_score = 0.5
        
        # Boost score for trusted domains
        if self.config.trusted_domains and domain in self.config.trusted_domains:
            base_score += 0.2
        
        # Boost score for category-specific domains
        if category.value in self._domain_patterns and domain in self._domain_patterns[category.value]:
            base_score += 0.2
        
        # Boost score for popular/authoritative domains
        authoritative_domains = [
            "github.com", "producthunt.com", "stackoverflow.com", "wikipedia.org",
            "morningstar.com", "vanguard.com", "fidelity.com"
        ]
        if domain in authoritative_domains:
            base_score += 0.1
        
        # Ensure score is within bounds
        return min(max(base_score, 0.0), 1.0)
    
    def _deduplicate_sites(self, sites: List[DiscoveryResult]) -> List[DiscoveryResult]:
        """Remove duplicate sites based on domain."""
        seen_domains = set()
        unique_sites = []
        
        for site in sites:
            if site.domain not in seen_domains:
                seen_domains.add(site.domain)
                unique_sites.append(site)
            else:
                # If we have multiple sites for the same domain, keep the one with higher relevance
                existing_site = next(s for s in unique_sites if s.domain == site.domain)
                if site.relevance_score > existing_site.relevance_score:
                    unique_sites.remove(existing_site)
                    unique_sites.append(site)
        
        return unique_sites
    
    def _rank_sites(self, sites: List[DiscoveryResult], query_text: str, category: QueryCategory) -> List[DiscoveryResult]:
        """Rank sites by relevance and quality."""
        # Sort by relevance score (descending)
        ranked_sites = sorted(sites, key=lambda x: x.relevance_score, reverse=True)
        
        # Apply category-specific ranking adjustments
        for site in ranked_sites:
            # Boost sites that match the query category
            if site.category == category.value:
                site.relevance_score = min(site.relevance_score + 0.1, 1.0)
            
            # Boost sites with higher confidence
            site.relevance_score = min(site.relevance_score + (site.confidence * 0.05), 1.0)
        
        # Re-sort after adjustments
        ranked_sites = sorted(ranked_sites, key=lambda x: x.relevance_score, reverse=True)
        
        return ranked_sites
    
    async def _cleanup_resources(self) -> None:
        """Clean up resources used by this agent."""
        # No specific cleanup needed for discovery agent
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information with discovery-specific details."""
        info = super().get_info()
        info.update({
            "scraper_type": "discovery",
            "discovery_methods": {
                "llm_enabled": self.config.enable_llm_discovery,
                "rule_based_enabled": self.config.enable_rule_based_discovery,
                "search_engine_enabled": self.config.enable_search_engine
            },
            "max_results": self.config.max_discovery_results,
            "min_relevance_score": self.config.min_relevance_score,
            "domain_patterns_count": sum(len(patterns) for patterns in self._domain_patterns.values())
        })
        return info
