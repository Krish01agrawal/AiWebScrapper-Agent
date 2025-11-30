"""
Failure simulators for testing error recovery and resilience.

This module provides context managers and utilities for simulating various
failure scenarios including MongoDB failures, Gemini API failures, timeouts,
and network issues.
"""
import asyncio
import logging
from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Dict, Any, List
from unittest.mock import patch, AsyncMock, MagicMock

logger = logging.getLogger(__name__)


# MongoDB Failure Simulators

@contextmanager
def simulate_mongodb_connection_failure():
    """
    Context manager that patches get_client() and DatabaseService methods to raise connection errors.
    
    This patches both the low-level get_client() and high-level DatabaseService methods
    used by WorkflowOrchestrator to ensure failures are properly simulated.
    """
    with patch('app.core.database.get_client') as mock_get_client, \
         patch('app.database.service.DatabaseService.store_query') as mock_store_query, \
         patch('app.database.service.DatabaseService.store_scraped_content') as mock_store_scraped, \
         patch('app.database.service.DatabaseService.store_processed_content') as mock_store_processed, \
         patch('app.database.service.DatabaseService.get_system_health') as mock_health:
        
        mock_get_client.side_effect = ConnectionError("MongoDB connection failed")
        mock_store_query.side_effect = ConnectionError("MongoDB connection failed")
        mock_store_scraped.side_effect = ConnectionError("MongoDB connection failed")
        mock_store_processed.side_effect = ConnectionError("MongoDB connection failed")
        mock_health.side_effect = ConnectionError("MongoDB connection failed")
        
        logger.debug("Simulating MongoDB connection failure")
        try:
            yield
        finally:
            logger.debug("Restored MongoDB connection")


