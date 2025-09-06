# BlueFlagBot

A bot that posts auto racing and motorsport videos to Lemmy.

## Overview

BlueFlagBot monitors YouTube channels for new racing videos, scores them based on content relevance, and posts the best ones to a Lemmy community. It uses a configuration-based approach that gives you direct control over which channels to monitor and how to tag their content.

## Features

- **Channel Configuration**: Define which YouTube channels to monitor and how to tag their content
- **Content Scoring**: Automatically filter and prioritize videos based on content relevance
- **Tag Assignment**: Assign primary and secondary tags to channels
- **Duplicate Detection**: Avoid posting the same video multiple times
- **Scheduled Content**: Handle upcoming live streams and premieres
- **API Quota Management**: Efficiently use the YouTube API quota
- **Daemon Process**: Run as a background service with PID management

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/frostytrichs/bfb-rev-2
   cd bfb-rev-2
   ```

2. Run the installation script:
   ```
   python3 install.py
   ```

   The installation script will:
   - Create necessary directories
   - Install required dependencies
   - Set up authentication for YouTube and Lemmy
   - Initialize the database
   - Create default configuration files

3. Configure your channels:
   - Edit `channels.json` to add the YouTube channels you want to monitor

4. Configure the bot settings:
   - Edit `config.ini` to adjust settings like scan intervals, posting limits, etc.

## Usage

### Starting the Bot

```
python3 blueflagbot.py start
```

### Stopping the Bot

```
python3 blueflagbot.py stop
```

### Checking Status

```
python3 blueflagbot.py status
```

### Restarting the Bot

```
python3 blueflagbot.py restart
```

### Running a Single Scan

```
python3 blueflagbot.py run-once
```

This will run a single scan cycle without starting the daemon process.

## Configuration

### Main Configuration File

The main configuration file is `config.ini`. It contains settings for:

- General bot settings
- YouTube API settings
- Lemmy API settings
- Channel configuration settings
- Content scoring settings
- Error handling and retry settings
- Database settings

### Channel Configuration

Channels are configured in `channels.json`. Each channel entry includes:

- `name`: A human-readable name for the channel
- `channelID`: The YouTube channel ID
- `primary_tag`: The default tag to use for videos from this channel
- `secondary_tags`: Optional array of tags that may override the primary tag based on video content

### Content Scoring

Videos are scored based on keywords in their title and description. The keywords are defined in JSON files in the `keywords` directory, with separate files for different languages.

The scoring system uses categories like:
- `auto_reject`: Keywords that automatically reject a video
- `race_content`: Keywords indicating race content
- `analysis_content`: Keywords indicating analysis content
- `quality_boosters`: Keywords indicating high-quality content
- `warning_signs`: Keywords indicating potentially low-quality content

## Directory Structure

```
bfb-rev-2/
├── blueflagbot.py         # Main entry point with daemon functionality
├── config.ini             # Main configuration file
├── channels.json          # Channel configuration
├── install.py             # Installation script
├── keywords/              # Keyword files directory
│   └── en.json            # English keywords
├── src/                   # Source code directory
│   ├── api/               # API clients
│   │   ├── lemmy.py       # Lemmy API client
│   │   └── youtube.py     # YouTube API client
│   ├── core/              # Core functionality
│   │   ├── bot.py         # Main bot logic
│   │   ├── daemon.py      # Daemon implementation
│   │   ├── database.py    # Database management
│   │   └── scoring.py     # Content scoring system
│   └── utils/             # Utility functions
│       ├── config.py      # Configuration management
│       ├── logging.py     # Logging setup
│       └── pid.py         # PID file management
├── credentials/           # Authentication credentials (created during installation)
├── data/                  # Database and other data files (created during installation)
└── logs/                  # Log files directory (created during installation)
```

## Requirements

- Python 3.6 or higher
- YouTube Data API v3 credentials
- Lemmy account