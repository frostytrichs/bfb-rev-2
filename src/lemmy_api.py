#!/usr/bin/env python3
"""
Lemmy API client module.
Handles interactions with the Lemmy API.
"""

import logging
import requests
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class LemmyAPI:
    """
    Client for interacting with the Lemmy API.
    """
    
    def __init__(self, instance_url: str):
        """
        Initialize the Lemmy API client.
        
        Args:
            instance_url: URL of the Lemmy instance
        """
        self.instance_url = instance_url
        self.api_base = urljoin(instance_url, "/api/v3/")
        self.session = requests.Session()
        self.jwt_token: Optional[str] = None
        
    def login(self, username: str, password: str) -> bool:
        """
        Log in to the Lemmy instance and get a JWT token.
        
        Args:
            username: Lemmy username
            password: Lemmy password
            
        Returns:
            True if login was successful, False otherwise
        """
        login_url = urljoin(self.api_base, "user/login")
        
        payload = {
            "username_or_email": username,
            "password": password
        }
        
        try:
            response = self.session.post(login_url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            self.jwt_token = data.get("jwt")
            
            if self.jwt_token:
                logger.info(f"Successfully logged in as {username}")
                return True
            else:
                logger.error("Login successful but no JWT token received")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Login failed: {e}")
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
    
    def get_communities(self, limit: int = 20, page: int = 1) -> Optional[List[Dict[str, Any]]]:
        """
        Get a list of communities.
        
        Args:
            limit: Maximum number of communities to return
            page: Page number
            
        Returns:
            List of communities or None if request failed
        """
        url = urljoin(self.api_base, "community/list")
        
        params = {
            "limit": limit,
            "page": page,
            "sort": "Active"
        }
        
        try:
            response = self.session.get(
                url, 
                params=params, 
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("communities", [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get communities: {e}")
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
        if not self.jwt_token:
            logger.error("Cannot create post: Not logged in")
            return None
            
        post_url = urljoin(self.api_base, "post")
        
        payload = {
            "community_id": community_id,
            "name": name
        }
        
        if body:
            payload["body"] = body
            
        if url:
            payload["url"] = url
            
        try:
            response = self.session.post(
                post_url, 
                json=payload, 
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully created post: {name}")
            return data.get("post")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create post: {e}")
            return None
    
    def create_comment(
        self, 
        post_id: int, 
        content: str, 
        parent_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a comment on a post or reply to another comment.
        
        Args:
            post_id: ID of the post
            content: Comment content
            parent_id: ID of the parent comment (optional, for replies)
            
        Returns:
            Comment data if successful, None otherwise
        """
        if not self.jwt_token:
            logger.error("Cannot create comment: Not logged in")
            return None
            
        comment_url = urljoin(self.api_base, "comment")
        
        payload = {
            "post_id": post_id,
            "content": content
        }
        
        if parent_id:
            payload["parent_id"] = parent_id
            
        try:
            response = self.session.post(
                comment_url, 
                json=payload, 
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully created comment on post {post_id}")
            return data.get("comment")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create comment: {e}")
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
        url = urljoin(self.api_base, "post/list")
        
        params = {
            "limit": limit,
            "page": page,
            "sort": sort
        }
        
        if community_id:
            params["community_id"] = community_id
            
        try:
            response = self.session.get(
                url, 
                params=params, 
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("posts", [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get posts: {e}")
            return None