"""
ABOUTME: Main SleepAnomalyDetector class for sleep data anomaly detection
ABOUTME: Uses IsolationForest ML algorithm to detect anomalies in sleep device data
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from .cache import CacheManager
from .config import get_env_float, get_env_int, get_env_var
from .exceptions import APIError, ConfigError, DataError
from .plugins import PluginManager


class SleepAnomalyDetector:
    """Sleep data anomaly detection using IsolationForest."""

    def __init__(self, console: Console, plugin_name: str = None):
        """
        Initialize the SleepAnomalyDetector with the specified console and plugin.
        
        Parameters:
            console (Console): The console instance for output and user interaction.
            plugin_name (str, optional): The name of the sleep tracker plugin to use. If not provided, the default plugin is selected.
        
        Loads configuration from environment variables and sets up the plugin manager.
        """
        self.console = console
        self.plugin_manager = PluginManager(console)
        self._load_config(plugin_name)

    def _load_config(self, plugin_name: str = None):
        """
        Load and validate configuration settings from environment variables, including anomaly detection parameters, notification credentials, cache options, OpenAI API key, and plugin selection.
        
        Raises:
            ConfigError: If required configuration values are missing or invalid.
            Exits the program on configuration errors.
        """
        try:
            # Core anomaly detection config
            self.contam_env = get_env_float("IFOREST_CONTAM", 0.05)
            self.window_env = get_env_int("IFOREST_TRAIN_WINDOW", 90)
            self.n_out_env = get_env_int("IFOREST_SHOW_N", 5)
            
            # Notification config
            self.pushover_token = get_env_var("PUSHOVER_APIKEY")
            self.pushover_user = get_env_var("PUSHOVER_USERKEY")

            # Cache config (now generic, not Emfit-specific)
            self.cache_dir = Path(get_env_var("SLEEP_TRACKER_CACHE_DIR", "./cache"))
            self.cache_enabled = (
                get_env_var("SLEEP_TRACKER_CACHE_ENABLED", "true").lower() == "true"
            )
            self.cache_ttl_hours = get_env_int("SLEEP_TRACKER_CACHE_TTL_HOURS", 24)

            # OpenAI config
            self.openai_api_key = get_env_var("OPENAI_API_KEY")
            
            # Plugin selection
            self.plugin_name = plugin_name or get_env_var("SLEEP_TRACKER_PLUGIN", "emfit")
            
            # Load the selected plugin
            self.plugin = self.plugin_manager.get_plugin(self.plugin_name)
            if not self.plugin:
                available_plugins = self.plugin_manager.list_plugins()
                raise ConfigError(
                    f"Plugin '{self.plugin_name}' not found. Available plugins: {available_plugins}"
                )

            # Validate contamination range
            if not 0.0 < self.contam_env < 1.0:
                raise ConfigError(
                    f"IFOREST_CONTAM must be between 0 and 1, got {self.contam_env}"
                )

            # Validate window size
            if self.window_env < 7:
                raise ConfigError(
                    f"IFOREST_TRAIN_WINDOW must be at least 7 days, got {self.window_env}"
                )

        except ConfigError as e:
            self.console.print(f"❌ Configuration error: {e}")
            sys.exit(1)

    def get_api_client(self):
        """
        Returns an authenticated API client instance from the selected sleep tracker plugin.
        """
        return self.plugin.get_api_client()

    def get_device_ids(self, auto_discover: bool = True) -> tuple[list[str], dict[str, str]]:
        """
        Retrieve device IDs and their corresponding names from the selected plugin.
        
        Parameters:
        	auto_discover (bool): Whether to automatically discover devices using the plugin.
        
        Returns:
        	A tuple containing a list of device IDs and a dictionary mapping device IDs to device names.
        """
        return self.plugin.get_device_ids(auto_discover)

    def fetch_sleep_data(
        self,
        device_id: str,
        start_date: datetime,
        end_date: datetime,
        cache: CacheManager,
    ) -> pd.DataFrame:
        """
        Fetches sleep data for a specified device and date range using the configured sleep tracker plugin.
        
        Parameters:
            device_id (str): The unique identifier of the sleep tracking device.
            start_date (datetime): The start date of the data retrieval period.
            end_date (datetime): The end date of the data retrieval period.
        
        Returns:
            pd.DataFrame: A DataFrame containing the retrieved sleep data for the specified device and date range.
        """
        return self.plugin.fetch_data(device_id, start_date, end_date, cache)

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocesses sleep data by filling missing numeric values with medians and clipping extreme outliers.
        
        Numeric columns (excluding "date") with missing values are filled using their median. Outliers beyond five standard deviations from the mean are clipped to within this range. Raises a DataError if preprocessing fails.
        
        Returns:
            pd.DataFrame: The processed DataFrame with missing values filled and outliers clipped.
        """
        try:
            original_shape = df.shape

            # Fill missing values with median
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if "date" in numeric_cols:
                numeric_cols.remove("date")

            missing_counts = df[numeric_cols].isnull().sum()
            if missing_counts.sum() > 0:
                self.console.print(
                    f"⚠️  Filling {missing_counts.sum()} missing values with median"
                )

            df_processed = df.copy()
            df_processed[numeric_cols] = df_processed[numeric_cols].fillna(
                df_processed[numeric_cols].median()
            )

            # Clip outliers (5 standard deviations)
            outlier_counts = {}
            for col in numeric_cols:
                s = df_processed[col]
                if s.std() > 0:  # Avoid division by zero
                    lim = 5 * s.std(ddof=0)
                    original_values = s.copy()
                    df_processed[col] = s.clip(s.mean() - lim, s.mean() + lim)
                    outlier_counts[col] = (original_values != df_processed[col]).sum()

            total_outliers = sum(outlier_counts.values())
            if total_outliers > 0:
                self.console.print(f"⚠️  Clipped {total_outliers} outlier values")

            self.console.print(
                f"✅ Preprocessed data: {original_shape[0]} rows, {original_shape[1]} columns"
            )
            return df_processed

        except Exception as e:
            raise DataError(f"Error preprocessing data: {e}") from e

    def fit_iforest(self, X: np.ndarray, contamination: float) -> IsolationForest:
        """Fit IsolationForest model on the data."""
        try:
            if X.shape[0] < 10:
                raise DataError(
                    f"Insufficient data for anomaly detection: {X.shape[0]} samples (need at least 10)"
                )

            with self.console.status("[bold green]Training IsolationForest model..."):
                model = IsolationForest(
                    n_estimators=256,
                    contamination=contamination,
                    random_state=42,
                    n_jobs=-1,  # Use all available cores
                ).fit(X)

            self.console.print(
                f"✅ Trained IsolationForest on {X.shape[0]} samples with {X.shape[1]} features"
            )
            return model

        except Exception as e:
            if isinstance(e, DataError):
                raise
            raise DataError(f"Error training IsolationForest: {e}") from e

    def notify(self, msg: str) -> None:
        """
        Sends a push notification with the specified message via Pushover if credentials are configured.
        
        If Pushover credentials are missing, the notification is skipped and a warning is printed.
        """
        if not (self.pushover_token and self.pushover_user):
            self.console.print("⚠️  No Pushover credentials – alert skipped")
            return

        try:
            import requests  # lazy import

            with self.console.status("[bold green]Sending Pushover notification..."):
                response = requests.post(
                    "https://api.pushover.net/1/messages.json",
                    data={
                        "token": self.pushover_token,
                        "user": self.pushover_user,
                        "message": msg,
                        "title": self.plugin.notification_title,
                    },
                    timeout=10,
                )
                response.raise_for_status()

            self.console.print("✅ Pushover notification sent successfully")

        except requests.exceptions.RequestException as e:
            self.console.print(f"❌ Pushover notification failed: {e}")
            logging.error(f"Pushover API error: {e}")
        except Exception as e:
            self.console.print(f"❌ Unexpected error sending notification: {e}")
            logging.error(f"Notification error: {e}")

    def analyze_outlier_with_gpt(
        self, outlier_row: pd.Series, df: pd.DataFrame
    ) -> str | None:
        """Use GPT-o3 to analyze why a specific day is an outlier."""
        if not self.openai_api_key:
            self.console.print("⚠️  No OpenAI API key – GPT analysis skipped")
            return None

        try:
            # Calculate percentiles for context
            percentiles = {}
            for col in ["hr", "rr", "sleep_dur", "score"]:
                if col in df.columns:
                    percentiles[col] = {
                        "p10": df[col].quantile(0.1),
                        "p25": df[col].quantile(0.25),
                        "p50": df[col].quantile(0.5),
                        "p75": df[col].quantile(0.75),
                        "p90": df[col].quantile(0.9),
                        "mean": df[col].mean(),
                        "std": df[col].std(),
                    }

            # Create the prompt
            prompt = f"""Analyze this sleep data anomaly detected by IsolationForest:

**Outlier Day ({outlier_row.date.date()}):**
- Heart Rate: {outlier_row.hr:.1f} bpm
- Respiratory Rate: {outlier_row.rr:.1f} breaths/min
- Sleep Duration: {outlier_row.sleep_dur:.1f} hours
- Sleep Score: {outlier_row.score:.1f}
- Anomaly Score: {outlier_row.if_score:.4f} (more negative = more anomalous)

**Historical Context ({len(df)} days):**
"""

            for metric, stats in percentiles.items():
                current_val = getattr(outlier_row, metric)
                prompt += f"""
{metric.upper()}:
- Current: {current_val:.1f}
- Mean: {stats["mean"]:.1f} (±{stats["std"]:.1f})
- Percentiles: P10={stats["p10"]:.1f}, P25={stats["p25"]:.1f}, P50={stats["p50"]:.1f}, P75={stats["p75"]:.1f}, P90={stats["p90"]:.1f}
"""

            prompt += """
Please provide a concise analysis (2-3 sentences) explaining why this day was flagged as an outlier. Focus on which metrics are most unusual compared to the historical patterns and what this might indicate about sleep quality or health patterns. Your analysis should be insightful and actionable, providing recommendations for further investigation or intervention if necessary - specifically around sickness, cold, or health issues."""

            # Call OpenAI API
            with self.console.status("[bold green]Analyzing outlier with GPT-o3..."):
                client = OpenAI(api_key=self.openai_api_key)
                response = client.chat.completions.create(
                    model="o3",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a sleep health analyst. Provide clear, concise explanations of sleep data anomalies.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                )

            analysis = response.choices[0].message.content.strip()
            self.console.print("✅ GPT-o3 analysis complete")
            return analysis

        except Exception as e:
            self.console.print(f"❌ GPT analysis failed: {e}")
            logging.error(f"GPT analysis error: {e}")
            return None

    def display_results(
        self,
        df: pd.DataFrame,
        n_out: int,
        alert: bool,
        gpt_analysis: bool = False,
        device_id: str = None,
        device_name: str = None,
    ) -> None:
        """
        Displays summary statistics and recent anomaly results for sleep data, with optional GPT-based analysis and alert notifications.
        
        Shows a summary table of key sleep metrics, a table of recent detected outliers, and highlights if the latest day is anomalous. If enabled, provides GPT-generated analysis for outliers and sends notifications when anomalies are detected. Output is formatted using rich console tables and panels.
        """
        # Create summary statistics table
        display_name = device_name or device_id or "Unknown Device"
        title = (
            f"Sleep Data Summary - {display_name}"
            if device_id
            else "Sleep Data Summary"
        )
        stats_table = Table(title=title, show_header=True, header_style="bold magenta")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Mean", justify="right")
        stats_table.add_column("Std", justify="right")
        stats_table.add_column("Min", justify="right")
        stats_table.add_column("Max", justify="right")

        for col in ["hr", "rr", "sleep_dur", "score"]:
            stats_table.add_row(
                col.upper(),
                f"{df[col].mean():.1f}",
                f"{df[col].std():.1f}",
                f"{df[col].min():.1f}",
                f"{df[col].max():.1f}",
            )

        self.console.print(stats_table)

        # Show outlier information
        outliers = df[df["if_label"] == -1].tail(n_out)
        outlier_count = len(df[df["if_label"] == -1])

        if outlier_count > 0:
            outlier_title = f"Recent Outliers ({outlier_count} total)"
            if device_id:
                outlier_title += f" - {display_name}"
            outlier_table = Table(
                title=outlier_title, show_header=True, header_style="bold red"
            )
            outlier_table.add_column("Date", style="cyan")
            outlier_table.add_column("Score", justify="right")
            outlier_table.add_column("HR", justify="right")
            outlier_table.add_column("RR", justify="right")
            outlier_table.add_column("Sleep Score", justify="right")

            for _, row in outliers.iterrows():
                outlier_table.add_row(
                    str(row.date.date()),
                    f"{row.if_score:.4f}",
                    f"{row.hr:.0f}",
                    f"{row.rr:.1f}",
                    f"{row.score:.0f}",
                )

            self.console.print(outlier_table)

            # Show GPT analysis for the most recent outlier if it's not the latest day
            if (
                gpt_analysis
                and len(outliers) > 0
                and outliers.iloc[-1].date.date() != df.iloc[-1].date.date()
            ):
                most_recent_outlier = outliers.iloc[-1]
                gpt_analysis_result = self.analyze_outlier_with_gpt(
                    most_recent_outlier, df
                )
                if gpt_analysis_result:
                    self.console.print(
                        Panel(
                            f"🤖 GPT Analysis for {most_recent_outlier.date.date()}:\n{gpt_analysis_result}",
                            style="bold yellow",
                            title="📊 OUTLIER ANALYSIS",
                        )
                    )
        else:
            self.console.print(
                Panel("✅ No outliers detected in the dataset", style="green")
            )

        # Check latest day
        latest = df.iloc[-1]
        if latest.if_label == -1:
            device_suffix = f" ({display_name})" if device_id else ""
            alert_msg = f"⚠️ ANOMALY DETECTED for {latest.date.date()}{device_suffix}"
            details = f"HR: {latest.hr:.0f}, RR: {latest.rr:.1f}, Sleep Score: {latest.score:.0f}, IF Score: {latest.if_score:.4f}"

            # Get GPT analysis for the outlier (auto-run for latest day anomalies)
            gpt_analysis_result = self.analyze_outlier_with_gpt(latest, df)
            if gpt_analysis_result:
                self.console.print(
                    Panel(
                        f"{alert_msg}\n{details}\n\n🤖 GPT Analysis:\n{gpt_analysis_result}",
                        style="bold red",
                        title="🚨 ALERT",
                    )
                )
            else:
                self.console.print(
                    Panel(f"{alert_msg}\n{details}", style="bold red", title="🚨 ALERT")
                )

            if alert:
                device_info = f" {display_name}" if device_id else ""
                base_msg = f"⚠️ {self.plugin.name.title()}{device_info} anomaly {latest.date.date()} (HR {latest.hr:.0f}, RR {latest.rr:.1f}, Score {latest.score:.0f})"
                if gpt_analysis_result:
                    full_msg = f"{base_msg}\n\n🤖 Analysis: {gpt_analysis_result}"
                    self.notify(full_msg)
                else:
                    self.notify(base_msg)
        else:
            self.console.print(
                Panel(
                    f"✅ Latest day ({latest.date.date()}) is NORMAL (score: {latest.if_score:.4f})",
                    style="green",
                )
            )

    def run_single_device(
        self,
        device_id: str,
        device_name: str,
        cache: CacheManager,
        window: int,
        contamin: float,
        n_out: int,
        alert: bool,
        gpt_analysis: bool = False,
        force_outlier_date: str = None,
    ) -> None:
        """
        Run anomaly detection on sleep data for a single device using IsolationForest.
        
        Fetches and preprocesses sleep data for the specified device and date window, selects available features, standardizes them, and fits an IsolationForest model to detect anomalies. Optionally forces a specific date to be marked as an outlier for testing. Displays results, including summary statistics and detected outliers, and can trigger notifications or GPT-based analysis if enabled.
        
        Parameters:
            device_id (str): Unique identifier for the device to analyze.
            device_name (str): Human-readable name of the device.
            cache (CacheManager): Cache manager for data retrieval.
            window (int): Number of days to include in the analysis window.
            contamin (float): Contamination rate for the IsolationForest model.
            n_out (int): Number of recent outliers to display.
            alert (bool): Whether to send notifications for detected anomalies.
            gpt_analysis (bool, optional): Whether to perform GPT-based analysis on outliers.
            force_outlier_date (str, optional): Date (YYYY-MM-DD) to forcibly mark as an outlier for testing.
        """
        try:
            self.console.print(
                Panel.fit(f"📱 Processing Device: {device_name}", style="bold cyan")
            )

            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=window)

            self.console.print(
                f"📅 Analyzing data from {start_date} to {end_date} ({window} days)"
            )
            self.console.print(f"🎯 Contamination rate: {contamin:.2%}")

            # Fetch data from sleep tracker API
            df = self.fetch_sleep_data(
                device_id,
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.min.time()),
                cache,
            )

            # Preprocess data
            df = self.preprocess(df)

            # Prepare features for IsolationForest
            feature_cols = ["hr", "rr", "sleep_dur", "score", "tnt"]

            # Handle missing tnt column gracefully
            available_cols = [
                col
                for col in feature_cols
                if col in df.columns and not df[col].isna().all()
            ]
            if len(available_cols) < 4:
                raise DataError(f"Insufficient features available: {available_cols}")

            self.console.print(f"📊 Using features: {available_cols}")

            with self.console.status("[bold green]Standardizing features..."):
                scaler = StandardScaler()
                X = scaler.fit_transform(df[available_cols])

            # Fit model and predict
            model = self.fit_iforest(X, contamin)
            df["if_label"] = model.predict(X)
            df["if_score"] = model.decision_function(X)

            # Force a specific date as outlier if requested
            if force_outlier_date:
                try:
                    from datetime import datetime as dt

                    force_date = dt.strptime(force_outlier_date, "%Y-%m-%d").date()
                    matching_rows = df[df["date"].dt.date == force_date]
                    if not matching_rows.empty:
                        df.loc[df["date"].dt.date == force_date, "if_label"] = -1
                        df.loc[
                            df["date"].dt.date == force_date, "if_score"
                        ] = -0.5  # Set a clearly anomalous score
                        self.console.print(
                            f"🔧 Forced {force_date} to be marked as an outlier for testing"
                        )
                    else:
                        self.console.print(
                            f"⚠️  Date {force_date} not found in the dataset"
                        )
                except ValueError:
                    self.console.print(
                        f"⚠️  Invalid date format: {force_outlier_date}. Use YYYY-MM-DD"
                    )

            # Display results
            self.display_results(df, n_out, alert, gpt_analysis, device_id, device_name)

        except DataError as e:
            self.console.print(
                Panel(
                    f"❌ {type(e).__name__} for device {device_id}: {e}",
                    style="bold red",
                )
            )
        except Exception as e:
            self.console.print(
                Panel(
                    f"❌ Unexpected error for device {device_id}: {e}", style="bold red"
                )
            )
            logging.exception(f"Unexpected error for device {device_id}")

    def run(
        self,
        window: int,
        contamin: float,
        n_out: int,
        alert: bool,
        gpt_analysis: bool = False,
        auto_discover: bool = True,
        force_outlier_date: str = None,
    ) -> None:
        """
        Runs anomaly detection on sleep data for all available devices using the configured plugin.
        
        Initializes caching, retrieves device IDs, and processes each device by running anomaly detection and displaying results. Handles expired cache cleanup, error reporting, and optional GPT-based analysis and alerting. Exits the program on configuration or API errors.
        """
        try:
            self.console.print(
                Panel.fit(f"🔍 {self.plugin.name.title()} Anomaly Detection Started", style="bold blue")
            )

            # Initialize cache
            cache = CacheManager(self.cache_dir, self.cache_ttl_hours)

            # Clean up expired cache files
            if self.cache_enabled:
                expired_count = cache.clear_expired()
                if expired_count > 0:
                    self.console.print(
                        f"🗑️  Cleaned up {expired_count} expired cache files"
                    )

            # Get device IDs and names
            device_ids, device_names = self.get_device_ids(auto_discover)

            if len(device_ids) == 0:
                raise ConfigError("No device IDs found to process")

            self.console.print(f"📱 Processing {len(device_ids)} device(s)")

            # Process each device
            for i, device_id in enumerate(device_ids):
                if i > 0:
                    self.console.print(
                        "\n" + "─" * 80 + "\n"
                    )  # Separator between devices

                device_name = device_names.get(device_id, device_id)
                self.run_single_device(
                    device_id,
                    device_name,
                    cache,
                    window,
                    contamin,
                    n_out,
                    alert,
                    gpt_analysis,
                    force_outlier_date,
                )

            self.console.print(
                Panel.fit("✅ Analysis Complete for All Devices", style="bold green")
            )

        except (ConfigError, APIError) as e:
            self.console.print(Panel(f"❌ {type(e).__name__}: {e}", style="bold red"))
            sys.exit(1)
        except Exception as e:
            self.console.print(Panel(f"❌ Unexpected error: {e}", style="bold red"))
            logging.exception("Unexpected error in run()")
            sys.exit(1)

    def discover_devices(self) -> None:
        """
        Displays information from the selected plugin to assist the user in discovering available device IDs.
        """
        self.plugin.discover_devices()

    def clear_cache(self) -> int:
        """
        Deletes all cached JSON files in the cache directory.
        
        Returns:
            int: The number of cache files that were removed.
        """
        cache = CacheManager(self.cache_dir, self.cache_ttl_hours)
        cache_files = list(cache.cache_dir.glob("*.json"))
        for cache_file in cache_files:
            cache_file.unlink()
        return len(cache_files)
