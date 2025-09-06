#!/usr/bin/env python3
"""
Content scoring system for BlueFlagBot.
"""

import re
import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ContentScorer:
    """
    Scores content based on keywords and other factors.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the content scorer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.keywords = config.get('keywords', {})
        self.filtering = config.get('filtering', {})
        
        # Default to English keywords if available
        self.active_keywords = self.keywords.get('en', {})
        
        # Set default thresholds
        self.min_quality_threshold = self.filtering.get('min_quality_threshold', 65)
        self.livestream_quality_threshold = self.filtering.get('livestream_quality_threshold', 60)
    
    def calculate_content_quality_score(self, video_data: Dict[str, Any]) -> int:
        """
        Calculate content quality score (0-100).
        
        Args:
            video_data: Video data dictionary
            
        Returns:
            Quality score (0-100)
        """
        title = video_data['title'].lower()
        description = video_data.get('description', '').lower()
        view_count = video_data.get('view_count', 0)
        
        # Start with base score
        score = 50
        
        # Check for auto-reject keywords
        for keyword in self.active_keywords.get('auto_reject', []):
            if keyword.lower() in title:
                logger.info(f"Auto-reject keyword '{keyword}' found in title: {title}")
                return 0
        
        # Add points for quality boosters
        for keyword in self.active_keywords.get('quality_boosters', []):
            if keyword.lower() in title:
                score += 10
                logger.debug(f"Quality booster '{keyword}' found in title (+10): {title}")
            elif keyword.lower() in description:
                score += 5
                logger.debug(f"Quality booster '{keyword}' found in description (+5)")
        
        # Add points for race content
        for keyword in self.active_keywords.get('race_content', []):
            if keyword.lower() in title:
                score += 15
                logger.debug(f"Race content '{keyword}' found in title (+15): {title}")
            elif keyword.lower() in description:
                score += 8
                logger.debug(f"Race content '{keyword}' found in description (+8)")
        
        # Add points for analysis content
        for keyword in self.active_keywords.get('analysis_content', []):
            if keyword.lower() in title:
                score += 8
                logger.debug(f"Analysis content '{keyword}' found in title (+8): {title}")
            elif keyword.lower() in description:
                score += 4
                logger.debug(f"Analysis content '{keyword}' found in description (+4)")
        
        # Subtract points for warning signs
        for keyword in self.active_keywords.get('warning_signs', []):
            if keyword.lower() in title:
                score -= 15
                logger.debug(f"Warning sign '{keyword}' found in title (-15): {title}")
            elif keyword.lower() in description:
                score -= 8
                logger.debug(f"Warning sign '{keyword}' found in description (-8)")
        
        # Add points for view count (reduced impact)
        if view_count > 5000:
            score += 5
            logger.debug(f"High view count: {view_count} (+5)")
        elif view_count > 2500:
            score += 3
            logger.debug(f"Medium view count: {view_count} (+3)")
        elif view_count > 1000:
            score += 1
            logger.debug(f"Low view count: {view_count} (+1)")
        
        # Age/popularity penalty
        age_hours = (datetime.now() - video_data['published_at']).total_seconds() / 3600
        if age_hours > 24 and view_count < 500:
            score -= 10
            logger.debug(f"Age/popularity penalty: {age_hours} hours old with {view_count} views (-10)")
        
        # Special bonus for livestreams
        if video_data.get('is_livestream', False):
            live_content_bonus = self.filtering.get('live_content_bonus', 25)
            score += live_content_bonus
            logger.debug(f"Livestream bonus: +{live_content_bonus}")
        
        # Special bonus for rally stage content
        if ('stage' in title.lower() and ('rally' in title.lower() or 'wrc' in title.lower())) or 'special stage' in title.lower():
            score += 10
            logger.debug(f"Rally stage content bonus (+10)")
        
        # Ensure score is within range
        final_score = max(0, min(100, score))
        logger.info(f"Final quality score for '{title}': {final_score}/100")
        return final_score
    
    def is_acceptable_content(self, video_data: Dict[str, Any]) -> bool:
        """
        Determine if content meets quality standards for posting.
        
        Args:
            video_data: Video data dictionary
            
        Returns:
            True if content is acceptable, False otherwise
        """
        # Calculate quality score
        quality_score = self.calculate_content_quality_score(video_data)
        
        # Store quality score in video data
        video_data['quality_score'] = quality_score
        
        # Use lower threshold for livestreams
        if video_data.get('is_livestream', False):
            threshold = self.livestream_quality_threshold
        else:
            threshold = self.min_quality_threshold
        
        # Check if score meets threshold
        if quality_score < threshold:
            logger.info(f"Content quality below threshold: {quality_score}/{threshold}")
            return False
        
        # Check for YouTube shorts
        if self.is_youtube_short(video_data):
            logger.info(f"Rejecting YouTube Short: {video_data['title']}")
            return False
        
        return True
    
    def is_youtube_short(self, video_data: Dict[str, Any]) -> bool:
        """
        Check if video is a YouTube Short.
        
        Args:
            video_data: Video data dictionary
            
        Returns:
            True if the video is a Short, False otherwise
        """
        title = video_data['title'].lower()
        
        # Check for Short indicators in title
        short_indicators = ['#shorts', '#short', '#youtubeshorts']
        for indicator in short_indicators:
            if indicator in title:
                return True
        
        # Check duration if available
        duration = video_data.get('duration')
        if duration:
            try:
                # Parse ISO 8601 duration
                match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
                if not match:
                    return True
                
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = int(match.group(3) or 0)
                
                total_seconds = hours * 3600 + minutes * 60 + seconds
                min_length = self.filtering.get('min_video_length_seconds', 60)
                
                return total_seconds < min_length
            except Exception as e:
                logger.error(f"Error checking video duration: {e}")
        
        return False


class RacingSeriesDetector:
    """
    Detects racing series from video metadata and assigns tags.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the racing series detector.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.channels = config.get('channels', [])
        
        # Create a lookup dictionary for faster access
        self.channel_lookup = {}
        for channel in self.channels:
            self.channel_lookup[channel['channelID']] = channel
    
    def detect_series_and_tag(self, video_data: Dict[str, Any]) -> Tuple[str, int]:
        """
        Detect racing series and return best single tag with priority.
        
        Args:
            video_data: Video data dictionary
            
        Returns:
            Tuple of (tag, priority)
        """
        channel_id = video_data['channel_id']
        title = video_data['title'].lower()
        description = video_data.get('description', '').lower()
        
        # Check if channel is in our configuration
        if channel_id in self.channel_lookup:
            channel_info = self.channel_lookup[channel_id]
            primary_tag = channel_info['primary_tag']
            secondary_tags = channel_info.get('secondary_tags', [])
            
            # Default priority (can be customized later)
            base_priority = 5
            
            best_tag = primary_tag
            
            # Check for secondary tags in title and description
            for secondary_tag in secondary_tags:
                tag_lower = secondary_tag.lower()
                if tag_lower in title or tag_lower in description:
                    if self.is_more_specific_tag(secondary_tag, primary_tag, title, description):
                        best_tag = secondary_tag
                        break
            
            return (best_tag, base_priority)
        else:
            # Channel not in our configuration
            return ('OTHER', 1)
    
    def is_more_specific_tag(self, secondary_tag: str, primary_tag: str, title: str, description: str) -> bool:
        """
        Determine if secondary tag is more specific for this content.
        
        Args:
            secondary_tag: Secondary tag
            primary_tag: Primary tag
            title: Video title
            description: Video description
            
        Returns:
            True if secondary tag is more specific, False otherwise
        """
        title_lower = title.lower()
        description_lower = description.lower()
        
        # Class tags (LMP2, GT3, etc.)
        class_tags = ['LMP2', 'LMP3', 'GT3', 'GT4', 'HYPERCAR', 'LMGT3', 'GTLM', 'GTD']
        if secondary_tag in class_tags:
            return secondary_tag.lower() in title_lower
        
        # Event tags (SPA24H, 24H, etc.)
        event_tags = ['SPA24H', '24H']
        if secondary_tag in event_tags:
            if secondary_tag == 'SPA24H':
                return 'spa' in title_lower and ('24' in title_lower or 'hour' in title_lower)
            elif secondary_tag == '24H':
                return '24' in title_lower and ('hour' in title_lower or 'h' in title_lower)
        
        # Rally specific tags
        rally_tags = ['WRC2', 'JWRC', 'ARA']
        if secondary_tag in rally_tags:
            if secondary_tag == 'WRC2':
                return 'wrc2' in title_lower or 'wrc 2' in title_lower or 'wrc-2' in title_lower
            elif secondary_tag == 'JWRC':
                return 'jwrc' in title_lower or 'junior wrc' in title_lower
            elif secondary_tag == 'ARA':
                return 'ara' in title_lower or 'american rally' in title_lower
        
        # Porsche specific tags
        porsche_tags = ['PSCNA', 'IMSA']
        if secondary_tag in porsche_tags:
            if secondary_tag == 'PSCNA':
                return 'sprint challenge' in title_lower
            elif secondary_tag == 'IMSA':
                return 'imsa' in title_lower
        
        return False