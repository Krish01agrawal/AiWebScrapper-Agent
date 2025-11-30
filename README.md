# Traycer Try API

A modern FastAPI application with MongoDB integration, Google Gemini AI capabilities, and intelligent web scraping, built following 2024-2025 best practices.

## 🚀 Features

- **FastAPI Framework**: Modern, fast web framework for building APIs with Python
- **Async MongoDB**: Motor driver for high-performance async database operations
- **Google Gemini AI**: Integration with Google's latest AI model for intelligent operations
- **Intelligent Web Scraping**: AI-powered site discovery and content extraction with ethical practices
- **AI Web Scraping API**: Complete `/scrape` endpoint that orchestrates query processing, web scraping, and AI analysis
- **Environment-based Configuration**: Secure configuration management using environment variables
- **Health Checks**: Comprehensive system health monitoring endpoints
- **CORS Support**: Cross-origin resource sharing for frontend integration
- **Type Safety**: Full type hints and Pydantic validation throughout

### 🏭 Production-Ready Features

- **🔐 API Key Authentication**: Secure API key-based authentication with rate limiting per key
- **📊 Structured Logging**: JSON-formatted logs with rotation and contextual information
- **⚡ In-Memory Caching**: TTL-based caching layer for improved performance and reduced API calls
- **📈 Metrics & Monitoring**: Prometheus-compatible metrics export with comprehensive performance tracking
- **🐳 Docker Support**: Multi-stage Docker builds with optimized production images
- **🔧 Docker Compose**: Complete orchestration setup with MongoDB and optional Mongo Express
- **🏥 Advanced Health Checks**: Kubernetes-compatible liveness and readiness probes
- **🛡️ Security Middleware**: Request validation, error handling, and performance monitoring
- **📋 Production Configuration**: Comprehensive environment templates for production deployment

## 📋 Prerequisites

