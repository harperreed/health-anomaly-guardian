"""
ABOUTME: Unit tests for cache management functionality
ABOUTME: Tests CacheManager class for JSON-based API response caching
"""

import time
from datetime import datetime, timedelta

from anomaly_detector.cache import CacheManager


class TestCacheManager:
    """Test CacheManager class."""

    def test_cache_manager_init_creates_directory(self, temp_dir):
        """Test that CacheManager creates cache directory on init."""
        cache_dir = temp_dir / "new_cache"
        assert not cache_dir.exists()

        cache = CacheManager(cache_dir, ttl_hours=1)
        assert cache_dir.exists()
        assert cache.cache_dir == cache_dir
        assert cache.ttl_hours == 1

    def test_cache_manager_init_existing_directory(self, temp_dir):
        """Test that CacheManager works with existing directory."""
        cache_dir = temp_dir / "existing_cache"
        cache_dir.mkdir()

        cache = CacheManager(cache_dir, ttl_hours=2)
        assert cache_dir.exists()
        assert cache.cache_dir == cache_dir
        assert cache.ttl_hours == 2

    def test_get_cache_key_generates_consistent_hash(self, cache_manager):
        """Test that cache key generation is consistent."""
        key1 = cache_manager._get_cache_key("device123", "2024-01-15")
        key2 = cache_manager._get_cache_key("device123", "2024-01-15")
        key3 = cache_manager._get_cache_key("device456", "2024-01-15")

        assert key1 == key2  # Same inputs produce same key
        assert key1 != key3  # Different inputs produce different keys
        assert len(key1) == 32  # MD5 hash length

    def test_get_cache_path(self, cache_manager):
        """Test cache path generation."""
        cache_key = "abcdef123456"
        path = cache_manager._get_cache_path(cache_key)

        assert path.name == "abcdef123456.json"
        assert path.parent == cache_manager.cache_dir

    def test_set_and_get_cache_data(self, cache_manager):
        """Test setting and getting cache data."""
        device_id = "test_device"
        date = "2024-01-15"
        test_data = {"temperature": 25.5, "humidity": 60, "readings": [1, 2, 3]}

        # Cache should be empty initially
        result = cache_manager.get(device_id, date)
        assert result is None

        # Set cache data
        cache_manager.set(device_id, date, test_data)

        # Get cache data
        result = cache_manager.get(device_id, date)
        assert result == test_data

    def test_cache_expiry(self, temp_dir):
        """Test that cache entries expire after TTL."""
        cache = CacheManager(
            temp_dir / "cache", ttl_hours=0.000001
        )  # Very short TTL (0.0036 seconds)
        device_id = "test_device"
        date = "2024-01-15"
        test_data = {"test": "data"}

        # Set cache data
        cache.set(device_id, date, test_data)

        # Should be available immediately
        result = cache.get(device_id, date)
        assert result == test_data

        # Wait for expiry (small delay)
        time.sleep(0.01)  # 10ms should be enough for 3.6ms TTL

        # Should be expired now
        result = cache.get(device_id, date)
        assert result is None

    def test_cache_invalid_json_handling(self, cache_manager):
        """Test handling of corrupted cache files."""
        device_id = "test_device"
        date = "2024-01-15"

        # Create a corrupted cache file
        cache_key = cache_manager._get_cache_key(device_id, date)
        cache_path = cache_manager._get_cache_path(cache_key)
        cache_path.write_text("invalid json content")

        # Should return None for corrupted cache
        result = cache_manager.get(device_id, date)
        assert result is None

    def test_cache_different_devices_separate(self, cache_manager):
        """Test that different devices have separate cache entries."""
        date = "2024-01-15"
        device1_data = {"device": "1", "value": 100}
        device2_data = {"device": "2", "value": 200}

        cache_manager.set("device1", date, device1_data)
        cache_manager.set("device2", date, device2_data)

        assert cache_manager.get("device1", date) == device1_data
        assert cache_manager.get("device2", date) == device2_data

    def test_cache_different_dates_separate(self, cache_manager):
        """Test that different dates have separate cache entries."""
        device_id = "test_device"
        date1_data = {"date": "2024-01-15", "value": 100}
        date2_data = {"date": "2024-01-16", "value": 200}

        cache_manager.set(device_id, "2024-01-15", date1_data)
        cache_manager.set(device_id, "2024-01-16", date2_data)

        assert cache_manager.get(device_id, "2024-01-15") == date1_data
        assert cache_manager.get(device_id, "2024-01-16") == date2_data

    def test_clear_expired_removes_old_files(self, temp_dir):
        """Test that clear_expired removes only expired files."""
        cache = CacheManager(temp_dir / "cache", ttl_hours=1)

        # Create some cache files
        valid_data = {"valid": True}
        expired_data = {"expired": True}

        cache.set("device1", "2024-01-15", valid_data)
        cache.set("device2", "2024-01-16", expired_data)

        # Manually age one file to make it expired
        device2_key = cache._get_cache_key("device2", "2024-01-16")
        device2_path = cache._get_cache_path(device2_key)

        # Set file time to 2 hours ago (beyond TTL)
        old_time = (datetime.now() - timedelta(hours=2)).timestamp()
        device2_path.touch()
        # Get the stat for reference (line required for timestamp setup)
        _ = device2_path.stat().st_mtime
        import os

        os.utime(device2_path, (old_time, old_time))

        # Clear expired files
        removed_count = cache.clear_expired()

        assert removed_count == 1
        assert cache.get("device1", "2024-01-15") == valid_data  # Still available
        assert cache.get("device2", "2024-01-16") is None  # Removed

    def test_get_stats(self, cache_manager):
        """Test cache statistics."""
        # Initially empty
        stats = cache_manager.get_stats()
        assert stats["total_files"] == 0
        assert stats["valid_files"] == 0
        assert stats["expired_files"] == 0

        # Add some cache entries
        cache_manager.set("device1", "2024-01-15", {"data": 1})
        cache_manager.set("device2", "2024-01-16", {"data": 2})

        stats = cache_manager.get_stats()
        assert stats["total_files"] == 2
        assert stats["valid_files"] == 2
        assert stats["expired_files"] == 0

    def test_cache_handles_complex_data_types(self, cache_manager):
        """Test that cache handles complex nested data structures."""
        complex_data = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3, "four"],
            "nested": {"level2": {"level3": "deep_value"}},
        }

        cache_manager.set("device", "2024-01-15", complex_data)
        result = cache_manager.get("device", "2024-01-15")

        assert result == complex_data
