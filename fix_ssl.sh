#!/bin/bash

echo "🔧 Fixing SSL issues for Video Subtitle Generator"
echo "================================================"

# Check if Homebrew is installed
if command -v brew &> /dev/null; then
    echo "✅ Homebrew found"
    
    echo "📌 Installing Python via Homebrew (with proper SSL)..."
    brew install python3
    
    echo "📌 Creating fresh virtual environment..."
    python3 -m venv fresh_venv
    
    echo "📌 Activating environment..."
    source fresh_venv/bin/activate
    
    echo "📌 Upgrading pip..."
    python -m pip install --upgrade pip
    
    echo "📌 Installing requirements..."
    pip install -r requirements.txt
    
    echo "✅ Setup complete! Use this environment:"
    echo "source fresh_venv/bin/activate"
    echo "python main.py"
    
else
    echo "❌ Homebrew not found"
    echo "Please install Homebrew first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
fi