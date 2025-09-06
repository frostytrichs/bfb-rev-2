# User Guide

This guide explains how to set up and use the Lemmy Bot.

## Installation

1. Ensure you have Python 3.8 or newer installed.

2. Clone the repository:
   ```bash
   git clone https://github.com/frostytrichs/bfb-rev-2.git
   cd bfb-rev-2
   ```

3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The bot can be configured using either a configuration file or environment variables.

### Using a Configuration File

1. Create a configuration file:
   ```bash
   mkdir -p config
   python -c "from src.config import create_default_config; create_default_config('config/config.json')"
   ```

2. Edit the configuration file (`config/config.json`) with your preferred text editor:
   ```json
   {
     "instance": "https://lemmy.world",
     "username": "your_username",
     "password": "your_password",
     "log_level": "INFO",
     "features": {
       "auto_post": false,
       "auto_reply": false
     }
   }
   ```

### Using Environment Variables

You can also configure the bot using environment variables:

```bash
export LEMMY_INSTANCE="https://lemmy.world"
export LEMMY_USERNAME="your_username"
export LEMMY_PASSWORD="your_password"
export LEMMY_BOT_LOG_LEVEL="INFO"
```

Environment variables take precedence over the configuration file.

## Running the Bot

To run the bot:

```bash
python -m src.bot --config config/config.json
```

If you're using environment variables, you can omit the `--config` parameter:

```bash
python -m src.bot
```

## Features

*Note: This section will be expanded as features are implemented.*

### Automated Posting

*Details will be added during development.*

### Comment Monitoring and Replies

*Details will be added during development.*

## Troubleshooting

### Common Issues

*This section will be expanded during development.*

### Logs

The bot logs its activity to the console by default. You can change the log level in the configuration file or using the `LEMMY_BOT_LOG_LEVEL` environment variable.

Valid log levels are:
- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

## Getting Help

If you encounter issues or have questions, please open an issue on the GitHub repository:
https://github.com/frostytrichs/bfb-rev-2/issues