#!/bin/bash

# Video Subtitle Generator Setup Script
# Prepares the environment for running the subtitle generator

set -e  # Exit on any error

echo "🎬 Video Subtitle Generator Setup"
echo "=================================="

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

# Check if Docker is installed and running
check_docker() {
    print_status "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker from https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker Desktop."
        exit 1
    fi
    
    print_success "Docker is installed and running"
}

# Check Docker Compose
check_docker_compose() {
    print_status "Checking Docker Compose..."
    
    if docker compose version &> /dev/null; then
        print_success "Docker Compose v2 is available"
    elif docker-compose version &> /dev/null; then
        print_warning "Using legacy docker-compose. Consider upgrading to Docker Compose v2"
    else
        print_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
}

# Create required directories
create_directories() {
    print_status "Creating required directories..."
    
    directories=("data/input" "data/output" "data/config" "data/logs" "data/temp" "data/jobs")
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "Created directory: $dir"
        else
            print_status "Directory already exists: $dir"
        fi
    done
    
    # Create .gitkeep files to preserve empty directories
    for dir in "${directories[@]}"; do
        if [ ! -f "$dir/.gitkeep" ]; then
            touch "$dir/.gitkeep"
        fi
    done
}

# Setup environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.template" ]; then
            cp ".env.template" ".env"
            print_success "Created .env file from template"
            print_warning "Please edit .env file with your Google Cloud credentials and settings"
        else
            print_warning ".env.template not found. You'll need to create .env manually"
        fi
    else
        print_status ".env file already exists"
    fi
}

# Check for service account file
check_service_account() {
    print_status "Checking for Google Cloud service account..."
    
    if [ ! -f "service-account.json" ] && [ ! -f "data/config/service-account.json" ]; then
        print_warning "Service account file not found"
        echo ""
        echo "📋 To complete setup:"
        echo "1. Go to Google Cloud Console"
        echo "2. Navigate to IAM & Admin > Service Accounts"
        echo "3. Create or select a service account"
        echo "4. Download the JSON key file"
        echo "5. Save it as 'service-account.json' in the project root"
        echo "   OR save it as 'data/config/service-account.json'"
        echo ""
        echo "🔗 Guide: https://cloud.google.com/iam/docs/keys-create-delete"
    else
        print_success "Service account file found"
    fi
}

# Test Docker setup
test_docker_setup() {
    print_status "Testing Docker setup..."
    
    if docker compose config &> /dev/null; then
        print_success "Docker Compose configuration is valid"
    else
        print_error "Docker Compose configuration is invalid"
        print_error "Please check your compose.yml file"
        exit 1
    fi
}

# Show next steps
show_next_steps() {
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Configure your .env file with Google Cloud credentials"
    echo "2. Add your service-account.json file"
    echo "3. Copy video files to data/input/"
    echo "4. Run: docker compose run --rm subtitle-generator"
    echo ""
    echo "📚 For detailed instructions, see README.md"
    echo "🔧 For troubleshooting, see PRODUCTION.md"
}

# Main setup process
main() {
    print_status "Starting setup process..."
    
    check_docker
    check_docker_compose
    create_directories
    setup_environment
    check_service_account
    test_docker_setup
    show_next_steps
}

# Run main function
main "$@"