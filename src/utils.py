"""Utility functions for the subtitle generator."""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import colorlog

def setup_logging(config) -> logging.Logger:
    """Set up logging configuration."""
    log_level = config.get('logging.level', 'INFO')
    log_file = config.get('logging.log_file', 'logs/subtitle_generator.log')
    
    # Create log directory
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Set up color logging for console
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            '%(log_color)s%(levelname)-8s%(reset)s %(message)s',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    )
    
    # Set up file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=config.get('logging.backup_count', 5)
    )
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

def validate_input_file(file_path: Path) -> bool:
    """Validate if the input file exists and is a video file."""
    if not file_path.exists():
        return False
    
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}
    return file_path.suffix.lower() in video_extensions

def format_time(seconds: float) -> str:
    """Format seconds into human-readable time."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def get_file_size(file_path: Path) -> str:
    """Get human-readable file size."""
    size = file_path.stat().st_size
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    
    return f"{size:.2f} PB"
