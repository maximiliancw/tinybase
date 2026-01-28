"""
Rate limiting for concurrent function execution.

Provides backend abstraction for tracking concurrent function executions
per user using either DiskCache or Redis.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

import diskcache
import redis
from fastapi import HTTPException, status

from tinybase.auth import CurrentUserOptional
from tinybase.settings import config, settings

logger = logging.getLogger(__name__)


# =============================================================================
# Backend Abstraction
# =============================================================================


class RateLimitBackend(ABC):
    """Abstract base class for rate limiting backends."""

    @abstractmethod
    def increment(self, key: str, ttl: int = 3600) -> int:
        """
        Increment counter for a key and return new value.

        Args:
            key: The counter key.
            ttl: Time-to-live in seconds for the counter.

        Returns:
            New counter value after increment.
        """
        pass

    @abstractmethod
    def decrement(self, key: str) -> int:
        """
        Decrement counter for a key and return new value.

        Args:
            key: The counter key.

        Returns:
            New counter value after decrement.
        """
        pass

    @abstractmethod
    def get(self, key: str) -> int:
        """
        Get current counter value for a key.

        Args:
            key: The counter key.

        Returns:
            Current counter value (0 if key doesn't exist).
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete a counter key.

        Args:
            key: The counter key to delete.
        """
        pass


# =============================================================================
# DiskCache Backend
# =============================================================================


class DiskCacheBackend(RateLimitBackend):
    """Rate limiting backend using DiskCache for local file-based storage."""

    def __init__(self, cache_dir: str):
        """
        Initialize DiskCache backend.

        Args:
            cache_dir: Directory path for cache storage.
        """
        self.cache = diskcache.Cache(cache_dir)

    def increment(self, key: str, ttl: int = 3600) -> int:
        """Increment counter using atomic DiskCache operation."""
        # DiskCache incr() is atomic and thread-safe
        new_value = self.cache.incr(key, default=0)
        # Set expiration on the key
        self.cache.touch(key, expire=ttl)
        return new_value

    def decrement(self, key: str) -> int:
        """Decrement counter using atomic DiskCache operation."""
        # Use incr with negative value for decrement
        new_value = self.cache.incr(key, delta=-1, default=0)
        # Don't let it go below 0
        if new_value < 0:
            self.cache.set(key, 0)
            return 0
        return new_value

    def get(self, key: str) -> int:
        """Get current counter value."""
        value = self.cache.get(key, default=0)
        return int(value) if value is not None else 0

    def delete(self, key: str) -> None:
        """Delete counter key."""
        self.cache.delete(key)


# =============================================================================
# Redis Backend
# =============================================================================


class RedisBackend(RateLimitBackend):
    """Rate limiting backend using Redis for distributed storage."""

    def __init__(self, redis_url: str):
        """
        Initialize Redis backend.

        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0").
        """
        self.client = redis.from_url(redis_url, decode_responses=True)

    def increment(self, key: str, ttl: int = 3600) -> int:
        """Increment counter using atomic Redis INCR command."""
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        results = pipe.execute()
        return int(results[0])

    def decrement(self, key: str) -> int:
        """Decrement counter using atomic Redis DECR command."""
        new_value = self.client.decr(key)
        # Don't let it go below 0
        if new_value < 0:
            self.client.set(key, 0)
            return 0
        return new_value

    def get(self, key: str) -> int:
        """Get current counter value."""
        value = self.client.get(key)
        return int(value) if value is not None else 0

    def delete(self, key: str) -> None:
        """Delete counter key."""
        self.client.delete(key)


# =============================================================================
# Backend Factory
# =============================================================================


_backend_instance: RateLimitBackend | None = None


def get_rate_limit_backend() -> RateLimitBackend:
    """
    Get the rate limiting backend instance.

    Uses singleton pattern to reuse backend connections.

    Returns:
        RateLimitBackend instance (DiskCache or Redis).
    """
    global _backend_instance

    if _backend_instance is not None:
        return _backend_instance

    if config.rate_limit_backend == "redis":
        if not config.rate_limit_redis_url:
            raise ValueError("rate_limit_redis_url is required when using Redis backend")
        logger.info(f"Initializing Redis rate limiting backend: {config.rate_limit_redis_url}")
        _backend_instance = RedisBackend(config.rate_limit_redis_url)
    else:
        logger.info(f"Initializing DiskCache rate limiting backend: {config.rate_limit_cache_dir}")
        _backend_instance = DiskCacheBackend(config.rate_limit_cache_dir)

    return _backend_instance


def reset_rate_limit_backend() -> None:
    """Reset the backend instance (primarily for testing)."""
    global _backend_instance
    _backend_instance = None


# =============================================================================
# FastAPI Dependency
# =============================================================================


async def check_rate_limit(
    user: CurrentUserOptional,
) -> AsyncGenerator[None, None]:
    """
    FastAPI dependency to enforce concurrent function execution limits.

    Uses yield to ensure cleanup (decrement) happens even on errors.
    This is the FastAPI-idiomatic way to handle resource cleanup.

    Args:
        user: Current authenticated user (None for anonymous/scheduled functions).

    Yields:
        None (allows request to proceed if rate limit not exceeded).

    Raises:
        HTTPException: 429 if rate limit is exceeded.
    """
    if not user:
        # No rate limiting for anonymous/scheduled functions
        yield
        return

    backend = get_rate_limit_backend()
    key = f"concurrent_functions:user:{user.id}"

    # Get max concurrent from runtime settings
    max_concurrent = settings.limits.max_concurrent_functions_per_user

    # Increment counter
    current = backend.increment(key, ttl=3600)

    if current > max_concurrent:
        # Over limit - decrement and reject
        backend.decrement(key)
        logger.warning(
            f"Rate limit exceeded for user {user.id}: {current}/{max_concurrent} concurrent functions"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: maximum {max_concurrent} concurrent functions per user",
            headers={"Retry-After": "60"},
        )

    logger.debug(f"Rate limit check passed for user {user.id}: {current}/{max_concurrent}")

    try:
        yield
    finally:
        # Always decrement, even on errors
        new_count = backend.decrement(key)
        logger.debug(
            f"Decremented rate limit counter for user {user.id}: {new_count}/{max_concurrent}"
        )
