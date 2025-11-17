# Integration Testing Guide

## Introduction

This document provides a comprehensive guide for end-to-end integration testing of the AI Web Scraper API. The integration testing approach systematically verifies the FastAPI application's functionality from server startup through complete workflow execution.

### Overview

The integration testing suite validates:
- Server startup and initialization
- Health check endpoints for all system components
- Scrape endpoint functionality with sample queries
- Response schema validation
- Workflow stage verification
- Caching behavior
- Error handling

### Prerequisites

- Python 3.8+
- MongoDB (running locally or accessible)
- Google Gemini API key
- All project dependencies installed (`pip install -r requirements.txt`)

### Estimated Time

Complete test suite execution: **30-45 minutes**

## Quick Start

Run the complete integration test suite with a single command:

```bash
bash scripts/test_workflow.sh
```

### Expected Output

The script will:
1. Validate environment configuration
2. Start the FastAPI server
3. Test all health check endpoints
4. Execute sample queries for different categories
5. Validate response schemas
6. Verify workflow stages
7. Test caching functionality

### Success Criteria

All phases should complete with "PASS" status. If any phase fails, review the error messages and check the troubleshooting section.

## Environment Setup

### Required Environment Variables

Create a `.env` file with the following variables:

```bash
GEMINI_API_KEY=your_google_gemini_api_key_here
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=traycer_try
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=true
```

### Validation

Validate your environment configuration:

```bash
python scripts/preflight_check.py
```

### Troubleshooting Common Setup Issues

**Missing API Key:**
```bash
# Get API key from: https://makersuite.google.com/app/apikey
export GEMINI_API_KEY="your-key-here"
```

**MongoDB Connection Issues:**
```bash
# Test MongoDB connection
python scripts/test_connections.py --mongodb-only

# Start MongoDB with Docker
docker run -d -p 27017:27017 --name mongodb mongo:7.0
```

## Server Startup Testing

### Manual Startup

Start the server manually:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Scripted Startup

Use the startup script with validation:

```bash
bash scripts/start_server.sh
```

Options:
- `--production`: Production mode with workers
- `--port <port>`: Custom port
- `--skip-validation`: Skip environment validation
- `--skip-health-check`: Skip post-startup health check

### Verification

Check server logs for successful initialization:
- MongoDB connection established
- Gemini API client initialized
- Scraper session ready
- Cache system operational

Test root endpoint:
```bash
curl http://localhost:8000/
```

Expected response includes:
- Version information
- Environment details
- Available endpoints
- Feature flags

## Health Check Testing

### Basic Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "components": {
    "database": {"status": "healthy"},
    "gemini_api": {"status": "healthy"},
    "cache": {"status": "healthy"}
  }
}
```

### Component Health Checks

**Database:**
```bash
curl http://localhost:8000/health/database
```

**Cache:**
```bash
curl http://localhost:8000/health/cache
```

**System:**
```bash
curl http://localhost:8000/health/system
```

**Workflow:**
```bash
curl http://localhost:8000/api/v1/scrape/health
```

### Automated Testing

Run comprehensive health checks:

```bash
python scripts/test_health.py --all
```

Test specific component:
```bash
python scripts/test_health.py --component database
```

Continuous monitoring:
```bash
python scripts/test_health.py --continuous --interval 30
```

### Interpreting Results

- **healthy**: All systems operational
- **degraded**: Some non-critical issues (service still functional)
- **unhealthy**: Critical failures (service may not function properly)

## Scrape Endpoint Testing

### Test AI Tools Query

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Best AI agents for coding and software development",
    "timeout_seconds": 180,
    "store_results": true
  }'
```

### Test Mutual Funds Query

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Best mutual funds for beginners with low risk",
    "timeout_seconds": 180,
    "store_results": true
  }'
