# Video Subtitle Generator

A production-ready, automated video subtitle generation system using Google Vertex AI with support for English, Hindi, and Bengali languages.

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](Dockerfile)

## 🌟 Features

- 🎬 **Automatic Video Processing**: Smart chunking for efficient processing
- 🤖 **AI-Powered Transcription**: Using Google's Gemini model
- 🌍 **Multi-Language Support**: English, Hindi, and Bengali
- 🔄 **Hindi Translation Methods**: Direct translation or via English
- ⚡ **Parallel Processing**: Fast processing with configurable workers
- 🐳 **Docker Support**: Includes ffmpeg for containerized deployment
- 🖥️ **Linux Optimized**: Bash script for easy Linux automation
- 🔒 **Secure Configuration**: Centralized secrets management

## 📋 Language Support

- **English (en)**: Direct transcription and translation
- **Hindi (hi)**: Two methods available:
  - Direct: Bengali/source → Hindi
  - Via English: Bengali/source → English → Hindi
- **Bengali (bn)**: Direct transcription and translation

## 🚀 Quick Start

### Linux Users (Recommended)
```bash
# Make scripts executable
chmod +x subtitle_generator.sh

# Configure
cp config.yaml.example config.yaml
# Edit config.yaml with your Google Cloud settings

# Run
./subtitle_generator.sh video.mp4 hi direct
```

### Docker Users
```bash
# Build and run
docker build -t subtitle-generator .
./docker_run.sh video.mp4 en
```

## 📖 Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Usage Guide](docs/USAGE.md)
- [API Documentation](docs/API.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## 🛠️ Prerequisites

- Python 3.9+ OR Docker
- FFmpeg (included in Docker image)
- Google Cloud Project with Vertex AI API enabled
- Service account with appropriate permissions

## 💻 Usage Examples

### Bash Script (Linux)
```bash
# English subtitles
./subtitle_generator.sh video.mp4 en

# Hindi subtitles (direct)
./subtitle_generator.sh video.mp4 hi direct

# Hindi subtitles (via English)
./subtitle_generator.sh video.mp4 hi via_english

# Bengali subtitles
./subtitle_generator.sh video.mp4 bn
```

### Docker
```bash
# Interactive mode
./docker_run.sh

# Batch mode
./docker_run.sh video.mp4 hi via_english
```

### Python
```bash
# Interactive mode
python main.py

# Command line mode
python main.py --video video.mp4 --lang hi --method via_english
```

## 🔧 Configuration

```yaml
gcp:
  project_id: "your-project-id"
  location: "us-central1"

subtitles:
  supported_languages: ["en", "hi", "bn"]
  hindi_translation_method: "direct"  # or "via_english"
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ for the video subtitle community**
