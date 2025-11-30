# Makefile for AI Web Scraper project
# Provides convenient commands for testing, development, and deployment

.PHONY: help test test-unit test-integration test-agents test-scraper test-processing test-database test-api test-fast test-parallel coverage test-watch test-debug clean install-test-deps validate-env test-report start-server start-server-dev start-server-prod test-health test-scrape test-workflow test-integration-full validate-response test-cache test-ai-tools test-mutual-funds integration-report

# Default target
help:
	@echo "AI Web Scraper - Available Commands:"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test              Run all tests with coverage"
	@echo "  test-unit         Run only unit tests"
	@echo "  test-integration  Run only integration tests"
	@echo "  test-agents       Run only agent tests"
	@echo "  test-scraper      Run only scraper tests"
	@echo "  test-processing   Run only processing tests"
	@echo "  test-database     Run only database tests"
	@echo "  test-api          Run only API tests"
	@echo "  test-fast         Run tests without slow tests"
	@echo "  test-parallel     Run tests in parallel"
	@echo "  test-watch        Run tests in watch mode"
	@echo "  test-debug        Run tests with debugging enabled"
	@echo ""
	@echo "Coverage Commands:"
	@echo "  coverage          Generate and view coverage report"
	@echo ""
	@echo "Utility Commands:"
	@echo "  clean             Clean test artifacts"
	@echo "  install-test-deps Install testing dependencies"
	@echo "  validate-env      Run environment validation"
	@echo "  test-report       Generate comprehensive test report"
	@echo ""
	@echo "Server Commands:"
	@echo "  start-server      Start server with environment validation"
	@echo "  start-server-dev  Start server in development mode"
	@echo "  start-server-prod Start server in production mode"
	@echo ""
	@echo "Integration Testing Commands:"
	@echo "  test-health       Test all health check endpoints"
	@echo "  test-scrape       Test scrape endpoint with sample queries"
	@echo "  test-workflow     Test complete workflow from startup to validation"
	@echo "  test-integration-full Run comprehensive integration test suite"
	@echo "  validate-response Validate API response schema"
	@echo "  test-cache        Test cache hit/miss behavior"
	@echo "  test-ai-tools     Test all AI tools sample queries"
	@echo "  test-mutual-funds Test all mutual funds sample queries"
	@echo "  integration-report Generate comprehensive test report"
	@echo ""
	@echo "Real-World Scenario Testing Commands:"
	@echo "  test-real-world   Run real-world scenario tests"
	@echo "  test-real-world-json Run real-world tests (JSON output)"
	@echo "  test-performance Run performance benchmarks"
	@echo "  test-performance-json Run performance benchmarks (JSON output)"
	@echo "  test-edge-cases   Run edge case tests"
	@echo "  test-ai-agents    Test AI agents query"
	@echo "  test-mutual-funds-query Test mutual funds query"
	@echo "  test-comprehensive Run comprehensive test suite (all tests)"
	@echo ""
	@echo "Load Testing & Performance Commands:"
	@echo "  test-load              Basic load test with default concurrency"
	@echo "  test-load-ramp         Gradual ramp-up test"
	@echo "  test-load-burst        Burst traffic test"
	@echo "  test-load-sustained    Sustained load test"
	@echo "  test-cache-performance Cache behavior validation"
	@echo "  test-rate-limits       Rate limiting validation"
	@echo "  test-connection-pool   MongoDB connection pool stress test"
	@echo "  test-load-all          Run all load test scenarios"
	@echo "  analyze-load-results   Analyze load test results"
	@echo "  test-load-baseline     Establish performance baseline"
	@echo "  test-load-compare      Compare against baseline"
	@echo ""

# Testing commands
test:
	@echo "🧪 Running all tests with coverage..."
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term --cov-report=xml

test-unit:
	@echo "🧪 Running unit tests..."
	pytest tests/ -m unit -v

test-integration:
	@echo "🧪 Running integration tests..."
	pytest tests/ -m integration -v

test-agents:
	@echo "🧪 Running agent tests..."
	pytest tests/test_agents.py -v

test-scraper:
	@echo "🧪 Running scraper tests..."
	pytest tests/test_scraper.py -v

