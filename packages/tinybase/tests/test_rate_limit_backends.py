"""
Tests for rate limiting backends and dependencies.

Tests the rate limiting module including:
- DiskCacheBackend operations
- RedisBackend operations (mocked)
- check_rate_limit FastAPI dependency
- Backend factory and singleton management
"""

import tempfile
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from tinybase.rate_limit import (
    DiskCacheBackend,
    RedisBackend,
    check_rate_limit,
    get_rate_limit_backend,
    reset_rate_limit_backend,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def diskcache_backend():
    """Create a DiskCacheBackend with a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = DiskCacheBackend(tmpdir)
        yield backend


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock_client = MagicMock()

    # Mock pipeline
    mock_pipe = MagicMock()
    mock_pipe.incr.return_value = None
    mock_pipe.expire.return_value = None
    mock_pipe.execute.return_value = [1, True]  # [incr result, expire result]
    mock_client.pipeline.return_value = mock_pipe

    # Mock direct methods
    mock_client.get.return_value = None
    mock_client.decr.return_value = 0
    mock_client.set.return_value = True
    mock_client.delete.return_value = 1

    return mock_client


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock()
    user.id = uuid4()
    return user


@pytest.fixture(autouse=True)
def reset_backend():
    """Reset the rate limit backend singleton before and after each test."""
    reset_rate_limit_backend()
    yield
    reset_rate_limit_backend()


# =============================================================================
# DiskCacheBackend Tests
# =============================================================================


def test_diskcache_increment(diskcache_backend):
    """Test incrementing counter in DiskCache."""
    key = "test:counter"

    result1 = diskcache_backend.increment(key)
    assert result1 == 1

    result2 = diskcache_backend.increment(key)
    assert result2 == 2


def test_diskcache_increment_with_ttl(diskcache_backend):
    """Test increment sets TTL."""
    key = "test:ttl"

    diskcache_backend.increment(key, ttl=60)

    # Key should exist
    value = diskcache_backend.get(key)
    assert value == 1


def test_diskcache_decrement(diskcache_backend):
    """Test decrementing counter in DiskCache."""
    key = "test:counter"

    diskcache_backend.increment(key)
    diskcache_backend.increment(key)

    result = diskcache_backend.decrement(key)
    assert result == 1


def test_diskcache_decrement_no_negative(diskcache_backend):
    """Test decrement doesn't go below 0."""
    key = "test:negative"

    # Decrement non-existent key
    result = diskcache_backend.decrement(key)
    assert result == 0

    # Decrement from 0
    result = diskcache_backend.decrement(key)
    assert result == 0


def test_diskcache_get_nonexistent(diskcache_backend):
    """Test getting non-existent key returns 0."""
    value = diskcache_backend.get("nonexistent")
    assert value == 0


def test_diskcache_get_existing(diskcache_backend):
    """Test getting existing key."""
    key = "test:get"
    diskcache_backend.increment(key)
    diskcache_backend.increment(key)

    value = diskcache_backend.get(key)
    assert value == 2


def test_diskcache_delete(diskcache_backend):
    """Test deleting a key."""
    key = "test:delete"

    diskcache_backend.increment(key)
    assert diskcache_backend.get(key) == 1

    diskcache_backend.delete(key)
    assert diskcache_backend.get(key) == 0


def test_diskcache_delete_nonexistent(diskcache_backend):
    """Test deleting non-existent key doesn't raise."""
    diskcache_backend.delete("nonexistent")


# =============================================================================
# RedisBackend Tests
# =============================================================================


def test_redis_backend_init():
    """Test RedisBackend initialization."""
    with patch("tinybase.rate_limit.redis.from_url") as mock_from_url:
        mock_from_url.return_value = MagicMock()

        RedisBackend("redis://localhost:6379/0")

        mock_from_url.assert_called_once_with("redis://localhost:6379/0", decode_responses=True)


def test_redis_increment(mock_redis):
    """Test incrementing counter in Redis."""
    with patch("tinybase.rate_limit.redis.from_url", return_value=mock_redis):
        backend = RedisBackend("redis://localhost:6379/0")

        result = backend.increment("test:key", ttl=3600)

        mock_redis.pipeline.assert_called_once()
        pipe = mock_redis.pipeline.return_value
        pipe.incr.assert_called_once_with("test:key")
        pipe.expire.assert_called_once_with("test:key", 3600)
        pipe.execute.assert_called_once()
        assert result == 1


def test_redis_decrement(mock_redis):
    """Test decrementing counter in Redis."""
    mock_redis.decr.return_value = 2

    with patch("tinybase.rate_limit.redis.from_url", return_value=mock_redis):
        backend = RedisBackend("redis://localhost:6379/0")

        result = backend.decrement("test:key")

        mock_redis.decr.assert_called_once_with("test:key")
        assert result == 2


def test_redis_decrement_no_negative(mock_redis):
    """Test Redis decrement doesn't go below 0."""
    mock_redis.decr.return_value = -1

    with patch("tinybase.rate_limit.redis.from_url", return_value=mock_redis):
        backend = RedisBackend("redis://localhost:6379/0")

        result = backend.decrement("test:key")

        # Should set to 0 and return 0
        mock_redis.set.assert_called_once_with("test:key", 0)
        assert result == 0


def test_redis_get_existing(mock_redis):
    """Test getting existing key from Redis."""
    mock_redis.get.return_value = "5"

    with patch("tinybase.rate_limit.redis.from_url", return_value=mock_redis):
        backend = RedisBackend("redis://localhost:6379/0")

        result = backend.get("test:key")

        assert result == 5


def test_redis_get_nonexistent(mock_redis):
    """Test getting non-existent key from Redis returns 0."""
    mock_redis.get.return_value = None

    with patch("tinybase.rate_limit.redis.from_url", return_value=mock_redis):
        backend = RedisBackend("redis://localhost:6379/0")

        result = backend.get("nonexistent")

        assert result == 0


def test_redis_delete(mock_redis):
    """Test deleting key from Redis."""
    with patch("tinybase.rate_limit.redis.from_url", return_value=mock_redis):
        backend = RedisBackend("redis://localhost:6379/0")

        backend.delete("test:key")

        mock_redis.delete.assert_called_once_with("test:key")


# =============================================================================
# Backend Factory Tests
# =============================================================================


def test_get_rate_limit_backend_diskcache():
    """Test getting DiskCache backend."""
    mock_config = MagicMock()
    mock_config.rate_limit_backend = "diskcache"
    mock_config.rate_limit_cache_dir = tempfile.mkdtemp()

    with patch("tinybase.rate_limit.config", mock_config):
        backend = get_rate_limit_backend()

        assert isinstance(backend, DiskCacheBackend)


def test_get_rate_limit_backend_redis():
    """Test getting Redis backend."""
    mock_config = MagicMock()
    mock_config.rate_limit_backend = "redis"
    mock_config.rate_limit_redis_url = "redis://localhost:6379/0"

    with patch("tinybase.rate_limit.config", mock_config):
        with patch("tinybase.rate_limit.redis.from_url") as mock_from_url:
            mock_from_url.return_value = MagicMock()

            backend = get_rate_limit_backend()

            assert isinstance(backend, RedisBackend)


def test_get_rate_limit_backend_redis_no_url():
    """Test Redis backend raises error without URL."""
    mock_config = MagicMock()
    mock_config.rate_limit_backend = "redis"
    mock_config.rate_limit_redis_url = None

    with patch("tinybase.rate_limit.config", mock_config):
        with pytest.raises(ValueError, match="rate_limit_redis_url is required"):
            get_rate_limit_backend()


def test_get_rate_limit_backend_singleton():
    """Test backend factory returns singleton."""
    mock_config = MagicMock()
    mock_config.rate_limit_backend = "diskcache"
    mock_config.rate_limit_cache_dir = tempfile.mkdtemp()

    with patch("tinybase.rate_limit.config", mock_config):
        backend1 = get_rate_limit_backend()
        backend2 = get_rate_limit_backend()

        assert backend1 is backend2


def test_reset_rate_limit_backend():
    """Test resetting backend singleton."""
    mock_config = MagicMock()
    mock_config.rate_limit_backend = "diskcache"
    mock_config.rate_limit_cache_dir = tempfile.mkdtemp()

    with patch("tinybase.rate_limit.config", mock_config):
        backend1 = get_rate_limit_backend()

        reset_rate_limit_backend()
        mock_config.rate_limit_cache_dir = tempfile.mkdtemp()

        backend2 = get_rate_limit_backend()

        assert backend1 is not backend2


# =============================================================================
# check_rate_limit Dependency Tests
# =============================================================================


@pytest.mark.asyncio
async def test_check_rate_limit_no_user():
    """Test rate limit passes for anonymous user."""

    async def consume_generator():
        async for _ in check_rate_limit(None):
            pass

    # Should not raise
    await consume_generator()


@pytest.mark.asyncio
async def test_check_rate_limit_under_limit(mock_user, diskcache_backend):
    """Test rate limit passes when under limit."""
    mock_settings = MagicMock()
    mock_settings.limits.max_concurrent_functions_per_user = 10

    with patch("tinybase.rate_limit.settings", mock_settings):
        with patch("tinybase.rate_limit.get_rate_limit_backend", return_value=diskcache_backend):
            gen = check_rate_limit(mock_user)

            # Enter the generator
            await gen.__anext__()

            # Should have incremented counter
            key = f"concurrent_functions:user:{mock_user.id}"
            assert diskcache_backend.get(key) >= 1


@pytest.mark.asyncio
async def test_check_rate_limit_cleanup_on_exit(mock_user, diskcache_backend):
    """Test rate limit decrements counter on exit."""
    mock_settings = MagicMock()
    mock_settings.limits.max_concurrent_functions_per_user = 10

    with patch("tinybase.rate_limit.settings", mock_settings):
        with patch("tinybase.rate_limit.get_rate_limit_backend", return_value=diskcache_backend):
            gen = check_rate_limit(mock_user)

            # Enter
            await gen.__anext__()

            key = f"concurrent_functions:user:{mock_user.id}"
            count_during = diskcache_backend.get(key)
            assert count_during >= 1

            # Exit (simulate request completion)
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass

            # Counter should be decremented
            count_after = diskcache_backend.get(key)
            assert count_after == count_during - 1


@pytest.mark.asyncio
async def test_check_rate_limit_over_limit(mock_user, diskcache_backend):
    """Test rate limit rejects when over limit."""
    from fastapi import HTTPException

    mock_settings = MagicMock()
    mock_settings.limits.max_concurrent_functions_per_user = 2

    with patch("tinybase.rate_limit.settings", mock_settings):
        with patch("tinybase.rate_limit.get_rate_limit_backend", return_value=diskcache_backend):
            key = f"concurrent_functions:user:{mock_user.id}"

            # Pre-fill counter to be at limit
            diskcache_backend.increment(key)
            diskcache_backend.increment(key)

            gen = check_rate_limit(mock_user)

            with pytest.raises(HTTPException) as exc_info:
                await gen.__anext__()

            assert exc_info.value.status_code == 429
            assert "Rate limit exceeded" in exc_info.value.detail


@pytest.mark.asyncio
async def test_check_rate_limit_decrements_on_rejection(mock_user, diskcache_backend):
    """Test rate limit decrements counter when rejecting request."""
    from fastapi import HTTPException

    mock_settings = MagicMock()
    mock_settings.limits.max_concurrent_functions_per_user = 1

    with patch("tinybase.rate_limit.settings", mock_settings):
        with patch("tinybase.rate_limit.get_rate_limit_backend", return_value=diskcache_backend):
            key = f"concurrent_functions:user:{mock_user.id}"

            # Pre-fill counter
            diskcache_backend.increment(key)

            gen = check_rate_limit(mock_user)

            try:
                await gen.__anext__()
            except HTTPException:
                pass

            # Counter should have been decremented after rejection
            final_count = diskcache_backend.get(key)
            assert final_count == 1  # Back to original


# =============================================================================
# Edge Cases
# =============================================================================


def test_diskcache_concurrent_access(diskcache_backend):
    """Test DiskCache handles concurrent increment/decrement."""
    key = "test:concurrent"

    # Simulate concurrent operations
    for _ in range(10):
        diskcache_backend.increment(key)

    assert diskcache_backend.get(key) == 10

    for _ in range(10):
        diskcache_backend.decrement(key)

    assert diskcache_backend.get(key) == 0


def test_diskcache_multiple_keys(diskcache_backend):
    """Test DiskCache tracks multiple keys independently."""
    key1 = "user:1:counter"
    key2 = "user:2:counter"

    diskcache_backend.increment(key1)
    diskcache_backend.increment(key1)
    diskcache_backend.increment(key2)

    assert diskcache_backend.get(key1) == 2
    assert diskcache_backend.get(key2) == 1

    diskcache_backend.delete(key1)

    assert diskcache_backend.get(key1) == 0
    assert diskcache_backend.get(key2) == 1


@pytest.mark.asyncio
async def test_check_rate_limit_cleanup_on_exception(mock_user, diskcache_backend):
    """Test rate limit decrements counter even on exceptions."""
    mock_settings = MagicMock()
    mock_settings.limits.max_concurrent_functions_per_user = 10

    with patch("tinybase.rate_limit.settings", mock_settings):
        with patch("tinybase.rate_limit.get_rate_limit_backend", return_value=diskcache_backend):
            gen = check_rate_limit(mock_user)

            # Enter
            await gen.__anext__()

            key = f"concurrent_functions:user:{mock_user.id}"
            count_during = diskcache_backend.get(key)

            # Simulate exception by throwing into generator
            try:
                await gen.athrow(Exception("Test error"))
            except Exception:
                pass

            # Counter should still be decremented
            count_after = diskcache_backend.get(key)
            assert count_after == count_during - 1
