# Installation Guide

## Prerequisites

- Linux (Ubuntu 20.04+ recommended)
- Python 3.9+ OR Docker
- FFmpeg (for native installation)
- Google Cloud Project with Vertex AI enabled

## Option 1: Native Installation

1. **Install system dependencies:**
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg python3-pip python3-venv
```

2. **Clone and setup:**
```bash
git clone <repository-url>
cd video-subtitle-generator
chmod +x subtitle_generator.sh
```

3. **Install Python packages:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **Configure:**
```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your Google Cloud project ID
```

5. **Set up credentials:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
```

## Option 2: Docker Installation

1. **Install Docker:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

2. **Build image:**
```bash
docker build -t subtitle-generator .
```

3. **Run:**
```bash
./docker_run.sh video.mp4 en
```

## Google Cloud Setup

1. Create a project in Google Cloud Console
2. Enable Vertex AI API
3. Create a service account with Vertex AI User role
4. Download the service account JSON key
5. Place it in `credentials/` directory

## Verify Installation

```bash
# Check dependencies
ffmpeg -version
python3 --version

# Test the script
./subtitle_generator.sh --help
```
