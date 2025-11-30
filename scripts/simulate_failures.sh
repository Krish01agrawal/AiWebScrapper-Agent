#!/bin/bash
# Simulate infrastructure failures for error recovery testing
#
# This script provides commands to simulate various infrastructure failures
# including MongoDB downtime, Gemini API failures, and network issues.
#
# Usage:
#   ./scripts/simulate_failures.sh mongodb down
#   ./scripts/simulate_failures.sh gemini invalid-key
#   ./scripts/simulate_failures.sh restore-all

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_BACKUP="$PROJECT_ROOT/.env.backup"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Backup .env file
backup_env() {
    if [ -f "$ENV_FILE" ] && [ ! -f "$ENV_BACKUP" ]; then
        cp "$ENV_FILE" "$ENV_BACKUP"
        log_info "Backed up .env to .env.backup"
    fi
}

# Restore .env file
restore_env() {
    if [ -f "$ENV_BACKUP" ]; then
        cp "$ENV_BACKUP" "$ENV_FILE"
        log_info "Restored .env from backup"
        rm -f "$ENV_BACKUP"
    else
        log_warn "No .env backup found"
    fi
}

# MongoDB operations
mongodb_down() {
    log_info "Stopping MongoDB service..."
    
    # Try different methods to stop MongoDB
    if command -v docker &> /dev/null; then
        # Docker-based MongoDB
        if docker ps | grep -q mongo; then
            docker stop $(docker ps -q --filter ancestor=mongo:7.0) 2>/dev/null || true
            log_info "MongoDB Docker container stopped"
        else
            log_warn "No MongoDB Docker container found"
        fi
    elif command -v brew &> /dev/null && brew services list | grep -q mongodb-community; then
        # Homebrew MongoDB
        brew services stop mongodb-community
        log_info "MongoDB service stopped (Homebrew)"
    elif command -v systemctl &> /dev/null && systemctl is-active --quiet mongod; then
        # Systemd MongoDB
        sudo systemctl stop mongod
        log_info "MongoDB service stopped (systemd)"
    else
        log_warn "Could not find MongoDB service to stop"
        log_info "Please manually stop MongoDB for testing"
    fi
}

mongodb_up() {
    log_info "Starting MongoDB service..."
    
    # Try different methods to start MongoDB
    if command -v docker &> /dev/null; then
        # Docker-based MongoDB
        if docker ps -a | grep -q mongo; then
            docker start $(docker ps -aq --filter ancestor=mongo:7.0) 2>/dev/null || true
            log_info "MongoDB Docker container started"
        else
            log_warn "No MongoDB Docker container found"
        fi
    elif command -v brew &> /dev/null && brew services list | grep -q mongodb-community; then
        # Homebrew MongoDB
        brew services start mongodb-community
        log_info "MongoDB service started (Homebrew)"
    elif command -v systemctl &> /dev/null; then
        # Systemd MongoDB
        sudo systemctl start mongod
        log_info "MongoDB service started (systemd)"
    else
        log_warn "Could not find MongoDB service to start"
        log_info "Please manually start MongoDB"
    fi
}

# Gemini API key operations
gemini_invalid_key() {
    log_info "Setting invalid Gemini API key..."
    backup_env
    
    if [ -f "$ENV_FILE" ]; then
        # Replace or add invalid API key
        if grep -q "^GEMINI_API_KEY=" "$ENV_FILE"; then
            sed -i.bak 's/^GEMINI_API_KEY=.*/GEMINI_API_KEY=invalid_key_12345/' "$ENV_FILE"
        else
            echo "GEMINI_API_KEY=invalid_key_12345" >> "$ENV_FILE"
        fi
        log_info "Gemini API key set to invalid value"
        log_warn "Remember to restore the key after testing!"
    else
        log_error ".env file not found"
        exit 1
    fi
}

gemini_restore_key() {
    log_info "Restoring Gemini API key..."
    restore_env
}

