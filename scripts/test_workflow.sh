#!/bin/bash

# Comprehensive workflow test script
# Tests complete workflow from server startup to scrape endpoint validation

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
DEFAULT_PORT=8000
DEFAULT_TIMEOUT=180
PORT=$DEFAULT_PORT
TIMEOUT=$DEFAULT_TIMEOUT
SKIP_VALIDATION=false
KEEP_SERVER=false
VERBOSE=false
SAVE_RESPONSES=false
SERVER_PID=""
TEST_RESULTS_DIR="test_results_$(date +%Y%m%d_%H%M%S)"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

cleanup() {
    if [ "$KEEP_SERVER" = false ] && [ -n "$SERVER_PID" ]; then
        log_info "Stopping server (PID: $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
        log_success "Server stopped"
    fi
    
    if [ "$SAVE_RESPONSES" = false ]; then
        # Clean up temporary files
        rm -f ai_tools_response.json mutual_funds_response.json 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        --keep-server)
            KEEP_SERVER=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --save-responses)
            SAVE_RESPONSES=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-validation    Skip environment validation"
            echo "  --keep-server        Don't stop server after tests"
            echo "  --port <port>        Custom port (default: $DEFAULT_PORT)"
            echo "  --timeout <seconds>  Request timeout (default: $DEFAULT_TIMEOUT)"
            echo "  --verbose            Show detailed output"
            echo "  --save-responses     Keep response files for analysis"
            echo "  -h, --help           Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Test summary tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test phase tracking
declare -A PHASE_RESULTS

# Display banner
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}     AI Web Scraper API - Workflow Integration Test     ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Phase 1: Environment Validation
log_info "Phase 1: Environment Validation"
PHASE_START=$(date +%s)

if [ "$SKIP_VALIDATION" = false ]; then
    if ! python scripts/preflight_check.py --skip-connections 2>/dev/null; then
        log_error "Environment validation failed"
        log_warning "Run 'python scripts/preflight_check.py' for details"
        PHASE_RESULTS["Phase 1"]="FAIL"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        exit 3
    fi
    log_success "Environment validation passed"
    PHASE_RESULTS["Phase 1"]="PASS"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    log_warning "Skipping environment validation"
    PHASE_RESULTS["Phase 1"]="SKIP"
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))
PHASE_DURATION=$(($(date +%s) - PHASE_START))
log_info "Phase 1 completed in ${PHASE_DURATION}s"
echo ""

# Phase 2: Server Startup
log_info "Phase 2: Server Startup"
PHASE_START=$(date +%s)

log_info "Starting server on port $PORT..."
uvicorn app.main:app --host 0.0.0.0 --port "$PORT" > /dev/null 2>&1 &
SERVER_PID=$!

log_info "Waiting for server to initialize..."
MAX_WAIT=30
WAIT_COUNT=0

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        log_success "Server is ready and responding"
        PHASE_RESULTS["Phase 2"]="PASS"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        break
    fi
    
    WAIT_COUNT=$((WAIT_COUNT + 1))
    if [ $WAIT_COUNT -lt $MAX_WAIT ]; then
        sleep 1
    fi
done

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    log_error "Server failed to start within ${MAX_WAIT} seconds"
    PHASE_RESULTS["Phase 2"]="FAIL"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    exit 2
fi

# Test root endpoint
if curl -s "http://localhost:$PORT/" > /dev/null 2>&1; then
    log_success "Root endpoint is accessible"
else
    log_warning "Root endpoint test failed"
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))
PHASE_DURATION=$(($(date +%s) - PHASE_START))
log_info "Phase 2 completed in ${PHASE_DURATION}s"
echo ""

# Phase 3: Health Check Testing
log_info "Phase 3: Health Check Testing"
PHASE_START=$(date +%s)

PHASE_3_FAILED=false

# Test basic health
log_info "Testing basic health endpoint..."
if curl -s "http://localhost:$PORT/health" | grep -q '"status"'; then
    log_success "Basic health check passed"
else
    log_error "Basic health check failed"
    PHASE_3_FAILED=true
fi

# Test database health
log_info "Testing database health endpoint..."
if curl -s "http://localhost:$PORT/health/database" | grep -q '"status"'; then
    log_success "Database health check passed"
else
    log_warning "Database health check failed (may be expected if MongoDB not configured)"
fi

# Test cache health
log_info "Testing cache health endpoint..."
if curl -s "http://localhost:$PORT/health/cache" | grep -q '"status"'; then
    log_success "Cache health check passed"
else
    log_warning "Cache health check failed"
fi

