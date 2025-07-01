"""
Configuration Manager
Handles loading and accessing configuration and prompts
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, List

# Production imports
from .exceptions import ConfigurationError, ValidationError
from .validators import ConfigValidator, SystemValidator
from .logger import get_logger

logger = get_logger(__name__)

class ConfigManager:
    def __init__(self, config_path: str = "config/config.yaml", validate: bool = True):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.prompts = self._load_prompts()
        
        if validate:
            self._validate_configuration()
            self._validate_system_requirements()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load main configuration file"""
        if not self.config_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {self.config_path}",
                context={'config_path': str(self.config_path)}
            )
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    raise ConfigurationError("Configuration file is empty")
                
                config = yaml.safe_load(content)
                if config is None:
                    raise ConfigurationError("Configuration file contains no valid data")
                    
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML in configuration file: {e}",
                context={'config_path': str(self.config_path), 'yaml_error': str(e)}
            )
        except PermissionError:
            raise ConfigurationError(
                f"Permission denied reading configuration file: {self.config_path}",
                context={'config_path': str(self.config_path)}
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration: {e}",
                context={'config_path': str(self.config_path), 'error': str(e)}
            )
            
        # Load local overrides if they exist
        local_config_path = self.config_path.parent / "config.local.yaml"
        if local_config_path.exists():
            with open(local_config_path, 'r', encoding='utf-8') as f:
                local_config = yaml.safe_load(f)
                config = self._deep_merge(config, local_config)
                
        return config
        
    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load all prompt files"""
        prompts = {}
        prompt_dir = Path("config/prompts")
        
        if prompt_dir.exists():
            for prompt_file in prompt_dir.glob("*.yaml"):
                lang_code = prompt_file.stem
                try:
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        prompts[lang_code] = yaml.safe_load(f)
                except Exception as e:
                    print(f"Warning: Failed to load prompt file {prompt_file}: {e}")
                    
        return prompts
        
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def get(self, key: str, default: Optional[Any] = None, required: bool = False) -> Any:
        """Get configuration value using dot notation with validation"""
        if not key:
            raise ValidationError("Configuration key cannot be empty")
        
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                if required:
                    raise ConfigurationError(
                        f"Required configuration key not found: {key}",
                        context={'key': key, 'available_keys': list(self.config.keys())}
                    )
                return default
                
        return value
        
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
        
    def get_prompt(self, language: str, method: Optional[str] = None) -> str:
        """Get prompt for a specific language and method"""
        if language == "hin" and method:
            prompt_key = f"hin_{method}"
        else:
            prompt_key = language
            
        if prompt_key in self.prompts:
            return self.prompts[prompt_key].get('prompt', '')
            
        return ""
    
    def _validate_configuration(self):
        """Validate the loaded configuration"""
        try:
            ConfigValidator.validate_configuration(self.config)
            logger.info("Configuration validation passed")
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
    
    def _validate_system_requirements(self):
        """Validate system requirements"""
        try:
            result = SystemValidator.validate_system_requirements()
            if not result['valid']:
                raise ConfigurationError(
                    "System requirements not met",
                    context={'errors': result['errors'], 'details': result}
                )
            logger.info("System requirements validation passed")
        except Exception as e:
            logger.error(f"System validation failed: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on configuration"""
        try:
            health = {
                'config_file_exists': self.config_path.exists(),
                'config_loaded': bool(self.config),
                'prompts_loaded': bool(self.prompts),
                'required_keys_present': True,
                'errors': []
            }
            
            # Check required keys
            required_keys = [
                'gcp.project_id',
                'gcp.location',
                'app.output_dir',
                'app.temp_dir'
            ]
            
            for key in required_keys:
                if self.get(key) is None:
                    health['required_keys_present'] = False
                    health['errors'].append(f"Missing required key: {key}")
            
            # Check prompts
            if not self.prompts:
                health['errors'].append("No prompts loaded")
            
            health['status'] = 'healthy' if not health['errors'] else 'unhealthy'
            return health
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
        
    def get_sdh_prompt(self, language: str) -> str:
        """Get SDH prompt for a specific language"""
        prompt_key = f"{language}_sdh"
        
        if prompt_key in self.prompts:
            return self.prompts[prompt_key].get('prompt', '')
            
        # Fallback to generic SDH prompt
        return self.prompts.get('eng_sdh', {}).get('prompt', '')
        
    def get_safety_settings(self) -> List[Dict[str, str]]:
        """Get Vertex AI safety settings"""
        return self.get('vertex_ai.safety_settings', [])
        
    def get_available_languages(self) -> Dict[str, Dict[str, Any]]:
        """Get available subtitle languages"""
        return self.get('languages.subtitles.available', {})
        
    def get_supported_video_formats(self) -> List[str]:
        """Get supported video formats"""
        return self.get('system.supported_video_formats', ['mp4', 'avi', 'mkv', 'mov', 'webm'])
        
    def save_config(self) -> None:
        """Save current configuration to file"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
