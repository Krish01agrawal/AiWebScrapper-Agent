"""
Robots.txt compliance module for ethical web scraping.
"""
import logging
import time
from typing import Optional, Dict, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import aiohttp

from app.core.config import settings
from app.scraper.session import get_scraper_session
from app.scraper.rate_limiter import get_rate_limit_manager

logger = logging.getLogger(__name__)


class RobotsChecker:
    """Handles robots.txt compliance for web scraping."""
    
    def __init__(self):
        self._cache: Dict[str, Tuple[RobotFileParser, float]] = {}
        self._cache_ttl = 3600  # 1 hour cache TTL
        self._session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get the scraper session."""
        if self._session is None:
            self._session = get_scraper_session()
        return self._session
    
    async def _fetch_robots_txt(self, base_url: str) -> Optional[str]:
        """Fetch robots.txt content from a website."""
        try:
            robots_url = urljoin(base_url, "/robots.txt")
            session = await self._get_session()
            
            async with session.get(robots_url, timeout=settings.scraper_request_timeout_seconds) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.debug(f"Fetched robots.txt from {robots_url}")
                    return content
                else:
                    logger.debug(f"Robots.txt not found at {robots_url} (status: {response.status})")
                    return None
                    
        except Exception as e:
            logger.debug(f"Failed to fetch robots.txt from {base_url}: {e}")
            return None
    
    def _parse_robots_txt(self, content: str, base_url: str) -> RobotFileParser:
        """Parse robots.txt content and return a RobotFileParser instance."""
        parser = RobotFileParser()
        parser.set_url(base_url)  # Set the base URL for relative paths
        
        # Create a temporary file-like object to feed content to robotparser
        import io
        content_io = io.StringIO(content)
        
        # Use the standard library's read method with our content
        try:
            # For newer Python versions, we need to manually parse
            # This is a complete implementation that works with the standard library
            lines = content.split('\n')
            current_user_agent = None
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    if ':' in line:
                        directive, value = line.split(':', 1)
                        directive = directive.strip().lower()
                        value = value.strip()
                        
                        if directive == 'user-agent':
                            current_user_agent = value
                            # Initialize the user agent in the parser
                            if not hasattr(parser, '_user_agents'):
                                parser._user_agents = {}
                            parser._user_agents[current_user_agent] = {'allow': [], 'disallow': []}
                        
                        elif directive == 'disallow' and current_user_agent:
                            if current_user_agent in parser._user_agents:
                                parser._user_agents[current_user_agent]['disallow'].append(value)
                        
                        elif directive == 'allow' and current_user_agent:
                            if current_user_agent in parser._user_agents:
                                parser._user_agents[current_user_agent]['allow'].append(value)
                        
                        elif directive == 'crawl-delay':
                            try:
                                delay = float(value)
                                # Store crawl delay for later use
                                if not hasattr(parser, '_crawl_delay'):
                                    parser._crawl_delay = {}
                                if current_user_agent:
                                    parser._crawl_delay[current_user_agent] = delay
                                else:
                                    parser._crawl_delay['*'] = delay
                            except ValueError:
                                logger.warning(f"Invalid crawl-delay value: {value}")
                        
                        elif directive == 'sitemap':
                            # Store sitemap URL for later use
                            if not hasattr(parser, '_sitemaps'):
                                parser._sitemaps = []
                            parser._sitemaps.append(value)
            
            # Set default user agent if none specified
            if not hasattr(parser, '_user_agents') or not parser._user_agents:
                parser._user_agents = {'*': {'allow': [], 'disallow': []}}
            
        except Exception as e:
            logger.warning(f"Error parsing robots.txt: {e}")
            # Fallback to default permissive settings
            parser._user_agents = {'*': {'allow': [], 'disallow': []}}
        
        return parser
    
    async def can_fetch(self, url: str, user_agent: str = None) -> bool:
        """Check if a URL can be fetched according to robots.txt."""
        if not settings.scraper_respect_robots:
            return True
        
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            user_agent = user_agent or settings.scraper_user_agent
            
            # Check cache first
            cache_key = base_url
            if cache_key in self._cache:
                parser, timestamp = self._cache[cache_key]
                if time.time() - timestamp < self._cache_ttl:
                    can_fetch = self._check_can_fetch(parser, url, user_agent)
                    logger.debug(f"Robots.txt cache hit for {base_url}: can_fetch={can_fetch}")
                    return can_fetch
            
            # Fetch and parse robots.txt
            content = await self._fetch_robots_txt(base_url)
            
            if content is None:
                # No robots.txt found, default to allowing access
                logger.debug(f"No robots.txt found for {base_url}, allowing access")
                return True
            
            # Parse the robots.txt content
            parser = self._parse_robots_txt(content, base_url)
            
            # Cache the parsed result
            self._cache[cache_key] = (parser, time.time())
            
            # Check if we can fetch
            can_fetch = self._check_can_fetch(parser, url, user_agent)
            
            logger.debug(f"Robots.txt check for {url}: can_fetch={can_fetch}")
            return can_fetch
            
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            # On error, default to allowing access but log the issue
            return True
    
    def _check_can_fetch(self, parser: RobotFileParser, url: str, user_agent: str) -> bool:
        """Check if a URL can be fetched using the parsed robots.txt rules."""
        try:
            if not hasattr(parser, '_user_agents'):
                return True
            
            # Check specific user agent first, then wildcard
            for agent in [user_agent, '*']:
                if agent in parser._user_agents:
                    rules = parser._user_agents[agent]
                    
                    # Check disallow rules first
                    for disallow_path in rules['disallow']:
                        if self._path_matches(url, disallow_path):
                            return False
                    
                    # Check allow rules
                    for allow_path in rules['allow']:
                        if self._path_matches(url, allow_path):
                            return True
                    
                    # If we have rules for this user agent, apply them
                    if rules['disallow'] or rules['allow']:
                        # If no allow rules and we have disallow rules, check if any disallow matches
                        if rules['disallow'] and not rules['allow']:
                            for disallow_path in rules['disallow']:
                                if self._path_matches(url, disallow_path):
                                    return False
                        return True
            
            # Default to allowing if no specific rules found
            return True
            
        except Exception as e:
            logger.warning(f"Error in _check_can_fetch: {e}")
            return True
    
    def _path_matches(self, url: str, pattern: str) -> bool:
        """Check if a URL path matches a robots.txt pattern."""
        try:
            parsed_url = urlparse(url)
            url_path = parsed_url.path
            
            # Handle wildcard patterns
            if pattern == '*':
                return True
            
            # Handle exact path matches
            if pattern == url_path:
                return True
            
            # Handle prefix matches
            if pattern.endswith('*'):
                pattern_prefix = pattern[:-1]
                return url_path.startswith(pattern_prefix)
            
            # Handle exact prefix matches
            if url_path.startswith(pattern):
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error in _path_matches: {e}")
            return False
    
    async def get_crawl_delay(self, url: str, user_agent: str = None) -> Optional[float]:
        """Get the crawl-delay directive for a URL from robots.txt."""
        if not settings.scraper_respect_robots:
            return None
        
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            user_agent = user_agent or settings.scraper_user_agent
            
            # Check cache first
            cache_key = base_url
            if cache_key in self._cache:
                parser, timestamp = self._cache[cache_key]
                if time.time() - timestamp < self._cache_ttl:
                    delay = self._get_crawl_delay_from_parser(parser, user_agent)
                    if delay is not None:
                        logger.debug(f"Robots.txt cache hit for {base_url}: crawl_delay={delay}")
                        return delay
            
            # Fetch and parse robots.txt
            content = await self._fetch_robots_txt(base_url)
            
            if content is None:
                return None
            
            # Parse the robots.txt content
            parser = self._parse_robots_txt(content, base_url)
            
            # Cache the parsed result
            self._cache[cache_key] = (parser, time.time())
            
            # Get crawl delay
            delay = self._get_crawl_delay_from_parser(parser, user_agent)
            
            if delay is not None:
                logger.debug(f"Robots.txt crawl-delay for {base_url}: {delay}s")
                
                # Update rate limiter with crawl delay
                rate_limit_manager = get_rate_limit_manager()
                await rate_limit_manager.set_crawl_delay(url, delay)
            
            return delay
            
        except Exception as e:
            logger.warning(f"Error getting crawl-delay for {url}: {e}")
            return None
    
    def _get_crawl_delay_from_parser(self, parser: RobotFileParser, user_agent: str) -> Optional[float]:
        """Extract crawl delay from the parsed robots.txt parser."""
        try:
            if not hasattr(parser, '_crawl_delay'):
                return None
            
            # Check specific user agent first, then wildcard
            for agent in [user_agent, '*']:
                if agent in parser._crawl_delay:
                    return parser._crawl_delay[agent]
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting crawl delay: {e}")
            return None
    
    async def check_and_update_rate_limits(self, url: str) -> None:
        """Check robots.txt and update rate limits accordingly."""
        try:
            # Check if we can fetch
            can_fetch = await self.can_fetch(url)
            if not can_fetch:
                logger.warning(f"URL {url} is disallowed by robots.txt")
                return
            
            # Get crawl delay and update rate limiter
            await self.get_crawl_delay(url)
            
        except Exception as e:
            logger.warning(f"Error checking robots.txt for rate limiting {url}: {e}")
    
    def clear_cache(self) -> None:
        """Clear the robots.txt cache."""
        self._cache.clear()
        logger.debug("Robots.txt cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about the robots.txt cache."""
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0
        
        for _, timestamp in self._cache.values():
            if current_time - timestamp < self._cache_ttl:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_ttl_seconds": self._cache_ttl
        }


# Global robots checker instance
_robots_checker: Optional[RobotsChecker] = None


def get_robots_checker() -> RobotsChecker:
    """Get the global robots checker instance."""
    global _robots_checker
    
    if _robots_checker is None:
        _robots_checker = RobotsChecker()
    
    return _robots_checker


async def init_robots_checker() -> None:
    """Initialize the robots checker."""
    global _robots_checker
    
    if _robots_checker is None:
        _robots_checker = RobotsChecker()
        logger.info("Robots checker initialized")


async def close_robots_checker() -> None:
    """Close the robots checker."""
    global _robots_checker
    
    if _robots_checker is not None:
        _robots_checker.clear_cache()
        _robots_checker = None
        logger.info("Robots checker closed")
