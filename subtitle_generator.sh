#!/bin/bash

# Video Subtitle Generator - Linux Bash Script
# Usage: ./subtitle_generator.sh <video_file> <target_language> [hindi_method]
# Languages: en (English), hi (Hindi), bn (Bengali)
# Hindi methods: direct, via_english (only applicable when target is Hindi)

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to check dependencies
check_dependencies() {
    local missing_deps=0
    
    # Check for Python 3
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        missing_deps=1
    fi
    
    # Check for ffmpeg
    if ! command -v ffmpeg &> /dev/null; then
        print_error "ffmpeg is not installed. Please install: sudo apt-get install ffmpeg"
        missing_deps=1
    fi
    
    # Check for required Python packages
    if ! python3 -c "import yaml" &> /dev/null; then
        print_warning "PyYAML not installed. Installing..."
        pip3 install pyyaml
    fi
    
    # Check if config.yaml exists
    if [ ! -f "config.yaml" ]; then
        print_error "config.yaml not found. Please create it from config.yaml.example"
        missing_deps=1
    fi
    
    return $missing_deps
}

# Function to validate input
validate_input() {
    local video_file="$1"
    local target_lang="$2"
    
    # Check if video file exists
    if [ ! -f "$video_file" ]; then
        print_error "Video file not found: $video_file"
        return 1
    fi
    
    # Check if file is a video
    if ! ffprobe -v error -select_streams v:0 -show_entries stream=codec_type -of csv=p=0 "$video_file" &> /dev/null; then
        print_error "File is not a valid video: $video_file"
        return 1
    fi
    
    # Validate language
    if [[ ! "$target_lang" =~ ^(en|hi|bn)$ ]]; then
        print_error "Invalid language: $target_lang. Supported: en, hi, bn"
        return 1
    fi
    
    return 0
}

# Function to get video duration
get_video_duration() {
    local video_file="$1"
    ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$video_file" | cut -d. -f1
}

# Function to create output directory
setup_output_dir() {
    local video_file="$1"
    local base_name=$(basename "$video_file" .${video_file##*.})
    local timestamp=$(date +'%Y%m%d_%H%M%S')
    local output_dir="output/${base_name}_${timestamp}"
    
    mkdir -p "$output_dir"
    echo "$output_dir"
}

# Main function
main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Video Subtitle Generator${NC}"
    echo -e "${BLUE}================================${NC}\n"
    
    # Check arguments
    if [ $# -lt 2 ]; then
        echo "Usage: $0 <video_file> <target_language> [hindi_method]"
        echo "Languages: en (English), hi (Hindi), bn (Bengali)"
        echo "Hindi methods: direct, via_english (only for Hindi target)"
        echo ""
        echo "Examples:"
        echo "  $0 video.mp4 en                    # English subtitles"
        echo "  $0 video.mp4 hi direct             # Hindi subtitles (direct translation)"
        echo "  $0 video.mp4 hi via_english        # Hindi subtitles (via English)"
        echo "  $0 video.mp4 bn                    # Bengali subtitles"
        exit 1
    fi
    
    local video_file="$1"
    local target_lang="$2"
    local hindi_method="${3:-direct}"
    
    # Resolve absolute path
    video_file=$(realpath "$video_file")
    
    print_status "Checking dependencies..."
    if ! check_dependencies; then
        print_error "Missing dependencies. Please install them and try again."
        exit 1
    fi
    print_success "All dependencies satisfied"
    
    print_status "Validating input..."
    if ! validate_input "$video_file" "$target_lang"; then
        exit 1
    fi
    print_success "Input validated"
    
    # Get video info
    local duration=$(get_video_duration "$video_file")
    local size=$(du -h "$video_file" | cut -f1)
    print_status "Video: $(basename "$video_file")"
    print_status "Duration: ${duration}s | Size: $size"
    print_status "Target language: $target_lang"
    
    if [ "$target_lang" = "hi" ]; then
        print_status "Hindi translation method: $hindi_method"
    fi
    
    # Setup output directory
    local output_dir=$(setup_output_dir "$video_file")
    print_status "Output directory: $output_dir"
    
    # Create a simple Python runner that calls our main app
    print_status "Starting subtitle generation..."
    
    # Use Python directly with command line arguments
    python3 << EOF
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.getcwd())

# Import and run
from main import SubtitleApp

# Create app instance
app = SubtitleApp('config.yaml')

# Override config for this run
if '$target_lang' == 'hi':
    app.config._config['subtitles']['hindi_translation_method'] = '$hindi_method'

# Process video
settings = {
    'video_path': Path('$video_file'),
    'source_language': 'auto',
    'target_language': '$target_lang',
    'formats': ['srt', 'vtt'],
    'burn_subtitles': False,
    'output_dir': Path('$output_dir')
}

try:
    success = app.process_video(settings)
    if success:
        print("\n✓ Subtitle generation completed successfully!")
        print(f"Output files saved to: $output_dir")
        
        # List generated files
        for file in Path('$output_dir').glob('*'):
            print(f"  - {file.name}")
    else:
        print("\n✗ Subtitle generation failed")
        sys.exit(1)
except Exception as e:
    print(f"\n✗ Error: {str(e)}")
    sys.exit(1)
EOF
    
    # Check if successful
    if [ $? -eq 0 ]; then
        print_success "Subtitle generation completed!"
        print_status "Files saved to: $output_dir"
        
        # List generated files
        echo -e "\n${GREEN}Generated files:${NC}"
        ls -la "$output_dir" | grep -E "\.(srt|vtt|mp4)$" | awk '{print "  • " $9}'
        
        # Offer to play with subtitles (optional)
        echo -e "\n${YELLOW}To play video with subtitles:${NC}"
        echo "  mpv \"$video_file\" --sub-file=\"$output_dir/$(basename "$video_file" .${video_file##*.})_subtitles.srt\""
        echo "  or"
        echo "  vlc \"$video_file\" --sub-file=\"$output_dir/$(basename "$video_file" .${video_file##*.})_subtitles.srt\""
    else
        print_error "Subtitle generation failed. Check logs for details."
        exit 1
    fi
}

# Run main function
main "$@"