# Network operations
network_block() {
    log_warn "Network blocking requires root privileges and may affect system connectivity"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Network blocking cancelled"
        return
    fi
    
    log_info "Blocking network connections (this may require sudo)..."
    log_warn "This is a destructive operation. Use with caution."
    
    # Note: Actual network blocking would require iptables/firewall rules
    # This is a placeholder that logs the action
    log_info "Network blocking simulation (not actually blocking for safety)"
    log_info "To actually block, you would use: sudo iptables -A OUTPUT -j DROP"
}

network_restore() {
    log_info "Restoring network connectivity..."
    log_info "Network restore simulation (not actually restoring)"
    log_info "To actually restore, you would use: sudo iptables -F"
}

# Health check
health_check() {
    log_info "Checking service health..."
    
    # Check MongoDB
    if command -v docker &> /dev/null; then
        if docker ps | grep -q mongo; then
            log_info "MongoDB: Running (Docker)"
        else
            log_warn "MongoDB: Not running (Docker)"
        fi
    elif command -v brew &> /dev/null && brew services list | grep -q mongodb-community; then
        if brew services list | grep mongodb-community | grep -q started; then
            log_info "MongoDB: Running (Homebrew)"
        else
            log_warn "MongoDB: Not running (Homebrew)"
        fi
    elif command -v systemctl &> /dev/null; then
        if systemctl is-active --quiet mongod; then
            log_info "MongoDB: Running (systemd)"
        else
            log_warn "MongoDB: Not running (systemd)"
        fi
    else
        log_warn "MongoDB: Status unknown"
    fi
    
    # Check FastAPI server
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        log_info "FastAPI Server: Running"
    else
        log_warn "FastAPI Server: Not running"
    fi
    
    # Check .env file
    if [ -f "$ENV_FILE" ]; then
        if grep -q "^GEMINI_API_KEY=invalid" "$ENV_FILE" 2>/dev/null; then
            log_warn "Gemini API Key: Invalid (for testing)"
        elif grep -q "^GEMINI_API_KEY=" "$ENV_FILE" 2>/dev/null; then
            log_info "Gemini API Key: Configured"
        else
            log_warn "Gemini API Key: Not configured"
        fi
    else
        log_warn ".env file: Not found"
    fi
}

# Restore all services
restore_all() {
    log_info "Restoring all services to normal state..."
    
    mongodb_up
    gemini_restore_key
    
    log_info "All services restored"
}

# Main command handler
main() {
    local command="${1:-}"
    local subcommand="${2:-}"
    
    case "$command" in
        mongodb)
            case "$subcommand" in
                down)
                    mongodb_down
                    ;;
                up)
                    mongodb_up
                    ;;
                *)
                    echo "Usage: $0 mongodb {down|up}"
                    exit 1
                    ;;
            esac
            ;;
        gemini)
            case "$subcommand" in
                invalid-key)
                    gemini_invalid_key
                    ;;
                restore-key)
                    gemini_restore_key
                    ;;
                *)
                    echo "Usage: $0 gemini {invalid-key|restore-key}"
                    exit 1
                    ;;
            esac
            ;;
        network)
            case "$subcommand" in
                block)
                    network_block
                    ;;
                restore)
                    network_restore
                    ;;
                *)
                    echo "Usage: $0 network {block|restore}"
                    exit 1
                    ;;
            esac
            ;;
        health-check)
            health_check
            ;;
        restore-all)
            restore_all
            ;;
        *)
            echo "Error Recovery Failure Simulator"
            echo ""
            echo "Usage: $0 {command} [subcommand]"
            echo ""
            echo "Commands:"
            echo "  mongodb {down|up}          Stop or start MongoDB service"
            echo "  gemini {invalid-key|restore-key}  Set invalid or restore Gemini API key"
            echo "  network {block|restore}   Simulate network issues (requires confirmation)"
            echo "  health-check              Check status of all services"
            echo "  restore-all               Restore all services to normal state"
            echo ""
            echo "Examples:"
            echo "  $0 mongodb down"
            echo "  $0 gemini invalid-key"
            echo "  $0 health-check"
            echo "  $0 restore-all"
            exit 1
            ;;
    esac
}

# Trap to restore services on exit (optional, commented out for safety)
# trap restore_all EXIT

# Run main function
main "$@"

