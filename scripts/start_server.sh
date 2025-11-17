#!/bin/bash

# Server startup script with environment validation and dependency checks
# Handles graceful server initialization with comprehensive pre-flight checks

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
DEFAULT_PORT=8000
DEFAULT_HOST="0.0.0.0"
DEFAULT_WORKERS=4
SERVER_PID=""

# Parse command line arguments
SKIP_VALIDATION=false
SKIP_HEALTH_CHECK=false
PRODUCTION_MODE=false
RELOAD=true
PORT=$DEFAULT_PORT
HOST=$DEFAULT_HOST
WORKERS=$DEFAULT_WORKERS

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
    if [ -n "$SERVER_PID" ]; then
        log_info "Stopping server (PID: $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
        log_success "Server stopped"
    fi
}

trap cleanup EXIT INT TERM

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --reload)
            RELOAD=true
            shift
            ;;
        --production)
            PRODUCTION_MODE=true
            RELOAD=false
            shift
            ;;
        --skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        --skip-health-check)
            SKIP_HEALTH_CHECK=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --port <port>              Custom port (default: $DEFAULT_PORT)"
            echo "  --host <host>              Custom host (default: $DEFAULT_HOST)"
            echo "  --workers <n>              Number of workers for production (default: $DEFAULT_WORKERS)"
            echo "  --reload                   Enable auto-reload for development (default: true)"
            echo "  --production               Production mode (disable reload, use workers)"
            echo "  --skip-validation          Skip environment validation"
            echo "  --skip-health-check        Skip post-startup health check"
            echo "  -h, --help                 Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                         # Development mode with auto-reload"
            echo "  $0 --production             # Production mode with workers"
            echo "  $0 --port 8080             # Custom port"
            echo "  $0 --skip-validation       # Skip validation (faster startup)"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Display startup banner
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}        AI Web Scraper API - Server Startup            ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Detect Python interpreter at the top
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    log_error "Python interpreter not found"
    exit 1
fi

# Phase 1: Environment Validation
if [ "$SKIP_VALIDATION" = false ]; then
    log_info "Phase 1: Environment Validation"
    
    if [ ! -f ".env" ]; then
        log_error ".env file not found. Please create it from .env.example"
        exit 1
    fi
    
    log_info "Running environment validation..."
    if ! "$PYTHON" scripts/preflight_check.py --skip-connections 2>/dev/null; then
        log_error "Environment validation failed"
        log_warning "Run '$PYTHON scripts/preflight_check.py' for details"
        exit 1
    fi
    log_success "Environment validation passed"
else
    log_warning "Skipping environment validation"
fi

# Phase 2: Dependency Check
log_info "Phase 2: Dependency Check"

# Validate Python version using detected interpreter
PYTHON_VERSION=$("$PYTHON" --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    log_error "Python 3.8+ is required. Found: $PYTHON_VERSION"
    exit 1
fi
log_success "Python version: $PYTHON_VERSION (using: $PYTHON)"

# Check virtual environment (optional but recommended)
if [ -z "${VIRTUAL_ENV:-}" ]; then
    log_warning "Virtual environment not activated (recommended)"
else
    log_success "Virtual environment: $VIRTUAL_ENV"
fi

# Check required packages using detected interpreter
log_info "Checking required packages..."
MISSING_PACKAGES=()

if ! "$PYTHON" -c "import fastapi" 2>/dev/null; then
    MISSING_PACKAGES+=("fastapi")
fi

if ! "$PYTHON" -c "import uvicorn" 2>/dev/null; then
    MISSING_PACKAGES+=("uvicorn")
fi

if ! "$PYTHON" -c "import motor" 2>/dev/null; then
    MISSING_PACKAGES+=("motor")
fi

if ! "$PYTHON" -c "import google.generativeai" 2>/dev/null; then
    MISSING_PACKAGES+=("google-generativeai")
fi

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    log_error "Missing required packages: ${MISSING_PACKAGES[*]}"
    log_info "Install with: pip install -r requirements.txt"
    exit 1
fi
log_success "All required packages installed"

# Phase 3: Service Availability Check
log_info "Phase 3: Service Availability Check"

log_info "Testing MongoDB connection..."
if "$PYTHON" scripts/test_connections.py --mongodb-only 2>/dev/null; then
    log_success "MongoDB connection successful"
else
    log_warning "MongoDB connection failed (will be tested during startup)"
fi

log_info "Testing Gemini API connection..."
if "$PYTHON" scripts/test_connections.py --gemini-only 2>/dev/null; then
    log_success "Gemini API connection successful"
else
    log_warning "Gemini API connection failed (will be tested during startup)"
fi

# Phase 4: Server Startup
log_info "Phase 4: Server Startup"

log_info "Starting server on $HOST:$PORT..."

if [ "$PRODUCTION_MODE" = true ]; then
    log_info "Production mode: $WORKERS workers, no reload"
    uvicorn app.main:app --host "$HOST" --port "$PORT" --workers "$WORKERS" &
else
    if [ "$RELOAD" = true ]; then
        log_info "Development mode: auto-reload enabled"
        uvicorn app.main:app --host "$HOST" --port "$PORT" --reload &
    else
        log_info "Development mode: no reload"
        uvicorn app.main:app --host "$HOST" --port "$PORT" &
    fi
fi

SERVER_PID=$!
log_success "Server started (PID: $SERVER_PID)"

# Phase 5: Post-Startup Verification
if [ "$SKIP_HEALTH_CHECK" = false ]; then
    log_info "Phase 5: Post-Startup Verification"
    log_info "Waiting for server to initialize (5 seconds)..."
    sleep 5
    
    log_info "Testing health endpoint..."
    MAX_RETRIES=10
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
            log_success "Server is ready and responding"
            break
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            log_info "Waiting for server... ($RETRY_COUNT/$MAX_RETRIES)"
            sleep 2
        else
            log_error "Server health check failed after $MAX_RETRIES attempts"
            exit 1
        fi
    done
else
    log_warning "Skipping post-startup health check"
fi

# Display success message
echo ""
log_success "╔════════════════════════════════════════════════════════════╗"
log_success "║                    Server Started Successfully              ║"
log_success "╚════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Server Information:${NC}"
echo "  • URL: http://$HOST:$PORT"
echo "  • API Documentation: http://$HOST:$PORT/docs"
echo "  • Alternative Docs: http://$HOST:$PORT/redoc"
echo "  • Health Check: http://$HOST:$PORT/health"
echo "  • Process ID: $SERVER_PID"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Wait for server process
wait $SERVER_PID

