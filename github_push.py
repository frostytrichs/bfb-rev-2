#!/usr/bin/env python3
"""
Script to push code to GitHub repository using PAT.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(f"STDERR: {e.stderr}")
        return None

def push_to_github(repo_path, username, pat, repo_name, branch="main"):
    """Push code to GitHub repository using PAT."""
    os.chdir(repo_path)
    
    # Check if we're in a git repository
    if not Path(repo_path).joinpath(".git").exists():
        print(f"Error: {repo_path} is not a git repository")
        return False
    
    # Set remote URL with PAT
    remote_url = f"https://{username}:{pat}@github.com/{username}/{repo_name}.git"
    result = run_command(f"git remote set-url origin {remote_url}")
    if result is None:
        return False
    
    # Push to GitHub
    result = run_command(f"git push -u origin {branch}")
    if result is None:
        return False
    
    print(f"Successfully pushed to {username}/{repo_name} on branch {branch}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python github_push.py <username> <pat> <repo_name> [branch]")
        sys.exit(1)
    
    username = sys.argv[1]
    pat = sys.argv[2]
    repo_name = sys.argv[3]
    branch = sys.argv[4] if len(sys.argv) > 4 else "main"
    
    repo_path = "/workspace/bfb-rev-2"
    success = push_to_github(repo_path, username, pat, repo_name, branch)
    
    sys.exit(0 if success else 1)