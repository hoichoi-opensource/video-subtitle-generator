# How to Use Video Subtitle Generator

## Quick Start

1. **Place your video files in the input folder:**
   ```bash
   cp your-video.mp4 input/
   ```

2. **Run the application:**
   ```bash
   ./subtitle-gen
   ```

3. **Follow the interactive menu:**
   - You'll see the main menu with found video files
   - Select option **1** (Process Single Video)
   - Choose a video from the list that appears
   - Select languages and processing options

## Step-by-Step Walkthrough

### Step 1: Main Menu
When you run `./subtitle-gen`, you'll see:

```
🎬 VIDEO SUBTITLE GENERATOR v1.0 🎬
Powered by Google Gemini AI

✅ Found 2 video file(s) in input folder

Select an option:
1  Process Single Video (select from input folder)
2  Batch Process Videos  
3  Resume Previous Job
4  View Job History
5  Exit

Enter your choice [1]: 
```

### Step 2: Video Selection
After selecting option 1, you'll see your available videos:

```
Checking for videos in: /path/to/project/input
Found 2 video files

Available videos in input folder:
  [1] my-video.mp4 (61.0 MB)
  [2] another-video.mp4 (45.2 MB)
  [0] Enter custom path

Select video or enter 0 for custom path [1]: 
```

### Step 3: Language Selection
Choose which languages you want subtitles for:

```
Available Languages:
  [1] ✓ English (eng) - Default
  [2]   Hindi (hin)
  [3]   Bengali (ben)

Enter language numbers (comma-separated): 1,2
Enable SDH (Subtitles for Deaf/Hard of hearing)? [y/N]: n
```

### Step 4: Processing
The application will process your video through multiple stages:
- Video analysis and chunking
- Upload to Google Cloud Storage  
- AI subtitle generation
- Download and merge results
- Save to output folder

### Step 5: Results
Subtitles will be saved to: `output/<video-name>/`

## Command Line Usage

You can also use command line arguments:

```bash
# Process specific video
./subtitle-gen --video path/to/video.mp4

# Batch process all videos in input folder
./subtitle-gen --batch input/

# Resume a previous job
./subtitle-gen --resume JOB_ID
```

## Supported Video Formats

- `.mp4` (recommended)
- `.avi`
- `.mkv`
- `.mov`
- `.webm`

## Output Structure

```
output/
├── my-video/
│   ├── my-video_eng.srt
│   ├── my-video_eng.vtt
│   ├── my-video_hin.srt
│   └── my-video_hin.vtt
└── another-video/
    ├── another-video_eng.srt
    └── another-video_eng.vtt
```

## Troubleshooting

### "No video files found"
- Check that video files are in the `input/` folder
- Verify file extensions are supported (mp4, avi, mkv, mov, webm)
- File names should not contain special characters

### Import errors
- Run `python test_imports.py` to check dependencies
- Follow instructions in `INSTALL.md` to fix SSL issues

### Google Cloud errors
- Verify service account JSON file exists
- Check that Vertex AI is enabled in your GCP project
- Ensure service account has correct permissions