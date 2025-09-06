#!/usr/bin/env python3
"""
Tests for the content scoring module.
"""

import os
import sys
import json
import pytest
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import the src package
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.scoring import ContentScorer, RacingSeriesDetector


def test_content_scorer_initialization():
    """Test initializing the content scorer."""
    # Create a minimal config
    config = {
        "keywords": {
            "en": {
                "auto_reject": ["shorts", "podcast"],
                "race_content": ["race", "qualifying"],
                "analysis_content": ["analysis", "review"],
                "quality_boosters": ["official", "live"],
                "warning_signs": ["reaction", "rumor"]
            }
        },
        "filtering": {
            "min_quality_threshold": 65,
            "livestream_quality_threshold": 60
        }
    }
    
    scorer = ContentScorer(config)
    
    # Check that the scorer was initialized correctly
    assert scorer.min_quality_threshold == 65
    assert scorer.livestream_quality_threshold == 60
    assert "auto_reject" in scorer.active_keywords
    assert "race_content" in scorer.active_keywords


def test_calculate_content_quality_score():
    """Test calculating content quality score."""
    # Create a minimal config
    config = {
        "keywords": {
            "en": {
                "auto_reject": ["shorts", "podcast"],
                "race_content": ["race", "qualifying"],
                "analysis_content": ["analysis", "review"],
                "quality_boosters": ["official", "live"],
                "warning_signs": ["reaction", "rumor"]
            }
        },
        "filtering": {
            "min_quality_threshold": 65,
            "livestream_quality_threshold": 60
        }
    }
    
    scorer = ContentScorer(config)
    
    # Test a high-quality video
    high_quality_video = {
        "title": "Official Race Highlights - Round 5",
        "description": "Watch the full race highlights from round 5 of the championship.",
        "published_at": datetime.now(),
        "view_count": 5000
    }
    
    score = scorer.calculate_content_quality_score(high_quality_video)
    assert score > 65
    
    # Test a low-quality video
    low_quality_video = {
        "title": "My reaction to the race",
        "description": "Just sharing my thoughts on the race.",
        "published_at": datetime.now(),
        "view_count": 100
    }
    
    score = scorer.calculate_content_quality_score(low_quality_video)
    assert score < 65
    
    # Test auto-reject
    auto_reject_video = {
        "title": "Race highlights #shorts",
        "description": "Quick highlights from the race.",
        "published_at": datetime.now(),
        "view_count": 1000
    }
    
    score = scorer.calculate_content_quality_score(auto_reject_video)
    assert score == 0


def test_racing_series_detector():
    """Test the racing series detector."""
    config = {
        "channels": [
            {
                "name": "Formula 1",
                "channelID": "UCB_qr75-ydFVKSF9Dmo6izg",
                "primary_tag": "F1",
                "secondary_tags": ["F2", "F3", "F1A"]
            },
            {
                "name": "World Rally Championship",
                "channelID": "UC5G6kTnHXDz0WIBC2VGBOqg",
                "primary_tag": "WRC",
                "secondary_tags": ["WRC2", "JWRC", "RALLY"]
            }
        ]
    }
    
    detector = RacingSeriesDetector(config)
    
    # Test F1 video
    f1_video = {
        "channel_id": "UCB_qr75-ydFVKSF9Dmo6izg",
        "title": "Race Highlights - 2023 Monaco Grand Prix",
        "description": "All the action from the streets of Monaco."
    }
    
    tag, priority = detector.detect_series_and_tag(f1_video)
    assert tag == "F1"
    
    # Test WRC2 video
    wrc2_video = {
        "channel_id": "UC5G6kTnHXDz0WIBC2VGBOqg",
        "title": "WRC2 Highlights - Rally Finland",
        "description": "The best action from WRC2 in Finland."
    }
    
    tag, priority = detector.detect_series_and_tag(wrc2_video)
    assert tag == "WRC2"