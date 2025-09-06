#!/usr/bin/env python3
"""
Example script demonstrating basic usage of the Lemmy Bot.
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path so we can import the src package
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot import LemmyBot
from src.config import ConfigManager, create_default_config
from src.lemmy_api import LemmyAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def create_example_config():
    """
    Create an example configuration file if it doesn't exist.
    
    Returns:
        Path to the configuration file
    """
    config_dir = Path.home() / ".lemmy-bot"
    config_dir.mkdir(exist_ok=True)
    
    config_path = config_dir / "config.json"
    
    if not config_path.exists():
        create_default_config(str(config_path))
        logger.info(f"Created example configuration at {config_path}")
        logger.info("Please edit this file with your Lemmy credentials before running the bot.")
        sys.exit(0)
        
    return str(config_path)


def main():
    """
    Run a simple example bot.
    """
    # Create or load configuration
    config_path = create_example_config()
    config_manager = ConfigManager(config_path)
    
    try:
        config = config_manager.load_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error(f"Please edit {config_path} with your Lemmy credentials.")
        sys.exit(1)
    
    # Create and run the bot
    bot = LemmyBot(config)
    
    try:
        # Example of direct API usage
        logger.info("Demonstrating direct API usage:")
        
        api = LemmyAPI(config["instance"])
        if api.login(config["username"], config["password"]):
            logger.info("API login successful")
            
            # Get some communities
            communities = api.get_communities(limit=5)
            if communities:
                logger.info(f"Found {len(communities)} communities:")
                for community in communities:
                    name = community.get("community", {}).get("name", "Unknown")
                    title = community.get("community", {}).get("title", "Unknown")
                    logger.info(f"- {name}: {title}")
        
        # Run the main bot
        logger.info("\nStarting the main bot:")
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        bot.stop()
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()