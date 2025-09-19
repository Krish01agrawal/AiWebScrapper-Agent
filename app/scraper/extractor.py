"""
Content extraction agent with multiple fallback strategies.
"""
import asyncio
import logging
import time
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse
import re

import json
from datetime import datetime
from bs4 import BeautifulSoup
import aiohttp

from app.scraper.base import BaseScraperAgent
from app.scraper.schemas import (
    ScrapedContent, ContentType, ContentExtractionConfig,
    ScrapingError, ErrorType
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class ContentExtractorAgent(BaseScraperAgent):
    """Agent for extracting content from websites with multiple fallback strategies."""
    
    def __init__(
        self,
        name: str = "ContentExtractorAgent",
        description: str = "Extracts content from websites using multiple strategies",
        version: str = "1.0.0",
        gemini_client: Optional[Any] = None,
        settings: Optional[Any] = None,
        config: Optional[ContentExtractionConfig] = None
    ):
        super().__init__(name, description, version, gemini_client, settings)
        self.config = config or ContentExtractionConfig()
    
    async def execute(self, url: str, extraction_options: Optional[Dict[str, Any]] = None) -> ScrapedContent:
        """Execute content extraction for a URL."""
        start_time = time.time()
        
        try:
            # Validate and normalize URL
            url = self._validate_url(url)
            logger.info(f"Starting content extraction for: {url}")
            
            # Fetch the webpage
            response = await self._fetch_url(url)
            html_content = await response.text()
            
            # Check content size
            if len(html_content.encode('utf-8')) > settings.scraper_content_size_limit:
                raise ScrapingError(
                    error_type=ErrorType.CONTENT_TOO_LARGE,
                    message=f"HTML content too large: {len(html_content.encode('utf-8'))} bytes",
                    url=url,
                    can_retry=False
                )
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract content using multiple strategies
            content, extraction_method, fallback_used = await self._extract_content(soup, url)
            
            # Extract metadata
            metadata = await self._extract_metadata(soup, url)
            
            # Extract images and links if enabled
            images = []
            links = []
            if self.config.include_images:
                images = self._extract_images(soup, url)
            if self.config.include_links:
                links = self._extract_links(soup, url)
            
            # Calculate content quality score
            content_quality_score = self._calculate_content_quality(content, metadata)
            
            # Create ScrapedContent object
            processing_time = time.time() - start_time
            content_size_bytes = len(content.encode('utf-8'))
            
            scraped_content = ScrapedContent(
                url=url,
                title=metadata.get('title'),
                content=content,
                content_type=metadata.get('content_type', ContentType.GENERAL),
                author=metadata.get('author'),
                publish_date=metadata.get('publish_date'),
                description=metadata.get('description'),
                keywords=metadata.get('keywords'),
                images=images,
                links=links,
                timestamp=datetime.utcnow(),
                processing_time=processing_time,
                content_size_bytes=content_size_bytes,
                content_quality_score=content_quality_score,
                extraction_method=extraction_method,
                fallback_used=fallback_used
            )
            
            logger.info(f"Content extraction completed in {processing_time:.2f}s. "
                       f"Extracted {content_size_bytes} bytes of content.")
            
            return scraped_content
            
        except Exception as e:
            logger.error(f"Content extraction failed for {url}: {e}")
            raise
    
    async def _extract_content(self, soup: BeautifulSoup, url: str) -> Tuple[str, str, bool]:
        """Extract main content using multiple strategies."""
        fallback_used = False
        extraction_method = "unknown"
        
        # Strategy 1: Primary extraction with BeautifulSoup
        content = self._extract_with_beautifulsoup(soup)
        if content and len(content.strip()) >= self.config.min_content_length:
            extraction_method = "beautifulsoup_primary"
            return content, extraction_method, fallback_used
        
        # Strategy 2: JSON-LD structured data
        if self.config.enable_json_ld:
            content = self._extract_json_ld(soup)
            if content and len(content.strip()) >= self.config.min_content_length:
                extraction_method = "json_ld_structured_data"
                fallback_used = True
                return content, extraction_method, fallback_used
        
        # Strategy 3: Open Graph meta tags
        if self.config.enable_open_graph:
            content = self._extract_open_graph(soup)
            if content and len(content.strip()) >= self.config.min_content_length:
                extraction_method = "open_graph_meta_tags"
                fallback_used = True
                return content, extraction_method, fallback_used
        
        # Strategy 4: Generic text extraction
        if self.config.enable_generic_extraction:
            content = self._extract_generic_text(soup)
            if content and len(content.strip()) >= self.config.min_content_length:
                extraction_method = "generic_text_extraction"
                fallback_used = True
                return content, extraction_method, fallback_used
        
        # If all strategies fail, return a minimal content
        extraction_method = "minimal_fallback"
        fallback_used = True
        return f"No content could be extracted from {url}", extraction_method, fallback_used
    
    def _extract_with_beautifulsoup(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content using BeautifulSoup with intelligent content detection."""
        content_parts = []
        
        # Try to find main content areas
        if self.config.prefer_main_content:
            # Look for main content tags
            main_selectors = [
                'main', 'article', '[role="main"]', '.main-content', '.content',
                '.post-content', '.entry-content', '.article-content'
            ]
            
            for selector in main_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = self._extract_text_from_element(element)
                    if text and len(text.strip()) >= self.config.min_content_length:
                        content_parts.append(text)
        
        # If no main content found, try article tags
        if self.config.prefer_article_tags and not content_parts:
            articles = soup.find_all('article')
            for article in articles:
                text = self._extract_text_from_element(article)
                if text and len(text.strip()) >= self.config.min_content_length:
                    content_parts.append(text)
        
        # If still no content, try paragraph-based extraction
        if not content_parts:
            paragraphs = soup.find_all('p')
            text_content = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 50:  # Only include substantial paragraphs
                    text_content.append(text)
            
            if text_content:
                content_parts.append('\n\n'.join(text_content))
        
        # Combine and clean content
        if content_parts:
            combined_content = '\n\n'.join(content_parts)
            return self._clean_content(combined_content)
        
        return None
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content from JSON-LD structured data."""
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                
                # Handle different JSON-LD structures
                if isinstance(data, dict):
                    content = self._extract_from_json_ld_object(data)
                    if content:
                        return content
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            content = self._extract_from_json_ld_object(item)
                            if content:
                                return content
                                
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return None
    
    def _extract_from_json_ld_object(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract content from a JSON-LD object."""
        # Try different content fields (removed duplicate 'content')
        content_fields = ['text', 'description', 'articleBody', 'content']
        
        for field in content_fields:
            if field in data and data[field]:
                content = data[field]
                if isinstance(content, str) and len(content.strip()) >= self.config.min_content_length:
                    return self._clean_content(content)
        
        return None
    
    def _extract_open_graph(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content from Open Graph meta tags."""
        # Try multiple Open Graph tags for better content extraction
        og_tags = [
            'og:description',
            'og:title',
            'og:article:content',
            'og:article:section',
            'og:site_name'
        ]
        
        for tag in og_tags:
            og_content = soup.find('meta', property=tag)
            if og_content and og_content.get('content'):
                content = og_content['content']
                if len(content.strip()) >= self.config.min_content_length:
                    return self._clean_content(content)
        
        # Also try Twitter Card tags as fallback
        twitter_tags = [
            'twitter:description',
            'twitter:title',
            'twitter:card'
        ]
        
        for tag in twitter_tags:
            twitter_content = soup.find('meta', name=tag)
            if twitter_content and twitter_content.get('content'):
                content = twitter_content['content']
                if len(content.strip()) >= self.config.min_content_length:
                    return self._clean_content(content)
        
        return None
    
    def _extract_generic_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract content using generic text extraction."""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # More selective removal of navigation and structural elements
        # Only remove if they're clearly navigation or non-content
        for element in soup.find_all(['nav', 'header', 'footer', 'aside']):
            # Check if element contains substantial content before removing
            text_content = element.get_text(strip=True)
            if len(text_content) < 100:  # Only remove if it's short (likely navigation)
                element.decompose()
        
        # Get all text content
        text = soup.get_text()
        
        # Clean and normalize
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        if text and len(text) >= self.config.min_content_length:
            return self._clean_content(text)
        
        return None
    
    def _extract_text_from_element(self, element) -> Optional[str]:
        """Extract clean text from a BeautifulSoup element."""
        if not element:
            return None
        
        # Remove unwanted elements
        for unwanted in element.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            unwanted.decompose()
        
        # Get text content
        text = element.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        return text if text else None
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize extracted content."""
        if not content:
            return ""
        
        # Apply content cleaning based on configuration
        if self.config.remove_ads:
            content = self._remove_ad_content(content)
        
        if self.config.normalize_whitespace:
            content = self._normalize_whitespace(content)
        
        if self.config.remove_duplicate_lines:
            content = self._remove_duplicate_lines(content)
        
        # Truncate if too long
        if len(content.encode('utf-8')) > self.config.max_content_length:
            max_chars = self.config.max_content_length // 4
            content = content[:max_chars] + "... [Content truncated]"
        
        return content.strip()
    
    def _remove_ad_content(self, content: str) -> str:
        """Remove advertisement-related content."""
        ad_patterns = [
            r'advertisement',
            r'sponsored',
            r'promoted',
            r'click here',
            r'buy now',
            r'sign up',
            r'subscribe'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content
    
    def _normalize_whitespace(self, content: str) -> str:
        """Normalize whitespace in content."""
        # Replace multiple spaces with single space
        content = re.sub(r' +', ' ', content)
        
        # Replace multiple newlines with double newlines
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # Clean up leading/trailing whitespace on lines
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(lines)
        
        return content
    
    def _remove_duplicate_lines(self, content: str) -> str:
        """Remove duplicate consecutive lines."""
        lines = content.split('\n')
        cleaned_lines = []
        prev_line = None
        
        for line in lines:
            if line != prev_line:
                cleaned_lines.append(line)
                prev_line = line
        
        return '\n'.join(cleaned_lines)
    
    async def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract metadata from the webpage."""
        metadata = {}
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            metadata['description'] = meta_desc.get('content', '').strip()
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            keywords_text = meta_keywords.get('content', '')
            metadata['keywords'] = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
        
        # Author
        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta:
            metadata['author'] = author_meta.get('content', '').strip()
        
        # Open Graph title
        og_title = soup.find('meta', property='og:title')
        if og_title and not metadata.get('title'):
            metadata['title'] = og_title.get('content', '').strip()
        
        # Open Graph description
        og_desc = soup.find('meta', property='og:description')
        if og_desc and not metadata.get('description'):
            metadata['description'] = og_desc.get('content', '').strip()
        
        # Determine content type
        metadata['content_type'] = self._determine_content_type(soup, metadata)
        
        # Try to extract publish date
        publish_date = self._extract_publish_date(soup)
        if publish_date:
            metadata['publish_date'] = publish_date
        
        return metadata
    
    def _determine_content_type(self, soup: BeautifulSoup, metadata: Dict[str, Any]) -> ContentType:
        """Determine the type of content on the page."""
        # Check for article indicators
        if soup.find('article') or soup.find('time'):
            return ContentType.ARTICLE
        
        # Check for product indicators
        if soup.find('meta', property='product:price:amount'):
            return ContentType.PRODUCT_PAGE
        
        # Check for documentation indicators
        if soup.find('nav', class_='sidebar') or soup.find('div', class_='toc'):
            return ContentType.DOCUMENTATION
        
        # Check for blog indicators
        if soup.find('time') and soup.find('div', class_='post'):
            return ContentType.BLOG_POST
        
        # Check for news indicators
        if soup.find('time') and soup.find('div', class_='news'):
            return ContentType.NEWS_ARTICLE
        
        return ContentType.GENERAL
    
    def _extract_publish_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract publish date from various sources."""
        # Try meta tags first
        date_meta = soup.find('meta', property='article:published_time')
        if date_meta:
            try:
                return datetime.fromisoformat(date_meta['content'].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        # Try time tags
        time_tag = soup.find('time')
        if time_tag and time_tag.get('datetime'):
            try:
                return datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        # Try JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'datePublished' in data:
                    date_str = data['datePublished']
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except (json.JSONDecodeError, ValueError):
                continue
        
        return None
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract images with alt text and URLs."""
        images = []
        
        for img in soup.find_all('img'):
            src = img.get('src')
            alt = img.get('alt', '')
            
            if src:
                # Make URL absolute if relative
                if not src.startswith(('http://', 'https://')):
                    src = urljoin(base_url, src)
                
                images.append({
                    'url': src,
                    'alt': alt.strip() if alt else ''
                })
        
        return images
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract links with text and URLs."""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            text = link.get_text(strip=True)
            
            if href and text:
                # Make URL absolute if relative
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(base_url, href)
                
                # Categorize links
                link_type = 'internal' if urlparse(href).netloc == urlparse(base_url).netloc else 'external'
                
                links.append({
                    'url': href,
                    'text': text,
                    'type': link_type
                })
        
        return links
    
    def _calculate_content_quality(self, content: str, metadata: Dict[str, Any]) -> float:
        """Calculate a quality score for the extracted content."""
        score = 0.5  # Base score
        
        # Content length bonus
        content_length = len(content)
        if content_length > 1000:
            score += 0.2
        elif content_length > 500:
            score += 0.1
        
        # Metadata completeness bonus
        if metadata.get('title'):
            score += 0.1
        if metadata.get('description'):
            score += 0.1
        if metadata.get('author'):
            score += 0.1
        if metadata.get('publish_date'):
            score += 0.1
        
        # Content structure bonus
        if '\n\n' in content:  # Has paragraphs
            score += 0.1
        
        # Ensure score is within bounds
        return min(max(score, 0.0), 1.0)
    
    async def _cleanup_resources(self) -> None:
        """Clean up resources used by this agent."""
        # No specific cleanup needed for extractor agent
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information with extraction-specific details."""
        info = super().get_info()
        info.update({
            "scraper_type": "extractor",
            "extraction_strategies": {
                "beautifulsoup_primary": True,
                "json_ld": self.config.enable_json_ld,
                "open_graph": self.config.enable_open_graph,
                "generic_extraction": self.config.enable_generic_extraction
            },
            "content_limits": {
                "min_length": self.config.min_content_length,
                "max_length": self.config.max_content_length
            },
            "cleaning_options": {
                "remove_ads": self.config.remove_ads,
                "remove_navigation": self.config.remove_navigation,
                "remove_footers": self.config.remove_footers
            }
        })
        return info
