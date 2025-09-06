#!/usr/bin/env python3
"""
BlueFlagBot - A bot that posts auto racing and motorsport videos to Lemmy.
Main entry point with daemon functionality.
"""

import os
import sys
import time
import signal
import argparse
import logging
from pathlib import Path
from typing import Optional

from src.core.bot import BlueFlagBot
from src.core.daemon import Daemon
from src.utils.config import ConfigManager
from src.utils.logging import setup_logging

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

# Default paths
DEFAULT_CONFIG_PATH = BASE_DIR / "config.ini"
DEFAULT_PID_FILE = BASE_DIR / "data" / "blueflagbot.pid"
DEFAULT_LOG_FILE = BASE_DIR / "logs" / "blueflagbot.log"


class BlueFlagBotDaemon(Daemon):
    """
    Daemon implementation for BlueFlagBot.
    """
    
    def __init__(
        self,
        config_path: str,
        pid_file: str,
        log_file: str,
        log_level: str = "INFO"
    ):
        super().__init__(pid_file)
        self.config_path = config_path
        self.log_file = log_file
        self.log_level = log_level
        self.bot: Optional[BlueFlagBot] = None
        self.running = False
        
    def run(self):
        """
        Main daemon process.
        """
        # Set up logging
        setup_logging(self.log_file, self.log_level)
        logger = logging.getLogger(__name__)
        
        try:
            logger.info("Starting BlueFlagBot daemon")
            
            # Load configuration
            config_manager = ConfigManager(self.config_path)
            config = config_manager.load_config()
            
            # Create and run the bot
            self.bot = BlueFlagBot(config)
            self.running = True
            
            # Set up signal handlers
            signal.signal(signal.SIGTERM, self.handle_signal)
            signal.signal(signal.SIGINT, self.handle_signal)
            
            # Run the bot in continuous mode
            self.bot.run_continuous()
            
        except Exception as e:
            logger.error(f"Error in daemon process: {e}", exc_info=True)
            sys.exit(1)
    
    def handle_signal(self, signum, frame):
        """
        Handle termination signals.
        """
        logger = logging.getLogger(__name__)
        logger.info(f"Received signal {signum}, shutting down")
        
        if self.bot:
            self.bot.stop()
        
        self.running = False
        sys.exit(0)


def run_once(config_path: str, log_file: str, log_level: str = "INFO"):
    """
    Run the bot once without starting the daemon.
    """
    # Set up logging
    setup_logging(log_file, log_level)
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Running BlueFlagBot once")
        
        # Load configuration
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        
        # Create and run the bot
        bot = BlueFlagBot(config)
        bot.run_once()
        
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
        sys.exit(1)


def main():
    """
    Main entry point.
    """
    parser = argparse.ArgumentParser(description="BlueFlagBot - Motorsport Video Bot")
    
    # Command argument
    parser.add_argument(
        "command",
        choices=["start", "stop", "restart", "status", "run-once"],
        help="Command to execute"
    )
    
    # Optional arguments
    parser.add_argument(
        "--config", "-c",
        default=str(DEFAULT_CONFIG_PATH),
        help=f"Path to configuration file (default: {DEFAULT_CONFIG_PATH})"
    )
    
    parser.add_argument(
        "--pid-file", "-p",
        default=str(DEFAULT_PID_FILE),
        help=f"Path to PID file (default: {DEFAULT_PID_FILE})"
    )
    
    parser.add_argument(
        "--log-file", "-l",
        default=str(DEFAULT_LOG_FILE),
        help=f"Path to log file (default: {DEFAULT_LOG_FILE})"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Ensure directories exist
    os.makedirs(os.path.dirname(args.pid_file), exist_ok=True)
    os.makedirs(os.path.dirname(args.log_file), exist_ok=True)
    
    # Create daemon instance
    daemon = BlueFlagBotDaemon(
        config_path=args.config,
        pid_file=args.pid_file,
        log_file=args.log_file,
        log_level=args.log_level
    )
    
    # Execute command
    if args.command == "start":
        daemon.start()
    elif args.command == "stop":
        daemon.stop()
    elif args.command == "restart":
        daemon.restart()
    elif args.command == "status":
        daemon.status()
    elif args.command == "run-once":
        run_once(args.config, args.log_file, args.log_level)


if __name__ == "__main__":
    main()