# Error Recovery Testing Guide

## Overview

The AI Web Scraper includes comprehensive error recovery testing to ensure production readiness under various failure scenarios. This guide covers authentication failures, infrastructure outages, API failures, timeouts, graceful degradation, and recovery suggestions.

Error recovery testing validates that the system:
- Handles failures gracefully without crashing
- Provides clear error messages with actionable recovery suggestions
- Returns partial results when non-critical stages fail
- Maintains system stability during cascading failures
- Logs errors with sufficient context for debugging

## Error Scenarios Covered

### 1. Authentication Errors

#### Missing API Key
- **Scenario**: Request sent without API key header
- **Expected Behavior**: Returns 401 with `AUTHENTICATION_REQUIRED` error code
- **Recovery**: Include valid API key in `X-API-Key` header

#### Invalid API Key Format
- **Scenario**: API key doesn't match expected format (`traycer_*`)
- **Expected Behavior**: Returns 401 with `INVALID_API_KEY` error code
- **Recovery**: Use properly formatted API key

#### Expired/Revoked API Keys
- **Scenario**: API key has expired or been revoked
- **Expected Behavior**: Returns 401 with `INVALID_API_KEY` error code
- **Recovery**: Generate new API key or renew expired key

#### Insufficient Permissions
- **Scenario**: API key lacks required permissions
- **Expected Behavior**: Returns 403 with `PERMISSION_ERROR` error code
- **Recovery**: Use API key with appropriate permissions

### 2. MongoDB Failures

#### Connection Failures
- **Scenario**: MongoDB service is down or unreachable
- **Expected Behavior**: 
  - Workflow continues without database storage
  - Returns 200 with warnings about storage failure
  - Partial results include scraped and processed content
- **Recovery**: 
  - Check MongoDB service status
  - Verify connection string in `.env`
  - Ensure network connectivity to MongoDB

#### Timeout Errors
- **Scenario**: MongoDB operations exceed timeout threshold
- **Expected Behavior**: 
  - Operation fails gracefully
  - Workflow continues with partial results
  - Error logged with timeout details
- **Recovery**: 
  - Increase `database_query_timeout_seconds` in settings
  - Check MongoDB performance and indexes
  - Verify network latency

#### Service Unavailable
- **Scenario**: MongoDB service is unavailable during workflow execution
- **Expected Behavior**: 
  - Graceful degradation
  - Results returned without storage
  - Warnings included in response
- **Recovery**: 
  - Restart MongoDB service
  - Check MongoDB logs for errors
  - Verify resource availability

#### Partial Storage Failures
- **Scenario**: Some database operations succeed, others fail
- **Expected Behavior**: 
  - Successful operations complete
  - Failed operations logged as warnings
  - Partial results returned
- **Recovery**: 
  - Review failed operation logs
  - Check database constraints and indexes
  - Retry failed operations

### 3. Gemini API Failures

#### Invalid API Key
- **Scenario**: Gemini API key is invalid or expired
- **Expected Behavior**: 
  - Query processing fails with `QUERY_PROCESSING_ERROR`
  - Error message includes Gemini-specific details
  - Returns 500 with recovery suggestions
- **Recovery**: 
  - Verify `GEMINI_API_KEY` in `.env`
  - Check API key validity in Google Cloud Console
  - Generate new API key if expired

#### Quota Exceeded
- **Scenario**: Gemini API quota/billing limit reached
- **Expected Behavior**: 
  - Request fails with quota error
  - Error message indicates quota issue
  - Returns 500 with recovery suggestions
- **Recovery**: 
  - Check billing status in Google Cloud Console
  - Upgrade quota if needed
  - Implement rate limiting to prevent quota exhaustion

#### Rate Limiting
- **Scenario**: Too many requests to Gemini API
- **Expected Behavior**: 
  - Request fails with rate limit error
  - Error includes retry information
  - Returns 500 with recovery suggestions
- **Recovery**: 
  - Implement exponential backoff
  - Reduce request frequency
  - Check rate limit configuration

#### Network Errors
- **Scenario**: Network connectivity issues with Gemini API
- **Expected Behavior**: 
  - Request fails with network error
  - Error logged with connection details
  - Returns 500 with recovery suggestions
- **Recovery**: 
  - Check internet connectivity
  - Verify firewall rules
  - Retry request after network restoration

#### Service Unavailable
- **Scenario**: Gemini API service is temporarily unavailable
- **Expected Behavior**: 
  - Request fails with service unavailable error
  - Error indicates temporary issue
  - Returns 500 with recovery suggestions
- **Recovery**: 
  - Check Gemini API status page
  - Retry request after service restoration
  - Implement circuit breaker pattern

