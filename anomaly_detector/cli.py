"""
ABOUTME: Command-line interface for the sleep anomaly detector
ABOUTME: Handles argument parsing and main entry point functionality
"""

import argparse
import logging
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from rich.console import Console
    from rich.logging import RichHandler

    # Initialize Rich console
    console = Console()
except ImportError:
    # Fallback console for testing
    class FakeConsole:
        def print(self, *args, **kwargs):
            pass

    console = FakeConsole()
    RichHandler = None


def load_environment():
    """Load environment variables with error handling."""
    try:
        env_path = Path(".env")
        if env_path.exists() and load_dotenv is not None:
            load_dotenv(env_path)
            # Only print if not in test mode
            if "pytest" not in sys.modules:
                console.print(f"✅ Loaded environment from {env_path}")
        else:
            # Only print if not in test mode
            if "pytest" not in sys.modules:
                console.print(
                    "⚠️  No .env file found, using system environment variables"
                )
    except Exception as e:
        if "pytest" not in sys.modules:
            console.print(f"❌ Error loading .env file: {e}")
        sys.exit(1)


def cli() -> argparse.Namespace:
    """
    Parse and return command-line arguments for the sleep anomaly detection CLI tool.

    Returns:
        argparse.Namespace: Parsed arguments controlling plugin selection, training window, anomaly detection parameters, output options, cache management, device discovery, and plugin listing.
    """
    p = argparse.ArgumentParser(
        description="Sleep data anomaly detection using IsolationForest"
    )
    p.add_argument(
        "--plugin",
        type=str,
        default="emfit",
        help="Sleep tracker plugin to use (emfit, oura, eight)",
    )
    p.add_argument(
        "--train-days",
        type=int,
        default=90,
        help="Training window length",
    )
    p.add_argument(
        "--contamination",
        type=float,
        default=0.05,
        help="Expected anomaly fraction",
    )
    p.add_argument(
        "--show-n",
        type=int,
        default=5,
        help="How many recent outlier days to print",
    )
    p.add_argument(
        "--alert", action="store_true", help="Push alert if *today* is outlier"
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level",
    )
    p.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all cached data before running",
    )
    p.add_argument(
        "--no-cache", action="store_true", help="Disable caching for this run"
    )
    p.add_argument(
        "--gpt-analysis",
        action="store_true",
        help="Enable GPT-o3 analysis for historical outliers (latest day anomalies analyzed automatically)",
    )
    p.add_argument(
        "--discover-devices",
        action="store_true",
        help="Show user info to help discover device IDs",
    )
    p.add_argument(
        "--manual-devices",
        action="store_true",
        help="Use manual device configuration instead of auto-discovery",
    )
    p.add_argument(
        "--force-outlier",
        type=str,
        help="Force a specific date (YYYY-MM-DD) to be marked as an outlier for testing",
    )
    p.add_argument(
        "--list-plugins",
        action="store_true",
        help="List all available sleep tracker plugins",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format instead of rich console tables",
    )
    p.add_argument(
        "--version",
        action="version",
        version="Sleep Anomaly Detector 1.0.0",
    )
    return p.parse_args()


def main():
    """
    Execute the main entry point for the sleep anomaly detection CLI tool.

    Parses command-line arguments, configures environment and logging, manages plugin selection, cache, and device discovery, and runs the anomaly detection process. Handles special CLI flags for listing plugins, clearing cache, and device discovery, exiting after completing the requested operation or upon error or interruption.
    """
    try:
        # Debug output for testing
        if "pytest" in sys.modules:
            print(f"DEBUG: About to parse args: {sys.argv}", file=sys.stderr)
        a = cli()
        if "pytest" in sys.modules:
            print(f"DEBUG: Args parsed successfully: {a}", file=sys.stderr)
    except SystemExit as e:
        # Re-raise SystemExit to allow proper handling of --help, --version, and invalid args
        if "pytest" in sys.modules:
            print(f"DEBUG: SystemExit caught with code: {e.code}", file=sys.stderr)
        raise

    # Load environment after argument parsing
    load_environment()

    # Override cache settings from CLI args
    if a.no_cache:
        os.environ["SLEEP_TRACKER_CACHE_ENABLED"] = "false"

    # Set up rich logging
    if RichHandler is not None:
        logging.basicConfig(
            level=getattr(logging, a.log_level),
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=console, rich_tracebacks=True)],
        )
    else:
        logging.basicConfig(
            level=getattr(logging, a.log_level),
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    try:
        # Import detector here to avoid issues during CLI parsing
        from .detector import SleepAnomalyDetector

        # Create detector instance with selected plugin
        detector = SleepAnomalyDetector(console, a.plugin)

        # Handle plugin listing
        if a.list_plugins:
            console.print(
                f"🔌 Available sleep tracker plugins: {detector.plugin_manager.list_plugins()}"
            )
            console.print(f"🔌 Current plugin: {detector.plugin_name}")
            sys.exit(0)

        # Handle cache clearing
        if a.clear_cache:
            cleared_count = detector.clear_cache()
            console.print(f"🗑️  Cleared {cleared_count} cache files")
            if not any(
                [
                    a.train_days != detector.window_env,
                    a.contamination != detector.contam_env,
                    a.show_n != detector.n_out_env,
                ]
            ):
                # If only clearing cache, exit
                sys.exit(0)

        # Handle device discovery
        if a.discover_devices:
            try:
                detector.discover_devices()
                sys.exit(0)
            except Exception as e:
                console.print(f"❌ Failed to fetch user info: {e}")
                sys.exit(1)

        detector.run(
            a.train_days,
            a.contamination,
            a.show_n,
            a.alert,
            a.gpt_analysis,
            not a.manual_devices,
            a.force_outlier,
            a.json,
        )
    except KeyboardInterrupt:
        console.print("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as exc:
        console.print(f"❌ Fatal error: {exc}")
        logging.exception("Fatal error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
