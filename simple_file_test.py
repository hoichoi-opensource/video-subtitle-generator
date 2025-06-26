#!/usr/bin/env python3
"""
Simple test of file selection without dependencies
"""

from pathlib import Path

print("🔍 Simple File Selection Test")
print("=" * 30)

# Check input directory
input_dir = Path("input")
print(f"Input directory exists: {input_dir.exists()}")
print(f"Input directory path: {input_dir.absolute()}")

# Supported formats (hardcoded for testing)
supported_formats = ["mp4", "avi", "mkv", "mov", "webm"]
print(f"Supported formats: {supported_formats}")

# List all files in input directory
if input_dir.exists():
    all_files = list(input_dir.iterdir())
    print(f"All files in input directory: {[f.name for f in all_files if f.is_file()]}")
    
    # Test the actual logic
    video_files = []
    for ext in supported_formats:
        lower_matches = list(input_dir.glob(f"*.{ext}"))
        upper_matches = list(input_dir.glob(f"*.{ext.upper()}"))
        video_files.extend(lower_matches)
        video_files.extend(upper_matches)
        if lower_matches or upper_matches:
            print(f"Extension '{ext}': found {len(lower_matches)} lowercase, {len(upper_matches)} uppercase")
    
    print(f"\nTotal video files found: {len(video_files)}")
    if video_files:
        print("Available videos:")
        for i, vf in enumerate(video_files, 1):
            print(f"  [{i}] {vf.name}")
    else:
        print("❌ No video files found!")
        
    # Test individual patterns
    print("\nTesting individual patterns:")
    print(f"*.mp4: {list(input_dir.glob('*.mp4'))}")
    print(f"*.MP4: {list(input_dir.glob('*.MP4'))}")
else:
    print("❌ Input directory does not exist!")