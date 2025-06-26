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

# Check and install proper Python
echo "🐍 Setting up Python with SSL support..."
if [ "$OS" == "macOS" ]; then
    if command -v brew &> /dev/null; then
        echo "📦 Installing/updating Python via Homebrew for proper SSL support..."
        brew install python@3.13 || brew reinstall python@3.13
        
        # Use Homebrew Python
        PYTHON_CMD="/usr/local/bin/python3"
        if [ ! -f "$PYTHON_CMD" ]; then
            PYTHON_CMD="$(brew --prefix)/bin/python3"
        fi
    else
        echo "❌ Homebrew not found. Installing Homebrew first..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        brew install python@3.13
        PYTHON_CMD="$(brew --prefix)/bin/python3"
    fi
elif [ "$OS" == "Linux" ]; then
    # For Linux, ensure Python 3.8+ is available
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 not found. Please install Python 3.8 or higher."
        exit 1
    fi
    PYTHON_CMD="python3"
else
    echo "❌ Unsupported OS. Please install manually."
    exit 1
fi

echo "✅ Using Python: $PYTHON_CMD"

# Install FFmpeg
echo "🎥 Checking FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "📦 Installing FFmpeg..."
    
    if [ "$OS" == "Linux" ]; then
        sudo apt update
        sudo apt install -y ffmpeg
    elif [ "$OS" == "macOS" ]; then
        brew install ffmpeg
    fi
else
    echo "✅ FFmpeg already installed"
fi

# Remove old virtual environment if exists
if [ -d "venv" ]; then
    echo "🗑️ Removing old virtual environment..."
    rm -rf venv
fi

# Create virtual environment with proper Python
echo "🔧 Setting up Python virtual environment..."
$PYTHON_CMD -m venv venv
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies using minimal requirements
echo "📦 Installing dependencies..."
pip install --no-cache-dir -r requirements-minimal.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p input output temp jobs logs chunks subtitles
touch input/.gitkeep output/.gitkeep temp/.gitkeep jobs/.gitkeep logs/.gitkeep

# Make scripts executable
chmod +x subtitle-gen run.sh fix_ssl.sh

echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Set up Google Cloud credentials:"
echo "   - Download service account JSON from GCP Console"
echo "   - Save it as 'service-account.json' in this directory"
echo ""
echo "🚀 Ready to use! Just run:"
echo "   ./subtitle-gen"
echo ""
echo "💡 The virtual environment will be activated automatically!"
echo "   No need to run 'source venv/bin/activate' manually"
echo ""
echo "📝 Alternative commands:"
echo "   ./run.sh          # Same as ./subtitle-gen"
echo "   ./subtitle-gen --help   # Show command options"
echo ""
echo "🔧 If you encounter SSL issues, run: ./fix_ssl.sh"
