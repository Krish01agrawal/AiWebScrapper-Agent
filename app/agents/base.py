from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import asyncio
import logging
from datetime import datetime

from app.core.gemini import GeminiClient
from app.core.config import get_settings, Settings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents providing common functionality."""
    
    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        gemini_client: Optional[GeminiClient] = None,
        settings: Optional[Settings] = None
    ):
        self.name = name
        self.description = description
        self.version = version
        self.gemini_client = gemini_client
        # Set logger for this agent instance
        self.logger = logging.getLogger(f"{__name__}.{name}")
        # Load settings with fallback
        if settings is not None:
            self.settings = settings
        else:
            try:
                self.settings = get_settings()
            except Exception as e:
                self.logger.warning(f"Failed to load settings: {e}, using fallback")
                # Create minimal fallback settings
                class FallbackSettings:
                    scraper_concurrency = 5
                    scraper_request_timeout_seconds = 20
                    scraper_delay_seconds = 1.0
                    scraper_user_agent = "TrayceAI-Bot/1.0"
                    scraper_respect_robots = True
                    scraper_max_retries = 3
                    scraper_max_redirects = 5
                    scraper_content_size_limit = 10485760
                    agent_timeout_seconds = 30
                    parser_timeout_seconds = 45
                    categorizer_timeout_seconds = 30
                    processor_timeout_seconds = 60
                
                self.settings = FallbackSettings()
        self.created_at = datetime.utcnow()
        
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the agent's main functionality. Must be implemented by subclasses."""
        pass
    
    def _get_agent_timeout(self) -> int:
        """Get the appropriate timeout for this agent based on its type."""
        if "parser" in self.name.lower():
            return self.settings.parser_timeout_seconds
        elif "categorizer" in self.name.lower():
            return self.settings.categorizer_timeout_seconds
        elif "processor" in self.name.lower():
            return self.settings.processor_timeout_seconds
        else:
            return self.settings.agent_timeout_seconds
    
    async def execute_with_timeout(self, *args, timeout_seconds: Optional[int] = None, **kwargs) -> Any:
        """Execute the agent with timeout handling."""
        if timeout_seconds is None:
            timeout_seconds = self._get_agent_timeout()
        
        try:
            return await asyncio.wait_for(
                self.execute(*args, **kwargs),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            self.logger.error(f"Agent {self.name} execution timed out after {timeout_seconds} seconds")
            raise
        except Exception as e:
            self.logger.error(f"Agent {self.name} execution failed: {str(e)}")
            raise
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "type": self.__class__.__name__,
            "timeout_seconds": self._get_agent_timeout()
        }
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', version='{self.version}')"
    
    def __repr__(self) -> str:
        return self.__str__()
