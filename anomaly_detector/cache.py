"""
ABOUTME: JSON-based caching system for API responses
ABOUTME: Provides TTL-based caching to reduce API calls and improve performance
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path


class CacheManager:
    """JSON-based caching for API responses."""

    def __init__(self, cache_dir: Path, ttl_hours: int = 87600):
        """
        Initialize the CacheManager with a cache directory and a time-to-live (TTL) in hours.

        Parameters:
            cache_dir (Path): Directory where cache files will be stored.
            ttl_hours (int, optional): Number of hours before a cache entry expires. Defaults to 87600 (10 years).
        """
        self.cache_dir = cache_dir
        self.ttl_hours = ttl_hours
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_key(self, device_id: str, date: str, plugin_name: str = None) -> str:
        """
        Generate a unique cache key by hashing the combination of device ID, date, and optionally a plugin name.

        Parameters:
            device_id (str): Identifier for the device.
            date (str): Date string associated with the cache entry.
            plugin_name (str, optional): Optional plugin context to further distinguish the cache key.

        Returns:
            str: MD5 hash string representing the cache key.
        """
        if plugin_name is not None:
            key_data = f"{plugin_name}:{device_id}:{date}"
        else:
            key_data = f"{device_id}:{date}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """
        Return the file path for the cache entry corresponding to the given cache key.

        Parameters:
            cache_key (str): The unique key identifying the cache entry.

        Returns:
            Path: The full path to the cache file.
        """
        return self.cache_dir / f"{cache_key}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """
        Determine whether the specified cache file exists and has not expired based on the configured TTL.

        Returns:
            bool: True if the cache file exists and is within the TTL window; False otherwise.
        """
        if not cache_path.exists():
            return False

        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry_time = datetime.now() - timedelta(hours=self.ttl_hours)
        return file_time > expiry_time

    def get(self, device_id: str, date: str, plugin_name: str = None) -> dict | None:
        """
        Retrieve cached API response data for the specified device, date, and optional plugin if the cache entry exists and is not expired.

        Parameters:
            device_id (str): Identifier for the device.
            date (str): Date string associated with the cache entry.
            plugin_name (str, optional): Name of the plugin to further distinguish the cache entry.

        Returns:
            dict | None: Cached data as a dictionary if available and valid; otherwise, None.
        """
        cache_key = self._get_cache_key(device_id, date, plugin_name)
        cache_path = self._get_cache_path(cache_key)

        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path) as f:
                    return json.load(f)
            except Exception as e:
                logging.debug(f"Cache read error for {date}: {e}")
                return None
        return None

    def set(
        self, device_id: str, date: str, data: dict, plugin_name: str = None
    ) -> None:
        """
        Stores API response data in the cache for the specified device, date, and optional plugin context.

        Parameters:
            device_id (str): Identifier for the device.
            date (str): Date string associated with the cached data.
            data (dict): The API response data to cache.
            plugin_name (str, optional): Name of the plugin to distinguish cache entries.
        """
        cache_key = self._get_cache_key(device_id, date, plugin_name)
        cache_path = self._get_cache_path(cache_key)

        try:
            # Ensure parent directory exists
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.debug(f"Cache write error for {date}: {e}")

    def clear_expired(self) -> int:
        """Remove expired cache files and return count removed."""
        removed = 0
        for cache_file in self.cache_dir.glob("*.json"):
            if not self._is_cache_valid(cache_file):
                try:
                    cache_file.unlink()
                    removed += 1
                except Exception as e:
                    logging.debug(f"Error removing {cache_file}: {e}")
        return removed

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        cache_files = list(self.cache_dir.glob("*.json"))
        valid_files = [f for f in cache_files if self._is_cache_valid(f)]

        return {
            "total_files": len(cache_files),
            "valid_files": len(valid_files),
            "expired_files": len(cache_files) - len(valid_files),
        }
