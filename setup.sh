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

# Check Python
echo -e "\n📌 Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python ${PYTHON_VERSION} found"

# Check FFmpeg
echo -e "\n📌 Checking FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg is not installed."
    
    if [ "${OS_TYPE}" == "Mac" ]; then
        echo "Install with: brew install ffmpeg"
    elif [ "${OS_TYPE}" == "Linux" ]; then
        echo "Install with: sudo apt-get install ffmpeg (Ubuntu/Debian)"
        echo "         or: sudo yum install ffmpeg (CentOS/RHEL)"
    else
        echo "Please install FFmpeg from: https://ffmpeg.org/download.html"
    fi
    exit 1
else
    echo "✅ FFmpeg found"
fi

# Create virtual environment
echo -e "\n📌 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists"
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo -e "\n📌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo -e "\n📌 Upgrading pip..."
python3 -m pip install --upgrade pip

# Install requirements
echo -e "\n📌 Installing requirements..."
pip install -r requirements.txt

# Create required directories
echo -e "\n📌 Creating required directories..."
mkdir -p input output temp jobs logs chunks subtitles

# Create .gitkeep files
touch input/.gitkeep output/.gitkeep temp/.gitkeep jobs/.gitkeep logs/.gitkeep

echo -e "\n✅ Setup complete!"
echo ""
echo "⚠️  Important: You need to set up Google Cloud credentials:"
echo "1. Create a service account in Google Cloud Console"
echo "2. Download the JSON key file"
echo "3. Save it as 'service-account.json' in the project root"
echo ""
echo "To run the application:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Run: python main.py"