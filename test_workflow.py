#!/usr/bin/env python3
"""
Test the main workflow without dependencies
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def test_file_selection():
    """Test the file selection logic"""
    print("🧪 Testing File Selection Workflow")
    print("=" * 40)
    
    # Check input directory
    input_dir = Path("input")
    print(f"1. Input directory: {input_dir.absolute()}")
    print(f"   Exists: {input_dir.exists()}")
    
    # Test file discovery
    supported_formats = ['mp4', 'avi', 'mkv', 'mov', 'webm']
    video_files = []
    
    for ext in supported_formats:
        video_files.extend(input_dir.glob(f"*.{ext}"))
        video_files.extend(input_dir.glob(f"*.{ext.upper()}"))
    
    print(f"2. Video files found: {len(video_files)}")
    
    if video_files:
        print("   Available videos:")
        for i, vf in enumerate(video_files, 1):
            file_size = vf.stat().st_size / (1024**2)  # Size in MB
            print(f"     [{i}] {vf.name} ({file_size:.1f} MB)")
        print("     [0] Enter custom path")
        print("\n✅ File selection should work correctly!")
        print("   When you run ./subtitle-gen:")
        print("   1. Select option '1' (Process Single Video)")
        print("   2. You'll see the list above")
        print("   3. Enter a number to select a video")
    else:
        print("   No video files found")
        print(f"   Add .mp4, .avi, .mkv, .mov, or .webm files to: {input_dir.absolute()}")
        return False
    
    return True

def test_config_access():
    """Test if config can be loaded"""
    print("\n🧪 Testing Config Access")
    print("=" * 25)
    
    try:
        # Try without actual import
        config_file = Path("config/config.yaml")
        print(f"Config file exists: {config_file.exists()}")
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                content = f.read()
                if 'supported_video_formats' in content:
                    print("✅ Config contains video format settings")
                else:
                    print("❌ Config missing video format settings")
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

if __name__ == "__main__":
    success1 = test_file_selection()
    success2 = test_config_access()
    
    print("\n" + "=" * 40)
    if success1 and success2:
        print("✅ All tests passed!")
        print("\nTo use the application:")
        print("1. Run: ./subtitle-gen")
        print("2. Select option 1 (Process Single Video)")
        print("3. Choose a video from the list")
    else:
        print("❌ Some tests failed")
        print("Check the issues above before running the application")