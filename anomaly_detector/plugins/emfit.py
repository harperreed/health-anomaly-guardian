"""
ABOUTME: Emfit sleep tracker plugin
ABOUTME: Handles Emfit API integration for sleep data fetching and device management
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from emfit.api import EmfitAPI
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ..cache import CacheManager
from ..config import get_env_var
from ..exceptions import APIError, ConfigError, DataError
from . import SleepTrackerPlugin


class EmfitPlugin(SleepTrackerPlugin):
    """Emfit sleep tracker plugin."""
    
    def _load_config(self) -> None:
        """
        Loads Emfit plugin configuration values from environment variables.
        
        Retrieves the Emfit username, password, API token, and device IDs (single or comma-separated list) from environment variables and stores them as instance attributes.
        """
        self.username = get_env_var("EMFIT_USERNAME")
        self.password = get_env_var("EMFIT_PASSWORD")
        self.token = get_env_var("EMFIT_TOKEN")
        self.device_id = get_env_var("EMFIT_DEVICE_ID")
        self.device_ids = get_env_var("EMFIT_DEVICE_IDS")  # Comma-separated list
    
    def get_api_client(self) -> EmfitAPI:
        """
        Creates and returns an authenticated EmfitAPI client using either an API token or username and password.
        
        Raises:
            APIError: If authentication fails or required credentials are missing.
            
        Returns:
            EmfitAPI: An authenticated EmfitAPI client instance.
        """
        try:
            api = EmfitAPI(self.token)
            
            if not self.token:
                if not (self.username and self.password):
                    raise APIError(
                        "Either EMFIT_TOKEN or EMFIT_USERNAME/PASSWORD must be set"
                    )
                
                with self.console.status(
                    "[bold green]Authenticating with Emfit API..."
                ):
                    login_response = api.login(self.username, self.password)
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
    
    def get_device_ids(self, auto_discover: bool = True) -> tuple[list[str], dict[str, str]]:
        """
        Retrieve a list of Emfit device IDs and their corresponding names, using auto-discovery or manual configuration.
        
        If auto-discovery is enabled, attempts to fetch device information from the Emfit API and extract device IDs and names. If auto-discovery fails or is disabled, falls back to device IDs specified in environment variables. Raises a ConfigError if no devices are found.
        
        Parameters:
            auto_discover (bool): Whether to attempt automatic device discovery via the API.
        
        Returns:
            tuple[list[str], dict[str, str]]: A list of device IDs and a mapping from device ID to device name.
        """
        device_ids = []
        device_names = {}
        
        # Get API client for device discovery
        api = self.get_api_client()
        
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
        if self.device_ids:
            device_ids = [
                device_id.strip()
                for device_id in self.device_ids.split(",")
                if device_id.strip()
            ]
            device_names = {device_id: device_id for device_id in device_ids}
            self.console.print(f"📱 Using configured device IDs: {device_ids}")
            return device_ids, device_names
        
        if self.device_id:
            device_ids = [self.device_id]
            device_names = {self.device_id: self.device_id}
            self.console.print(f"📱 Using single device ID: {device_ids}")
            return device_ids, device_names
        
        # Fallback error
        raise ConfigError(
            "No device IDs found. Auto-discovery failed and no manual configuration found. "
            "Please set EMFIT_DEVICE_ID (single device) or EMFIT_DEVICE_IDS (comma-separated list) "
            "environment variables, or check your API credentials."
        )
    
    def fetch_data(
        self,
        device_id: str,
        start_date: datetime,
        end_date: datetime,
        cache: CacheManager,
    ) -> pd.DataFrame:
        """
        Retrieve and cache Emfit sleep data for a device over a specified date range.
        
        For each day in the range, attempts to load sleep data from the cache; if unavailable, fetches from the Emfit API and caches the result. Only entries with valid heart rate, respiratory rate, sleep duration, and score are included. Incomplete or failed dates are reported. Raises a DataError if no valid data is found.
        
        Parameters:
            device_id (str): The Emfit device identifier.
            start_date (datetime): Start of the date range (inclusive).
            end_date (datetime): End of the date range (inclusive).
            cache (CacheManager): Cache manager for storing and retrieving daily sleep data.
        
        Returns:
            pd.DataFrame: DataFrame containing valid daily sleep metrics for the specified device and date range.
        """
        api = self.get_api_client()
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
                    trends = cache.get(device_id, date_str, self.name)
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
                            cache.set(device_id, date_str, trends, self.name)
                    
                    if trends and "data" in trends and trends["data"]:
                        sleep_data = trends["data"][0]
                        
                        # Map API data to standard format
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
    
    def discover_devices(self) -> None:
        """
        Displays Emfit user information to assist in identifying device IDs for configuration.
        
        Fetches and prints user details from the Emfit API, guiding the user on how to set device IDs in environment variables. If fetching fails, prints an error message and re-raises the exception.
        """
        try:
            api = self.get_api_client()
            user_info = api.get_user()
            self.console.print("🔍 Emfit User Information:")
            self.console.print(user_info)
            self.console.print(
                "\n💡 Look for device IDs in the above output and add them to your .env file as:"
            )
            self.console.print("   EMFIT_DEVICE_ID=single_device_id")
            self.console.print("   OR")
            self.console.print("   EMFIT_DEVICE_IDS=device1,device2,device3")
        except Exception as e:
            self.console.print(f"❌ Failed to fetch Emfit user info: {e}")
            raise
    
    @property
    def notification_title(self) -> str:
        """
        Returns the title string used for Emfit anomaly alert push notifications.
        """
        return "Emfit Anomaly Alert"