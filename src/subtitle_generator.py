"""Subtitle generation module using Vertex AI."""

import os
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting
from google.cloud import storage
import logging
import re
from datetime import timedelta

class SubtitleGenerator:
    """Handles subtitle generation using Vertex AI."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._init_vertex_ai()
        self._init_storage_client()
        
    def _init_vertex_ai(self):
        """Initialize Vertex AI with configuration."""
        project_id = self.config.get('gcp.project_id')
        location = self.config.get('gcp.location', 'us-central1')
        
        # Initialize with credentials if provided
        credentials_path = self.config.get('gcp.credentials_path')
        if credentials_path and os.path.exists(credentials_path):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        vertexai.init(project=project_id, location=location)
        
        # Initialize model
        self.model = GenerativeModel(
            self.config.get('vertex_ai.model', 'gemini-2.0-pro-exp'),
            system_instruction=[self._get_system_instruction()]
        )
        
        # Generation config
        self.generation_config = {
            "max_output_tokens": self.config.get('vertex_ai.max_output_tokens', 8192),
            "temperature": self.config.get('vertex_ai.temperature', 0.2),
            "top_p": self.config.get('vertex_ai.top_p', 0.95),
        }
        
        # Safety settings
        self.safety_settings = [
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=SafetySetting.HarmBlockThreshold.OFF,
            ),
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=SafetySetting.HarmBlockThreshold.OFF,
            ),
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=SafetySetting.HarmBlockThreshold.OFF,
            ),
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=SafetySetting.HarmBlockThreshold.OFF,
            ),
        ]
    
    def _init_storage_client(self):
        """Initialize Google Cloud Storage client."""
        self.storage_client = storage.Client()
        self.bucket_name = self.config.get('storage.bucket_name')
        
        if self.bucket_name:
            try:
                self.bucket = self.storage_client.bucket(self.bucket_name)
                if not self.bucket.exists():
                    self.bucket = self.storage_client.create_bucket(self.bucket_name)
                    self.logger.info(f"Created bucket: {self.bucket_name}")
            except Exception as e:
                self.logger.warning(f"Could not access/create bucket: {e}")
                self.bucket = None
        else:
            self.bucket = None
    
    def _get_system_instruction(self) -> str:
        """Get system instruction for the model."""
        return """You are an expert transcriber and subtitle creator, specializing in creating accurate subtitles 
and translations. Your task is to generate well-formatted subtitles that are:
1. Accurately transcribed from the audio
2. Properly synchronized with the video
3. Translated naturally while preserving meaning
4. Formatted correctly in the requested subtitle format
5. Easy to read with appropriate line breaks and timing"""
    
    def _get_prompt(self, source_lang: str, target_lang: str, translation_method: str = "direct") -> str:
        """Generate prompt for subtitle generation with specific translation methods."""
        
        # For Hindi translation via English
        if target_lang == 'hi' and translation_method == 'via_english':
            return f"""Generate subtitles for the provided video.

INSTRUCTIONS:
- First, transcribe all spoken dialogue accurately in the original language
- Then translate to English maintaining natural flow
- Keep English subtitles for later Hindi translation
- Include relevant sound effects in square brackets [like this]
- Break long sentences into readable chunks (max 42 characters per line)
- Ensure proper synchronization with speech timing
- Format: SRT with timestamps in hh:mm:ss,mmm --> hh:mm:ss,mmm

OUTPUT FORMAT:
```srt
1
00:00:00,000 --> 00:00:03,450
First subtitle line in English

2
00:00:03,500 --> 00:00:07,200
Second subtitle line in English
can span multiple lines
```

Generate complete English subtitles first:"""
        
        # Standard prompt for direct translation
        lang_instruction = ""
        if source_lang != 'auto':
            lang_instruction = f"The audio is in {source_lang}. "
        
        if target_lang != source_lang:
            if target_lang == 'hi':
                lang_instruction += "Translate directly to Hindi (हिन्दी)."
            elif target_lang == 'bn':
                lang_instruction += "Translate to Bengali (বাংলা)."
            else:
                lang_instruction += f"Translate to {target_lang}."
        
        return f"""Generate subtitles for the provided video.

