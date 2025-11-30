# Load Testing & Performance Validation Guide

## Introduction

This document provides a comprehensive guide for load testing and performance validation of the AI Web Scraper API. The load testing suite validates system behavior under various concurrent load scenarios, including rate limiting, caching, memory usage, and MongoDB connection pooling.

### Overview

The load testing suite validates:
- Concurrent request handling at various concurrency levels
- Rate limiting enforcement and correctness
- Cache hit/miss rates and effectiveness
- Memory usage and potential memory leaks
- MongoDB connection pool behavior under load
- Response time percentiles and performance degradation

### Prerequisites

- Python 3.8+
- MongoDB (running locally or accessible)
- Google Gemini API key
- All project dependencies installed (`pip install -r requirements.txt`)
- FastAPI server running and accessible

### Estimated Time

Complete load test suite execution: **10-30 minutes** (depending on scenarios)

## Quick Start

Run a basic load test with default settings:

```bash
make test-load
```

Run all load test scenarios:

```bash
make test-load-all
```

## Test Scenarios

### 1. Gradual Ramp-Up

Gradually increases concurrent requests from 1 to 50 to observe system behavior under increasing load.

```bash
make test-load-ramp
# or
python scripts/test_load_performance.py --ramp-up --concurrency 50 --verbose
```

**What it tests:**
- System stability as load increases
- Response time degradation under increasing load
- Memory usage trends
- Connection pool utilization

**Expected behavior:**
- Response times may increase gradually with concurrency
- Memory usage should stabilize (no leaks)
- Connection pool should handle load without saturation

### 2. Burst Traffic

Sends a sudden spike of 50 concurrent requests simultaneously to test system resilience.

```bash
make test-load-burst
# or
python scripts/test_load_performance.py --burst --concurrency 50 --verbose
```

**What it tests:**
- System response to sudden traffic spikes
- Rate limiting under burst conditions
- Cache behavior under concurrent requests
- Error handling under stress

**Expected behavior:**
- Some requests may be rate limited (429)
- Response times may spike initially
- System should recover quickly

### 3. Sustained Load

Maintains a constant level of concurrent requests for an extended period (default: 2 minutes).

```bash
make test-load-sustained
# or
python scripts/test_load_performance.py --sustained --concurrency 20 --duration 120 --verbose
```

**What it tests:**
- System stability under sustained load
- Memory leak detection
- Connection pool behavior over time
- Performance consistency

**Expected behavior:**
- Stable response times throughout test
- No memory growth over time
- Consistent cache hit rates

### 4. Cache Validation

Tests cache behavior by sending identical requests and measuring hit rates.

```bash
make test-cache-performance
# or
python scripts/test_load_performance.py --cache-test --verbose
```

**What it tests:**
- Cache hit/miss rates
- Cache TTL expiration
- Cache performance impact (time saved)
- Cache header validation

**Expected behavior:**
- First request: MISS
- Subsequent requests: HIT
- Cache hits should be significantly faster

### 5. Rate Limit Validation

Tests rate limiting enforcement by exceeding configured limits.

```bash
make test-rate-limits
# or
python scripts/test_load_performance.py --rate-limit-test --verbose
```

**What it tests:**
- Rate limit enforcement (429 responses)
- Rate limit header correctness
- Rate limit recovery after expiration
- Authenticated vs unauthenticated limits

**Expected behavior:**
- Requests exceeding limit should return 429
- Correct rate limit headers in responses
- Rate limit resets after 60 seconds

### 6. Connection Pool Stress

Monitors MongoDB connection pool behavior under concurrent load.

```bash
make test-connection-pool
# or
python scripts/test_load_performance.py --sustained --concurrency 20 --verbose
```

**What it tests:**
- Connection pool configuration (max_pool_size)
- Pool saturation detection (if utilization data is available)
- Connection pool size recommendations

**Expected behavior:**
- Pool configuration should be appropriate for load
- Note: Motor/pymongo does not expose real-time connection counts, so utilization_percentage may be None
- Monitor for connection pool errors instead of relying on utilization metrics

## Running Load Tests

### Command-Line Usage

Basic load test:

```bash
python scripts/test_load_performance.py --concurrency 20 --duration 60
```

With JSON output:

