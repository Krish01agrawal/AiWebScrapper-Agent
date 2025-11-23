# Real-World Scenario Testing

## Overview

Real-world scenario testing validates the AI web scraper system with actual user queries, verifying that scraped content is relevant, AI analysis provides meaningful insights, and performance meets acceptable thresholds. Unlike unit and integration tests that focus on endpoint functionality and schema compliance, real-world tests validate the complete workflow with deep content quality checks.

### Purpose

- Validate content discovery and extraction quality
- Verify AI analysis provides meaningful insights
- Test edge cases comprehensively
- Benchmark performance against acceptable limits
- Ensure system works with actual user queries

### When to Run

- Before major releases
- After significant code changes
- As part of CI/CD pipeline
- For performance regression detection
- When validating new query categories

## Test Categories

### AI Tools Queries

Tests queries related to AI tools, coding assistants, and software development tools.

**Examples:**
- "best AI agents for coding"
- "AI tools for image generation"
- "open source LLMs"

**Expected Results:**
- At least 70% of scraped URLs should be relevant to AI tools domain
- Themes should include query keywords
- Confidence scores >0.7
- At least 3 entities extracted per content item

**Validation Criteria:**
- URL relevance: domains like github.com, huggingface.co, openai.com
- Title relevance: keywords like "AI", "agent", "coding"
- Content relevance: keyword density >0.05
- AI insights: themes match query, confidence >0.7

### Mutual Funds Queries

Tests queries related to mutual funds, investments, and financial planning.

**Examples:**
- "best mutual funds for beginners"
- "low-risk index funds"
- "retirement planning funds"

**Expected Results:**
- At least 70% of scraped URLs should be relevant to finance domain
- Themes should include query keywords
- Confidence scores >0.7
- At least 3 entities extracted per content item

**Validation Criteria:**
- URL relevance: domains like morningstar.com, moneycontrol.com, valueresearchonline.com
- Title relevance: keywords like "fund", "NAV", "return", "equity"
- Content relevance: keyword density >0.05
- AI insights: themes match query, confidence >0.7

### Edge Cases

Comprehensive edge case testing to ensure system robustness.

**Test Cases:**
1. **Empty Query**: Should return 400 validation error
2. **Long Query (1000 chars)**: Should handle or return validation error
3. **Special Characters**: Should handle @#$%^&*() characters
4. **Ambiguous Queries**: Multi-domain queries like "best tools for coding and investing"
5. **Non-English Queries**: Test internationalization support

**Validation Criteria:**
- System should handle edge cases gracefully
- Appropriate error messages for invalid inputs
- No crashes or unexpected behavior

### Performance Tests

Validates response times against configurable thresholds.

**Timing Thresholds:**
- Query Processing: <5 seconds
- Web Scraping: <120 seconds
- AI Processing: <60 seconds
- Database Storage: <10 seconds
- Total Execution: <300 seconds

**Performance Categories:**
- **EXCELLENT**: <50% of threshold
- **GOOD**: 50-80% of threshold
- **ACCEPTABLE**: 80-100% of threshold
- **SLOW**: 100-120% of threshold (warning)
- **CRITICAL**: >120% of threshold (failure)

## Running Tests

### Command-Line Usage

**Test specific query:**
```bash
python scripts/test_real_world_scenarios.py --query "best AI agents for coding" --verbose
```

**Test all queries in category:**
```bash
python scripts/test_real_world_scenarios.py --category ai_tools --verbose
```

**Run comprehensive test suite:**
```bash
python scripts/test_real_world_scenarios.py --all --save-report --verbose
```

**Performance benchmarking:**
```bash
python scripts/test_real_world_scenarios.py --performance --verbose
```

**Edge case testing:**
```bash
python scripts/test_real_world_scenarios.py --edge-cases --verbose
```

**JSON output:**
```bash
python scripts/test_real_world_scenarios.py --all --json --save-report
```

### Make Targets

**Quick test commands:**
```bash
# Test specific user queries
make test-ai-agents
make test-mutual-funds

# Run comprehensive real-world tests
make test-real-world

# Performance benchmarking
make test-performance

# Edge case testing
make test-edge-cases
```

