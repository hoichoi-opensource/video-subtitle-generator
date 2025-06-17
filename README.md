# Video Subtitle Generation System

A production-ready video subtitle generation system that uses Google's Vertex AI (Gemini) to automatically generate accurate subtitles for videos in multiple languages.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Features

- 🎬 **Automatic Subtitle Generation**: Uses Vertex AI's Gemini model for accurate transcription
- 🌐 **Multi-language Support**: English, Hindi, and Bengali
- 📊 **Real-time Progress Tracking**: Visual stage-by-stage progress display
- 🔄 **Resume Capability**: Resume failed jobs from any stage
- 📁 **Batch Processing**: Process multiple videos at once
- ☁️ **Google Cloud Integration**: Seamless GCS and Vertex AI integration
- 🎨 **Interactive CLI**: Colorful, user-friendly command-line interface
- 📈 **Performance Optimized**: Chunk-based processing for large videos

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com//hoichoi-opensource/Video-subtitle-Generator.git
   cd Video-subtitle-Generator
   ```

2. **Run the installer**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Set up Google Cloud credentials**
   - Create a Google Cloud project
   - Enable Vertex AI and Cloud Storage APIs
   - Create a service account and download the JSON key
   - Place it in `credentials/service-account.json`

4. **Configure the system**
   - Edit `config/config.yaml` with your settings

5. **Start processing**
   ```bash
   ./videosub.sh
   ```

## System Requirements

- Python 3.8 or higher
- FFmpeg
- Google Cloud account with billing enabled
- Sufficient disk space for video processing

## Supported Video Formats

- MP4, AVI, MKV, MOV, WMV, FLV, WEBM

## Documentation

- [Installation Guide](INSTALLATION.md) - Detailed installation instructions
- [Configuration Guide](CONFIGURATION.md) - Configuration options
- [Usage Guide](USAGE.md) - How to use the system
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

## Project Structure

```
video-subtitle-system/
├── input/              # Place your video files here
├── output/             # Generated subtitles and processed videos
├── scripts/            # Python modules
├── config/             # Configuration files
├── credentials/        # Google Cloud credentials
├── videosub.sh         # Main interactive script
└── install.sh          # Installation script
```

## Processing Stages

The system processes videos through 10 clearly defined stages:

1. **Validating Input File** - Checks video format and integrity
2. **Analyzing Video** - Extracts metadata and calculates chunks
3. **Creating Video Chunks** - Splits video into manageable segments
4. **Connecting to Google Cloud** - Establishes GCS connection
5. **Uploading Chunks to GCS** - Transfers chunks to cloud storage
6. **Initializing Vertex AI** - Prepares the AI model
7. **Generating Subtitles** - Creates subtitles for each chunk
8. **Downloading Subtitles** - Retrieves generated subtitles
9. **Merging Subtitles** - Combines all chunks into final subtitle
10. **Finalizing Output** - Cleanup and format conversion

## Configuration

The system uses `gemini-2.5-pro-preview-05-06` as the default AI model. Key configuration options:

- **Chunk Duration**: Configurable video segment length (default: 60s)
- **Output Formats**: SRT and VTT subtitle formats
- **Languages**: English, Hindi, Bengali (expandable)
- **Parallel Processing**: Configurable worker count

## Usage Examples

### Single Video Processing
```bash
./videosub.sh
# Select option 1 (Process Video)
# Choose your video and language
```

### Batch Processing
```bash
./videosub.sh
# Select option 2 (Batch Process)
# Specify directory and language
```

### Check Job Status
```bash
./videosub.sh
# Select option 3 (Check Status)
# Enter job ID or 'list' to see recent jobs
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Cloud Vertex AI team for the excellent Gemini model
- FFmpeg community for video processing capabilities
- Open source contributors

## Support

For issues and questions:
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) first
- Open an issue on GitHub
- Contact support at support@example.com
