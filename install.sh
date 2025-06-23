#!/bin/bash

set -e

echo "==============================================="
echo "🎬 Video Subtitle Generator - Installation 🎬"
echo "==============================================="
echo ""

# Detect OS
OS="Unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
fi

echo "📍 Detected OS: $OS"
echo ""

# Check Python version
echo "🐍 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Install FFmpeg
echo "🎥 Checking FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "📦 Installing FFmpeg..."
    
    if [ "$OS" == "Linux" ]; then
        sudo apt update
        sudo apt install -y ffmpeg
    elif [ "$OS" == "macOS" ]; then
        if command -v brew &> /dev/null; then
            brew install ffmpeg
        else
            echo "❌ Homebrew not found. Please install Homebrew first."
            exit 1
        fi
    fi
else
    echo "✅ FFmpeg already installed"
fi

# Create virtual environment
echo "🔧 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install requirements
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Add your service account JSON as 'service-account.json'"
echo "2. Run: ./subtitle-gen"