```bash
python scripts/test_load_performance.py --concurrency 20 --json
```

Save results to file:

```bash
python scripts/test_load_performance.py --all --save-results --verbose
```

### Arguments

- `--url`: Base API URL (default: http://localhost:8000)
- `--api-key`: API key for authentication
- `--concurrency`: Number of concurrent requests (default: 20)
- `--duration`: Test duration in seconds (default: 60)
- `--ramp-up`: Run gradual ramp-up test
- `--burst`: Run burst traffic test
- `--sustained`: Run sustained load test
- `--cache-test`: Run cache behavior test
- `--rate-limit-test`: Run rate limit validation test
- `--all`: Run all test scenarios
- `--json`: Output results in JSON format
- `--save-results`: Save results to file
- `--verbose`: Show detailed output

### Makefile Commands

```bash
make test-load              # Basic load test
make test-load-ramp         # Gradual ramp-up test
make test-load-burst        # Burst traffic test
make test-load-sustained    # Sustained load test
make test-cache-performance # Cache validation
make test-rate-limits       # Rate limit validation
make test-connection-pool  # Connection pool stress test
make test-load-all          # Run all scenarios
make analyze-load-results   # Analyze saved results
```

## Understanding Results

### Metrics Explained

**Response Times:**
- `min`: Fastest response time
- `max`: Slowest response time
- `avg`: Average response time
- `p50`: Median response time (50th percentile)
- `p90`: 90th percentile response time
- `p95`: 95th percentile response time
- `p99`: 99th percentile response time

**Cache Metrics:**
- `hits`: Number of cache hits
- `misses`: Number of cache misses
- `hit_rate`: Percentage of requests served from cache
- `time_saved`: Total time saved by cache

**Rate Limiting:**
- `rate_limit_hits`: Number of 429 responses
- `rate_limit_percentage`: Percentage of requests rate limited

**Memory:**
- `start_memory_mb`: Memory usage at test start
- `end_memory_mb`: Memory usage at test end
- `peak_memory_mb`: Peak memory usage during test
- `memory_growth_mb`: Memory growth during test

**Connection Pool:**
- `max_pool_size`: Maximum pool size (configuration)
- `in_use`: Connections currently in use (may be None if not available)
- `available`: Available connections (may be None if not available)
- `utilization_percentage`: Pool utilization percentage (None if in_use cannot be determined)
- `approximate`: Flag indicating if values are approximate or unavailable

### Interpreting Reports

**Good Performance Indicators:**
- Response time p95 < 10 seconds
- Cache hit rate > 50%
- Memory growth < 10MB per 100 requests
- Connection pool utilization < 80%
- Success rate > 95%

**Warning Signs:**
- Response time p95 > 30 seconds
- Cache hit rate < 30%
- Memory growth > 50MB per 100 requests
- Connection pool utilization > 90%
- Success rate < 80%

### Analyzing Results

Generate analysis report from saved results:

```bash
python scripts/analyze_load_test_results.py \
    --results-file test_results/load_test_20240101_120000.json \
    --format markdown \
    --output analysis_report.md
```

Compare against baseline:

```bash
python scripts/analyze_load_test_results.py \
    --results-file test_results/load_test_current.json \
    --baseline-file test_results/baseline_load_test.json \
    --format markdown
```

## Performance Benchmarks

### Expected Baselines

**Response Times (under normal load):**
- p50: < 5 seconds
- p90: < 15 seconds
- p95: < 20 seconds
- p99: < 30 seconds

**Cache Performance:**
- Hit rate: > 50% (after warm-up)
- Cache hit speedup: > 2x faster than miss

**Memory Usage:**
- Start: < 200MB
- Peak: < 500MB
- Growth: < 10MB per 100 requests

**Connection Pool:**
- Max pool size: 10 (default, configuration value)
- Note: Real-time utilization cannot be determined as Motor/pymongo doesn't expose connection counts

### Acceptable Thresholds

- **Response Time p95**: < 30 seconds
- **Success Rate**: > 90%
- **Cache Hit Rate**: > 40%
- **Memory Growth**: < 20MB per 100 requests
- **Connection Pool**: No connection errors (utilization metrics may be unavailable)

## Troubleshooting

### Rate Limiting Too Aggressive

**Symptoms:**
- High rate limit hit percentage (>20%)
- Legitimate requests being blocked

**Solutions:**
- Increase `api_rate_limit_requests_per_minute` in config
- Use API key authentication for higher limits
- Review rate limiting implementation

### Cache Not Working

**Symptoms:**
- Cache hit rate = 0%
- All requests show MISS

**Solutions:**
- Verify `cache_enabled = True` in config
- Check cache TTL settings
- Verify cache key generation
- Check cache headers in responses

### Memory Leaks

**Symptoms:**
- Memory growth > 50MB per 100 requests
- Memory continuously increasing

**Solutions:**
- Review object lifecycle management
- Check for unclosed connections/resources
- Enable memory profiling
- Review cache eviction policies

### Connection Pool Exhaustion

**Symptoms:**
- MongoDB connection errors
- Timeout errors when accessing database
- Note: Real-time pool utilization metrics are not available from Motor/pymongo

**Solutions:**
- Increase `mongodb_max_pool_size` in config
- Review connection pool settings
- Check for connection leaks (unclosed connections)
- Optimize database queries
- Monitor for connection errors in logs rather than relying on utilization metrics

### Slow Responses Under Load

**Symptoms:**
- Response times increase significantly with concurrency
- p95 > 30 seconds

**Solutions:**
- Review database query performance
- Check for resource contention
- Optimize processing pipeline
- Consider horizontal scaling

## Best Practices

### When to Run Load Tests

- Before major releases
- After performance-related changes
- When adding new features that affect performance
- Regularly (weekly/monthly) for baseline tracking
- After infrastructure changes

### How to Interpret Results

1. **Compare against baselines**: Track performance over time
2. **Focus on percentiles**: p95/p99 are more important than averages
3. **Look for trends**: Gradual degradation indicates issues
4. **Consider context**: Response times depend on query complexity
5. **Monitor multiple metrics**: Don't focus on just one metric

### Setting Realistic Expectations

- Response times vary by query complexity
- Cache effectiveness depends on query patterns
- Memory usage scales with concurrent requests
- Connection pool needs depend on database load

### Optimizing Based on Results

1. **Identify bottlenecks**: Use percentiles to find slow operations
2. **Optimize cache**: Increase TTL or size if hit rate is low
3. **Tune connection pool**: Adjust size based on observed errors and load patterns (utilization metrics may be unavailable)
4. **Review memory**: Address leaks if growth is excessive
5. **Optimize queries**: Improve database performance if needed

## Integration with CI/CD

### GitHub Actions

Load tests run automatically on:
- Push to main/develop branches (if relevant files changed)
- Pull requests to main/develop
- Manual dispatch (workflow_dispatch)
- Scheduled runs (weekly on Sundays at 2 AM UTC)

### Automated Performance Regression Detection

The CI/CD pipeline:
1. Runs load tests on each PR
2. Compares results against baseline
3. Fails if critical regressions detected (>20% slower)
4. Posts results as PR comments
5. Uploads detailed reports as artifacts

### Baseline Management

- Baselines are stored in `test_results/baseline_*.json`
- Updated automatically on main branch if no regressions
- Used for comparison in PR checks
- Archived for historical tracking

## Advanced Usage

### Custom Test Scenarios

Create custom scenarios by modifying `test_load_performance.py`:

```python
async def custom_scenario(tester):
    # Your custom test logic
    pass
```

### Baseline Comparison

Establish baseline:

```bash
python scripts/test_load_performance.py --all --save-results
cp test_results/load_test_*.json test_results/baseline_load_test.json
```

Compare against baseline:

```bash
python scripts/analyze_load_test_results.py \
    --results-file test_results/load_test_current.json \
    --baseline-file test_results/baseline_load_test.json
```

### Performance Profiling

Enable detailed profiling:

```bash
python scripts/test_load_performance.py --all --verbose --save-results
```

Review detailed metrics in saved JSON files.

## Additional Resources

- [Integration Testing Guide](INTEGRATION_TESTING.md)
- [Real-World Testing Guide](REAL_WORLD_TESTING.md)
- [Performance Benchmarking](scripts/utils/performance_benchmarker.py)
- [API Documentation](../README.md)

