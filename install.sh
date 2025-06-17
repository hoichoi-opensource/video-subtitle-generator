#!/bin/bash
# install.sh - Installation script for Video Subtitle Generation System

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Function to print colored text
print_color() {
    local color=$1
    local text=$2
    echo -e "${color}${text}${NC}"
}

# Function to print banner
print_banner() {
    clear
    print_color $CYAN "╔════════════════════════════════════════════════════════════╗"
    print_color $CYAN "║                                                            ║"
    print_color $CYAN "║${BOLD}        VIDEO SUBTITLE SYSTEM - INSTALLER                   ${NC}${CYAN}║"
    print_color $CYAN "║                                                            ║"
    print_color $CYAN "╚════════════════════════════════════════════════════════════╝"
    echo
}

# Function to check command availability
check_command() {
    local cmd=$1
    local name=$2
    if command -v $cmd &> /dev/null; then
        print_color $GREEN "✅ $name: Found"
        return 0
    else
        print_color $RED "❌ $name: Not found"
        return 1
    fi
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            echo "debian"
        elif [ -f /etc/redhat-release ]; then
            echo "redhat"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Main installation function
main() {
    print_banner
    
    print_color $BOLD "Starting installation process..."
    echo
    
    # Step 1: Check system requirements
    print_color $BLUE "Step 1: Checking system requirements..."
    echo
    
    local os_type=$(detect_os)
    print_color $CYAN "Detected OS: $os_type"
    echo
    
    # Check Python
    local python_cmd=""
    if command -v python3 &> /dev/null; then
        python_cmd="python3"
    elif command -v python &> /dev/null; then
        # Check if it's Python 3
        if python --version 2>&1 | grep -q "Python 3"; then
            python_cmd="python"
        fi
    fi
    
    if [ -z "$python_cmd" ]; then
        print_color $RED "❌ Python 3 not found!"
        print_color $YELLOW "Please install Python 3.8 or higher"
        
        case $os_type in
            "debian")
                print_color $CYAN "Run: sudo apt-get install python3 python3-pip python3-venv"
                ;;
            "redhat")
                print_color $CYAN "Run: sudo yum install python3 python3-pip"
                ;;
            "macos")
                print_color $CYAN "Run: brew install python3"
                ;;
            *)
                print_color $CYAN "Please install Python 3.8+ from https://www.python.org/"
                ;;
        esac
        exit 1
    else
        local python_version=$($python_cmd --version 2>&1 | awk '{print $2}')
        print_color $GREEN "✅ Python: $python_version"
    fi
    
    # Check pip
    if ! $python_cmd -m pip --version &> /dev/null; then
        print_color $YELLOW "⚠️  pip not found, attempting to install..."
        $python_cmd -m ensurepip --upgrade
    fi
    
    # Check FFmpeg
    if ! check_command "ffmpeg" "FFmpeg"; then
        print_color $YELLOW "FFmpeg is required for video processing"
        
        case $os_type in
            "debian")
                print_color $CYAN "Run: sudo apt-get install ffmpeg"
                ;;
            "redhat")
                print_color $CYAN "Run: sudo yum install ffmpeg"
                ;;
            "macos")
                print_color $CYAN "Run: brew install ffmpeg"
                ;;
            "windows")
                print_color $CYAN "Download from: https://ffmpeg.org/download.html"
                ;;
            *)
                print_color $CYAN "Please install FFmpeg from https://ffmpeg.org/"
                ;;
        esac
        
        print_color $YELLOW "Install FFmpeg and run this installer again."
        exit 1
    fi
    
    # Check Git (optional but recommended)
    check_command "git" "Git"
    
    echo
    
    # Step 2: Create directory structure
    print_color $BLUE "Step 2: Creating directory structure..."
    echo
    
    directories=("input" "output" "logs" "temp" "credentials" "config")
    for dir in "${directories[@]}"; do
        if mkdir -p "$dir" 2>/dev/null; then
            print_color $GREEN "✅ Created directory: $dir"
        else
            print_color $YELLOW "⚠️  Directory exists: $dir"
        fi
    done
    
    # Create .gitkeep files
    for dir in "${directories[@]}"; do
        touch "$dir/.gitkeep" 2>/dev/null
    done
    
    echo
    
    # Step 3: Set up Python virtual environment
    print_color $BLUE "Step 3: Setting up Python virtual environment..."
    echo
    
    if [ -d "venv" ]; then
        print_color $YELLOW "Virtual environment already exists. Recreate? [y/N]: "
        read recreate
        if [[ "$recreate" =~ ^[Yy]$ ]]; then
            rm -rf venv
            $python_cmd -m venv venv
            print_color $GREEN "✅ Virtual environment recreated"
        else
            print_color $YELLOW "⚠️  Using existing virtual environment"
        fi
    else
        $python_cmd -m venv venv
        print_color $GREEN "✅ Virtual environment created"
    fi
    
    # Activate virtual environment
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    
    echo
    
    # Step 4: Install Python dependencies
    print_color $BLUE "Step 4: Installing Python dependencies..."
    echo
    
    # Upgrade pip first
    print_color $CYAN "Upgrading pip..."
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        print_color $CYAN "Installing requirements..."
        pip install -r requirements.txt
        
        if [ $? -eq 0 ]; then
            print_color $GREEN "✅ All dependencies installed successfully"
        else
            print_color $RED "❌ Error installing dependencies"
            print_color $YELLOW "Please check the error messages above"
            deactivate
            exit 1
        fi
    else
        print_color $RED "❌ requirements.txt not found!"
        deactivate
        exit 1
    fi
    
    # Deactivate virtual environment
    deactivate
    
    echo
    
    # Step 5: Set up configuration
    print_color $BLUE "Step 5: Setting up configuration..."
    echo
    
    if [ ! -f "config/config.yaml" ]; then
        if [ -f "config/config.yaml.example" ]; then
            cp "config/config.yaml.example" "config/config.yaml"
            print_color $GREEN "✅ Created config.yaml from example"
            print_color $YELLOW "⚠️  Please edit config/config.yaml with your settings"
        else
            print_color $RED "❌ config.yaml.example not found!"
        fi
    else
        print_color $YELLOW "⚠️  config.yaml already exists"
    fi
    
    echo
    
    # Step 6: Check Google Cloud setup
    print_color $BLUE "Step 6: Checking Google Cloud setup..."
    echo
    
    if [ -f "credentials/service-account.json" ]; then
        print_color $GREEN "✅ Service account credentials found"
    else
        print_color $YELLOW "⚠️  Service account credentials not found"
        print_color $CYAN "To set up Google Cloud:"
        print_color $WHITE "  1. Create a Google Cloud project"
        print_color $WHITE "  2. Enable Vertex AI API and Cloud Storage API"
        print_color $WHITE "  3. Create a service account with necessary permissions"
        print_color $WHITE "  4. Download the JSON key file"
        print_color $WHITE "  5. Save it as: credentials/service-account.json"
    fi
    
    echo
    
    # Step 7: Make scripts executable
    print_color $BLUE "Step 7: Making scripts executable..."
    echo
    
    if [ -f "videosub.sh" ]; then
        chmod +x videosub.sh
        print_color $GREEN "✅ Made videosub.sh executable"
    fi
    
    if [ -f "install.sh" ]; then
        chmod +x install.sh
        print_color $GREEN "✅ Made install.sh executable"
    fi
    
    echo
    
    # Step 8: Create test files
    print_color $BLUE "Step 8: Creating test files..."
    echo
    
    # Create a simple test to verify installation
    cat > test_installation.py << 'EOF'
