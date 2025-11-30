"""
Test utilities for error recovery and resilience testing.

This package provides failure simulators, mock factories, and other utilities
for comprehensive error scenario testing.
"""

from tests.utils.failure_simulators import (
    simulate_mongodb_connection_failure,
    simulate_mongodb_timeout,
    simulate_mongodb_unavailable,
    MongoDBFailureSimulator,
    simulate_gemini_invalid_key,
    simulate_gemini_quota_exceeded,
    simulate_gemini_network_error,
    simulate_gemini_rate_limit,
    simulate_gemini_timeout,
    GeminiFailureSimulator,
    simulate_stage_timeout,
    simulate_slow_operation,
    TimeoutSimulator,
    simulate_network_error,
    simulate_dns_failure,
    simulate_connection_refused,
    simulate_partial_scraping_failure,
    simulate_partial_processing_failure,
    PartialFailureSimulator,
)

from tests.utils.mock_factories import (
    create_error_response,
    create_validation_error,
    create_timeout_error,
    create_partial_result_error,
    create_mock_database_service,
    create_mock_gemini_client,
    create_mock_api_key_manager,
    create_mock_workflow_orchestrator,
    create_test_api_key,
    create_test_error_detail,
    create_test_execution_metadata,
    create_mongodb_error,
    create_gemini_error,
    create_timeout_scenario,
)

__all__ = [
    # Failure simulators
    "simulate_mongodb_connection_failure",
    "simulate_mongodb_timeout",
    "simulate_mongodb_unavailable",
    "MongoDBFailureSimulator",
    "simulate_gemini_invalid_key",
    "simulate_gemini_quota_exceeded",
    "simulate_gemini_network_error",
    "simulate_gemini_rate_limit",
    "simulate_gemini_timeout",
    "GeminiFailureSimulator",
    "simulate_stage_timeout",
    "simulate_slow_operation",
    "TimeoutSimulator",
    "simulate_network_error",
    "simulate_dns_failure",
    "simulate_connection_refused",
    "simulate_partial_scraping_failure",
    "simulate_partial_processing_failure",
    "PartialFailureSimulator",
    # Mock factories
    "create_error_response",
    "create_validation_error",
    "create_timeout_error",
    "create_partial_result_error",
    "create_mock_database_service",
    "create_mock_gemini_client",
    "create_mock_api_key_manager",
    "create_mock_workflow_orchestrator",
    "create_test_api_key",
    "create_test_error_detail",
    "create_test_execution_metadata",
    "create_mongodb_error",
    "create_gemini_error",
    "create_timeout_scenario",
]

