#!/usr/bin/env python3
"""
YouTube API client for BlueFlagBot.
"""

import os
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class YouTubeAPI:
    """
    Client for interacting with the YouTube API.
    """
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize the YouTube API client.
        
        Args:
            config: Configuration dictionary
            db: Database instance for tracking quota usage
        """
        self.config = config
        self.db = db
        self.youtube_service = None
        self.quota_used_this_run = 0
        
        # Get YouTube config
        self.youtube_config = config.get('youtube', {})
        
        # Set default paths if not specified
        if 'oauth_credentials_file' not in self.youtube_config:
            base_dir = Path.cwd()
            self.youtube_config['oauth_credentials_file'] = str(base_dir / "credentials" / "youtube_oauth.json")
        
        if 'token_file' not in self.youtube_config:
            base_dir = Path.cwd()
            self.youtube_config['token_file'] = str(base_dir / "credentials" / "youtube_token.json")
        
        # Set quota limits
        self.daily_quota_limit = self.youtube_config.get('daily_quota', 10000)
        self.run_quota_limit = self.youtube_config.get('quota_per_run', 300)
    
    def authenticate(self) -> bool:
        """
        Authenticate with the YouTube API.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            creds = None
            token_file = self.youtube_config['token_file']
            oauth_file = self.youtube_config['oauth_credentials_file']
            
            # Check if token file exists
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file)
            
            # If no credentials or credentials are invalid, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Refreshing YouTube credentials...")
                    creds.refresh(Request())
                else:
                    logger.info("YouTube OAuth required...")
                    
                    # Check if OAuth credentials file exists
                    if not os.path.exists(oauth_file):
                        logger.error(f"OAuth credentials file not found: {oauth_file}")
                        return False
                    
                    # Set up OAuth flow
                    flow = InstalledAppFlow.from_client_secrets_file(
                        oauth_file,
                        ['https://www.googleapis.com/auth/youtube.readonly']
                    )
                    
                    # Use non-local redirect for SSH environments
                    flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    
                    # Print instructions for authentication
                    print("\n=== YouTube OAuth Required ===")
                    print("Setting up YouTube API access...")
                    print(f"\n1. Open this URL in your browser:")
                    print(f"   {auth_url}")
                    print(f"\n2. Complete the authorization")
                    print(f"3. Copy the authorization code")
                    print(f"4. Paste it below")
                    
                    # Get authorization code from user
                    auth_code = input("\nEnter authorization code: ").strip()
                    
                    # Exchange authorization code for credentials
                    flow.fetch_token(code=auth_code)
                    creds = flow.credentials
                
                # Save credentials for next run
                os.makedirs(os.path.dirname(token_file), exist_ok=True)
                with open(token_file, 'w') as f:
                    f.write(creds.to_json())
            
            # Build YouTube service
            self.youtube_service = build('youtube', 'v3', credentials=creds)
            logger.info("YouTube API authenticated successfully")
            return True
            
        except Exception as e:
            logger.error(f"YouTube authentication failed: {e}")
            return False
    
    def track_quota_usage(self, cost: int):
        """
        Track YouTube API quota usage.
        
        Args:
            cost: Quota cost of the operation
        """
        self.quota_used_this_run += cost
        
        # Update database if available
        if self.db:
            today = datetime.now().date()
            
            # Check if stats exist for today
            query = "SELECT * FROM bot_stats WHERE date = ?"
            result = self.db.fetch_one(query, (today,))
            
            if result:
                # Update existing stats
                query = '''
                    UPDATE bot_stats 
                    SET youtube_quota_used = youtube_quota_used + ?
                    WHERE date = ?
                '''
                
                self.db.execute_and_commit(query, (cost, today))
            else:
                # Insert new stats
                query = '''
                    INSERT INTO bot_stats 
                    (date, posts_made, youtube_quota_used, errors_count, videos_processed)
                    VALUES (?, 0, ?, 0, 0)
                '''
                
                self.db.execute_and_commit(query, (today, cost))
    
    def check_quota_limit(self, estimated_cost: int) -> bool:
        """
        Check if there's enough quota available for an operation.
        
        Args:
            estimated_cost: Estimated quota cost of the operation
            
        Returns:
            True if there's enough quota, False otherwise
        """
        # Check if the estimated cost exceeds the per-run limit
        if self.quota_used_this_run + estimated_cost > self.run_quota_limit:
            logger.warning(
                f"Estimated quota cost ({estimated_cost}) would exceed per-run limit "
                f"({self.run_quota_limit - self.quota_used_this_run} remaining)"
            )
            return False
        
        # Check daily quota usage if database is available
        if self.db:
            daily_usage = self.db.get_youtube_quota_usage()
            
            if daily_usage + estimated_cost > self.daily_quota_limit:
                logger.warning(
                    f"Daily quota limit would be exceeded: "
                    f"{daily_usage}/{self.daily_quota_limit} used, "
                    f"need {estimated_cost} more"
                )
                return False
            
            logger.info(
                f"Quota check passed: {daily_usage + estimated_cost}/{self.daily_quota_limit} "
                f"({self.quota_used_this_run + estimated_cost}/{self.run_quota_limit} this run)"
            )
        else:
            logger.info(
                f"Quota check passed: {self.quota_used_this_run + estimated_cost}/{self.run_quota_limit} this run"
            )
        
        return True
    
    def get_subscription_channels(self) -> List[Dict]:
        """
        Get list of subscribed channels.
        
        Returns:
            List of channel dictionaries
        """
        if not self.youtube_service:
            if not self.authenticate():
                return []
        
        # Check quota
        estimated_cost = 1  # Initial request
        if not self.check_quota_limit(estimated_cost):
            return []
        
        channels = []
        next_page_token = None
        total_cost = 0
        
        try:
            while True:
                request = self.youtube_service.subscriptions().list(
                    part='snippet',
                    mine=True,
                    maxResults=50,
                    pageToken=next_page_token
                )
                
                response = request.execute()
                total_cost += 1  # Each request costs 1 unit
                
                for item in response.get('items', []):
                    channel_info = {
                        'channel_id': item['snippet']['resourceId']['channelId'],
                        'channel_name': item['snippet']['title'],
                        'description': item['snippet'].get('description', '')
                    }
                    channels.append(channel_info)
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                
                # Check if we have enough quota for another page
                if not self.check_quota_limit(1):
                    logger.warning("Stopping channel retrieval due to quota limits")
                    break
            
            # Track quota usage
            self.track_quota_usage(total_cost)
            
            logger.info(f"Found {len(channels)} subscribed channels")
            return channels
            
        except HttpError as e:
            logger.error(f"Error fetching subscriptions: {e}")
            return []
    
    def get_channel_recent_videos(self, channel_id: str, max_results: int = 10) -> List[Dict]:
        """
        Get recent videos from a specific channel.
        
        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of videos to return
            
        Returns:
            List of video dictionaries
        """
        if not self.youtube_service:
            if not self.authenticate():
                return []
        
        # Check quota - getting channel info + playlist items + video details
        estimated_cost = 3
        if not self.check_quota_limit(estimated_cost):
            return []
        
        try:
            # Get channel uploads playlist ID
            channel_request = self.youtube_service.channels().list(
                part='contentDetails',
                id=channel_id
            )
            
            channel_response = channel_request.execute()
            self.track_quota_usage(1)  # Channel request costs 1 unit
            
            if not channel_response.get('items'):
                logger.warning(f"No channel found with ID: {channel_id}")
                return []
            
            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get playlist items
            playlist_request = self.youtube_service.playlistItems().list(
                part='snippet',
                playlistId=uploads_playlist_id,
                maxResults=max_results
            )
            
            playlist_response = playlist_request.execute()
            self.track_quota_usage(1)  # Playlist request costs 1 unit
            
            videos = []
            video_ids = []
            
            # Get the maximum age in hours for videos
            max_age_hours = self.config.get('filtering', {}).get('video_max_age_hours', 24)
            cutoff_date = datetime.now() - timedelta(hours=max_age_hours)
            
            # Pre-filter videos based on publishedAt date and cache
            for item in playlist_response.get('items', []):
                video_id = item['snippet']['resourceId']['videoId']
                
                # Check if the video is in the old video cache
                if self.db and self.db.is_video_in_old_cache(video_id):
                    logger.debug(f"Skipping cached old video: {video_id}")
                    continue
                
                # Check the publishedAt date from the playlist item
                playlist_published_date = date_parser.parse(item['snippet']['publishedAt']).replace(tzinfo=None)
                
                # Check if the title contains "LIVE" which might indicate a livestream
                title = item['snippet']['title'].upper()
                might_be_livestream = "LIVE" in title
                
                # If the video is older than our cutoff and not a potential livestream,
                # add it to the cache and skip it
                # We add a buffer of 7 days (168 hours) to account for livestreams that might have old publishedAt dates
                # We also keep videos with "LIVE" in the title for further processing
                if playlist_published_date < (cutoff_date - timedelta(hours=168)) and not might_be_livestream:
                    logger.debug(f"Skipping old video based on playlist date: {item['snippet']['title']}")
                    if self.db:
                        self.db.add_video_to_old_cache(video_id, item['snippet']['channelId'], is_livestream=False)
                    continue
                
                video_ids.append(video_id)
            
            if not video_ids:
                return []
            
            # Get video details
            videos_request = self.youtube_service.videos().list(
                part='snippet,statistics,contentDetails,liveStreamingDetails',
                id=','.join(video_ids)
            )
            
            videos_response = videos_request.execute()
            self.track_quota_usage(1)  # Video details request costs 1 unit
            
            for video_info in videos_response.get('items', []):
                video_id = video_info['id']
                channel_id = video_info['snippet']['channelId']
                published_date = date_parser.parse(video_info['snippet']['publishedAt']).replace(tzinfo=None)
                
                # Check if this is a livestream or upcoming stream
                is_livestream = False
                is_upcoming = False
                scheduled_start_time = None
                actual_start_time = None
                
                if 'liveStreamingDetails' in video_info:
                    live_details = video_info['liveStreamingDetails']
                    
                    # Check for scheduled start time (upcoming stream)
                    if 'scheduledStartTime' in live_details:
                        scheduled_start_time = date_parser.parse(live_details['scheduledStartTime']).replace(tzinfo=None)
                        is_upcoming = True
                    
                    # Check for actual start time (currently live)
                    if 'actualStartTime' in live_details:
                        actual_start_time = date_parser.parse(live_details['actualStartTime']).replace(tzinfo=None)
                        is_livestream = 'actualEndTime' not in live_details  # Only consider it live if it hasn't ended
                
                # If it's a regular video (not live or upcoming) and it's too old, add to cache and skip
                if not is_livestream and not is_upcoming and published_date < cutoff_date:
                    logger.debug(f"Adding old video to cache: {video_info['snippet']['title']}")
                    if self.db:
                        self.db.add_video_to_old_cache(video_id, channel_id, is_livestream=False)
                    continue
                
                # If it's an upcoming stream with a past scheduled start time, add to cache and skip
                if is_upcoming and scheduled_start_time and scheduled_start_time < datetime.now():
                    logger.debug(f"Adding past scheduled stream to cache: {video_info['snippet']['title']}")
                    if self.db:
                        self.db.add_video_to_old_cache(video_id, channel_id, is_livestream=False)
                    continue
                
                # Check if this is a YouTube Short
                duration = video_info['contentDetails']['duration']
                if self.is_youtube_short(duration):
                    if self.db:
                        self.db.add_video_to_old_cache(video_id, channel_id, is_livestream=False)
                    continue
                
                # Create video data dictionary
                video_data = {
                    'video_id': video_info['id'],
                    'title': video_info['snippet']['title'],
                    'channel_name': video_info['snippet']['channelTitle'],
                    'channel_id': video_info['snippet']['channelId'],
                    'published_at': published_date,
                    'url': f"https://www.youtube.com/watch?v={video_info['id']}",
                    'description': video_info['snippet']['description'],
                    'view_count': int(video_info['statistics'].get('viewCount', 0)),
                    'duration': duration,
                    'is_livestream': is_livestream,
                    'is_upcoming': is_upcoming,
                    'scheduled_start_time': scheduled_start_time,
                    'actual_start_time': actual_start_time
                }
                
                videos.append(video_data)
            
            return videos
            
        except HttpError as e:
            logger.error(f"Error fetching videos for channel {channel_id}: {e}")
            return []
    
    def is_youtube_short(self, duration: str) -> bool:
        """
        Check if video is a YouTube Short based on duration.
        
        Args:
            duration: Video duration in ISO 8601 format
            
        Returns:
            True if the video is a Short, False otherwise
        """
        import re
        
        try:
            # For livestreams, the duration might be 'P0D' or similar
            # We don't want to consider livestreams as shorts
            if duration == 'P0D':
                return False
            
            # Parse ISO 8601 duration
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
            if not match:
                return True
            
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            min_length = self.config.get('filtering', {}).get('min_video_length_seconds', 60)
            
            return total_seconds < min_length
        except Exception as e:
            logger.error(f"Error checking if video is a Short: {e}")
            return True
    
    def reset_quota_usage(self):
        """
        Reset quota usage for this run.
        """
        self.quota_used_this_run = 0