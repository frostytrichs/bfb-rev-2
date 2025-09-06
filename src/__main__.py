#!/usr/bin/env python3
"""
Main entry point for the Lemmy Bot.
This allows the bot to be run as a module: python -m src
"""

import os
import sys
import argparse
import logging
from typing import Dict, Any

from .bot import LemmyBot
from .config import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Lemmy Bot")
    parser.add_argument(
        "--config", 
        "-c", 
        type=str, 
        help="Path to configuration file"
    )
    parser.add_argument(
        "--log-level", 
        "-l", 
        type=str, 
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level"
    )
    
    return parser.parse_args()


def setup_logging(log_level: str):
    """
    Set up logging with the specified level.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    logging.getLogger().setLevel(numeric_level)
    logger.info(f"Log level set to {log_level}")


def main():
    """
    Main entry point for the bot.
    """
    # Parse command line arguments
    args = parse_arguments()
    
    try:
        # Load configuration
        config_manager = ConfigManager(args.config)
        config = config_manager.load_config()
        
        # Set up logging
        log_level = args.log_level or config.get("log_level", "INFO")
        setup_logging(log_level)
        
        # Create and run the bot
        bot = LemmyBot(config)
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()