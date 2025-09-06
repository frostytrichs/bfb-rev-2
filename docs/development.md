# Development Guide

This document provides information for developers working on the Lemmy Bot project.

## Project Structure

```
bfb-rev-2/
├── docs/               # Documentation
├── src/                # Source code
│   ├── __init__.py     # Package marker
│   ├── bot.py          # Main bot class
│   ├── config.py       # Configuration management
│   └── lemmy_api.py    # Lemmy API client
├── tests/              # Test cases
│   ├── __init__.py     # Package marker
│   └── test_config.py  # Tests for configuration
├── .gitignore          # Git ignore file
├── README.md           # Project overview
└── requirements.txt    # Python dependencies
```

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/frostytrichs/bfb-rev-2.git
   cd bfb-rev-2
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a configuration file:
   ```bash
   # Create a config directory
   mkdir -p config
   
   # Create a default config file
   python -c "from src.config import create_default_config; create_default_config('config/config.json')"
   ```

5. Edit the configuration file with your Lemmy credentials.

## Running Tests

Run the test suite using pytest:

```bash
pytest
```

## Code Style

This project follows the PEP 8 style guide. We use Black for code formatting and Flake8 for linting.

Format code with Black:
```bash
black src tests
```

Check code with Flake8:
```bash
flake8 src tests
```

## Adding Features

When adding new features:

1. Create a new branch for your feature
2. Write tests for the new functionality
3. Implement the feature
4. Ensure all tests pass
5. Format and lint your code
6. Submit a pull request

## Documentation

Please document all functions, classes, and modules using docstrings. We follow the Google docstring format.

Example:
```python
def function_name(param1, param2):
    """Short description of the function.
    
    Longer description explaining the function in detail.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of the return value
        
    Raises:
        ExceptionType: When and why this exception is raised
    """
    # Function implementation
```