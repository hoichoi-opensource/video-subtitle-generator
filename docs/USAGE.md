# Usage Guide

## Basic Usage

### Linux Bash Script
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
./docker_run.sh video.mp4 hi direct
```

### Python Direct
```bash
# Interactive mode
python main.py

# Command line
python main.py --video video.mp4 --lang hi --method via_english
```

## Language Options

| Language | Code | Notes |
|----------|------|-------|
| English | en | Direct transcription |
| Hindi | hi | Two methods: direct or via_english |
| Bengali | bn | Direct transcription |

## Output Files

Generated files are saved in `output/video_name_timestamp/`:
- `video_name_subtitles.srt` - SubRip format
- `video_name_subtitles.vtt` - WebVTT format

## Performance Tips

1. Use smaller chunk sizes (30s) for better parallelization
2. Increase workers in config.yaml for faster processing
3. Use direct translation for Hindi when possible (faster)

## Playing Videos with Subtitles

```bash
# Using VLC
vlc video.mp4 --sub-file=output/subtitles.srt

# Using MPV
mpv video.mp4 --sub-file=output/subtitles.srt
```