@contextmanager
def simulate_mongodb_timeout():
    """Patches database operations to raise timeout errors."""
    async def raise_timeout(*args, **kwargs):
        raise asyncio.TimeoutError("MongoDB operation timed out")
    
    with patch('app.core.database.get_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_db = AsyncMock()
        mock_collection = AsyncMock()
        
        # Make all collection operations raise timeout
        mock_collection.insert_one = AsyncMock(side_effect=raise_timeout)
        mock_collection.insert_many = AsyncMock(side_effect=raise_timeout)
        mock_collection.find_one = AsyncMock(side_effect=raise_timeout)
        mock_collection.find = AsyncMock(side_effect=raise_timeout)
        mock_collection.update_one = AsyncMock(side_effect=raise_timeout)
        mock_collection.update_many = AsyncMock(side_effect=raise_timeout)
        mock_collection.delete_one = AsyncMock(side_effect=raise_timeout)
        mock_collection.delete_many = AsyncMock(side_effect=raise_timeout)
        mock_collection.count_documents = AsyncMock(side_effect=raise_timeout)
        
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_get_client.return_value = mock_client
        
        logger.debug("Simulating MongoDB timeout")
        try:
            yield
        finally:
            logger.debug("Restored MongoDB operations")


@contextmanager
def simulate_mongodb_unavailable():
    """Simulates MongoDB service down."""
    with patch('app.core.database.get_client') as mock_get_client:
        mock_get_client.side_effect = RuntimeError("MongoDB service unavailable")
        logger.debug("Simulating MongoDB unavailable")
        try:
            yield
        finally:
            logger.debug("Restored MongoDB availability")


class MongoDBFailureSimulator:
    """Configurable MongoDB failure simulator."""
    
    def __init__(self, failure_mode: str = "connection_failure"):
        """
        Initialize MongoDB failure simulator.
        
        Args:
            failure_mode: One of "connection_failure", "timeout", "unavailable"
        """
        self.failure_mode = failure_mode
        self.patches = []
    
    def __enter__(self):
        """Start simulating failure."""
        if self.failure_mode == "connection_failure":
            self.patches.append(patch('app.core.database.get_client'))
            mock_get_client = self.patches[-1].__enter__()
            mock_get_client.side_effect = ConnectionError("MongoDB connection failed")
        elif self.failure_mode == "timeout":
            self.patches.append(patch('app.core.database.get_client'))
            mock_get_client = self.patches[-1].__enter__()
            mock_client = AsyncMock()
            mock_db = AsyncMock()
            mock_collection = AsyncMock()
            async def raise_timeout(*args, **kwargs):
                raise asyncio.TimeoutError("MongoDB operation timed out")
            mock_collection.insert_one = AsyncMock(side_effect=raise_timeout)
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)
            mock_client.__getitem__ = MagicMock(return_value=mock_db)
            mock_get_client.return_value = mock_client
        elif self.failure_mode == "unavailable":
            self.patches.append(patch('app.core.database.get_client'))
            mock_get_client = self.patches[-1].__enter__()
            mock_get_client.side_effect = RuntimeError("MongoDB service unavailable")
        
        logger.debug(f"Simulating MongoDB failure: {self.failure_mode}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop simulating failure."""
        for p in reversed(self.patches):
            p.__exit__(exc_type, exc_val, exc_tb)
        logger.debug(f"Restored MongoDB: {self.failure_mode}")


# Gemini API Failure Simulators

@contextmanager
def simulate_gemini_invalid_key():
    """
    Patches Gemini client to raise API key errors.
    
    This patches both generate_content and is_available/get_model_info to ensure
    all GeminiClient methods used by the system properly reflect the failure.
    """
    with patch('app.core.gemini.GeminiClient.generate_content') as mock_generate, \
         patch('app.core.gemini.GeminiClient.is_available') as mock_available, \
         patch('app.core.gemini.GeminiClient.get_model_info') as mock_model_info:
        
        mock_generate.side_effect = Exception("API key not valid. Please pass a valid API key.")
        mock_available.return_value = False
        mock_model_info.return_value = {
            "model_name": "gemini-1.5-pro",
            "is_available": False,
            "api_key_configured": False
        }
        
        logger.debug("Simulating Gemini invalid API key")
        try:
            yield
        finally:
            logger.debug("Restored Gemini API key")


@contextmanager
def simulate_gemini_quota_exceeded():
    """
    Simulates quota/billing errors.
    
    This patches generate_content and updates is_available to reflect quota issues.
    """
    with patch('app.core.gemini.GeminiClient.generate_content') as mock_generate, \
         patch('app.core.gemini.GeminiClient.is_available') as mock_available:
        
        mock_generate.side_effect = Exception("Quota exceeded for quota metric 'Generative Language API requests'")
        mock_available.return_value = False  # Quota exceeded means service unavailable
        
        logger.debug("Simulating Gemini quota exceeded")
        try:
            yield
        finally:
            logger.debug("Restored Gemini quota")


@contextmanager
def simulate_gemini_network_error():
    """Simulates network connectivity issues."""
    with patch('app.core.gemini.GeminiClient.generate_content') as mock_generate:
        mock_generate.side_effect = ConnectionError("Network error: Failed to connect to Gemini API")
        logger.debug("Simulating Gemini network error")
        try:
            yield
        finally:
            logger.debug("Restored Gemini network")


@contextmanager
def simulate_gemini_rate_limit():
    """Simulates rate limiting errors."""
    with patch('app.core.gemini.GeminiClient.generate_content') as mock_generate:
        mock_generate.side_effect = Exception("429 Resource has been exhausted (e.g. check quota).")
        logger.debug("Simulating Gemini rate limit")
        try:
            yield
        finally:
            logger.debug("Restored Gemini rate limit")


@contextmanager
def simulate_gemini_timeout():
    """Simulates API timeout."""
    with patch('app.core.gemini.GeminiClient.generate_content') as mock_generate:
        mock_generate.side_effect = asyncio.TimeoutError("Gemini API request timed out")
        logger.debug("Simulating Gemini timeout")
        try:
            yield
        finally:
            logger.debug("Restored Gemini timeout")


class GeminiFailureSimulator:
    """Configurable Gemini API failure simulator."""
    
    def __init__(self, error_type: str = "invalid_key"):
        """
        Initialize Gemini failure simulator.
        
        Args:
            error_type: One of "invalid_key", "quota_exceeded", "network_error", 
                      "rate_limit", "timeout"
        """
        self.error_type = error_type
        self.patch_obj = None
    
    def __enter__(self):
        """Start simulating failure."""
        self.patch_obj = patch('app.core.gemini.GeminiClient.generate_content')
        mock_generate = self.patch_obj.__enter__()
        
        error_messages = {
            "invalid_key": "API key not valid. Please pass a valid API key.",
            "quota_exceeded": "Quota exceeded for quota metric 'Generative Language API requests'",
            "network_error": ConnectionError("Network error: Failed to connect to Gemini API"),
            "rate_limit": Exception("429 Resource has been exhausted (e.g. check quota)."),
            "timeout": asyncio.TimeoutError("Gemini API request timed out"),
        }
        
        mock_generate.side_effect = error_messages.get(self.error_type, Exception("Unknown Gemini error"))
        logger.debug(f"Simulating Gemini failure: {self.error_type}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop simulating failure."""
        if self.patch_obj:
            self.patch_obj.__exit__(exc_type, exc_val, exc_tb)
        logger.debug(f"Restored Gemini: {self.error_type}")


# Timeout Simulators

@asynccontextmanager
async def simulate_stage_timeout(stage_name: str, delay: float = 0.1):
    """Simulates timeout in specific workflow stage."""
    async def delayed_operation(*args, **kwargs):
        await asyncio.sleep(delay)
        raise asyncio.TimeoutError(f"{stage_name} timed out after {delay} seconds")
    
    logger.debug(f"Simulating timeout for stage: {stage_name}")
    try:
        yield delayed_operation
    finally:
        logger.debug(f"Restored stage: {stage_name}")


@asynccontextmanager
async def simulate_slow_operation(delay: float):
    """Adds artificial delay to operations."""
    async def slow_operation(*args, **kwargs):
        await asyncio.sleep(delay)
        return kwargs.get('default_return', None)
    
    logger.debug(f"Simulating slow operation with delay: {delay}s")
    try:
        yield slow_operation
    finally:
        logger.debug("Restored operation speed")


class TimeoutSimulator:
    """Controlled timeout testing."""
    
    def __init__(self, timeout_seconds: float = 1.0):
        """
        Initialize timeout simulator.
        
        Args:
            timeout_seconds: Timeout duration in seconds
        """
        self.timeout_seconds = timeout_seconds
        self.patches = []
    
    def __enter__(self):
        """Start timeout simulation."""
        logger.debug(f"Simulating timeout: {self.timeout_seconds}s")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timeout simulation."""
        logger.debug("Restored timeout behavior")
    
    async def simulate_operation(self, operation, *args, **kwargs):
        """Simulate an operation with timeout."""
        try:
            return await asyncio.wait_for(operation(*args, **kwargs), timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(f"Operation timed out after {self.timeout_seconds} seconds")


# Network Failure Simulators

@contextmanager
def simulate_network_error():
    """Simulates network connectivity issues."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.side_effect = ConnectionError("Network connectivity issue")
        logger.debug("Simulating network error")
        try:
            yield
        finally:
            logger.debug("Restored network connectivity")


@contextmanager
def simulate_dns_failure():
    """Simulates DNS resolution failures."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.side_effect = Exception("DNS resolution failed")
        logger.debug("Simulating DNS failure")
        try:
            yield
        finally:
            logger.debug("Restored DNS resolution")


@contextmanager
def simulate_connection_refused():
    """Simulates connection refused errors."""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.side_effect = ConnectionRefusedError("Connection refused")
        logger.debug("Simulating connection refused")
        try:
            yield
        finally:
            logger.debug("Restored connection")


# Partial Failure Simulators

@contextmanager
def simulate_partial_scraping_failure(success_rate: float = 0.5):
    """
    Some scrapers succeed, some fail.
    
    Args:
        success_rate: Probability of success (0.0 to 1.0)
    """
    import random
    
    async def partial_scrape(*args, **kwargs):
        if random.random() < success_rate:
            return kwargs.get('success_result', [])
        else:
            raise Exception("Scraping failed for this URL")
    
    with patch('app.scraper.orchestrator.ScraperOrchestrator.scrape_for_query') as mock_scrape:
        mock_scrape.side_effect = partial_scrape
        logger.debug(f"Simulating partial scraping failure (success_rate={success_rate})")
        try:
            yield
        finally:
            logger.debug("Restored scraping behavior")


@contextmanager
def simulate_partial_processing_failure(success_rate: float = 0.5):
    """
    Some content processes, some fails.
    
    Args:
        success_rate: Probability of success (0.0 to 1.0)
    """
    import random
    
    async def partial_process(*args, **kwargs):
        if random.random() < success_rate:
            return kwargs.get('success_result', [])
        else:
            raise Exception("Processing failed for this content")
    
    with patch('app.processing.orchestrator.ProcessingOrchestrator.process_scraped_content') as mock_process:
        mock_process.side_effect = partial_process
        logger.debug(f"Simulating partial processing failure (success_rate={success_rate})")
        try:
            yield
        finally:
            logger.debug("Restored processing behavior")


class PartialFailureSimulator:
    """Controlled partial failures."""
    
    def __init__(self, success_rate: float = 0.5, failure_type: str = "scraping"):
        """
        Initialize partial failure simulator.
        
        Args:
            success_rate: Probability of success (0.0 to 1.0)
            failure_type: One of "scraping", "processing"
        """
        self.success_rate = success_rate
        self.failure_type = failure_type
        self.patch_obj = None
    
    def __enter__(self):
        """Start partial failure simulation."""
        import random
        
        async def partial_operation(*args, **kwargs):
            if random.random() < self.success_rate:
                return kwargs.get('success_result', [])
            else:
                raise Exception(f"{self.failure_type} failed")
        
        if self.failure_type == "scraping":
            self.patch_obj = patch('app.scraper.orchestrator.ScraperOrchestrator.scrape_for_query')
        elif self.failure_type == "processing":
            self.patch_obj = patch('app.processing.orchestrator.ProcessingOrchestrator.process_scraped_content')
        
        if self.patch_obj:
            mock_op = self.patch_obj.__enter__()
            mock_op.side_effect = partial_operation
        
        logger.debug(f"Simulating partial {self.failure_type} failure (success_rate={self.success_rate})")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop partial failure simulation."""
        if self.patch_obj:
            self.patch_obj.__exit__(exc_type, exc_val, exc_tb)
        logger.debug(f"Restored {self.failure_type} behavior")

