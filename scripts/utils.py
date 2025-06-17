"""Utility functions for the video subtitle system."""

import os
import re
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import ffmpeg
import humanize
from tenacity import retry, stop_after_attempt, wait_exponential


def get_video_info(video_path: str) -> Dict[str, Any]:
    """Extract video information using ffmpeg-python."""
    try:
        probe = ffmpeg.probe(video_path)
        video_stream = next(
            (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
            None
        )
        audio_stream = next(
            (stream for stream in probe['streams'] if stream['codec_type'] == 'audio'),
            None
        )
        
        if not video_stream:
            raise ValueError("No video stream found")
        
        duration = float(probe['format']['duration'])
        size = int(probe['format']['size'])
        
        return {
            'duration': duration,
            'duration_formatted': format_duration(duration),
            'size': size,
            'size_formatted': humanize.naturalsize(size),
            'width': int(video_stream['width']),
            'height': int(video_stream['height']),
            'fps': eval(video_stream['r_frame_rate']),
            'codec': video_stream['codec_name'],
            'audio_codec': audio_stream['codec_name'] if audio_stream else None,
            'bitrate': int(probe['format']['bit_rate']),
            'format': probe['format']['format_name']
        }
    except Exception as e:
        raise ValueError(f"Error probing video: {str(e)}")


def format_duration(seconds: float) -> str:
    """Format duration in seconds to HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def validate_video_file(file_path: str) -> Tuple[bool, str]:
    """Validate if the file is a valid video file."""
    valid_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
    
    path = Path(file_path)
    
    if not path.exists():
        return False, "File does not exist"
    
    if not path.is_file():
        return False, "Path is not a file"
    
    if path.suffix.lower() not in valid_extensions:
        return False, f"Unsupported file extension: {path.suffix}"
    
    try:
        info = get_video_info(file_path)
        if info['duration'] < 1:
            return False, "Video duration is too short"
        return True, "Valid video file"
    except Exception as e:
        return False, f"Invalid video file: {str(e)}"


def generate_job_id(video_name: str, language: str) -> str:
    """Generate a unique job ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', video_name)
    return f"{clean_name}_{language}_{timestamp}"


def ensure_directory(path: str) -> Path:
    """Ensure a directory exists, create if not."""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def clean_filename(filename: str) -> str:
    """Clean filename for safe file system usage."""
    # Remove file extension
    name = Path(filename).stem
    # Replace problematic characters
    cleaned = re.sub(r'[^\w\s-]', '', name)
    # Replace spaces with underscores
    cleaned = re.sub(r'[-\s]+', '_', cleaned)
    return cleaned


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def run_command(command: List[str], description: str = "Running command") -> Tuple[bool, str]:
    """Run a shell command with retry logic."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"{description} failed: {e.stderr}"


def estimate_processing_time(duration: float, num_chunks: int) -> float:
    """Estimate processing time based on video duration and chunks."""
    # Rough estimates based on experience
    chunk_processing_time = 30  # seconds per chunk for subtitle generation
    upload_time_per_chunk = 10  # seconds
    overhead = 60  # seconds for initialization and finalization
    
    total_time = (num_chunks * (chunk_processing_time + upload_time_per_chunk)) + overhead
    return total_time


def format_eta(seconds: float) -> str:
    """Format ETA in a human-readable format."""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minutes"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def check_disk_space(path: str, required_gb: float = 10.0) -> Tuple[bool, str]:
    """Check if there's enough disk space."""
    stat = os.statvfs(path)
    available_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
    
    if available_gb < required_gb:
        return False, f"Insufficient disk space: {available_gb:.1f}GB available, {required_gb}GB required"
    
    return True, f"Disk space OK: {available_gb:.1f}GB available"


def save_job_metadata(job_id: str, metadata: Dict[str, Any], output_dir: str):
    """Save job metadata to a JSON file."""
    metadata_file = Path(output_dir) / f"{job_id}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)


def load_job_metadata(job_id: str, output_dir: str) -> Optional[Dict[str, Any]]:
    """Load job metadata from JSON file."""
    metadata_file = Path(output_dir) / f"{job_id}_metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            return json.load(f)
    return None