### 4. Timeout Scenarios

#### Query Processing Timeout
- **Scenario**: Query processing exceeds timeout
- **Expected Behavior**: 
  - Returns 500 with `WORKFLOW_TIMEOUT` error
  - Execution metadata includes completed stages
  - Partial results from completed stages
- **Recovery**: 
  - Increase `timeout_seconds` parameter
  - Simplify query complexity
  - Check Gemini API performance

#### Web Scraping Timeout
- **Scenario**: Web scraping exceeds timeout
- **Expected Behavior**: 
  - Returns 500 with `WORKFLOW_TIMEOUT` error
  - Partial results include query processing results
  - Scraped content from completed requests
- **Recovery**: 
  - Increase timeout for scraping stage
  - Reduce number of URLs to scrape
  - Check target website responsiveness

#### AI Processing Timeout
- **Scenario**: AI processing exceeds timeout
- **Expected Behavior**: 
  - Workflow continues with scraped content only
  - Returns 200 with warnings about processing failure
  - Partial results include scraped content
- **Recovery**: 
  - Increase AI processing timeout
  - Reduce content batch size
  - Check Gemini API performance

#### Database Storage Timeout
- **Scenario**: Database storage exceeds timeout
- **Expected Behavior**: 
  - Workflow continues without storage
  - Returns 200 with warnings about storage failure
  - Results returned without database persistence
- **Recovery**: 
  - Increase database timeout settings
  - Optimize database indexes
  - Check MongoDB performance

#### Overall Workflow Timeout
- **Scenario**: Entire workflow exceeds timeout
- **Expected Behavior**: 
  - Returns 500 with `WORKFLOW_TIMEOUT` error
  - Execution metadata includes all completed stages
  - Partial results from all completed stages
- **Recovery**: 
  - Increase `timeout_seconds` parameter
  - Simplify query or processing requirements
  - Optimize workflow stages

### 5. Validation Errors

#### Empty/Invalid Queries
- **Scenario**: Query is empty or too short
- **Expected Behavior**: 
  - Returns 400 with `VALIDATION_ERROR`
  - Error details include field-level information
  - Recovery suggestions provided
- **Recovery**: 
  - Provide non-empty query with at least 3 characters
  - Check query text for formatting issues

#### Invalid Configuration
- **Scenario**: Processing configuration has invalid values
- **Expected Behavior**: 
  - Returns 400 with `VALIDATION_ERROR`
  - Error details specify invalid fields
  - Recovery suggestions provided
- **Recovery**: 
  - Review configuration parameters
  - Ensure values are within valid ranges
  - Check API documentation for valid options

#### Malicious Input
- **Scenario**: Query contains script tags or suspicious content
- **Expected Behavior**: 
  - Returns 400 with `VALIDATION_ERROR`
  - Malicious content filtered out
  - Error message indicates validation failure
- **Recovery**: 
  - Remove script tags and suspicious URLs
  - Use plain text queries only
  - Review input sanitization

### 6. Graceful Degradation

#### Partial Scraping Failures
- **Scenario**: Some scrapers succeed, others fail
- **Expected Behavior**: 
  - Workflow continues with successful scrapes
  - Returns 200 with warnings about failed scrapes
  - Results include successfully scraped content
- **Recovery**: 
  - Review failed scrape logs
  - Check target website accessibility
  - Retry failed scrapes

#### Partial Processing Failures
- **Scenario**: Some content processes successfully, others fail
- **Expected Behavior**: 
  - Workflow continues with processed content
  - Returns 200 with warnings about processing failures
  - Results include successfully processed content
- **Recovery**: 
  - Review processing error logs
  - Check content quality and format
  - Retry failed processing

#### Database Storage Failures
- **Scenario**: Database storage fails but workflow succeeds
- **Expected Behavior**: 
  - Workflow completes successfully
  - Returns 200 with warnings about storage failure
  - Results returned without database persistence
- **Recovery**: 
  - Check MongoDB connection and status
  - Review database error logs
  - Retry storage operation

## Running Error Tests

### Unit Tests

Run all error scenario tests:
```bash
pytest tests/test_error_scenarios.py -v
```

Run specific error category:
```bash
# MongoDB failures
pytest tests/test_error_scenarios.py::TestMongoDBFailures -v

# Gemini API failures
pytest tests/test_error_scenarios.py::TestGeminiAPIFailures -v

# Timeout scenarios
pytest tests/test_error_scenarios.py::TestTimeoutScenarios -v

# Validation errors
pytest tests/test_error_scenarios.py::TestValidationErrors -v

# Graceful degradation
pytest tests/test_error_scenarios.py::TestGracefulDegradation -v
```

