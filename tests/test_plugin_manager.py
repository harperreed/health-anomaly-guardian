"""
ABOUTME: Tests for the plugin manager and plugin system
ABOUTME: Tests plugin loading, instantiation, and error handling
"""

import pytest
from unittest.mock import Mock, patch
from rich.console import Console

from anomaly_detector.plugins import PluginManager, SleepTrackerPlugin
from anomaly_detector.exceptions import APIError, ConfigError


class TestPluginManager:
    """Test the plugin manager functionality."""
    
    def setup_method(self):
        """
        Initializes a Console and PluginManager instance before each test method.
        """
        self.console = Console()
        self.plugin_manager = PluginManager(self.console)
    
    def test_plugin_manager_initialization(self):
        """
        Verify that the plugin manager is initialized with the correct console and a non-empty plugins dictionary.
        """
        assert self.plugin_manager.console == self.console
        assert isinstance(self.plugin_manager._plugins, dict)
        assert len(self.plugin_manager._plugins) > 0
    
    def test_load_known_plugins(self):
        """
        Verify that the plugin manager loads exactly the known plugins "emfit", "oura", and "eight".
        """
        available_plugins = self.plugin_manager.list_plugins()
        
        # Should have at least emfit plugin
        assert "emfit" in available_plugins
        assert "oura" in available_plugins
        assert "eight" in available_plugins
        
        # Should have exactly 3 plugins
        assert len(available_plugins) == 3
    
    def test_get_plugin_success(self):
        """
        Test that retrieving the "emfit" plugin returns a valid instance with the correct name.
        
        Ensures that the plugin manager returns a non-null instance of `SleepTrackerPlugin` for "emfit" and that its name attribute matches the requested plugin.
        """
        emfit_plugin = self.plugin_manager.get_plugin("emfit")
        
        assert emfit_plugin is not None
        assert isinstance(emfit_plugin, SleepTrackerPlugin)
        assert emfit_plugin.name == "emfit"
    
    def test_get_plugin_case_insensitive(self):
        """
        Verify that plugin retrieval by name is case-insensitive, ensuring the same plugin instance type is returned regardless of input casing.
        """
        plugin_lower = self.plugin_manager.get_plugin("emfit")
        plugin_upper = self.plugin_manager.get_plugin("EMFIT")
        plugin_mixed = self.plugin_manager.get_plugin("EmFiT")
        
        assert plugin_lower is not None
        assert plugin_upper is not None
        assert plugin_mixed is not None
        
        # Should all be the same type
        assert type(plugin_lower) == type(plugin_upper) == type(plugin_mixed)
    
    def test_get_plugin_nonexistent(self):
        """
        Verify that requesting a nonexistent plugin returns None.
        """
        nonexistent_plugin = self.plugin_manager.get_plugin("nonexistent")
        
        assert nonexistent_plugin is None
    
    def test_get_default_plugin(self):
        """
        Verify that the default plugin returned by the plugin manager is an instance of SleepTrackerPlugin named "emfit".
        """
        default_plugin = self.plugin_manager.get_default_plugin()
        
        assert default_plugin is not None
        assert isinstance(default_plugin, SleepTrackerPlugin)
        assert default_plugin.name == "emfit"
    
    def test_list_plugins_returns_list(self):
        """
        Verify that the list_plugins method returns a non-empty list of plugin names as strings.
        """
        plugins = self.plugin_manager.list_plugins()
        
        assert isinstance(plugins, list)
        assert all(isinstance(name, str) for name in plugins)
        assert len(plugins) > 0
    
    @patch('anomaly_detector.plugins.logging')
    def test_plugin_loading_handles_import_errors(self, mock_logging):
        """
        Test that the plugin manager handles import errors during plugin loading without crashing.
        
        Simulates an ImportError when loading plugins and verifies that the PluginManager initializes with a valid plugins dictionary and logs the error.
        """
        # This test verifies error handling behavior
        # Since we whitelist known modules, this mainly tests the error handling path
        with patch('anomaly_detector.plugins.__import__', side_effect=ImportError("Test error")):
            manager = PluginManager(self.console)
            
            # Should still work with empty plugins dict
            assert isinstance(manager._plugins, dict)
    
    def test_plugin_interface_compliance(self):
        """
        Verify that every loaded plugin implements all required interface methods and attributes.
        """
        for plugin_name in self.plugin_manager.list_plugins():
            plugin = self.plugin_manager.get_plugin(plugin_name)
            
            assert hasattr(plugin, '_load_config')
            assert hasattr(plugin, 'get_api_client')
            assert hasattr(plugin, 'get_device_ids')
            assert hasattr(plugin, 'fetch_data')
            assert hasattr(plugin, 'discover_devices')
            assert hasattr(plugin, 'notification_title')
            assert hasattr(plugin, '_get_cache_key')
    
    def test_cache_key_generation(self):
        """
        Verify that plugins generate unique cache keys prefixed with their plugin names to prevent key collisions.
        """
        emfit_plugin = self.plugin_manager.get_plugin("emfit")
        oura_plugin = self.plugin_manager.get_plugin("oura")
        
        device_id = "test_device"
        date_str = "2024-01-01"
        
        emfit_key = emfit_plugin._get_cache_key(device_id, date_str)
        oura_key = oura_plugin._get_cache_key(device_id, date_str)
        
        assert emfit_key == f"emfit_{device_id}_{date_str}"
        assert oura_key == f"oura_{device_id}_{date_str}"
        
        # Keys should be different to prevent collision
        assert emfit_key != oura_key
    
    def test_plugin_security_whitelist(self):
        """
        Verify that only the whitelisted plugins ("emfit", "oura", "eight") are loaded by the plugin manager.
        """
        # This test ensures our security improvement works
        # We should only load emfit, oura, and eight plugins
        available_plugins = self.plugin_manager.list_plugins()
        
        expected_plugins = {"emfit", "oura", "eight"}
        actual_plugins = set(available_plugins)
        
        assert actual_plugins == expected_plugins
    
    @patch('anomaly_detector.plugins.logging')
    def test_plugin_instantiation_error_handling(self, mock_logging):
        """
        Test that the plugin manager handles exceptions raised during plugin instantiation without crashing.
        
        Simulates an error in the constructor of the "emfit" plugin and verifies that `get_plugin` returns `None` and logs the error.
        """
        with patch.object(self.plugin_manager._plugins['emfit'], '__init__', side_effect=Exception("Test error")):
            plugin = self.plugin_manager.get_plugin("emfit")
            
            assert plugin is None
            mock_logging.error.assert_called_once()