#!/bin/bash

# Quick environment validation script for AI Web Scraper project
# This script performs rapid environment validation during development
# Usage: bash scripts/quick_check.sh [--full] [--fix] [--help]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"

# Default options
FULL_CHECK=false
FIX_ISSUES=false
VERBOSE=false

# Function to print colored output
print_status() {
    local message="$1"
    local status="${2:-info}"
    
    case "$status" in
        "success")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "error")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "warning")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "info")
            echo -e "${CYAN}ℹ️  $message${NC}"
            ;;
        *)
            echo "   $message"
            ;;
    esac
}

# Function to print header
print_header() {
    echo -e "${BOLD}${CYAN}🔍 Quick Environment Check${NC}"
    echo -e "${CYAN}==============================${NC}"
    echo "Project: $(basename "$PROJECT_ROOT")"
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --full     Run full preflight check"
    echo "  --fix      Attempt to fix common issues"
    echo "  --verbose  Enable verbose output"
    echo "  --help     Show this help message"
    echo
    echo "Examples:"
    echo "  $0                    # Quick check"
    echo "  $0 --full            # Full validation"
    echo "  $0 --fix             # Fix issues automatically"
    echo "  $0 --full --verbose  # Full check with verbose output"
}

# Function to check if .env file exists
check_env_file() {
    if [[ ! -f "$ENV_FILE" ]]; then
        print_status ".env file not found" "error"
        print_status "Copy .env.example to .env and configure your values" "info"
        
        if [[ "$FIX_ISSUES" == true ]]; then
            if [[ -f "$ENV_EXAMPLE" ]]; then
                cp "$ENV_EXAMPLE" "$ENV_FILE"
                print_status "Created .env from .env.example" "success"
                print_status "Please edit .env with your actual values" "warning"
            else
                print_status ".env.example not found - cannot auto-fix" "error"
            fi
        fi
        return 1
    else
        print_status ".env file exists" "success"
        return 0
    fi
}

# Function to check Python version
check_python_version() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
        PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)
        
        if [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -ge 8 ]]; then
            print_status "Python $PYTHON_VERSION (OK)" "success"
            return 0
        else
            print_status "Python $PYTHON_VERSION (requires 3.8+)" "error"
            return 1
        fi
    else
        print_status "Python 3 not found" "error"
        return 1
    fi
}

# Function to check virtual environment
check_virtual_env() {
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        print_status "Virtual environment active: $(basename "$VIRTUAL_ENV")" "success"
        return 0
    else
        print_status "Virtual environment not activated" "warning"
        print_status "Run: python3 -m venv venv && source venv/bin/activate" "info"
        return 1
    fi
}

# Function to check requirements.txt
check_requirements() {
    if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
        print_status "requirements.txt not found" "error"
        return 1
    else
        print_status "requirements.txt exists" "success"
        return 0
    fi
}

# Function to check MongoDB connection
check_mongodb() {
    if command -v nc &> /dev/null; then
        if nc -z localhost 27017 2>/dev/null; then
            print_status "MongoDB running on localhost:27017" "success"
            return 0
        else
            print_status "MongoDB not running on localhost:27017" "warning"
            return 1
        fi
    elif command -v bash &> /dev/null && bash -c 'echo > /dev/tcp/localhost/27017' 2>/dev/null; then
        print_status "MongoDB running on localhost:27017" "success"
        return 0
    elif command -v telnet &> /dev/null; then
        if timeout 2 telnet localhost 27017 2>/dev/null | grep -q "Connected"; then
            print_status "MongoDB running on localhost:27017" "success"
            return 0
        else
            print_status "MongoDB not running on localhost:27017" "warning"
            return 1
        fi
    else
        print_status "Cannot check MongoDB (nc/bash/telnet not available)" "warning"
        return 1
    fi
}

