#!/bin/bash

echo "🎬 Video Subtitle Generator Setup Script"
echo "======================================="

# Check OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     OS_TYPE=Linux;;
    Darwin*)    OS_TYPE=Mac;;
    CYGWIN*)    OS_TYPE=Windows;;
    MINGW*)     OS_TYPE=Windows;;
    *)          OS_TYPE="UNKNOWN:${OS}"
esac

echo "Detected OS: ${OS_TYPE}"

# Function to check Python SSL support
check_python_ssl() {
    python3 -c "import ssl; print('SSL support: OK')" 2>/dev/null
    return $?
}

# Check and setup Python with SSL support
echo -e "\n📌 Checking Python with SSL support..."
if [ "${OS_TYPE}" == "Mac" ]; then
    # On macOS, prefer Homebrew Python for SSL support
    if command -v brew &> /dev/null; then
        echo "📦 Ensuring proper Python installation via Homebrew..."
        brew list python@3.13 &>/dev/null || brew install python@3.13
        
        PYTHON_CMD="$(brew --prefix)/bin/python3"
        if [ ! -f "$PYTHON_CMD" ]; then
            PYTHON_CMD="/usr/local/bin/python3"
        fi
    else
        echo "❌ Homebrew not found. Installing Homebrew first..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        brew install python@3.13
        PYTHON_CMD="$(brew --prefix)/bin/python3"
    fi
elif [ "${OS_TYPE}" == "Linux" ]; then
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    PYTHON_CMD="python3"
else
    echo "❌ Unsupported OS: ${OS_TYPE}"
    exit 1
fi

# Test SSL support
echo "🔐 Testing SSL support..."
if ! $PYTHON_CMD -c "import ssl; print('SSL support: OK')" 2>/dev/null; then
    echo "❌ Python SSL support not available. Please install Python with SSL support."
    if [ "${OS_TYPE}" == "Mac" ]; then
        echo "Try: brew reinstall python@3.13"
    fi
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python ${PYTHON_VERSION} with SSL support found"

# Check FFmpeg
echo -e "\n📌 Checking FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg is not installed."
    
    if [ "${OS_TYPE}" == "Mac" ]; then
        echo "📦 Installing FFmpeg via Homebrew..."
        brew install ffmpeg
    elif [ "${OS_TYPE}" == "Linux" ]; then
        echo "Install with: sudo apt-get install ffmpeg (Ubuntu/Debian)"
        echo "         or: sudo yum install ffmpeg (CentOS/RHEL)"
        exit 1
    else
        echo "Please install FFmpeg from: https://ffmpeg.org/download.html"
        exit 1
    fi
else
    echo "✅ FFmpeg found"
fi

# Remove old virtual environment
echo -e "\n📌 Setting up clean virtual environment..."
if [ -d "venv" ]; then
    echo "🗑️ Removing existing virtual environment..."
    rm -rf venv
fi

# Create virtual environment with proper Python
echo "🔧 Creating virtual environment..."
$PYTHON_CMD -m venv venv
echo "✅ Virtual environment created"

# Activate virtual environment
echo -e "\n📌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo -e "\n📌 Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies using minimal requirements
echo -e "\n📌 Installing dependencies..."
pip install --no-cache-dir -r requirements-minimal.txt

# Create required directories
echo -e "\n📌 Creating required directories..."
mkdir -p input output temp jobs logs chunks subtitles

# Create .gitkeep files
touch input/.gitkeep output/.gitkeep temp/.gitkeep jobs/.gitkeep logs/.gitkeep

# Make scripts executable
chmod +x subtitle-gen run.sh fix_ssl.sh

echo -e "\n✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Set up Google Cloud credentials:"
echo "   - Create a service account in Google Cloud Console"
echo "   - Enable Vertex AI API and Cloud Storage API"
echo "   - Download the JSON key file"
echo "   - Save it as 'service-account.json' in the project root"
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
echo "🆘 If you encounter issues:"
echo "   - SSL errors: Run ./fix_ssl.sh"
echo "   - Import errors: Restart terminal and try again"
echo "   - Permission errors: Run chmod +x subtitle-gen run.sh"