```

### Expected Response Structure

```json
{
  "status": "success",
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_abc123",
  "query": {
    "text": "Best AI agents for coding",
    "category": "ai_tools",
    "confidence_score": 0.95
  },
  "results": {
    "total_items": 15,
    "processed_items": 12,
    "success_rate": 0.80
  },
  "analytics": {
    "pages_scraped": 20,
    "processing_time_breakdown": {
      "query_processing": 1.2,
      "web_scraping": 28.8,
      "ai_processing": 14.4,
      "database_storage": 0.8
    }
  },
  "execution_metadata": {
    "execution_time_ms": 45230.5,
    "stages_timing": {
      "query_processing": 1.2,
      "web_scraping": 28.8,
      "ai_processing": 14.4,
      "database_storage": 0.8
    }
  }
}
```

### Automated Testing

Test specific query:
```bash
python scripts/test_scrape_endpoint.py --query "Best AI tools for coding"
```

Test all categories:
```bash
python scripts/test_scrape_endpoint.py --all
```

Test with authentication:
```bash
python scripts/test_scrape_endpoint.py --query "test" --api-key "your_key"
```

Test caching:
```bash
python scripts/test_scrape_endpoint.py --cache
```

Test edge cases:
```bash
python scripts/test_scrape_endpoint.py --edge-cases
```

Save responses for analysis:
```bash
python scripts/test_scrape_endpoint.py --all --save-responses
```

## Workflow Verification

### Stage 1: Query Processing

**Expected Duration:** 1-3 seconds

**Verification:**
- Query is parsed correctly
- Category classification is accurate
- Confidence score is reasonable (>0.5)

**Check in response:**
```bash
jq '.query' response.json
```

### Stage 2: Web Scraping

**Expected Duration:** 10-30 seconds

**Verification:**
- Relevant sites are discovered
- Content is extracted successfully
- Robots.txt compliance verified

**Check in response:**
```bash
jq '.analytics.pages_scraped' response.json
```

### Stage 3: AI Processing

**Expected Duration:** 15-45 seconds

**Verification:**
- Content is cleaned and analyzed
- Summaries are generated
- Structured data extracted

**Check in response:**
```bash
jq '.results.processed_contents[0].summary' response.json
```

### Stage 4: Database Storage

**Expected Duration:** 1-5 seconds

**Verification:**
- Results stored in MongoDB
- All collections updated
- Data integrity maintained

**Check in response:**
```bash
jq '.execution_metadata.stages_timing.database_storage' response.json
```

### Verification Commands

Extract stage timings:
```bash
jq '.execution_metadata.stages_timing' response.json
```

Verify all stages completed:
```bash
jq '.execution_metadata.stages_timing | keys' response.json
```

## Response Schema Validation

### Validate Response Structure

```bash
python scripts/validate_response_schema.py --response-file response.json
```

### Required Fields Checklist

- ✓ status ("success" or "error")
- ✓ timestamp (ISO 8601 format)
- ✓ request_id (unique identifier)
- ✓ query (text, category, confidence_score)
- ✓ results (total_items, processed_items, success_rate)
- ✓ analytics (pages_scraped, processing_time_breakdown)
- ✓ execution_metadata (execution_time_ms, stages_timing)

### Data Type Validation

- Numeric fields are numbers
- Timestamps are valid ISO 8601
- Arrays contain expected item types
- Nested objects have required fields

### Range Validation

- confidence_score: 0.0 to 1.0
- success_rate: 0.0 to 1.0
- execution_time_ms: positive number
- total_items: non-negative integer

## Performance Benchmarks

### Expected Response Times

- **Query processing:** 1-3 seconds
- **Web scraping:** 10-30 seconds
- **AI processing:** 15-45 seconds
- **Database storage:** 1-5 seconds
- **Total:** 30-90 seconds (typical)

### Acceptable Ranges

- **Fast queries:** <30 seconds
- **Normal queries:** 30-90 seconds
- **Complex queries:** 90-180 seconds
- **Timeout threshold:** 300 seconds (5 minutes)

### Performance Testing

Measure response time:
```bash
time curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

## Cache Testing

### Test Cache Functionality

First request (cache MISS):
```bash
curl -v -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}' \
  | grep -i "X-Cache-Status"
```

Second request (cache HIT):
```bash
curl -v -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}' \
  | grep -i "X-Cache-Status"
```

### Expected Behavior

- First request: `X-Cache-Status: MISS`
- Second request: `X-Cache-Status: HIT`
- Second request is significantly faster
- Cache age increases with time

### Cache Statistics

```bash
curl http://localhost:8000/health/cache
```

## Error Handling Testing

### Test Invalid Query

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{"query": ""}'
```

Expected: 400 Bad Request with validation error

### Test Query Too Long

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"$(python -c 'print("a" * 1001)')\"}"
```

Expected: 400 Bad Request with length validation error

### Test Invalid Timeout

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "timeout_seconds": 10}'
```

Expected: 400 Bad Request (timeout must be ≥30)

## Troubleshooting Guide

### Server Won't Start

1. Check environment variables are set
2. Verify MongoDB is running
3. Check port 8000 is not in use
4. Review server logs for errors

```bash
# Check if port is in use
lsof -i :8000

# Check MongoDB
python scripts/test_connections.py --mongodb-only
```

### Health Checks Fail

**Database unhealthy:**
- Check MongoDB connection string
- Verify MongoDB is running
- Test connection: `python scripts/test_connections.py --mongodb-only`

**Gemini unhealthy:**
- Verify API key is valid
- Check API quota and billing
- Test connection: `python scripts/test_connections.py --gemini-only`

**Cache unhealthy:**
- Check memory availability
- Review cache configuration

### Scrape Requests Timeout

1. Increase `timeout_seconds` parameter
2. Check network connectivity
3. Verify target websites are accessible
4. Review scraper logs for errors

### No Content Found

1. Try different query phrasing
2. Check if query is too specific
3. Verify scraper can access target sites
4. Review robots.txt compliance

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run Integration Tests
  run: |
    bash scripts/test_workflow.sh --save-responses

- name: Upload Test Results
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: |
      *_response.json
      test_report.json
```

### Exit Codes

- **0**: All tests passed
- **1**: Some tests failed
- **2**: Server startup failed
- **3**: Environment validation failed

## Best Practices

1. **Always validate environment** before testing
2. **Use realistic queries** for testing
3. **Save responses** for analysis
4. **Monitor resource usage** during tests
5. **Test with and without authentication**
6. **Test caching behavior**
7. **Verify error handling**
8. **Check performance benchmarks**

## Appendix

### Sample Queries by Category

**AI Tools:**
- "Best AI agents for coding"
- "AI tools for image generation"
- "Open source AI models"

**Mutual Funds:**
- "Best mutual funds for beginners"
- "Top index funds"
- "Low-cost retirement funds"

**General:**
- "Latest AI trends"
- "Cloud computing comparison"
- "Web scraping best practices"

### Common Error Codes

- `VALIDATION_ERROR`: Invalid request format
- `WORKFLOW_TIMEOUT`: Request exceeded timeout
- `QUERY_PROCESSING_ERROR`: Failed to parse query
- `SCRAPING_ERROR`: Failed to scrape content
- `NO_CONTENT_FOUND`: No relevant content found

### Useful Commands

```bash
# Check server status
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs

# Monitor server logs
tail -f logs/app.log

# Check MongoDB data
mongosh --eval "use traycer_try; db.queries.find().limit(5)"
```

---

For more information, see the main [README.md](../README.md) and [Environment Setup Guide](ENVIRONMENT_SETUP.md).