Run middleware error tests:
```bash
pytest tests/test_middleware_errors.py -v
```

Run tests with specific markers:
```bash
# Run only MongoDB failure tests
pytest -m mongodb_failure

# Run only timeout tests
pytest -m timeout_scenario

# Run all error scenario tests
pytest -m error_scenario
```

### Integration Tests

Run end-to-end error recovery tests:
```bash
# Run all error recovery tests
python scripts/test_error_recovery.py --all

# Run specific scenario
python scripts/test_error_recovery.py --test invalid_api_key
python scripts/test_error_recovery.py --test mongodb_failure
python scripts/test_error_recovery.py --test gemini_failure
python scripts/test_error_recovery.py --test timeout
python scripts/test_error_recovery.py --test validation_errors
python scripts/test_error_recovery.py --test rate_limit
python scripts/test_error_recovery.py --test graceful_degradation

# Run with custom server URL
python scripts/test_error_recovery.py --url http://staging.example.com --all

# Generate JSON report
python scripts/test_error_recovery.py --all --output error_recovery_results.json
```

### Manual Testing

Simulate MongoDB failure:
```bash
# Stop MongoDB
./scripts/simulate_failures.sh mongodb down

# Test scrape endpoint
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'

# Restore MongoDB
./scripts/simulate_failures.sh mongodb up
```

Simulate Gemini API failure:
```bash
# Set invalid API key
./scripts/simulate_failures.sh gemini invalid-key

# Test scrape endpoint
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'

# Restore API key
./scripts/simulate_failures.sh gemini restore-key
```

Check service health:
```bash
./scripts/simulate_failures.sh health-check
```

Restore all services:
```bash
./scripts/simulate_failures.sh restore-all
```

## Expected Error Responses

### Error Response Structure

All error responses follow this structure:

```json
{
  "status": "error",
  "timestamp": "2024-01-01T12:00:00Z",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "http_status": 400,
    "details": [
      {
        "error_code": "ERROR_CODE",
        "message": "Detailed error message",
        "context": {
          "field": "query",
          "additional_info": "value"
        },
        "recovery_suggestions": [
          "Suggestion 1",
          "Suggestion 2"
        ]
      }
    ]
  },
  "execution_metadata": {
    "execution_time_ms": 45.2,
    "start_time": "2024-01-01T12:00:00Z",
    "end_time": "2024-01-01T12:00:05Z",
    "stages_timing": {
      "query_processing": 1.2,
      "web_scraping": 3.5
    },
    "completed_stages": ["query_processing", "web_scraping"],
    "failed_stage": "ai_processing"
  },
  "request_id": "req_12345"
}
```

### Error Codes and HTTP Status Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `AUTHENTICATION_REQUIRED` | 401 | API key missing |
| `INVALID_API_KEY` | 401 | API key invalid or expired |
| `PERMISSION_ERROR` | 403 | Insufficient permissions |
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `WORKFLOW_TIMEOUT` | 408 | Workflow execution timed out |
| `QUERY_PROCESSING_ERROR` | 500 | Query processing failed |
| `SCRAPING_ERROR` | 500 | Web scraping failed |
| `AI_PROCESSING_ERROR` | 500 | AI processing failed |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `GEMINI_API_ERROR` | 500 | Gemini API error |
| `INTERNAL_ERROR` | 500 | Unexpected internal error |

## Recovery Suggestions

### By Error Code

#### WORKFLOW_TIMEOUT
- Try increasing the `timeout_seconds` parameter
- Simplify your query to reduce processing time
- Try again during off-peak hours

#### QUERY_PROCESSING_ERROR
- Check your query text for special characters or formatting issues
- Try rephrasing your query more clearly
- Ensure your query is in English
- Verify Gemini API key is valid

#### SCRAPING_ERROR
- Check if the target websites are accessible
- Try a more specific query to target different websites
- Retry the request as this may be a temporary issue

#### NO_CONTENT_FOUND
- Try broadening your search query
- Use different keywords or phrases
- Check if your query topic has available online content

#### VALIDATION_ERROR
- Check your request format and required fields
- Ensure query text is within length limits
- Verify processing configuration parameters

#### AUTHENTICATION_REQUIRED
- Include API key in `X-API-Key` header
- Verify API key format is correct
- Check if authentication is enabled

#### INVALID_API_KEY
- Verify API key is correct
- Check if API key has expired
- Generate new API key if needed

#### RATE_LIMIT_EXCEEDED
- Wait before retrying (check `Retry-After` header)
- Reduce request frequency
- Upgrade API key rate limit if needed

#### DATABASE_ERROR
- Check MongoDB connection and status
- Verify database configuration
- Review database error logs

