# Video Subtitle Generator

A production-grade video subtitle generation system powered by Google's Gemini AI. Automatically generates accurate subtitles in multiple languages with support for both regular CC and SDH (Subtitles for the Deaf and Hard of Hearing) formats.

## Features

- 🎬 **Automatic Subtitle Generation**: Uses Vertex AI's Gemini model for accurate transcription (REAL AI, not mock)
- 🌐 **Multi-language Support**: English (primary), Hindi (dual-method), and Bengali
- 🦻 **SDH Support**: Optional SDH subtitles with sound effects, music descriptions, and speaker identification
- 📊 **Real-time Progress Tracking**: Visual stage-by-stage progress display
- 🔄 **Resume Capability**: Resume failed jobs from any stage
- 📁 **Batch Processing**: Process multiple videos at once
- ☁️ **Google Cloud Integration**: Seamless GCS and Vertex AI integration
- 🎨 **Interactive CLI**: Colorful, user-friendly command-line interface
- 📈 **Performance Optimized**: Chunk-based processing for large videos

## Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu 18.04+) or macOS (10.15+)
- **Python**: 3.8 or higher with SSL support
- **Memory**: Minimum 4GB RAM (8GB+ recommended for large videos)
- **Storage**: At least 10GB free space

### Google Cloud Platform Setup
1. **GCP Account**: Active Google Cloud Platform account
2. **Project**: Create or select a GCP project
3. **APIs**: Enable the following APIs:
   - Vertex AI API
   - Cloud Storage API
   - AI Platform API (if using older models)
4. **Service Account**: Create a service account with these roles:
   - Vertex AI User
   - Storage Object Admin
   - AI Platform Developer

## Installation

### Option 1: Automated Installation (Recommended)

1. **Clone the repository:**
```bash
git clone https://github.com/your-org/video-subtitle-generator.git
cd video-subtitle-generator
```

2. **Run the installer:**
```bash
chmod +x install.sh
./install.sh
```

The installer will:
- Detect your operating system
- Install Python with proper SSL support (via Homebrew on macOS)
- Install FFmpeg
- Create a clean virtual environment
- Install all required dependencies
- Set up project directories

### Option 2: Manual Installation

#### Step 1: Install System Dependencies

**On macOS:**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python and FFmpeg
brew install python@3.13 ffmpeg
```

**On Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv ffmpeg
```

**On CentOS/RHEL:**
```bash
sudo yum install python3 python3-pip ffmpeg
```

#### Step 2: Set up Virtual Environment

```bash
# Use Homebrew Python on macOS for proper SSL support
# On macOS:
/usr/local/bin/python3 -m venv venv

# On Linux:
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

#### Step 3: Install Dependencies

```bash
# Install core dependencies
pip install --no-cache-dir ffmpeg-python PyYAML click rich python-dotenv requests urllib3 typing-extensions

# Install Google Cloud dependencies
pip install --no-cache-dir google-cloud-storage google-auth google-auth-oauthlib google-auth-httplib2

# Install Google AI Platform
pip install --no-cache-dir google-cloud-aiplatform==1.40.0
```

#### Step 4: Create Project Structure

```bash
mkdir -p input output temp jobs logs chunks subtitles
touch input/.gitkeep output/.gitkeep temp/.gitkeep jobs/.gitkeep logs/.gitkeep
chmod +x subtitle-gen
```

## Configuration

### 1. Google Cloud Authentication

**Download Service Account Key:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to IAM & Admin → Service Accounts
3. Find your service account and click "Actions" → "Manage keys"
4. Click "Add Key" → "Create new key" → "JSON"
5. Download the JSON file

**Set up Authentication:**
```bash
# Copy the downloaded file to your project directory
cp ~/Downloads/your-service-account-key.json ./service-account.json

# Verify the file exists and has proper permissions
ls -la service-account.json
chmod 600 service-account.json

# Test the setup
./subtitle-gen
```

### 2. Configuration File

The application uses `config/config.yaml` for settings. Key configurations:

```yaml
gcp:
  project_id: "your-gcp-project-id"
  location: "us-central1"
  service_account_path: "./service-account.json"

vertex_ai:
  default_model: "gemini-2.5-pro-preview-05-06"
  max_tokens: 8192
  temperature: 0.2
```

## Usage

### Testing Installation

```bash
# Test the installation - virtual environment activates automatically!
./subtitle-gen

# If you see the main menu, installation is successful!
```

### Interactive Mode (Recommended for beginners)

```bash
./subtitle-gen
```

**No need to manually activate the virtual environment!** The script automatically:
- Detects and activates the virtual environment
- Verifies all dependencies are working
- Creates necessary directories
- Starts the application

This will show an interactive menu with options to:
1. Process single video
2. Batch process videos
3. Resume previous jobs
4. View job history

### Command Line Usage

**Process a single video:**
```bash
./subtitle-gen --video /path/to/your/video.mp4
```

**Batch process videos:**
```bash
./subtitle-gen --batch /path/to/video/directory
```

**Resume a previous job:**
```bash
./subtitle-gen --resume job_id_here
```

**Alternative ways to run:**
```bash
./run.sh                    # Same as ./subtitle-gen
./subtitle-gen --help       # Show all available options
```

### Video Input

1. **Supported Formats**: MP4, AVI, MOV, MKV, WebM
2. **Place videos in**: `input/` directory
3. **File naming**: Use descriptive names (avoid special characters)

### Output Files

Generated files are saved in `output/video_name/`:
- `video_name_lang.srt` - Subtitle file
- `video_name_lang.vtt` - WebVTT format
- `video_name_subtitle_info.txt` - Processing information

## Troubleshooting

### Common Issues

**SSL Certificate Errors:**
```bash
# Run the SSL fix script
./fix_ssl.sh

# Or manually reinstall Python with SSL support (macOS)
brew reinstall python@3.13
```

**Import Errors:**
```bash
# Restart your terminal and try again
# If persistent, recreate virtual environment:
rm -rf venv
./setup.sh
```

**Permission Errors:**
```bash
chmod +x subtitle-gen fix_ssl.sh
```

**Google Cloud Authentication Errors:**
```bash
# Verify service account file
cat service-account.json | jq .

# Check file permissions
ls -la service-account.json

# Test authentication - the application will test this automatically
./subtitle-gen
```

### Getting Help

**Enable Debug Mode:**
```bash
export DEBUG=1
./subtitle-gen
```

**Check Logs:**
```bash
# View latest log file
ls -la logs/
tail -f logs/latest.log
```

**Verify Dependencies:**
```bash
# The application automatically checks dependencies on startup
./subtitle-gen

# Or run the test script directly (will auto-activate venv)
python test_imports.py
```

## Advanced Usage

### Custom Prompts

Edit prompt files in `config/prompts/` to customize subtitle generation for different languages and styles.

### Batch Configuration

Create batch processing configurations for different video types and requirements.

### Integration

The tool can be integrated into larger workflows using its command-line interface and JSON output format.

## Performance Tips

1. **Large Videos**: Videos over 1GB are automatically chunked for processing
2. **Parallel Processing**: Use batch mode for multiple videos
3. **Cloud Resources**: Ensure sufficient GCP quotas for Vertex AI
4. **Local Storage**: Keep at least 2x video size free space for processing

## Supported Languages

- **English**: Primary transcription and translation target
- **Hindi**: Direct transcription and translation from English
- **Bengali**: Translation from English
- **Extensible**: Add more languages by configuring prompts

## License

MIT License - see LICENSE file for details

## Support

For issues and feature requests, please use the GitHub issue tracker or contact the development team.
