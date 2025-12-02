#!/bin/bash
#
# Comprehensive curl command collection for AI Web Scraper API testing
# Usage: bash demo/curl_collection.sh [options]
#

set -e

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-}"
TIMEOUT="${TIMEOUT:-300}"
SAVE_RESPONSES=false
VERBOSE=false
QUICK_MODE=false

# Test counters
TOTAL_TESTS=0
SUCCESSFUL_TESTS=0
FAILED_TESTS=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
RESET='\033[0m'

# Helper functions
print_header() {
    echo -e "\n${CYAN}========================================${RESET}"
    echo -e "${CYAN}$1${RESET}"
    echo -e "${CYAN}========================================${RESET}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${RESET}"
}

print_error() {
    echo -e "${RED}✗ $1${RESET}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${RESET}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${RESET}"
}

run_curl() {
    local description="$1"
    local method="${2:-GET}"
    local url="$3"
    local data="${4:-}"
    local headers="${5:-}"
    local expected_status="${6:-200}"
    
    print_info "$description"
    
    local curl_cmd="curl -s -w '\n%{http_code}'"
    
    if [ "$VERBOSE" = true ]; then
        curl_cmd="$curl_cmd -v"
    fi
    
    if [ -n "$API_KEY" ]; then
        curl_cmd="$curl_cmd -H 'X-API-Key: $API_KEY'"
    fi
    
    if [ -n "$headers" ]; then
        curl_cmd="$curl_cmd $headers"
    fi
    
    if [ "$method" = "POST" ]; then
        curl_cmd="$curl_cmd -X POST -H 'Content-Type: application/json'"
        if [ -n "$data" ]; then
            curl_cmd="$curl_cmd -d '$data'"
        fi
    fi
    
    curl_cmd="$curl_cmd '$url'"
    
    local start_time=$(date +%s.%N)
    local response=$(eval $curl_cmd)
    local end_time=$(date +%s.%N)
    
    # Extract HTTP status code (last line)
    local http_code=$(echo "$response" | tail -n 1)
    local response_body=$(echo "$response" | sed '$d')
    
    # Update test counters
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ "$http_code" -eq "$expected_status" ] || ([ "$expected_status" = "200" ] && [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]); then
        SUCCESSFUL_TESTS=$((SUCCESSFUL_TESTS + 1))
        print_success "HTTP Status: $http_code (expected: $expected_status)"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        print_error "HTTP Status: $http_code (expected: $expected_status)"
    fi
    
    # Calculate duration if bc is available
    local duration="N/A"
    if [ "$BC_AVAILABLE" = true ]; then
        duration=$(echo "$end_time - $start_time" | bc)
    fi
    
    # Check if jq is available for formatting
    if command -v jq &> /dev/null; then
        echo "$response_body" | jq . 2>/dev/null || echo "$response_body"
    else
        echo "$response_body"
    fi
    
    if [ "$BC_AVAILABLE" = true ]; then
        echo -e "${CYAN}Duration: ${duration}s${RESET}\n"
    else
        echo -e "${CYAN}Duration: N/A (bc not available)${RESET}\n"
    fi
    
    # Save response if requested
    if [ "$SAVE_RESPONSES" = true ]; then
        local timestamp=$(date +%Y%m%d_%H%M%S)
        local filename="demo_response_${timestamp}.json"
        echo "$response_body" > "$filename"
        print_info "Response saved to: $filename"
    fi
}

