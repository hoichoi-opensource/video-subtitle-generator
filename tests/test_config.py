import pytest
from pathlib import Path
from src.config import Config

def test_config_loading():
    """Test configuration loading from file."""
    config = Config("config.yaml.example")
    assert config.get("gcp.project_id") == "your-project-id"
    assert config.get("subtitles.supported_languages") == ["en", "hi", "bn"]

def test_config_defaults():
    """Test default value retrieval."""
    config = Config("config.yaml.example")
    assert config.get("nonexistent.key", "default") == "default"