- **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
- **MongoDB 4.4+** - [Download MongoDB](https://www.mongodb.com/try/download/community) or use [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- **Google Gemini API Key** - [Get API Key](https://makersuite.google.com/app/apikey)
- **Git** - [Download Git](https://git-scm.com/downloads)

**Estimated setup time:** 15-20 minutes

## 🚀 Quick Start

If you're in a hurry, run these commands:

```bash
# Clone and navigate
git clone <repository-url>
cd traycerTry

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your values
# Set GEMINI_API_KEY=your_actual_api_key_here
# Set MONGODB_URI=mongodb://localhost:27017

# Validate environment
python scripts/preflight_check.py

# Start the application
uvicorn app.main:app --reload
```

## Demo Materials

For team demonstrations and presentations, we provide comprehensive demo materials:

### Interactive Demo Script

Run an interactive demo with example queries and live progress tracking:

```bash
# Quick demo (pre-selected query)
python scripts/demo.py --quick

# Category-based demo
python scripts/demo.py --category ai_tools

# Custom query
python scripts/demo.py --query "Your custom query here"

# Full interactive menu
python scripts/demo.py
```

The demo script provides:
- Colored terminal output for visual appeal
- Live progress tracking through scraping stages
- Real-time metrics display
- Cache demonstration
- Error handling examples

### API Collections

**Postman Collection:**

- Import `demo/postman_collection.json` into Postman
- Includes all endpoints with example requests and responses
- Pre-configured environment variables
- Test scripts for validation

**Curl Scripts:**

```bash
# Run comprehensive curl tests
bash demo/curl_collection.sh

# With API key
bash demo/curl_collection.sh --api-key your_key_here

# Save responses
bash demo/curl_collection.sh --save-responses
```

### Live Monitoring Dashboard

Open the monitoring dashboard for live metrics during demos:

```bash
# Open in default browser
open demo/dashboard.html

# Or navigate to file in browser
# file:///path/to/traycerTry/demo/dashboard.html
```

The dashboard displays:
- Real-time system health status
- Request metrics and performance
- Cache statistics
- Recent activity log
- Auto-refresh every 10 seconds

### Documentation

- **Demo Guide**: See [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) for step-by-step presentation flow
- **Known Limitations**: See [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) for system constraints and Q&A prep

### Quick Demo Checklist

1. Start MongoDB: `docker run -d -p 27017:27017 mongo:7.0`
2. Validate environment: `python scripts/preflight_check.py`
3. Start server: `bash scripts/start_server.sh`
4. Open dashboard: `open demo/dashboard.html`
5. Run demo: `python scripts/demo.py --quick`

For detailed demo instructions, see [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md).

## 🛠️ Detailed Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd traycerTry
   ```

2. **Create and activate virtual environment**
   ```bash
   # Using venv (recommended)
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Or using conda
   conda create -n traycer-try python=3.9
   conda activate traycer-try
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env with your actual values
   nano .env  # or use your preferred editor
   ```

## ✅ Environment Validation

Before starting the application, validate your environment setup:

```bash
# Quick validation
bash scripts/quick_check.sh

# Full validation
python scripts/preflight_check.py

# Test connections only
python scripts/test_connections.py

# Fix environment issues
python scripts/fix_env.py
```

For detailed setup instructions, see [Environment Setup Guide](docs/ENVIRONMENT_SETUP.md).

## 🧪 Testing

The AI Web Scraper project includes a comprehensive test suite with proper fixtures, mocks, and async support using pytest-asyncio.

### Running Tests

#### Quick Start
```bash
# Run all tests with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/test_agents.py -v

# Run unit tests only
pytest tests/ -m unit -v

# Run integration tests
pytest tests/ -m integration -v
```

#### Using Make Commands
```bash
make test              # Run all tests with coverage
make test-unit         # Run unit tests only
make test-fast         # Skip slow tests
make coverage          # View coverage report
make clean             # Clean test artifacts
```

### Test Organization

### Test Coverage

The test suite includes:
- **Unit Tests**: Component-level testing with mocks
- **Integration Tests**: End-to-end workflow validation
- **Real-World Scenario Tests**: Content quality and relevance validation
- **Performance Tests**: Timing and benchmarking
- **Load Tests**: Concurrent request handling, rate limiting, caching, memory usage, connection pooling

The test suite is organized into the following modules:

- **`tests/test_agents.py`**: Tests for query processing and categorization (694 lines)
- **`tests/test_scraper.py`**: Tests for web scraping functionality (891 lines)
- **`tests/test_processing.py`**: Tests for AI content processing (1165 lines)
- **`tests/test_database.py`**: Tests for database operations (946 lines)
- **`tests/test_api.py`**: Tests for API endpoints (717 lines)

### Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit`: Unit tests (no external dependencies)
- `@pytest.mark.integration`: Integration tests (mocked services)
- `@pytest.mark.slow`: Tests that take >5 seconds
- `@pytest.mark.requires_gemini`: Tests requiring actual Gemini API
- `@pytest.mark.requires_mongodb`: Tests requiring MongoDB connection

### Environment Setup for Tests

Tests use mocked services by default and don't require actual API keys or database connections:

```bash
# Tests work out of the box with mocks
pytest tests/ -v

# To run tests requiring actual services (optional)
export GEMINI_API_KEY="your-api-key"
export MONGODB_URI="mongodb://localhost:27017/test"
pytest tests/ -m "requires_gemini or requires_mongodb" -v
```

### Coverage Requirements

- **Minimum Coverage**: 70%
- **Target Coverage by Module**:
  - agents: >80%
  - scraper: >75%
  - processing: >75%
  - database: >80%
  - api: >85%

View HTML coverage report:
```bash
make coverage
# Opens htmlcov/index.html in your browser
```

### Continuous Integration

Tests run automatically on GitHub Actions for:
- Push to main/develop branches
- Pull requests
- Multiple Python versions (3.8, 3.9, 3.10, 3.11)
- Multiple operating systems (Ubuntu, macOS, Windows)

View test results in PR checks and the Actions tab.

### Troubleshooting Tests

#### Common Issues and Solutions

**Import Errors**
```bash
# Ensure all dependencies installed
pip install -r requirements.txt

# Check Python path
python scripts/preflight_check.py --skip-connections
```

**Async Errors**
```bash
# Verify pytest-asyncio is installed
pip install pytest-asyncio

# Check async test patterns in conftest.py
```

**Timeout Errors**
```bash
# Increase timeout for slow tests
pytest tests/ --timeout=60

# Run only fast tests
pytest tests/ -m "not slow" -v
```

**Mock Errors**
```bash
# Verify mock setup in conftest.py
# Check that mock responses match actual API structure
```

**Database Errors**
```bash
# Use mocked database (default)
pytest tests/test_database.py -v

# Or start MongoDB for integration tests
make db-start
pytest tests/test_database.py -m requires_mongodb -v
```

### Writing New Tests

When adding new tests, follow these patterns:

1. **Use existing fixtures** from `conftest.py`
2. **Add appropriate markers** (`@pytest.mark.unit`, etc.)
3. **Mock external services** (Gemini API, MongoDB)
4. **Include docstrings** explaining test purpose
5. **Follow naming conventions**: `test_<functionality>_<scenario>`

Example:
```python
@pytest.mark.unit
async def test_agent_parsing_success(mock_gemini_client):
    """Test that agent correctly parses valid Gemini response."""
    # Test implementation
```

### Test Results Documentation

- **Detailed Results**: `docs/TEST_RESULTS.md`
- **Coverage Report**: `htmlcov/index.html`
- **CI/CD Results**: GitHub Actions tab
- **Test Execution**: `python scripts/run_tests.py --coverage --output markdown`

### Performance Testing

Run performance and load tests:
```bash
make perf-test
# Runs tests marked as slow or performance
```

### Security Testing

Run security scans:
```bash
make security-test
# Runs bandit and safety checks
```

### Full Test Suite

Run the complete test suite:
```bash
make test-all
# Runs unit, integration, performance, and security tests
```

For more detailed testing information, see the generated test reports in `docs/TEST_RESULTS.md`.

## 🔄 Integration Testing

The AI Web Scraper API includes comprehensive end-to-end integration testing to verify complete workflow functionality from server startup through scrape endpoint execution.

### Quick Start

Run the complete integration test suite:

```bash
# Run complete workflow test
make test-workflow

# Or manually
bash scripts/test_workflow.sh
```

### Starting the Server

**Development mode (with auto-reload):**
```bash
make start-server-dev

# Or using script
bash scripts/start_server.sh
```

**Production mode (with workers):**
```bash
make start-server-prod

# Or using script
bash scripts/start_server.sh --production
```

**Manual start:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Health Check Testing

**Test all health endpoints:**
```bash
make test-health

# Or manually
python scripts/test_health.py --all
```

**Test specific component:**
```bash
python scripts/test_health.py --component database
```

**Using curl:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/database
curl http://localhost:8000/health/cache
```

### Scrape Endpoint Testing

**Test all sample queries:**
```bash
make test-scrape
```

**Test specific category:**
```bash
make test-ai-tools
make test-mutual-funds
```

**Test specific query:**
```bash
python scripts/test_scrape_endpoint.py --query "Best AI tools for coding"
```

**Using curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Best AI agents for coding",
    "timeout_seconds": 180
  }'
```

### Sample Queries

**AI Tools:**
- "Best AI agents for coding and software development"
- "AI tools for image generation with free tiers"
- "Open source AI models for natural language processing"

**Mutual Funds:**
- "Best mutual funds for beginners with low risk"
- "Top performing index funds for long-term investment"
- "Low-cost mutual funds for retirement planning"

### Response Validation

**Validate response schema:**
```bash
python scripts/validate_response_schema.py --response-file response.json
```

**Expected response structure:**
```json
{
  "status": "success",
  "timestamp": "2024-01-01T12:00:00Z",
  "query": {
    "text": "...",
    "category": "ai_tools",
    "confidence_score": 0.95
  },
  "results": {...},
  "analytics": {...},
  "execution_metadata": {...}
}
```

### Workflow Verification

The workflow consists of 4 stages:

1. **Query Processing** (1-3 seconds)
   - Query parsing and categorization
   - Confidence score calculation

2. **Web Scraping** (10-30 seconds)
   - Site discovery and content extraction
   - Robots.txt compliance

3. **AI Processing** (15-45 seconds)
   - Content cleaning and analysis
   - Summary generation
   - Structured data extraction

4. **Database Storage** (1-5 seconds)
   - Results storage in MongoDB
   - Collection updates

**Verify all stages in response:**
```bash
jq '.execution_metadata.stages_timing' response.json
```

### Cache Testing

**Test cache functionality:**
```bash
make test-cache

# Or manually
python scripts/test_scrape_endpoint.py --cache
```

**Check cache headers:**
```bash
curl -v -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}' \
  | grep -i "X-Cache-Status"
```

### Performance Benchmarks

- **Fast queries:** <30 seconds
- **Normal queries:** 30-90 seconds
- **Complex queries:** 90-180 seconds
- **Timeout threshold:** 300 seconds

### Troubleshooting

- **Server won't start:** Check environment variables with `python scripts/preflight_check.py`
- **Health checks fail:** Verify MongoDB and Gemini API connectivity
- **Scrape requests timeout:** Increase `timeout_seconds` parameter
- **No content found:** Try different query phrasing

### Documentation

- **Detailed guide:** `docs/INTEGRATION_TESTING.md`
- **Real-world testing:** `docs/REAL_WORLD_TESTING.md`
- **Demo Guide:** [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) - Step-by-step guide for team presentations
- **Known Limitations:** [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) - System constraints and known issues
- **API documentation:** http://localhost:8000/docs
- **Health checks:** http://localhost:8000/health

### Real-World Scenario Testing

The AI Web Scraper includes comprehensive real-world scenario testing that validates content quality, relevance, and AI analysis results with actual user queries.

**Quick Start:**
```bash
# Test specific user queries
make test-ai-agents
make test-mutual-funds-query

# Run comprehensive real-world tests
make test-real-world

# Performance benchmarking
make test-performance

# Edge case testing
make test-edge-cases
```

**Detailed Documentation:**
See [Real-World Testing Guide](docs/REAL_WORLD_TESTING.md) for comprehensive documentation on:
- Content quality validation
- Relevance scoring methodology
- Performance benchmarking
- Edge case testing
- Test report interpretation

### Error Recovery Testing

The AI Web Scraper includes comprehensive error recovery testing to ensure production readiness under various failure scenarios.

**Quick Start:**
```bash
# Run all error scenario tests
make test-errors

# Run middleware error tests
make test-middleware-errors

# Run end-to-end error recovery tests
make test-error-recovery

# Run all error tests
make test-all-errors
```

**Error Scenarios Tested:**

1. **Authentication Errors**
   - Invalid/missing API keys
   - Expired/revoked keys
   - Insufficient permissions

2. **Infrastructure Failures**
   - MongoDB connection failures
   - MongoDB timeouts
   - Service unavailability

3. **External API Failures**
   - Gemini API key errors
   - Quota exceeded
   - Rate limiting
   - Network errors

4. **Timeout Scenarios**
   - Query processing timeouts
   - Web scraping timeouts
   - AI processing timeouts
   - Overall workflow timeouts

5. **Validation Errors**
   - Invalid input validation
   - Configuration errors
   - Malicious input handling

6. **Graceful Degradation**
   - Partial scraping failures
   - Partial processing failures
   - Database storage failures

**Simulating Failures:**
```bash
# Simulate MongoDB failure
make simulate-mongodb-failure

# Simulate Gemini API failure
make simulate-gemini-failure

# Restore all services
make restore-services

# Run tests with simulated failures
make test-with-failures
```

**Expected Behavior:**

- **Graceful Degradation:** System continues with partial results when non-critical stages fail
- **Clear Error Messages:** All errors include specific error codes and recovery suggestions
- **Partial Results:** Completed stages return results even if later stages fail
- **Retry Guidance:** Error responses indicate whether retry is possible
- **Structured Logging:** All errors logged with context for debugging

**Detailed Documentation:**
See [Error Recovery Testing Guide](docs/ERROR_RECOVERY_TESTING.md) for comprehensive documentation on:
- Error scenario details
- Recovery suggestions
- Graceful degradation behavior
- Monitoring and alerting
- Troubleshooting guide

### Load Testing & Performance Validation

The AI Web Scraper includes comprehensive load testing infrastructure to validate concurrent request handling, rate limiting, caching, memory usage, and MongoDB connection pooling under various load scenarios.

**Quick Start:**
```bash
# Basic load test
make test-load

# Run all load test scenarios
make test-load-all

# Analyze load test results
make analyze-load-results
```

**Test Scenarios:**
- **Gradual Ramp-Up**: Tests system behavior as concurrent requests increase from 1 to 50
- **Burst Traffic**: Tests system resilience with sudden spikes of 50 concurrent requests
- **Sustained Load**: Maintains constant concurrent load for extended periods
- **Cache Validation**: Tests cache hit/miss rates and effectiveness
- **Rate Limit Validation**: Tests rate limiting enforcement and correctness
- **Connection Pool Stress**: Monitors MongoDB connection pool behavior under load

**Understanding Results:**
- Response time percentiles (p50, p90, p95, p99) indicate performance under load
- Cache hit rates show caching effectiveness
- Memory growth patterns help detect memory leaks
- Connection pool utilization indicates database connection health

**Performance Benchmarks:**
- Response time p95: < 30 seconds under normal load
- Cache hit rate: > 50% (after warm-up)
- Memory growth: < 10MB per 100 requests
- Connection pool utilization: < 80%

**Troubleshooting:**
- Rate limiting too aggressive: Increase `api_rate_limit_requests_per_minute` in config
- Cache not working: Verify `cache_enabled = True` and check cache headers
- Memory leaks: Review object lifecycle and connection management
- Connection pool exhaustion: Increase `mongodb_max_pool_size` in config

**CI/CD Integration:**
Load tests run automatically on push to main/develop, pull requests, and weekly scheduled runs. Results are compared against baselines to detect performance regressions.

**Detailed Documentation:**
See [Load Testing Guide](docs/LOAD_TESTING.md) for comprehensive documentation on:
- Test scenario details
- Metrics interpretation
- Performance benchmarks
- Troubleshooting guide
- Best practices

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Run Integration Tests
  run: make test-workflow

# Real-world scenario tests
- name: Run Real-World Tests
  run: make test-real-world
```

### Quick Start with Docker Compose

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd traycerTry
   ```

2. **Configure environment**
   ```bash
   # Copy production environment template
   cp .env.production.example .env.production
   
   # Edit with your actual values
   nano .env.production
   ```

3. **Start the application stack**
   ```bash
   # Start all services (API + MongoDB + Mongo Express)
   docker-compose up -d
   
   # View logs
   docker-compose logs -f api
   
   # Check service status
   docker-compose ps
   ```

4. **Access the application**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Mongo Express (optional): http://localhost:8081
   - Health Check: http://localhost:8000/health
   - Metrics: http://localhost:8000/api/v1/metrics

### Docker Commands

```bash
# Build the image
docker build -t traycer-api .

# Run the container
docker run -d \
  --name traycer-api \
  -p 8000:8000 \
  --env-file .env.production \
  traycer-api

# View container logs
docker logs -f traycer-api

# Stop and remove container
docker stop traycer-api && docker rm traycer-api
```

### Production Deployment

For production deployment, consider:

1. **Use a reverse proxy** (nginx/traefik) for SSL termination
2. **Set up monitoring** with Prometheus/Grafana
3. **Configure log aggregation** (ELK stack)
4. **Use external MongoDB** (MongoDB Atlas)
5. **Set up CI/CD pipeline** for automated deployments

### Kubernetes Deployment

The application includes Kubernetes-compatible health checks:

- **Liveness Probe**: `GET /live`
- **Readiness Probe**: `GET /ready`
- **Health Check**: `GET /health`

Example Kubernetes deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: traycer-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: traycer-api
  template:
    metadata:
      labels:
        app: traycer-api
    spec:
      containers:
      - name: api
        image: traycer-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: MONGODB_URL
          value: "mongodb://mongodb-service:27017"
        livenessProbe:
          httpGet:
            path: /live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## ⚙️ Environment Variables

### Development Setup

Copy `env.example` to `.env` and configure the following variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGODB_DB` | Database name | `traycer_try` |
| `GEMINI_API_KEY` | Google Gemini API key | `your_api_key_here` |
| `ENVIRONMENT` | App environment | `development` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DEBUG` | Debug mode | `true` |

### Production Configuration

For production deployment, copy `.env.production.example` to `.env.production` and configure:

#### Authentication & Security
| Variable | Description | Example |
|----------|-------------|---------|
| `API_AUTH_ENABLED` | Enable API key authentication | `true` |
| `API_KEYS` | List of valid API keys | `["prod-key-1", "prod-key-2"]` |
| `API_KEY_RATE_LIMIT_PER_MINUTE` | Rate limit per API key | `100` |
| `SECRET_KEY` | Application secret key | `your-super-secret-key` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `["https://yourdomain.com"]` |
| `TRUSTED_HOSTS` | Trusted host names | `["yourdomain.com"]` |

#### Caching & Performance
| Variable | Description | Example |
|----------|-------------|---------|
| `CACHE_ENABLED` | Enable in-memory caching | `true` |
| `CACHE_TTL_SECONDS` | Cache time-to-live | `3600` |
| `CACHE_MAX_SIZE` | Maximum cache entries | `1000` |
| `CACHE_RESPONSE_ENABLED` | Cache API responses | `true` |
| `WORKERS` | Number of worker processes | `4` |
| `MAX_CONNECTIONS` | Maximum connections | `1000` |
| `ENABLE_COMPRESSION` | Enable response compression | `true` |

#### Monitoring & Logging
| Variable | Description | Example |
|----------|-------------|---------|
| `METRICS_ENABLED` | Enable metrics collection | `true` |
| `METRICS_EXPORT_FORMAT` | Metrics format (prometheus/json) | `prometheus` |
| `LOG_FORMAT` | Log format (json/text) | `json` |
| `LOG_FILE` | Log file path | `/app/logs/app.log` |
| `LOG_MAX_BYTES` | Max log file size | `10485760` |
| `LOG_BACKUP_COUNT` | Number of backup files | `5` |

### Scraper Configuration

| Variable | Description | Default | Purpose |
|----------|-------------|---------|---------|
| `SCRAPER_CONCURRENCY` | Max concurrent requests | `5` | Control scraping load |
| `SCRAPER_REQUEST_TIMEOUT_SECONDS` | Request timeout | `20` | Prevent hanging requests |
| `SCRAPER_DELAY_SECONDS` | Delay between requests | `1.0` | Respectful scraping |
| `SCRAPER_USER_AGENT` | Bot identification | `"TrayceAI-Bot/1.0"` | Transparent bot identity |
| `SCRAPER_RESPECT_ROBOTS` | Robots.txt compliance | `true` | Ethical scraping |
| `SCRAPER_MAX_RETRIES` | Failed request retries | `3` | Handle transient failures |
| `SCRAPER_CONTENT_SIZE_LIMIT` | Max content size | `10485760` | Memory management (10MB) |

### Processing Configuration

| Variable | Description | Default | Purpose |
|----------|-------------|---------|---------|
| `PROCESSING_TIMEOUT_SECONDS` | Processing operation timeout | `60` | Prevent hanging processing |
| `PROCESSING_CONCURRENCY` | Parallel processing operations | `3` | Control processing load |
| `PROCESSING_ENABLE_AI_ANALYSIS` | AI-powered content analysis | `true` | Enable Gemini-based insights |
| `PROCESSING_ENABLE_SUMMARIZATION` | Content summarization | `true` | Generate content summaries |
| `PROCESSING_ENABLE_STRUCTURED_EXTRACTION` | Structured data extraction | `true` | Extract key information |
| `PROCESSING_ENABLE_DUPLICATE_DETECTION` | Duplicate content detection | `true` | Identify similar content |
| `SIMILARITY_THRESHOLD` | Duplicate detection sensitivity | `0.8` | Control duplicate sensitivity |
| `MIN_CONTENT_QUALITY_SCORE` | Quality filtering threshold | `0.4` | Filter low-quality content |
| `MAX_SUMMARY_LENGTH` | Summary length limit | `500` | Control summary size |
| `PROCESSING_BATCH_SIZE` | Batch processing size | `10` | Optimize processing efficiency |
| `CONTENT_PROCESSING_TIMEOUT` | Individual content timeout | `30` | Prevent hanging content processing |
| `MAX_CONCURRENT_AI_ANALYSES` | Max AI analysis concurrency | `5` | Control AI API load |
| `MAX_PROCESSING_MEMORY` | Memory threshold for batching | `512` | Memory management |
| `PROCESSING_MAX_SIMILARITY_CONTENT_PAIRS` | Max similarity pairs | `50` | Control duplicate detection scope |
| `PROCESSING_MAX_SIMILARITY_BATCH_SIZE` | Max similarity batch size | `10` | Optimize similarity analysis |

### Database Configuration

| Variable | Description | Default | Purpose |
|----------|-------------|---------|---------|
| `DATABASE_QUERY_TIMEOUT_SECONDS` | Database operation timeouts | `30` | Prevent hanging database operations |
| `DATABASE_MAX_RETRIES` | Maximum retries for failed operations | `3` | Handle transient database failures |
| `DATABASE_BATCH_SIZE` | Batch size for bulk operations | `100` | Optimize bulk database operations |
| `DATABASE_ENABLE_TEXT_SEARCH` | Enable full-text search features | `true` | Enable MongoDB text search capabilities |
| `DATABASE_CONTENT_TTL_DAYS` | Automatic content cleanup TTL | `90` | Manage storage by auto-deleting old content |
| `DATABASE_ANALYTICS_RETENTION_DAYS` | Analytics data retention period | `365` | Control analytics data storage duration |
| `DATABASE_ENABLE_CACHING` | Enable query result caching | `true` | Improve performance with result caching |
| `DATABASE_CACHE_TTL_SECONDS` | Cache expiration time | `3600` | Control cache lifetime (1 hour) |
| `DATABASE_MAX_CONTENT_SIZE_MB` | Maximum document size | `50` | Prevent oversized documents |
| `DATABASE_ENABLE_COMPRESSION` | Enable content compression | `true` | Reduce storage requirements |
| `DATABASE_INDEX_BACKGROUND` | Create indexes in background | `true` | Non-blocking index creation |
| `DATABASE_ENABLE_PROFILING` | Enable query profiling | `false` | Development query performance analysis |

## 🔧 Data Models

### ScrapedContent Schema
The application uses a comprehensive `ScrapedContent` model with the following required fields:
- `url`: Source URL of the scraped content
- `title`: Page title (optional)
- `content`: Main content text
- `content_type`: Type of content (article, product_page, documentation, etc.)
- `processing_time`: Time taken to scrape in seconds
- `content_size_bytes`: Size of scraped content in bytes
- `extraction_method`: Method used to extract content

Optional fields include:
- `author`, `publish_date`, `description`, `keywords`
- `images`, `links` (media and link information)
- `relevance_score`, `content_quality_score` (quality metrics)

### ParsedQuery Schema
Queries are processed using a `ParsedQuery` model that contains:
- `base_result`: BaseQueryResult with query text, confidence, processing time, and category
- `ai_tools_data`, `mutual_funds_data`, `general_data`: Category-specific data
- `raw_entities`, `suggestions`: Additional processing results

### Content ID Generation
For processing operations, content IDs are deterministically generated using:
```python
import hashlib
content_id = hashlib.md5(f"{content.url}|{content.title or 'no-title'}".encode()).hexdigest()
```

This ensures consistent identification across processing stages without requiring database persistence.

### Processing Configuration

The processing pipeline is highly configurable:

- **Stage Control**: Enable/disable specific processing stages
- **Quality Thresholds**: Set minimum quality scores for content filtering
- **Batch Processing**: Configure batch sizes and concurrency for efficiency
- **AI Parameters**: Control AI analysis depth and focus areas
- **Duplicate Detection**: Adjust similarity thresholds and detection strategies

**Note**: When a processing stage is disabled, the orchestrator still yields a minimal fallback object to maintain schema contracts and ensure consistent data structures throughout the pipeline.

## 🗄️ Database Integration

The application features a comprehensive MongoDB integration with advanced data management capabilities:

### Database Collections

The system uses the following MongoDB collections:

- **`queries`**: Stores parsed queries with metadata and execution results
- **`content`**: Stores scraped content with deduplication and quality metrics
- **`processed_content`**: Stores processed content with AI analysis results
- **`query_sessions`**: Tracks user sessions and analytics data
- **`analytics`**: Aggregated analytics and performance metrics
- **`migrations`**: Database schema migration history

### Data Lifecycle Management

- **Automatic Cleanup**: Old content is automatically deleted based on TTL settings
- **Analytics Retention**: Analytics data is retained for configurable periods
- **Deduplication**: Content is automatically deduplicated using content hashing
- **Compression**: Large content can be compressed to save storage space

### Indexing Strategy

The system creates comprehensive indexes for optimal performance:

- **Text Search**: Full-text search indexes on content and queries
- **Compound Indexes**: Multi-field indexes for common query patterns
- **TTL Indexes**: Automatic cleanup indexes for data lifecycle management
- **Background Creation**: Indexes are created in background to avoid blocking operations

### Database Health Monitoring

Comprehensive health check endpoints are available:

- `/health/database/collections` - Verify all collections exist and are accessible
- `/health/database/indexes` - Check index status and performance
- `/health/database/operations` - Test basic CRUD operations on all repositories

### Migration System

The application includes a robust migration system:

- **Version Control**: Track database schema versions
- **Automatic Application**: Migrations are applied automatically on startup
- **Rollback Support**: Migrations can be rolled back if needed
- **Schema Validation**: Validate database schema integrity

### Performance Optimization

- **Connection Pooling**: Optimized MongoDB connection pool settings
- **Batch Operations**: Efficient bulk operations for large datasets
- **Caching**: Query result caching for improved performance
- **Background Indexing**: Non-blocking index creation and maintenance

### Ethical Scraping Practices

The scraper is designed with ethical considerations:

- **Robots.txt Compliance**: Automatically checks and respects robots.txt files
- **Rate Limiting**: Configurable delays between requests to the same domain
- **User Agent Identification**: Clear bot identification in requests
- **Content Size Limits**: Prevents overwhelming servers with large requests
- **Respectful Delays**: Built-in politeness delays between requests

## 🏗️ Project Structure

```
traycerTry/
├── app/                    # Main application package
│   ├── __init__.py
│   ├── main.py            # FastAPI app entry point
│   ├── dependencies.py    # Shared dependencies
│   ├── core/              # Core infrastructure
│   │   ├── __init__.py
│   │   ├── config.py      # Configuration management
│   │   ├── database.py    # MongoDB connection
│   │   ├── gemini.py      # Gemini AI client
│   │   ├── cache.py       # In-memory caching layer
│   │   └── auth.py        # API key authentication
│   ├── api/               # API layer
│   │   ├── __init__.py
│   │   ├── middleware.py   # Request middleware (auth, logging, etc.)
│   │   └── routers/       # API route definitions
│   │       ├── __init__.py
│   │       ├── health.py   # Health check endpoints
│   │       ├── scrape.py   # Scraping endpoints
│   │       └── metrics.py  # Metrics and monitoring endpoints
│   ├── utils/             # Utility modules
│   │   ├── __init__.py
│   │   ├── logging.py     # Structured logging utilities
│   │   ├── metrics.py     # Metrics collection and export
│   │   └── health.py      # Health check utilities
│   ├── database/          # Database layer
│   │   ├── __init__.py
│   │   ├── models.py      # MongoDB document models
│   │   ├── indexes.py     # Index management
│   │   ├── migrations.py  # Database migrations
│   │   ├── service.py     # Database service layer
│   │   └── repositories/  # Data access layer
│   │       ├── __init__.py
│   │       ├── queries.py     # Query repository
│   │       ├── content.py     # Content repository
│   │       ├── processed.py   # Processed content repository
│   │       └── analytics.py   # Analytics repository
│   ├── agents/            # AI agent system
│   │   ├── __init__.py
│   │   ├── base.py        # Base agent class
│   │   ├── schemas.py     # Agent data models
│   │   ├── parsers.py     # Natural language parsing
│   │   ├── categorizer.py # Query categorization
│   │   └── processor.py   # Query processing workflow
│   ├── scraper/           # Web scraping module
│   │   ├── __init__.py
│   │   ├── base.py        # Base scraper agent
│   │   ├── session.py     # HTTP session management
│   │   ├── rate_limiter.py # Rate limiting system
│   │   ├── robots.py      # Robots.txt compliance
│   │   ├── discovery.py   # Site discovery agent
│   │   ├── extractor.py   # Content extraction agent
│   │   ├── orchestrator.py # Main orchestrator
│   │   └── schemas.py     # Scraper data models
│   └── processing/        # Data processing pipeline
│       ├── __init__.py
│       ├── schemas.py     # Processing data models
│       ├── cleaning.py    # Content cleaning agent
│       ├── analysis.py    # AI analysis agent
│       ├── summarization.py # Summarization agent
│       ├── extraction.py  # Structured data extractor
│       ├── duplicates.py  # Duplicate detection agent
│       ├── orchestrator.py # Processing orchestrator
│       └── prompts.py     # AI prompt templates
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── test_agents.py     # Agent tests
│   ├── test_scraper.py    # Scraper tests
│   └── test_processing.py # Processing pipeline tests
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── .env.production.example # Production environment template
├── .dockerignore          # Docker ignore rules
├── Dockerfile             # Multi-stage Docker build
├── docker-compose.yml     # Docker Compose orchestration
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## 🔐 API Authentication

The application supports API key-based authentication for secure access to endpoints.

### Authentication Setup

1. **Enable Authentication**
   ```bash
   # In your .env file
   API_AUTH_ENABLED=true
   API_KEYS=["your-api-key-1", "your-api-key-2", "your-api-key-3"]
   API_KEY_RATE_LIMIT_PER_MINUTE=100
   ```

2. **Using API Keys**
   ```bash
   # Include API key in request headers
   curl -X POST "http://localhost:8000/api/v1/scrape" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your-api-key-1" \
     -d '{"query": "Find AI tools for image generation"}'
   ```

3. **Public Endpoints** (no authentication required)
   - `GET /` - API information
   - `GET /health` - Health check
   - `GET /docs` - API documentation
   - `GET /redoc` - Alternative documentation
   - `GET /openapi.json` - OpenAPI specification

### Rate Limiting

- **Per API Key**: Configurable rate limit per minute
- **Per IP**: Fallback rate limiting for unauthenticated requests
- **Headers**: Rate limit information included in response headers

## 📊 Monitoring & Metrics

The application provides comprehensive monitoring and observability features.

### Metrics Endpoints

- **`GET /api/v1/metrics`** - Prometheus-compatible metrics export
- **`GET /api/v1/metrics/health`** - Overall system health status
- **`GET /api/v1/metrics/performance`** - Detailed performance metrics
- **`GET /api/v1/metrics/cache`** - Cache statistics and performance
- **`POST /api/v1/metrics/reset`** - Reset metrics counters (admin only)

### Available Metrics

#### API Metrics
- `api_requests_total` - Total API requests by endpoint and method
- `api_request_duration_seconds` - Request duration histogram
- `api_errors_total` - Total errors by type and endpoint
- `active_requests` - Current number of active requests

#### Cache Metrics
- `cache_operations_total` - Cache operations (hits, misses, sets)
- `cache_hit_rate` - Cache hit rate percentage
- `cache_size` - Current cache size
- `cache_evictions_total` - Total cache evictions

#### System Metrics
- `memory_usage_bytes` - Current memory usage
- `cpu_usage_percent` - CPU usage percentage
- `database_connections_active` - Active database connections

### Health Checks

#### Comprehensive Health Monitoring
- **`GET /health`** - Overall system health with detailed component status
- **`GET /live`** - Kubernetes liveness probe
- **`GET /ready`** - Kubernetes readiness probe
- **`GET /components`** - Detailed component health status
- **`GET /database`** - Database-specific health information
- **`GET /cache`** - Cache health and statistics
- **`GET /system`** - System resource health

#### Health Status Levels
- **Healthy**: All components operational
- **Degraded**: Some components have issues but service is functional
- **Unhealthy**: Critical components are down

### Structured Logging

The application uses structured JSON logging with:

- **Request Context**: Request ID, API key, user agent, IP address
- **Performance Data**: Response time, cache status, database queries
- **Error Tracking**: Detailed error information with stack traces
- **Security Events**: Authentication attempts, rate limiting events

#### Log Configuration
```bash
# Enable structured logging
LOG_FORMAT=json
LOG_FILE=/app/logs/app.log
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=5
```

## 🔌 AI Web Scraping API

The application provides a comprehensive `/scrape` API endpoint that orchestrates the complete AI web scraping workflow from natural language query to processed results.

### Main Endpoint: `POST /api/v1/scrape`

The main scraping endpoint that coordinates all three orchestrators (QueryProcessor, ScraperOrchestrator, ProcessingOrchestrator) in sequence, with database storage integration and detailed progress tracking.

#### Request Format

```json
{
  "query": "Find AI tools for image generation with free tiers",
  "processing_config": {
    "enable_ai_analysis": true,
    "enable_summarization": true,
    "max_summary_length": 300,
    "concurrency": 2
  },
  "timeout_seconds": 180,
  "store_results": true,
  "metadata": {
    "request_id": "req_12345",
    "session_id": "sess_67890"
  }
}
```

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Natural language query to process (3-1000 characters) |
| `processing_config` | object | No | Optional processing configuration overrides |
| `timeout_seconds` | integer | No | Custom timeout for request (30-600 seconds) |
| `store_results` | boolean | No | Whether to store results in database (default: true) |
| `metadata` | object | No | Optional request metadata for tracking |

#### Processing Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `timeout_seconds` | integer | 60 | Processing operation timeout (10-300) |
| `max_retries` | integer | 2 | Maximum retry attempts (0-5) |
| `concurrency` | integer | 3 | Parallel processing operations (1-10) |
| `enable_content_cleaning` | boolean | true | Enable content cleaning stage |
| `enable_ai_analysis` | boolean | true | Enable AI analysis stage |
| `enable_summarization` | boolean | true | Enable summarization stage |
| `enable_structured_extraction` | boolean | true | Enable structured data extraction |
| `enable_duplicate_detection` | boolean | true | Enable duplicate detection |
| `similarity_threshold` | float | 0.8 | Duplicate detection sensitivity (0.5-0.95) |
| `min_content_quality_score` | float | 0.4 | Minimum quality score for processing (0.0-1.0) |
| `max_summary_length` | integer | 500 | Maximum summary length (100-2000) |
| `batch_size` | integer | 10 | Batch processing size (1-50) |

#### Response Format

```json
{
  "status": "success",
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_12345",
  "query": {
    "text": "Find AI tools for image generation",
    "category": "ai_tools",
    "confidence_score": 0.95
  },
  "results": {
    "total_items": 12,
    "processed_items": 10,
    "success_rate": 0.83,
    "processed_contents": [
      {
        "original_content": {
          "url": "https://example.com/ai-tool",
          "title": "Best AI Image Generator",
          "content": "...",
          "content_type": "article",
          "relevance_score": 0.9
        },
        "cleaned_content": "...",
        "summary": {
          "executive_summary": "AI image generation tool overview",
          "key_points": ["Various features", "Pricing models"],
          "detailed_summary": "...",
          "main_topics": ["AI", "Image Generation"],
          "sentiment": "positive",
          "confidence_score": 0.92
        },
        "structured_data": {
          "entities": [...],
          "key_value_pairs": {...},
          "categories": [...]
        },
        "ai_insights": {
          "themes": ["AI Technology", "Image Generation"],
          "relevance_score": 0.87,
          "quality_metrics": {...},
          "recommendations": [...],
          "credibility_indicators": {...},
          "information_accuracy": 0.88,
          "source_reliability": 0.85
        }
      }
    ]
  },
  // Note: All timing values are in seconds, except execution_time_ms which is in milliseconds
  "analytics": {
    "pages_scraped": 15,
    "processing_time_breakdown": {
      "query_processing": 1.2,
      "web_scraping": 28.8,
      "ai_processing": 14.4,
      "database_storage": 0.8
    },
    "quality_metrics": {...}
  },
  "execution_metadata": {
    "execution_time_ms": 45230.5,
    "stages_timing": {
      "query_processing": 1.2,
      "web_scraping": 28.8,
      "ai_processing": 14.4,
      "database_storage": 0.8
    },
    "performance_metrics": {...}
  }
}
```

#### Error Response Format

```json
{
  "status": "error",
  "timestamp": "2024-01-01T12:00:00Z",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "http_status": 400,
    "details": [
      {
        "error_code": "VALIDATION_ERROR",
        "message": "Query text is required and cannot be empty",
        "context": {"field": "query"},
        "recovery_suggestions": ["Provide a non-empty query string"]
      }
    ]
  },
  "execution_metadata": {...}
}
```

### Health Check: `GET /api/v1/scrape/health`

Health check endpoint for the scrape workflow that tests all components.

#### Response Format

```json
{
  "status": "healthy",
  "components": {
    "query_processor": {"status": "healthy"},
    "scraper_orchestrator": {"status": "healthy"},
    "processing_orchestrator": {"status": "healthy"},
    "database_service": {"status": "healthy"}
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Usage Examples

#### Basic Query (with authentication)
```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-1" \
  -d '{
    "query": "Find the best AI tools for image generation"
  }'
```

#### Advanced Query with Configuration
```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-1" \
  -d '{
    "query": "Find mutual funds with low expense ratios for retirement",
    "processing_config": {
      "enable_ai_analysis": true,
      "enable_summarization": true,
      "max_summary_length": 300,
      "concurrency": 2,
      "similarity_threshold": 0.85
    },
    "timeout_seconds": 240,
    "store_results": true,
    "metadata": {
      "session_id": "user_session_123"
    }
  }'
```

#### Python Client Example
```python
import requests
import json

def scrape_content(query, api_key, config=None):
    url = "http://localhost:8000/api/v1/scrape"
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    
    payload = {
        "query": query,
        "store_results": True
    }
    
    if config:
        payload["processing_config"] = config
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# Example usage
result = scrape_content(
    "Find AI tools for code generation",
    api_key="your-api-key-1",
    config={
        "enable_ai_analysis": True,
        "max_summary_length": 200,
        "concurrency": 3
    }
)

if result:
    print(f"Found {result['results']['total_items']} items")
    for content in result['results']['processed_contents']:
        print(f"- {content['original_content']['title']}")
        print(f"  Summary: {content['summary']['executive_summary']}")
```

### Error Codes and Recovery

| Error Code | HTTP Status | Description | Recovery Suggestions |
|------------|-------------|-------------|---------------------|
| `VALIDATION_ERROR` | 400 | Invalid request format or parameters | Check request format and parameter constraints |
| `WORKFLOW_TIMEOUT` | 500 | Processing timed out | Increase timeout_seconds or simplify query |
| `QUERY_PROCESSING_ERROR` | 500 | Failed to process natural language query | Rephrase query or check for special characters |
| `SCRAPING_ERROR` | 500 | Web scraping failed | Check target website accessibility, retry request |
| `NO_CONTENT_FOUND` | 500 | No relevant content found for query | Broaden search terms or try different keywords |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests | Wait before retrying, check rate limits |
| `INTERNAL_ERROR` | 500 | Unexpected server error | Contact support if problem persists |

### Rate Limiting and Usage Guidelines

- **Default Rate Limit**: 60 requests per minute per IP
- **Request Timeout**: Maximum 600 seconds (10 minutes)
- **Query Length**: 3-1000 characters
- **Results Limit**: Maximum 50 results per request
- **Concurrent Processing**: Configurable up to 10 concurrent operations

### Performance Considerations

- **Batch Processing**: Use appropriate batch sizes (5-20) for optimal performance
- **Concurrency**: Balance concurrency settings with available resources
- **Timeout Management**: Set realistic timeouts based on query complexity
- **Quality Filtering**: Use quality thresholds to focus on high-value content
- **Caching**: Results are automatically cached when database storage is enabled

### Integration Examples

#### JavaScript/Node.js

```javascript
const axios = require('axios');

async function scrapeContent(query, apiKey, config = {}) {
  try {
    const response = await axios.post('http://localhost:8000/api/v1/scrape', {
      query: query,
      processing_config: config,
      store_results: true
    }, {
      headers: {
        'X-API-Key': apiKey
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Scraping failed:', error.response?.data || error.message);
    return null;
  }
}

// Usage
scrapeContent('Find AI tools for data analysis', 'your-api-key-1', {
  enable_ai_analysis: true,
  max_summary_length: 250
}).then(result => {
  if (result) {
    console.log(`Processing completed in ${result.execution_metadata.execution_time_ms}ms`);
    console.log(`Found ${result.results.total_items} items with ${result.results.success_rate * 100}% success rate`);
  }
});
```

## 🧪 Development

### Code Quality Tools

```bash
# Format code
black app/

# Sort imports
isort app/

# Lint code
flake8 app/

# Run tests
pytest
```

### Adding New Features

1. **Create new router** in `app/api/routers/`
2. **Add dependencies** in `app/dependencies.py` if needed
3. **Include router** in `app/main.py`
4. **Update tests** and documentation

### Scraper Development

1. **Add new extraction strategies** in `app/scraper/extractor.py`
2. **Extend discovery patterns** in `app/scraper/discovery.py`
3. **Configure rate limiting** in `app/scraper/rate_limiter.py`
4. **Update schemas** in `app/scraper/schemas.py`

## 🔒 Security Considerations

- Never commit `.env` files to version control
- Use strong, unique API keys
- Implement proper authentication for production
- Validate all input data
- Use HTTPS in production
- Respect website terms of service when scraping

## 🚧 Troubleshooting

### Quick Troubleshooting

For common issues, try these validation commands:

```bash
# Check environment configuration
python scripts/validate_env.py

# Test database and API connections
python scripts/test_connections.py

# Run comprehensive diagnostics
python scripts/preflight_check.py --verbose

# Fix common configuration issues
python scripts/fix_env.py
```

### Common Issues

1. **MongoDB Connection Failed**
   - Verify MongoDB is running
   - Check connection string in `.env`
   - Ensure network access to MongoDB instance
   - Run: `python scripts/test_connections.py --mongodb-only`

2. **Gemini API Errors**
   - Verify API key is correct
   - Check API quota and billing
   - Ensure internet connectivity
   - Run: `python scripts/test_connections.py --gemini-only`

3. **Environment Configuration Issues**
   - Run: `python scripts/validate_env.py`
   - Fix issues with: `python scripts/fix_env.py`
   - Check: [Environment Setup Guide](docs/ENVIRONMENT_SETUP.md#troubleshooting)

4. **Scraper Issues**
   - Check robots.txt compliance settings
   - Verify rate limiting configuration
   - Monitor HTTP session health
   - Check content size limits

5. **Import Errors**
   - Verify virtual environment is activated
   - Check all dependencies are installed
   - Verify Python path
   - Run: `python scripts/preflight_check.py --skip-connections`

### Scraper-Specific Issues

1. **Rate Limited by Websites**
   - Increase `SCRAPER_DELAY_SECONDS`
   - Reduce `SCRAPER_CONCURRENCY`
   - Check robots.txt for crawl-delay directives

2. **Content Extraction Failures**
   - Verify HTML parsing with BeautifulSoup
   - Check fallback extraction strategies
   - Monitor content size limits

3. **Discovery Agent Issues**
   - Verify Gemini API connectivity
   - Check domain pattern configuration
   - Monitor relevance score thresholds

### Processing Pipeline Issues

1. **AI Analysis Failures**
   - Verify Gemini API connectivity and quota
   - Check processing timeout settings
   - Monitor API response parsing
   - Review prompt templates for clarity

2. **Content Quality Filtering**
   - Adjust `MIN_CONTENT_QUALITY_SCORE` threshold
   - Review quality calculation algorithms
   - Check content cleaning effectiveness
   - Monitor AI analysis confidence scores

3. **Duplicate Detection Issues**
   - Adjust `SIMILARITY_THRESHOLD` sensitivity
   - Check fingerprint generation algorithms
   - Monitor AI similarity analysis performance
   - Review duplicate grouping logic

4. **Processing Performance**
   - Optimize `PROCESSING_BATCH_SIZE` and `PROCESSING_CONCURRENCY`
   - Monitor individual agent performance
   - Check memory usage for large content sets
   - Review timeout and retry configurations

### Database Issues

1. **Database Connection Problems**
   - Verify MongoDB is running and accessible
   - Check `MONGODB_URI` connection string format
   - Ensure network connectivity to MongoDB instance
   - Verify authentication credentials if required
   - Check MongoDB connection pool settings

2. **Index Creation Issues**
   - Monitor index creation progress in MongoDB logs
   - Check available disk space for index storage
   - Verify `DATABASE_INDEX_BACKGROUND` setting
   - Review index creation timeout settings
   - Check for conflicting index definitions

3. **Performance Issues**
   - Monitor database query performance using health endpoints
   - Check index usage with MongoDB profiler
   - Optimize `DATABASE_BATCH_SIZE` for bulk operations
   - Review `DATABASE_QUERY_TIMEOUT_SECONDS` settings
   - Monitor connection pool utilization

4. **Migration Problems**
   - Check migration history in `migrations` collection
   - Verify migration version consistency
   - Review migration rollback procedures
   - Check for data corruption during migrations
   - Monitor migration execution logs

5. **Data Lifecycle Issues**
   - Verify TTL index configuration
   - Check `DATABASE_CONTENT_TTL_DAYS` settings
   - Monitor automatic cleanup operations
   - Review analytics data retention policies
   - Check for orphaned documents

## 📖 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Motor MongoDB Driver](https://motor.readthedocs.io/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [MongoDB Indexing Best Practices](https://docs.mongodb.com/manual/core/indexes/)
- [MongoDB Performance Optimization](https://docs.mongodb.com/manual/core/performance/)
- [Google Gemini API](https://ai.google.dev/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/)
- [aiohttp Documentation](https://docs.aiohttp.org/)
- [Web Scraping Best Practices](https://www.scraperapi.com/blog/web-scraping-best-practices/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Scraper Contributions

When contributing to the scraper module:

- Follow ethical scraping practices
- Add comprehensive tests for new features
- Document rate limiting and robots.txt considerations
- Ensure backward compatibility with existing configurations

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation links above
- Review the troubleshooting section
- For scraping-specific issues, check the ethical practices section

---

**Happy Coding and Ethical Scraping! 🎉🕷️**
