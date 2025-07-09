# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a modular sleep anomaly detection system that monitors sleep data using IsolationForest machine learning algorithms. Uses a plugin architecture to support multiple sleep tracking systems including Emfit, Oura, and Eight Sleep. The system fetches data from APIs, analyzes it for anomalies, and provides alerts via Pushover notifications with optional GPT analysis.

## Common Commands

### Development
- `uv run main.py` - Run the main anomaly detection
- `uv run main.py --help` - Show all command line options
- `uv run main.py --train-days 30` - Use 30 days of training data
- `uv run main.py --alert` - Send push alerts for anomalies
- `uv run main.py --gpt-analysis` - Enable GPT analysis for outliers
- `uv run main.py --plugin emfit` - Use Emfit plugin (default)
- `uv run main.py --plugin oura` - Use Oura plugin
- `uv run main.py --plugin eight` - Use Eight Sleep plugin
- `uv run main.py --list-plugins` - List available plugins
- `uv run main.py --discover-devices` - Show device discovery info
- `uv run main.py --clear-cache` - Clear all cached API data
- `uv run main.py --force-outlier 2024-01-15` - Force a date as outlier for testing

### Code Quality
- `uv run ruff check .` - Run linting
- `uv run ruff format .` - Format code
- `uv run pytest` - Run tests (note: no test files exist yet)

### Pre-commit Hooks
- `pre-commit run --all-files` - Run all pre-commit hooks
- `pre-commit install` - Install pre-commit hooks

## Architecture

### Package Structure

```
anomaly_detector/
├── __init__.py          # Package exports and version info
├── exceptions.py        # Custom exception classes (ConfigError, APIError, DataError)
├── config.py           # Environment variable utilities (get_env_var, get_env_int, get_env_float)
├── cache.py            # CacheManager class for API response caching
├── detector.py         # SleepAnomalyDetector main class
├── cli.py              # Command-line interface and main entry point
└── plugins/            # Plugin system for sleep trackers
    ├── __init__.py     # PluginManager and SleepTrackerPlugin base class
    ├── emfit.py        # Emfit sleep tracker plugin
    ├── oura.py         # Oura ring plugin
    └── eight.py        # Eight Sleep plugin

main.py                 # Simple entry point that imports from package
```

### Core Components

1. **SleepAnomalyDetector Class** (`anomaly_detector/detector.py`)
   - Main class encapsulating all detection functionality
   - Instance-based configuration management
   - Plugin-based architecture for sleep tracker support
   - Clean separation of concerns with focused methods

2. **Configuration System** (`anomaly_detector/config.py`)
   - Environment variable validation with type checking
   - Utility functions for type-safe config loading
   - Support for both token-based and username/password authentication

3. **Caching System** (`anomaly_detector/cache.py`)
   - `CacheManager` class for JSON-based API response caching
   - TTL-based cache expiration and cleanup
   - Cache statistics and performance monitoring

4. **Exception Handling** (`anomaly_detector/exceptions.py`)
   - Custom exception classes for different error types
   - Clear separation between config, API, and data processing errors

5. **CLI Interface** (`anomaly_detector/cli.py`)
   - Command-line argument parsing
   - Environment setup and logging configuration
   - Main entry point orchestration

### Key Features

- **Multi-device Support**: Automatically discovers and processes multiple Emfit devices
- **Intelligent Caching**: Reduces API calls with TTL-based JSON caching
- **Flexible Configuration**: Environment variables for all settings
- **Rich Output**: Beautiful console output with progress bars and tables
- **AI Analysis**: Optional GPT-o3 analysis of sleep anomalies
- **Alert System**: Push notifications via Pushover for anomalies

### Environment Configuration

The system requires configuration via environment variables (see `.env.example`):
- Emfit API credentials (token or username/password)
- Device IDs (auto-discovered or manually configured)
- IsolationForest parameters (contamination rate, training window)
- Optional: Pushover credentials, OpenAI API key, cache settings

### Data Flow

1. CLI (`cli.py`) creates `SleepAnomalyDetector` instance and loads configuration
2. Authenticate with sleep device API via `get_emfit_api()`
3. Discover or use configured device IDs via `get_device_ids()`
4. For each device, call `run_single_device()`:
   - Fetch sleep data with `fetch_emfit_api_data()` (with caching)
   - Preprocess data with `preprocess()` (handle missing values, clip outliers)
   - Train IsolationForest model with `fit_iforest()`
   - Generate results with `display_results()`
   - Send alerts via `notify()` if anomalies detected

### Modular Benefits

- **Single Responsibility**: Each module has one clear purpose (~50-200 lines each)
- **Testability**: Easy to mock dependencies and test individual modules
- **Maintainability**: Clear separation of concerns across files
- **Reusability**: Components can be imported independently
- **Extensibility**: Easy to add support for other sleep tracking systems
- **Collaboration**: Multiple developers can work on different modules

## Development Notes

- Uses `uv` for dependency management
- Rich console library for beautiful CLI output
- Modular package architecture with focused single-responsibility modules
- Comprehensive error handling with custom exception classes
- Caching system to minimize API calls during development
- Pre-commit hooks enforce code quality with ruff and pytest
- No test files exist yet - this should be addressed for TDD workflow

## Usage as a Package

```python
from anomaly_detector import SleepAnomalyDetector, CacheManager
from rich.console import Console

# Create detector instance
console = Console()
detector = SleepAnomalyDetector(console)

# Run analysis
detector.run(window=30, contamin=0.05, n_out=5, alert=False)
```
