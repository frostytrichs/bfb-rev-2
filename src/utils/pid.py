#!/usr/bin/env python3
"""
PID file management utilities for BlueFlagBot.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PIDFile:
    """
    PID file management.
    """
    
    def __init__(self, pid_file: str):
        """
        Initialize the PID file manager.
        
        Args:
            pid_file: Path to the PID file
        """
        self.pid_file = pid_file
    
    def create(self):
        """
        Create a PID file with the current process ID.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            pid_dir = os.path.dirname(self.pid_file)
            if pid_dir:
                os.makedirs(pid_dir, exist_ok=True)
            
            # Write PID to file
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            
            logger.debug(f"Created PID file at {self.pid_file}")
            return True
        except Exception as e:
            logger.error(f"Error creating PID file: {e}")
            return False
    
    def remove(self):
        """
        Remove the PID file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
                logger.debug(f"Removed PID file at {self.pid_file}")
            return True
        except Exception as e:
            logger.error(f"Error removing PID file: {e}")
            return False
    
    def read(self):
        """
        Read the PID from the PID file.
        
        Returns:
            The PID as an integer, or None if the PID file doesn't exist or is invalid
        """
        try:
            if os.path.exists(self.pid_file):
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                return pid
            return None
        except (IOError, ValueError) as e:
            logger.error(f"Error reading PID file: {e}")
            return None
    
    def is_running(self):
        """
        Check if the process in the PID file is running.
        
        Returns:
            True if the process is running, False otherwise
        """
        pid = self.read()
        if pid is None:
            return False
        
        try:
            # Check if the process exists by sending signal 0
            os.kill(pid, 0)
            return True
        except OSError:
            # Process doesn't exist
            return False