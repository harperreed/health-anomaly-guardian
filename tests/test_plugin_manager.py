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
        """Set up test fixtures."""
        self.console = Console()
        self.plugin_manager = PluginManager(self.console)
    
    def test_plugin_manager_initialization(self):
        """Test plugin manager initializes properly."""
        assert self.plugin_manager.console == self.console
        assert isinstance(self.plugin_manager._plugins, dict)
        assert len(self.plugin_manager._plugins) > 0
    
    def test_load_known_plugins(self):
        """Test that known plugins are loaded correctly."""
        available_plugins = self.plugin_manager.list_plugins()
        
        # Should have at least emfit plugin
        assert "emfit" in available_plugins
        assert "oura" in available_plugins
        assert "eight" in available_plugins
        
        # Should have exactly 3 plugins
        assert len(available_plugins) == 3
    
    def test_get_plugin_success(self):
        """Test getting a plugin instance successfully."""
        emfit_plugin = self.plugin_manager.get_plugin("emfit")
        
        assert emfit_plugin is not None
        assert isinstance(emfit_plugin, SleepTrackerPlugin)
        assert emfit_plugin.name == "emfit"
    
    def test_get_plugin_case_insensitive(self):
        """Test plugin retrieval is case insensitive."""
        plugin_lower = self.plugin_manager.get_plugin("emfit")
        plugin_upper = self.plugin_manager.get_plugin("EMFIT")
        plugin_mixed = self.plugin_manager.get_plugin("EmFiT")
        
        assert plugin_lower is not None
        assert plugin_upper is not None
        assert plugin_mixed is not None
        
        # Should all be the same type
        assert type(plugin_lower) == type(plugin_upper) == type(plugin_mixed)
    
    def test_get_plugin_nonexistent(self):
        """Test getting a plugin that doesn't exist."""
        nonexistent_plugin = self.plugin_manager.get_plugin("nonexistent")
        
        assert nonexistent_plugin is None
    
    def test_get_default_plugin(self):
        """Test getting the default plugin."""
        default_plugin = self.plugin_manager.get_default_plugin()
        
        assert default_plugin is not None
        assert isinstance(default_plugin, SleepTrackerPlugin)
        assert default_plugin.name == "emfit"
    
    def test_list_plugins_returns_list(self):
        """Test list_plugins returns a list of strings."""
        plugins = self.plugin_manager.list_plugins()
        
        assert isinstance(plugins, list)
        assert all(isinstance(name, str) for name in plugins)
        assert len(plugins) > 0
    
    @patch('anomaly_detector.plugins.logging')
    def test_plugin_loading_handles_import_errors(self, mock_logging):
        """Test that plugin loading handles import errors gracefully."""
        # This test verifies error handling behavior
        # Since we whitelist known modules, this mainly tests the error handling path
        with patch('anomaly_detector.plugins.__import__', side_effect=ImportError("Test error")):
            manager = PluginManager(self.console)
            
            # Should still work with empty plugins dict
            assert isinstance(manager._plugins, dict)
    
    def test_plugin_interface_compliance(self):
        """Test that all loaded plugins implement the required interface."""
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
        """Test that cache keys are generated with plugin prefixes."""
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
        """Test that only whitelisted plugins are loaded."""
        # This test ensures our security improvement works
        # We should only load emfit, oura, and eight plugins
        available_plugins = self.plugin_manager.list_plugins()
        
        expected_plugins = {"emfit", "oura", "eight"}
        actual_plugins = set(available_plugins)
        
        assert actual_plugins == expected_plugins
    
    @patch('anomaly_detector.plugins.logging')
    def test_plugin_instantiation_error_handling(self, mock_logging):
        """Test that plugin instantiation errors are handled gracefully."""
        with patch.object(self.plugin_manager._plugins['emfit'], '__init__', side_effect=Exception("Test error")):
            plugin = self.plugin_manager.get_plugin("emfit")
            
            assert plugin is None
            mock_logging.error.assert_called_once()