#!/usr/bin/env python3
"""
Video Subtitle Generator - Main Entry Point
Production-grade subtitle generation using Google Gemini AI
"""

import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Import and run the subtitle processor
from subtitle_processor import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Application terminated by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)
