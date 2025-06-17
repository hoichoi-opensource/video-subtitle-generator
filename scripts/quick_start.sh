#!/bin/bash
# Quick start helper for new users

echo "Video Subtitle Generator - Quick Start"
echo "====================================="
echo ""

# Check if config exists
if [ ! -f "config.yaml" ]; then
    echo "Setting up configuration..."
    cp config.yaml.example config.yaml
    echo "✓ Created config.yaml from example"
    echo ""
    echo "Please edit config.yaml and add your Google Cloud project ID"
    echo "Then run this script again."
    exit 1
fi

# Check for credentials
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ ! -f "credentials/service-account.json" ]; then
    echo "Google Cloud credentials not found!"
    echo ""
    echo "Please either:"
    echo "1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable"
    echo "2. Place your service account JSON in credentials/"
    echo ""
    exit 1
fi

# Install dependencies if needed
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing dependencies..."
    ./scripts/install_dependencies.sh
fi

echo "Ready to generate subtitles!"
echo ""
echo "Usage examples:"
echo "  ./subtitle_generator.sh video.mp4 en"
echo "  ./subtitle_generator.sh video.mp4 hi direct"
echo "  ./subtitle_generator.sh video.mp4 hi via_english"
echo ""
