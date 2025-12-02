#!/bin/bash

# CryptoSat Bot Deployment Script
# This script automates the deployment of CryptoSat Bot using Docker Compose

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from template..."
        cp .env.example .env
        print_warning "Please edit .env file with your configuration before continuing."
        print_warning "Required variables: COINGLASS_API_KEY, TELEGRAM_BOT_TOKEN"
        read -p "Press Enter after editing .env file..."
    fi
    
    if [ ! -s ".env" ]; then
        print_error ".env file is empty. Please configure it first."
        exit 1
    fi
    
    print_success ".env file found and configured"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    mkdir -p data logs
    chmod 755 data logs
    print_success "Directories created"
}

# Build and start the bot
deploy_bot() {
    print_status "Building and starting CryptoSat Bot..."
    
    # Stop existing container if running
    docker-compose down 2>/dev/null || true
    
    # Build new image
    print_status "Building Docker image..."
    docker-compose build --no-cache
    
    # Start the bot
    print_status "Starting CryptoSat Bot..."
    docker-compose up -d
    
    # Wait a moment for container to start
    sleep 5
    
    # Check if container is running
    if docker-compose ps | grep -q "Up"; then
        print_success "CryptoSat Bot is now running!"
        print_status "Container status:"
        docker-compose ps
    else
        print_error "Failed to start CryptoSat Bot. Check logs:"
        docker-compose logs
        exit 1
    fi
}

# Show logs
show_logs() {
    print_status "Showing recent logs (Ctrl+C to exit):"
    docker-compose logs -f --tail=50
}

# Stop the bot
stop_bot() {
    print_status "Stopping CryptoSat Bot..."
    docker-compose down
    print_success "CryptoSat Bot stopped"
}

# Update the bot
update_bot() {
    print_status "Updating CryptoSat Bot..."
    
    # Pull latest code (if in git repository)
    if [ -d ".git" ]; then
        print_status "Pulling latest code..."
        git pull origin main
    fi
    
    # Rebuild and restart
    deploy_bot
    print_success "CryptoSat Bot updated and restarted"
}

# Show help
show_help() {
    echo "CryptoSat Bot Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy     Deploy the bot (default)"
    echo "  stop       Stop the running bot"
    echo "  restart    Restart the bot"
    echo "  logs       Show bot logs"
    echo "  update     Update and restart the bot"
    echo "  status     Show bot status"
    echo "  help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 deploy    # Deploy the bot"
    echo "  $0 logs      # Show logs"
    echo "  $0 stop      # Stop the bot"
}

# Show status
show_status() {
    print_status "CryptoSat Bot Status:"
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}● Bot is running${NC}"
        docker-compose ps
    else
        echo -e "${RED}● Bot is not running${NC}"
    fi
}

# Main script logic
main() {
    case "${1:-deploy}" in
        "deploy")
            check_docker
            check_env_file
            create_directories
            deploy_bot
            ;;
        "stop")
            stop_bot
            ;;
        "restart")
            stop_bot
            deploy_bot
            ;;
        "logs")
            show_logs
            ;;
        "update")
            check_docker
            check_env_file
            update_bot
            ;;
        "status")
            show_status
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
