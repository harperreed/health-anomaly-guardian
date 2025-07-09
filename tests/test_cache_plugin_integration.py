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

    def test_cache_key_generation_edge_cases(self, cache_manager):
        """Test cache key generation with edge cases."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        
        # Test with empty plugin name
        key_empty = cache_manager._get_cache_key(device_id, date_str, "")
        key_none = cache_manager._get_cache_key(device_id, date_str, None)
        key_no_plugin = cache_manager._get_cache_key(device_id, date_str)
        
        # Empty string should be different from None and no plugin
        assert key_empty != key_none
        assert key_empty != key_no_plugin
        assert key_none == key_no_plugin  # None should be treated same as no plugin
        
        # Test with special characters in plugin name
        key_special = cache_manager._get_cache_key(device_id, date_str, "plugin-with_special.chars")
        key_unicode = cache_manager._get_cache_key(device_id, date_str, "plugin_ñ_测试")
        
        assert key_special != key_unicode
        assert key_special != key_none
        assert key_unicode != key_none

    def test_cache_with_invalid_json_file(self, cache_manager):
        """Test cache behavior when cache file contains invalid JSON."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        
        # Create cache key and path
        cache_key = cache_manager._get_cache_key(device_id, date_str, plugin_name)
        cache_path = cache_manager._get_cache_path(cache_key)
        
        # Ensure cache directory exists
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write invalid JSON to cache file
        cache_path.write_text("invalid json content {")
        
        # Should return None for corrupted cache file
        result = cache_manager.get(device_id, date_str, plugin_name)
        assert result is None

    def test_cache_with_different_data_types(self, cache_manager):
        """Test caching various data types."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        
        # Test with different data types
        test_cases = [
            ("emfit", {"nested": {"dict": {"value": 42}}}),
            ("oura", [1, 2, 3, "string", {"nested": True}]),
            ("eight", "simple string"),
            ("garmin", 12345),
            ("fitbit", 123.45),
            ("withings", True),
            ("polar", None),
            ("suunto", []),
            ("jawbone", {}),
        ]
        
        for plugin_name, test_data in test_cases:
            cache_manager.set(device_id, date_str, test_data, plugin_name)
            retrieved = cache_manager.get(device_id, date_str, plugin_name)
            assert retrieved == test_data

    def test_cache_with_large_data(self, cache_manager):
        """Test caching large data sets."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        
        # Create large data structure
        large_data = {
            "measurements": [{"timestamp": i, "value": i * 0.1} for i in range(10000)],
            "metadata": {"device": device_id, "plugin": plugin_name},
            "large_string": "x" * 100000
        }
        
        # Should be able to cache and retrieve large data
        cache_manager.set(device_id, date_str, large_data, plugin_name)
        retrieved = cache_manager.get(device_id, date_str, plugin_name)
        assert retrieved == large_data

    def test_cache_concurrent_access_simulation(self, cache_manager):
        """Test cache behavior under simulated concurrent access."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        
        # Simulate concurrent writes to different plugins
        plugins_data = {
            "emfit": {"sleep_score": 85, "thread": "emfit"},
            "oura": {"sleep_score": 90, "thread": "oura"},
            "eight": {"sleep_score": 80, "thread": "eight"},
            "garmin": {"sleep_score": 75, "thread": "garmin"},
            "fitbit": {"sleep_score": 95, "thread": "fitbit"}
        }
        
        # Write all data simultaneously
        for plugin_name, data in plugins_data.items():
            cache_manager.set(device_id, date_str, data, plugin_name)
        
        # Verify all data can be retrieved correctly
        for plugin_name, expected_data in plugins_data.items():
            retrieved = cache_manager.get(device_id, date_str, plugin_name)
            assert retrieved == expected_data

    def test_cache_directory_creation_failure(self, cache_manager):
        """Test behavior when cache directory cannot be created."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        test_data = {"sleep_score": 85}
        
        # Mock Path.mkdir to raise PermissionError
        with patch.object(Path, 'mkdir', side_effect=PermissionError("Permission denied")):
            # Should handle the error gracefully
            cache_manager.set(device_id, date_str, test_data, plugin_name)
            
            # Should return None when can't read due to directory issues
            result = cache_manager.get(device_id, date_str, plugin_name)
            assert result is None

    def test_cache_file_write_permission_error(self, cache_manager):
        """Test behavior when cache file cannot be written due to permission error."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        test_data = {"sleep_score": 85}
        
        # Mock Path.write_text to raise PermissionError
        with patch.object(Path, 'write_text', side_effect=PermissionError("Permission denied")):
            # Should handle the error gracefully without crashing
            cache_manager.set(device_id, date_str, test_data, plugin_name)
            
            # Should return None when can't write
            result = cache_manager.get(device_id, date_str, plugin_name)
            assert result is None

    def test_cache_file_read_permission_error(self, cache_manager):
        """Test behavior when cache file cannot be read due to permission error."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        test_data = {"sleep_score": 85}
        
        # First set the data successfully
        cache_manager.set(device_id, date_str, test_data, plugin_name)
        
        # Mock Path.read_text to raise PermissionError
        with patch.object(Path, 'read_text', side_effect=PermissionError("Permission denied")):
            result = cache_manager.get(device_id, date_str, plugin_name)
            assert result is None

    def test_cache_with_extreme_plugin_names(self, cache_manager):
        """Test cache with extreme plugin name cases."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        test_data = {"sleep_score": 85}
        
        extreme_plugin_names = [
            "a" * 255,  # Very long plugin name
            "plugin with spaces",
            "plugin/with/slashes",
            "plugin\\with\\backslashes",
            "plugin:with:colons",
            "plugin|with|pipes",
            "plugin*with*wildcards",
            "plugin?with?questions",
            "plugin<with>brackets",
            "plugin\"with\"quotes",
            "plugin'with'single'quotes",
            "plugin\nwith\nnewlines",
            "plugin\twith\ttabs",
        ]
        
        for plugin_name in extreme_plugin_names:
            cache_manager.set(device_id, date_str, test_data, plugin_name)
            retrieved = cache_manager.get(device_id, date_str, plugin_name)
            assert retrieved == test_data

    def test_cache_with_extreme_device_ids(self, cache_manager):
        """Test cache with extreme device ID cases."""
        date_str = "2024-01-15"
        plugin_name = "emfit"
        test_data = {"sleep_score": 85}
        
        extreme_device_ids = [
            "",  # Empty device ID
            "a" * 1000,  # Very long device ID
            "device with spaces",
            "device/with/slashes",
            "device\\with\\backslashes",
            "device:with:colons",
            "device|with|pipes",
            "device*with*wildcards",
            "device?with?questions",
            "device<with>brackets",
            "device\"with\"quotes",
            "device'with'single'quotes",
            "device\nwith\nnewlines",
            "device\twith\ttabs",
            "device_ñ_测试_🎯",  # Unicode characters
        ]
        
        for device_id in extreme_device_ids:
            cache_manager.set(device_id, date_str, test_data, plugin_name)
            retrieved = cache_manager.get(device_id, date_str, plugin_name)
            assert retrieved == test_data

    def test_cache_with_extreme_date_strings(self, cache_manager):
        """Test cache with extreme date string cases."""
        device_id = "test_device_123"
        plugin_name = "emfit"
        test_data = {"sleep_score": 85}
        
        extreme_date_strings = [
            "",  # Empty date string
            "2024-01-01",  # Standard format
            "01/01/2024",  # Different format
            "2024-13-45",  # Invalid date
            "not-a-date",  # Completely invalid
            "2024-01-01T00:00:00Z",  # ISO format
            "a" * 100,  # Very long date string
            "date with spaces",
            "date/with/slashes",
            "date\\with\\backslashes",
            "date:with:colons",
            "date|with|pipes",
            "date\nwith\nnewlines",
            "date\twith\ttabs",
            "date_ñ_测试_🎯",  # Unicode characters
        ]
        
        for date_str in extreme_date_strings:
            cache_manager.set(device_id, date_str, test_data, plugin_name)
            retrieved = cache_manager.get(device_id, date_str, plugin_name)
            assert retrieved == test_data

    def test_cache_stats_with_mixed_valid_invalid_files(self, cache_manager):
        """Test cache stats with mix of valid and invalid cache files."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        test_data = {"sleep_score": 85}
        
        # Create some valid cache entries
        cache_manager.set(device_id, date_str, test_data, "emfit")
        cache_manager.set(device_id, date_str, test_data, "oura")
        
        # Create some invalid cache files directly
        cache_dir = cache_manager.cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create corrupted JSON file
        corrupted_file = cache_dir / "corrupted.json"
        corrupted_file.write_text("invalid json {")
        
        # Create expired file
        expired_file = cache_dir / "expired.json"
        expired_file.write_text('{"data": "test", "timestamp": "2020-01-01T00:00:00"}')
        
        # Create empty file
        empty_file = cache_dir / "empty.json"
        empty_file.write_text("")
        
        # Get stats
        stats = cache_manager.get_stats()
        
        # Should correctly identify valid vs invalid files
        assert stats["total_files"] >= 5
        assert stats["valid_files"] >= 2
        assert stats["expired_files"] >= 1

    def test_cache_clear_expired_with_permission_errors(self, cache_manager):
        """Test clearing expired cache files when some files cannot be deleted."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        test_data = {"sleep_score": 85}
        
        # Cache some data
        cache_manager.set(device_id, date_str, test_data, "emfit")
        cache_manager.set(device_id, date_str, test_data, "oura")
        
        # Mock the removal to fail for some files
        original_unlink = Path.unlink
        def mock_unlink(self, missing_ok=False):
            if "emfit" in str(self):
                raise PermissionError("Permission denied")
            return original_unlink(self, missing_ok)
        
        with patch.object(Path, 'unlink', mock_unlink):
            # Should handle permission errors gracefully
            removed_count = cache_manager.clear_expired()
            # Should still work for files that can be removed
            assert removed_count >= 0

    def test_cache_get_with_disk_space_error(self, cache_manager):
        """Test cache get operation when disk space is full."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        test_data = {"sleep_score": 85}
        
        # First set the data successfully
        cache_manager.set(device_id, date_str, test_data, plugin_name)
        
        # Mock Path.read_text to raise OSError (disk full)
        with patch.object(Path, 'read_text', side_effect=OSError("No space left on device")):
            result = cache_manager.get(device_id, date_str, plugin_name)
            assert result is None

    def test_cache_set_with_disk_space_error(self, cache_manager):
        """Test cache set operation when disk space is full."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        test_data = {"sleep_score": 85}
        
        # Mock Path.write_text to raise OSError (disk full)
        with patch.object(Path, 'write_text', side_effect=OSError("No space left on device")):
            # Should handle the error gracefully without crashing
            cache_manager.set(device_id, date_str, test_data, plugin_name)
            
            # Verify it doesn't crash and returns None when trying to read
            result = cache_manager.get(device_id, date_str, plugin_name)
            assert result is None

    def test_cache_with_zero_ttl(self, tmp_path):
        """Test cache behavior with zero TTL (immediate expiration)."""
        cache_dir = tmp_path / "cache"
        cache_manager = CacheManager(cache_dir, ttl_hours=0)
        
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        test_data = {"sleep_score": 85}
        
        # Cache data with zero TTL
        cache_manager.set(device_id, date_str, test_data, plugin_name)
        
        # Should immediately be considered expired
        result = cache_manager.get(device_id, date_str, plugin_name)
        assert result is None

    def test_cache_with_negative_ttl(self, tmp_path):
        """Test cache behavior with negative TTL."""
        cache_dir = tmp_path / "cache"
        cache_manager = CacheManager(cache_dir, ttl_hours=-1)
        
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        test_data = {"sleep_score": 85}
        
        # Cache data with negative TTL
        cache_manager.set(device_id, date_str, test_data, plugin_name)
        
        # Should be considered expired
        result = cache_manager.get(device_id, date_str, plugin_name)
        assert result is None

    def test_cache_with_very_large_ttl(self, tmp_path):
        """Test cache behavior with very large TTL."""
        cache_dir = tmp_path / "cache"
        cache_manager = CacheManager(cache_dir, ttl_hours=8760 * 100)  # 100 years
        
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        test_data = {"sleep_score": 85}
        
        # Cache data with very large TTL
        cache_manager.set(device_id, date_str, test_data, plugin_name)
        
        # Should be able to retrieve it
        result = cache_manager.get(device_id, date_str, plugin_name)
        assert result == test_data

    def test_cache_file_system_race_condition(self, cache_manager):
        """Test cache behavior when file system operations race."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        test_data = {"sleep_score": 85}
        
        # Set data first
        cache_manager.set(device_id, date_str, test_data, plugin_name)
        
        # Mock Path.exists to return False during get operation to simulate race condition
        original_exists = Path.exists
        def mock_exists(self):
            if "emfit" in str(self):
                return False
            return original_exists(self)
        
        with patch.object(Path, 'exists', mock_exists):
            result = cache_manager.get(device_id, date_str, plugin_name)
            assert result is None

    def test_cache_json_serialization_error(self, cache_manager):
        """Test cache behavior when JSON serialization fails."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        
        # Create data that cannot be JSON serialized
        class UnserializableClass:
            def __init__(self):
                self.value = "test"
        
        unserializable_data = {
            "normal_data": {"sleep_score": 85},
            "unserializable": UnserializableClass()
        }
        
        # Mock json.dumps to raise TypeError
        with patch('json.dumps', side_effect=TypeError("Object is not JSON serializable")):
            # Should handle the error gracefully
            cache_manager.set(device_id, date_str, unserializable_data, plugin_name)
            
            # Should return None when can't serialize
            result = cache_manager.get(device_id, date_str, plugin_name)
            assert result is None

    def test_cache_boundary_timestamp_conditions(self, cache_manager):
        """Test cache behavior at TTL boundary conditions."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        test_data = {"sleep_score": 85}
        
        # Set data
        cache_manager.set(device_id, date_str, test_data, plugin_name)
        
        # Get cache file path
        cache_key = cache_manager._get_cache_key(device_id, date_str, plugin_name)
        cache_path = cache_manager._get_cache_path(cache_key)
        
        # Test exactly at TTL boundary
        boundary_time = datetime.now() - timedelta(hours=cache_manager.ttl_hours)
        
        # Mock file modification time to be exactly at boundary
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_mtime = boundary_time.timestamp()
            
            # Should be considered expired (boundary is exclusive)
            result = cache_manager.get(device_id, date_str, plugin_name)
            assert result is None
        
        # Test just before boundary (should be valid)
        just_before_boundary = boundary_time + timedelta(seconds=1)
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_mtime = just_before_boundary.timestamp()
            
            result = cache_manager.get(device_id, date_str, plugin_name)
            assert result == test_data

    def test_cache_multiple_plugin_name_formats(self, cache_manager):
        """Test cache with various plugin name formats and casing."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        test_data = {"sleep_score": 85}
        
        plugin_variations = [
            "emfit",
            "EMFIT",
            "Emfit",
            "emFIT",
            "oura",
            "OURA",
            "Oura",
            "oURA",
            "eight_sleep",
            "EIGHT_SLEEP",
            "Eight_Sleep",
            "eight-sleep",
            "EIGHT-SLEEP",
            "Eight-Sleep",
        ]
        
        # Cache data with each variation
        for plugin_name in plugin_variations:
            cache_manager.set(device_id, date_str, test_data, plugin_name)
        
        # Each variation should be treated as separate cache entries
        for plugin_name in plugin_variations:
            result = cache_manager.get(device_id, date_str, plugin_name)
            assert result == test_data
        
        # Verify they are all different cache entries
        cache_files = list(cache_manager.cache_dir.glob("*.json"))
        assert len(cache_files) == len(plugin_variations)

    def test_cache_cleanup_on_corruption(self, cache_manager):
        """Test that cache automatically cleans up corrupted files."""
        device_id = "test_device_123"
        date_str = "2024-01-15"
        plugin_name = "emfit"
        
        # Create cache key and path
        cache_key = cache_manager._get_cache_key(device_id, date_str, plugin_name)
        cache_path = cache_manager._get_cache_path(cache_key)
        
        # Ensure cache directory exists
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write corrupted data
        cache_path.write_text("corrupted json data {")
        
        # Verify file exists
        assert cache_path.exists()
        
        # Try to get data (should fail and potentially clean up)
        result = cache_manager.get(device_id, date_str, plugin_name)
        assert result is None
        
        # Now try to set new data in the same location
        new_data = {"sleep_score": 90}
        cache_manager.set(device_id, date_str, new_data, plugin_name)
        
        # Should be able to retrieve new data
        result = cache_manager.get(device_id, date_str, plugin_name)
        assert result == new_data