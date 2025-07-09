"""
ABOUTME: Plugin system for sleep tracker integrations
ABOUTME: Handles plugin discovery, loading, and management
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import pandas as pd
from rich.console import Console

from ..cache import CacheManager
from ..exceptions import APIError, ConfigError


class SleepTrackerPlugin(ABC):
    """Abstract base class for sleep tracker plugins."""
    
    def __init__(self, console: Console):
        """
        Initializes the plugin with a console instance and sets the plugin name.
        
        The plugin name is derived from the class name by removing 'plugin' and converting to lowercase. Loads plugin-specific configuration.
        """
        self.console = console
        self.name = self.__class__.__name__.lower().replace('plugin', '')
        self._load_config()
    
    @abstractmethod
    def _load_config(self) -> None:
        """
        Load configuration settings for the plugin from environment variables.
        
        This method should be implemented by each plugin to initialize any required configuration using environment variables.
        """
        pass
    
    @abstractmethod
    def get_api_client(self) -> Any:
        """
        Initializes and returns an authenticated API client for the sleep tracker service.
        
        Returns:
            Any: An authenticated API client instance specific to the plugin implementation.
        """
        pass
    
    @abstractmethod
    def get_device_ids(self, auto_discover: bool = True) -> tuple[list[str], dict[str, str]]:
        """
        Return a list of available device IDs and a mapping of device IDs to display names.
        
        Parameters:
            auto_discover (bool): If True, attempt to automatically discover devices; otherwise, use configured devices only.
        
        Returns:
            tuple[list[str], dict[str, str]]: A tuple containing a list of device IDs and a dictionary mapping device IDs to their display names.
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
        Retrieve sleep data for a given device within a specified date range, returning a DataFrame with standardized columns.
        
        Parameters:
            device_id (str): Unique identifier of the device to fetch data from.
            start_date (datetime): Start of the date range for data retrieval.
            end_date (datetime): End of the date range for data retrieval.
            cache (CacheManager): Cache manager to optimize data access.
        
        Returns:
            pd.DataFrame: DataFrame containing columns for date, heart rate (hr), respiratory rate (rr), sleep duration (sleep_dur), sleep quality score (score), and optionally toss and turn count (tnt).
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
        Initialize the PluginManager with a console instance and load available sleep tracker plugins.
        """
        self.console = console
        self._plugins: Dict[str, Type[SleepTrackerPlugin]] = {}
        self._load_plugins()
    
    def _load_plugins(self) -> None:
        """
        Discovers and registers all valid sleep tracker plugin classes from Python files in the plugins directory.
        
        Scans the directory for plugin modules, imports them, and adds subclasses of `SleepTrackerPlugin` (excluding the base class) to the internal plugin registry. Skips files starting with an underscore or named `base.py`. Logs warnings if a plugin fails to load.
        """
        plugins_dir = Path(__file__).parent
        
        # Import all plugin modules
        for plugin_file in plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_") or plugin_file.name == "base.py":
                continue
                
            module_name = plugin_file.stem
            try:
                # Use importlib for safer import handling
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    f"anomaly_detector.plugins.{module_name}", 
                    plugin_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find plugin classes in the module
                    for attr_name in dir(module):
                        try:
                            attr = getattr(module, attr_name)
                            if (
                                isinstance(attr, type) and
                                issubclass(attr, SleepTrackerPlugin) and
                                attr is not SleepTrackerPlugin
                            ):
                                plugin_name = module_name.lower()
                                self._plugins[plugin_name] = attr
                                logging.debug(f"Loaded plugin: {plugin_name}")
                        except (AttributeError, TypeError) as e:
                            logging.debug(f"Skipping attribute {attr_name} in {module_name}: {e}")
                            continue
                else:
                    logging.warning(f"Could not create module spec for {module_name}")
                        
            except (ImportError, FileNotFoundError, AttributeError) as e:
                logging.warning(f"Failed to load plugin {module_name}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error loading plugin {module_name}: {e}")
    
    def get_plugin(self, name: str) -> Optional[SleepTrackerPlugin]:
        """
        Returns an instance of the sleep tracker plugin matching the given name, or None if not found.
        
        Parameters:
            name (str): The name of the plugin to retrieve (case-insensitive).
        
        Returns:
            Optional[SleepTrackerPlugin]: An instance of the requested plugin, or None if no matching plugin exists.
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