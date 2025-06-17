#!/bin/bash
# Install script for Ubuntu/Debian systems

set -e

echo "Video Subtitle Generator - Dependency Installation"
echo "================================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}This script is designed for Linux systems only${NC}"
    exit 1
fi

# Check if running with sudo (if needed)
if [ "$EUID" -ne 0 ] && [ "$1" != "--no-sudo" ]; then 
    echo "This script needs sudo privileges to install system packages"
    echo "Run with: sudo $0"
    echo "Or use: $0 --no-sudo (to skip system packages)"
    exit 1
fi

echo "Installing system dependencies..."

# Update package list
if [ "$1" != "--no-sudo" ]; then
    apt-get update

    # Install FFmpeg and related tools
    echo "Installing FFmpeg..."
    apt-get install -y ffmpeg

    # Install Python and development tools
    echo "Installing Python dependencies..."
    apt-get install -y python3.9 python3-pip python3-venv python3-dev

    # Install additional tools
    echo "Installing additional tools..."
    apt-get install -y git curl wget mediainfo

    echo -e "${GREEN}✓ System dependencies installed${NC}"
else
    echo "Skipping system package installation (--no-sudo flag)"
fi

# Python dependencies
echo -e "\nSetting up Python environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Created virtual environment${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python packages
echo "Installing Python packages..."
pip install -r requirements.txt

echo -e "${GREEN}✓ Python packages installed${NC}"

# Verify installations
echo -e "\nVerifying installations..."

# Check FFmpeg
if command -v ffmpeg &> /dev/null; then
    echo -e "${GREEN}✓ FFmpeg:$(ffmpeg -version 2>&1 | head -n1 | cut -d' ' -f3)${NC}"
else
    echo -e "${RED}✗ FFmpeg not found${NC}"
fi

# Check Python packages
python -c "import vertexai; print(f'\033[0;32m✓ Vertex AI installed\033[0m')" 2>/dev/null || echo -e "${RED}✗ Vertex AI not installed${NC}"
python -c "import ffmpeg; print(f'\033[0;32m✓ ffmpeg-python installed\033[0m')" 2>/dev/null || echo -e "${RED}✗ ffmpeg-python not installed${NC}"
python -c "import yaml; print(f'\033[0;32m✓ PyYAML installed\033[0m')" 2>/dev/null || echo -e "${RED}✗ PyYAML not installed${NC}"

echo -e "\n${GREEN}Installation complete!${NC}"
echo -e "\nNext steps:"
echo "1. Copy config.yaml.example to config.yaml"
echo "2. Edit config.yaml with your Google Cloud settings"
echo "3. Add your service account key to credentials/"
echo "4. Run: ./subtitle_generator.sh <video> <language>"

# Deactivate virtual environment
deactivate