**JSON output:**
```bash
make test-real-world-json
make test-performance-json
```

### CI/CD Integration

Real-world tests are included in the CI/CD pipeline via GitHub Actions workflow (`.github/workflows/real-world-tests.yml`). Tests run on:
- Push to main/develop branches
- Pull requests
- Daily schedule (midnight)
- Manual trigger (workflow_dispatch)

## Content Quality Validation

### Relevance Scoring Methodology

Content relevance is scored on three dimensions:

1. **URL Relevance (30% weight)**
   - Domain matching against category-specific domains
   - Partial domain matches
   - Category-specific subdomain detection

2. **Title Relevance (30% weight)**
   - Query keyword matching in title
   - Category-specific keyword matching
   - Match count scoring

3. **Content Relevance (40% weight)**
   - Keyword density calculation
   - Query keyword occurrences
   - Category-specific keyword occurrences

**Overall Relevance Score:**
- 0.8+: Highly relevant
- 0.5-0.7: Moderately relevant
- <0.5: Low relevance

### Domain-Specific Validation Rules

**AI Tools:**
- Relevant domains: github.com, huggingface.co, openai.com, anthropic.com, replicate.com
- Keywords: AI, agent, model, LLM, neural, machine learning, coding, development

**Mutual Funds:**
- Relevant domains: morningstar.com, moneycontrol.com, valueresearchonline.com, etmoney.com
- Keywords: fund, NAV, return, equity, debt, SIP, investment, portfolio

### AI Analysis Quality Checks

**Theme Validation:**
- Themes should include query keywords
- At least 2 themes per content item
- Themes should be relevant to query category

**Confidence Scores:**
- Confidence score >0.5 (minimum)
- Confidence score >0.7 (preferred)
- Relevance score >0.7 (preferred)

**Recommendations:**
- At least 2 actionable recommendations
- Recommendations should be relevant to query

### Structured Data Validation

**Entity Extraction:**
- At least 3 entities per content item
- Entities should be relevant to category
- Entity types should match category (e.g., "product", "company" for AI tools)

**Key-Value Pairs:**
- At least 3 meaningful key-value pairs
- Values should not be empty or generic
- Confidence scores >0.5 for extracted data

## Performance Benchmarking

### Acceptable Time Limits

Default thresholds from `app/core/config.py`:

| Stage | Threshold | Warning (80%) | Critical (100%) |
|-------|-----------|---------------|-----------------|
| Query Processing | 5s | 4s | 5s |
| Web Scraping | 120s | 96s | 120s |
| AI Processing | 60s | 48s | 60s |
| Database Storage | 10s | 8s | 10s |
| Total Execution | 300s | 240s | 300s |

### Performance Categories

- **EXCELLENT**: <50% of threshold - Optimal performance
- **GOOD**: 50-80% of threshold - Acceptable performance
- **ACCEPTABLE**: 80-100% of threshold - Within limits but approaching threshold
- **SLOW**: 100-120% of threshold - Warning, exceeds threshold
- **CRITICAL**: >120% of threshold - Failure, significantly exceeds threshold

### Optimization Recommendations

The benchmarker provides recommendations when:
- Stages exceed 80% of threshold
- Total execution time approaches limit
- Multiple stages are slow
- Performance regressions detected

### Baseline Comparison

Compare current performance against baseline:
```python
comparison = benchmarker.compare_against_baseline(current_timing, baseline_timing)
```

Identifies:
- Regressions (>20% slower)
- Improvements (>20% faster)
- Percentage differences per stage

## Test Reports

### Report Structure