test-processing:
	@echo "🧪 Running processing tests..."
	pytest tests/test_processing.py -v

test-database:
	@echo "🧪 Running database tests..."
	pytest tests/test_database.py -v

test-api:
	@echo "🧪 Running API tests..."
	pytest tests/test_api.py -v

test-fast:
	@echo "🧪 Running fast tests (excluding slow tests)..."
	pytest tests/ -v -m "not slow"

test-parallel:
	@echo "🧪 Running tests in parallel..."
	pytest tests/ -v -n auto

test-watch:
	@echo "🧪 Running tests in watch mode..."
	@if command -v ptw >/dev/null 2>&1; then \
		ptw tests/ -- -v; \
	else \
		echo "⚠️  pytest-watch not installed. Install with: pip install pytest-watch"; \
		echo "   Falling back to regular test run..."; \
		pytest tests/ -v; \
	fi

test-debug:
	@echo "🧪 Running tests with debugging enabled..."
	pytest tests/ -v -s --pdb

# Coverage commands
coverage:
	@echo "📊 Generating coverage report..."
	coverage report -m
	@echo ""
	@echo "📄 HTML coverage report generated in htmlcov/"
	@if command -v open >/dev/null 2>&1; then \
		echo "🌐 Opening coverage report..."; \
		open htmlcov/index.html; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		echo "🌐 Opening coverage report..."; \
		xdg-open htmlcov/index.html; \
	else \
		echo "📄 View coverage report at: htmlcov/index.html"; \
	fi

# Utility commands
clean:
	@echo "🧹 Cleaning test artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "test_results.json" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

install-test-deps:
	@echo "📦 Installing testing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Testing dependencies installed"

validate-env:
	@echo "🔍 Validating environment..."
	python scripts/preflight_check.py
	@echo "✅ Environment validation complete"

test-report:
	@echo "📊 Generating comprehensive test report..."
	python scripts/run_tests.py --coverage --output markdown --verbose
	@echo "✅ Test report generated: docs/TEST_RESULTS.md"

# Development commands
install-dev:
	@echo "📦 Installing development dependencies..."
	pip install -r requirements.txt
	pip install black isort flake8 mypy
	@echo "✅ Development dependencies installed"

format:
	@echo "🎨 Formatting code with black..."
	black app/ tests/ scripts/
	isort app/ tests/ scripts/
	@echo "✅ Code formatting complete"

lint:
	@echo "🔍 Running linters..."
	flake8 app/ tests/ scripts/
	@echo "✅ Linting complete"

type-check:
	@echo "🔍 Running type checker..."
	@if command -v mypy >/dev/null 2>&1; then \
		mypy app/; \
	else \
		echo "⚠️  mypy not installed. Install with: pip install mypy"; \
	fi
	@echo "✅ Type checking complete"

# Docker commands
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t ai-web-scraper .
	@echo "✅ Docker image built"

docker-test:
	@echo "🐳 Running tests in Docker..."
	docker run --rm ai-web-scraper make test
	@echo "✅ Docker tests complete"

# Database commands
db-start:
	@echo "🗄️  Starting MongoDB..."
	@if command -v docker >/dev/null 2>&1; then \
		docker run -d --name mongodb-test -p 27017:27017 mongo:7.0; \
		echo "✅ MongoDB started in Docker"; \
	else \
		echo "⚠️  Docker not available. Please start MongoDB manually"; \
	fi

db-stop:
	@echo "🗄️  Stopping MongoDB..."
	@if command -v docker >/dev/null 2>&1; then \
		docker stop mongodb-test && docker rm mongodb-test; \
		echo "✅ MongoDB stopped"; \
	else \
		echo "⚠️  Docker not available. Please stop MongoDB manually"; \
	fi

# Quick development workflow
dev-setup: install-dev validate-env
	@echo "🚀 Development environment setup complete!"
	@echo "Run 'make test' to run tests"
	@echo "Run 'make format' to format code"
	@echo "Run 'make lint' to check code quality"

# CI/CD simulation
ci-test: clean install-test-deps test coverage
	@echo "🔄 CI/CD test simulation complete"

# Performance testing
perf-test:
	@echo "⚡ Running performance tests..."
	pytest tests/ -m "slow or performance" -v --timeout=300
	@echo "✅ Performance tests complete"