# Test workflow health
log_info "Testing workflow health endpoint..."
if curl -s "http://localhost:$PORT/api/v1/scrape/health" | grep -q '"status"'; then
    log_success "Workflow health check passed"
else
    log_warning "Workflow health check failed"
fi

if [ "$PHASE_3_FAILED" = true ]; then
    PHASE_RESULTS["Phase 3"]="FAIL"
    FAILED_TESTS=$((FAILED_TESTS + 1))
else
    PHASE_RESULTS["Phase 3"]="PASS"
    PASSED_TESTS=$((PASSED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))
PHASE_DURATION=$(($(date +%s) - PHASE_START))
log_info "Phase 3 completed in ${PHASE_DURATION}s"
echo ""

# Phase 4: Sample Query Testing
log_info "Phase 4: Sample Query Testing"
PHASE_START=$(date +%s)

# Create results directory if saving responses
if [ "$SAVE_RESPONSES" = true ]; then
    mkdir -p "$TEST_RESULTS_DIR"
fi

# Track individual query results
AI_TOOLS_PASSED=false
MUTUAL_FUNDS_PASSED=false

# Test AI tools query
log_info "Testing AI tools query..."
AI_TOOLS_RESPONSE=$(curl -s -X POST "http://localhost:$PORT/api/v1/scrape" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"Best AI agents for coding\", \"timeout_seconds\": $TIMEOUT}")

    if echo "$AI_TOOLS_RESPONSE" | grep -q '"status".*"success"'; then
        log_success "AI tools query test passed"
        AI_TOOLS_PASSED=true
        
        if echo "$AI_TOOLS_RESPONSE" | grep -q '"category".*"ai_tools"'; then
            log_success "Category classification correct (ai_tools)"
        else
            log_warning "Category classification may be incorrect"
        fi
        
        # Comment 2: Always write to root for CI, optionally copy to timestamped directory
        echo "$AI_TOOLS_RESPONSE" | jq . > ai_tools_response.json 2>/dev/null || echo "$AI_TOOLS_RESPONSE" > ai_tools_response.json
        if [ "$SAVE_RESPONSES" = true ]; then
            mkdir -p "$TEST_RESULTS_DIR"
            cp ai_tools_response.json "$TEST_RESULTS_DIR/ai_tools_response.json"
        fi
else
    log_error "AI tools query test failed"
    if [ "$VERBOSE" = true ]; then
        echo "$AI_TOOLS_RESPONSE" | head -20
    fi
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test mutual funds query
log_info "Testing mutual funds query..."
MUTUAL_FUNDS_RESPONSE=$(curl -s -X POST "http://localhost:$PORT/api/v1/scrape" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"Best mutual funds for beginners\", \"timeout_seconds\": $TIMEOUT}")

    if echo "$MUTUAL_FUNDS_RESPONSE" | grep -q '"status".*"success"'; then
        log_success "Mutual funds query test passed"
        MUTUAL_FUNDS_PASSED=true
        
        if echo "$MUTUAL_FUNDS_RESPONSE" | grep -q '"category".*"mutual_funds"'; then
            log_success "Category classification correct (mutual_funds)"
        else
            log_warning "Category classification may be incorrect"
        fi
        
        # Comment 2: Always write to root for CI, optionally copy to timestamped directory
        echo "$MUTUAL_FUNDS_RESPONSE" | jq . > mutual_funds_response.json 2>/dev/null || echo "$MUTUAL_FUNDS_RESPONSE" > mutual_funds_response.json
        if [ "$SAVE_RESPONSES" = true ]; then
            mkdir -p "$TEST_RESULTS_DIR"
            cp mutual_funds_response.json "$TEST_RESULTS_DIR/mutual_funds_response.json"
        fi
else
    log_error "Mutual funds query test failed"
    if [ "$VERBOSE" = true ]; then
        echo "$MUTUAL_FUNDS_RESPONSE" | head -20
    fi
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Phase 4 passes only if both queries succeed
if [ "$AI_TOOLS_PASSED" = true ] && [ "$MUTUAL_FUNDS_PASSED" = true ]; then
    PHASE_RESULTS["Phase 4"]="PASS"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    PHASE_RESULTS["Phase 4"]="FAIL"
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))
PHASE_DURATION=$(($(date +%s) - PHASE_START))
log_info "Phase 4 completed in ${PHASE_DURATION}s"
echo ""

# Phase 5: Response Validation
log_info "Phase 5: Response Validation"
PHASE_START=$(date +%s)

# Comment 2: Files are always at root level for CI compatibility
RESPONSE_FILE_1="ai_tools_response.json"
RESPONSE_FILE_2="mutual_funds_response.json"

VALIDATION_PASSED=true

