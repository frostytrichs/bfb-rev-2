#!/usr/bin/env python3
"""
Configuration module for the Lemmy Bot.
Handles loading and validating configuration from various sources.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages bot configuration from files and environment variables.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file (optional)
        """
        self.config: Dict[str, Any] = {}
        self.config_path = config_path
        
        # Load environment variables from .env file if it exists
        load_dotenv()
        
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file and environment variables.
        
        Returns:
            Dict containing the merged configuration
        """
        # Start with empty config
        self.config = {}
        
        # Load from config file if specified
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading config file: {e}")
        
        # Override with environment variables
        env_config = self._load_from_env()
        self.config.update(env_config)
        
        # Validate the configuration
        self._validate_config()
        
        return self.config
    
    def _load_from_env(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.
        
        Returns:
            Dict containing configuration from environment variables
        """
        env_config = {}
        
        # Map environment variables to config keys
        env_mappings = {
            "LEMMY_INSTANCE": "instance",
            "LEMMY_USERNAME": "username",
            "LEMMY_PASSWORD": "password",
            "LEMMY_BOT_LOG_LEVEL": "log_level",
        }
        
        for env_var, config_key in env_mappings.items():
            if env_var in os.environ:
                env_config[config_key] = os.environ[env_var]
                
        return env_config
    
    def _validate_config(self):
        """
        Validate that the configuration has all required fields.
        Raises ValueError if configuration is invalid.
        """
        required_fields = ["instance", "username", "password"]
        
        for field in required_fields:
            if field not in self.config:
                logger.error(f"Missing required configuration field: {field}")
                raise ValueError(f"Missing required configuration field: {field}")
        
        logger.info("Configuration validated successfully")
        
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            Dict containing the current configuration
        """
        return self.config


def create_default_config(config_path: str):
    """
    Create a default configuration file if it doesn't exist.
    
    Args:
        config_path: Path where the configuration file should be created
    """
    if os.path.exists(config_path):
        logger.warning(f"Configuration file already exists at {config_path}")
        return
    
    default_config = {
        "instance": "https://lemmy.world",
        "username": "your_username",
        "password": "your_password",
        "log_level": "INFO",
        "features": {
            "auto_post": False,
            "auto_reply": False
        }
    }
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        
        logger.info(f"Created default configuration at {config_path}")
    except Exception as e:
        logger.error(f"Error creating default configuration: {e}")