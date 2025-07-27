"""
Subtitle Merger
Merges subtitle chunks and creates final output files
"""

import re
import os
import time
import shutil
from pathlib import Path
from typing import List, Dict, Callable, Optional, Tuple
from datetime import timedelta
from .config_manager import ConfigManager
from .utils import ensure_directory_exists
from rich.console import Console

console = Console()

class SubtitleMerger:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.output_dir = Path(config.get('app.output_dir', 'output'))
        
    def merge_subtitles(self, subtitles: List[Dict[str, str]], job_id: str, 
                       video_path: str, progress_callback: Optional[Callable[[int], None]] = None) -> List[str]:
        """Merge subtitle chunks into final files"""
        video_name = Path(video_path).stem
        video_output_dir = self.output_dir / video_name
        
        # Ensure output directory exists
        ensure_directory_exists(str(video_output_dir))
        
        console.print(f"\n[cyan]Saving subtitles to: {video_output_dir}[/cyan]")
        
        # Group subtitles by language and type
        language_groups = {}
        for subtitle in subtitles:
            lang = subtitle['language']
            sdh = subtitle.get('sdh', False)
            key = f"{lang}_sdh" if sdh else lang
            
            if key not in language_groups:
                language_groups[key] = []
            language_groups[key].append(subtitle)
            
        merged_files = []
        total_languages = len(language_groups)
        
        for i, (lang_key, lang_subtitles) in enumerate(language_groups.items()):
            # Sort by chunk number
            lang_subtitles.sort(key=lambda x: self._extract_chunk_number(x['chunk']))
            
            # Extract language and SDH flag
            if '_sdh' in lang_key:
                language = lang_key.replace('_sdh', '')
                suffix = '_sdh'
            else:
                language = lang_key
                suffix = ''
            
            console.print(f"  Merging {language}{suffix} subtitles ({len(lang_subtitles)} chunks)...")
            
            try:
                # Merge SRT files
                merged_srt = self._merge_srt_files(lang_subtitles, job_id)
                
                if not merged_srt.strip():
                    console.print(f"[yellow]    ⚠️  Warning: Empty content for {language}{suffix}[/yellow]")
                    continue
                
                # Save SRT
                srt_filename = f"{video_name}_{language}{suffix}.srt"
                srt_path = video_output_dir / srt_filename
                
                # Write with UTF-8 encoding and BOM for better compatibility
                with open(srt_path, 'w', encoding='utf-8-sig') as f:
                    f.write(merged_srt)
                
                # Verify file was written
                if srt_path.exists() and srt_path.stat().st_size > 0:
                    merged_files.append(str(srt_path))
                    console.print(f"    ✅ Created: {srt_filename} ({srt_path.stat().st_size:,} bytes)")
                else:
                    raise IOError(f"Failed to write SRT file: {srt_path}")
                
                # Convert to VTT
                vtt_filename = f"{video_name}_{language}{suffix}.vtt"
                vtt_path = video_output_dir / vtt_filename
                vtt_content = self._convert_srt_to_vtt(merged_srt)
                
                with open(vtt_path, 'w', encoding='utf-8-sig') as f:
                    f.write(vtt_content)
                
                # Verify VTT file
                if vtt_path.exists() and vtt_path.stat().st_size > 0:
                    merged_files.append(str(vtt_path))
                    console.print(f"    ✅ Created: {vtt_filename} ({vtt_path.stat().st_size:,} bytes)")
                else:
                    raise IOError(f"Failed to write VTT file: {vtt_path}")
                    
            except Exception as e:
                console.print(f"[red]    ❌ Failed to merge {language}{suffix}: {str(e)}[/red]")
                continue
            
            if progress_callback:
                progress = int((i + 1) / total_languages * 100)
                progress_callback(progress)
                
        if merged_files:
            console.print(f"\n[green]✅ Successfully created {len(merged_files)} subtitle files[/green]")
            
            # Create a summary file
            self._create_summary_file(video_output_dir, video_name, merged_files)
        else:
            raise RuntimeError("No subtitle files were successfully created")
            
        return merged_files
        
    def _extract_chunk_number(self, chunk_path: str) -> int:
        """Extract chunk number from path"""
        match = re.search(r'chunk_(\d+)', chunk_path)
        if match:
            return int(match.group(1))
        return 0
        
    def _merge_srt_files(self, subtitles: List[Dict[str, str]], job_id: str) -> str:
        """Merge SRT files with proper timing adjustment"""
        merged_content = []
        subtitle_counter = 1
        
        # Get chunk duration from config
        chunk_duration = self.config.get('processing.chunk_duration', 60)
        
        for subtitle in subtitles:
            # Get subtitle content
            content = ''
            
            if 'content' in subtitle and subtitle['content']:
                content = subtitle['content']
            elif 'local' in subtitle and os.path.exists(subtitle['local']):
                try:
                    with open(subtitle['local'], 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    console.print(f"[yellow]    Warning: Failed to read {subtitle['local']}: {str(e)}[/yellow]")
                    continue
            else:
                console.print(f"[yellow]    Warning: No content for subtitle file[/yellow]")
                continue
                    
            # Parse SRT entries
            entries = self._parse_srt_content(content)
            
            if not entries:
                console.print(f"[yellow]    Warning: No valid entries in subtitle file[/yellow]")
                continue
            
            # Extract actual chunk number from filename
            chunk_number = self._extract_chunk_number(subtitle['chunk'])
            
            # Calculate time offset based on actual chunk number (not enumeration index)
            time_offset_seconds = chunk_duration * chunk_number
            
            console.print(f"    Processing chunk_{chunk_number:03d} with offset {time_offset_seconds}s")
            
            # Process each entry
            for entry in entries:
                # Parse timestamps
                start_seconds = self._timestamp_to_seconds(entry['start'])
                end_seconds = self._timestamp_to_seconds(entry['end'])
                
                # Add offset
                start_seconds += time_offset_seconds
                end_seconds += time_offset_seconds
                
                # Convert back to SRT format
                start_str = self._seconds_to_timestamp(start_seconds)
                end_str = self._seconds_to_timestamp(end_seconds)
                
                # Create merged entry
                merged_entry = f"{subtitle_counter}\n{start_str} --> {end_str}\n{entry['text']}"
                merged_content.append(merged_entry)
                subtitle_counter += 1
                
        if not merged_content:
            return ""
            
        # Join with double newlines as per SRT format
        return '\n\n'.join(merged_content) + '\n'
        
    def _parse_srt_content(self, content: str) -> List[Dict[str, any]]:
        """Parse SRT content into structured entries"""
        entries = []
        
        # Clean content
        content = content.strip().replace('\ufeff', '')
        
        if not content:
            return entries
            
        # Split into subtitle blocks by double newlines
        blocks = re.split(r'\n\s*\n', content)
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue
                
            lines = block.split('\n')
            if len(lines) < 3:
                continue
                
            # First line should be the subtitle number
            if not lines[0].strip().isdigit():
                continue
                
            # Second line should contain the timestamp
            timestamp_match = re.match(
                r'(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})',
                lines[1].strip()
            )
            
            if timestamp_match:
                start_time = timestamp_match.group(1).replace('.', ',')
                end_time = timestamp_match.group(2).replace('.', ',')
                
                # Join remaining lines as subtitle text
                text = '\n'.join(lines[2:]).strip()
                
                if text:
                    entries.append({
                        'number': int(lines[0].strip()),
                        'start': start_time,
                        'end': end_time,
                        'text': text
                    })
                    
        return entries
        
    def _timestamp_to_seconds(self, timestamp: str) -> float:
        """Convert SRT timestamp to seconds"""
        try:
            # Handle both comma and dot as decimal separator
            timestamp = timestamp.replace(',', '.')
            
            # Parse hours:minutes:seconds.milliseconds
            time_parts = timestamp.split(':')
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            
            # Handle seconds and milliseconds
            seconds_parts = time_parts[2].split('.')
            seconds = int(seconds_parts[0])
            milliseconds = int(seconds_parts[1].ljust(3, '0')[:3]) if len(seconds_parts) > 1 else 0
            
            total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
            return total_seconds
            
        except Exception as e:
            console.print(f"[yellow]Warning: Invalid timestamp '{timestamp}': {str(e)}[/yellow]")
            return 0.0
            
    def _seconds_to_timestamp(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
        
    def _convert_srt_to_vtt(self, srt_content: str) -> str:
        """Convert SRT to WebVTT format"""
        # Add WebVTT header
        vtt_content = "WEBVTT\n\n"
        
        # Parse SRT entries
        entries = self._parse_srt_content(srt_content)
        
        # Convert each entry
        for i, entry in enumerate(entries, 1):
            # Replace comma with dot in timestamps for VTT format
            start_time = entry['start'].replace(',', '.')
            end_time = entry['end'].replace(',', '.')
            
            # Add entry (VTT doesn't require subtitle numbers)
            vtt_content += f"{start_time} --> {end_time}\n{entry['text']}\n\n"
        
        return vtt_content.strip() + '\n'
        
    def _create_summary_file(self, output_dir: Path, video_name: str, files: List[str]) -> None:
        """Create a summary file with processing information"""
        summary_path = output_dir / f"{video_name}_subtitle_info.txt"
        
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"Video Subtitle Generation Summary\n")
                f.write(f"================================\n\n")
                f.write(f"Video: {video_name}\n")
                f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Output Directory: {output_dir}\n\n")
                f.write(f"Generated Files:\n")
                
                for file_path in sorted(files):
                    file_name = Path(file_path).name
                    file_size = Path(file_path).stat().st_size
                    f.write(f"  - {file_name} ({file_size:,} bytes)\n")
                    
                f.write(f"\nTotal Files: {len(files)}\n")
                f.write(f"\nNote: These subtitles were generated using AI and may require manual review.\n")
                
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to create summary file: {str(e)}[/yellow]")