if [ -f "$RESPONSE_FILE_1" ]; then
    log_info "Validating AI tools response..."
    if python scripts/validate_response_schema.py --response-file "$RESPONSE_FILE_1" > /dev/null 2>&1; then
        log_success "AI tools response validation passed"
    else
        log_error "AI tools response validation failed"
        VALIDATION_PASSED=false
    fi
fi

if [ -f "$RESPONSE_FILE_2" ]; then
    log_info "Validating mutual funds response..."
    if python scripts/validate_response_schema.py --response-file "$RESPONSE_FILE_2" > /dev/null 2>&1; then
        log_success "Mutual funds response validation passed"
    else
        log_error "Mutual funds response validation failed"
        VALIDATION_PASSED=false
    fi
fi

if [ "$VALIDATION_PASSED" = true ]; then
    PHASE_RESULTS["Phase 5"]="PASS"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    PHASE_RESULTS["Phase 5"]="FAIL"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))
PHASE_DURATION=$(($(date +%s) - PHASE_START))
log_info "Phase 5 completed in ${PHASE_DURATION}s"
echo ""

# Phase 6: Workflow Stage Verification
log_info "Phase 6: Workflow Stage Verification"
PHASE_START=$(date +%s)

PHASE_6_FAILED=false
REQUIRED_STAGES=("query_processing" "web_scraping" "ai_processing")

if [ -f "$RESPONSE_FILE_1" ]; then
    log_info "Extracting stage timings from AI tools response..."
    
    # Check for required stages using jq if available, otherwise use grep
    if command -v jq >/dev/null 2>&1; then
        STAGES=$(jq -r '.execution_metadata.stages_timing | keys[]' "$RESPONSE_FILE_1" 2>/dev/null || echo "")
        if [ -n "$STAGES" ]; then
            log_success "Found stages: $(echo $STAGES | tr '\n' ' ')"
            
            # Comment 5: Track missing required stages and fail if any are missing
            MISSING_REQUIRED_STAGES=()
            for stage in "${REQUIRED_STAGES[@]}"; do
                if echo "$STAGES" | grep -q "^${stage}$"; then
                    log_success "Required stage found: $stage"
                    # Validate stage duration is non-negative
                    STAGE_DURATION=$(jq -r ".execution_metadata.stages_timing[\"$stage\"]" "$RESPONSE_FILE_1" 2>/dev/null || echo "")
                    if [ -n "$STAGE_DURATION" ] && [ "$(echo "$STAGE_DURATION < 0" | bc 2>/dev/null || echo 0)" = "1" ]; then
                        log_error "Invalid duration for stage $stage: $STAGE_DURATION (must be non-negative)"
                        PHASE_6_FAILED=true
                    fi
                else
                    log_error "Required stage missing: $stage"
                    MISSING_REQUIRED_STAGES+=("$stage")
                    PHASE_6_FAILED=true
                fi
            done
            
            if [ ${#MISSING_REQUIRED_STAGES[@]} -gt 0 ]; then
                log_error "Missing required stages: ${MISSING_REQUIRED_STAGES[*]}"
            fi
        else
            log_error "Could not extract stage timings from response"
            PHASE_6_FAILED=true
        fi
    else
        log_warning "jq not available, skipping detailed stage verification"
        # Without jq, we can't verify stages, so we'll mark as failed to be safe
        PHASE_6_FAILED=true
    fi
else
    log_error "Response file not found: $RESPONSE_FILE_1"
    PHASE_6_FAILED=true
fi

# Comment 5: Set phase result based on whether all required stages were found
if [ "$PHASE_6_FAILED" = true ]; then
    PHASE_RESULTS["Phase 6"]="FAIL"
    FAILED_TESTS=$((FAILED_TESTS + 1))
else
    PHASE_RESULTS["Phase 6"]="PASS"
    PASSED_TESTS=$((PASSED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))
PHASE_DURATION=$(($(date +%s) - PHASE_START))
log_info "Phase 6 completed in ${PHASE_DURATION}s"
echo ""

# Phase 7: Cache Testing
log_info "Phase 7: Cache Testing"
PHASE_START=$(date +%s)

log_info "Sending first request (expected: cache MISS)..."
FIRST_HEADERS=$(curl -s -D- -X POST "http://localhost:$PORT/api/v1/scrape" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"Test query for caching\", \"timeout_seconds\": $TIMEOUT}" | head -n 20)
FIRST_CACHE_STATUS=$(echo "$FIRST_HEADERS" | grep -i "X-Cache-Status" | cut -d' ' -f2 | tr -d '\r' | tr '[:lower:]' '[:upper:]')

sleep 2

log_info "Sending second request (expected: cache HIT)..."
SECOND_HEADERS=$(curl -s -D- -X POST "http://localhost:$PORT/api/v1/scrape" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"Test query for caching\", \"timeout_seconds\": $TIMEOUT}" | head -n 20)
SECOND_CACHE_STATUS=$(echo "$SECOND_HEADERS" | grep -i "X-Cache-Status" | cut -d' ' -f2 | tr -d '\r' | tr '[:lower:]' '[:upper:]')

# Comment 7: Check cache headers - first should be MISS, second should be HIT
CACHE_TEST_PASSED=false
if [ "$FIRST_CACHE_STATUS" = "MISS" ] && [ "$SECOND_CACHE_STATUS" = "HIT" ]; then
    log_success "Cache test passed (first: MISS, second: HIT)"
    CACHE_TEST_PASSED=true
elif [ -z "$FIRST_CACHE_STATUS" ] || [ -z "$SECOND_CACHE_STATUS" ]; then
    log_error "Cache test failed (cache headers not found in response)"
    log_warning "First cache status: ${FIRST_CACHE_STATUS:-NOT_FOUND}"
    log_warning "Second cache status: ${SECOND_CACHE_STATUS:-NOT_FOUND}"
else
    log_error "Cache test failed (unexpected cache status)"
    log_warning "First cache status: $FIRST_CACHE_STATUS (expected: MISS)"
    log_warning "Second cache status: $SECOND_CACHE_STATUS (expected: HIT)"
fi

if [ "$CACHE_TEST_PASSED" = true ]; then
    PHASE_RESULTS["Phase 7"]="PASS"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    PHASE_RESULTS["Phase 7"]="FAIL"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))
