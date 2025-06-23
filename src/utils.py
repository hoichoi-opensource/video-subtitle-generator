"""
Utility Functions
Common utilities used across the application
"""

import os
import sys
import logging
import ffmpeg
from pathlib import Path
from typing import Optional, Dict, Any

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up a logger with appropriate formatting"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    
    return logger

def ensure_directory_exists(directory: str) -> None:
    """Ensure a directory exists with proper permissions"""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    
    # Set permissions to 755 (rwxr-xr-x)
    try:
        os.chmod(str(path), 0o755)
    except:
        pass  # Ignore permission errors on some systems

def validate_video_file(video_path: str) -> bool:
    """Validate if the file is a valid video file"""
    if not os.path.exists(video_path):
        return False
    
    try:
        probe = ffmpeg.probe(video_path)
        
        # Check if file has video streams
        has_video = any(s['codec_type'] == 'video' for s in probe['streams'])
        
        # Check if file has valid duration
        duration = float(probe['format'].get('duration', 0))
        
        return has_video and duration > 0
        
    except Exception:
        return False

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def get_video_info(video_path: str) -> Optional[Dict[str, Any]]:
    """Get detailed video information"""
    try:
        probe = ffmpeg.probe(video_path)
        
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
        
        info = {
            'duration': float(probe['format'].get('duration', 0)),
            'size': int(probe['format'].get('size', 0)),
            'bit_rate': int(probe['format'].get('bit_rate', 0)),
            'format': probe['format'].get('format_name', 'unknown')
        }
        
        if video_stream:
            info.update({
                'width': video_stream.get('width', 0),
                'height': video_stream.get('height', 0),
                'video_codec': video_stream.get('codec_name', 'unknown'),
                'fps': eval(video_stream.get('r_frame_rate', '0/1'))
            })
            
        if audio_stream:
            info.update({
                'audio_codec': audio_stream.get('codec_name', 'unknown'),
                'audio_channels': audio_stream.get('channels', 0),
                'audio_sample_rate': int(audio_stream.get('sample_rate', 0))
            })
            
        return info
        
    except Exception:
        return None

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200 - len(ext)] + ext
    
    return filename

def is_ffmpeg_available() -> bool:
    """Check if FFmpeg is available in the system"""
    try:
        import subprocess
        result = subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.returncode == 0
    except:
        return False

def get_system_info() -> Dict[str, str]:
    """Get system information"""
    import platform
    
    return {
        'os': platform.system(),
        'os_version': platform.version(),
        'python_version': platform.python_version(),
        'architecture': platform.machine()
    }

def cleanup_directory(directory: str, pattern: str = "*") -> int:
    """Clean up files in a directory matching a pattern"""
    from pathlib import Path
    import glob
    
    count = 0
    dir_path = Path(directory)
    
    if dir_path.exists():
        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                try:
                    file_path.unlink()
                    count += 1
                except:
                    pass
                    
    return count
