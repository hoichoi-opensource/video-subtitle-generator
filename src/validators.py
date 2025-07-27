"""
Input validation and sanitization for production-grade reliability
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import mimetypes
import subprocess
from urllib.parse import urlparse

from .exceptions import ValidationError, ConfigurationError


class VideoValidator:
    """Comprehensive video file validation"""
    
    SUPPORTED_FORMATS = {
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
        '.flv': 'video/x-flv',
        '.wmv': 'video/x-ms-wmv'
    }
    
    MAX_FILE_SIZE_GB = 50  # Production limit
    MIN_FILE_SIZE_KB = 100  # Minimum viable video
    MAX_DURATION_HOURS = 12  # Maximum processing duration
    
    @classmethod
    def validate_file_path(cls, file_path: Union[str, Path]) -> Path:
        """Validate and sanitize file path"""
        if not file_path:
            raise ValidationError("File path cannot be empty")
        
        try:
            path = Path(file_path).resolve()
        except (OSError, ValueError) as e:
            raise ValidationError(f"Invalid file path: {file_path}", context={'error': str(e)})
        
        # Security: Enhanced path traversal protection
        original_path = Path(file_path)
        
        # Check for suspicious patterns
        path_str = str(original_path)
        if any(pattern in path_str for pattern in ['../', '..\\', '%2e%2e', '%2E%2E']):
            raise ValidationError(f"Path traversal attempt detected: {file_path}")
        
        # Ensure resolved path is within expected boundaries
        cwd = Path.cwd()
        try:
            path.relative_to(cwd)
        except ValueError:
            # Path is outside current working directory, check if it's a valid absolute path
            if not path.is_absolute():
                raise ValidationError(f"Invalid relative path outside working directory: {file_path}")
            # For absolute paths, ensure they exist and are accessible
            if not path.exists():
                raise ValidationError(f"Absolute path does not exist: {file_path}")
        
        if not path.exists():
            raise ValidationError(f"File does not exist: {path}")
        
        if not path.is_file():
            raise ValidationError(f"Path is not a file: {path}")
        
        return path
    
    @classmethod
    def validate_file_format(cls, file_path: Path) -> str:
        """Validate video file format"""
        suffix = file_path.suffix.lower()
        
        if suffix not in cls.SUPPORTED_FORMATS:
            raise ValidationError(
                f"Unsupported video format: {suffix}",
                context={
                    'file': str(file_path),
                    'supported_formats': list(cls.SUPPORTED_FORMATS.keys())
                }
            )
        
        # Additional MIME type validation
        mime_type, _ = mimetypes.guess_type(str(file_path))
        expected_mime = cls.SUPPORTED_FORMATS[suffix]
        
        if mime_type and not mime_type.startswith('video/'):
            raise ValidationError(f"File is not a video: detected {mime_type}")
        
        return suffix
    
    @classmethod
    def validate_file_size(cls, file_path: Path) -> int:
        """Validate file size constraints"""
        try:
            size_bytes = file_path.stat().st_size
        except OSError as e:
            raise ValidationError(f"Cannot read file size: {e}")
        
        size_gb = size_bytes / (1024**3)
        size_kb = size_bytes / 1024
        
        if size_kb < cls.MIN_FILE_SIZE_KB:
            raise ValidationError(f"File too small: {size_kb:.1f}KB (minimum {cls.MIN_FILE_SIZE_KB}KB)")
        
        if size_gb > cls.MAX_FILE_SIZE_GB:
            raise ValidationError(f"File too large: {size_gb:.1f}GB (maximum {cls.MAX_FILE_SIZE_GB}GB)")
        
        return size_bytes
    
    @classmethod
    def validate_video_integrity(cls, file_path: Path) -> Dict[str, Any]:
        """Validate video file integrity using ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(file_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # Prevent hanging
            )
            
            if result.returncode != 0:
                raise ValidationError(
                    f"Video file appears corrupted or invalid",
                    context={
                        'file': str(file_path),
                        'ffprobe_error': result.stderr
                    }
                )
            
            import json
            metadata = json.loads(result.stdout)
            
            # Validate video streams
            video_streams = [s for s in metadata.get('streams', []) if s.get('codec_type') == 'video']
            if not video_streams:
                raise ValidationError("No video streams found in file")
            
            # Check duration
            duration = float(metadata.get('format', {}).get('duration', 0))
            if duration <= 0:
                raise ValidationError("Invalid or zero duration video")
            
            if duration > cls.MAX_DURATION_HOURS * 3600:
                raise ValidationError(f"Video too long: {duration/3600:.1f}h (max {cls.MAX_DURATION_HOURS}h)")
            
            return {
                'duration': duration,
                'video_streams': len(video_streams),
                'audio_streams': len([s for s in metadata.get('streams', []) if s.get('codec_type') == 'audio']),
                'format': metadata.get('format', {}),
                'streams': metadata.get('streams', [])
            }
            
        except subprocess.TimeoutExpired:
            raise ValidationError("Video validation timed out - file may be corrupted")
        except json.JSONDecodeError:
            raise ValidationError("Unable to parse video metadata")
        except Exception as e:
            raise ValidationError(f"Video validation failed: {str(e)}")
    
    @classmethod
    def validate_video_file(cls, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Complete video file validation"""
        path = cls.validate_file_path(file_path)
        file_format = cls.validate_file_format(path)
        file_size = cls.validate_file_size(path)
        video_info = cls.validate_video_integrity(path)
        
        return {
            'path': str(path),
            'format': file_format,
            'size_bytes': file_size,
            'size_gb': file_size / (1024**3),
            'duration': video_info['duration'],
            'valid': True,
            'metadata': video_info
        }


class LanguageValidator:
    """Language code validation"""
    
    SUPPORTED_LANGUAGES = {
        # Core mandatory languages
        'eng': 'English',
        'hin': 'Hindi', 
        'ben': 'Bengali',
        
        # Optional Indian languages
        'tel': 'Telugu',
        'mar': 'Marathi',
        'tam': 'Tamil',
        'guj': 'Gujarati',
        'kan': 'Kannada',
        'mal': 'Malayalam',
        'pun': 'Punjabi',
        'ori': 'Odia',
        'asm': 'Assamese',
        'urd': 'Urdu',
        'san': 'Sanskrit',
        'kok': 'Konkani',
        'nep': 'Nepali',
        'sit': 'Sinhala',
        'mai': 'Maithili',
        'bho': 'Bhojpuri',
        'raj': 'Rajasthani',
        'mag': 'Magahi'
    }
    
    @classmethod
    def validate_language_codes(cls, languages: List[str]) -> List[str]:
        """Validate and normalize language codes"""
        if not languages:
            raise ValidationError("At least one language must be specified")
        
        if len(languages) > 10:  # Production limit for Indian languages
            raise ValidationError("Too many languages specified (max 10)")
        
        validated = []
        for lang in languages:
            if not isinstance(lang, str):
                raise ValidationError(f"Language code must be string: {lang}")
            
            lang = lang.lower().strip()
            if len(lang) != 3:
                raise ValidationError(f"Language code must be 3 characters: {lang}")
            
            if not re.match(r'^[a-z]{3}$', lang):
                raise ValidationError(f"Invalid language code format: {lang}")
            
            if lang not in cls.SUPPORTED_LANGUAGES:
                raise ValidationError(
                    f"Unsupported language: {lang}",
                    context={'supported': list(cls.SUPPORTED_LANGUAGES.keys())}
                )
            
            if lang not in validated:
                validated.append(lang)
        
        return validated
    
    @classmethod
    def get_core_languages(cls) -> Dict[str, str]:
        """Get core mandatory languages"""
        return {
            'eng': 'English',
            'hin': 'Hindi',
            'ben': 'Bengali'
        }
    
    @classmethod
    def get_optional_indian_languages(cls) -> Dict[str, str]:
        """Get optional Indian languages"""
        return {
            'tel': 'Telugu',
            'mar': 'Marathi',
            'tam': 'Tamil',
            'guj': 'Gujarati',
            'kan': 'Kannada',
            'mal': 'Malayalam',
            'pun': 'Punjabi',
            'ori': 'Odia',
            'asm': 'Assamese',
            'urd': 'Urdu',
            'san': 'Sanskrit',
            'kok': 'Konkani',
            'nep': 'Nepali',
            'sit': 'Sinhala',
            'mai': 'Maithili',
            'bho': 'Bhojpuri',
            'raj': 'Rajasthani',
            'mag': 'Magahi'
        }
    
    @classmethod
    def get_all_indian_languages(cls) -> Dict[str, str]:
        """Get all Indian languages (core + optional)"""
        indian_languages = {'hin': 'Hindi', 'ben': 'Bengali'}
        indian_languages.update(cls.get_optional_indian_languages())
        return indian_languages
    
    @classmethod
    def is_core_language(cls, lang_code: str) -> bool:
        """Check if language code is a core mandatory language"""
        return lang_code.lower() in cls.get_core_languages()
    
    @classmethod
    def is_indian_language(cls, lang_code: str) -> bool:
        """Check if language code is an Indian language"""
        return lang_code.lower() in cls.get_all_indian_languages()


class ConfigValidator:
    """Configuration validation"""
    
    REQUIRED_CONFIG_KEYS = {
        'gcp.project_id': str,
        'gcp.location': str,
        'gcp.auth_method': str,
        'app.output_dir': str,
        'app.temp_dir': str
    }
    
    VALID_AUTH_METHODS = ['service_account', 'adc']
    VALID_GCP_LOCATIONS = [
        'us-central1', 'us-east1', 'us-west1', 'us-west2',
        'europe-west1', 'europe-west2', 'europe-west3',
        'asia-southeast1', 'asia-northeast1'
    ]
    
    @classmethod
    def validate_configuration(cls, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive configuration validation"""
        errors = []
        
        # Check required keys
        for key, expected_type in cls.REQUIRED_CONFIG_KEYS.items():
            value = cls._get_nested_value(config_dict, key)
            if value is None:
                errors.append(f"Missing required configuration: {key}")
            elif not isinstance(value, expected_type):
                errors.append(f"Invalid type for {key}: expected {expected_type.__name__}, got {type(value).__name__}")
        
        # Validate specific values
        auth_method = cls._get_nested_value(config_dict, 'gcp.auth_method')
        if auth_method and auth_method not in cls.VALID_AUTH_METHODS:
            errors.append(f"Invalid auth_method: {auth_method} (valid: {cls.VALID_AUTH_METHODS})")
        
        location = cls._get_nested_value(config_dict, 'gcp.location')  
        if location and location not in cls.VALID_GCP_LOCATIONS:
            errors.append(f"Invalid GCP location: {location} (valid: {cls.VALID_GCP_LOCATIONS})")
        
        # Validate service account file if required
        if auth_method == 'service_account':
            sa_path = cls._get_nested_value(config_dict, 'gcp.service_account_path')
            if sa_path and not Path(sa_path).exists():
                errors.append(f"Service account file not found: {sa_path}")
        
        # Validate directories
        for dir_key in ['app.output_dir', 'app.temp_dir', 'app.jobs_dir', 'app.logs_dir']:
            dir_path = cls._get_nested_value(config_dict, dir_key)
            if dir_path:
                try:
                    Path(dir_path).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create directory {dir_key}: {e}")
        
        if errors:
            raise ConfigurationError(
                "Configuration validation failed",
                context={'errors': errors}
            )
        
        return config_dict
    
    @staticmethod
    def _get_nested_value(config_dict: Dict[str, Any], key: str) -> Any:
        """Get nested configuration value using dot notation"""
        keys = key.split('.')
        value = config_dict
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        return value


class SystemValidator:
    """System requirements and dependencies validation"""
    
    REQUIRED_COMMANDS = ['ffmpeg', 'ffprobe']
    MIN_DISK_SPACE_GB = 10
    MIN_MEMORY_MB = 2048
    
    @classmethod
    def validate_system_requirements(cls) -> Dict[str, Any]:
        """Validate system has required dependencies and resources"""
        results = {
            'commands': {},
            'disk_space': {},
            'memory': {},
            'valid': True,
            'errors': []
        }
        
        # Check required commands
        for cmd in cls.REQUIRED_COMMANDS:
            try:
                result = subprocess.run(
                    [cmd, '-version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                results['commands'][cmd] = {
                    'available': result.returncode == 0,
                    'version': result.stdout.split('\n')[0] if result.returncode == 0 else None
                }
                if result.returncode != 0:
                    results['errors'].append(f"Required command not found: {cmd}")
                    results['valid'] = False
            except (subprocess.TimeoutExpired, FileNotFoundError):
                results['commands'][cmd] = {'available': False, 'version': None}
                results['errors'].append(f"Required command not found: {cmd}")
                results['valid'] = False
        
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage(Path.cwd())
            free_gb = free / (1024**3)
            results['disk_space'] = {
                'free_gb': free_gb,
                'total_gb': total / (1024**3),
                'sufficient': free_gb >= cls.MIN_DISK_SPACE_GB
            }
            if free_gb < cls.MIN_DISK_SPACE_GB:
                results['errors'].append(f"Insufficient disk space: {free_gb:.1f}GB (minimum {cls.MIN_DISK_SPACE_GB}GB)")
                results['valid'] = False
        except Exception as e:
            results['errors'].append(f"Cannot check disk space: {e}")
            results['valid'] = False
        
        # Check memory (approximate)
        try:
            import psutil
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024**2)
            results['memory'] = {
                'available_mb': available_mb,
                'total_mb': memory.total / (1024**2),
                'sufficient': available_mb >= cls.MIN_MEMORY_MB
            }
            if available_mb < cls.MIN_MEMORY_MB:
                results['errors'].append(f"Insufficient memory: {available_mb:.0f}MB (minimum {cls.MIN_MEMORY_MB}MB)")
                results['valid'] = False
        except ImportError:
            # psutil not available, skip memory check
            results['memory'] = {'available': False, 'reason': 'psutil not installed'}
        except Exception as e:
            results['errors'].append(f"Cannot check memory: {e}")
            results['valid'] = False
        
        return results