#!/usr/bin/env python3
"""
Main bot implementation for BlueFlagBot.
"""

import os
import time
import html
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from src.api.youtube import YouTubeAPI
from src.api.lemmy import LemmyAPI
from src.core.database import Database
from src.core.scoring import ContentScorer, RacingSeriesDetector

logger = logging.getLogger(__name__)


class BlueFlagBot:
    """
    Main bot class for BlueFlagBot.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the BlueFlagBot.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.running = False
        
        # Set up base directory
        self.base_dir = Path.cwd()
        
        # Initialize database
        db_path = self.config.get('database', {}).get('path', 'data/blueflagbot.db')
        if not os.path.isabs(db_path):
            db_path = self.base_dir / db_path
        self.db = Database(db_path)
        
        # Initialize API clients
        self.youtube_api = YouTubeAPI(config, self.db)
        self.lemmy_api = LemmyAPI(config, self.db)
        
        # Initialize content scoring
        self.content_scorer = ContentScorer(config)
        self.series_detector = RacingSeriesDetector(config)
        
        # Get scan settings
        scan_config = config.get('scan', {})
        self.scan_interval = scan_config.get('interval_minutes', 30)
        self.max_posts_per_run = scan_config.get('max_posts_per_run', 5)
        self.max_posts_per_day = scan_config.get('max_posts_per_day', 100)
        self.max_posts_per_hour = scan_config.get('max_posts_per_hour', 20)
        self.time_between_posts = scan_config.get('time_between_posts_seconds', 60)
        
        # Test mode
        self.test_mode = config.get('general', {}).get('test_mode', False)
        if self.test_mode:
            logger.info("Running in TEST MODE - no actual posts will be made")
        
        logger.info("BlueFlagBot initialized")
    
    def run_continuous(self):
        """
        Run the bot in continuous mode.
        """
        self.running = True
        logger.info(f"Starting continuous mode with {self.scan_interval} minute intervals")
        
        try:
            while self.running:
                start_time = time.time()
                
                try:
                    # Run a single scan cycle
                    self.run_once()
                except Exception as e:
                    logger.error(f"Error in scan cycle: {e}", exc_info=True)
                    if self.db:
                        self.db.log_error("scan_cycle", str(e), "bot.py", "run_continuous")
                
                # Calculate time to next scan
                elapsed = time.time() - start_time
                sleep_time = max(0, (self.scan_interval * 60) - elapsed)
                
                if sleep_time > 0:
                    logger.info(f"Scan completed in {elapsed:.1f} seconds. Next scan in {sleep_time/60:.1f} minutes")
                    
                    # Sleep in smaller increments to allow for clean shutdown
                    sleep_increment = 5  # 5 seconds
                    for _ in range(int(sleep_time / sleep_increment)):
                        if not self.running:
                            break
                        time.sleep(sleep_increment)
                    
                    # Sleep any remaining time
                    remaining = sleep_time % sleep_increment
                    if remaining > 0 and self.running:
                        time.sleep(remaining)
                else:
                    logger.warning(f"Scan took longer than interval: {elapsed:.1f} seconds > {self.scan_interval * 60} seconds")
                    # Small delay to prevent CPU spinning if scans consistently take too long
                    time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, stopping")
            self.stop()
        
        except Exception as e:
            logger.error(f"Fatal error in continuous mode: {e}", exc_info=True)
            if self.db:
                self.db.log_error("fatal", str(e), "bot.py", "run_continuous")
            self.stop()
    
    def run_once(self):
        """
        Run a single scan cycle.
        """
        logger.info("Starting scan cycle")
        
        posts_made = 0
        errors = 0
        videos_processed = 0
        
        try:
            # Reset YouTube API quota usage for this run
            self.youtube_api.reset_quota_usage()
            
            # Authenticate with APIs
            if not self.youtube_api.authenticate():
                logger.error("Failed to authenticate with YouTube API")
                return
            
            if not self.lemmy_api.login():
                logger.error("Failed to authenticate with Lemmy API")
                return
            
            # Sync Lemmy posts to prevent duplicates
            self.lemmy_api.sync_community_posts()
            
            # Fetch candidate videos
            candidate_videos = self.fetch_candidate_videos()
            videos_processed = len(candidate_videos)
            
            if not candidate_videos:
                logger.info("No candidate videos found")
                return
            
            # Process videos in priority order
            for video in candidate_videos:
                # Stop if we've reached the maximum number of posts for this run
                if posts_made >= self.max_posts_per_run:
                    logger.info(f"Reached maximum posts per run ({self.max_posts_per_run})")
                    break
                
                if not self.should_post_video(video):
                    continue
                
                try:
                    post_id = self.create_lemmy_post(video)
                    if post_id:
                        posts_made += 1
                        
                        # Add delay between posts
                        if self.time_between_posts > 0 and posts_made < self.max_posts_per_run:
                            logger.info(f"Waiting {self.time_between_posts} seconds before next post...")
                            time.sleep(self.time_between_posts)
                    else:
                        errors += 1
                        
                except Exception as e:
                    logger.error(f"Error posting video {video['title']}: {e}", exc_info=True)
                    if self.db:
                        self.db.log_error("post_creation", str(e), "bot.py", "run_once")
                    errors += 1
            
            logger.info(f"Scan cycle complete: {posts_made} posts made, {errors} errors")
            
        except Exception as e:
            logger.error(f"Error in scan cycle: {e}", exc_info=True)
            if self.db:
                self.db.log_error("scan_cycle", str(e), "bot.py", "run_once")
            errors += 1
        
        finally:
            # Update statistics
            if self.db:
                quota_used = self.youtube_api.quota_used_this_run
                self.db.update_bot_stats(posts_made, quota_used, errors, videos_processed)
            
            # Perform database maintenance occasionally
            if datetime.now().hour == 3 and datetime.now().minute < 15:  # Around 3 AM
                if self.db:
                    self.db.cleanup_old_data()
    
    def fetch_candidate_videos(self) -> List[Dict]:
        """
        Fetch and filter candidate videos from channels.
        
        Returns:
            List of video dictionaries
        """
        logger.info("Fetching candidate videos from channels")
        
        # Get channels from configuration
        channels = self.config.get('channels', [])
        if not channels:
            logger.warning("No channels configured")
            return []
        
        # Estimate quota cost: ~3 units per channel
        estimated_quota = len(channels) * 3
        
        # Check if we have enough quota
        if not self.youtube_api.check_quota_limit(estimated_quota):
            logger.error("YouTube quota limit would be exceeded")
            return []
        
        all_videos = []
        
        # Process each channel
        for channel in channels:
            channel_id = channel['channelID']
            channel_name = channel['name']
            
            logger.info(f"Processing channel: {channel_name}")
            
            # Get recent videos from channel
            videos = self.youtube_api.get_channel_recent_videos(channel_id)
            
            # Process each video
            for video in videos:
                # Check for duplicates
                if self.db and self.db.check_for_duplicates(
                    video['video_id'], 
                    video['title'], 
                    video['channel_id'],
                    self.config.get('filtering', {}).get('duplicate_check_hours', 48)
                ):
                    logger.debug(f"Skipping duplicate: {video['title']}")
                    continue
                
                # Handle livestream and upcoming stream logic
                if video.get('is_upcoming'):
                    # Get the maximum age in hours for videos (applies to upcoming streams too)
                    max_age_hours = self.config.get('filtering', {}).get('video_max_age_hours', 24)
                    
                    # Calculate when the next scan will happen
                    next_scan_time = datetime.now() + timedelta(minutes=self.scan_interval)
                    current_time = datetime.now()
                    
                    # Calculate the maximum future time for upcoming streams
                    max_future_time = current_time + timedelta(hours=max_age_hours)
                    
                    # Skip streams with scheduled start times in the past
                    if video['scheduled_start_time'] < current_time:
                        logger.debug(f"Skipping upcoming stream with past start time: {video['title']}")
                        continue
                    
                    # Skip streams that are scheduled too far in the future (beyond max_age_hours)
                    if video['scheduled_start_time'] > max_future_time:
                        logger.debug(f"Skipping upcoming stream scheduled too far in the future: {video['title']}")
                        continue
                    
                    # If the stream won't be live before the next scan, skip it for now
                    if video['scheduled_start_time'] > next_scan_time:
                        logger.debug(f"Skipping upcoming stream that won't be live before next scan: {video['title']}")
                        continue
                    else:
                        logger.info(f"Including upcoming stream that will go live soon: {video['title']}")
                
                # Check if content is acceptable
                if not self.content_scorer.is_acceptable_content(video):
                    logger.debug(f"Skipping low-quality content: {video['title']}")
                    continue
                
                # Detect series and tag
                series_tag, priority = self.series_detector.detect_series_and_tag(video)
                
                # Add metadata to video
                video['series_tag'] = series_tag
                video['priority_score'] = priority
                
                # Add livestream status to logging
                stream_status = ""
                if video.get('is_livestream'):
                    stream_status = "[LIVE] "
                elif video.get('is_upcoming'):
                    stream_status = "[UPCOMING] "
                
                all_videos.append(video)
                logger.info(f"Added candidate: [{series_tag}] {stream_status}{video['title']} (Score: {video['quality_score']})")
        
        # Sort videos by quality score
        all_videos.sort(key=lambda x: x['quality_score'], reverse=True)
        
        logger.info(f"Found {len(all_videos)} candidate videos")
        return all_videos
    
    def should_post_video(self, video_data: Dict[str, Any]) -> bool:
        """
        Determine if video should be posted based on rate limiting and quality.
        
        Args:
            video_data: Video data dictionary
            
        Returns:
            True if video should be posted, False otherwise
        """
        if not self.db:
            # If no database, assume we should post
            return True
        
        # Check daily limit
        daily_posts = self.db.get_recent_posts_count(24)
        if daily_posts >= self.max_posts_per_day:
            logger.info(f"Daily post limit reached: {daily_posts}/{self.max_posts_per_day}")
            return False
        
        # Check hourly limit
        hourly_posts = self.db.get_recent_posts_count(1)
        if hourly_posts >= self.max_posts_per_hour:
            logger.info(f"Hourly post limit reached: {hourly_posts}/{self.max_posts_per_hour}")
            return False
        
        # Use lower threshold for livestreams if configured
        if video_data.get('is_livestream', False):
            threshold = self.config.get('filtering', {}).get('livestream_quality_threshold', 60)
            if video_data['quality_score'] < threshold:
                logger.info(f"Livestream quality too low: {video_data['quality_score']}/{threshold}")
                return False
        else:
            # Regular quality check for non-livestreams
            threshold = self.config.get('filtering', {}).get('min_quality_threshold', 65)
            if video_data['quality_score'] < threshold:
                logger.info(f"Video quality too low: {video_data['quality_score']}/{threshold}")
                return False
        
        return True
    
    def create_lemmy_post(self, video_data: Dict[str, Any]) -> Optional[int]:
        """
        Create a post on Lemmy.
        
        Args:
            video_data: Video data dictionary
            
        Returns:
            Post ID if successful, None otherwise
        """
        try:
            # Get community ID
            community_id = self.lemmy_api.get_community_id()
            if not community_id:
                logger.error("Failed to get community ID")
                return None
            
            # Format post title with series tag
            # Use html.unescape to handle HTML entities in YouTube titles
            post_title = f"[{video_data['series_tag']}] {html.unescape(video_data['title'])}"
            
            # Create post body with additional info
            post_body = f"""**Channel:** {video_data['channel_name']}
