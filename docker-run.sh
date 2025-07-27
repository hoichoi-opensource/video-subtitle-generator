#!/bin/bash
# Convenience script to run subtitle generator in Docker
# OS-agnostic through Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    echo -e "${2}${1}${NC}"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_message "❌ Docker is not installed. Please install Docker first." "$RED"
    print_message "Visit: https://docs.docker.com/get-docker/" "$YELLOW"
    exit 1
fi

# Check if docker compose is installed (prioritize modern syntax)
if ! docker compose version &> /dev/null; then
    # Fallback to legacy docker-compose
    if ! command -v docker-compose &> /dev/null; then
        print_message "❌ Docker Compose is not installed." "$RED"
        print_message "Install Docker Desktop or docker-compose-plugin" "$YELLOW"
        exit 1
    fi
    DOCKER_COMPOSE="docker-compose"
    print_message "⚠️  Using legacy docker-compose. Consider upgrading to 'docker compose'" "$YELLOW"
else
    DOCKER_COMPOSE="docker compose"
fi

# Create data directories if they don't exist
print_message "📁 Setting up data directories..." "$GREEN"
mkdir -p data/{input,output,logs,config,temp,jobs}

# Check for service account
if [ ! -f "data/config/service-account.json" ]; then
    print_message "⚠️  No service account found at data/config/service-account.json" "$YELLOW"
    print_message "   Please copy your Google Cloud service account JSON to this location." "$YELLOW"
    print_message "   Example: cp /path/to/service-account.json data/config/" "$YELLOW"
    echo ""
fi

# Build image if needed
if [[ "$(docker images -q video-subtitle-generator:latest 2> /dev/null)" == "" ]]; then
    print_message "🔨 Building Docker image (first time only)..." "$GREEN"
    $DOCKER_COMPOSE build
fi

# Parse command line arguments
if [ $# -eq 0 ]; then
    # No arguments - run interactive mode
    print_message "🎬 Starting Video Subtitle Generator (Interactive Mode)..." "$GREEN"
    $DOCKER_COMPOSE run --rm subtitle-generator
elif [ "$1" == "shell" ]; then
    # Shell access
    print_message "🔧 Opening shell in container..." "$GREEN"
    $DOCKER_COMPOSE run --rm subtitle-generator bash
elif [ "$1" == "health" ]; then
    # Health check
    print_message "🏥 Running health check..." "$GREEN"
    $DOCKER_COMPOSE run --rm subtitle-generator python -c "
from src.health_checker import quick_health_check
import json
print(json.dumps(quick_health_check(), indent=2))
"
elif [ "$1" == "daemon" ]; then
    # Run as daemon
    print_message "🚀 Starting as background service..." "$GREEN"
    $DOCKER_COMPOSE up -d
    print_message "✅ Service started. View logs with: docker compose logs -f" "$GREEN"
elif [ "$1" == "stop" ]; then
    # Stop daemon
    print_message "🛑 Stopping service..." "$YELLOW"
    $DOCKER_COMPOSE down
elif [ "$1" == "logs" ]; then
    # View logs
    $DOCKER_COMPOSE logs -f
elif [ "$1" == "process" ]; then
    # Process video with remaining arguments
    shift
    print_message "🎥 Processing video..." "$GREEN"
    $DOCKER_COMPOSE run --rm subtitle-generator python main.py "$@"
else
    # Pass all arguments to main.py
    print_message "🎬 Running with custom arguments..." "$GREEN"
    $DOCKER_COMPOSE run --rm subtitle-generator python main.py "$@"
fi