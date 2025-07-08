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
        """Initialize the plugin with a console instance."""
        self.console = console
        self.name = self.__class__.__name__.lower().replace('plugin', '')
        self._load_config()
    
    @abstractmethod
    def _load_config(self) -> None:
        """Load plugin-specific configuration from environment variables."""
        pass
    
    @abstractmethod
    def get_api_client(self):
        """Initialize and return authenticated API client."""
        pass
    
    @abstractmethod
    def get_device_ids(self, auto_discover: bool = True) -> tuple[list[str], dict[str, str]]:
        """
        Get list of device IDs and their display names.
        
        Args:
            auto_discover: Whether to attempt auto-discovery of devices
            
        Returns:
            tuple of (device_ids, device_names_dict)
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
        Fetch sleep data for the specified device and date range.
        
        Args:
            device_id: Device identifier
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            cache: Cache manager instance
            
        Returns:
            DataFrame with standardized sleep data columns:
            - date: datetime
            - hr: heart rate (bpm)
            - rr: respiratory rate (breaths/min)
            - sleep_dur: sleep duration (hours)
            - score: sleep quality score
            - tnt: toss and turn count (optional)
        """
        pass
    
    @abstractmethod
    def discover_devices(self) -> None:
        """Show device discovery information to help user configure devices."""
        pass
    
    @property
    @abstractmethod
    def notification_title(self) -> str:
        """Title to use for push notifications."""
        pass


class PluginManager:
    """Manages loading and access to sleep tracker plugins."""
    
    def __init__(self, console: Console):
        """Initialize plugin manager."""
        self.console = console
        self._plugins: Dict[str, Type[SleepTrackerPlugin]] = {}
        self._load_plugins()
    
    def _load_plugins(self) -> None:
        """Load all available plugins from the plugins directory."""
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
        """Get a plugin instance by name."""
        plugin_class = self._plugins.get(name.lower())
        if plugin_class:
            return plugin_class(self.console)
        return None
    
    def list_plugins(self) -> List[str]:
        """List all available plugin names."""
        return list(self._plugins.keys())
    
    def get_default_plugin(self) -> Optional[SleepTrackerPlugin]:
        """Get the default plugin (Emfit for backward compatibility)."""
        return self.get_plugin("emfit")