# Security testing
security-test:
	@echo "🔒 Running security tests..."
	@if command -v bandit >/dev/null 2>&1; then \
		bandit -r app/; \
	else \
		echo "⚠️  bandit not installed. Install with: pip install bandit"; \
	fi
	@if command -v safety >/dev/null 2>&1; then \
		safety check; \
	else \
		echo "⚠️  safety not installed. Install with: pip install safety"; \
	fi
	@echo "✅ Security tests complete"

# Full test suite (everything)
test-all: clean install-test-deps test-unit test-integration test-fast perf-test security-test coverage test-report
	@echo "🎯 Full test suite complete!"
	@echo "📊 Check docs/TEST_RESULTS.md for detailed results"
	@echo "📄 Check htmlcov/index.html for coverage report"

# Server commands
start-server:
	@echo "🚀 Starting server with environment validation..."
	bash scripts/start_server.sh

start-server-dev:
	@echo "🚀 Starting server in development mode..."
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

start-server-prod:
	@echo "🚀 Starting server in production mode..."
	bash scripts/start_server.sh --production

# Integration testing commands
test-health:
	@echo "🏥 Testing all health check endpoints..."
	python scripts/test_health.py --all

test-scrape:
	@echo "🕷️  Testing scrape endpoint with sample queries..."
	python scripts/test_scrape_endpoint.py --all

test-workflow:
	@echo "🔄 Testing complete workflow from startup to validation..."
	bash scripts/test_workflow.sh

test-integration-full:
	@echo "🧪 Running comprehensive integration test suite..."
	bash scripts/test_workflow.sh && python scripts/test_health.py --all && python scripts/test_scrape_endpoint.py --all

validate-response:
	@echo "✅ Validating API response schema..."
	@if [ -f response.json ]; then \
		python scripts/validate_response_schema.py --response-file response.json; \
	else \
		echo "⚠️  response.json not found. Provide a response file to validate."; \
		echo "   Usage: python scripts/validate_response_schema.py --response-file <file>"; \
	fi

test-cache:
	@echo "💾 Testing cache hit/miss behavior..."
	python scripts/test_scrape_endpoint.py --cache

test-ai-tools:
	@echo "🤖 Testing all AI tools sample queries..."
	python scripts/test_scrape_endpoint.py --category ai_tools

test-mutual-funds:
	@echo "💰 Testing all mutual funds sample queries..."
	python scripts/test_scrape_endpoint.py --category mutual_funds

integration-report:
	@echo "📊 Generating comprehensive integration test report..."
	bash scripts/test_workflow.sh --save-responses && python scripts/test_scrape_endpoint.py --all --json > integration_report.json
	@echo "✅ Integration test report generated: integration_report.json"

# Real-world scenario testing
test-real-world:
	@echo "Running real-world scenario tests..."
	python scripts/test_real_world_scenarios.py --all --verbose

test-real-world-json:
	@echo "Running real-world scenario tests (JSON output)..."
	python scripts/test_real_world_scenarios.py --all --json

# Performance benchmarking
test-performance:
	@echo "Running performance benchmarks..."
	python scripts/test_real_world_scenarios.py --performance --verbose

test-performance-json:
	@echo "Running performance benchmarks (JSON output)..."
	python scripts/test_real_world_scenarios.py --performance --json

# Edge case testing
test-edge-cases:
	@echo "Running edge case tests..."
	python scripts/test_real_world_scenarios.py --edge-cases --verbose

# Comprehensive testing (all tests)
test-comprehensive:
	@echo "Running comprehensive test suite..."
	$(MAKE) test-unit
	$(MAKE) test-integration
	$(MAKE) test-real-world
	$(MAKE) test-performance

# Quick real-world test (specific queries)
test-ai-agents:
	@echo "Testing AI agents query..."
	python scripts/test_real_world_scenarios.py --query "best AI agents for coding" --verbose

test-mutual-funds-query:
	@echo "Testing mutual funds query..."
	python scripts/test_real_world_scenarios.py --query "best mutual funds for beginners" --verbose

# Load testing and performance validation
test-load:
	@echo "Running basic load test..."
	python scripts/test_load_performance.py --concurrency 20 --duration 60 --verbose