# Function to check GEMINI_API_KEY
check_gemini_key() {
    if [[ -f "$ENV_FILE" ]]; then
        if grep -q "GEMINI_API_KEY=" "$ENV_FILE"; then
            API_KEY=$(grep "GEMINI_API_KEY=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
            if [[ -n "$API_KEY" && "$API_KEY" != "your_api_key_here" && "$API_KEY" != "gemini_api_key" ]]; then
                print_status "GEMINI_API_KEY is configured" "success"
                return 0
            else
                print_status "GEMINI_API_KEY is not properly configured" "error"
                return 1
            fi
        else
            print_status "GEMINI_API_KEY not found in .env" "error"
            return 1
        fi
    else
        print_status "Cannot check GEMINI_API_KEY (.env not found)" "error"
        return 1
    fi
}

# Function to check Python packages
check_python_packages() {
    local missing_packages=()
    
    # Check key packages
    local packages=("dotenv" "motor" "google.generativeai" "pydantic_settings" "fastapi" "uvicorn")
    
    for package in "${packages[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            print_status "✓ $package" "success"
        else
            print_status "✗ $package (not installed)" "error"
            missing_packages+=("$package")
        fi
    done
    
    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        print_status "Missing packages: ${missing_packages[*]}" "error"
        print_status "Run: pip install -r requirements.txt" "info"
        return 1
    else
        print_status "All required packages installed" "success"
        return 0
    fi
}

# Function to run Python validation
run_python_validation() {
    if [[ -f "$SCRIPT_DIR/validate_env.py" ]]; then
        print_status "Running environment validation..." "info"
        if python3 "$SCRIPT_DIR/validate_env.py" --project-root "$PROJECT_ROOT"; then
            print_status "Environment validation passed" "success"
            return 0
        else
            print_status "Environment validation failed" "error"
            return 1
        fi
    else
        print_status "validate_env.py not found" "warning"
        return 1
    fi
}

# Function to run full preflight check
run_full_check() {
    if [[ -f "$SCRIPT_DIR/preflight_check.py" ]]; then
        print_status "Running full preflight check..." "info"
        if python3 "$SCRIPT_DIR/preflight_check.py" --project-root "$PROJECT_ROOT"; then
            print_status "Full preflight check passed" "success"
            return 0
        else
            print_status "Full preflight check failed" "error"
            return 1
        fi
    else
        print_status "preflight_check.py not found" "error"
        return 1
    fi
}

# Function to fix common issues
fix_issues() {
    print_status "Attempting to fix common issues..." "info"
    
    # Create missing directories
    local dirs=("logs" "data" "temp")
    for dir in "${dirs[@]}"; do
        if [[ ! -d "$PROJECT_ROOT/$dir" ]]; then
            mkdir -p "$PROJECT_ROOT/$dir"
            print_status "Created directory: $dir" "success"
        fi
    done
    
    # Fix .env file if missing
    if [[ ! -f "$ENV_FILE" && -f "$ENV_EXAMPLE" ]]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        print_status "Created .env from .env.example" "success"
    fi
    
    # Fix permissions
    if [[ -d "$PROJECT_ROOT/logs" ]]; then
        chmod 755 "$PROJECT_ROOT/logs" 2>/dev/null || true
        print_status "Fixed logs directory permissions" "success"
    fi
    
    print_status "Fix attempts completed" "info"
}

# Function to print summary
print_summary() {
    local summary_exit_code="${1:-1}"
    echo
    echo -e "${BOLD}${CYAN}📊 Quick Check Summary${NC}"
    echo -e "${CYAN}=========================${NC}"
    
    # Use the exit_code from main function to determine success/failure
    if [[ $summary_exit_code -eq 0 ]]; then
        echo -e "${GREEN}${BOLD}🎉 Environment is ready!${NC}"
        echo -e "${GREEN}All critical checks passed${NC}"
        echo
        echo -e "${BOLD}Next Steps:${NC}"
        echo "  Start server: uvicorn app.main:app --reload"
        echo "  Access docs: http://localhost:8000/docs"
        echo "  Check health: curl http://localhost:8000/health"
    else
        echo -e "${RED}${BOLD}❌ Environment has issues${NC}"
        echo -e "${RED}Cannot start application - fix errors first${NC}"
        echo
        echo -e "${BOLD}Next Steps:${NC}"
        echo "  Fix errors above"
        echo "  Run: python scripts/fix_env.py"
        echo "  Re-run: $0"
    fi
}

# Main function
main() {
    local exit_code=0
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                FULL_CHECK=true
                shift
                ;;
            --fix)
                FIX_ISSUES=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    print_header
    
    # Run checks
    echo -e "${BOLD}Basic Checks:${NC}"
    
    check_env_file || exit_code=1
    check_python_version || exit_code=1
    check_virtual_env || exit_code=1
    check_requirements || exit_code=1
    
    echo
    echo -e "${BOLD}Service Checks:${NC}"
    
    check_mongodb || exit_code=1
    check_gemini_key || exit_code=1
    
    echo
    echo -e "${BOLD}Package Checks:${NC}"
    
    check_python_packages || exit_code=1
    
    # Run additional checks based on options
    if [[ "$FULL_CHECK" == true ]]; then
        echo
        echo -e "${BOLD}Full Validation:${NC}"
        run_full_check || exit_code=1
    else
        echo
        echo -e "${BOLD}Environment Validation:${NC}"
        run_python_validation || exit_code=1
    fi
    
    # Fix issues if requested
    if [[ "$FIX_ISSUES" == true ]]; then
        echo
        echo -e "${BOLD}Auto-Fix:${NC}"
        fix_issues
    fi
    
    # Print summary
    print_summary "$exit_code"
    
    exit $exit_code
}

# Run main function
main "$@"