Test reports are saved to `test_results/real_world_scenarios_{timestamp}.json` with the following structure:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "base_url": "http://localhost:8000",
  "test_categories": {
    "ai_tools": {
      "queries": [...],
      "passed": 4,
      "total": 5
    },
    "mutual_funds": {
      "queries": [...],
      "passed": 3,
      "total": 5
    }
  },
  "edge_cases": {...},
  "summary": {
    "total_tests": 15,
    "passed": 12,
    "failed": 3,
    "success_rate": 80.0
  }
}
```

### Key Metrics to Monitor

1. **Success Rate**: Overall test pass rate (target: >80%)
2. **Content Relevance**: Average relevance scores (target: >0.7)
3. **AI Quality**: Average AI analysis quality (target: >0.7)
4. **Structured Data**: Entity extraction quality (target: >0.7)
5. **Performance**: Stage timing vs thresholds (target: all stages <80% of threshold)

### Troubleshooting Common Issues

**Low Content Relevance:**
- Check if discovered sites match query category
- Verify domain relevance rules are correct
- Review query categorization accuracy

**Low AI Analysis Quality:**
- Verify Gemini API connectivity and quota
- Check AI insights confidence scores
- Review theme extraction logic

**Performance Issues:**
- Check network latency
- Review scraper concurrency settings
- Verify database connection pool
- Check AI processing batch size

**Structured Data Issues:**
- Verify entity extraction logic
- Check confidence score thresholds
- Review key-value pair extraction

## Extending Tests

### Adding New Query Categories

1. Add category to `REAL_WORLD_QUERIES` in `test_real_world_scenarios.py`
2. Add relevant domains to `ContentQualityAnalyzer`
3. Add category-specific keywords
4. Update validation rules

### Customizing Validation Rules

Modify `ContentQualityAnalyzer` methods:
- `analyze_url_relevance()`: Add domain patterns
- `analyze_title_relevance()`: Adjust keyword matching
- `analyze_content_snippet()`: Change keyword density thresholds

### Adding New Edge Cases

Add to `EDGE_CASE_QUERIES` in `test_real_world_scenarios.py`:
```python
EDGE_CASE_QUERIES = {
    "new_case": "test query here"
}
```

### Integrating with Monitoring Systems

Export test results to monitoring systems:
```python
# Example: Export to Prometheus
from prometheus_client import Counter, Gauge

test_results_counter = Counter('real_world_tests_total', 'Total real-world tests')
test_success_gauge = Gauge('real_world_tests_success_rate', 'Success rate')
```

## Best Practices

### Test Data Management

- Use consistent test queries for regression detection
- Maintain baseline performance metrics
- Archive test results for historical analysis
- Clean up old test result files periodically

### Handling Flaky Tests

- Retry failed tests automatically
- Identify and skip known flaky tests
- Monitor test stability over time
- Investigate root causes of flakiness

### Performance Regression Detection

- Compare against baseline on each run
- Alert on >20% performance degradation
- Track performance trends over time
- Set up automated alerts for regressions

### Continuous Improvement

- Review test results regularly
- Update validation thresholds based on real-world performance
- Refine relevance scoring algorithms
- Optimize slow stages identified in reports

## Example Reports

### Successful Test Run

```
REAL-WORLD SCENARIO TEST SUITE
============================================================

1. Testing AI Tools Queries
------------------------------------------------------------
  ✓ PASSED: best AI agents for coding
  ✓ PASSED: AI tools for image generation
  ✓ PASSED: open source LLMs

2. Testing Mutual Funds Queries
------------------------------------------------------------
  ✓ PASSED: best mutual funds for beginners
  ✓ PASSED: low-risk index funds

3. Testing Edge Cases
------------------------------------------------------------
  ✓ PASSED: empty query
  ✓ PASSED: long query
  ✓ PASSED: special characters

TEST SUMMARY
============================================================
Total Tests: 10
Passed: 10
Failed: 0
Success Rate: 100.0%
```

### Performance Report

```
Overall Status: PASS
Total Execution Time: 45.23s

Stage Performance:
  query_processing: 1.2s (EXCELLENT)
  web_scraping: 28.8s (GOOD)
  ai_processing: 14.4s (GOOD)
  database_storage: 0.8s (EXCELLENT)
```

## Additional Resources

- **Integration Testing Guide**: `docs/INTEGRATION_TESTING.md`
- **Test Results**: `docs/TEST_RESULTS.md`
- **API Documentation**: http://localhost:8000/docs
- **Configuration**: `app/core/config.py`

