#!/usr/bin/env python3
"""
Database management for BlueFlagBot.
"""

import os
import sqlite3
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database manager with connection pooling and proper resource management.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.connection_pool = {}
        self.lock = threading.Lock()
        
        # Ensure directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        # Initialize database
        self.init_database()
    
    def get_connection(self):
        """
        Get a database connection from the pool or create a new one.
        
        Returns:
            SQLite connection
        """
        thread_id = threading.get_ident()
        
        with self.lock:
            if thread_id not in self.connection_pool:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row  # Return rows as dictionaries
                self.connection_pool[thread_id] = conn
            
            return self.connection_pool[thread_id]
    
    def close_all_connections(self):
        """
        Close all database connections in the pool.
        """
        with self.lock:
            for conn in self.connection_pool.values():
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing database connection: {e}")
            
            self.connection_pool.clear()
    
    def init_database(self):
        """
        Initialize the database schema.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Posted videos table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posted_videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    channel_name TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    series_tag TEXT,
                    youtube_url TEXT NOT NULL,
                    lemmy_post_id INTEGER,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    upvotes INTEGER DEFAULT 0,
                    downvotes INTEGER DEFAULT 0,
                    priority_score INTEGER DEFAULT 0,
                    quality_score INTEGER DEFAULT 0
                )
            ''')
            
            # Subscription channels table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscription_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT UNIQUE NOT NULL,
                    channel_name TEXT NOT NULL,
                    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    video_count INTEGER DEFAULT 0
                )
            ''')
            
            # Bot statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    posts_made INTEGER DEFAULT 0,
                    youtube_quota_used INTEGER DEFAULT 0,
                    errors_count INTEGER DEFAULT 0,
                    videos_processed INTEGER DEFAULT 0
                )
            ''')
            
            # Duplicate tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS duplicate_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL,
                    title_hash TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(video_id, title_hash)
                )
            ''')
            
            # Lemmy posts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lemmy_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Old video cache table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS old_video_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT UNIQUE NOT NULL,
                    channel_id TEXT NOT NULL,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expiry TIMESTAMP NOT NULL
                )
            ''')
            
            # API quota tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_quota (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    youtube_quota_used INTEGER DEFAULT 0,
                    lemmy_requests INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Error log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS error_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    module TEXT,
                    function TEXT,
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error initializing database: {e}")
            raise
    
    def execute(self, query: str, params: tuple = ()):
        """
        Execute a query and return the cursor.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Cursor object
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            return cursor
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error executing query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    def execute_and_commit(self, query: str, params: tuple = ()):
        """
        Execute a query and commit the transaction.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Cursor object
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error executing query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    def execute_many(self, query: str, params_list: List[tuple]):
        """
        Execute a query with multiple parameter sets.
        
        Args:
            query: SQL query
            params_list: List of parameter tuples
            
        Returns:
            Cursor object
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error executing many: {e}")
            logger.error(f"Query: {query}")
            raise
    
    def fetch_one(self, query: str, params: tuple = ()):
        """
        Execute a query and fetch one result.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Single row as a dictionary, or None if no results
        """
        cursor = self.execute(query, params)
        return cursor.fetchone()
    
    def fetch_all(self, query: str, params: tuple = ()):
        """
        Execute a query and fetch all results.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            List of rows as dictionaries
        """
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    def record_posted_video(self, video_data: Dict[str, Any], post_id: int):
        """
        Record a posted video in the database.
        
        Args:
            video_data: Video data dictionary
            post_id: Lemmy post ID
        """
        query = '''
            INSERT INTO posted_videos 
            (video_id, title, channel_name, channel_id, series_tag, youtube_url, lemmy_post_id, 
             priority_score, quality_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            video_data['video_id'],
            video_data['title'],
            video_data['channel_name'],
            video_data['channel_id'],
            video_data.get('series_tag', 'OTHER'),
            video_data['url'],
            post_id,
            video_data.get('priority_score', 0),
            video_data.get('quality_score', 0)
        )
        
        self.execute_and_commit(query, params)
        logger.info(f"Recorded posted video: {video_data['title']}")
    
    def record_lemmy_post(self, post_id: int, url: str, title: str):
        """
        Record a Lemmy post in the database.
        
        Args:
            post_id: Lemmy post ID
            url: Post URL
            title: Post title
        """
        query = '''
            INSERT OR IGNORE INTO lemmy_posts (post_id, url, title)
            VALUES (?, ?, ?)
        '''
        
        self.execute_and_commit(query, (post_id, url, title))
    
    def check_for_duplicates(self, video_id: str, title: str, channel_id: str, hours: int = 48) -> bool:
        """
        Check if a video is a duplicate.
        
        Args:
            video_id: YouTube video ID
            title: Video title
            channel_id: YouTube channel ID
            hours: Number of hours to check for duplicates
            
        Returns:
            True if the video is a duplicate, False otherwise
        """
        # Check if video ID already exists in posted_videos
        query = "SELECT COUNT(*) as count FROM posted_videos WHERE video_id = ?"
        result = self.fetch_one(query, (video_id,))
        
        if result and result['count'] > 0:
            logger.info(f"Duplicate detected (video already posted): {title}")
            return True
        
        # Check if URL exists in lemmy_posts
        query = "SELECT COUNT(*) as count FROM lemmy_posts WHERE url LIKE ?"
        result = self.fetch_one(query, (f"%{video_id}%",))
        
        if result and result['count'] > 0:
            logger.info(f"Duplicate detected (URL already in Lemmy): {title}")
            return True
        
        # Check for similar titles within the specified time period
        cutoff_time = datetime.now() - timedelta(hours=hours)
        title_hash = self.generate_title_hash(title)
        
        query = '''
            SELECT COUNT(*) as count 
            FROM duplicate_tracking 
            WHERE title_hash = ? AND channel_id = ? AND detected_at > ?
        '''
        
        result = self.fetch_one(query, (title_hash, channel_id, cutoff_time))
        
        if result and result['count'] > 0:
            logger.info(f"Duplicate detected (similar title within {hours} hours): {title}")
            return True
        
        # Record this video in duplicate tracking
        query = '''
            INSERT OR IGNORE INTO duplicate_tracking (video_id, title_hash, channel_id)
            VALUES (?, ?, ?)
        '''
        
        self.execute_and_commit(query, (video_id, title_hash, channel_id))
        return False
    
    def generate_title_hash(self, title: str) -> str:
        """
        Generate a hash for title similarity checking.
        
        Args:
            title: Video title
            
        Returns:
            Hash string
        """
        import re
        import hashlib
        
        # Normalize the title
        normalized = re.sub(r'[^\w\s]', '', title.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove common words
        common_words = [
            'highlights', 'race', 'qualifying', 'practice', 'session', 'live', 'full', 
            'rally', 'stage', 'wrc', 'special'
        ]
        
        words = [w for w in normalized.split() if w not in common_words]
        
        # Sort words to handle reordering
        content = ' '.join(sorted(words))
        
        # Generate hash
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def is_video_in_old_cache(self, video_id: str) -> bool:
        """
        Check if a video ID is in the old video cache.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if the video is in the cache, False otherwise
        """
        query = '''
            SELECT 1 FROM old_video_cache 
            WHERE video_id = ? AND expiry > datetime('now')
        '''
        
        result = self.fetch_one(query, (video_id,))
        return result is not None
    
    def add_video_to_old_cache(self, video_id: str, channel_id: str, is_livestream: bool = False, days: int = 30):
        """
        Add a video ID to the old video cache.
        
        Args:
            video_id: YouTube video ID
            channel_id: YouTube channel ID
            is_livestream: Whether the video is a livestream
            days: Number of days until expiry
        """
        # Skip caching if it's a livestream
        if is_livestream:
            return
        
        query = '''
            INSERT OR REPLACE INTO old_video_cache 
            (video_id, channel_id, cached_at, expiry) 
            VALUES (?, ?, datetime('now'), datetime('now', '+? days'))
        '''
        
        self.execute_and_commit(query, (video_id, channel_id, days))
    
    def update_bot_stats(self, posts_made: int, quota_used: int, errors: int, videos_processed: int):
        """
        Update daily bot statistics.
        
        Args:
            posts_made: Number of posts made
            quota_used: YouTube API quota used
            errors: Number of errors
            videos_processed: Number of videos processed
        """
        today = datetime.now().date()
        
        # Check if stats exist for today
        query = "SELECT * FROM bot_stats WHERE date = ?"
        result = self.fetch_one(query, (today,))
        
        if result:
            # Update existing stats
            query = '''
                UPDATE bot_stats 
                SET posts_made = posts_made + ?,
                    youtube_quota_used = youtube_quota_used + ?,
                    errors_count = errors_count + ?,
                    videos_processed = videos_processed + ?
                WHERE date = ?
            '''
            
            self.execute_and_commit(query, (posts_made, quota_used, errors, videos_processed, today))
        else:
            # Insert new stats
            query = '''
                INSERT INTO bot_stats 
                (date, posts_made, youtube_quota_used, errors_count, videos_processed)
                VALUES (?, ?, ?, ?, ?)
            '''
            
            self.execute_and_commit(query, (today, posts_made, quota_used, errors, videos_processed))
    
    def get_recent_posts_count(self, hours: int = 24) -> int:
        """
        Get count of posts made in recent hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Number of posts made
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        query = "SELECT COUNT(*) as count FROM posted_videos WHERE posted_at > ?"
        result = self.fetch_one(query, (cutoff_time,))
        
        return result['count'] if result else 0
    
    def get_youtube_quota_usage(self) -> int:
        """
        Get YouTube API quota usage for today.
        
        Returns:
            Quota used today
        """
        today = datetime.now().date()
        
        query = "SELECT youtube_quota_used FROM bot_stats WHERE date = ?"
        result = self.fetch_one(query, (today,))
        
        return result['youtube_quota_used'] if result else 0
    
    def log_error(self, error_type: str, error_message: str, module: str = None, function: str = None):
        """
        Log an error in the database.
        
        Args:
            error_type: Type of error
            error_message: Error message
            module: Module where the error occurred
            function: Function where the error occurred
        """
        query = '''
            INSERT INTO error_log (error_type, error_message, module, function)
            VALUES (?, ?, ?, ?)
        '''
        
        self.execute_and_commit(query, (error_type, error_message, module, function))
    
    def cleanup_old_data(self, days: int = 30):
        """
        Clean up old data from the database.
        
        Args:
            days: Number of days to keep data
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Clean up old duplicate tracking
        query = "DELETE FROM duplicate_tracking WHERE detected_at < ?"
        self.execute_and_commit(query, (cutoff_date,))
        
        # Clean up expired cache entries
        query = "DELETE FROM old_video_cache WHERE expiry < datetime('now')"
        self.execute_and_commit(query, ())
        
        # Clean up old error logs (only resolved ones)
        query = "DELETE FROM error_log WHERE resolved = 1 AND timestamp < ?"
        self.execute_and_commit(query, (cutoff_date,))
        
        # Vacuum the database to reclaim space
        conn = self.get_connection()
        conn.execute("VACUUM")
        conn.commit()
        
        logger.info("Database cleanup completed")
    
    def get_status_report(self) -> Dict[str, Any]:
        """
        Generate a status report.
        
        Returns:
            Dictionary with status information
        """
        # Get recent activity
        posts_last_day = self.get_recent_posts_count(24)
        posts_last_week = self.get_recent_posts_count(24 * 7)
        
        # Get top series
        query = '''
            SELECT series_tag, COUNT(*) as count 
            FROM posted_videos 
            WHERE posted_at > ? 
            GROUP BY series_tag 
            ORDER BY count DESC 
            LIMIT 5
        '''
        
        cutoff_date = datetime.now() - timedelta(days=30)
        top_series = self.fetch_all(query, (cutoff_date,))
        
        # Get average quality score
        query = '''
            SELECT AVG(quality_score) as avg_quality 
            FROM posted_videos 
            WHERE posted_at > ?
        '''
        
        cutoff_date = datetime.now() - timedelta(days=7)
        result = self.fetch_one(query, (cutoff_date,))
        avg_quality = result['avg_quality'] if result and result['avg_quality'] is not None else 0
        
        # Get error count
        query = "SELECT COUNT(*) as count FROM error_log WHERE resolved = 0"
        result = self.fetch_one(query)
        unresolved_errors = result['count'] if result else 0
        
        # Get quota usage
        quota_used = self.get_youtube_quota_usage()
        
        return {
            'posts_last_day': posts_last_day,
            'posts_last_week': posts_last_week,
            'top_series': [dict(row) for row in top_series] if top_series else [],
            'average_quality': round(avg_quality, 1),
            'unresolved_errors': unresolved_errors,
            'quota_used_today': quota_used,
            'last_updated': datetime.now().isoformat()
        }