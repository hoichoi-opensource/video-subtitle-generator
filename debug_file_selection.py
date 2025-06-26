#!/usr/bin/env python3
"""
Debug script to test file selection logic
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

try:
    from config_manager import ConfigManager
    from rich.console import Console
    
    console = Console()
    config = ConfigManager()
    
    print("🔍 Debug: File Selection Logic")
    print("=" * 40)
    
    # Check input directory
    input_dir = Path("input")
    print(f"Input directory exists: {input_dir.exists()}")
    print(f"Input directory path: {input_dir.absolute()}")
    
    # Get supported formats
    supported_formats = config.get('system.supported_video_formats', [])
    print(f"Supported formats: {supported_formats}")
    
    # List all files in input directory
    if input_dir.exists():
        all_files = list(input_dir.iterdir())
        print(f"All files in input directory: {[f.name for f in all_files]}")
        
        # Test the actual logic
        video_files = []
        for ext in supported_formats:
            lower_matches = list(input_dir.glob(f"*.{ext}"))
            upper_matches = list(input_dir.glob(f"*.{ext.upper()}"))
            video_files.extend(lower_matches)
            video_files.extend(upper_matches)
            print(f"Extension '{ext}': found {len(lower_matches)} lowercase, {len(upper_matches)} uppercase")
        
        print(f"Total video files found: {len(video_files)}")
        for i, vf in enumerate(video_files, 1):
            print(f"  [{i}] {vf.name}")
            
        if video_files:
            console.print("\n[cyan]Available videos in input folder:[/cyan]")
            for i, vf in enumerate(video_files, 1):
                console.print(f"  [{i}] {vf.name}")
            console.print(f"  [0] Enter custom path")
        else:
            print("❌ No video files found!")
    else:
        print("❌ Input directory does not exist!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()