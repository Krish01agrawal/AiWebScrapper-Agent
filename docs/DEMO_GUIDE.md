# AI Web Scraper - Team Demo Guide

This guide provides a step-by-step flow for presenting the AI Web Scraper to your team, including talking points, demo actions, and troubleshooting tips.

## Pre-Demo Checklist (15 minutes before)

### Environment Setup

- [ ] MongoDB running: `docker ps | grep mongo` or `mongosh --eval "db.version()"`
- [ ] Environment variables set: `python scripts/preflight_check.py`
- [ ] Server started: `bash scripts/start_server.sh` (or `uvicorn app.main:app --reload`)
- [ ] Health checks passing: `curl http://localhost:8000/health`
- [ ] Demo script ready: `python scripts/demo.py --help`
- [ ] Monitoring dashboard open: Open `demo/dashboard.html` in browser
- [ ] Postman collection imported (optional): Import `demo/postman_collection.json`

### Test Queries Prepared

- [ ] AI Tools: "Best AI agents for coding and software development"
- [ ] Mutual Funds: "Best mutual funds for beginners with low risk"
- [ ] General: "Latest trends in artificial intelligence"
- [ ] Edge case: "AI tools for image generation with free tiers" (longer query)

### Backup Plan

- [ ] Pre-recorded responses saved: Run `python scripts/test_scrape_endpoint.py --all --save-responses` before demo
- [ ] Screenshots of successful runs ready
- [ ] Fallback to slides if live demo fails

## Demo Flow (30-45 minutes)

### Part 1: Introduction (5 minutes)

**Talking Points:**

- Problem statement: "Manual web research is time-consuming and inconsistent"
- Solution: "AI-powered web scraper that understands natural language queries"
- Key differentiators: Natural language input, AI-driven site discovery, intelligent content analysis, structured output
- Use cases: Market research, competitive analysis, investment research, technology evaluation

**Demo Action:**

- Show architecture diagram (if available) or describe: FastAPI → Query Processing (Gemini) → Web Scraping → AI Analysis (Gemini) → MongoDB Storage
- Open API documentation: `http://localhost:8000/docs` (Swagger UI)
- Highlight main endpoint: `/api/v1/scrape`

### Part 2: Quick Demo - AI Tools Query (10 minutes)

**Setup:**

```bash
python scripts/demo.py --quick

# OR

curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Best AI agents for coding and software development",
    "timeout_seconds": 180
  }' | jq .
```

**Talking Points:**

- Input: Natural language query (no need to specify URLs or structure)
- Processing stages: Watch live progress in terminal or dashboard
  - Stage 1: Query Processing (1-3s) - "System understands this is about AI tools"
  - Stage 2: Web Scraping (10-30s) - "Discovers and scrapes relevant sites"
  - Stage 3: AI Processing (15-45s) - "Analyzes content, extracts insights"
  - Stage 4: Database Storage (1-5s) - "Stores results for future reference"
- Output highlights:
  - Category: "ai_tools" (confidence: 0.95)
  - Total items: 15 sites scraped
  - Processed items: 12 successfully analyzed
  - Success rate: 80%
  - Key insights: Themes, entities, summaries

**Expected Results:**

- Response time: 30-60 seconds (mention this is within expected range)
- Relevant sites: GitHub, ProductHunt, AI tool directories
- Structured data: Tool names, features, pricing, URLs

**Potential Issues & Responses:**

- Slow response: "This is normal for first request; subsequent requests use cache"
- Some sites failed: "System continues with successful scrapes; see warnings field"
- Lower confidence: "System is being cautious; results are still relevant"

### Part 3: Feature Showcase - Caching (5 minutes)

**Setup:**

```bash
python scripts/demo.py --category ai_tools

# Run same query twice
```

**Talking Points:**

- First request: Cache MISS (full scraping, 30-60s)
- Second request: Cache HIT (instant response, <1s)
- Cache headers: Show `X-Cache-Status: HIT` and `X-Cache-Age: 5` (seconds)
- Benefits: Reduced load, faster responses, cost savings (fewer API calls)
- TTL: 1 hour default (configurable)

