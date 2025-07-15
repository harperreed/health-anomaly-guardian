# Health Anomaly Guardian 🛡️

[![CI](https://github.com/harperreed/health-anomaly-guardian/actions/workflows/ci.yml/badge.svg)](https://github.com/harperreed/health-anomaly-guardian/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)](https://github.com/harperreed/health-anomaly-guardian)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent health monitoring system that uses machine learning to detect anomalies in sleep data and alert you to potential health issues. Built with modern Python practices and comprehensive testing.

## ✨ Features

- **🤖 ML-Powered Detection**: Uses IsolationForest algorithm to identify unusual sleep patterns
- **📱 Multi-Device Support**: Automatically discovers and monitors multiple Emfit sleep sensors
- **🧠 AI Analysis**: Optional GPT-powered analysis of detected anomalies with health insights
- **📬 Smart Notifications**: Pushover integration for instant alerts
- **💾 Intelligent Caching**: Efficient API response caching with TTL management
- **🎨 Beautiful CLI**: Rich console interface with progress bars and colored output
- **🔧 Configurable**: Extensive configuration through environment variables

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/harperreed/health-anomaly-guardian.git
cd health-anomaly-guardian

# Install with uv (recommended)
uv sync

# Or install with pip
pip install -e .
```

### Configuration

Create a `.env` file with your API credentials:

```env
# Emfit API (choose one method)
EMFIT_TOKEN=your_emfit_api_token
# OR
EMFIT_USERNAME=your_username
EMFIT_PASSWORD=your_password

# Device Configuration (optional - auto-discovery enabled)
EMFIT_DEVICE_ID=single_device_id
# OR
EMFIT_DEVICE_IDS=device1,device2,device3

# Machine Learning Parameters
IFOREST_CONTAM=0.05           # Expected anomaly rate (5%)
IFOREST_TRAIN_WINDOW=90       # Training window in days
IFOREST_SHOW_N=5              # Number of recent outliers to show

# Optional Integrations
OPENAI_API_KEY=your_openai_key      # For AI-powered analysis
PUSHOVER_APIKEY=your_pushover_token # For notifications
PUSHOVER_USERKEY=your_pushover_user

# Caching Configuration
# Sleep data doesn't change once recorded, so cache is persistent by default
SLEEP_TRACKER_CACHE_ENABLED=true
SLEEP_TRACKER_CACHE_DIR=./cache
SLEEP_TRACKER_CACHE_TTL_HOURS=87600
```

### Usage

```bash
# Basic anomaly detection
uv run anomaly-detector

# Enable AI analysis of outliers
uv run anomaly-detector --gpt-analysis

# Send push notifications for today's anomalies
uv run anomaly-detector --alert

# Customize training parameters
uv run anomaly-detector --train-days 60 --contamination 0.1

# Discover available devices
uv run anomaly-detector --discover-devices

# Clear cache
uv run anomaly-detector --clear-cache
```

## 📊 How It Works

1. **Data Collection**: Fetches sleep metrics from Emfit API (heart rate, respiratory rate, sleep duration, etc.)
2. **ML Training**: Trains IsolationForest model on historical data to learn normal patterns
3. **Anomaly Detection**: Identifies days that deviate significantly from your normal sleep patterns
4. **AI Analysis**: Uses GPT to analyze why specific days were flagged as anomalous
5. **Alerts**: Sends notifications when current day shows anomalous patterns

## 🛠️ Development

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/harperreed/health-anomaly-guardian.git
cd health-anomaly-guardian

# Install development dependencies
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=anomaly_detector

# Run specific test categories
uv run pytest tests/test_detector.py -v
uv run pytest tests/test_e2e.py -v
```

### Code Quality

```bash
# Linting and formatting
uv run ruff check .
uv run ruff format .

# Security scanning
uv run safety check
uv run bandit -r anomaly_detector/
```

### Building

```bash
# Build package
uv build

# Test installation
pip install dist/*.whl
```

## 🏗️ Architecture

```
anomaly_detector/
├── __init__.py         # Package exports
├── cli.py             # Command-line interface
├── detector.py        # Main ML detection logic
├── cache.py           # API response caching
├── config.py          # Environment configuration
└── exceptions.py      # Custom exception classes

tests/
├── conftest.py        # Pytest fixtures
├── test_*.py          # Unit tests
└── test_e2e.py        # End-to-end tests
```

## 🔧 Configuration Reference

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `EMFIT_TOKEN` | - | Emfit API token (preferred method) |
| `EMFIT_USERNAME` | - | Emfit username (alternative) |
| `EMFIT_PASSWORD` | - | Emfit password (alternative) |
| `EMFIT_DEVICE_ID` | - | Single device ID |
| `EMFIT_DEVICE_IDS` | - | Comma-separated device IDs |
| `IFOREST_CONTAM` | 0.05 | Expected anomaly contamination rate |
| `IFOREST_TRAIN_WINDOW` | 90 | Training window in days |
| `IFOREST_SHOW_N` | 5 | Number of recent outliers to display |
| `OPENAI_API_KEY` | - | OpenAI API key for analysis |
| `PUSHOVER_APIKEY` | - | Pushover API token |
| `PUSHOVER_USERKEY` | - | Pushover user key |
| `SLEEP_TRACKER_CACHE_ENABLED` | true | Enable API response caching |
| `SLEEP_TRACKER_CACHE_DIR` | ./cache | Cache directory path |
| `SLEEP_TRACKER_CACHE_TTL_HOURS` | 87600 | Cache TTL in hours (10 years - persistent) |

## 📈 CI/CD

The project includes comprehensive GitHub Actions workflows:

- **Continuous Integration**: Automated testing, linting, and security scanning
- **Multi-Environment Testing**: Python 3.13 testing matrix
- **Code Coverage**: 85% coverage with detailed reporting
- **Security Scanning**: Bandit and Safety security analysis
- **Package Building**: Automated wheel and source distribution building
- **End-to-End Testing**: Optional E2E tests with real API integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure they pass (`uv run pytest`)
5. Commit with conventional commits (`git commit -m 'feat: add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Emfit](https://www.emfit.com/) for sleep tracking technology
- [scikit-learn](https://scikit-learn.org/) for machine learning algorithms
- [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- [uv](https://github.com/astral-sh/uv) for fast Python package management

---

**⚠️ Health Disclaimer**: This tool is for informational purposes only and should not be used as a substitute for professional medical advice. Always consult with healthcare professionals for medical concerns.
