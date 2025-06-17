"""Configuration management module."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Configuration container."""
    
    google_cloud: Dict[str, Any]
    vertex_ai: Dict[str, Any]
    processing: Dict[str, Any]
    languages: list
    paths: Dict[str, str]
    naming: Dict[str, str]
    stages: Dict[str, Any]
    logging: Dict[str, Any]
    output: Dict[str, Any]
    performance: Dict[str, Any]
    
    def __post_init__(self):
        """Validate and process configuration after initialization."""
        # Ensure all paths exist
        for key, path in self.paths.items():
            Path(path).mkdir(parents=True, exist_ok=True)
        
        # Process environment variable overrides
        self._process_env_overrides()
    
    def _process_env_overrides(self):
        """Override configuration with environment variables."""
        # Google Cloud overrides
        if project_id := os.getenv("GCP_PROJECT_ID"):
            self.google_cloud["project_id"] = project_id
        
        if credentials := os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            self.google_cloud["credentials_path"] = credentials
        
        if bucket := os.getenv("GCS_BUCKET_NAME"):
            self.google_cloud["bucket_name"] = bucket
    
    def get_language_by_code(self, code: str) -> Optional[Dict[str, str]]:
        """Get language configuration by code."""
        for lang in self.languages:
            if lang["code"] == code:
                return lang
        return None
    
    def format_name(self, pattern: str, **kwargs) -> str:
        """Format a naming pattern with given parameters."""
        return self.naming.get(pattern, "").format(**kwargs)


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            config_path = Path("config/config.yaml.example")
    
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)
    
    return Config(**config_data)


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: Optional[str] = None):
    """Reload configuration from file."""
    global _config
    _config = load_config(config_path)