#!/bin/bash
# docker_run.sh - Helper script to run subtitle generator in Docker

# Build the Docker image
echo "Building Docker image..."
docker build -t subtitle-generator .

# Function to run in interactive mode
run_interactive() {
    echo "Starting interactive mode..."
    docker run -it --rm \
        -v "$(pwd)/config.yaml:/app/config.yaml:ro" \
        -v "$(pwd)/input:/app/input" \
        -v "$(pwd)/output:/app/output" \
        -v "$(pwd)/logs:/app/logs" \
        -v "${GOOGLE_APPLICATION_CREDENTIALS}:/app/credentials.json:ro" \
        -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
        subtitle-generator
}

# Function to run in batch mode
run_batch() {
    local video_file="$1"
    local target_lang="$2"
    local hindi_method="${3:-direct}"
    
    # Copy video to input directory
    cp "$video_file" "./input/"
    local video_name=$(basename "$video_file")
    
    echo "Processing: $video_name -> $target_lang"
    
    docker run --rm \
        -v "$(pwd)/config.yaml:/app/config.yaml:ro" \
        -v "$(pwd)/input:/app/input" \
        -v "$(pwd)/output:/app/output" \
        -v "$(pwd)/logs:/app/logs" \
        -v "${GOOGLE_APPLICATION_CREDENTIALS}:/app/credentials.json:ro" \
        -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
        -e VIDEO_FILE="/app/input/$video_name" \
        -e TARGET_LANG="$target_lang" \
        -e HINDI_METHOD="$hindi_method" \
        subtitle-generator
}

# Main logic
if [ $# -eq 0 ]; then
    run_interactive
else
    video_file="$1"
    target_lang="$2"
    hindi_method="${3:-direct}"
    
    if [ ! -f "$video_file" ]; then
        echo "Error: Video file not found: $video_file"
        exit 1
    fi
    
    if [[ ! "$target_lang" =~ ^(en|hi|bn)$ ]]; then
        echo "Error: Invalid language. Use: en, hi, or bn"
        exit 1
    fi
    
    run_batch "$video_file" "$target_lang" "$hindi_method"
fi