#### GEMINI_API_ERROR
- Verify Gemini API key is valid
- Check API quota and billing status
- Review Gemini API status page

## Graceful Degradation Behavior

The system implements graceful degradation to ensure partial results are returned even when some stages fail:

### AI Processing Fails
- **Behavior**: Returns scraped content only
- **Response**: 200 with warnings about AI processing failure
- **Results**: Includes all successfully scraped content

### Database Storage Fails
- **Behavior**: Returns results without storage
- **Response**: 200 with warnings about storage failure
- **Results**: Includes all processed content

### Some Scrapers Fail
- **Behavior**: Returns successful scrapes
- **Response**: 200 with warnings about failed scrapes
- **Results**: Includes successfully scraped content

### Partial Content Processing
- **Behavior**: Returns processed + unprocessed content
- **Response**: 200 with warnings about processing failures
- **Results**: Includes all successfully processed content

## Monitoring and Alerting

### Error Rate Thresholds

Monitor the following metrics:
- **Error Rate**: Should be < 5% of total requests
- **Timeout Frequency**: Should be < 1% of total requests
- **Partial Result Rate**: Should be < 10% of total requests
- **Recovery Success Rate**: Should be > 80% for retryable errors

### Alert Configurations

Set up alerts for:
- Error rate exceeding threshold
- Timeout frequency increasing
- MongoDB connection failures
- Gemini API quota approaching limit
- Rate limit violations

### Logging

All errors are logged with structured context:
- Request ID for tracing
- Error type and message
- Stage where error occurred
- Execution metadata
- Recovery suggestions

## Troubleshooting Guide

### MongoDB Connection Issues

**Symptoms**: Database storage failures, connection errors

**Solutions**:
1. Check MongoDB service status: `./scripts/simulate_failures.sh health-check`
2. Verify connection string in `.env`: `MONGODB_URI`
3. Test connection: `mongosh <connection_string>`
4. Check network connectivity
5. Review MongoDB logs

### Gemini API Key Problems

**Symptoms**: Query processing failures, API key errors

**Solutions**:
1. Verify API key in `.env`: `GEMINI_API_KEY`
2. Check API key validity in Google Cloud Console
3. Verify quota and billing status
4. Test API key with simple request
5. Generate new API key if expired

### Timeout Tuning

**Symptoms**: Frequent timeout errors

**Solutions**:
1. Increase `timeout_seconds` parameter
2. Optimize query complexity
3. Reduce number of URLs to scrape
4. Check network latency
5. Review stage-specific timeouts

### Rate Limit Configuration

**Symptoms**: Rate limit errors, 429 responses

**Solutions**:
1. Check current rate limit settings
2. Implement exponential backoff
3. Reduce request frequency
4. Upgrade API key rate limit
5. Review rate limit headers in responses

### Network Connectivity

**Symptoms**: Network errors, connection failures

**Solutions**:
1. Check internet connectivity
2. Verify firewall rules
3. Test DNS resolution
4. Review proxy settings
5. Check network latency

## CI/CD Integration

### GitHub Actions

Error recovery tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests
- Daily schedule (2 AM UTC)
- Manual workflow dispatch

### Test Result Parsing

Test results are available as:
- JSON reports for programmatic parsing
- GitHub Actions artifacts
- PR comments with summary

### Failure Notifications

Configure notifications for:
- Test failures in CI/CD
- Error rate threshold breaches
- Service degradation alerts

## Best Practices

1. **Always test error scenarios before deployment**
   - Run error recovery tests in staging
   - Validate error responses
   - Test graceful degradation

2. **Monitor error rates in production**
   - Set up error rate alerts
   - Track error trends over time
   - Review error logs regularly

3. **Implement circuit breakers for external services**
   - Prevent cascading failures
   - Provide fallback mechanisms
   - Monitor service health

4. **Use exponential backoff for retries**
   - Avoid overwhelming services
   - Respect rate limits
   - Implement jitter for retries

5. **Log errors with structured context**
   - Include request IDs
   - Add execution metadata
   - Provide debugging information

6. **Provide actionable recovery suggestions**
   - Be specific about the issue
   - Suggest concrete solutions
   - Include relevant configuration

7. **Test cascading failures**
   - Simulate multiple failures
   - Verify system stability
   - Test recovery mechanisms

8. **Validate partial result handling**
   - Ensure partial results are useful
   - Verify warnings are clear
   - Test edge cases

## Related Documentation

- [Integration Testing Guide](INTEGRATION_TESTING.md)
- [Load Testing Guide](LOAD_TESTING.md)
- [Real-World Testing Guide](REAL_WORLD_TESTING.md)

