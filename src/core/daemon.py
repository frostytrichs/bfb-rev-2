#!/usr/bin/env python3
"""
Daemon implementation for BlueFlagBot.
Based on a simple daemon implementation that doesn't require external libraries.
"""

import os
import sys
import time
import atexit
import signal
import logging
from pathlib import Path


class Daemon:
    """
    A generic daemon class.
    
    Usage: subclass the Daemon class and override the run() method.
    """
    
    def __init__(self, pid_file: str):
        """
        Initialize the daemon with a PID file path.
        
        Args:
            pid_file: Path to the PID file
        """
        self.pid_file = pid_file
        self.logger = logging.getLogger(__name__)
    
    def daemonize(self):
        """
        Daemonize the process.
        
        This method performs the standard double-fork magic to detach from the
        controlling terminal and run in the background.
        """
        try:
            # First fork
            pid = os.fork()
            if pid > 0:
                # Exit first parent
                sys.exit(0)
        except OSError as e:
            self.logger.error(f"Fork #1 failed: {e}")
            sys.exit(1)
        
        # Decouple from parent environment
        os.chdir('/')
        os.setsid()
        os.umask(0)
        
        try:
            # Second fork
            pid = os.fork()
            if pid > 0:
                # Exit from second parent
                sys.exit(0)
        except OSError as e:
            self.logger.error(f"Fork #2 failed: {e}")
            sys.exit(1)
        
        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')
        
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        
        # Write PID file
        atexit.register(self.delete_pid)
        pid = str(os.getpid())
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.pid_file), exist_ok=True)
        
        with open(self.pid_file, 'w+') as f:
            f.write(f"{pid}\n")
    
    def delete_pid(self):
        """
        Delete the PID file.
        """
        if os.path.isfile(self.pid_file):
            os.remove(self.pid_file)
    
    def get_pid(self):
        """
        Get the PID from the PID file.
        
        Returns:
            The PID as an integer, or None if the PID file doesn't exist or is invalid
        """
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            return pid
        except (IOError, ValueError):
            return None
    
    def is_running(self):
        """
        Check if the daemon is running.
        
        Returns:
            True if the daemon is running, False otherwise
        """
        pid = self.get_pid()
        if pid is None:
            return False
        
        try:
            # Check if the process exists
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    
    def start(self):
        """
        Start the daemon.
        """
        # Check if the daemon is already running
        if self.is_running():
            pid = self.get_pid()
            message = f"Daemon already running with PID {pid}"
            print(message)
            self.logger.warning(message)
            sys.exit(1)
        
        # Start the daemon
        print("Starting daemon...")
        self.daemonize()
        self.run()
    
    def stop(self):
        """
        Stop the daemon.
        """
        # Get the PID from the PID file
        pid = self.get_pid()
        if not pid:
            message = "Daemon not running"
            print(message)
            self.logger.warning(message)
            return
        
        # Try to kill the daemon process
        try:
            print(f"Stopping daemon (PID {pid})...")
            os.kill(pid, signal.SIGTERM)
            
            # Wait for the process to terminate
            for _ in range(10):
                if not self.is_running():
                    break
                time.sleep(0.5)
            else:
                # Force kill if it didn't terminate
                print("Daemon did not terminate gracefully, forcing...")
                os.kill(pid, signal.SIGKILL)
            
            # Remove the PID file
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
            
            print("Daemon stopped")
        except OSError as e:
            if "No such process" in str(e):
                # Process not found, but PID file exists
                if os.path.exists(self.pid_file):
                    os.remove(self.pid_file)
                print("Daemon not running (stale PID file removed)")
            else:
                print(f"Error stopping daemon: {e}")
                self.logger.error(f"Error stopping daemon: {e}")
                sys.exit(1)
    
    def restart(self):
        """
        Restart the daemon.
        """
        self.stop()
        time.sleep(1)  # Give it a moment to fully stop
        self.start()
    
    def status(self):
        """
        Check the status of the daemon.
        """
        if self.is_running():
            pid = self.get_pid()
            print(f"Daemon is running with PID {pid}")
        else:
            print("Daemon is not running")
    
    def run(self):
        """
        The main method to be overridden by subclasses.
        
        This method will be called after the process has been daemonized.
        """
        raise NotImplementedError("You must override this method")