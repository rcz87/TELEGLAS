#!/bin/bash

# TELEGLAS VPS Readiness Check Script
# This script checks if the VPS environment is ready to run the bot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Function to print colored output
print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"
}

print_check() {
    echo -e "${BLUE}[CHECK]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((FAILED++))
}

print_warning() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1"
    ((WARNINGS++))
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check Python version
check_python() {
    print_check "Checking Python version..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            print_success "Python $PYTHON_VERSION (>= 3.8 required)"
        else
            print_fail "Python $PYTHON_VERSION found, but 3.8+ required"
            print_info "Install Python 3.8+: sudo apt install python3.11 python3.11-venv python3-pip"
        fi
    else
        print_fail "Python 3 not found"
        print_info "Install Python: sudo apt install python3 python3-venv python3-pip"
    fi
}

# Check pip
check_pip() {
    print_check "Checking pip..."
    if command -v pip3 &> /dev/null; then
        print_success "pip3 is installed"
    else
        print_fail "pip3 not found"
        print_info "Install pip: sudo apt install python3-pip"
    fi
}

# Check required directories
check_directories() {
    print_check "Checking required directories..."
    if [ -d "logs" ] && [ -d "data" ]; then
        print_success "Required directories (logs, data) exist"
    else
        print_warning "Missing directories (will be created)"
        print_info "Run: mkdir -p logs data"
    fi
}

