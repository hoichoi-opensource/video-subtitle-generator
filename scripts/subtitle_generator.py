"""Subtitle generation module using Vertex AI."""

import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting
from tenacity import retry, stop_after_attempt, wait_exponential

from .logger import setup_logging, console, log_stage
from .config import get_config
from .utils import ensure_directory, save_job_metadata


class SubtitleGenerator:
    """Generate subtitles using Vertex AI Gemini model."""
    
    def __init__(self, logger_name: str = "subtitle_generator"):
        self.logger = setup_logging(logger_name)
        self.config = get_config()
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Vertex AI model."""
        try:
            # Initialize Vertex AI
            vertexai.init(
                project=self.config.google_cloud["project_id"],
                location=self.config.google_cloud["location"]
            )
            
            # Create model instance with configuration
            model_config = self.config.vertex_ai
            
            self.model = GenerativeModel(
                model_config["model"],  # gemini-2.5-pro-preview-05-06
                system_instruction=[self._get_system_instruction()]
            )
            
            self.generation_config = model_config["generation_config"]
            
            # Configure safety settings
            self.safety_settings = []
            for setting in model_config["safety_settings"]:
                self.safety_settings.append(
                    SafetySetting(
                        category=getattr(SafetySetting.HarmCategory, setting["category"]),
                        threshold=getattr(SafetySetting.HarmBlockThreshold, setting["threshold"])
                    )
                )
            
            self.logger.info(f"Initialized model: {model_config['model']}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Vertex AI model: {str(e)}")
            raise
    
    def _get_system_instruction(self) -> str:
        """Get system instruction for the model."""
        return """You are an expert transcriber and subtitles creator, specializing in creating subtitles and translated subtitles. Your task is to generate accurate and well-formatted subtitles for videos. You should ensure that the subtitles are easy to read, synchronized with the video, and follow the specified format. You can also provide translated subtitles if requested.

Key requirements:
1. Generate accurate transcriptions that match the audio
2. Create properly timed subtitles that are synchronized with speech
3. Use proper punctuation and capitalization
4. Keep subtitle lines reasonably short (max 2 lines, ~40 characters per line)
5. Ensure readability with appropriate timing (minimum 1 second display time)
6. Handle multiple speakers clearly
7. Include relevant non-speech audio descriptions when important [sound effects]
8. Follow standard SRT format exactly"""
    
    def _get_subtitle_prompt(self, language: str) -> str:
        """Get the subtitle generation prompt."""
        language_name = self.config.get_language_by_code(language)["name"]
        
        return f"""Generate subtitles for the provided video.

INSTRUCTIONS: 
- The subtitles should be in {language_name} language.
- If the video is not in {language_name}, translate the subtitles to {language_name}.
- The subtitles should be in SRT format.
- The subtitles should be accurate and match the video content.
- The subtitles should be easy to read and understand.
- The subtitles should be synchronized with the video.
- Timestamps are strictly in the format: `hh:mm:ss,mmm --> hh:mm:ss,mmm`
- Each subtitle block should be numbered sequentially starting from 1.
- Include important non-speech sounds in square brackets [like this].

FORMAT: 
```srt
1
00:00:00,000 --> 00:00:02,500
First subtitle text here

2
00:00:02,500 --> 00:00:05,000
Second subtitle text here
```

