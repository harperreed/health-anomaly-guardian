"""
ABOUTME: Command-line interface for the sleep anomaly detector
ABOUTME: Handles argument parsing and main entry point functionality
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler

from .detector import SleepAnomalyDetector

# Initialize Rich console
console = Console()

# Load environment variables with error handling
try:
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)
        console.print(f"✅ Loaded environment from {env_path}")
    else:
        console.print("⚠️  No .env file found, using system environment variables")
except Exception as e:
    console.print(f"❌ Error loading .env file: {e}")
    sys.exit(1)


def cli() -> argparse.Namespace:
    """Parse command line arguments."""
    # Create a temporary detector instance just to get default values
    temp_detector = SleepAnomalyDetector(console)

    p = argparse.ArgumentParser(
        description="Sleep data anomaly detection using IsolationForest"
    )
    p.add_argument(
        "--train-days",
        type=int,
        default=temp_detector.window_env,
        help="Training window length",
    )
    p.add_argument(
        "--contamination",
        type=float,
        default=temp_detector.contam_env,
        help="Expected anomaly fraction",
    )
    p.add_argument(
        "--show-n",
        type=int,
        default=temp_detector.n_out_env,
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
    return p.parse_args()


def main():
    """Main entry point for the CLI."""
    a = cli()

    # Override cache settings from CLI args
    if a.no_cache:
        os.environ["EMFIT_CACHE_ENABLED"] = "false"

    # Set up rich logging
    logging.basicConfig(
        level=getattr(logging, a.log_level),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )

    try:
        # Create detector instance
        detector = SleepAnomalyDetector(console)

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
