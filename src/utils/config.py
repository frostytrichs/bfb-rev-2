#!/usr/bin/env python3
"""
Configuration utilities for BlueFlagBot.
"""

import os
import json
import logging
import configparser
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages bot configuration from INI files, JSON files, and environment variables.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file (optional)
        """
        self.config: Dict[str, Any] = {}
        self.config_path = config_path
        self.parser = configparser.ConfigParser()
    
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
                # Determine file type based on extension
                if self.config_path.endswith('.ini'):
                    self._load_from_ini()
                elif self.config_path.endswith('.json'):
                    self._load_from_json()
                else:
                    logger.warning(f"Unknown config file type: {self.config_path}")
                    
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading config file: {e}")
        
        # Load channel configuration
        self._load_channel_config()
        
        # Load keyword configuration
        self._load_keyword_config()
        
        # Override with environment variables
        env_config = self._load_from_env()
        self._deep_update(self.config, env_config)
        
        # Validate the configuration
        self._validate_config()
        
        return self.config
    
    def _load_from_ini(self):
        """
        Load configuration from INI file.
        """
        self.parser.read(self.config_path)
        
        # Convert to dictionary
        for section in self.parser.sections():
            self.config[section] = {}
            for key, value in self.parser.items(section):
                # Try to convert values to appropriate types
                if value.lower() in ('true', 'yes', 'on', '1'):
                    self.config[section][key] = True
                elif value.lower() in ('false', 'no', 'off', '0'):
                    self.config[section][key] = False
                elif value.isdigit():
                    self.config[section][key] = int(value)
                elif value.replace('.', '', 1).isdigit() and value.count('.') == 1:
                    self.config[section][key] = float(value)
                else:
                    self.config[section][key] = value
        
        # Also include DEFAULT section
        if 'DEFAULT' not in self.config and self.parser.defaults():
            self.config['DEFAULT'] = {}
            for key, value in self.parser.defaults().items():
                # Try to convert values to appropriate types
                if value.lower() in ('true', 'yes', 'on', '1'):
                    self.config['DEFAULT'][key] = True
                elif value.lower() in ('false', 'no', 'off', '0'):
                    self.config['DEFAULT'][key] = False
                elif value.isdigit():
                    self.config['DEFAULT'][key] = int(value)
                elif value.replace('.', '', 1).isdigit() and value.count('.') == 1:
                    self.config['DEFAULT'][key] = float(value)
                else:
                    self.config['DEFAULT'][key] = value
    
    def _load_from_json(self):
        """
        Load configuration from JSON file.
        """
        with open(self.config_path, 'r') as f:
            file_config = json.load(f)
            self.config.update(file_config)
    
    def _load_channel_config(self):
        """
        Load channel configuration from channels.json.
        """
        # Determine the base directory
        if self.config_path:
            base_dir = Path(self.config_path).parent
        else:
            base_dir = Path.cwd()
        
        channel_path = base_dir / "channels.json"
        
        if channel_path.exists():
            try:
                with open(channel_path, 'r') as f:
                    channels = json.load(f)
                
                self.config['channels'] = channels
                logger.info(f"Loaded {len(channels)} channels from {channel_path}")
            except Exception as e:
                logger.error(f"Error loading channel configuration: {e}")
    
    def _load_keyword_config(self):
        """
        Load keyword configuration from keywords directory.
        """
        # Determine the base directory
        if self.config_path:
            base_dir = Path(self.config_path).parent
        else:
            base_dir = Path.cwd()
        
        keywords_dir = base_dir / "keywords"
        
        if keywords_dir.exists() and keywords_dir.is_dir():
            keywords = {}
            
            # Load all JSON files in the keywords directory
            for file_path in keywords_dir.glob("*.json"):
                try:
                    language = file_path.stem  # Use filename without extension as language code
                    
                    with open(file_path, 'r') as f:
                        keywords[language] = json.load(f)
                    
                    logger.info(f"Loaded keywords for language '{language}' from {file_path}")
                except Exception as e:
                    logger.error(f"Error loading keyword file {file_path}: {e}")
            
            if keywords:
                self.config['keywords'] = keywords
    
    def _load_from_env(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.
        
        Returns:
            Dict containing configuration from environment variables
        """
        env_config = {}
        
        # Map environment variables to config keys
        env_mappings = {
            # General settings
            "LEMMY_INSTANCE": ("lemmy", "instance"),
            "LEMMY_USERNAME": ("lemmy", "username"),
            "LEMMY_PASSWORD": ("lemmy", "password"),
            "LEMMY_COMMUNITY": ("lemmy", "community"),
            
            # Logging settings
            "LOG_LEVEL": ("logging", "level"),
            "LOG_FILE": ("logging", "file"),
            
            # Scan settings
            "SCAN_INTERVAL": ("scan", "interval_minutes"),
            "MAX_POSTS_PER_RUN": ("scan", "max_posts_per_run"),
            "MAX_POSTS_PER_DAY": ("scan", "max_posts_per_day"),
            
            # YouTube API settings
            "YOUTUBE_API_QUOTA": ("youtube", "daily_quota"),
            "YOUTUBE_API_KEY": ("youtube", "api_key"),
        }
        
        for env_var, config_path in env_mappings.items():
            if env_var in os.environ:
                # Create nested dictionaries as needed
                current = env_config
                for part in config_path[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                # Set the value, converting to appropriate type if possible
                value = os.environ[env_var]
                
                # Try to convert to appropriate type
                if value.lower() in ('true', 'yes', 'on', '1'):
                    current[config_path[-1]] = True
                elif value.lower() in ('false', 'no', 'off', '0'):
                    current[config_path[-1]] = False
                elif value.isdigit():
                    current[config_path[-1]] = int(value)
                elif value.replace('.', '', 1).isdigit() and value.count('.') == 1:
                    current[config_path[-1]] = float(value)
                else:
                    current[config_path[-1]] = value
        
        return env_config
    
    def _deep_update(self, target: Dict, source: Dict):
        """
        Deep update a nested dictionary.
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with updates
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def _validate_config(self):
        """
        Validate that the configuration has all required fields.
        Raises ValueError if configuration is invalid.
        """
        # Check for Lemmy configuration
        if 'lemmy' not in self.config:
            logger.error("Missing Lemmy configuration section")
            raise ValueError("Missing Lemmy configuration section")
        
        lemmy_config = self.config['lemmy']
        required_lemmy_fields = ["instance", "username", "password", "community"]
        
        for field in required_lemmy_fields:
            if field not in lemmy_config:
                logger.error(f"Missing required Lemmy configuration field: {field}")
                raise ValueError(f"Missing required Lemmy configuration field: {field}")
        
        # Check for YouTube configuration
        if 'youtube' not in self.config:
            logger.error("Missing YouTube configuration section")
            raise ValueError("Missing YouTube configuration section")
        
        # Check for channels configuration
        if 'channels' not in self.config or not self.config['channels']:
            logger.warning("No channels configured")
        
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
    
    # Determine file type based on extension
    if config_path.endswith('.ini'):
        create_default_ini_config(config_path)
    elif config_path.endswith('.json'):
        create_default_json_config(config_path)
    else:
        logger.warning(f"Unknown config file type: {config_path}")
        # Default to INI
        create_default_ini_config(config_path)


def create_default_ini_config(config_path: str):
    """
    Create a default INI configuration file.
    
    Args:
        config_path: Path where the configuration file should be created
    """
    config = configparser.ConfigParser()
    
    # General settings
    config['general'] = {
        'test_mode': 'false',
        'debug': 'false'
    }
    
    # Lemmy settings
    config['lemmy'] = {
        'instance': 'https://lemmy.world',
        'username': 'your_username',
        'password': 'your_password',
        'community': 'your_community'
    }
    
    # YouTube settings
    config['youtube'] = {
        'daily_quota': '10000',
        'quota_per_run': '300',
        'oauth_credentials_file': 'credentials/youtube_oauth.json',
        'token_file': 'credentials/youtube_token.json'
    }
    
    # Scan settings
    config['scan'] = {
        'interval_minutes': '30',
        'max_posts_per_run': '5',
        'max_posts_per_day': '100',
        'max_posts_per_hour': '20',
        'time_between_posts_seconds': '60',
        'video_max_age_hours': '24'
    }
    
    # Content filtering
    config['filtering'] = {
        'min_quality_threshold': '65',
        'livestream_quality_threshold': '60',
        'duplicate_check_hours': '48',
        'min_video_length_seconds': '60',
        'never_cache_livestreams': 'true'
    }
    
    # Logging settings
    config['logging'] = {
        'level': 'INFO',
        'file': 'logs/blueflagbot.log',
        'max_size_mb': '10',
        'backup_count': '5'
    }
    
    # Error handling
    config['error_handling'] = {
        'max_retries': '3',
        'retry_delay_seconds': '60',
        'backoff_factor': '2'
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
    
    # Write the configuration file
    with open(config_path, 'w') as f:
        config.write(f)
    
    logger.info(f"Created default INI configuration at {config_path}")


def create_default_json_config(config_path: str):
    """
    Create a default JSON configuration file.
    
    Args:
        config_path: Path where the configuration file should be created
    """
    default_config = {
        "general": {
            "test_mode": False,
            "debug": False
        },
        "lemmy": {
            "instance": "https://lemmy.world",
            "username": "your_username",
            "password": "your_password",
            "community": "your_community"
        },
        "youtube": {
            "daily_quota": 10000,
            "quota_per_run": 300,
            "oauth_credentials_file": "credentials/youtube_oauth.json",
            "token_file": "credentials/youtube_token.json"
        },
        "scan": {
            "interval_minutes": 30,
            "max_posts_per_run": 5,
            "max_posts_per_day": 100,
            "max_posts_per_hour": 20,
            "time_between_posts_seconds": 60,
            "video_max_age_hours": 24
        },
        "filtering": {
            "min_quality_threshold": 65,
            "livestream_quality_threshold": 60,
            "duplicate_check_hours": 48,
            "min_video_length_seconds": 60,
            "never_cache_livestreams": True
        },
        "logging": {
            "level": "INFO",
            "file": "logs/blueflagbot.log",
            "max_size_mb": 10,
            "backup_count": 5
        },
        "error_handling": {
            "max_retries": 3,
            "retry_delay_seconds": 60,
            "backoff_factor": 2
        }
    }
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        
        logger.info(f"Created default JSON configuration at {config_path}")
    except Exception as e:
        logger.error(f"Error creating default configuration: {e}")