INSTRUCTIONS:
- Transcribe all spoken dialogue accurately
- {lang_instruction}
- Use natural, conversational translation that preserves meaning
- Include relevant sound effects in square brackets [like this]
- Break long sentences into readable chunks (max 42 characters per line)
- Ensure proper synchronization with speech timing
- Maintain exact timestamp sync with the audio
- Format: SRT with timestamps in hh:mm:ss,mmm --> hh:mm:ss,mmm

OUTPUT FORMAT:
```srt
1
00:00:00,000 --> 00:00:03,450
First subtitle line here

2
00:00:03,500 --> 00:00:07,200
Second subtitle line
can span multiple lines

3
00:00:07,250 --> 00:00:10,000
[Sound effect] Dialogue here
```

Generate complete, properly formatted SRT subtitles:"""
    
    def _upload_chunk_to_gcs(self, chunk_path: Path) -> str:
        """Upload chunk to GCS and return URI."""
        if not self.bucket:
            return str(chunk_path)  # Return local path if no bucket
        
        blob_name = f"{self.config.get('storage.chunks_prefix', 'chunks')}/{chunk_path.name}"
        blob = self.bucket.blob(blob_name)
        
        blob.upload_from_filename(str(chunk_path))
        return f"gs://{self.bucket_name}/{blob_name}"
    
    def _process_single_chunk(self, chunk_info: Tuple[int, Path], source_lang: str, 
                            target_lang: str, retry_attempts: int = 3) -> Dict[str, Any]:
        """Process a single video chunk with translation method support."""
        chunk_index, chunk_path = chunk_info
        translation_method = self.config.get('subtitles.hindi_translation_method', 'direct')
        
        # Special handling for Hindi via English
        if target_lang == 'hi' and translation_method == 'via_english':
            # Step 1: Generate English subtitles first
            english_result = self._generate_subtitles_for_chunk(
                chunk_index, chunk_path, source_lang, 'en', 'direct', retry_attempts
            )
            
            # Step 2: Translate English to Hindi
            hindi_subtitles = self._translate_subtitles_to_hindi(english_result['subtitles'])
            
            return {
                'chunk_index': chunk_index,
                'subtitles': hindi_subtitles,
                'raw_srt': self._format_as_srt(hindi_subtitles),
                'english_subtitles': english_result['subtitles']  # Keep for reference
            }
        else:
            # Direct translation
            return self._generate_subtitles_for_chunk(
                chunk_index, chunk_path, source_lang, target_lang, 'direct', retry_attempts
            )
    
    def _generate_subtitles_for_chunk(self, chunk_index: int, chunk_path: Path, 
                                    source_lang: str, target_lang: str, 
                                    translation_method: str, retry_attempts: int) -> Dict[str, Any]:
        """Generate subtitles for a chunk with retry logic."""
        for attempt in range(retry_attempts):
            try:
                # Upload to GCS if configured
                if self.bucket:
                    chunk_uri = self._upload_chunk_to_gcs(chunk_path)
                    video_part = Part.from_uri(uri=chunk_uri, mime_type="video/mp4")
                else:
                    # Use local file
                    with open(chunk_path, 'rb') as f:
                        video_data = f.read()
                    video_part = Part.from_data(video_data, mime_type="video/mp4")
                
                # Generate subtitles
                prompt = self._get_prompt(source_lang, target_lang, translation_method)
                response = self.model.generate_content(
                    [video_part, prompt],
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings,
                )
                
                # Extract SRT content
                srt_content = self._extract_srt_content(response.text)
                
                # Parse and validate SRT
                subtitles = self._parse_srt(srt_content)
                
                return {
                    'chunk_index': chunk_index,
                    'subtitles': subtitles,
                    'raw_srt': srt_content
                }
                
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for chunk {chunk_index}: {e}")
                if attempt < retry_attempts - 1:
                    time.sleep(self.config.get('processing.retry_delay', 5))
                else:
                    raise Exception(f"Failed to process chunk {chunk_index} after {retry_attempts} attempts: {e}")
    
    def _translate_subtitles_to_hindi(self, english_subtitles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Translate English subtitles to Hindi using Vertex AI."""
        hindi_subtitles = []
        
        # Process in batches for efficiency
        batch_size = 10
        for i in range(0, len(english_subtitles), batch_size):
            batch = english_subtitles[i:i + batch_size]
            
            # Create translation prompt
            texts_to_translate = [sub['text'] for sub in batch]
            prompt = f"""Translate the following English subtitles to Hindi (हिन्दी):

{chr(10).join(f"{j+1}. {text}" for j, text in enumerate(texts_to_translate))}

INSTRUCTIONS:
- Provide natural, conversational Hindi translations
- Preserve the meaning and tone
- Keep [sound effects] in English within square brackets
- Use Devanagari script for Hindi text
- Maintain the same numbering

Provide only the Hindi translations in the same numbered format:"""
            
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings,
                )
                
                # Parse translations
                translations = self._parse_numbered_translations(response.text, len(batch))
                
                # Create Hindi subtitle entries
                for j, subtitle in enumerate(batch):
                    hindi_subtitle = subtitle.copy()
                    hindi_subtitle['text'] = translations[j] if j < len(translations) else subtitle['text']
                    hindi_subtitles.append(hindi_subtitle)
                    
            except Exception as e:
                self.logger.error(f"Failed to translate batch: {e}")
                # Fallback: keep English text
                hindi_subtitles.extend(batch)
        
        return hindi_subtitles
    
    def _parse_numbered_translations(self, response_text: str, expected_count: int) -> List[str]:
        """Parse numbered translations from response."""
        translations = []
        lines = response_text.strip().split('\n')
        
        for line in lines:
            # Match numbered lines (1. text, 2. text, etc.)
            match = re.match(r'^\d+\.\s*(.+)$', line.strip())
            if match:
                translations.append(match.group(1).strip())
        
        # Ensure we have the right number of translations
        while len(translations) < expected_count:
            translations.append("")
        
        return translations[:expected_count]
    
    def _extract_srt_content(self, response_text: str) -> str:
        """Extract SRT content from model response."""
        # Look for content between ```srt markers
        srt_match = re.search(r'```srt\s*\n(.*?)\n```', response_text, re.DOTALL)
        if srt_match:
            return srt_match.group(1).strip()
        
        # Fallback: look for SRT-like content
        lines = response_text.strip().split('\n')
        srt_lines = []
        in_srt = False
        
        for line in lines:
            if re.match(r'^\d+$', line.strip()):
                in_srt = True
            if in_srt and line.strip():
                srt_lines.append(line)
            elif in_srt and not line.strip() and srt_lines:
                srt_lines.append('')
        
        return '\n'.join(srt_lines)
    
    def _parse_srt(self, srt_content: str) -> List[Dict[str, Any]]:
        """Parse SRT content into structured format."""
        subtitles = []
        blocks = srt_content.strip().split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    # Parse index
                    index = int(lines[0])
                    
                    # Parse timing
                    timing_match = re.match(
                        r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})',
                        lines[1]
                    )
                    
                    if timing_match:
                        start_time = timing_match.group(1)
                        end_time = timing_match.group(2)
                        
                        # Get text (may be multiple lines)
                        text = '\n'.join(lines[2:])
                        
                        subtitles.append({
                            'index': index,
                            'start': start_time,
                            'end': end_time,
                            'text': text
                        })
                except Exception as e:
                    self.logger.warning(f"Failed to parse subtitle block: {e}")
                    continue
        
        return subtitles
    
    def process_chunks(self, chunks: List[Path], source_lang: str, target_lang: str,
                      progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Process multiple chunks in parallel."""
        max_workers = self.config.get('processing.max_parallel_workers', 5)
        chunk_duration = self.config.get('processing.chunk_duration', 60)
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_chunk = {
                executor.submit(
                    self._process_single_chunk,
                    (i, chunk),
                    source_lang,
                    target_lang
                ): i
                for i, chunk in enumerate(chunks)
            }
            
            # Process completed tasks
            for future in as_completed(future_to_chunk):
                try:
                    result = future.result()
                    
                    # Adjust timestamps based on chunk position
                    chunk_index = result['chunk_index']
                    offset_seconds = chunk_index * chunk_duration
                    
                    adjusted_subtitles = self._adjust_timestamps(
                        result['subtitles'],
                        offset_seconds
                    )
                    
                    result['subtitles'] = adjusted_subtitles
                    results.append(result)
                    
                    if progress_callback:
                        progress_callback()
                        
                except Exception as e:
                    self.logger.error(f"Failed to process chunk: {e}")
                    raise
        
        # Sort results by chunk index
        results.sort(key=lambda x: x['chunk_index'])
        return results
    
    def _adjust_timestamps(self, subtitles: List[Dict[str, Any]], offset_seconds: float) -> List[Dict[str, Any]]:
        """Adjust subtitle timestamps by offset."""
        adjusted = []
        
        for subtitle in subtitles:
            adjusted_subtitle = subtitle.copy()
            adjusted_subtitle['start'] = self._add_time_offset(subtitle['start'], offset_seconds)
            adjusted_subtitle['end'] = self._add_time_offset(subtitle['end'], offset_seconds)
            adjusted.append(adjusted_subtitle)
        
        return adjusted
    
    def _add_time_offset(self, time_str: str, offset_seconds: float) -> str:
        """Add offset to time string."""
        # Parse time string
        time_match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_str)
        if not time_match:
            return time_str
        
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        seconds = int(time_match.group(3))
        milliseconds = int(time_match.group(4))
        
        # Convert to total seconds
        total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
        total_seconds += offset_seconds
        
        # Convert back to time format
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def merge_subtitles(self, chunk_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge subtitles from all chunks."""
        merged = []
        index = 1
        
        for chunk_result in chunk_results:
            for subtitle in chunk_result['subtitles']:
                subtitle_copy = subtitle.copy()
                subtitle_copy['index'] = index
                merged.append(subtitle_copy)
                index += 1
        
        return merged
    
    def save_subtitles(self, subtitles: List[Dict[str, Any]], output_path: Path, format: str = 'srt'):
        """Save subtitles to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == 'srt':
            content = self._format_as_srt(subtitles)
        elif format.lower() == 'vtt':
            content = self._format_as_vtt(subtitles)
        else:
            raise ValueError(f"Unsupported subtitle format: {format}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _format_as_srt(self, subtitles: List[Dict[str, Any]]) -> str:
        """Format subtitles as SRT."""
        lines = []
        
        for subtitle in subtitles:
            lines.append(str(subtitle['index']))
            lines.append(f"{subtitle['start']} --> {subtitle['end']}")
            lines.append(subtitle['text'])
            lines.append('')
        
        return '\n'.join(lines)
    
    def _format_as_vtt(self, subtitles: List[Dict[str, Any]]) -> str:
        """Format subtitles as WebVTT."""
        lines = ['WEBVTT', '']
        
        for subtitle in subtitles:
            # Convert SRT timestamp to VTT format
            start = subtitle['start'].replace(',', '.')
            end = subtitle['end'].replace(',', '.')
            
            lines.append(f"{start} --> {end}")
            lines.append(subtitle['text'])
            lines.append('')
        
        return '\n'.join(lines)