**Demo Action:**

- Show timing difference: "60x faster with cache"
- Show cache statistics: `curl http://localhost:8000/health/cache | jq .`
- Explain cache invalidation: "Automatic after 1 hour or manual reset"

### Part 4: Different Query Types (10 minutes)

**Mutual Funds Query:**

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Best mutual funds for beginners with low risk",
    "timeout_seconds": 180
  }' | jq .
```

**Talking Points:**

- Category detection: "finance" or "investment" (not "ai_tools")
- Different sites: Financial news, investment platforms, fund databases
- Domain-specific extraction: NAV, expense ratio, returns, risk rating
- Demonstrates versatility: Same API, different domains

**General Query:**

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Latest trends in artificial intelligence",
    "timeout_seconds": 180
  }' | jq .
```

**Talking Points:**

- Broader category: "general" or "technology"
- News sites, blogs, research papers
- Trend analysis: Themes, sentiment, key topics

### Part 5: Advanced Features (5 minutes)

**Custom Processing Config:**

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI tools for image generation",
    "processing_config": {
      "enable_ai_analysis": true,
      "enable_summarization": true,
      "max_summary_length": 300,
      "enable_duplicate_detection": true
    },
    "timeout_seconds": 180,
    "store_results": true
  }' | jq .
```

**Talking Points:**

- Customization: Enable/disable processing stages
- Performance tuning: Adjust timeouts, limits
- Storage control: Option to skip database storage for testing
- Flexibility: Adapt to different use cases

**Monitoring Dashboard:**

- Open `demo/dashboard.html` in browser
- Show real-time metrics: Request count, error rate, cache hit rate, response times
- System health: CPU, memory, disk usage
- Explain: "Production-ready monitoring for operations team"

### Part 6: Error Handling & Edge Cases (5 minutes)

**Invalid Query:**

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{"query": ""}'
```

**Talking Points:**

- Validation: Clear error messages
- Recovery suggestions: "Ensure query text is within length limits"
- Status codes: 400 for validation, 500 for server errors
- Graceful degradation: Partial results when possible

**Timeout Validation Error (Business Rule):**

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{"query": "Test query", "timeout_seconds": 20}'
```

**Talking Points:**

- Business-rule validation: `timeout_seconds` must be between 30-600 seconds
- Returns HTTP 400 with `VALIDATION_ERROR` code
- Clear error message: "timeout_seconds must be at least 30 seconds, got 20"
- Recovery suggestions provided: "Set timeout_seconds to at least 30 seconds"
- This is a validation error, not a workflow timeout

**Real Workflow Timeout Scenario:**

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{"query": "Complex query requiring extensive processing", "timeout_seconds": 30}'
```

**Talking Points:**

- Valid timeout provided (30 seconds, within allowed range)
- Workflow execution exceeds the timeout during actual processing
- Returns HTTP 500 with `WORKFLOW_TIMEOUT` error code
- Partial results: Returned if available from completed stages
- Retry guidance: "Try increasing the timeout_seconds parameter"
- This demonstrates actual workflow timeout handling, not validation

## Q&A Preparation

### Common Questions & Answers

**Q: How does it handle JavaScript-heavy sites?**

A: Currently limited to server-side rendered content. JavaScript-heavy sites may return minimal HTML. Future enhancement: Browser automation (Selenium/Playwright).

**Q: What about rate limiting and being blocked?**

A: We respect robots.txt, use per-domain delays (1s default), and identify as a scraper. Some sites may block us. Future: Rotating proxies, user-agent rotation.

**Q: How accurate is the AI analysis?**

A: Powered by Google Gemini. Accuracy varies by domain (best for common topics). Confidence scores indicate uncertainty. Always review results.

**Q: Can it scrape private/authenticated sites?**

A: No, only public content. No support for login/authentication. Privacy and legal considerations.

**Q: What's the cost?**

A: Main costs: Google Gemini API usage (pay-per-token), MongoDB hosting, server compute. Estimate: $X per 1000 queries (provide actual estimate based on testing).

