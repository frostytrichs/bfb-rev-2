#!/usr/bin/env python3
"""
Lemmy API client for BlueFlagBot.
"""

import os
import json
import logging
import time
import requests
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs

logger = logging.getLogger(__name__)


class LemmyAPI:
    """
    Client for interacting with the Lemmy API.
    """
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize the Lemmy API client.
        
        Args:
            config: Configuration dictionary
            db: Database instance for tracking API usage
        """
        self.config = config
        self.db = db
        self.lemmy_config = config.get('lemmy', {})
        
        self.instance_url = self.lemmy_config.get('instance', 'https://lemmy.world')
        self.username = self.lemmy_config.get('username', '')
        self.password = self.lemmy_config.get('password', '')
        self.community = self.lemmy_config.get('community', '')
        
        self.api_base = urljoin(self.instance_url, "/api/v3/")
        self.session = requests.Session()
        self.jwt_token = None
        
        # Error handling settings
        self.max_retries = config.get('error_handling', {}).get('max_retries', 3)
        self.retry_delay = config.get('error_handling', {}).get('retry_delay_seconds', 60)
        self.backoff_factor = config.get('error_handling', {}).get('backoff_factor', 2)
        
        # Load credentials if available
        self.load_credentials()
    
    def load_credentials(self):
        """
        Load credentials from file if available.
        """
        try:
            # Determine the base directory
            if 'credentials_file' in self.lemmy_config:
                creds_file = self.lemmy_config['credentials_file']
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                creds_file = os.path.join(base_dir, "credentials", "lemmy_auth.json")
            
            if os.path.exists(creds_file):
                with open(creds_file, 'r') as f:
                    creds = json.load(f)
                
                # Update config with credentials
                self.instance_url = creds.get('instance', self.instance_url)
                self.username = creds.get('username', self.username)
                self.password = creds.get('password', self.password)
                self.community = creds.get('community', self.community)
                self.jwt_token = creds.get('jwt_token')
                
                # Update API base URL
                self.api_base = urljoin(self.instance_url, "/api/v3/")
                
                logger.info("Loaded Lemmy credentials from file")
        except Exception as e:
            logger.error(f"Error loading Lemmy credentials: {e}")
    
    def save_credentials(self):
        """
        Save credentials to file.
        """
        try:
            # Determine the base directory
            if 'credentials_file' in self.lemmy_config:
                creds_file = self.lemmy_config['credentials_file']
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                creds_dir = os.path.join(base_dir, "credentials")
                os.makedirs(creds_dir, exist_ok=True)
                creds_file = os.path.join(creds_dir, "lemmy_auth.json")
            
            creds = {
                'instance': self.instance_url,
                'username': self.username,
                'password': self.password,
                'community': self.community,
                'jwt_token': self.jwt_token
            }
            
            with open(creds_file, 'w') as f:
                json.dump(creds, f, indent=4)
            
            logger.info("Saved Lemmy credentials to file")
        except Exception as e:
            logger.error(f"Error saving Lemmy credentials: {e}")
    
    def login(self) -> bool:
        """
        Log in to the Lemmy instance and get a JWT token.
        
        Returns:
            True if login was successful, False otherwise
        """
        login_url = urljoin(self.api_base, "user/login")
        
        payload = {
            "username_or_email": self.username,
            "password": self.password
        }
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(login_url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                self.jwt_token = data.get("jwt")
                
                if self.jwt_token:
                    # Update session headers with token
                    self.session.headers.update({
                        'Authorization': f"Bearer {self.jwt_token}"
                    })
                    
                    # Save credentials with token
                    self.save_credentials()
                    
                    logger.info(f"Successfully logged in as {self.username}")
                    return True
                else:
                    logger.error("Login successful but no JWT token received")
                    return False
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Login attempt {attempt + 1}/{self.max_retries} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    # Calculate delay with exponential backoff
                    delay = self.retry_delay * (self.backoff_factor ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("All login attempts failed")
                    return False
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get headers with authentication token.
        
        Returns:
            Dict containing authorization headers
        """
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
            
        return headers
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """
        Make a request to the Lemmy API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            
        Returns:
            Response data as dictionary, or None if request failed
        """
        url = urljoin(self.api_base, endpoint)
        
        # Ensure we're authenticated
        if not self.jwt_token and endpoint != "user/login":
            if not self.login():
                return None
        
        for attempt in range(self.max_retries):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params, headers=self._get_auth_headers())
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=data, headers=self._get_auth_headers())
                elif method.upper() == 'PUT':
                    response = self.session.put(url, json=data, headers=self._get_auth_headers())
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, json=data, headers=self._get_auth_headers())
                else:
                    logger.error(f"Unsupported HTTP method: {method}")
                    return None
                
                # Check for authentication errors
                if response.status_code == 401:
                    logger.warning("Authentication token expired, logging in again")
                    if not self.login():
                        return None
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                logger.error(f"API request attempt {attempt + 1}/{self.max_retries} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    # Calculate delay with exponential backoff
                    delay = self.retry_delay * (self.backoff_factor ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All API request attempts failed for {endpoint}")
                    return None
    
    def get_community_id(self) -> Optional[int]:
        """
        Get the ID of the configured community.
        
        Returns:
            Community ID, or None if not found
        """
        params = {'name': self.community}
        response = self._make_request('GET', 'community', params=params)
        
        if response and 'community_view' in response:
            community_id = response['community_view']['community']['id']
            logger.info(f"Found community ID for {self.community}: {community_id}")
            return community_id
        else:
            logger.error(f"Failed to get community ID for {self.community}")
            return None
    
    def get_communities(self, limit: int = 20, page: int = 1) -> Optional[List[Dict[str, Any]]]:
        """
        Get a list of communities.
        
        Args:
            limit: Maximum number of communities to return
            page: Page number
            
        Returns:
            List of communities or None if request failed
        """
        params = {
            "limit": limit,
            "page": page,
            "sort": "Active"
        }
        
        response = self._make_request('GET', 'community/list', params=params)
        
        if response:
            return response.get("communities", [])
        else:
            return None
    
    def create_post(
        self, 
        community_id: int, 
        name: str, 
        body: Optional[str] = None, 
        url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new post in a community.
        
        Args:
            community_id: ID of the community
            name: Title of the post
            body: Body text of the post (optional)
            url: URL to include in the post (optional)
            
        Returns:
            Post data if successful, None otherwise
        """
        payload = {
            "community_id": community_id,
            "name": name
        }
        
        if body:
            payload["body"] = body
            
        if url:
            payload["url"] = url
            
        response = self._make_request('POST', 'post', data=payload)
        
        if response and 'post_view' in response:
            post = response['post_view']['post']
            logger.info(f"Successfully created post: {name}")
            
            # Record in database if available
            if self.db:
                self.db.record_lemmy_post(post['id'], url or '', name)
            
            return post
        else:
            logger.error(f"Failed to create post: {name}")
            return None
    
    def get_posts(
        self, 
        community_id: Optional[int] = None,
        limit: int = 20, 
        page: int = 1,
        sort: str = "New"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get posts from a community or from all communities.
        
        Args:
            community_id: ID of the community (optional)
            limit: Maximum number of posts to return
            page: Page number
            sort: Sort method ("New", "Hot", "Top", etc.)
            
        Returns:
            List of posts or None if request failed
        """
        params = {
            "limit": limit,
            "page": page,
            "sort": sort
        }
        
        if community_id:
            params["community_id"] = community_id
            
        response = self._make_request('GET', 'post/list', params=params)
        
        if response:
            return response.get("posts", [])
        else:
            return None
    
    def sync_community_posts(self, limit: int = 50) -> bool:
        """
        Sync existing posts from the community to prevent duplicates.
        
        Args:
            limit: Maximum number of posts to sync
            
        Returns:
            True if sync was successful, False otherwise
        """
        try:
            if not self.db:
                logger.warning("No database available for syncing posts")
                return False
            
            community_id = self.get_community_id()
            if not community_id:
                logger.error("Failed to get community ID for syncing posts")
                return False
                
            logger.info(f"Syncing existing posts from community (ID: {community_id})")
            
            # Get posts from Lemmy
            posts = self.get_posts(community_id=community_id, limit=limit, sort="New")
            
            if not posts:
                logger.warning("No posts found in community")
                return False
                
            # Store posts in database
            for post in posts:
                post_view = post.get('post', {})
                post_id = post_view.get('id')
                url = post_view.get('url', '')
                title = post_view.get('name', '')
                
                # Only store YouTube URLs
                if 'youtube.com' in url or 'youtu.be' in url:
                    self.db.record_lemmy_post(post_id, url, title)
                    
                    # Extract video ID from URL
                    video_id = self.extract_youtube_id(url)
                    if video_id:
                        # Also add to posted_videos to prevent reposting
                        self.db.execute_and_commit(
                            "INSERT OR IGNORE INTO posted_videos (video_id, title, channel_name, channel_id, series_tag, youtube_url, lemmy_post_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (video_id, title, "Unknown (Synced)", "Unknown", "SYNCED", url, post_id)
                        )
            
            logger.info(f"Synced {len(posts)} posts from community")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing community posts: {e}")
            return False
    
    def extract_youtube_id(self, url: str) -> Optional[str]:
        """
        Extract YouTube video ID from URL.
        
        Args:
            url: YouTube URL
            
        Returns:
            Video ID, or None if not found
        """
        try:
            if 'youtu.be' in url:
                return url.split('/')[-1].split('?')[0]
            elif 'youtube.com/watch' in url:
                parsed_url = urlparse(url)
                return parse_qs(parsed_url.query).get('v', [None])[0]
            return None
        except Exception as e:
            logger.error(f"Error extracting YouTube ID: {e}")
            return None