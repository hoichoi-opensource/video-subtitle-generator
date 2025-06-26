"""
AI Generator
Handles subtitle generation using Google Vertex AI
"""

import os
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting
from google.cloud import storage
from config_manager import ConfigManager
from rich.console import Console

console = Console()

class AIGenerator:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.project_id = config.get('gcp.project_id')
        self.location = config.get('gcp.location', 'us-central1')
        self.model = None
        self.storage_client = None
        
    def initialize(self) -> None:
        """Initialize Vertex AI with proper authentication"""
        try:
            # Set up authentication
            auth_method = self.config.get('gcp.auth_method', 'service_account')
            
            if auth_method == 'service_account':
                service_account_path = self.config.get('gcp.service_account_path', './service-account.json')
                if not Path(service_account_path).exists():
                    raise FileNotFoundError(f"Service account file not found: {service_account_path}")
                
                # Set environment variable for authentication
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(Path(service_account_path).resolve())
            
            # Initialize Vertex AI
            vertexai.init(project=self.project_id, location=self.location)
            
            # Initialize model with system instruction
            model_name = self.config.get('vertex_ai.default_model', 'gemini-1.5-pro-preview-05-06')
            
            system_instruction = """You are an expert transcriber and subtitles creator, specializing in creating subtitles and translated subtitles. Your task is to generate accurate and well-formatted subtitles for videos. You should ensure that the subtitles are easy to read, synchronized with the video, and follow the specified format. You can also provide translated subtitles if requested."""
            
            self.model = GenerativeModel(
                model_name,
                system_instruction=[system_instruction]
            )
            
            # Initialize storage client for video access
            from google.oauth2 import service_account
            
            if auth_method == 'service_account':
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                self.storage_client = storage.Client(project=self.project_id, credentials=credentials)
            else:
                self.storage_client = storage.Client(project=self.project_id)
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Vertex AI: {str(e)}")
            
    def generate_subtitles(self, chunks: List[Dict[str, str]], languages: List[str], 
                          bucket_name: str, progress_callback: Optional[Callable[[int], None]] = None) -> List[Dict[str, str]]:
        """Generate subtitles for all chunks and languages"""
        generated_subtitles = []
        total_tasks = len(chunks) * len(languages)
        
        # Check if SDH is enabled
        enable_sdh = self.config.config.get('current_job', {}).get('enable_sdh', False)
        
        # Determine which subtitle types to generate
        subtitle_types = ['regular']
        if enable_sdh:
            subtitle_types.append('sdh')
            total_tasks *= 2  # Double the tasks for SDH
            
        completed_tasks = 0
        
        for chunk_info in chunks:
            chunk_name = chunk_info['chunk']
            chunk_gcs_uri = chunk_info['gcs']
            
            console.print(f"    Processing chunk: {chunk_name}")
            
            for language in languages:
                for subtitle_type in subtitle_types:
                    try:
                        # Generate subtitle
                        subtitle_content = self._generate_subtitle_for_chunk(
                            chunk_gcs_uri,
                            language,
                            is_sdh=(subtitle_type == 'sdh')
                        )
                        
                        if subtitle_content:
                            # Simple validation: check if subtitles cover reasonable duration
                            last_timestamp = self._get_last_timestamp(subtitle_content)
                            if last_timestamp < 30:  # Less than 30 seconds coverage
                                console.print(f"[yellow]      Warning: Short subtitle duration ({last_timestamp}s) for {chunk_name}[/yellow]")
                            
                            # Save to GCS
                            blob_name = f"subtitles/{chunk_name}_{language}"
                            if subtitle_type == 'sdh':
                                blob_name += "_sdh"
                            blob_name += ".srt"
                            
                            # Upload to GCS
                            bucket = self.storage_client.bucket(bucket_name)
                            blob = bucket.blob(blob_name)
                            blob.upload_from_string(subtitle_content, content_type='text/plain')
                            
                            generated_subtitles.append({
                                'chunk': chunk_name,
                                'language': language,
                                'sdh': (subtitle_type == 'sdh'),
                                'gcs': f"gs://{bucket_name}/{blob_name}",
                                'blob_name': blob_name
                            })
                            
                    except Exception as e:
                        console.print(f"[red]      Error generating {language} {subtitle_type}: {str(e)}[/red]")
                        
                    completed_tasks += 1
                    if progress_callback:
                        progress = int(completed_tasks / total_tasks * 100)
                        progress_callback(progress)
                        
        return generated_subtitles
        
    def _generate_subtitle_for_chunk(self, video_uri: str, language: str, is_sdh: bool) -> Optional[str]:
        """Generate subtitle for a single chunk"""
        # Get appropriate prompt
        if is_sdh:
            prompt = self.config.get_sdh_prompt(language)
        else:
            prompt = self.config.get_prompt(language)
            
        if not prompt:
            console.print(f"[yellow]      Warning: No prompt found for {language}{'_sdh' if is_sdh else ''}[/yellow]")
            return None
            
        # Handle Hindi special case
        if language == 'hin' and not is_sdh:
            # Generate using both methods and compare
            return self._generate_hindi_subtitle(video_uri, prompt)
            
        # Create video part
        video_part = Part.from_uri(
            uri=video_uri,
            mime_type="video/mp4"
        )
        
        # Get safety settings
        safety_settings = self._get_safety_settings()
        
        # Generate subtitle
        try:
            response = self.model.generate_content(
                [video_part, prompt],
                safety_settings=safety_settings,
                generation_config={
                    "temperature": self.config.get('vertex_ai.temperature', 0.2),
                    "top_p": self.config.get('vertex_ai.top_p', 0.95),
                    "max_output_tokens": self.config.get('vertex_ai.max_output_tokens', 8192)
                }
            )
            
            if response.text:
                # Clean and validate SRT format
                return self._clean_srt_content(response.text)
            else:
                console.print(f"[yellow]      Warning: Empty response from AI[/yellow]")
                return None
                
        except Exception as e:
            console.print(f"[red]      AI generation error: {str(e)}[/red]")
            return None
            
    def _generate_hindi_subtitle(self, video_uri: str, prompt: str) -> Optional[str]:
        """Generate Hindi subtitle using dual method approach"""
        # Method 1: Translation approach
        translate_prompt = self.config.get_prompt('hin', 'translate')
        
        # Method 2: Direct approach
        direct_prompt = self.config.get_prompt('hin', 'direct')
        
        results = {}
        
        # Try translation method
        if translate_prompt:
            try:
                video_part = Part.from_uri(uri=video_uri, mime_type="video/mp4")
                response = self.model.generate_content(
                    [video_part, translate_prompt],
                    safety_settings=self._get_safety_settings()
                )
                if response.text:
                    results['translate'] = self._clean_srt_content(response.text)
            except:
                pass
                
        # Try direct method
        if direct_prompt:
            try:
                video_part = Part.from_uri(uri=video_uri, mime_type="video/mp4")
                response = self.model.generate_content(
                    [video_part, direct_prompt],
                    safety_settings=self._get_safety_settings()
                )
                if response.text:
                    results['direct'] = self._clean_srt_content(response.text)
            except:
                pass
                
        # Compare and select best result
        if not results:
            return None
            
        # For now, prefer direct method if available
        # In future, could implement quality scoring
        if 'direct' in results:
            return results['direct']
        else:
            return results.get('translate')
            
    def _get_safety_settings(self) -> List[SafetySetting]:
        """Get safety settings for AI generation"""
        # Match the reference implementation - set all to OFF
        settings = [
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
        
        return settings
        
    def _get_last_timestamp(self, srt_content: str) -> float:
        """Get the last timestamp from SRT content in seconds"""
        try:
            # Find all timestamps in the content
            import re
            timestamp_pattern = r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})'
            matches = re.findall(timestamp_pattern, srt_content)
            
            if not matches:
                return 0.0
            
            # Get the end time of the last subtitle
            last_end_time = matches[-1][1]
            
            # Convert to seconds
            parts = last_end_time.replace(',', '.').split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            
            return hours * 3600 + minutes * 60 + seconds
            
        except Exception:
            return 0.0
        
    def _clean_srt_content(self, content: str) -> str:
        """Clean and validate SRT content - more flexible parsing like reference implementation"""
        # Remove any markdown formatting
        content = content.strip()
        
        # Extract SRT content from code blocks if present
        if '```srt' in content:
            srt_file = content.split('```srt')[1]
            srt_file = srt_file.split('```')[0]
            if srt_file.startswith('\n'):
                srt_file = srt_file[1:]
        else:
            srt_file = content
            
        # Use simple line processing like reference implementation
        final_srt = ""
        lines = srt_file.strip().split('\n')
        
        # Track current position in subtitle block (0=number, 1=timestamp, 2+=text)
        block_position = 0
        current_block = []
        
        for line in lines:
            line = line.strip()
            
            # Empty line indicates end of subtitle block
            if not line:
                if current_block and len(current_block) >= 3:
                    # We have a complete subtitle block
                    final_srt += '\n'.join(current_block) + '\n\n'
                current_block = []
                block_position = 0
                continue
            
            # Check if this is a subtitle number (all digits)
            if line.isdigit() and (block_position == 0 or not current_block):
                # Start new subtitle block
                if current_block and len(current_block) >= 3:
                    # Save previous block if complete
                    final_srt += '\n'.join(current_block) + '\n\n'
                current_block = [line]
                block_position = 1
            # Check if this is a timestamp
            elif '-->' in line and block_position == 1:
                current_block.append(line)
                block_position = 2
            # Everything else is subtitle text
            elif block_position >= 2 or (current_block and len(current_block) >= 2):
                current_block.append(line)
                block_position += 1
            # Handle case where there are no empty lines between subtitles
            elif line.isdigit() and current_block and len(current_block) >= 3:
                # Save current block and start new one
                final_srt += '\n'.join(current_block) + '\n\n'
                current_block = [line]
                block_position = 1
                
        # Don't forget the last subtitle block
        if current_block and len(current_block) >= 3:
            final_srt += '\n'.join(current_block) + '\n\n'
        
        # Clean up final output
        final_srt = final_srt.strip()
        if final_srt:
            final_srt += '\n'
            
        return final_srt
