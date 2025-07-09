"""
Tests for the cache manager integration with plugin names.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from anomaly_detector.cache import CacheManager


class TestCachePluginIntegration:
    """Tests for cache integration with plugin names."""

    @pytest.fixture
    def cache_dir(self, tmp_path):
        """
        Creates and returns a temporary directory path for cache storage during tests.
        
        Parameters:
            tmp_path: A pytest-provided temporary directory unique to the test invocation.
        
        Returns:
            Path object representing the cache directory location.
        """
        return tmp_path / "cache"

    @pytest.fixture
    def cache_manager(self, cache_dir):
        """
        Create a CacheManager instance configured to use the specified cache directory with a 24-hour time-to-live for cached entries.
        
        Parameters:
            cache_dir (Path): The directory where cache files will be stored.
        
        Returns:
            CacheManager: An instance of CacheManager using the provided directory and TTL.
        """
        return CacheManager(cache_dir, ttl_hours=24)

    def test_cache_key_generation_with_plugin_name(self, cache_manager):
        """
        Verify that cache keys generated for the same device and date are unique when different plugin names are used, including the case with no plugin name.
        """
        device_id = "test_device_123"
        date_str = "2024-01-15"
        
        # Generate cache keys with different plugin names
        key_emfit = cache_manager._get_cache_key(device_id, date_str, "emfit")
        key_oura = cache_manager._get_cache_key(device_id, date_str, "oura")
        key_eight = cache_manager._get_cache_key(device_id, date_str, "eight")
        key_no_plugin = cache_manager._get_cache_key(device_id, date_str)
        
        # All keys should be different
        assert key_emfit != key_oura
        assert key_oura != key_eight
        assert key_eight != key_emfit
        assert key_no_plugin != key_emfit
        assert key_no_plugin != key_oura
        assert key_no_plugin != key_eight

    def test_cache_key_generation_consistent(self, cache_manager):
        """
        Verify that generating a cache key with the same device ID, date, and plugin name consistently produces the same key.
        """
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        
        key1 = cache_manager._get_cache_key(device_id, date_str, plugin_name)
        key2 = cache_manager._get_cache_key(device_id, date_str, plugin_name)
        
        assert key1 == key2

    def test_cache_set_and_get_with_plugin_name(self, cache_manager):
        """
        Verifies that data cached with a specific plugin name can only be retrieved using the same plugin name, ensuring isolation between plugins and preventing access without specifying the correct plugin.
        """
        device_id = "test_device_123"
        date_str = "2024-01-15"
        test_data = {"sleep_score": 85, "hr": 65, "rr": 14}
        
        # Cache data for emfit plugin
        cache_manager.set(device_id, date_str, test_data, "emfit")
        
        # Should be able to retrieve it with the same plugin name
        retrieved_data = cache_manager.get(device_id, date_str, "emfit")
        assert retrieved_data == test_data
        
        # Should not be able to retrieve it with a different plugin name
        retrieved_data_oura = cache_manager.get(device_id, date_str, "oura")
        assert retrieved_data_oura is None
        
        # Should not be able to retrieve it without plugin name
        retrieved_data_no_plugin = cache_manager.get(device_id, date_str)
        assert retrieved_data_no_plugin is None

    def test_cache_plugin_isolation(self, cache_manager):
        """
        Verify that data cached under different plugin names for the same device and date remains isolated, ensuring each plugin retrieves only its own cached data.
        """
        device_id = "test_device_123"
        date_str = "2024-01-15"
        
        emfit_data = {"sleep_score": 85, "hr": 65, "rr": 14, "source": "emfit"}
        oura_data = {"sleep_score": 90, "hr": 70, "rr": 16, "source": "oura"}
        eight_data = {"sleep_score": 80, "hr": 60, "rr": 12, "source": "eight"}
        
        # Cache data for each plugin
        cache_manager.set(device_id, date_str, emfit_data, "emfit")
        cache_manager.set(device_id, date_str, oura_data, "oura")
        cache_manager.set(device_id, date_str, eight_data, "eight")
        
        # Each plugin should retrieve its own data
        assert cache_manager.get(device_id, date_str, "emfit") == emfit_data
        assert cache_manager.get(device_id, date_str, "oura") == oura_data
        assert cache_manager.get(device_id, date_str, "eight") == eight_data

    def test_cache_backwards_compatibility(self, cache_manager):
        """
        Verify that caching and retrieval function correctly when no plugin name is specified, ensuring backward compatibility with previous cache behavior.
        """
        device_id = "test_device_123"
        date_str = "2024-01-15"
        test_data = {"sleep_score": 85, "hr": 65, "rr": 14}
        
        # Cache data without plugin name
        cache_manager.set(device_id, date_str, test_data)
        
        # Should be able to retrieve it without plugin name
        retrieved_data = cache_manager.get(device_id, date_str)
        assert retrieved_data == test_data

    def test_cache_collision_prevention(self, cache_manager):
        """
        Verify that caching data for different plugins with the same device ID and date does not cause collisions, ensuring each plugin retrieves only its own cached data.
        """
        device_id = "device_123"  # Same device ID for different plugins
        date_str = "2024-01-15"
        
        emfit_data = {"sleep_score": 85, "source": "emfit"}
        oura_data = {"sleep_score": 90, "source": "oura"}
        
        # Cache data for both plugins with same device ID
        cache_manager.set(device_id, date_str, emfit_data, "emfit")
        cache_manager.set(device_id, date_str, oura_data, "oura")
        
        # Each plugin should get its own data, not collision
        assert cache_manager.get(device_id, date_str, "emfit") == emfit_data
        assert cache_manager.get(device_id, date_str, "oura") == oura_data

    def test_cache_expiration_with_plugin_names(self, cache_manager):
        """
        Verify that cached data associated with a plugin name expires as expected and cannot be retrieved after the TTL has elapsed.
        """
        device_id = "test_device_123"
        date_str = "2024-01-15"
        test_data = {"sleep_score": 85, "hr": 65, "rr": 14}
        
        # Cache data for emfit plugin
        cache_manager.set(device_id, date_str, test_data, "emfit")
        
        # Should be able to retrieve it
        retrieved_data = cache_manager.get(device_id, date_str, "emfit")
        assert retrieved_data == test_data
        
        # Mock the cache file to be old (expired)
        cache_key = cache_manager._get_cache_key(device_id, date_str, "emfit")
        cache_path = cache_manager._get_cache_path(cache_key)
        
        # Set file time to be older than TTL
        old_time = datetime.now() - timedelta(hours=cache_manager.ttl_hours + 1)
        cache_path.touch()
        cache_path.stat().st_mtime = old_time.timestamp()
        
        # Should not be able to retrieve expired data
        retrieved_data = cache_manager.get(device_id, date_str, "emfit")
        assert retrieved_data is None

    def test_cache_clear_expired_with_plugin_names(self, cache_manager):
        """
        Verify that expired cache files associated with specific plugin names are correctly identified and removed, while valid cache files remain intact.
        """
        device_id = "test_device_123"
        date_str = "2024-01-15"
        test_data = {"sleep_score": 85, "hr": 65, "rr": 14}
        
        # Cache data for multiple plugins
        cache_manager.set(device_id, date_str, test_data, "emfit")
        cache_manager.set(device_id, date_str, test_data, "oura")
        
        # Get cache files
        cache_files = list(cache_manager.cache_dir.glob("*.json"))
        assert len(cache_files) == 2
        
        # Make one file expired by changing its timestamp
        old_time = datetime.now() - timedelta(hours=cache_manager.ttl_hours + 1)
        cache_files[0].touch()
        cache_files[0].stat().st_mtime = old_time.timestamp()
        
        # Clear expired files
        removed_count = cache_manager.clear_expired()
        assert removed_count >= 1  # At least one file should be removed
        
        # Should still have the valid file
        remaining_files = list(cache_manager.cache_dir.glob("*.json"))
        assert len(remaining_files) >= 1

    def test_cache_stats_with_plugin_names(self, cache_manager):
        """
        Verify that cache statistics accurately report the total, valid, and expired cache files when data is cached under multiple plugin names.
        """
        device_id = "test_device_123"
        date_str = "2024-01-15"
        test_data = {"sleep_score": 85, "hr": 65, "rr": 14}
        
        # Cache data for multiple plugins
        cache_manager.set(device_id, date_str, test_data, "emfit")
        cache_manager.set(device_id, date_str, test_data, "oura")
        cache_manager.set(device_id, date_str, test_data, "eight")
        
        # Get stats
        stats = cache_manager.get_stats()
        
        assert stats["total_files"] == 3
        assert stats["valid_files"] == 3
        assert stats["expired_files"] == 0
        assert isinstance(stats, dict)
        assert all(isinstance(v, int) for v in stats.values())