import hashlib
import json
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import logging

# Configure a logger for cache events
logger = logging.getLogger(__name__)


class SimpleCache:
    """
    A simple, thread-safe, in-memory cache with Time-To-Live (TTL) support
    and user-specific invalidation.
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._expiry: Dict[str, datetime] = {}
        # This mapping allows for surgical invalidation of a single user's cache
        self._user_keys: Dict[str, set] = defaultdict(set)
        self._lock = threading.Lock()  # Ensures thread safety for concurrent requests
        self._hit_count = 0
        self._miss_count = 0

    def _make_key(self, user_id: str, endpoint: str, params: Dict[str, Any]) -> str:
        """Creates a deterministic, unique key from the request parameters."""
        # Using json.dumps ensures a standard representation and avoids collision (e.g., "a" + "11" vs "a1" + "1")
        # default=str handles objects like Decimal that might not be natively serializable
        param_string = json.dumps(params, sort_keys=True, default=str)
        key_data = f"{user_id}:{endpoint}:{param_string}"
        # Use a cryptographic hash to create a short, fixed-length key
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, user_id: str, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """Retrieves an item from the cache if it exists and has not expired."""
        key = self._make_key(user_id, endpoint, params)
        with self._lock:
            if key in self._cache:
                if datetime.now() < self._expiry[key]:
                    # Cache hit and it's valid
                    self._hit_count += 1
                    logger.info(f"CACHE HIT for key: {key}")
                    return self._cache[key]
                else:
                    # Cache hit but it's expired, so clean it up
                    self._cleanup_key(key, user_id)

            # Cache miss
            self._miss_count += 1
            logger.info(f"CACHE MISS for key: {key}")
            return None

    def set(self, user_id: str, endpoint: str, params: Dict[str, Any], value: Any, ttl_seconds: int = 300):
        """Adds an item to the cache with a specific TTL."""
        key = self._make_key(user_id, endpoint, params)
        with self._lock:
            self._cache[key] = value
            self._expiry[key] = datetime.now() + timedelta(seconds=ttl_seconds)
            self._user_keys[user_id].add(key)
            logger.info(f"CACHE SET for key: {key} with TTL {ttl_seconds}s")

    def invalidate_user(self, user_id: str):
        """Removes all cache entries associated with a specific user."""
        with self._lock:
            if user_id in self._user_keys:
                # Create a copy to iterate over
                keys_to_delete = list(self._user_keys[user_id])
                count = 0
                for key in keys_to_delete:
                    self._cleanup_key(key, user_id)
                    count += 1
                logger.info(
                    f"CACHE INVALIDATED {count} entries for user: {user_id}")

    def _cleanup_key(self, key: str, user_id: str):
        """Internal helper to remove a specific key and its associations."""
        self._cache.pop(key, None)
        self._expiry.pop(key, None)
        if user_id in self._user_keys and key in self._user_keys[user_id]:
            self._user_keys[user_id].remove(key)


# Create a single, global instance of the cache that the application will use.
# This pattern is called a singleton.
cache = SimpleCache()
