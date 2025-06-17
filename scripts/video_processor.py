"""Video processing module for chunking and manipulation."""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import ffmpeg
from tqdm import tqdm

from .logger import setup_logging, console, log_stage
from .utils import get_video_info, ensure_directory, clean_filename, format_duration
from .config import get_config


class VideoProcessor:
    """Handle video processing operations."""
    
    def __init__(self, logger_name: str = "video_processor"):
        self.logger = setup_logging(logger_name)
        self.config = get_config()
    
    def create_chunks(
        self,
        video_path: str,
        output_dir: str,
        chunk_duration: Optional[int] = None,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """Split video into chunks of specified duration."""
        if chunk_duration is None:
            chunk_duration = self.config.processing["chunk_duration"]
        
        self.logger.info(f"Creating chunks for video: {video_path}")
        
        # Get video info
        video_info = get_video_info(video_path)
        total_duration = video_info['duration']
        
        # Calculate number of chunks
        num_chunks = int(total_duration / chunk_duration) + (
            1 if total_duration % chunk_duration > 0 else 0
        )
        
        self.logger.info(
            f"Video duration: {format_duration(total_duration)}, "
            f"creating {num_chunks} chunks of {chunk_duration}s each"
        )
        
        # Ensure output directory exists
        chunk_dir = ensure_directory(output_dir)
        
        # Get clean video name
        video_name = clean_filename(Path(video_path).name)
        
        chunks = []
        
        # Create progress bar
        with tqdm(total=num_chunks, desc="Creating chunks", unit="chunk") as pbar:
            for i in range(num_chunks):
                start_time = i * chunk_duration
                
                # Calculate actual duration for last chunk
                if i == num_chunks - 1:
                    actual_duration = total_duration - start_time
                else:
                    actual_duration = chunk_duration
                
                # Generate chunk filename
                chunk_filename = f"{video_name}_chunk_{i+1:03d}.mp4"
                chunk_path = chunk_dir / chunk_filename
                
                try:
                    # Create chunk using ffmpeg
                    (
                        ffmpeg
                        .input(video_path, ss=start_time, t=actual_duration)
                        .output(
                            str(chunk_path),
                            vcodec='copy',
                            acodec='copy',
                            avoid_negative_ts='make_zero'
                        )
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                    
                    chunk_info = {
                        'index': i + 1,
                        'filename': chunk_filename,
                        'path': str(chunk_path),
                        'start_time': start_time,
                        'duration': actual_duration,
                        'size': chunk_path.stat().st_size
                    }
                    
                    chunks.append(chunk_info)
                    
                    if progress_callback:
                        progress_callback(i + 1, num_chunks)
                    
                    pbar.update(1)
                    
                except ffmpeg.Error as e:
                    self.logger.error(f"Error creating chunk {i+1}: {e.stderr.decode()}")
                    raise
        
        self.logger.info(f"Successfully created {len(chunks)} chunks")
        return chunks
    
    def merge_subtitles(
        self,
        subtitle_files: List[str],
        output_path: str,
        video_info: Dict[str, Any]
    ) -> str:
        """Merge multiple subtitle files into one."""
        self.logger.info(f"Merging {len(subtitle_files)} subtitle files")
        
        merged_content = []
        subtitle_index = 1
        time_offset = 0.0
        
        for i, subtitle_file in enumerate(subtitle_files):
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                continue
            
            # Parse SRT content
            subtitles = self._parse_srt(content)
            
            # Adjust timestamps and indices
            for subtitle in subtitles:
                subtitle['index'] = subtitle_index
                subtitle['start'] += time_offset
                subtitle['end'] += time_offset
                
                merged_content.append(
                    f"{subtitle['index']}\n"
                    f"{self._format_timestamp(subtitle['start'])} --> "
                    f"{self._format_timestamp(subtitle['end'])}\n"
                    f"{subtitle['text']}\n"
                )
                
                subtitle_index += 1
            
            # Update time offset for next chunk
            if i < len(subtitle_files) - 1:
                chunk_duration = video_info['chunks'][i]['duration']
                time_offset += chunk_duration
        
        # Write merged subtitle file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(merged_content))
        
        self.logger.info(f"Merged subtitle saved to: {output_path}")
        return output_path
    
    def burn_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        progress_callback=None
    ) -> str:
        """Burn subtitles into video."""
        self.logger.info("Burning subtitles into video")
        
        try:
            # Use ffmpeg to burn subtitles
            (
                ffmpeg
                .input(video_path)
                .output(
                    output_path,
                    vf=f"subtitles={subtitle_path}:force_style='Fontsize=24'"
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            self.logger.info(f"Video with burned subtitles saved to: {output_path}")
            return output_path
            
        except ffmpeg.Error as e:
            self.logger.error(f"Error burning subtitles: {e.stderr.decode()}")
            raise
    
    def _parse_srt(self, content: str) -> List[Dict[str, Any]]:
        """Parse SRT subtitle content."""
        import re
        
        pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.*\n)*?)(?=\n\d+\n|\Z)'
        matches = re.findall(pattern, content, re.MULTILINE)
        
        subtitles = []
        for match in matches:
            index, start_time, end_time, text = match
            subtitles.append({
                'index': int(index),
                'start': self._parse_timestamp(start_time),
                'end': self._parse_timestamp(end_time),
                'text': text.strip()
            })
        
        return subtitles
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse SRT timestamp to seconds."""
        parts = timestamp.replace(',', '.').split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to SRT timestamp."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')
    
    def clean_chunks(self, chunk_dir: str):
        """Clean up temporary chunk files."""
        self.logger.info(f"Cleaning up chunks in: {chunk_dir}")
        
        try:
            if Path(chunk_dir).exists():
                shutil.rmtree(chunk_dir)
                self.logger.info("Chunks cleaned successfully")
        except Exception as e:
            self.logger.warning(f"Error cleaning chunks: {str(e)}")