**Published:** {video_data['published_at'].strftime('%Y-%m-%d %H:%M UTC')}

{video_data['url']}

---
*Posted by BlueFlagBot - Quality Score: {video_data['quality_score']}/100*"""
            
            if self.test_mode:
                # In test mode, log the post but don't actually post it
                logger.info(f"TEST MODE: Would post: {post_title}")
                
                # Generate a fake post ID for testing
                import hashlib
                fake_post_id = int(hashlib.md5(video_data['video_id'].encode()).hexdigest(), 16) % 10000000
                
                # Record the post in the database even in test mode
                if self.db:
                    self.db.record_posted_video(video_data, fake_post_id)
                
                return fake_post_id
            else:
                # In production mode, actually post to Lemmy
                post = self.lemmy_api.create_post(
                    community_id=community_id,
                    name=post_title,
                    body=post_body,
                    url=video_data['url']
                )
                
                if post:
                    post_id = post['id']
                    
                    # Record in database
                    if self.db:
                        self.db.record_posted_video(video_data, post_id)
                    
                    logger.info(f"Successfully posted: [{video_data['series_tag']}] {video_data['title']}")
                    return post_id
                else:
                    logger.error(f"Failed to create post: {post_title}")
                    return None
                
        except Exception as e:
            logger.error(f"Error creating Lemmy post: {e}", exc_info=True)
            if self.db:
                self.db.log_error("post_creation", str(e), "bot.py", "create_lemmy_post")
            return None
    
    def stop(self):
        """
        Stop the bot gracefully.
        """
        logger.info("Stopping BlueFlagBot")
        self.running = False
        
        # Close database connections
        if self.db:
            self.db.close_all_connections()
        
        logger.info("BlueFlagBot stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the bot.
        
        Returns:
            Dictionary with status information
        """
        status = {
            'running': self.running,
            'test_mode': self.test_mode,
            'scan_interval': self.scan_interval,
            'max_posts_per_run': self.max_posts_per_run,
            'max_posts_per_day': self.max_posts_per_day,
            'max_posts_per_hour': self.max_posts_per_hour,
            'time_between_posts': self.time_between_posts,
            'youtube_quota_used': self.youtube_api.quota_used_this_run if hasattr(self.youtube_api, 'quota_used_this_run') else 0,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add database status if available
        if self.db:
            db_status = self.db.get_status_report()
            status.update(db_status)
        
        return status