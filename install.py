#!/usr/bin/env python3
"""
Installation script for BlueFlagBot.
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path


def check_python_version():
    """
    Check if Python version is 3.6 or higher.
    """
    if sys.version_info < (3, 6):
        print("Error: Python 3.6 or higher is required.")
        sys.exit(1)
    print(f"Python version: {sys.version}")


def create_directories():
    """
    Create necessary directories.
    """
    directories = [
        "data",
        "logs",
        "credentials"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")


def install_dependencies():
    """
    Install required Python packages.
    """
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully.")
    except subprocess.CalledProcessError:
        print("Error: Failed to install dependencies.")
        sys.exit(1)


def setup_youtube_auth():
    """
    Set up YouTube API authentication.
    """
    oauth_file = Path("credentials/youtube_oauth.json")
    token_file = Path("credentials/youtube_token.json")
    
    if not oauth_file.exists():
        print("\n=== YouTube API Setup ===")
        print("You need to set up YouTube API credentials.")
        print("1. Go to https://console.developers.google.com/")
        print("2. Create a new project")
        print("3. Enable the YouTube Data API v3")
        print("4. Create OAuth 2.0 credentials")
        print("5. Download the client_secret.json file")
        print("6. Rename it to youtube_oauth.json")
        print("7. Place it in the credentials directory")
        
        input("\nPress Enter when you have completed these steps...")
        
        if not oauth_file.exists():
            print("Error: youtube_oauth.json not found in credentials directory.")
            return False
    
    print("YouTube API credentials found.")
    return True


def setup_lemmy_auth():
    """
    Set up Lemmy authentication.
    """
    lemmy_auth_file = Path("credentials/lemmy_auth.json")
    
    if not lemmy_auth_file.exists():
        print("\n=== Lemmy API Setup ===")
        
        instance = input("Enter Lemmy instance URL (e.g., https://lemmy.world): ")
        username = input("Enter Lemmy username: ")
        password = input("Enter Lemmy password: ")
        community = input("Enter Lemmy community name: ")
        
        lemmy_auth = {
            "instance": instance,
            "username": username,
            "password": password,
            "community": community
        }
        
        with open(lemmy_auth_file, "w") as f:
            json.dump(lemmy_auth, f, indent=4)
        
        print("Lemmy authentication credentials saved.")
    else:
        print("Lemmy authentication credentials found.")
    
    return True


def update_config():
    """
    Update config.ini with user preferences.
    """
    config_file = Path("config.ini")
    
    if config_file.exists():
        update = input("\nConfig file already exists. Do you want to update it? (y/n): ")
        if update.lower() != "y":
            print("Skipping config update.")
            return
    
    print("\n=== Bot Configuration ===")
    print("Setting up basic configuration...")
    
    # Read existing config if it exists
    import configparser
    config = configparser.ConfigParser()
    if config_file.exists():
        config.read(config_file)
    
    # Update test mode
    test_mode = input("Run in test mode (no actual posts will be made)? (y/n): ")
    if "general" not in config:
        config["general"] = {}
    config["general"]["test_mode"] = "true" if test_mode.lower() == "y" else "false"
    
    # Update scan interval
    scan_interval = input("Enter scan interval in minutes (default: 30): ")
    if not scan_interval:
        scan_interval = "30"
    if "scan" not in config:
        config["scan"] = {}
    config["scan"]["interval_minutes"] = scan_interval
    
    # Update posts per run
    posts_per_run = input("Enter maximum posts per run (default: 5): ")
    if not posts_per_run:
        posts_per_run = "5"
    config["scan"]["max_posts_per_run"] = posts_per_run
    
    # Write updated config
    with open(config_file, "w") as f:
        config.write(f)
    
    print("Configuration updated successfully.")


def main():
    """
    Main installation function.
    """
    parser = argparse.ArgumentParser(description="Install BlueFlagBot")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency installation")
    parser.add_argument("--skip-auth", action="store_true", help="Skip authentication setup")
    args = parser.parse_args()
    
    print("=== BlueFlagBot Installation ===")
    
    # Check Python version
    check_python_version()
    
    # Create directories
    create_directories()
    
    # Install dependencies
    if not args.skip_deps:
        install_dependencies()
    else:
        print("Skipping dependency installation.")
    
    # Set up authentication
    if not args.skip_auth:
        setup_youtube_auth()
        setup_lemmy_auth()
    else:
        print("Skipping authentication setup.")
    
    # Update configuration
    update_config()
    
    print("\n=== Installation Complete ===")
    print("You can now run the bot using:")
    print("  python3 blueflagbot.py start")
    print("\nTo run in test mode (no actual posts):")
    print("  1. Ensure test_mode = true in config.ini")
    print("  2. Run: python3 blueflagbot.py run-once")


if __name__ == "__main__":
    main()