#!/usr/bin/env python3
import sys

print("Testing installation...")

try:
    import yaml
    print("✅ PyYAML")
except ImportError:
    print("❌ PyYAML")

try:
    import ffmpeg
    print("✅ ffmpeg-python")
except ImportError:
    print("❌ ffmpeg-python")

try:
    import vertexai
    print("✅ Vertex AI")
except ImportError:
    print("❌ Vertex AI")

try:
    from google.cloud import storage
    print("✅ Google Cloud Storage")
except ImportError:
    print("❌ Google Cloud Storage")

try:
    import tqdm
    print("✅ tqdm")
except ImportError:
    print("❌ tqdm")

try:
    import colorama
    print("✅ colorama")
except ImportError:
    print("❌ colorama")

try:
    import rich
    print("✅ rich")
except ImportError:
    print("❌ rich")

print("\nInstallation test complete!")
EOF
    
    # Run test
    source venv/bin/activate
    python test_installation.py
    deactivate
    
    rm -f test_installation.py
    
    echo
    
    # Final summary
    print_color $BOLD "Installation Summary:"
    echo
    print_color $GREEN "✅ Directory structure created"
    print_color $GREEN "✅ Virtual environment set up"
    print_color $GREEN "✅ Dependencies installed"
    print_color $GREEN "✅ Scripts made executable"
    
    if [ ! -f "credentials/service-account.json" ]; then
        echo
        print_color $YELLOW "⚠️  Next steps:"
        print_color $WHITE "  1. Set up Google Cloud credentials"
        print_color $WHITE "  2. Edit config/config.yaml with your settings"
        print_color $WHITE "  3. Run ./videosub.sh to start"
    else
        echo
        print_color $GREEN "🎉 Installation complete!"
        print_color $WHITE "Run ./videosub.sh to start using the system"
    fi
    
    echo
    print_color $CYAN "For detailed instructions, see:"
    print_color $WHITE "  - README.md"
    print_color $WHITE "  - INSTALLATION.md"
    print_color $WHITE "  - CONFIGURATION.md"
    
    echo
}

# Run main function
main