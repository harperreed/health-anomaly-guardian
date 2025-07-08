"""
ABOUTME: Plugin system for sleep tracker integrations
ABOUTME: Handles plugin discovery, loading, and management
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type

import pandas as pd
from rich.console import Console

from ..cache import CacheManager
from ..exceptions import APIError, ConfigError


class SleepTrackerPlugin(ABC):
    """Abstract base class for sleep tracker plugins."""
    
    def __init__(self, console: Console):
        """
        Initialize the sleep tracker plugin with the provided console and load its configuration.
        
        Parameters:
            console (Console): The console instance used for logging or user interaction.
        """
        self.console = console
        self.name = self.__class__.__name__.lower().replace('plugin', '')
        self._load_config()
    
    @abstractmethod
    def _load_config(self) -> None:
        """
        Load plugin-specific configuration from environment variables.
        
        This method should be implemented by subclasses to initialize any required settings or credentials needed for the plugin to operate.
        """
        pass
    
    @abstractmethod
    def get_api_client(self):
        """
        Initialize and return an authenticated API client for the sleep tracker service.
        
        Returns:
            An authenticated API client instance specific to the plugin implementation.
        """
        pass
    
    @abstractmethod
    def get_device_ids(self, auto_discover: bool = True) -> tuple[list[str], dict[str, str]]:
        """
        Return a list of device IDs and a mapping of device IDs to display names.
        
        Parameters:
            auto_discover (bool): If True, attempt to automatically discover available devices.
        
        Returns:
            tuple: A tuple containing a list of device IDs and a dictionary mapping device IDs to their display names.
        """
        pass
    
    @abstractmethod
    def fetch_data(
        self,
        device_id: str,
        start_date: datetime,
        end_date: datetime,
        cache: CacheManager,
    ) -> pd.DataFrame:
        """
        Retrieve standardized sleep data for a given device and date range.
        
        Parameters:
            device_id (str): The unique identifier of the sleep tracking device.
            start_date (datetime): The beginning of the date range for data retrieval.
            end_date (datetime): The end of the date range for data retrieval.
            cache (CacheManager): Cache manager to optimize data access.
        
        Returns:
            pd.DataFrame: A DataFrame containing sleep data with columns: `date`, `hr`, `rr`, `sleep_dur`, `score`, and optionally `tnt`.
        """
        pass
    
    @abstractmethod
    def discover_devices(self) -> None:
        """
        Display information to assist the user in discovering and configuring available devices.
        """
        pass
    
    @property
    @abstractmethod
    def notification_title(self) -> str:
        """
        Returns the title string to be used for push notifications sent by the plugin.
        """
        pass


class PluginManager:
    """Manages loading and access to sleep tracker plugins."""
    
    def __init__(self, console: Console):
        """
        Initialize the PluginManager and load all available sleep tracker plugins.
        
        Parameters:
            console (Console): Console instance used for logging and user interaction.
        """
        self.console = console
        self._plugins: Dict[str, Type[SleepTrackerPlugin]] = {}
        self._load_plugins()
    
    def _load_plugins(self) -> None:
        """
        Discover and register all valid sleep tracker plugin classes from the plugins directory.
        
        Scans the directory for Python files (excluding those starting with '_' or named 'base.py'), dynamically imports each module, and registers any classes that subclass `SleepTrackerPlugin` (excluding the base class itself) in the internal plugin registry.
        """
        plugins_dir = Path(__file__).parent
        
        # Import all plugin modules
        for plugin_file in plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_") or plugin_file.name == "base.py":
                continue
                
            module_name = plugin_file.stem
            try:
                module = __import__(f"anomaly_detector.plugins.{module_name}", fromlist=[module_name])
                
                # Find plugin classes in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type) and
                        issubclass(attr, SleepTrackerPlugin) and
                        attr is not SleepTrackerPlugin
                    ):
                        plugin_name = module_name.lower()
                        self._plugins[plugin_name] = attr
                        logging.debug(f"Loaded plugin: {plugin_name}")
                        
            except ImportError as e:
                logging.warning(f"Failed to load plugin {module_name}: {e}")
    
    def get_plugin(self, name: str) -> Optional[SleepTrackerPlugin]:
        """
        Return an instance of the sleep tracker plugin matching the given name, or None if not found.
        
        Parameters:
            name (str): The name of the plugin to retrieve (case-insensitive).
        
        Returns:
            Optional[SleepTrackerPlugin]: An instance of the requested plugin, or None if no matching plugin is available.
        """
        plugin_class = self._plugins.get(name.lower())
        if plugin_class:
            return plugin_class(self.console)
        return None
    
    def list_plugins(self) -> List[str]:
        """
        Return a list of all available sleep tracker plugin names.
        """
        return list(self._plugins.keys())
    
    def get_default_plugin(self) -> Optional[SleepTrackerPlugin]:
        """
        Return an instance of the default sleep tracker plugin, which is "emfit" for backward compatibility.
        
        Returns:
            Optional[SleepTrackerPlugin]: The default plugin instance if available, otherwise None.
        """
        return self.get_plugin("emfit")