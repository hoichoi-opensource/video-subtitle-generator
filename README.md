# Video Subtitle Generator

A production-grade video subtitle generation system powered by Google's Gemini AI. Automatically generates accurate subtitles in multiple languages with support for both regular CC and SDH (Subtitles for the Deaf and Hard of Hearing) formats.

## Features

- 🎬 **Automatic Subtitle Generation**: Uses Vertex AI's Gemini model for accurate transcription
- 🌐 **Multi-language Support**: English (primary), Hindi (dual-method), and Bengali
- 🦻 **SDH Support**: Optional SDH subtitles with sound effects, music descriptions, and speaker identification
- 📊 **Real-time Progress Tracking**: Visual stage-by-stage progress display
- 🔄 **Resume Capability**: Resume failed jobs from any stage
- 📁 **Batch Processing**: Process multiple videos at once
- ☁️ **Google Cloud Integration**: Seamless GCS and Vertex AI integration
- 🎨 **Interactive CLI**: Colorful, user-friendly command-line interface
- 📈 **Performance Optimized**: Chunk-based processing for large videos

## Prerequisites

- Linux or macOS
- Python 3.8+
- Google Cloud Platform account with:
  - Vertex AI API enabled
  - Cloud Storage API enabled
  - Service account with appropriate permissions
- FFmpeg (installed automatically)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/hoichoi-opensource/video-subtitle-generator.git
cd video-subtitle-generator
```

2. Run the installer:
```bash
chmod +x install.sh
./install.sh
```

3. Set up authentication:
```bash
# Download service account JSON from GCP Console
cp ~/Downloads/your-service-account.json ./service-account.json
```

## Usage

### Interactive Mode
```bash
./subtitle-gen
```

### Process Single Video
```bash
./subtitle-gen --video /path/to/video.mp4
```

### Batch Process Videos
```bash
./subtitle-gen --batch /path/to/video/directory
```

## License

MIT License - see LICENSE file for details
