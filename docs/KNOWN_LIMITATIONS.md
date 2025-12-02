# Known Limitations and Constraints

This document provides a comprehensive overview of system limitations, constraints, and known issues for the AI Web Scraper API. Understanding these limitations helps set realistic expectations and guides future improvements.

## 1. Performance Limitations

### Response Time

- **Typical queries**: 30-90 seconds
- **Complex queries**: 90-180 seconds
- **Maximum timeout**: 600 seconds (10 minutes)
- **Factors affecting speed**: number of sites to scrape, content size, AI processing complexity
- **Recommendation**: Set realistic timeout expectations for users

### Concurrency

- **Default concurrent scraping**: 5 sites simultaneously (configurable via `SCRAPER_MAX_CONCURRENT_REQUESTS`)
- **Rate limiting**: Per-domain delays (1 second default) to respect robots.txt
- **MongoDB connection pool**: Limited by `MONGODB_MAX_POOL_SIZE` (default: 100)
- **Memory usage increases with concurrent requests**

### Scalability

- **Single-instance deployment** (no distributed scraping yet)
- **In-memory cache** (not shared across instances)
- **No horizontal scaling support** for scraper orchestrator
- **Future**: Consider Redis for distributed caching, message queue for distributed scraping

## 2. Content Extraction Limitations

### Website Compatibility

- **JavaScript-heavy sites**: Limited support (no browser automation, relies on server-side rendering)
- **Dynamic content**: May miss content loaded via AJAX/fetch after initial page load
- **Single-page applications (SPAs)**: Often return minimal HTML
- **Recommendation**: Best results with traditional server-rendered websites

### Robots.txt Compliance

- **Strictly respects robots.txt directives** (may skip sites with restrictive policies)
- **User-agent**: Identifies as web scraper (some sites may block)
- **Crawl delays**: Honors specified delays (can slow down scraping)
- **Trade-off**: Ethical scraping vs. comprehensive coverage

### Content Types

- **Supports**: HTML, plain text, JSON-LD, Open Graph metadata
- **Limited support**: PDFs, images (metadata only), videos
- **Not supported**: Flash, proprietary formats, password-protected content
- **File size limit**: 10MB per page (configurable via `SCRAPER_MAX_CONTENT_SIZE_MB`)

## 3. AI Processing Limitations

### Gemini API Constraints

- **Rate limits**: Subject to Google Gemini API quotas (varies by plan)
- **Token limits**: Input/output token limits per request
- **Cost**: API usage incurs costs (monitor via Google Cloud Console)
- **Fallback**: No offline mode if API is unavailable
- **Recommendation**: Monitor API usage and set budget alerts

### Query Understanding

- **Language**: Optimized for English queries (other languages may have lower accuracy)
- **Ambiguity**: Ambiguous queries may be miscategorized (confidence score indicates uncertainty)
- **Domain coverage**: Best for common domains (AI tools, finance, tech); niche topics may have limited results
- **Context**: No conversation history (each query is independent)

### Content Analysis

- **Summarization**: Limited to configured max length (default: 500 words)
- **Entity extraction**: May miss domain-specific entities
- **Sentiment analysis**: Basic implementation (not fine-tuned for all domains)
- **Relevance scoring**: Heuristic-based (may not match human judgment perfectly)

## 4. Data Storage Limitations

### MongoDB

- **Storage**: Unlimited in theory, but monitor disk space
- **TTL cleanup**: Old data auto-deleted based on `DATABASE_QUERY_TTL_DAYS` (default: 30 days)
- **Indexing**: Compound indexes may slow down writes at scale
- **Backup**: No automatic backup (configure MongoDB backup separately)

### Cache

- **In-memory only**: Data lost on restart
- **Size limit**: `CACHE_MAX_SIZE` (default: 1000 entries)
- **Eviction**: LRU (Least Recently Used) when full
- **TTL**: `CACHE_TTL_SECONDS` (default: 3600 = 1 hour)
- **Not suitable for**: Long-term storage, shared across instances

## 5. Security and Privacy

### Authentication

- **API key-based**: Simple but not OAuth/JWT
- **No user management**: Keys managed manually in code/config
- **Permissions**: Basic role-based (admin, read, write)
- **Future**: Consider OAuth2, user registration, API key rotation

### Data Privacy

