import time
import re
import hashlib
import psutil
import asyncio
import gc
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from collections import defaultdict
from app.agents.base import BaseAgent
from app.scraper.schemas import ScrapedContent
from app.processing.schemas import DuplicateAnalysis, ProcessingConfig
from app.core.gemini import GeminiClient
from app.core.config import get_settings
from app.utils.ids import generate_content_id


class DisjointSetUnion:
    """Disjoint Set Union (DSU) data structure for efficient grouping of duplicate content."""
    
    def __init__(self):
        self.parent = {}
        self.rank = {}
    
    def find(self, x):
        """Find the root of the set containing x with path compression."""
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        return self.parent[x]
    
    def union(self, x, y):
        """Union two sets containing x and y using rank optimization."""
        root_x = self.find(x)
        root_y = self.find(y)
        
        if root_x == root_y:
            return
        
        # Union by rank
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1
    
    def get_groups(self):
        """Get all groups as lists of connected elements."""
        groups = {}
        for element in self.parent:
            root = self.find(element)
            if root not in groups:
                groups[root] = []
            groups[root].append(element)
        
        # Return only groups with more than one element
        return [group for group in groups.values() if len(group) > 1]


class MemoryCircuitBreaker:
    """Circuit breaker pattern for memory pressure situations."""
    
    def __init__(self, threshold_mb: int = 512, cooldown_seconds: int = 30):
        self.threshold_mb = threshold_mb
        self.cooldown_seconds = cooldown_seconds
        self.last_triggered = 0
        self.is_open = False
    
    def check_memory_pressure(self) -> bool:
        """Check if memory pressure is high enough to trigger circuit breaker."""
        if self.is_open:
            # Check if cooldown period has passed
            if time.time() - self.last_triggered > self.cooldown_seconds:
                self.is_open = False
                return False
            return True
        
        current_memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        if current_memory_mb > self.threshold_mb * 1.8:  # 80% above threshold
            self.is_open = True
            self.last_triggered = time.time()
            return True
        
        return False
    
    def reset(self):
        """Reset the circuit breaker."""
        self.is_open = False
        self.last_triggered = 0


