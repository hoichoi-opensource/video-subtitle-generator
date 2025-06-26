# Installation Guide

## Quick Fix for SSL Issues

If you're getting SSL certificate errors with pip, try these solutions:

### Solution 1: Use Homebrew Python (macOS)
```bash
# Install Python via Homebrew (includes proper SSL)
brew install python3

# Create new virtual environment
python3 -m venv fresh_venv
source fresh_venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Solution 2: Use conda
```bash
# Install miniconda or anaconda
# Then create environment
conda create -n subtitle-gen python=3.11
conda activate subtitle-gen
pip install -r requirements.txt
```

### Solution 3: Fix current Python
```bash
# Update certificates (macOS)
/Applications/Python\ 3.11/Install\ Certificates.command

# Or manually
pip install --upgrade certifi
```

## Package Installation Issues

If `vertexai` import fails, install the correct packages:

```bash
pip install google-cloud-aiplatform
pip install google-generativeai
pip install vertexai
```

## Test Installation

Run this after installation:
```bash
python test_imports.py
```

This will show you exactly which packages are missing.