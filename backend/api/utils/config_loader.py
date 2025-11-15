"""
Configuration loader for ROSETTA API.
Loads and validates config.yaml file.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

_config: Optional[Dict[str, Any]] = None


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config.yaml (defaults to backend/api/config.yaml)
    
    Returns:
        Configuration dictionary
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid
    """
    global _config
    
    if config_path is None:
        # Default to config.yaml in same directory as this file
        api_dir = Path(__file__).parent.parent
        config_path = str(api_dir / "config.yaml")
    
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            _config = yaml.safe_load(f)
        
        logger.info(f"Configuration loaded from: {config_path}")
        _validate_config(_config)
        
        return _config
    
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse config file: {e}")
        raise


def get_config() -> Dict[str, Any]:
    """
    Get loaded configuration.
    Loads default config if not already loaded.
    
    Returns:
        Configuration dictionary
    """
    global _config
    
    if _config is None:
        load_config()
    
    return _config  # type: ignore


def _validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration structure.
    
    Args:
        config: Configuration dictionary
    
    Raises:
        ValueError: If required keys are missing
    """
    required_sections = ["server", "upload", "cache", "ocr", "llm", "jobs"]
    
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")
    
    # Validate server config
    if "host" not in config["server"] or "port" not in config["server"]:
        raise ValueError("Server config must include 'host' and 'port'")
    
    # Validate upload limits
    upload = config["upload"]
    if upload.get("max_file_size_mb", 0) <= 0:
        raise ValueError("max_file_size_mb must be positive")
    
    if upload.get("max_pdf_pages", 0) <= 0:
        raise ValueError("max_pdf_pages must be positive")
    
    # Validate LLM model path
    model_path = config["llm"].get("model_path")
    if not model_path:
        raise ValueError("LLM model_path is required")
    
    logger.info("Configuration validation passed")
