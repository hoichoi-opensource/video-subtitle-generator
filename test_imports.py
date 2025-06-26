#!/usr/bin/env python3
"""
Test script to check if imports will work
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

print("🔍 Testing Video Subtitle Generator imports...")
print("=" * 50)

# Test basic imports first
try:
    import json, time, os
    from pathlib import Path
    from typing import List, Dict, Optional
    print("✅ Basic Python modules imported successfully")
except ImportError as e:
    print(f"❌ Basic import failed: {e}")
    sys.exit(1)

# Test rich
try:
    from rich.console import Console
    from rich.panel import Panel
    print("✅ Rich library imported successfully")
except ImportError as e:
    print(f"❌ Rich import failed: {e}")
    print("   Install with: pip install rich")

# Test click
try:
    import click
    print("✅ Click library imported successfully")
except ImportError as e:
    print(f"❌ Click import failed: {e}")
    print("   Install with: pip install click")

# Test PyYAML
try:
    import yaml
    print("✅ PyYAML imported successfully")
except ImportError as e:
    print(f"❌ PyYAML import failed: {e}")
    print("   Install with: pip install PyYAML")

# Test Google Cloud packages
try:
    from google.cloud import storage
    print("✅ Google Cloud Storage imported successfully")
except ImportError as e:
    print(f"❌ Google Cloud Storage import failed: {e}")
    print("   Install with: pip install google-cloud-storage")

try:
    import vertexai
    print("✅ Vertex AI imported successfully")
except ImportError as e:
    print(f"❌ Vertex AI import failed: {e}")
    print("   Install with: pip install google-cloud-aiplatform")

try:
    from vertexai import generative_models
    print("✅ Vertex AI generative_models imported successfully")
except ImportError as e:
    print(f"❌ Vertex AI generative_models import failed: {e}")
    print("   Install with: pip install google-cloud-aiplatform")

# Test the actual import structure used in the application
try:
    from google.cloud.aiplatform import gapic
    from google.cloud.aiplatform_v1.services.prediction_service import client as prediction_client
    print("✅ Google Cloud AI Platform services imported successfully")
except ImportError as e:
    print(f"❌ Google Cloud AI Platform services import failed: {e}")
    print("   This is expected - using alternative import structure")

# Test FFmpeg
try:
    import ffmpeg
    print("✅ FFmpeg-python imported successfully")
except ImportError as e:
    print(f"❌ FFmpeg-python import failed: {e}")
    print("   Install with: pip install ffmpeg-python")

# Test local modules
print("\n🏠 Testing local modules...")
try:
    from config_manager import ConfigManager
    print("✅ ConfigManager imported successfully")
except ImportError as e:
    print(f"❌ ConfigManager import failed: {e}")

try:
    from utils import ensure_directory_exists
    print("✅ Utils imported successfully")
except ImportError as e:
    print(f"❌ Utils import failed: {e}")

try:
    from state_manager import StateManager
    print("✅ StateManager imported successfully")
except ImportError as e:
    print(f"❌ StateManager import failed: {e}")

print("\n" + "=" * 50)
print("🏁 Import test complete!")
print("\nTo fix SSL issues:")
print("1. Install Python via official installer or pyenv")
print("2. Or use: brew install python")
print("3. Create new venv: python3 -m venv new_venv")
print("4. Activate: source new_venv/bin/activate")
print("5. Install deps: pip install -r requirements.txt")