PHASE_DURATION=$(($(date +%s) - PHASE_START))
log_info "Phase 7 completed in ${PHASE_DURATION}s"
echo ""

# Phase 8: Real-World Scenario Testing
log_info "Phase 8: Real-World Scenario Testing"
PHASE_START=$(date +%s)

log_info "Running real-world scenario tests..."
if python scripts/test_real_world_scenarios.py --all --save-report --verbose > /dev/null 2>&1; then
    log_success "Real-world scenario tests passed"
    PHASE_RESULTS["Phase 8"]="PASS"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    log_error "Real-world scenario tests failed"
    PHASE_RESULTS["Phase 8"]="FAIL"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))
PHASE_DURATION=$(($(date +%s) - PHASE_START))
log_info "Phase 8 completed in ${PHASE_DURATION}s"
echo ""

# Phase 9: Performance Benchmarking
log_info "Phase 9: Performance Benchmarking"
PHASE_START=$(date +%s)

log_info "Running performance benchmarks..."
if python scripts/test_real_world_scenarios.py --performance --save-report --verbose > /dev/null 2>&1; then
    log_success "Performance benchmarks passed"
    PHASE_RESULTS["Phase 9"]="PASS"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    log_warning "Performance benchmarks had warnings"
    PHASE_RESULTS["Phase 9"]="WARN"
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))
PHASE_DURATION=$(($(date +%s) - PHASE_START))
log_info "Phase 9 completed in ${PHASE_DURATION}s"
echo ""

# Test Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}                    TEST SUMMARY                        ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

printf "%-30s %-10s\n" "Phase" "Status"
echo "------------------------------------------------------------"

for phase in "Phase 1" "Phase 2" "Phase 3" "Phase 4" "Phase 5" "Phase 6" "Phase 7" "Phase 8" "Phase 9"; do
    status="${PHASE_RESULTS[$phase]:-UNKNOWN}"
    if [ "$status" = "PASS" ]; then
        printf "%-30s ${GREEN}%-10s${NC}\n" "$phase" "$status"
    elif [ "$status" = "FAIL" ]; then
        printf "%-30s ${RED}%-10s${NC}\n" "$phase" "$status"
    else
        printf "%-30s ${YELLOW}%-10s${NC}\n" "$phase" "$status"
    fi
done

echo ""
echo "Overall Results:"
echo "  Total Tests: $TOTAL_TESTS"
echo "  Passed: $PASSED_TESTS"
echo "  Failed: $FAILED_TESTS"

if [ $TOTAL_TESTS -gt 0 ]; then
    SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo "  Success Rate: ${SUCCESS_RATE}%"
fi

if [ "$SAVE_RESPONSES" = true ]; then
    echo ""
    echo "Response files saved to: $TEST_RESULTS_DIR"
fi

echo ""

# Final status
if [ $FAILED_TESTS -eq 0 ]; then
    log_success "All tests passed!"
    exit 0
else
    log_error "Some tests failed"
    exit 1
fi

