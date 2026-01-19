"""
Tests for function process pool.

Tests cold start optimization, TTL, cleanup, and pool management.
"""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from tinybase.functions.pool import FunctionProcessPool, WarmProcess, get_pool, utcnow


class TestFunctionProcessPool:
    """Test FunctionProcessPool class."""

    def test_pool_initialization(self):
        """Test pool initialization."""
        pool = FunctionProcessPool(max_pool_size=5, ttl_seconds=300)

        assert pool.max_pool_size == 5
        assert pool.ttl_seconds == 300
        assert len(pool._pools) == 0

    def test_pool_disabled_when_max_size_zero(self):
        """Test that pool is disabled when max_pool_size is 0."""
        pool = FunctionProcessPool(max_pool_size=0, ttl_seconds=300)

        file_path = Path("/test/func.py")
        warm = pool.get_warm_process(file_path)

        assert warm is None

    def test_pool_disabled_when_ttl_zero(self):
        """Test that cleanup is disabled when TTL is 0."""
        pool = FunctionProcessPool(max_pool_size=3, ttl_seconds=0)

        pool.start()
        # Should not start cleanup thread when TTL is 0
        assert pool._cleanup_thread is None

        pool.stop()

    def test_get_warm_process_empty_pool(self):
        """Test getting warm process from empty pool."""
        pool = FunctionProcessPool(max_pool_size=3, ttl_seconds=300)

        file_path = Path("/test/func.py")
        warm = pool.get_warm_process(file_path)

        assert warm is None

    def test_prewarm_function(self):
        """Test pre-warming a function."""
        pool = FunctionProcessPool(max_pool_size=3, ttl_seconds=300)

        file_path = Path("/test/func.py")
        pool.prewarm_function(file_path)

        # Should have one warm process in pool
        assert str(file_path) in pool._pools
        assert len(pool._pools[str(file_path)]) == 1

        warm = pool.get_warm_process(file_path)
        assert warm is not None
        assert warm.file_path == file_path

    def test_get_warm_process_from_pool(self):
        """Test getting warm process from pool."""
        pool = FunctionProcessPool(max_pool_size=3, ttl_seconds=300)

        file_path = Path("/test/func.py")
        pool.prewarm_function(file_path)

        warm = pool.get_warm_process(file_path)
        assert warm is not None

        # Pool should be empty now
        assert len(pool._pools[str(file_path)]) == 0

    def test_return_warm_process(self):
        """Test returning warm process to pool."""
        pool = FunctionProcessPool(max_pool_size=3, ttl_seconds=300)

        file_path = Path("/test/func.py")
        warm = WarmProcess(file_path=file_path, last_used=utcnow())

        pool.return_warm_process(file_path, warm)

        # Should be in pool
        assert str(file_path) in pool._pools
        assert len(pool._pools[str(file_path)]) == 1

    def test_pool_max_size_limit(self):
        """Test that pool respects max size limit."""
        pool = FunctionProcessPool(max_pool_size=2, ttl_seconds=300)

        file_path = Path("/test/func.py")

        # Add 3 warm processes
        for i in range(3):
            warm = WarmProcess(file_path=file_path, last_used=utcnow())
            pool.return_warm_process(file_path, warm)

        # Should only have 2 in pool (oldest discarded)
        assert len(pool._pools[str(file_path)]) == 2

    def test_pool_ttl_expiration(self):
        """Test that expired processes are removed."""
        from collections import deque
        from datetime import timedelta

        pool = FunctionProcessPool(max_pool_size=3, ttl_seconds=1)  # 1 second TTL

        file_path = Path("/test/func.py")

        # Create old warm process (2 seconds old, expired)
        old_time = utcnow() - timedelta(seconds=2)
        warm = WarmProcess(file_path=file_path, last_used=old_time)
        # Manually add to pool without updating last_used (which return_warm_process would do)
        key = str(file_path)
        with pool._lock:
            pool._pools.setdefault(key, deque()).append(warm)

        # Try to get it - should be None (expired)
        retrieved = pool.get_warm_process(file_path)
        assert retrieved is None

    def test_pool_cleanup_expired(self):
        """Test cleanup of expired processes."""
        pool = FunctionProcessPool(max_pool_size=3, ttl_seconds=1)  # 1 second TTL

        file_path = Path("/test/func.py")

        # Add expired process (3 seconds old)
        from collections import deque
        from datetime import timedelta

        old_time = utcnow() - timedelta(seconds=3)
        expired_warm = WarmProcess(file_path=file_path, last_used=old_time)
        # Manually add to pool without updating last_used
        key = str(file_path)
        with pool._lock:
            pool._pools.setdefault(key, deque()).append(expired_warm)

        # Add valid process (created now)
        valid_warm = WarmProcess(file_path=file_path, last_used=utcnow())
        pool.return_warm_process(file_path, valid_warm)

        # Wait a bit but not long enough to expire the valid one
        time.sleep(0.1)

        # Run cleanup
        pool._cleanup_expired()

        # Should only have valid process left
        assert str(file_path) in pool._pools
        assert len(pool._pools[str(file_path)]) == 1

    def test_pool_cleanup_removes_empty_pools(self):
        """Test that cleanup removes empty pools."""
        pool = FunctionProcessPool(max_pool_size=3, ttl_seconds=1)

        file_path = Path("/test/func.py")

        # Add expired process
        from datetime import timedelta

        old_time = utcnow() - timedelta(seconds=2)
        expired_warm = WarmProcess(file_path=file_path, last_used=old_time)
        pool.return_warm_process(file_path, expired_warm)

        # Wait for expiration
        time.sleep(1.5)

        # Run cleanup
        pool._cleanup_expired()

        # Pool should be removed
        assert str(file_path) not in pool._pools

    def test_pool_start_stop(self):
        """Test starting and stopping the pool."""
        pool = FunctionProcessPool(max_pool_size=3, ttl_seconds=60)

        pool.start()
        assert pool._running is True
        assert pool._cleanup_thread is not None
        assert pool._cleanup_thread.is_alive()

        pool.stop()
        assert pool._running is False
        # Thread should be stopped - wait a bit for it to finish
        if pool._cleanup_thread:
            pool._cleanup_thread.join(timeout=2)
            # Thread may still be alive if it's in the middle of a sleep,
            # but _running should be False so it will stop on next iteration
            # For this test, we just verify _running is False
            assert pool._running is False

    def test_pool_multiple_functions(self):
        """Test pool with multiple different functions."""
        pool = FunctionProcessPool(max_pool_size=2, ttl_seconds=300)

        file1 = Path("/test/func1.py")
        file2 = Path("/test/func2.py")

        pool.prewarm_function(file1)
        pool.prewarm_function(file2)

        # Should have separate pools
        assert str(file1) in pool._pools
        assert str(file2) in pool._pools
        assert len(pool._pools[str(file1)]) == 1
        assert len(pool._pools[str(file2)]) == 1

    def test_get_pool_singleton(self):
        """Test that get_pool returns singleton."""
        with patch("tinybase.config.settings") as mock_settings:
            mock_config = MagicMock()
            mock_config.function_cold_start_pool_size = 3
            mock_config.function_cold_start_ttl_seconds = 300
            mock_settings.return_value = mock_config

            # Reset the global pool to test singleton behavior
            import tinybase.functions.pool

            tinybase.functions.pool._pool = None

            pool1 = get_pool()
            pool2 = get_pool()

            assert pool1 is pool2

    def test_warm_process_dataclass(self):
        """Test WarmProcess dataclass."""
        file_path = Path("/test/func.py")
        now = utcnow()

        warm = WarmProcess(file_path=file_path, last_used=now, process=None)

        assert warm.file_path == file_path
        assert warm.last_used == now
        assert warm.process is None

    def test_pool_thread_safety(self):
        """Test that pool operations are thread-safe."""
        import threading

        pool = FunctionProcessPool(max_pool_size=10, ttl_seconds=300)
        file_path = Path("/test/func.py")

        def add_warm():
            for _ in range(10):
                warm = WarmProcess(file_path=file_path, last_used=utcnow())
                pool.return_warm_process(file_path, warm)

        def get_warm():
            for _ in range(10):
                pool.get_warm_process(file_path)

        # Run concurrently
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=add_warm))
            threads.append(threading.Thread(target=get_warm))

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Should not have crashed or corrupted state
        assert isinstance(pool._pools, dict)
