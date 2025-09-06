#!/usr/bin/env python3
"""
Tests for the configuration module.
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
from src.config import ConfigManager, create_default_config


def test_create_default_config():
    """Test creating a default configuration file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = os.path.join(temp_dir, "config.json")
        create_default_config(config_path)
        
        # Check that the file was created
        assert os.path.exists(config_path)
        
        # Check that the file contains valid JSON
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Check that the required fields are present
        assert "instance" in config
        assert "username" in config
        assert "password" in config


def test_load_config_from_file():
    """Test loading configuration from a file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = os.path.join(temp_dir, "config.json")
        
        # Create a test configuration
        test_config = {
            "instance": "https://test.instance",
            "username": "test_user",
            "password": "test_pass",
            "log_level": "DEBUG"
        }
        
        with open(config_path, 'w') as f:
            json.dump(test_config, f)
        
        # Load the configuration
        config_manager = ConfigManager(config_path)
        loaded_config = config_manager.load_config()
        
        # Check that the loaded configuration matches the test configuration
        assert loaded_config["instance"] == test_config["instance"]
        assert loaded_config["username"] == test_config["username"]
        assert loaded_config["password"] == test_config["password"]
        assert loaded_config["log_level"] == test_config["log_level"]


def test_load_config_from_env(monkeypatch):
    """Test loading configuration from environment variables."""
    # Set environment variables
    monkeypatch.setenv("LEMMY_INSTANCE", "https://env.instance")
    monkeypatch.setenv("LEMMY_USERNAME", "env_user")
    monkeypatch.setenv("LEMMY_PASSWORD", "env_pass")
    
    # Load the configuration
    config_manager = ConfigManager()
    loaded_config = config_manager.load_config()
    
    # Check that the loaded configuration matches the environment variables
    assert loaded_config["instance"] == "https://env.instance"
    assert loaded_config["username"] == "env_user"
    assert loaded_config["password"] == "env_pass"


def test_env_overrides_file(monkeypatch):
    """Test that environment variables override file configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = os.path.join(temp_dir, "config.json")
        
        # Create a test configuration
        test_config = {
            "instance": "https://test.instance",
            "username": "test_user",
            "password": "test_pass",
            "log_level": "DEBUG"
        }
        
        with open(config_path, 'w') as f:
            json.dump(test_config, f)
        
        # Set environment variables
        monkeypatch.setenv("LEMMY_INSTANCE", "https://env.instance")
        
        # Load the configuration
        config_manager = ConfigManager(config_path)
        loaded_config = config_manager.load_config()
        
        # Check that the environment variable overrides the file configuration
        assert loaded_config["instance"] == "https://env.instance"
        assert loaded_config["username"] == test_config["username"]
        assert loaded_config["password"] == test_config["password"]


def test_validate_config():
    """Test configuration validation."""
    # Test with missing required fields
    config_manager = ConfigManager()
    config_manager.config = {
        "instance": "https://test.instance",
        # Missing username and password
    }
    
    # Validation should raise an error
    with pytest.raises(ValueError):
        config_manager._validate_config()
    
    # Test with all required fields
    config_manager.config = {
        "instance": "https://test.instance",
        "username": "test_user",
        "password": "test_pass"
    }
    
    # Validation should not raise an error
    config_manager._validate_config()