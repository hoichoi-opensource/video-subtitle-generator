"""Video processing module for chunking and manipulation."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Callable, Optional, Any
import ffmpeg
from concurrent.futures import ThreadPoolExecutor
import logging

class VideoProcessor:
    """Handles video chunking and processing operations."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.chunk_duration = config.get('processing.chunk_duration', 60)
        self.temp_dir = Path("temp_chunks")
        self.temp_dir.mkdir(exist_ok=True)
    
    def analyze_video(self, video_path: Path) -> Dict[str, Any]:
        """Analyze video file and return metadata."""
        try:
            probe = ffmpeg.probe(str(video_path))
            video_info = {
                'duration': float(probe['format']['duration']),
                'size': int(probe['format']['size']),
                'bit_rate': int(probe['format']['bit_rate']),
                'format': probe['format']['format_name'],
                'streams': []
            }
            
            for stream in probe['streams']:
                stream_info = {
                    'type': stream['codec_type'],
                    'codec': stream['codec_name'],
                }
                
                if stream['codec_type'] == 'video':
                    stream_info.update({
                        'width': stream['width'],
                        'height': stream['height'],
                        'fps': eval(stream['r_frame_rate'])
                    })
                elif stream['codec_type'] == 'audio':
                    stream_info.update({
                        'sample_rate': stream['sample_rate'],
                        'channels': stream['channels']
                    })
                
                video_info['streams'].append(stream_info)
            
            return video_info
            
        except ffmpeg.Error as e:
            self.logger.error(f"Error analyzing video: {e.stderr.decode()}")
            raise Exception(f"Failed to analyze video: {str(e)}")
    
    def create_chunks(self, video_path: Path, progress_callback: Optional[Callable] = None) -> List[Path]:
        """Split video into chunks for processing."""
        video_info = self.analyze_video(video_path)
        duration = video_info['duration']
        
        chunks = []
        num_chunks = int(duration // self.chunk_duration) + (1 if duration % self.chunk_duration else 0)
        
        for i in range(num_chunks):
            start_time = i * self.chunk_duration
            chunk_path = self.temp_dir / f"chunk_{i+1:03d}.mp4"
            
            try:
                # Use keyframe seeking for better chunk boundaries
                (
                    ffmpeg
                    .input(str(video_path), ss=start_time, t=self.chunk_duration)
                    .output(
                        str(chunk_path),
                        vcodec='copy',
                        acodec='copy',
                        avoid_negative_ts='make_zero'
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                
                chunks.append(chunk_path)
                
                if progress_callback:
                    progress = ((i + 1) / num_chunks) * 100
                    progress_callback(progress)
                    
            except ffmpeg.Error as e:
                self.logger.error(f"Error creating chunk {i+1}: {e.stderr.decode()}")
                raise
        
        return chunks
    
    def burn_subtitles(self, video_path: Path, subtitle_path: Path, output_path: Path, 
                      progress_callback: Optional[Callable] = None) -> Path:
        """Burn subtitles into video."""
        try:
            # Prepare subtitle filter
            subtitle_filter = f"subtitles='{str(subtitle_path)}':force_style='Fontsize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2'"
            
            # Get video info for progress tracking
            video_info = self.analyze_video(video_path)
            duration = video_info['duration']
            
            # Run ffmpeg with progress parsing
            process = (
                ffmpeg
                .input(str(video_path))
                .output(
                    str(output_path),
                    vf=subtitle_filter,
                    vcodec=self.config.get('output.video_codec', 'libx264'),
                    acodec=self.config.get('output.audio_codec', 'aac'),
                    preset=self.config.get('output.quality_preset', 'medium')
                )
                .overwrite_output()
                .run_async(pipe_stderr=True)
            )
            
            # Parse progress
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                    
                line = line.decode('utf-8', errors='ignore')
                if 'time=' in line:
                    # Extract time from ffmpeg output
                    time_str = line.split('time=')[1].split()[0]
                    try:
                        # Convert time to seconds
                        parts = time_str.split(':')
                        if len(parts) == 3:
                            hours, minutes, seconds = parts
                            current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                            progress = (current_time / duration) * 100
                            if progress_callback:
                                progress_callback(min(progress, 99))
                    except:
                        pass
            
            process.wait()
            if progress_callback:
                progress_callback(100)
            
            return output_path
            
        except ffmpeg.Error as e:
            self.logger.error(f"Error burning subtitles: {e.stderr.decode()}")
            raise Exception(f"Failed to burn subtitles: {str(e)}")
    
    def cleanup_chunks(self, chunks: List[Path]):
        """Clean up temporary chunk files."""
        for chunk in chunks:
            try:
                if chunk.exists():
                    chunk.unlink()
            except Exception as e:
                self.logger.warning(f"Failed to delete chunk {chunk}: {e}")
        
        # Try to remove temp directory if empty
        try:
            if self.temp_dir.exists() and not list(self.temp_dir.iterdir()):
                self.temp_dir.rmdir()
        except Exception as e:
            self.logger.warning(f"Failed to remove temp directory: {e}")
