"""
Tests for the plugin manager and plugin loading functionality.
"""

import pytest
from unittest.mock import Mock, patch
from rich.console import Console

from anomaly_detector.plugins import PluginManager, SleepTrackerPlugin
from anomaly_detector.exceptions import APIError


class TestPluginManager:
    """Tests for the PluginManager class."""

    def test_plugin_manager_initialization(self):
        """Test that PluginManager initializes correctly."""
        console = Console()
        manager = PluginManager(console)
        
        assert manager.console == console
        assert isinstance(manager._plugins, dict)
        assert len(manager._plugins) > 0  # Should have at least emfit plugin

    def test_list_plugins(self):
        """Test listing available plugins."""
        console = Console()
        manager = PluginManager(console)
        
        plugins = manager.list_plugins()
        
        assert isinstance(plugins, list)
        assert "emfit" in plugins
        assert "oura" in plugins
        assert "eight" in plugins

    def test_get_plugin_existing(self):
        """Test getting an existing plugin."""
        console = Console()
        manager = PluginManager(console)
        
        plugin = manager.get_plugin("emfit")
        
        assert plugin is not None
        assert isinstance(plugin, SleepTrackerPlugin)
        assert plugin.name == "emfit"

    def test_get_plugin_nonexistent(self):
        """Test getting a non-existent plugin."""
        console = Console()
        manager = PluginManager(console)
        
        plugin = manager.get_plugin("nonexistent")
        
        assert plugin is None

    def test_get_plugin_case_insensitive(self):
        """Test that plugin names are case insensitive."""
        console = Console()
        manager = PluginManager(console)
        
        plugin_lower = manager.get_plugin("emfit")
        plugin_upper = manager.get_plugin("EMFIT")
        plugin_mixed = manager.get_plugin("EmFiT")
        
        assert plugin_lower is not None
        assert plugin_upper is not None
        assert plugin_mixed is not None
        assert type(plugin_lower) == type(plugin_upper) == type(plugin_mixed)

    def test_get_default_plugin(self):
        """Test getting the default plugin."""
        console = Console()
        manager = PluginManager(console)
        
        default_plugin = manager.get_default_plugin()
        
        assert default_plugin is not None
        assert default_plugin.name == "emfit"

    @patch('anomaly_detector.plugins.logging')
    def test_plugin_loading_with_import_error(self, mock_logging):
        """Test plugin loading handles import errors gracefully."""
        console = Console()
        
        # Test that the plugin manager continues to work even if some plugins fail to load
        manager = PluginManager(console)
        
        # Should still have successfully loaded plugins
        assert len(manager._plugins) > 0

    def test_plugin_loading_error_isolation(self):
        """Test that plugin loading errors are properly isolated."""
        console = Console()
        
        # Create plugin manager - should not crash even if some plugins have issues
        manager = PluginManager(console)
        
        # Should have at least the working emfit plugin
        assert "emfit" in manager.list_plugins()
        
        # Should be able to get a working plugin
        emfit_plugin = manager.get_plugin("emfit")
        assert emfit_plugin is not None


class TestSleepTrackerPlugin:
    """Tests for the SleepTrackerPlugin abstract base class."""

    def test_plugin_name_generation(self):
        """Test that plugin names are generated correctly."""
        console = Console()
        manager = PluginManager(console)
        
        emfit_plugin = manager.get_plugin("emfit")
        oura_plugin = manager.get_plugin("oura")
        eight_plugin = manager.get_plugin("eight")
        
        assert emfit_plugin.name == "emfit"
        assert oura_plugin.name == "oura"
        assert eight_plugin.name == "eight"

    def test_plugin_notification_titles(self):
        """Test that plugins have appropriate notification titles."""
        console = Console()
        manager = PluginManager(console)
        
        emfit_plugin = manager.get_plugin("emfit")
        oura_plugin = manager.get_plugin("oura")
        eight_plugin = manager.get_plugin("eight")
        
        assert emfit_plugin.notification_title == "Emfit Anomaly Alert"
        assert oura_plugin.notification_title == "Oura Anomaly Alert"
        assert eight_plugin.notification_title == "Eight Sleep Anomaly Alert"

    def test_incomplete_plugin_implementations(self):
        """Test that incomplete plugins raise appropriate errors."""
        console = Console()
        manager = PluginManager(console)
        
        # Oura plugin should raise APIError when trying to get API client
        oura_plugin = manager.get_plugin("oura")
        with pytest.raises(APIError) as exc_info:
            oura_plugin.get_api_client()
        assert "incomplete" in str(exc_info.value).lower()
        
        # Eight plugin should raise APIError when trying to get API client
        eight_plugin = manager.get_plugin("eight")
        with pytest.raises(APIError) as exc_info:
            eight_plugin.get_api_client()
        assert "incomplete" in str(exc_info.value).lower()

    @patch.dict('os.environ', {'EMFIT_TOKEN': 'test_token'})
    def test_emfit_plugin_config_loading(self):
        """Test that emfit plugin loads configuration properly."""
        console = Console()
        manager = PluginManager(console)
        
        emfit_plugin = manager.get_plugin("emfit")
        
        # Should have loaded config
        assert emfit_plugin.token == 'test_token'

    @patch.dict('os.environ', {'OURA_API_TOKEN': 'test_token'})
    def test_oura_plugin_config_loading(self):
        """Test that oura plugin loads configuration properly."""
        console = Console()
        manager = PluginManager(console)
        
        oura_plugin = manager.get_plugin("oura")
        
        # Should have loaded config
        assert oura_plugin.api_token == 'test_token'

    @patch.dict('os.environ', {'EIGHT_USERNAME': 'test_user', 'EIGHT_PASSWORD': 'test_pass'})
    def test_eight_plugin_config_loading(self):
        """Test that eight plugin loads configuration properly."""
        console = Console()
        manager = PluginManager(console)
        
        eight_plugin = manager.get_plugin("eight")
        
        # Should have loaded config
        assert eight_plugin.username == 'test_user'
        assert eight_plugin.password == 'test_pass'