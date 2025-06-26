"""
Video Chunker
Handles video analysis and splitting into chunks
"""

import os
import ffmpeg
from pathlib import Path
from typing import List, Dict, Callable, Optional, Any
from config_manager import ConfigManager
from utils import ensure_directory_exists, safe_eval_fraction

class VideoChunker:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.chunk_duration = config.get('processing.chunk_duration', 60)
        self.temp_dir = Path(config.get('app.temp_dir', 'temp'))
        
    def analyze_video(self, video_path: str) -> Dict[str, Any]:
        """Analyze video and get metadata"""
        try:
            probe = ffmpeg.probe(video_path)
            
            # Extract video stream info
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
            
            # Get duration
            duration = float(probe['format']['duration'])
            
            # Calculate number of chunks needed
            total_chunks = int((duration + self.chunk_duration - 1) // self.chunk_duration)
            
            # Format duration string
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            return {
                'duration': duration,
                'duration_str': duration_str,
                'total_chunks': total_chunks,
                'width': video_stream.get('width') if video_stream else None,
                'height': video_stream.get('height') if video_stream else None,
                'fps': safe_eval_fraction(video_stream.get('r_frame_rate', '0/1')) if video_stream else None,
                'video_codec': video_stream.get('codec_name') if video_stream else None,
                'audio_codec': audio_stream.get('codec_name') if audio_stream else None,
                'audio_channels': audio_stream.get('channels') if audio_stream else None,
                'audio_sample_rate': audio_stream.get('sample_rate') if audio_stream else None,
                'file_size': os.path.getsize(video_path)
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to analyze video: {str(e)}")
            
    def split_video(self, video_path: str, job_id: str, 
                   progress_callback: Optional[Callable[[int], None]] = None) -> List[str]:
        """Split video into chunks"""
        video_info = self.analyze_video(video_path)
        total_duration = video_info['duration']
        total_chunks = video_info['total_chunks']
        
        # Create chunks directory
        chunks_dir = self.temp_dir / job_id
        ensure_directory_exists(str(chunks_dir))
        
        chunks = []
        
        for i in range(total_chunks):
            start_time = i * self.chunk_duration
            
            # Calculate actual chunk duration (last chunk might be shorter)
            if i == total_chunks - 1:
                chunk_duration = total_duration - start_time
            else:
                chunk_duration = self.chunk_duration
                
            # Output file path
            chunk_filename = f"chunk_{i:03d}.mp4"
            chunk_path = chunks_dir / chunk_filename
            
            try:
                # Use ffmpeg to extract chunk with precise timing
                (
                    ffmpeg
                    .input(video_path, ss=start_time, t=chunk_duration)
                    .output(
                        str(chunk_path),
                        vcodec='libx264',
                        acodec='aac',
                        audio_bitrate='128k',
                        video_bitrate='1000k',
                        preset='fast',
                        movflags='faststart',
                        avoid_negative_ts='make_zero',  # Ensure timestamps start at 0
                        **{'threads': '0'}  # Use all available threads
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
                
                # Verify chunk was created
                if chunk_path.exists() and chunk_path.stat().st_size > 0:
                    chunks.append(str(chunk_path))
                else:
                    raise RuntimeError(f"Failed to create chunk {i}")
                    
            except Exception as e:
                raise RuntimeError(f"Failed to create chunk {i}: {str(e)}")
                
            # Update progress
            if progress_callback:
                progress = int((i + 1) / total_chunks * 100)
                progress_callback(progress)
                
        return chunks
        
    def extract_audio(self, video_path: str, output_path: str) -> str:
        """Extract audio from video"""
        try:
            (
                ffmpeg
                .input(video_path)
                .output(
                    output_path,
                    acodec='pcm_s16le',
                    ac=1,
                    ar='16k'
                )
                .overwrite_output()
                .run(quiet=True)
            )
            
            if not Path(output_path).exists():
                raise RuntimeError("Failed to extract audio")
                
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"Failed to extract audio: {str(e)}")
            
    def get_chunk_info(self, chunk_path: str) -> Dict[str, Any]:
        """Get information about a chunk"""
        try:
            probe = ffmpeg.probe(chunk_path)
            duration = float(probe['format']['duration'])
            
            return {
                'path': chunk_path,
                'duration': duration,
                'size': os.path.getsize(chunk_path)
            }
            
        except Exception as e:
            return {
                'path': chunk_path,
                'duration': 0,
                'size': 0,
                'error': str(e)
            }
            
    def cleanup_chunks(self, job_id: str) -> None:
        """Clean up chunk files for a job"""
        chunks_dir = self.temp_dir / job_id
        
        if chunks_dir.exists():
            import shutil
            shutil.rmtree(chunks_dir, ignore_errors=True)
