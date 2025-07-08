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
from emfit.api import EmfitAPI
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from .cache import CacheManager
from .config import get_env_float, get_env_int, get_env_var
from .exceptions import APIError, ConfigError, DataError


class SleepAnomalyDetector:
    """Sleep data anomaly detection using IsolationForest."""

    def __init__(self, console: Console):
        """Initialize the detector with configuration from environment variables."""
        self.console = console
        self._load_config()

    def _load_config(self):
        """Load and validate configuration from environment variables."""
        try:
            self.contam_env = get_env_float("IFOREST_CONTAM", 0.05)
            self.window_env = get_env_int("IFOREST_TRAIN_WINDOW", 90)
            self.n_out_env = get_env_int("IFOREST_SHOW_N", 5)
            self.pushover_token = get_env_var("PUSHOVER_APIKEY")
            self.pushover_user = get_env_var("PUSHOVER_USERKEY")

            # Emfit API config
            self.emfit_username = get_env_var("EMFIT_USERNAME")
            self.emfit_password = get_env_var("EMFIT_PASSWORD")
            self.emfit_token = get_env_var("EMFIT_TOKEN")
            self.emfit_device_id = get_env_var("EMFIT_DEVICE_ID")
            self.emfit_device_ids = get_env_var(
                "EMFIT_DEVICE_IDS"
            )  # Comma-separated list

            # Cache config
            self.cache_dir = Path(get_env_var("EMFIT_CACHE_DIR", "./cache"))
            self.cache_enabled = (
                get_env_var("EMFIT_CACHE_ENABLED", "true").lower() == "true"
            )
            self.cache_ttl_hours = get_env_int("EMFIT_CACHE_TTL_HOURS", 24)

            # OpenAI config
            self.openai_api_key = get_env_var("OPENAI_API_KEY")

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

    def get_emfit_api(self) -> EmfitAPI:
        """Initialize and authenticate with Emfit API."""
        try:
            api = EmfitAPI(self.emfit_token)

            if not self.emfit_token:
                if not (self.emfit_username and self.emfit_password):
                    raise APIError(
                        "Either EMFIT_TOKEN or EMFIT_USERNAME/PASSWORD must be set"
                    )

                with self.console.status(
                    "[bold green]Authenticating with Emfit API..."
                ):
                    login_response = api.login(self.emfit_username, self.emfit_password)
                    logging.debug(f"Login Response: {login_response}")

                if not login_response or not login_response.get("token"):
                    raise APIError(f"Authentication failed: {login_response}")

                self.console.print("✅ Successfully authenticated with Emfit API")
            else:
                self.console.print("✅ Using Emfit API token")

            return api

        except Exception as e:
            if isinstance(e, APIError):
                raise
            raise APIError(f"Failed to initialize Emfit API: {e}") from e

    def get_device_ids(
        self, api: EmfitAPI, auto_discover: bool = True
    ) -> tuple[list[str], dict[str, str]]:
        """Get list of device IDs to process and their names."""
        device_ids = []
        device_names = {}

        # Try auto-discovery first if enabled
        if auto_discover:
            try:
                with self.console.status(
                    "[bold green]Auto-discovering devices from user info..."
                ):
                    user_info = api.get_user()
                    logging.debug(f"User info: {user_info}")

                    # Extract device IDs from device_settings
                    if isinstance(user_info, dict) and "device_settings" in user_info:
                        device_settings = user_info["device_settings"]
                        if isinstance(device_settings, list) and device_settings:
                            device_ids = []
                            device_names = {}
                            display_names = []
                            for device in device_settings:
                                if isinstance(device, dict) and "device_id" in device:
                                    device_id = str(device["device_id"])
                                    device_name = device.get("device_name", device_id)
                                    device_ids.append(device_id)
                                    device_names[device_id] = device_name
                                    display_names.append(f"{device_name} ({device_id})")

                            if device_ids:
                                self.console.print(
                                    f"📱 Auto-discovered {len(device_ids)} devices: {', '.join(display_names)}"
                                )
                                return device_ids, device_names
            except Exception as e:
                self.console.print(f"⚠️  Auto-discovery failed: {e}")

        # Fallback to manual configuration
        if self.emfit_device_ids:
            device_ids = [
                device_id.strip()
                for device_id in self.emfit_device_ids.split(",")
                if device_id.strip()
            ]
            device_names = {device_id: device_id for device_id in device_ids}
            self.console.print(f"📱 Using configured device IDs: {device_ids}")
            return device_ids, device_names

        if self.emfit_device_id:
            device_ids = [self.emfit_device_id]
            device_names = {self.emfit_device_id: self.emfit_device_id}
            self.console.print(f"📱 Using single device ID: {device_ids}")
            return device_ids, device_names

        # Fallback error
        raise ConfigError(
            "No device IDs found. Auto-discovery failed and no manual configuration found. "
            "Please set EMFIT_DEVICE_ID (single device) or EMFIT_DEVICE_IDS (comma-separated list) "
            "environment variables, or check your API credentials."
        )

    def fetch_emfit_api_data(
        self,
        api: EmfitAPI,
        device_id: str,
        start_date: datetime,
        end_date: datetime,
        cache: CacheManager,
    ) -> pd.DataFrame:
        """Fetch sleep data from Emfit API for the specified date range with caching."""
        data = []
        current_date = start_date
        total_days = (end_date - start_date).days + 1
        failed_dates = []
        incomplete_dates = []
        cache_hits = 0
        cache_misses = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task(
                f"Fetching {total_days} days of sleep data", total=total_days
            )

            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")

                try:
                    progress.update(
                        task, description=f"Processing {current_date.date()}"
                    )

                    # Try cache first
                    trends = cache.get(device_id, date_str)
                    if trends:
                        cache_hits += 1
                        progress.update(
                            task, description=f"Cache hit: {current_date.date()}"
                        )
                    else:
                        cache_misses += 1
                        progress.update(
                            task, description=f"API fetch: {current_date.date()}"
                        )
                        trends = api.get_trends(device_id, date_str, date_str)

                        # Cache the response if successful
                        if trends:
                            cache.set(device_id, date_str, trends)

                    if trends and "data" in trends and trends["data"]:
                        sleep_data = trends["data"][0]

                        # Map API data to match our expected format
                        row = {
                            "date": pd.to_datetime(sleep_data["date"]),
                            "hr": sleep_data.get("meas_hr_avg"),
                            "rr": sleep_data.get("meas_rr_avg"),
                            "sleep_dur": sleep_data.get("sleep_duration"),
                            "score": sleep_data.get("sleep_score"),
                            "tnt": sleep_data.get("tossnturn_count"),
                        }

                        # Validate essential data
                        if all(
                            v is not None
                            for v in [
                                row["hr"],
                                row["rr"],
                                row["sleep_dur"],
                                row["score"],
                            ]
                        ):
                            # Additional validation
                            if row["hr"] > 0 and row["rr"] > 0 and row["sleep_dur"] > 0:
                                data.append(row)
                            else:
                                incomplete_dates.append(current_date.date())
                        else:
                            incomplete_dates.append(current_date.date())
                    else:
                        failed_dates.append(current_date.date())

                except Exception as e:
                    failed_dates.append(current_date.date())
                    logging.error(f"Error fetching data for {current_date.date()}: {e}")

                current_date += timedelta(days=1)
                progress.advance(task)

        # Display cache statistics
        if self.cache_enabled:
            cache_stats = cache.get_stats()
            self.console.print(
                f"💾 Cache stats: {cache_hits} hits, {cache_misses} misses, {cache_stats['valid_files']} valid files"
            )

        # Report results
        if failed_dates:
            self.console.print(
                f"⚠️  Failed to fetch data for {len(failed_dates)} dates: {failed_dates[:5]}{'...' if len(failed_dates) > 5 else ''}"
            )

        if incomplete_dates:
            self.console.print(
                f"⚠️  Incomplete data for {len(incomplete_dates)} dates: {incomplete_dates[:5]}{'...' if len(incomplete_dates) > 5 else ''}"
            )

        if not data:
            raise DataError(
                f"No valid sleep data found for the specified date range ({start_date.date()} to {end_date.date()})"
            )

        self.console.print(
            f"✅ Successfully fetched {len(data)} days of valid sleep data"
        )
        return pd.DataFrame(data)

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess the data by handling missing values and outliers."""
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
        """Send push notification via Pushover."""
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
                        "title": "Emfit Anomaly Alert",
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
        """Display results in a rich format."""
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
                base_msg = f"⚠️ Emfit{device_info} anomaly {latest.date.date()} (HR {latest.hr:.0f}, RR {latest.rr:.1f}, Score {latest.score:.0f})"
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
        api: EmfitAPI,
        cache: CacheManager,
        window: int,
        contamin: float,
        n_out: int,
        alert: bool,
        gpt_analysis: bool = False,
        force_outlier_date: str = None,
    ) -> None:
        """Run anomaly detection for a single device."""
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

            # Fetch data from API
            df = self.fetch_emfit_api_data(
                api,
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
        """Run the anomaly detection on Emfit API data for all devices."""
        try:
            self.console.print(
                Panel.fit("🔍 Emfit Anomaly Detection Started", style="bold blue")
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

            # Get API instance
            api = self.get_emfit_api()

            # Get device IDs and names
            device_ids, device_names = self.get_device_ids(api, auto_discover)

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
                    api,
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
        """Show user information to help discover device IDs."""
        try:
            api = self.get_emfit_api()
            user_info = api.get_user()
            self.console.print("🔍 User Information:")
            self.console.print(user_info)
            self.console.print(
                "\n💡 Look for device IDs in the above output and add them to your .env file as:"
            )
            self.console.print("   EMFIT_DEVICE_ID=single_device_id")
            self.console.print("   OR")
            self.console.print("   EMFIT_DEVICE_IDS=device1,device2,device3")
        except Exception as e:
            self.console.print(f"❌ Failed to fetch user info: {e}")
            raise

    def clear_cache(self) -> int:
        """Clear all cached data and return count of files removed."""
        cache = CacheManager(self.cache_dir, self.cache_ttl_hours)
        cache_files = list(cache.cache_dir.glob("*.json"))
        for cache_file in cache_files:
            cache_file.unlink()
        return len(cache_files)