test-load-ramp:
	@echo "Running gradual ramp-up test..."
	python scripts/test_load_performance.py --ramp-up --concurrency 50 --verbose

test-load-burst:
	@echo "Running burst traffic test..."
	python scripts/test_load_performance.py --burst --concurrency 50 --verbose

test-load-sustained:
	@echo "Running sustained load test..."
	python scripts/test_load_performance.py --sustained --concurrency 20 --duration 120 --verbose

test-cache-performance:
	@echo "Testing cache behavior..."
	python scripts/test_load_performance.py --cache-test --verbose

test-rate-limits:
	@echo "Testing rate limiting..."
	python scripts/test_load_performance.py --rate-limit-test --verbose

test-connection-pool:
	@echo "Testing connection pool under load..."
	python scripts/test_load_performance.py --sustained --concurrency 20 --verbose

test-load-all:
	@echo "Running all load test scenarios..."
	python scripts/test_load_performance.py --all --save-results --verbose

analyze-load-results:
	@echo "Analyzing load test results..."
	@LATEST=$$(ls -t test_results/load_test_*.json 2>/dev/null | head -1); \
	if [ -n "$$LATEST" ]; then \
		python scripts/analyze_load_test_results.py --results-file $$LATEST --format markdown --verbose; \
	else \
		echo "⚠️  No load test results found. Run 'make test-load-all' first."; \
	fi

test-load-baseline:
	@echo "Establishing performance baseline..."
	python scripts/test_load_performance.py --all --save-results --verbose
	@LATEST=$$(ls -t test_results/load_test_*.json 2>/dev/null | head -1); \
	if [ -n "$$LATEST" ]; then \
		cp $$LATEST test_results/baseline_load_test.json; \
		echo "✅ Baseline saved to test_results/baseline_load_test.json"; \
	else \
		echo "⚠️  Failed to create baseline. Check test results."; \
	fi

test-load-compare:
	@echo "Comparing against baseline..."
	@if [ -f test_results/baseline_load_test.json ]; then \
		LATEST=$$(ls -t test_results/load_test_*.json 2>/dev/null | head -1); \
		if [ -n "$$LATEST" ]; then \
			python scripts/analyze_load_test_results.py \
				--results-file $$LATEST \
				--baseline-file test_results/baseline_load_test.json \
				--format markdown --verbose; \
		else \
			echo "⚠️  No current test results found. Run 'make test-load-all' first."; \
		fi \
	else \
		echo "⚠️  No baseline found. Run 'make test-load-baseline' first."; \
	fi

# Error Recovery Testing
.PHONY: test-errors
test-errors:
	@echo "Running error scenario tests..."
	pytest tests/test_error_scenarios.py -v --tb=short

.PHONY: test-middleware-errors
test-middleware-errors:
	@echo "Running middleware error tests..."
	pytest tests/test_middleware_errors.py -v --tb=short

.PHONY: test-error-recovery
test-error-recovery:
	@echo "Running end-to-end error recovery tests..."
	python scripts/test_error_recovery.py --all

.PHONY: test-all-errors
test-all-errors: test-errors test-middleware-errors test-error-recovery
	@echo "All error tests completed"

.PHONY: simulate-mongodb-failure
simulate-mongodb-failure:
	@echo "Simulating MongoDB failure..."
	./scripts/simulate_failures.sh mongodb down
	@echo "MongoDB stopped. Run 'make restore-services' to restore."

.PHONY: simulate-gemini-failure
simulate-gemini-failure:
	@echo "Simulating Gemini API failure..."
	./scripts/simulate_failures.sh gemini invalid-key
	@echo "Gemini API key invalidated. Run 'make restore-services' to restore."

.PHONY: restore-services
restore-services:
	@echo "Restoring all services..."
	./scripts/simulate_failures.sh restore-all
	@echo "Services restored"

.PHONY: test-with-failures
test-with-failures:
	@echo "Running tests with simulated failures..."
	$(MAKE) simulate-mongodb-failure
	python scripts/test_error_recovery.py --test mongodb_failure
	$(MAKE) restore-services
	$(MAKE) simulate-gemini-failure
	python scripts/test_error_recovery.py --test gemini_failure
	$(MAKE) restore-services