- **Scraped content**: Stored in MongoDB (ensure compliance with data retention policies)
- **Logging**: May contain query text and URLs (review logs for sensitive data)
- **No PII detection**: System doesn't automatically redact personal information
- **Recommendation**: Implement data retention policies, log sanitization

### Rate Limiting

- **Per-API-key**: Configurable limits (default: 100 requests/hour)
- **No IP-based limiting**: Multiple keys from same IP not restricted
- **No CAPTCHA**: Vulnerable to automated abuse without additional protection

## 6. Error Handling and Recovery

### Partial Failures

- **Some sites fail**: System continues with successful scrapes (partial results returned)
- **AI processing errors**: May return unprocessed content
- **Database errors**: May lose data if storage fails (no retry for DB writes)
- **Recommendation**: Check `warnings` field in response for non-fatal errors

### Timeout Handling

- **Hard timeout**: Request aborted after `timeout_seconds` (no partial results if timeout during DB storage)
- **No resume**: Cannot resume interrupted scraping sessions
- **Recommendation**: Use shorter timeouts for testing, longer for production

### Error Messages

- **Generic in production**: Detailed errors disabled by default (set `API_ENABLE_DETAILED_ERRORS=true` for debugging)
- **Recovery suggestions**: Provided but may not cover all edge cases
- **Logging**: Check server logs for detailed error traces

## 7. Known Issues

### High Priority

- **None currently identified** (all critical bugs resolved in testing)

### Medium Priority

- **Cache hit rate calculation**: May be inaccurate with very low traffic
- **Duplicate detection**: Semantic similarity threshold (0.85) may miss near-duplicates or flag false positives
- **Site discovery**: LLM-based discovery may suggest irrelevant sites for niche queries

### Low Priority

- **Metrics reset**: Requires admin API key (no automatic reset on schedule)
- **Log rotation**: Manual configuration required (not automatic)
- **Health check latency**: Database ping adds ~100ms to health check response

## 8. Browser and Client Limitations

### API Clients

- **CORS**: Configured for specific origins (update `CORS_ORIGINS` for new clients)
- **Request size**: Limited by FastAPI defaults (10MB body size)
- **Timeout**: Client must support long-running requests (up to 10 minutes)

### Response Size

- **Large responses**: May exceed client memory limits (100+ processed items)
- **Pagination**: Not implemented (all results returned in single response)
- **Recommendation**: Use `processing_config` to limit items processed

## 9. Deployment Limitations

### Docker

- **Single container**: No multi-container orchestration in docker-compose (MongoDB separate)
- **Resource limits**: Not set by default (configure in docker-compose.yml)
- **Health checks**: Basic (no advanced readiness probes)

### Kubernetes

- **No Helm chart**: Manual YAML configuration required
- **No autoscaling**: HPA not configured
- **No service mesh**: No Istio/Linkerd integration

### Cloud Platforms

- **Not tested on**: AWS Lambda, Google Cloud Run (long-running requests may timeout)
- **Best suited for**: VM-based deployments (EC2, GCE, Azure VMs)

## 10. Future Improvements

### Planned Enhancements

- **Browser automation**: Selenium/Playwright for JavaScript-heavy sites
- **Distributed scraping**: Message queue (RabbitMQ/Redis) for horizontal scaling
- **Advanced caching**: Redis for shared cache across instances
- **Pagination**: Support for large result sets
- **Webhooks**: Async notifications when scraping completes
- **API versioning**: v2 endpoint with breaking changes
- **User management**: OAuth2, API key rotation, usage dashboards

### Community Requests

- **Custom extractors**: Plugin system for domain-specific extraction logic
- **Export formats**: CSV, Excel, PDF report generation
- **Scheduled scraping**: Cron-like scheduling for recurring queries
- **Comparison mode**: Compare results across time periods

## Configuration Reference

For configuration limits and defaults, see:
- `app/core/config.py` - All configuration settings and validation rules
- `README.md` - Feature documentation and setup instructions
- `docs/INTEGRATION_TESTING.md` - Performance benchmarks and testing guidelines

## Getting Help

If you encounter limitations not documented here:

1. Check the [GitHub Issues](https://github.com/your-repo/issues) for known problems
2. Review server logs for detailed error information
3. Consult the API documentation at `/docs` endpoint
4. Contact the development team with specific use cases

## Version History

- **v1.0.0** (2024-01-01): Initial documentation of limitations

