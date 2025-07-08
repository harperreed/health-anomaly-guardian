"""
ABOUTME: Eight Sleep tracker plugin
ABOUTME: Handles Eight Sleep API integration for sleep data fetching and device management
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ..cache import CacheManager
from ..config import get_env_var
from ..exceptions import APIError, ConfigError, DataError
from . import SleepTrackerPlugin


class EightPlugin(SleepTrackerPlugin):
    """Eight Sleep tracker plugin."""
    
    def _load_config(self) -> None:
        """
        Loads Eight Sleep configuration parameters from environment variables.
        
        Sets the plugin's username, password, device ID, and user ID attributes using environment variables required for Eight Sleep API integration.
        """
        self.username = get_env_var("EIGHT_USERNAME")
        self.password = get_env_var("EIGHT_PASSWORD")
        self.device_id = get_env_var("EIGHT_DEVICE_ID")
        self.user_id = get_env_var("EIGHT_USER_ID")
    
    def get_api_client(self):
        """
        Initializes and returns an authenticated Eight Sleep API client.
        
        Raises:
            APIError: If the required Eight Sleep credentials are not set in the environment.
        
        Returns:
            An authenticated Eight Sleep API client instance, or None if not yet implemented.
        """
        if not (self.username and self.password):
            raise APIError("EIGHT_USERNAME and EIGHT_PASSWORD environment variables must be set")
        
        # TODO: Initialize actual Eight Sleep API client
        # Example: return EightSleepAPI(username=self.username, password=self.password)
        self.console.print("✅ Eight Sleep API client initialized")
        return None  # Placeholder
    
    def get_device_ids(self, auto_discover: bool = True) -> tuple[list[str], dict[str, str]]:
        """
        Return a list of Eight Sleep device IDs and their corresponding names, using either configured values or auto-discovery.
        
        Parameters:
            auto_discover (bool): If True, attempts to auto-discover devices if no device ID is configured.
        
        Returns:
            tuple[list[str], dict[str, str]]: A list of device IDs and a mapping from device IDs to device names.
        
        Raises:
            ConfigError: If no device ID is found and auto-discovery is unsuccessful.
        """
        # Use configured device ID if available
        if self.device_id:
            device_ids = [self.device_id]
            device_names = {self.device_id: f"Eight Sleep Pod ({self.device_id})"}
            self.console.print(f"📱 Using configured Eight Sleep device ID: {self.device_id}")
            return device_ids, device_names
        
        # Auto-discovery for Eight Sleep devices
        if auto_discover:
            try:
                # TODO: Implement actual device discovery via Eight Sleep API
                # api = self.get_api_client()
                # devices = api.get_devices()
                # device_ids = [device["device_id"] for device in devices]
                # device_names = {device["device_id"]: device["name"] for device in devices}
                
                # Placeholder auto-discovery
                device_id = "eight-pod-default"
                device_names = {device_id: "Eight Sleep Pod"}
                self.console.print(f"📱 Auto-discovered Eight Sleep device: {device_id}")
                return [device_id], device_names
            except Exception as e:
                self.console.print(f"⚠️  Eight Sleep auto-discovery failed: {e}")
        
        raise ConfigError(
            "No Eight Sleep device ID found. Please set EIGHT_DEVICE_ID environment variable "
            "or enable auto-discovery with valid EIGHT_USERNAME/EIGHT_PASSWORD."
        )
    
    def fetch_data(
        self,
        device_id: str,
        start_date: datetime,
        end_date: datetime,
        cache: CacheManager,
    ) -> pd.DataFrame:
        """
        Fetches sleep data for a specified Eight Sleep device and date range, utilizing caching to minimize redundant API calls.
        
        Attempts to retrieve cached data for each day in the range; if unavailable, placeholder logic is used (actual API integration pending). Only days with all key metrics present are included in the results. Raises a DataError if no valid data is found.
        
        Parameters:
            device_id (str): The unique identifier of the Eight Sleep device.
            start_date (datetime): The start date of the data retrieval range.
            end_date (datetime): The end date of the data retrieval range.
            cache (CacheManager): Cache manager for storing and retrieving sleep data.
        
        Returns:
            pd.DataFrame: DataFrame containing sleep metrics for each valid day in the specified range.
        """
        # TODO: Implement actual Eight Sleep API data fetching
        # This is a placeholder implementation
        
        api = self.get_api_client()
        data = []
        current_date = start_date
        total_days = (end_date - start_date).days + 1
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task(
                f"Fetching {total_days} days of Eight Sleep data", total=total_days
            )
            
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                
                try:
                    progress.update(
                        task, description=f"Processing {current_date.date()}"
                    )
                    
                    # Try cache first
                    cached_data = cache.get(device_id, date_str)
                    if cached_data:
                        sleep_data = cached_data
                    else:
                        # TODO: Fetch from Eight Sleep API
                        # sleep_data = api.get_sleep_session(device_id, date_str)
                        # cache.set(device_id, date_str, sleep_data)
                        
                        # Placeholder data structure
                        sleep_data = None
                    
                    if sleep_data:
                        # TODO: Map Eight Sleep API response to standard format
                        row = {
                            "date": pd.to_datetime(current_date),
                            "hr": None,  # Map from Eight Sleep's heart rate data
                            "rr": None,  # Map from Eight Sleep's respiratory rate data
                            "sleep_dur": None,  # Map from Eight Sleep's sleep duration
                            "score": None,  # Map from Eight Sleep's sleep fitness score
                            "tnt": None,  # Map from Eight Sleep's movement/restlessness data
                        }
                        
                        # Validate and add to data
                        if all(v is not None for v in [row["hr"], row["rr"], row["sleep_dur"], row["score"]]):
                            data.append(row)
                
                except Exception as e:
                    logging.error(f"Error fetching Eight Sleep data for {current_date.date()}: {e}")
                
                current_date += timedelta(days=1)
                progress.advance(task)
        
        if not data:
            raise DataError(
                f"No valid Eight Sleep data found for the specified date range ({start_date.date()} to {end_date.date()}). "
                f"This is a placeholder implementation - actual Eight Sleep API integration needed."
            )
        
        self.console.print(
            f"✅ Successfully fetched {len(data)} days of Eight Sleep data"
        )
        return pd.DataFrame(data)
    
    def discover_devices(self) -> None:
        """
        Displays instructions and guidance for configuring Eight Sleep device integration.
        
        Provides manual setup steps for environment variables and placeholder messages for future device discovery functionality. If an error occurs during the process, it is displayed and re-raised.
        """
        try:
            # TODO: Implement actual device discovery
            self.console.print("🔍 Eight Sleep Device Discovery:")
            self.console.print("TODO: Implement Eight Sleep API device discovery")
            self.console.print(
                "\n💡 To configure Eight Sleep manually, add to your .env file:"
            )
            self.console.print("   EIGHT_USERNAME=your_username")
            self.console.print("   EIGHT_PASSWORD=your_password")
            self.console.print("   EIGHT_DEVICE_ID=your_device_id  # Optional")
            self.console.print("   EIGHT_USER_ID=your_user_id  # Optional")
        except Exception as e:
            self.console.print(f"❌ Failed to discover Eight Sleep devices: {e}")
            raise
    
    @property
    def notification_title(self) -> str:
        """
        Returns the title string used for Eight Sleep anomaly alert push notifications.
        """
        return "Eight Sleep Anomaly Alert"