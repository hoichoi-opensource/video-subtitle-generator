"""Configuration management module."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional

class Config:
    """Centralized configuration management."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Load configuration from YAML file."""
        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._apply_environment_overrides()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _apply_environment_overrides(self):
        """Override config values with environment variables if present."""
        env_mappings = {
            'GCP_PROJECT_ID': 'gcp.project_id',
            'GCP_LOCATION': 'gcp.location',
            'VERTEX_AI_MODEL': 'vertex_ai.model',
            'GCS_BUCKET': 'storage.bucket_name',
        }
        
        for env_var, config_path in env_mappings.items():
            if env_value := os.getenv(env_var):
                self._set_nested(config_path, env_value)
    
    def _set_nested(self, path: str, value: Any):
        """Set a nested configuration value using dot notation."""
        keys = path.split('.')
        current = self._config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation."""
        keys = path.split('.')
        current = self._config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def get_all(self) -> Dict[str, Any]:
        """Get the entire configuration dictionary."""
        return self._config.copy()
