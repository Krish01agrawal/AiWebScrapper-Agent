#!/usr/bin/env python3
"""
Simple test runner with timeouts to identify hanging tests.
"""
import asyncio
import sys
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

async def run_test_with_timeout(test_name, test_func, timeout=10):
    """Run a test with a timeout."""
    try:
        print(f"Running {test_name}...")
        start_time = time.time()
        
        # Create a task with timeout
        task = asyncio.create_task(test_func())
        await asyncio.wait_for(task, timeout=timeout)
        
        elapsed = time.time() - start_time
        print(f"✓ {test_name} passed in {elapsed:.2f}s")
        return True
        
    except asyncio.TimeoutError:
        print(f"✗ {test_name} TIMED OUT after {timeout}s")
        return False
    except Exception as e:
        print(f"✗ {test_name} failed: {e}")
        return False

async def main():
    """Run tests with timeouts."""
    print("Running scraper tests with timeouts...")
    
    # Import test modules
    try:
        from tests.test_scraper import (
            TestScraperSession, TestRateLimiter, TestRobotsCompliance,
            TestBaseScraperAgent, TestSiteDiscoveryAgent, TestContentExtractorAgent,
            TestScraperOrchestrator, TestScraperSchemas, TestScraperIntegration,
            TestScraperPerformance, TestScraperErrorScenarios
        )
    except ImportError as e:
        print(f"Import error: {e}")
        return
    
    # Test results
    results = []
    
    # Run session tests
    session_tests = TestScraperSession()
    results.append(await run_test_with_timeout(
        "test_init_and_close_scraper_session",
        session_tests.test_init_and_close_scraper_session
    ))
    
    # Run base agent tests (synchronous)
    print("Running test_agent_initialization...")
    try:
        # Create a base agent directly without pytest fixtures
        from app.scraper.base import BaseScraperAgent
        agent = BaseScraperAgent("TestAgent", "Test agent for testing", "1.0.0")
        
        # Test basic functionality
        assert agent.name == "TestAgent"
        assert agent.description == "Test agent for testing"
        assert agent.version == "1.0.0"
        
        print("✓ test_agent_initialization passed")
        results.append(True)
    except Exception as e:
        print(f"✗ test_agent_initialization failed: {e}")
        results.append(False)
    
    # Test URL validation
    print("Running test_url_validation...")
    try:
        # Test valid URLs
        valid_urls = ["https://example.com", "http://test.org/page", "example.com"]
        for url in valid_urls:
            validated = agent._validate_url(url)
            assert validated.startswith(("http://", "https://"))
        
        # Test invalid URLs
        invalid_urls = ["", "not-a-url"]
        for url in invalid_urls:
            try:
                agent._validate_url(url)
                assert False, f"Expected ValueError for {url}"
            except ValueError:
                pass
        
        print("✓ test_url_validation passed")
        results.append(True)
    except Exception as e:
        print(f"✗ test_url_validation failed: {e}")
        results.append(False)
    
    print(f"\nTest Summary: {sum(results)}/{len(results)} tests passed")
    
    if not all(results):
        print("Some tests failed or timed out!")
        sys.exit(1)
    else:
        print("All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