save_response() {
    local response="$1"
    local filename="$2"
    echo "$response" > "$filename"
    print_info "Response saved to: $filename"
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            BASE_URL="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        --save-responses)
            SAVE_RESPONSES=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --url <url>          Set base URL (default: http://localhost:8000)"
            echo "  --api-key <key>      Set API key for authentication"
            echo "  --save-responses     Save all responses to files"
            echo "  --verbose            Show full curl output"
            echo "  --quick              Run only essential tests"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if jq is available
if ! command -v jq &> /dev/null; then
    print_warning "jq is not installed. JSON responses will not be formatted."
    print_info "Install jq for better output: brew install jq (macOS) or apt-get install jq (Linux)"
fi

# Check if bc is available for duration calculation
BC_AVAILABLE=false
if command -v bc &> /dev/null; then
    BC_AVAILABLE=true
else
    print_warning "bc is not installed. Duration calculation will be skipped."
fi

print_header "AI Web Scraper API - Curl Collection"
print_info "Base URL: $BASE_URL"
if [ -n "$API_KEY" ]; then
    print_info "API Key: ${API_KEY:0:8}..."
fi
echo ""

# Test server connectivity
print_header "Server Connectivity"
if curl -s -f "$BASE_URL/health" > /dev/null 2>&1; then
    print_success "Server is reachable"
else
    print_error "Server is not reachable at $BASE_URL"
    print_info "Make sure the server is running: uvicorn app.main:app --reload"
    exit 1
fi

# Health Checks
print_header "Health Checks"

run_curl "Overall health check" "GET" "$BASE_URL/health"
run_curl "Database health check" "GET" "$BASE_URL/health/database"
run_curl "Cache health check" "GET" "$BASE_URL/health/cache"
run_curl "Workflow health check" "GET" "$BASE_URL/api/v1/scrape/health"

if [ "$QUICK_MODE" = true ]; then
    print_header "Quick Mode - Essential Tests Only"
    run_curl "Quick scrape test" "POST" "$BASE_URL/api/v1/scrape" \
        '{"query": "Best AI agents for coding", "timeout_seconds": 180}'
    exit 0
fi

# Scrape Requests
print_header "Scrape Requests"

run_curl "AI Tools query" "POST" "$BASE_URL/api/v1/scrape" \
    '{"query": "Best AI agents for coding and software development", "timeout_seconds": 180, "store_results": true}'

run_curl "Mutual Funds query" "POST" "$BASE_URL/api/v1/scrape" \
    '{"query": "Best mutual funds for beginners with low risk", "timeout_seconds": 180}'

run_curl "General query" "POST" "$BASE_URL/api/v1/scrape" \
    '{"query": "Latest trends in artificial intelligence", "timeout_seconds": 180}'

run_curl "Query with custom processing config" "POST" "$BASE_URL/api/v1/scrape" \
    '{"query": "AI tools for image generation", "processing_config": {"enable_ai_analysis": true, "enable_summarization": true, "max_summary_length": 300}, "timeout_seconds": 180}'

# Metrics & Monitoring
print_header "Metrics & Monitoring"

run_curl "Prometheus metrics" "GET" "$BASE_URL/api/v1/metrics?format=prometheus"

if [ -n "$API_KEY" ]; then
    run_curl "JSON metrics (requires admin)" "GET" "$BASE_URL/api/v1/metrics?format=json" "" "-H 'X-API-Key: $API_KEY'"
    run_curl "Performance metrics (requires admin)" "GET" "$BASE_URL/api/v1/metrics/performance" "" "-H 'X-API-Key: $API_KEY'"
    run_curl "Cache statistics (requires admin)" "GET" "$BASE_URL/api/v1/metrics/cache" "" "-H 'X-API-Key: $API_KEY'"
else
    print_warning "Skipping admin-only metrics endpoints (API key not provided)"
fi

run_curl "Metrics health" "GET" "$BASE_URL/api/v1/metrics/health"

# Cache Testing
print_header "Cache Testing"

print_info "First request (cache MISS expected)..."
CACHE_TEST_QUERY='{"query": "test cache query", "timeout_seconds": 180}'
start_time=$(date +%s.%N)
response1=$(curl -s -X POST "$BASE_URL/api/v1/scrape" \
    -H "Content-Type: application/json" \
    -d "$CACHE_TEST_QUERY" \
    -w "\n%{http_code}" \
    -D /tmp/headers1.txt)
end_time=$(date +%s.%N)
if [ "$BC_AVAILABLE" = true ]; then
    duration1=$(echo "$end_time - $start_time" | bc)
else
    duration1="N/A"
fi
cache_status1=$(grep -i "X-Cache-Status" /tmp/headers1.txt | cut -d' ' -f2 | tr -d '\r\n' || echo "UNKNOWN")
print_info "Cache Status: $cache_status1"
if [ "$BC_AVAILABLE" = true ]; then
    print_info "Duration: ${duration1}s"
else
    print_info "Duration: N/A (bc not available)"
fi
echo ""

print_info "Waiting 2 seconds before second request..."
sleep 2

print_info "Second request (cache HIT expected)..."
start_time=$(date +%s.%N)
response2=$(curl -s -X POST "$BASE_URL/api/v1/scrape" \
    -H "Content-Type: application/json" \
    -d "$CACHE_TEST_QUERY" \
    -w "\n%{http_code}" \
    -D /tmp/headers2.txt)
end_time=$(date +%s.%N)
if [ "$BC_AVAILABLE" = true ]; then
    duration2=$(echo "$end_time - $start_time" | bc)
else
    duration2="N/A"
fi
cache_status2=$(grep -i "X-Cache-Status" /tmp/headers2.txt | cut -d' ' -f2 | tr -d '\r\n' || echo "UNKNOWN")
print_info "Cache Status: $cache_status2"
if [ "$BC_AVAILABLE" = true ]; then
    print_info "Duration: ${duration2}s"
    
    if [ "$cache_status2" = "HIT" ] && [ "$(echo "$duration2 < $duration1" | bc)" -eq 1 ]; then
        speedup=$(echo "scale=2; $duration1 / $duration2" | bc)
        print_success "Cache working! ${speedup}x faster with cache"
    else
        print_warning "Cache may not be working as expected"
    fi
else
    print_info "Duration: N/A (bc not available)"
    if [ "$cache_status2" = "HIT" ]; then
        print_success "Cache working! (speedup calculation unavailable without bc)"
    else
        print_warning "Cache may not be working as expected"
    fi
fi
echo ""

# Error Scenarios
print_header "Error Scenarios"

run_curl "Empty query (validation error)" "POST" "$BASE_URL/api/v1/scrape" \
    '{"query": ""}' "" "" "400"

# Build long query string safely
LONG_QUERY=$(python3 -c "print('a' * 1001)")
# Escape double quotes for JSON
ESCAPED_QUERY=$(echo "$LONG_QUERY" | sed 's/"/\\"/g')
run_curl "Query too long (validation error)" "POST" "$BASE_URL/api/v1/scrape" \
    "{\"query\": \"$ESCAPED_QUERY\"}" "" "" "400"

run_curl "Invalid timeout (validation error)" "POST" "$BASE_URL/api/v1/scrape" \
    '{"query": "Test query", "timeout_seconds": 20}' "" "" "400"

# Summary
print_header "Test Summary"
print_info "Base URL: $BASE_URL"
print_info "Total Tests: $TOTAL_TESTS"
if [ "$SUCCESSFUL_TESTS" -gt 0 ]; then
    print_success "Successful: $SUCCESSFUL_TESTS"
fi
if [ "$FAILED_TESTS" -gt 0 ]; then
    print_error "Failed: $FAILED_TESTS"
fi
if [ "$SAVE_RESPONSES" = true ]; then
    print_info "Responses saved to: demo_response_*.json"
fi

# Cleanup
rm -f /tmp/headers1.txt /tmp/headers2.txt

# Exit with non-zero status if there were failures
if [ "$FAILED_TESTS" -gt 0 ]; then
    exit 1
else
    exit 0
fi

