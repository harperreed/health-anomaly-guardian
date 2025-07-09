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
        """Create a temporary cache directory."""
        return tmp_path / "cache"

    @pytest.fixture
    def cache_manager(self, cache_dir):
        """Create a CacheManager instance."""
        return CacheManager(cache_dir, ttl_hours=24)

    def test_cache_key_generation_with_plugin_name(self, cache_manager):
        """Test that cache keys are different for different plugins."""
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
        """Test that cache key generation is consistent for same inputs."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        
        key1 = cache_manager._get_cache_key(device_id, date_str, plugin_name)
        key2 = cache_manager._get_cache_key(device_id, date_str, plugin_name)
        
        assert key1 == key2

    def test_cache_set_and_get_with_plugin_name(self, cache_manager):
        """Test caching with plugin names."""
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
        """Test that plugins can cache data independently."""
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
        """Test that cache still works without plugin names."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        test_data = {"sleep_score": 85, "hr": 65, "rr": 14}
        
        # Cache data without plugin name
        cache_manager.set(device_id, date_str, test_data)
        
        # Should be able to retrieve it without plugin name
        retrieved_data = cache_manager.get(device_id, date_str)
        assert retrieved_data == test_data

    def test_cache_collision_prevention(self, cache_manager):
        """Test that cache prevents collisions between plugins with same device IDs."""
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
        """Test that cache expiration works properly with plugin names."""
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
        """Test clearing expired cache files works with plugin names."""
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
        """Test cache statistics work with plugin names."""
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