class DuplicateDetectionAgent(BaseAgent):
    """Advanced duplicate detection agent using multiple strategies and AI-powered similarity analysis."""
    
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        super().__init__(
            name="DuplicateDetectionAgent",
            description="Detect duplicate content using multiple strategies",
            gemini_client=gemini_client
        )
        self.logger.info("DuplicateDetectionAgent initialized")
        
        # Initialize memory management components
        self.memory_circuit_breaker = MemoryCircuitBreaker(
            threshold_mb=getattr(self.settings, 'processing_memory_threshold_mb', 512)
        )
        self.gc_counter = 0
        self.last_gc_time = time.time()
        
        # Initialize Gemini client with error handling
        try:
            if gemini_client:
                self.gemini_client = gemini_client
            else:
                self.gemini_client = GeminiClient()
            self.logger.info("DuplicateDetectionAgent initialized with Gemini client")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini client: {str(e)}")
            self.gemini_client = None
            self.logger.warning("DuplicateDetectionAgent initialized without Gemini client - AI features will be disabled")
    
    async def detect_duplicates(
        self, 
        scraped_contents: List[ScrapedContent],
        config: Optional[Any] = None
    ) -> List[DuplicateAnalysis]:
        """
        Detect duplicates using multiple sophisticated techniques with improved memory management.
        
        Args:
            scraped_contents: List of scraped content to analyze
            
        Returns:
            List of DuplicateAnalysis objects for each content item
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting duplicate detection for {len(scraped_contents)} content pieces")
            
            if len(scraped_contents) <= 1:
                # No duplicates possible with single item
                return [self._create_no_duplicates_analysis(content) for content in scraped_contents]
            
            # Check memory pressure before starting
            if self.memory_circuit_breaker.check_memory_pressure():
                self.logger.warning("Memory pressure detected, using fallback duplicate detection")
                return await self._detect_duplicates_fallback(scraped_contents)
            
            # Check if Gemini client is available for AI-powered similarity analysis
            if not self.gemini_client:
                self.logger.warning("Gemini client not available, using only pattern-based duplicate detection")
                # Fall back to pattern-based detection only
                return await self._detect_duplicates_pattern_only(scraped_contents)
            
            # Generate content fingerprints with streaming approach
            fingerprints = await self._generate_fingerprints_streaming(scraped_contents)
            
            # Detect exact duplicates using hashing
            exact_duplicates = self._detect_exact_duplicates(fingerprints)
            
            # Detect near-duplicates using streaming similarity analysis
            near_duplicates = await self._detect_near_duplicates_streaming(scraped_contents, fingerprints, config)
            
            # Detect URL-based duplicates
            url_duplicates = self._detect_url_duplicates(scraped_contents)
            
            # Combine all duplicate detection results
            duplicate_analyses = await self._combine_duplicate_results(
                scraped_contents, exact_duplicates, near_duplicates, url_duplicates
            )
            
            # Force garbage collection after major processing
            self._optimized_garbage_collection()
            
            processing_time = time.time() - start_time
            self.logger.info(f"Duplicate detection completed in {processing_time:.2f}s")
            
            return duplicate_analyses
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Duplicate detection failed: {str(e)}")
            
            # Return fallback analyses
            return [self._create_fallback_analysis(content, str(e)) for content in scraped_contents]
    
    async def _generate_fingerprints_streaming(self, contents: List[ScrapedContent]) -> Dict[str, Dict[str, Any]]:
        """Generate fingerprints using streaming approach to reduce memory usage."""
        fingerprints = {}
        
        # Process content in smaller chunks to manage memory
        chunk_size = min(50, len(contents))
        
        for i in range(0, len(contents), chunk_size):
            chunk = contents[i:i + chunk_size]
            
            for content in chunk:
                content_id = self._generate_content_id(content)
                
                # Text content fingerprint (normalized)
                text_fingerprint = self._generate_text_fingerprint(content.content)
                
                # Title fingerprint
                title_fingerprint = self._generate_text_fingerprint(content.title)
                
                # URL fingerprint
                url_fingerprint = self._generate_url_fingerprint(content.url)
                
                # Content length fingerprint
                length_fingerprint = len(content.content)
                
                # Store fingerprints
                fingerprints[content_id] = {
                    "text": text_fingerprint,
                    "title": title_fingerprint,
                    "url": url_fingerprint,
                    "length": length_fingerprint,
                    "word_count": len(content.content.split()),
                    "structure": self._generate_structure_fingerprint(content.content)
                }
            
            # Check memory pressure after each chunk
            if self.memory_circuit_breaker.check_memory_pressure():
                self.logger.warning("Memory pressure during fingerprint generation, stopping early")
                break
            
            # Small delay between chunks to allow memory cleanup
            await asyncio.sleep(0.01)
    
        return fingerprints
    
    def _optimized_garbage_collection(self):
        """Perform optimized garbage collection with throttling and debug logging."""
        self.gc_counter += 1
        current_time = time.time()
        
        # Only run GC every 10 calls or every 30 seconds, whichever comes first
        if (self.gc_counter % 10 == 0) or (current_time - self.last_gc_time > 30):
            self.logger.debug(f"Running garbage collection (call #{self.gc_counter})")
            collected = gc.collect()
            self.last_gc_time = current_time
            self.logger.debug(f"Garbage collection completed, collected {collected} objects")
        else:
            self.logger.debug(f"Skipping garbage collection (call #{self.gc_counter}, last GC was {current_time - self.last_gc_time:.1f}s ago)")
    
    def _generate_text_fingerprint(self, text: str) -> str:
        """Generate normalized text fingerprint."""
        if not text:
            return ""
        
        # Normalize text
        normalized = text.lower()
        normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
        normalized = normalized.strip()
        
        # Generate hash
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _generate_url_fingerprint(self, url: str) -> str:
        """Normalize URL for comparison with proper tracking parameter removal."""
        if not url:
            return ""
        
        # Convert HttpUrl to string if needed
        url_str = str(url)
        
        try:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            
            # Parse the URL
            parsed = urlparse(url_str.lower())
            
            # Remove www prefix from netloc
            netloc = parsed.netloc
            if netloc.startswith('www.'):
                netloc = netloc[4:]
            
            # Parse query parameters
            query_params = parse_qs(parsed.query)
            
            # Remove common tracking parameters
            tracking_params = [
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'ref', 'source', 'fbclid', 'gclid', 'msclkid', 'mc_cid', 'mc_eid',
                'affiliate', 'partner', 'campaign', 'tracking', 'click', 'redirect'
            ]
            
            # Filter out tracking parameters
            filtered_params = {
                k: v for k, v in query_params.items() 
                if k.lower() not in [p.lower() for p in tracking_params]
            }
            
            # Reconstruct query string without tracking parameters
            if filtered_params:
                # Convert back to query string format
                query_string = urlencode(filtered_params, doseq=True)
            else:
                query_string = ""
            
            # Reconstruct URL without tracking parameters
            clean_url = urlunparse((
                parsed.scheme,
                netloc,
                parsed.path.rstrip('/'),  # Remove trailing slash
                parsed.params,
                query_string,
                ""  # No fragment
            ))
            
            # Remove protocol for comparison
            normalized = re.sub(r'^https?://', '', clean_url)
            
            return normalized
            
        except Exception as e:
            # Fallback to regex-based approach if parsing fails
            self.logger.warning(f"URL parsing failed for {url}, using fallback method: {str(e)}")
            
            # Remove protocol
            normalized = re.sub(r'^https?://', '', url_str.lower())
            
            # Remove www prefix
            normalized = re.sub(r'^www\.', '', normalized)
            
            # Remove query parameters (fallback)
            normalized = re.sub(r'\?.*$', '', normalized)
            
            # Remove trailing slash
            normalized = normalized.rstrip('/')
            
            return normalized
    
    def _generate_structure_fingerprint(self, content: str) -> str:
        """Generate fingerprint based on content structure."""
        if not content:
            return ""
        
        # Count paragraphs, sentences, words
        paragraphs = len([p for p in content.split('\n\n') if p.strip()])
        sentences = len([s for s in content.split('.') if s.strip()])
        words = len(content.split())
        
        # Create structure signature
        structure = f"p{paragraphs}_s{sentences}_w{words}"
        
        return hashlib.md5(structure.encode()).hexdigest()
    
    def _generate_metadata_fingerprint(self, metadata: Dict[str, Any]) -> str:
        """Generate fingerprint based on metadata."""
        if not metadata:
            return ""
        
        # Sort metadata keys for consistent fingerprinting
        sorted_items = sorted(metadata.items())
        metadata_str = str(sorted_items)
        
        return hashlib.md5(metadata_str.encode()).hexdigest()
    
    def _detect_exact_duplicates(self, fingerprints: Dict[str, Dict[str, Any]]) -> List[List[str]]:
        """Detect exact duplicates using fingerprint comparison."""
        exact_groups = []
        processed = set()
        
        for content_id, fingerprint in fingerprints.items():
            if content_id in processed:
                continue
            
            duplicates = [content_id]
            processed.add(content_id)
            
            # Compare with other content
            for other_id, other_fingerprint in fingerprints.items():
                if other_id == content_id or other_id in processed:
                    continue
                
                # Check if fingerprints match
                if (fingerprint["text"] == other_fingerprint["text"] and 
                    fingerprint["title"] == other_fingerprint["title"]):
                    duplicates.append(other_id)
                    processed.add(other_id)
            
            if len(duplicates) > 1:
                exact_groups.append(duplicates)
        
        return exact_groups
    
    async def _detect_near_duplicates_streaming(
        self, 
        contents: List[ScrapedContent], 
        fingerprints: Dict[str, Dict[str, Any]],
        config: Optional[Any] = None
    ) -> List[List[str]]:
        """Detect near-duplicates using streaming similarity analysis with improved memory management."""
        near_duplicate_groups = []
        
        # Group content by similar characteristics
        content_groups = self._group_by_characteristics(contents, fingerprints)
        
        # Analyze each group for near-duplicates with streaming approach
        for group in content_groups:
            if len(group) <= 1:
                continue
            
            # Check memory pressure before processing group
            if self.memory_circuit_breaker.check_memory_pressure():
                self.logger.warning("Memory pressure during similarity analysis, skipping remaining groups")
                break
            
            # Use streaming similarity analysis within group
            async for similarity_group in self._analyze_similarity_streaming(group, contents, config):
                if similarity_group:
                    near_duplicate_groups.append(similarity_group)
                    
                    # Check memory after each group
                    if self.memory_circuit_breaker.check_memory_pressure():
                        self.logger.warning("Memory pressure during group processing, stopping early")
                        break
            
            # Small delay between groups
            await asyncio.sleep(0.05)
        
        return near_duplicate_groups

    async def _analyze_similarity_streaming(
        self, 
        content_group: List[str], 
        all_contents: List[ScrapedContent],
        config: Optional[Any] = None
    ) -> AsyncGenerator[List[str], None]:
        """Streaming AI similarity analysis with improved memory management and timeout protection."""
        if len(content_group) <= 1:
            return
        
        try:
            # Check if Gemini client is available
            if not self.gemini_client:
                self.logger.warning("Gemini client not available for AI similarity analysis")
                return
            
            # Get configurable limits from config or settings
            config_or_settings = config or self.settings
            max_concurrent_analyses = getattr(config_or_settings, 'max_concurrent_ai_analyses', getattr(self.settings, 'processing_max_concurrent_ai_analyses', 5))
            max_content_length = getattr(config_or_settings, 'gemini_max_similarity_content_length', getattr(self.settings, 'gemini_max_similarity_content_length', 1000))
            max_content_pairs = getattr(config_or_settings, 'max_similarity_content_pairs', getattr(self.settings, 'processing_max_similarity_content_pairs', 50))
            max_batch_size = getattr(config_or_settings, 'max_similarity_batch_size', getattr(self.settings, 'processing_max_similarity_batch_size', 10))
            memory_threshold_mb = getattr(config_or_settings, 'memory_threshold_mb', getattr(self.settings, 'processing_memory_threshold_mb', 512))
            timeout_seconds = getattr(config_or_settings, 'content_processing_timeout', getattr(self.settings, 'processing_content_timeout', 30))
            
            # Monitor available memory and adjust batch size dynamically
            available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
            if available_memory_mb < memory_threshold_mb:
                # Reduce batch size when memory is low
                max_batch_size = max(2, max_batch_size // 2)
                max_content_pairs = max(10, max_content_pairs // 2)
                self.logger.warning(f"Low memory detected ({available_memory_mb:.1f}MB), reducing batch size to {max_batch_size}")
            
            self.logger.info(f"Processing similarity analysis with max {max_concurrent_analyses} concurrent analyses, batch size {max_batch_size}")
            
            # Create content pairs using true streaming generator
            async def generate_content_pairs_streaming():
                pair_count = 0
                for i in range(len(content_group)):
                    for j in range(i + 1, len(content_group)):
                        if pair_count >= max_content_pairs:
                            return
                        yield (content_group[i], content_group[j])
                        pair_count += 1
                        # Small delay to prevent overwhelming the system
                        await asyncio.sleep(0.001)
            
            # Process in streaming batches
            processed = set()
            batch_pairs = []
            pair_count = 0
            
            async for pair in generate_content_pairs_streaming():
                batch_pairs.append(pair)
                pair_count += 1
                
                # Process batch when it reaches the target size
                if len(batch_pairs) >= max_batch_size:
                    # Check memory before processing batch
                    if self.memory_circuit_breaker.check_memory_pressure():
                        self.logger.warning("Memory pressure detected, pausing batch processing")
                        await asyncio.sleep(2.0)  # Longer pause for memory pressure
                        continue
                    
                    # Process batch with limited concurrency and timeout protection
                    batch_results = await self._process_similarity_batch_with_timeout(
                        batch_pairs, all_contents, processed, max_concurrent_analyses, 
                        max_content_length, timeout_seconds
                    )
                    
                    # Yield results as they come
                    for result in batch_results:
                        if result:
                            yield result
                    
                    # Clear batch data to free memory
                    batch_pairs.clear()
                    
                    # Add small delay to prevent overwhelming the AI service
                    await asyncio.sleep(0.1)
                    
                    # Optimized garbage collection after each batch
                    self._optimized_garbage_collection()
                
                # Stop if we've reached the maximum pairs limit
                if pair_count >= max_content_pairs:
                    break
            
            # Process remaining pairs in the final batch
            if batch_pairs:
                batch_results = await self._process_similarity_batch_with_timeout(
                    batch_pairs, all_contents, processed, max_concurrent_analyses, 
                    max_content_length, timeout_seconds
                )
                for result in batch_results:
                    if result:
                        yield result
                batch_pairs.clear()
                
        except Exception as e:
            self.logger.error(f"AI similarity analysis failed: {str(e)}")
            return

    async def _process_similarity_batch_with_timeout(
        self,
        batch_pairs: List[Tuple[str, str]],
        all_contents: List[ScrapedContent],
        processed: set,
        max_concurrent: int,
        max_content_length: int,
        timeout_seconds: int
    ) -> List[List[str]]:
        """Process a batch of content pairs with timeout protection and improved error handling."""
        similarity_groups = []
        
        # Process pairs with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_pair_with_timeout(pair):
            async with semaphore:
                try:
                    # Add timeout protection for individual API calls
                    return await asyncio.wait_for(
                        self._analyze_content_pair_simplified(pair, all_contents, processed, max_content_length),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    self.logger.warning(f"Content pair analysis timed out after {timeout_seconds}s")
                    return None
                except Exception as e:
                    self.logger.error(f"Content pair analysis failed: {str(e)}")
                    return None
        
        # Process pairs concurrently with limited concurrency and timeout
        tasks = [process_pair_with_timeout(pair) for pair in batch_pairs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and collect valid results
        for result in results:
            if isinstance(result, list) and result:
                similarity_groups.extend(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Content pair analysis failed: {str(result)}")
        
        return similarity_groups

    async def _analyze_content_pair_simplified(
        self,
        pair: Tuple[str, str],
        all_contents: List[ScrapedContent],
        processed: set,
        max_content_length: int,
        config: Optional[Any] = None
    ) -> List[List[str]]:
        """Analyze similarity for a single content pair with simplified logic."""
        content_id1, content_id2 = pair
        
        if content_id1 in processed or content_id2 in processed:
            return []
        
        try:
            # Build id_to_content map for efficient lookups
            id_to_content = {self._generate_content_id(c): c for c in all_contents}
            
            # Get content objects using generated IDs
            content1 = id_to_content.get(content_id1)
            content2 = id_to_content.get(content_id2)
            
            if not content1 or not content2:
                return []
            
            # Analyze similarity using AI with content length limits
            similarity_score = await self._get_ai_similarity_score_simplified(
                content1, content2, max_content_length
            )
            
            # Use configurable similarity threshold with config preference
            similarity_threshold = getattr(config, 'similarity_threshold', None) if config else getattr(self.settings, 'processing_similarity_threshold', 0.8)
            
            if similarity_score >= similarity_threshold:
                # Create similarity group
                group = [content_id1, content_id2]
                processed.add(content_id1)
                processed.add(content_id2)
                
                # Limited search for additional similar content to prevent memory issues
                search_limit = 20  # Configurable limit
                for other_content in all_contents[:search_limit]:
                    other_id = self._generate_content_id(other_content)
                    if other_id not in processed:
                        try:
                            score = await self._get_ai_similarity_score_simplified(
                                content1, other_content, max_content_length
                            )
                            if score >= similarity_threshold:
                                group.append(other_id)
                                processed.add(other_id)
                        except Exception as e:
                            self.logger.warning(f"Failed to analyze similarity with content {other_id}: {str(e)}")
                            continue
                
                if len(group) > 1:
                    return [group]
        
        except Exception as e:
            self.logger.error(f"Error analyzing content pair {content_id1}-{content_id2}: {str(e)}")
        
        return []

    async def _get_ai_similarity_score_simplified(
        self, 
        content1: ScrapedContent, 
        content2: ScrapedContent,
        max_content_length: int
    ) -> float:
        """Get AI-powered similarity score between two content pieces with simplified logic."""
        # Add null check for Gemini client
        if not self.gemini_client:
            self.logger.warning("Gemini client not available for AI similarity analysis")
            # Return a lower neutral score when AI is unavailable
            return 0.1  # Lower score to avoid false positives
        
        try:
            # Build similarity analysis prompt using configurable content length
            from app.processing.prompts import ProcessingPrompts
            
            prompt = ProcessingPrompts.get_duplicate_detection_prompt(
                title1=content1.title,
                content1=content1.content[:max_content_length],
                title2=content2.title,
                content2=content2.content[:max_content_length],
                max_length=max_content_length
            )
            
            response = await self.gemini_client.generate_content(
                prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 500}
            )
            
            # Extract similarity score with better error handling
            try:
                import json
                raw_text = getattr(response, "text", str(response))
                json_start = raw_text.find('{')
                json_end = raw_text.rfind('}') + 1
                
                if json_start != -1 and json_end > 0:
                    json_str = raw_text[json_start:json_end]
                    parsed = json.loads(json_str)
                    similarity_score = float(parsed.get("similarity_score", 0.5))
                    
                    # Validate score range
                    if 0.0 <= similarity_score <= 1.0:
                        return similarity_score
                    else:
                        self.logger.warning(f"Invalid similarity score {similarity_score}, using default 0.5")
                        return 0.5
                else:
                    self.logger.warning("No JSON found in AI response, using default similarity score 0.5")
                    return 0.5
                    
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                self.logger.warning(f"Failed to parse AI similarity response: {str(e)}, using default score 0.5")
                return 0.5
                
        except Exception as e:
            self.logger.error(f"AI similarity analysis failed: {str(e)}")
            # Return a lower neutral score on AI failure
            return 0.2  # Lower score to avoid false positives

    def _group_by_characteristics(
        self, 
        contents: List[ScrapedContent], 
        fingerprints: Dict[str, Dict[str, Any]]
    ) -> List[List[str]]:
        """Group content by similar characteristics for efficient analysis."""
        groups = []
        processed = set()
        
        for content in contents:
            content_id = self._generate_content_id(content)
            if content_id in processed:
                continue
            
            # Find content with similar characteristics
            similar_content = [content_id]
            processed.add(content_id)
            
            content_fingerprint = fingerprints.get(content_id)
            if content_fingerprint is None:
                continue
            
            for other_content in contents:
                other_id = self._generate_content_id(other_content)
                if other_id == content_id or other_id in processed:
                    continue
                
                other_fingerprint = fingerprints.get(other_id)
                if other_fingerprint is None:
                    continue
                
                # Check for similar characteristics
                if self._are_similar_characteristics(content_fingerprint, other_fingerprint):
                    similar_content.append(other_id)
                    processed.add(other_id)
            
            groups.append(similar_content)
        
        return groups
    
    def _are_similar_characteristics(
        self, 
        fp1: Dict[str, Any], 
        fp2: Dict[str, Any]
    ) -> bool:
        """Check if two content pieces have similar characteristics."""
        # Check content length similarity (within 20%)
        length_diff = abs(fp1["length"] - fp2["length"])
        length_threshold = max(fp1["length"], fp2["length"]) * 0.2
        
        if length_diff > length_threshold:
            return False
        
        # Check word count similarity (within 25%)
        word_diff = abs(fp1["word_count"] - fp2["word_count"])
        word_threshold = max(fp1["word_count"], fp2["word_count"]) * 0.25
        
        if word_diff > word_threshold:
            return False
        
        # Check structure similarity
        if fp1["structure"] == fp2["structure"]:
            return True
        
        return False

    async def _detect_duplicates_pattern_only(self, scraped_contents: List[ScrapedContent]) -> List[DuplicateAnalysis]:
        """Detect duplicates using only pattern-based methods when AI is unavailable."""
        try:
            self.logger.info("Using pattern-based duplicate detection only")
            
            # Generate content fingerprints
            fingerprints = await self._generate_fingerprints_streaming(scraped_contents)
            
            # Detect exact duplicates using hashing
            exact_duplicates = self._detect_exact_duplicates(fingerprints)
            
            # Detect URL-based duplicates
            url_duplicates = self._detect_url_duplicates(scraped_contents)
            
            # Create duplicate analyses without AI similarity
            duplicate_analyses = []
            for content in scraped_contents:
                content_id = self._generate_content_id(content)
                
                # Check for exact duplicates
                exact_duplicate_ids = []
                for group in exact_duplicates:
                    if content_id in group:
                        exact_duplicate_ids = [cid for cid in group if cid != content_id]
                        break
                
                # Check for URL duplicates
                url_duplicate_ids = []
                for group in url_duplicates:
                    if content_id in group:
                        url_duplicate_ids = [cid for cid in group if cid != content_id]
                        break
                
                # Combine all duplicate types
                all_duplicate_ids = list(set(exact_duplicate_ids + url_duplicate_ids))
                
                if all_duplicate_ids:
                    # Create similarity scores dict
                    similarity_scores = {duplicate_id: 1.0 for duplicate_id in all_duplicate_ids}
                    
                    # Find best version (use current content as best for now)
                    best_id = content_id
                    
                    duplicate_analysis = DuplicateAnalysis(
                        content_id=content_id,
                        has_duplicates=True,
                        duplicate_confidence=0.9,
                        duplicate_groups=[all_duplicate_ids],
                        deduplication_recommendations=[
                            f"Keep {content_id} as primary version",
                            f"Consider removing duplicates: {', '.join(all_duplicate_ids)}"
                        ],
                        best_version_id=best_id,
                        processing_metadata={
                            "analysis_method": "pattern_only",
                            "confidence_reason": "Pattern-based detection found duplicates"
                        }
                    )
                else:
                    duplicate_analysis = DuplicateAnalysis(
                        content_id=content_id,
                        has_duplicates=False,
                        duplicate_confidence=0.9,
                        duplicate_groups=[],
                        deduplication_recommendations=["No duplicates detected"],
                        best_version_id=content_id,
                        processing_metadata={
                            "analysis_method": "pattern_only",
                            "confidence_reason": "Pattern-based detection found no duplicates"
                        }
                    )
                
                duplicate_analyses.append(duplicate_analysis)
            
            return duplicate_analyses
            
        except Exception as e:
            self.logger.error(f"Pattern-only duplicate detection failed: {str(e)}")
            # Return fallback analyses
            return [self._create_fallback_analysis(content, str(e)) for content in scraped_contents]
    
    def _detect_url_duplicates(self, contents: List[ScrapedContent]) -> List[List[str]]:
        """Detect duplicates based on URL patterns."""
        url_groups = []
        url_mapping = {}
        
        for content in contents:
            normalized_url = self._generate_url_fingerprint(content.url)
            content_id = self._generate_content_id(content)
            
            if normalized_url in url_mapping:
                url_mapping[normalized_url].append(content_id)
            else:
                url_mapping[normalized_url] = [content_id]
        
        # Create groups for URLs with multiple content pieces
        for url, content_ids in url_mapping.items():
            if len(content_ids) > 1:
                url_groups.append(content_ids)
        
        return url_groups
    
    async def _combine_duplicate_results(
        self,
        contents: List[ScrapedContent],
        exact_duplicates: List[List[str]],
        near_duplicates: List[List[str]],
        url_duplicates: List[List[str]]
    ) -> List[DuplicateAnalysis]:
        """Combine all duplicate detection results into comprehensive analyses using DSU for deterministic grouping."""
        # Build id_to_content map once for efficient lookups
        id_to_content = {self._generate_content_id(c): c for c in contents}
        
        # Initialize DSU for deterministic grouping
        dsu = DisjointSetUnion()
        similarity_scores = {}
        
        # Union IDs from exact duplicates
        for group in exact_duplicates:
            for i in range(len(group) - 1):
                dsu.union(group[i], group[i + 1])
                # Track similarity scores for exact duplicates
                similarity_scores[f"{group[i]}_{group[i + 1]}"] = 1.0
        
        # Union IDs from URL duplicates
        for group in url_duplicates:
            for i in range(len(group) - 1):
                dsu.union(group[i], group[i + 1])
                # Track similarity scores for URL duplicates
                similarity_scores[f"{group[i]}_{group[i + 1]}"] = 0.9
        
        # Union IDs from near-duplicates
        for group in near_duplicates:
            for i in range(len(group) - 1):
                dsu.union(group[i], group[i + 1])
                # Calculate similarity scores for near duplicates
                content1 = id_to_content.get(group[i])
                content2 = id_to_content.get(group[i + 1])
                if content1 and content2:
                    length_diff = abs(len(content1.content) - len(content2.content))
                    max_length = max(len(content1.content), len(content2.content))
                    similarity = max(0.0, 1.0 - (length_diff / max_length))
                    similarity_scores[f"{group[i]}_{group[i + 1]}"] = similarity
        
        # Generate groups from DSU
        duplicate_groups = dsu.get_groups()
        
        # Create DuplicateAnalysis for each content piece
        analyses = []
        for content in contents:
            content_id = self._generate_content_id(content)
            
            # Find the group this content belongs to
            duplicate_group = next((group for group in duplicate_groups if content_id in group), None)
            
            if duplicate_group and len(duplicate_group) > 1:
                # Get other duplicates (exclude self)
                other_duplicates = [cid for cid in duplicate_group if cid != content_id]
                
                # Extract relevant similarity scores for this content
                content_similarity_scores = {}
                for other_id in other_duplicates:
                    key1 = f"{content_id}_{other_id}"
                    key2 = f"{other_id}_{content_id}"
                    if key1 in similarity_scores:
                        content_similarity_scores[other_id] = similarity_scores[key1]
                    elif key2 in similarity_scores:
                        content_similarity_scores[other_id] = similarity_scores[key2]
                
                # Find best version (highest quality score)
                best_version = max(duplicate_group, key=lambda x: id_to_content.get(x, content).content_quality_score or 0.0)
                
                analysis = DuplicateAnalysis(
                    content_id=content_id,
                    has_duplicates=True,
                    duplicate_confidence=0.9,
                    duplicate_groups=[duplicate_group],
                    similarity_scores=content_similarity_scores,
                    deduplication_recommendations=[f"Keep {best_version}, remove others"],
                    best_version_id=best_version,
                    processing_metadata={
                        "analysis_method": "dsu_combined_analysis",
                        "confidence_reason": "DSU-based deterministic grouping found duplicates"
                    }
                )
            else:
                analysis = self._create_no_duplicates_analysis(content)
            
            analyses.append(analysis)
        
        return analyses
    
    def _generate_content_id(self, content: ScrapedContent) -> str:
        """Generate a deterministic ID for content based on URL and title."""
        return generate_content_id(content.url, content.title)

    def _create_no_duplicates_analysis(self, content: ScrapedContent) -> DuplicateAnalysis:
        """Create analysis result for content with no duplicates."""
        return DuplicateAnalysis(
            content_id=self._generate_content_id(content),
            has_duplicates=False,
            duplicate_confidence=0.0,
            duplicate_groups=[],
            similarity_scores={},
            processing_metadata={
                "analysis_method": "no_duplicates_found",
                "confidence_reason": "Content appears unique"
            }
        )

    def _create_fallback_analysis(self, content: ScrapedContent, error: str) -> DuplicateAnalysis:
        """Create fallback analysis result when processing fails."""
        return DuplicateAnalysis(
            content_id=self._generate_content_id(content),
            has_duplicates=False,
            duplicate_confidence=0.0,
            duplicate_groups=[],
            similarity_scores={},
            processing_metadata={
                "analysis_method": "fallback",
                "error": error,
                "confidence_reason": "Fallback due to processing error"
            }
        )
    
    async def execute(self, scraped_contents: List[ScrapedContent], config: Optional[Any] = None) -> List[DuplicateAnalysis]:
        """Execute the agent's main functionality."""
        return await self.detect_duplicates(scraped_contents, config)

    async def _detect_duplicates_fallback(self, scraped_contents: List[ScrapedContent]) -> List[DuplicateAnalysis]:
        """Fallback duplicate detection when memory pressure is high."""
        self.logger.info("Using fallback duplicate detection due to memory pressure")
        
        # Simple hash-based detection only
        fingerprints = {}
        for content in scraped_contents:
            content_hash = hashlib.md5(content.content.encode()).hexdigest()
            content_id = self._generate_content_id(content)
            fingerprints[content_id] = {"hash": content_hash}
        
        # Find exact duplicates only
        duplicate_groups = []
        processed = set()
        
        for content_id, fingerprint in fingerprints.items():
            if content_id in processed:
                continue
            
            duplicates = [content_id]
            processed.add(content_id)
            
            for other_id, other_fingerprint in fingerprints.items():
                if other_id == content_id or other_id in processed:
                    continue
                
                if fingerprint["hash"] == other_fingerprint["hash"]:
                    duplicates.append(other_id)
                    processed.add(other_id)
            
            if len(duplicates) > 1:
                duplicate_groups.append(duplicates)
        
        # Create analyses
        analyses = []
        for content in scraped_contents:
            content_id = self._generate_content_id(content)
            duplicate_group = next((group for group in duplicate_groups if content_id in group), None)
            
            if duplicate_group:
                analysis = DuplicateAnalysis(
                    content_id=content_id,
                    has_duplicates=True,
                    duplicate_confidence=0.95,
                    duplicate_groups=[duplicate_group],
                    similarity_scores={other_id: 1.0 for other_id in duplicate_group if other_id != content_id},
                    deduplication_recommendations=["Keep first occurrence, remove duplicates"],
                    best_version_id=duplicate_group[0],
                    processing_metadata={
                        "analysis_method": "fallback_hash_only",
                        "confidence_reason": "Fallback hash-only found duplicates"
                    }
                )
            else:
                analysis = DuplicateAnalysis(
                    content_id=content_id,
                    has_duplicates=False,
                    duplicate_confidence=1.0,
                    duplicate_groups=[],
                    similarity_scores={},
                    deduplication_recommendations=[],
                    best_version_id=content_id,
                    processing_metadata={
                        "analysis_method": "fallback_hash_only",
                        "confidence_reason": "Fallback hash-only found no duplicates"
                    }
                )
            
            analyses.append(analysis)
        
        return analyses
