import re
import time
from typing import Dict, Any, List, Optional
from app.agents.base import BaseAgent
from app.scraper.schemas import ScrapedContent
from app.utils.ids import generate_content_id
from datetime import datetime


class ContentCleaningAgent(BaseAgent):
    """Advanced content cleaning agent with comprehensive text processing capabilities."""
    
    def __init__(self, remove_square_brackets: bool = True, remove_curly_brackets: bool = True, remove_html_tags: bool = True, remove_duplicate_sentences: bool = True):
        super().__init__(
            name="ContentCleaningAgent",
            description="Clean and enhance scraped content with advanced text processing"
        )
        self.logger.info("ContentCleaningAgent initialized")
        
        # Cleaning toggles
        self.remove_square_brackets = remove_square_brackets
        self.remove_curly_brackets = remove_curly_brackets
        self.remove_html_tags = remove_html_tags
        self.remove_duplicate_sentences = remove_duplicate_sentences
    
    def _generate_content_id(self, content: ScrapedContent) -> str:
        """Generate a deterministic ID for content based on URL and title."""
        return generate_content_id(content.url, content.title)

    async def clean_content(self, scraped_content: ScrapedContent) -> Dict[str, Any]:
        """Clean and enhance scraped content."""
        content_id = self._generate_content_id(scraped_content)
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting content cleaning for content ID: {content_id}")
            
            # Get content text
            content_text = getattr(scraped_content, 'content', str(scraped_content))
            
            # Apply cleaning pipeline
            cleaned_text = await self._clean_text_content(content_text)
            
            # Analyze content structure
            structure_analysis = await self._analyze_content_structure(cleaned_text)
            
            # Calculate quality metrics
            quality_metrics = await self._calculate_quality_metrics(cleaned_text)
            
            # Calculate cleaning metrics
            original_text = scraped_content.content
            whitespace_normalized = len(original_text) - len(cleaned_text)
            
            # Count duplicate sentences removed
            original_sentences = original_text.split('.')
            cleaned_sentences = cleaned_text.split('.')
            duplicates_removed = len(original_sentences) - len(set(s.strip() for s in original_sentences if s.strip()))
            
            # Get stored cleaning metrics
            cleaning_metrics = getattr(self, '_cleaning_metrics', {})
            html_tags_removed = cleaning_metrics.get('html_tags_removed_count', 0)
            square_brackets_removed = cleaning_metrics.get('square_brackets_removed_count', 0)
            curly_brackets_removed = cleaning_metrics.get('curly_brackets_removed_count', 0)
            
            # Enhance metadata using the dedicated method
            enhanced = await self._enhance_metadata(
                scraped_content, 
                cleaned_text, 
                quality_metrics,
                html_tags_removed,
                square_brackets_removed,
                curly_brackets_removed,
                whitespace_normalized,
                duplicates_removed
            )
            
            processing_duration = time.time() - start_time
            
            result = {
                "id": content_id,
                "cleaned_content": cleaned_text,
                "structure_analysis": structure_analysis,
                "quality_metrics": quality_metrics,
                "enhanced_metadata": enhanced,
                "processing_duration": processing_duration,
                "processing_errors": []
            }
            
            self.logger.info(
                f"Content cleaning completed for {content_id} in {processing_duration:.2f}s"
            )
            return result
            
        except Exception as e:
            processing_duration = time.time() - start_time
            self.logger.error(f"Content cleaning failed for {content_id}: {str(e)}")
            
            # Create error object
            from app.processing.schemas import ProcessingError
            error = ProcessingError(
                error_type="cleaning_failed",
                error_message=str(e),
                content_id=content_id,
                stage="content_cleaning",
                timestamp=datetime.utcnow(),
                retry_count=0,
                recoverable=True,
            )
            
            # Return fallback result
            raw_text = getattr(scraped_content, 'content', str(scraped_content))
            
            return {
                "id": content_id,
                "cleaned_content": raw_text,
                "structure_analysis": {},
                "quality_metrics": {"readability": 0.0, "information_density": 0.0},
                "enhanced_metadata": {},
                "processing_duration": processing_duration,
                "processing_errors": [error.model_dump()]
            }
    
    async def execute(self, scraped_content: ScrapedContent) -> dict:
        """Execute the agent's main functionality."""
        return await self.clean_content(scraped_content)
    
    async def _clean_text_content(self, raw_text: str) -> str:
        """Clean and normalize text content."""
        if not raw_text:
            return raw_text
        
        # Normalize newlines first (Windows/Mac to Unix)
        cleaned = raw_text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Replace only repeated spaces/tabs, not newlines
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        
        # Compress multiple blank lines to double newlines
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)
        
        # Remove common boilerplate patterns
        boilerplate_patterns = [
            r'cookie policy',
            r'privacy policy',
            r'terms of service',
            r'© \d{4}.*?\.',
            r'all rights reserved',
            r'powered by.*?\.',
        ]
        
        for pattern in boilerplate_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean formatting artifacts based on toggles
        html_tags_removed = 0
        square_brackets_removed = 0
        curly_brackets_removed = 0
        
        if self.remove_square_brackets:
            square_brackets_removed = len(re.findall(r'\[.*?\]', cleaned))
            cleaned = re.sub(r'\[.*?\]', '', cleaned)
        
        if self.remove_curly_brackets:
            curly_brackets_removed = len(re.findall(r'\{.*?\}', cleaned))
            cleaned = re.sub(r'\{.*?\}', '', cleaned)
        
        if self.remove_html_tags:
            html_tags_removed = len(re.findall(r'<.*?>', cleaned))
            cleaned = re.sub(r'<.*?>', '', cleaned)
        
        # Store metrics for later use
        self._cleaning_metrics = {
            'html_tags_removed_count': html_tags_removed,
            'square_brackets_removed_count': square_brackets_removed,
            'curly_brackets_removed_count': curly_brackets_removed
        }
        
        # Remove duplicate sentences with safer sentence splitting (if enabled)
        if self.remove_duplicate_sentences:
            sentences = self._split_sentences_safely(cleaned)
            unique_sentences = []
            seen_sentences = set()
            
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and sentence not in seen_sentences:
                    unique_sentences.append(sentence)
                    seen_sentences.add(sentence)
            
            cleaned = '. '.join(unique_sentences)
        
        # Normalize encoding and special characters
        cleaned = cleaned.replace('\u201c', '"').replace('\u201d', '"')
        cleaned = cleaned.replace('\u2018', "'").replace('\u2019', "'")
        cleaned = cleaned.replace('\u2013', '-').replace('\u2014', '--')
        
        return cleaned.strip()
    
    def _split_sentences_safely(self, text: str) -> List[str]:
        """Split text into sentences while preserving abbreviations and common patterns."""
        if not text:
            return []
        
        # Common abbreviations that should not end sentences
        abbreviations = {
            'dr', 'mr', 'mrs', 'ms', 'prof', 'sr', 'jr', 'inc', 'ltd', 'corp', 'co',
            'usa', 'uk', 'ca', 'ny', 'la', 'sf', 'dc', 'etc', 'vs', 'st', 'ave',
            'blvd', 'rd', 'apt', 'ste', 'no', 'vol', 'pp', 'ed', 'rev', 'gen',
            'adm', 'capt', 'lt', 'sgt', 'maj', 'col', 'cmdr', 'gov', 'sen', 'rep'
        }
        
        # Use regex to split on sentence boundaries while preserving abbreviations
        # Look for periods followed by whitespace and capital letters, or end of string
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])$'
        sentences = re.split(sentence_pattern, text)
        
        # Filter out empty sentences and clean up
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                # Check if this looks like an abbreviation that was incorrectly split
                if sentence.lower() in abbreviations:
                    # Merge with previous sentence if it exists
                    if cleaned_sentences:
                        cleaned_sentences[-1] += ' ' + sentence
                    else:
                        cleaned_sentences.append(sentence)
                else:
                    cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    async def _analyze_content_structure(self, cleaned_text: str) -> Dict[str, Any]:
        """Analyze the structure of cleaned content."""
        if not cleaned_text:
            return {}
        
        # Count paragraphs (double newlines)
        paragraphs = len([p for p in cleaned_text.split('\n\n') if p.strip()])
        
        # Count sentences
        sentences = len([s for s in cleaned_text.split('.') if s.strip()])
        
        # Count words
        words = len(cleaned_text.split())
        
        # Identify headings (lines that end with colon or are short and capitalized)
        lines = cleaned_text.split('\n')
        headings = []
        for line in lines:
            line = line.strip()
            if line and (line.endswith(':') or 
                        (len(line.split()) <= 8 and line.isupper())):
                headings.append(line)
        
        # Identify lists (lines starting with bullet points or numbers)
        list_items = []
        for line in lines:
            line = line.strip()
            if re.match(r'^[\-\*•]\s+', line) or re.match(r'^\d+\.\s+', line):
                list_items.append(line)
        
        return {
            "paragraphs": paragraphs,
            "sentences": sentences,
            "words": words,
            "headings": headings,
            "list_items": list_items,
            "estimated_reading_time": max(1, words // 200)  # 200 words per minute
        }
    
    async def _calculate_quality_metrics(self, cleaned_text: str) -> Dict[str, float]:
        """Assess the quality of cleaned content."""
        if not cleaned_text:
            return {"readability": 0.0, "information_density": 0.0, "coherence": 0.0}
        
        # Simple readability score based on sentence and word length
        sentences = [s.strip() for s in cleaned_text.split('.') if s.strip()]
        if not sentences:
            return {"readability": 0.0, "information_density": 0.0, "coherence": 0.0}
        
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        
        # Readability score (lower is better, normalized to 0-1)
        readability_score = max(0.0, min(1.0, 1.0 - (avg_sentence_length - 10) / 30))
        
        # Information density (unique words vs total words)
        words = cleaned_text.split()
        unique_words = set(word.lower() for word in words)
        information_density = len(unique_words) / max(1, len(words))
        
        # Simple coherence score based on paragraph structure
        paragraphs = [p.strip() for p in cleaned_text.split('\n\n') if p.strip()]
        coherence_score = min(1.0, len(paragraphs) / max(1, len(sentences) / 3))
        
        return {
            "readability": round(readability_score, 3),
            "information_density": round(information_density, 3),
            "coherence": round(coherence_score, 3)
        }
    
    async def _enhance_metadata(
        self, 
        scraped_content: ScrapedContent, 
        cleaned_text: str, 
        quality_metrics: Dict[str, float],
        html_tags_removed: int,
        square_brackets_removed: int,
        curly_brackets_removed: int,
        whitespace_normalized: int,
        duplicates_removed: int
    ) -> Dict[str, Any]:
        """Enhance metadata with additional information."""
        enhanced = {
            "cleaning_method": "comprehensive",
            "original_length": len(scraped_content.content),
            "cleaned_length": len(cleaned_text),
            "html_tags_removed_count": html_tags_removed,
            "square_brackets_removed_count": square_brackets_removed,
            "curly_brackets_removed_count": curly_brackets_removed,
            "boilerplate_removed_chars": whitespace_normalized,
            "whitespace_reduced_chars": whitespace_normalized,
            "removed_duplicates": duplicates_removed,
            "original_quality_score": scraped_content.content_quality_score or 0.0,
            "cleaning_timestamp": datetime.utcnow().isoformat(),
            "enhancement_applied": True
        }
        
        # Add quality metrics
        enhanced.update(quality_metrics)
        
        # Add content statistics
        enhanced["word_count"] = len(cleaned_text.split())
        enhanced["character_count"] = len(cleaned_text)
        
        # Add language detection
        try:
            from langdetect import detect
            lang = detect(cleaned_text)
            enhanced["language"] = lang
        except ImportError:
            enhanced["language"] = "unknown"
        except Exception:
            enhanced["language"] = "unknown"
        
        # Calculate enhanced quality score
        enhanced["enhanced_quality_score"] = self._calculate_enhanced_quality(
            scraped_content.content_quality_score or 0.0, quality_metrics
        )
        
        return enhanced
    
    def _calculate_enhanced_quality(
        self, 
        original_score: float, 
        quality_metrics: Dict[str, float]
    ) -> float:
        """Calculate enhanced quality score based on cleaning results."""
        # Weight factors for different quality aspects
        weights = {
            "readability": 0.3,
            "information_density": 0.4,
            "coherence": 0.3
        }
        
        # Calculate weighted quality score
        weighted_score = sum(
            quality_metrics.get(metric, 0.0) * weight 
            for metric, weight in weights.items()
        )
        
        # Combine with original score (70% original, 30% enhanced)
        enhanced_score = (original_score * 0.7) + (weighted_score * 0.3)
        
        return round(min(1.0, max(0.0, enhanced_score)), 3)