**Q: How does it scale?**

A: Current: Single-instance deployment. Future: Distributed scraping with message queues, Redis for shared cache, horizontal scaling.

**Q: What about data privacy and compliance?**

A: Scraped data stored in MongoDB (30-day TTL default). No PII detection. Recommendation: Implement data retention policies, review logs for sensitive data.

**Q: Can I customize extraction logic?**

A: Currently uses generic extractors. Future: Plugin system for domain-specific logic.

**Q: How do I deploy to production?**

A: Docker/docker-compose provided. Kubernetes YAML available. Best on VM-based platforms (EC2, GCE). See `README.md` deployment section.

**Q: What if the demo fails?**

A: Fallback to pre-recorded responses, screenshots, or slides. Emphasize: "This is a live system; occasional issues are expected."

## Post-Demo Actions

### Immediate Follow-up

- [ ] Share demo materials: Postman collection, curl scripts, demo guide
- [ ] Provide access: API keys, server URL (if applicable)
- [ ] Schedule follow-up: Q&A session, training, feedback collection

### Documentation

- [ ] Send links: README, API docs, integration guide, known limitations
- [ ] Share recordings: Demo video, screenshots
- [ ] Provide examples: Sample queries, expected outputs

### Next Steps

- [ ] Gather feedback: What worked, what didn't, feature requests
- [ ] Prioritize improvements: Based on team input
- [ ] Plan rollout: Pilot users, production deployment timeline

## Troubleshooting During Demo

### Server Won't Start

- Check MongoDB: `docker ps | grep mongo`
- Check port: `lsof -i :8000` (kill if occupied)
- Check logs: `tail -f logs/app.log`
- Fallback: Use pre-recorded responses

### Slow Responses

- Explain: "First request is slower; cache helps subsequent requests"
- Check network: `ping google.com`
- Check Gemini API: `python scripts/test_connections.py --gemini-only`
- Fallback: Use cached responses or pre-recorded demos

### Errors During Scraping

- Check warnings: Show `warnings` field in response
- Explain: "Some sites may be temporarily unavailable; system continues with others"
- Retry: "Let's try a different query"
- Fallback: Show successful pre-recorded response

### Dashboard Not Loading

- Check file path: `open demo/dashboard.html`
- Check CORS: Ensure server allows dashboard origin
- Fallback: Use curl to show metrics: `curl http://localhost:8000/api/v1/metrics?format=json | jq .`

## Tips for Success

1. **Practice**: Run through demo 2-3 times before presentation
2. **Timing**: Keep to schedule; skip sections if running long
3. **Engagement**: Ask questions, encourage interaction
4. **Transparency**: Acknowledge limitations, don't oversell
5. **Backup**: Always have pre-recorded responses ready
6. **Enthusiasm**: Show excitement about the technology
7. **Context**: Explain why each feature matters
8. **Visuals**: Use dashboard, terminal colors, formatted output
9. **Pace**: Don't rush; let results load naturally
10. **Feedback**: Note questions/concerns for follow-up

## Reference Materials

- **Interactive Demo**: `scripts/demo.py` - Run with `python scripts/demo.py`
- **Postman Collection**: `demo/postman_collection.json` - Import into Postman
- **Curl Scripts**: `demo/curl_collection.sh` - Run with `bash demo/curl_collection.sh`
- **Known Limitations**: `docs/KNOWN_LIMITATIONS.md` - System constraints and Q&A prep
- **API Documentation**: `http://localhost:8000/docs` - Swagger UI
- **README**: `README.md` - Comprehensive documentation

## Demo Scripts Quick Reference

```bash
# Quick demo
python scripts/demo.py --quick

# Category demo
python scripts/demo.py --category ai_tools

# Custom query
python scripts/demo.py --query "Your query here"

# Interactive menu
python scripts/demo.py

# Curl collection
bash demo/curl_collection.sh

# With API key
bash demo/curl_collection.sh --api-key your_key_here
```

Good luck with your demo! 🚀