Generate the subtitles now:"""
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_subtitle_for_chunk(
        self,
        video_path: str,
        output_path: str,
        language: str = "en",
        chunk_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate subtitle for a single video chunk."""
        self.logger.info(f"Generating subtitle for: {Path(video_path).name}")
        
        try:
            # Create video part for Vertex AI
            if video_path.startswith("gs://"):
                # GCS path
                video_part = Part.from_uri(uri=video_path, mime_type="video/mp4")
            else:
                # Local file - need to upload to GCS first
                raise ValueError("Local file processing not implemented. Please upload to GCS first.")
            
            # Generate content
            prompt = self._get_subtitle_prompt(language)
            
            response = self.model.generate_content(
                [video_part, prompt],
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            # Extract SRT content from response
            srt_content = self._extract_srt_from_response(response.text)
            
            # Validate and clean SRT content
            srt_content = self._validate_and_clean_srt(srt_content, chunk_info)
            
            # Save subtitle file
            ensure_directory(Path(output_path).parent)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            self.logger.info(f"Generated subtitle saved to: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error generating subtitle: {str(e)}")
            raise
    
    def generate_subtitles_for_chunks(
        self,
        chunks: List[Dict[str, Any]],
        gcs_paths: List[str],
        output_dir: str,
        language: str = "en",
        job_id: str = None,
        progress_callback=None
    ) -> List[str]:
        """Generate subtitles for multiple video chunks."""
        subtitle_files = []
        
        for i, (chunk, gcs_path) in enumerate(zip(chunks, gcs_paths)):
            try:
                # Generate output filename
                subtitle_filename = chunk['filename'].replace('.mp4', '.srt')
                subtitle_path = Path(output_dir) / subtitle_filename
                
                # Generate subtitle
                self.generate_subtitle_for_chunk(
                    video_path=gcs_path,
                    output_path=str(subtitle_path),
                    language=language,
                    chunk_info=chunk
                )
                
                subtitle_files.append(str(subtitle_path))
                
                if progress_callback:
                    progress_callback(i + 1, len(chunks))
                
                # Small delay to avoid rate limiting
                if i < len(chunks) - 1:
                    time.sleep(2)
                    
            except Exception as e:
                self.logger.error(f"Failed to generate subtitle for chunk {i+1}: {str(e)}")
                # Continue with other chunks
                subtitle_files.append(None)
        
        # Filter out failed chunks
        subtitle_files = [f for f in subtitle_files if f is not None]
        
        self.logger.info(f"Generated {len(subtitle_files)} subtitles out of {len(chunks)} chunks")
        return subtitle_files
    
    def _extract_srt_from_response(self, response_text: str) -> str:
        """Extract SRT content from model response."""
        # Look for SRT content in code blocks
        if "```srt" in response_text:
            start = response_text.find("```srt") + 6
            end = response_text.find("```", start)
            if end > start:
                srt_content = response_text[start:end].strip()
            else:
                srt_content = response_text[start:].strip()
        else:
            # Assume the entire response is SRT content
            srt_content = response_text.strip()
        
        # Clean up any leading/trailing whitespace
        srt_content = srt_content.strip()
        
        return srt_content
    
    def _validate_and_clean_srt(
        self,
        srt_content: str,
        chunk_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Validate and clean SRT content."""
        lines = srt_content.split('\n')
        cleaned_lines = []
        
        # Track subtitle blocks
        current_block = []
        block_count = 0
        
        for line in lines:
            line = line.strip()
            
            if not line:
                # Empty line - end of subtitle block
                if current_block:
                    # Validate block has at least 3 lines (index, timestamp, text)
                    if len(current_block) >= 3:
                        cleaned_lines.extend(current_block)
                        cleaned_lines.append('')  # Add empty line between blocks
                        block_count += 1
                    current_block = []
            else:
                current_block.append(line)
        
        # Handle last block if no trailing empty line
        if current_block and len(current_block) >= 3:
            cleaned_lines.extend(current_block)
            block_count += 1
        
        # Ensure proper formatting
        final_srt = '\n'.join(cleaned_lines)
        
        # Remove any duplicate empty lines
        while '\n\n\n' in final_srt:
            final_srt = final_srt.replace('\n\n\n', '\n\n')
        
        # Ensure file ends with single newline
        final_srt = final_srt.strip() + '\n'
        
        self.logger.info(f"Validated SRT with {block_count} subtitle blocks")
        
        return final_srt
    
    def convert_to_vtt(self, srt_path: str, vtt_path: str) -> str:
        """Convert SRT to WebVTT format."""
        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()
        
        # Convert to VTT
        vtt_content = "WEBVTT\n\n"
        
        # Replace commas with dots in timestamps
        lines = srt_content.split('\n')
        for line in lines:
            if ' --> ' in line:
                line = line.replace(',', '.')
            vtt_content += line + '\n'
        
        # Save VTT file
        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write(vtt_content)
        
        self.logger.info(f"Converted to VTT: {vtt_path}")
        return vtt_path