# Check .env file
check_env_file() {
    print_check "Checking .env configuration file..."
    if [ -f ".env" ]; then
        print_success ".env file exists"

        # Check required variables
        print_check "Verifying required environment variables..."

        MISSING_VARS=()

        if ! grep -q "^COINGLASS_API_KEY=" .env || grep -q "^COINGLASS_API_KEY=$" .env || grep -q "^COINGLASS_API_KEY=your_" .env; then
            MISSING_VARS+=("COINGLASS_API_KEY")
        fi

        if ! grep -q "^TELEGRAM_BOT_TOKEN=" .env || grep -q "^TELEGRAM_BOT_TOKEN=$" .env || grep -q "^TELEGRAM_BOT_TOKEN=your_" .env; then
            MISSING_VARS+=("TELEGRAM_BOT_TOKEN")
        fi

        if [ ${#MISSING_VARS[@]} -eq 0 ]; then
            print_success "All required environment variables are configured"
        else
            print_fail "Missing or incomplete environment variables: ${MISSING_VARS[*]}"
            print_info "Edit .env file and set: ${MISSING_VARS[*]}"
        fi
    else
        print_fail ".env file not found"
        print_info "Create .env file: cp .env.example .env && nano .env"
    fi
}

# Check Python dependencies
check_dependencies() {
    print_check "Checking Python dependencies..."

    # Try to import critical modules
    python3 -c "
import sys
import importlib

modules = {
    'python-telegram-bot': 'telegram',
    'aiogram': 'aiogram',
    'aiohttp': 'aiohttp',
    'loguru': 'loguru',
    'python-dotenv': 'dotenv',
    'redis': 'redis',
    'aiosqlite': 'aiosqlite',
    'APScheduler': 'apscheduler',
}

missing = []
for package, module in modules.items():
    try:
        importlib.import_module(module)
    except ImportError:
        missing.append(package)

if missing:
    print('MISSING:' + ','.join(missing))
    sys.exit(1)
else:
    print('OK')
    sys.exit(0)
" 2>/dev/null

    if [ $? -eq 0 ]; then
        print_success "All Python dependencies are installed"
    else
        RESULT=$(python3 -c "
import sys
import importlib

modules = {
    'python-telegram-bot': 'telegram',
    'aiogram': 'aiogram',
    'aiohttp': 'aiohttp',
    'loguru': 'loguru',
    'python-dotenv': 'dotenv',
    'redis': 'redis',
    'aiosqlite': 'aiosqlite',
    'APScheduler': 'apscheduler',
}

missing = []
for package, module in modules.items():
    try:
        importlib.import_module(module)
    except ImportError:
        missing.append(package)

if missing:
    print('MISSING:' + ','.join(missing))
" 2>/dev/null)

        print_fail "Missing Python packages: ${RESULT#MISSING:}"
        print_info "Install dependencies: pip3 install -r requirements.txt"
    fi
}

# Check project imports
check_project_imports() {
    print_check "Checking project module imports..."

    python3 << 'PYEOF' 2>/dev/null
import sys
sys.path.insert(0, '.')

try:
    from config.settings import settings
    print("OK:config.settings")
except Exception as e:
    print(f"FAIL:config.settings:{e}")
    sys.exit(1)

try:
    from core.database import db_manager
    print("OK:core.database")
except Exception as e:
    print(f"FAIL:core.database:{e}")
    sys.exit(1)

try:
    from utils.auth import is_user_allowed
    print("OK:utils.auth")
except Exception as e:
    print(f"FAIL:utils.auth:{e}")
    sys.exit(1)

try:
    from utils.process_lock import ProcessLock
    print("OK:utils.process_lock")
except Exception as e:
    print(f"FAIL:utils.process_lock:{e}")
    sys.exit(1)
PYEOF

    if [ $? -eq 0 ]; then
        print_success "All project modules can be imported"
    else
        print_fail "Some project modules failed to import"
        print_info "Check for syntax errors or missing dependencies"
    fi
}

# Check disk space
check_disk_space() {
    print_check "Checking disk space..."
    AVAILABLE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')

    if [ "$AVAILABLE" -ge 5 ]; then
        print_success "Sufficient disk space: ${AVAILABLE}GB available"
    elif [ "$AVAILABLE" -ge 2 ]; then
        print_warning "Low disk space: ${AVAILABLE}GB available (5GB+ recommended)"
    else
        print_fail "Insufficient disk space: ${AVAILABLE}GB available (minimum 2GB required)"
    fi
}

# Check RAM
check_memory() {
    print_check "Checking available memory..."
    TOTAL_MEM=$(free -m | awk 'NR==2{print $2}')

    if [ "$TOTAL_MEM" -ge 2000 ]; then
        print_success "Sufficient memory: ${TOTAL_MEM}MB available"
    elif [ "$TOTAL_MEM" -ge 1000 ]; then
        print_warning "Low memory: ${TOTAL_MEM}MB available (2GB+ recommended)"
    else
        print_fail "Insufficient memory: ${TOTAL_MEM}MB available (minimum 1GB required)"
    fi
}

# Check network connectivity
check_network() {
    print_check "Checking network connectivity..."
    if ping -c 1 8.8.8.8 &> /dev/null; then
        print_success "Internet connection is working"
    else
        print_fail "No internet connection"
        print_info "Check network settings and firewall"
    fi
}

# Check if bot lock file exists
check_bot_running() {
    print_check "Checking if bot is already running..."
    if [ -f ".bot.lock" ]; then
        PID=$(cat .bot.lock 2>/dev/null)
        if kill -0 "$PID" 2>/dev/null; then
            print_warning "Bot is already running (PID: $PID)"
            print_info "Stop the bot first or remove stale lock file: rm .bot.lock"
        else
            print_warning "Stale lock file found (.bot.lock)"
            print_info "Remove it: rm .bot.lock"
        fi
    else
        print_success "No bot instance is currently running"
    fi
}

# Check git
check_git() {
    print_check "Checking git..."
    if command -v git &> /dev/null; then
        print_success "git is installed"

        if [ -d ".git" ]; then
            print_info "Git repository: $(git remote get-url origin 2>/dev/null || echo 'No remote configured')"
            print_info "Current branch: $(git branch --show-current 2>/dev/null || echo 'Unknown')"
        fi
    else
        print_warning "git not found (optional, but useful for updates)"
        print_info "Install git: sudo apt install git"
    fi
}

# Check systemd service
check_systemd_service() {
    print_check "Checking systemd service..."
    if [ -f "/etc/systemd/system/teleglas.service" ]; then
        print_success "systemd service file exists"

        if systemctl is-enabled teleglas.service &>/dev/null; then
            print_info "Service is enabled (will start on boot)"
        else
            print_warning "Service is not enabled"
            print_info "Enable it: sudo systemctl enable teleglas.service"
        fi

        if systemctl is-active teleglas.service &>/dev/null; then
            print_info "Service is currently running"
        else
            print_info "Service is not running"
        fi
    else
        print_warning "systemd service not configured (optional)"
        print_info "See VPS_DEPLOYMENT_INSTRUCTIONS.md for service setup"
    fi
}

# Main execution
main() {
    print_header "TELEGLAS VPS Readiness Check"

    # Navigate to script directory
    cd "$(dirname "$0")/.." || exit 1

    print_info "Checking VPS environment for TELEGLAS bot deployment..."
    print_info "Working directory: $(pwd)"
    echo ""

    # Run all checks
    check_python
    check_pip
    check_directories
    check_env_file
    check_dependencies
    check_project_imports
    check_disk_space
    check_memory
    check_network
    check_bot_running
    check_git
    check_systemd_service

    # Summary
    print_header "Summary"
    echo -e "${GREEN}Passed:${NC} $PASSED"
    echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
    echo -e "${RED}Failed:${NC} $FAILED"
    echo ""

    if [ $FAILED -eq 0 ]; then
        if [ $WARNINGS -eq 0 ]; then
            echo -e "${GREEN}✓ Your VPS is ready to run TELEGLAS bot!${NC}"
            echo -e "${BLUE}Run the bot with: python3 main.py${NC}"
        else
            echo -e "${YELLOW}⚠ Your VPS can run the bot, but there are warnings to address.${NC}"
            echo -e "${BLUE}You can still start the bot with: python3 main.py${NC}"
        fi
    else
        echo -e "${RED}✗ Your VPS is NOT ready yet. Please fix the failed checks above.${NC}"
        exit 1
    fi
}

# Run main function
main
