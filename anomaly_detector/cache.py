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

    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.ttl_hours = ttl_hours
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_key(self, device_id: str, date: str) -> str:
        """Generate cache key for a device/date combo."""
        key_data = f"{device_id}:{date}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the cache file path for a key."""
        return self.cache_dir / f"{cache_key}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file is still valid (not expired)."""
        if not cache_path.exists():
            return False

        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry_time = datetime.now() - timedelta(hours=self.ttl_hours)
        return file_time > expiry_time

    def get(self, device_id_or_key: str, date: str = None) -> dict | None:
        """Get cached API response if available and valid.
        
        Args:
            device_id_or_key: Either a device_id (old format) or a cache key (new format)
            date: Date string (required for old format, ignored for new format)
            
        Returns:
            Cached data if available and valid, None otherwise
        """
        if date is None:
            # New format: device_id_or_key is actually a cache key
            cache_key = hashlib.md5(device_id_or_key.encode()).hexdigest()
        else:
            # Old format: generate cache key from device_id and date
            cache_key = self._get_cache_key(device_id_or_key, date)
        
        cache_path = self._get_cache_path(cache_key)

        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path) as f:
                    return json.load(f)
            except Exception as e:
                logging.debug(f"Cache read error for {device_id_or_key}: {e}")
                return None
        return None

    def set(self, device_id_or_key: str, date_or_data: str | dict, data: dict = None) -> None:
        """Cache API response data.
        
        Args:
            device_id_or_key: Either a device_id (old format) or a cache key (new format)
            date_or_data: Date string (old format) or data dict (new format)
            data: Data dict (old format only)
        """
        if data is None:
            # New format: device_id_or_key is a cache key, date_or_data is the data
            cache_key = hashlib.md5(device_id_or_key.encode()).hexdigest()
            cache_data = date_or_data
            log_key = device_id_or_key
        else:
            # Old format: generate cache key from device_id and date
            cache_key = self._get_cache_key(device_id_or_key, date_or_data)
            cache_data = data
            log_key = date_or_data
        
        cache_path = self._get_cache_path(cache_key)

        try:
            with open(cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logging.debug(f"Cache write error for {log_key}: {e}")

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
