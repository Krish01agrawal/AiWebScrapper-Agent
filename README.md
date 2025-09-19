# Traycer Try API

A modern FastAPI application with MongoDB integration, Google Gemini AI capabilities, and intelligent web scraping, built following 2024-2025 best practices.

## 🚀 Features

- **FastAPI Framework**: Modern, fast web framework for building APIs with Python
- **Async MongoDB**: Motor driver for high-performance async database operations
- **Google Gemini AI**: Integration with Google's latest AI model for intelligent operations
- **Intelligent Web Scraping**: AI-powered site discovery and content extraction with ethical practices
- **Environment-based Configuration**: Secure configuration management using environment variables
- **Health Checks**: Comprehensive system health monitoring endpoints
- **CORS Support**: Cross-origin resource sharing for frontend integration
- **Type Safety**: Full type hints and Pydantic validation throughout

## 📋 Prerequisites

- Python 3.8+
- MongoDB instance (local or MongoDB Atlas)
- Google Gemini API key
- Virtual environment tool (venv, conda, or pipenv)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd traycerTry
   ```

2. **Create and activate virtual environment**
   ```bash
   # Using venv (recommended)
   python -m venv venv
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
   cp env.example .env
   
   # Edit .env with your actual values
   nano .env  # or use your preferred editor
   ```

## ⚙️ Environment Variables

Copy `env.example` to `.env` and configure the following variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGODB_DB` | Database name | `traycer_try` |
| `GEMINI_API_KEY` | Google Gemini API key | `your_api_key_here` |
| `ENVIRONMENT` | App environment | `development` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DEBUG` | Debug mode | `true` |

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
│   ├── api/               # API layer
│   │   ├── __init__.py
│   │   └── routers/       # API route definitions
│   │       ├── __init__.py
│   │       └── health.py  # Health check endpoints
│   ├── core/              # Core infrastructure
│   │   ├── __init__.py
│   │   ├── config.py      # Configuration management
│   │   ├── database.py    # MongoDB connection
│   │   └── gemini.py      # Gemini AI client
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
│   └── scraper/           # Web scraping module
│       ├── __init__.py
│       ├── base.py        # Base scraper agent
│       ├── session.py     # HTTP session management
│       ├── rate_limiter.py # Rate limiting system
│       ├── robots.py      # Robots.txt compliance
│       ├── discovery.py   # Site discovery agent
│       ├── extractor.py   # Content extraction agent
│       ├── orchestrator.py # Main orchestrator
│       └── schemas.py     # Scraper data models
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
├── .gitignore            # Git ignore rules
└── README.md             # This file
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

### Common Issues

1. **MongoDB Connection Failed**
   - Verify MongoDB is running
   - Check connection string in `.env`
   - Ensure network access to MongoDB instance

2. **Gemini API Errors**
   - Verify API key is correct
   - Check API quota and billing
   - Ensure internet connectivity

3. **Scraper Issues**
   - Check robots.txt compliance settings
   - Verify rate limiting configuration
   - Monitor HTTP session health
   - Check content size limits

4. **Import Errors**
   - Verify virtual environment is activated
   - Check all dependencies are installed
   - Verify Python path

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
