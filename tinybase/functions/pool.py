"""
Cold start optimization: Process pool for keeping functions warm.

Maintains a pool of pre-warmed subprocess environments to reduce cold start latency.
"""

import logging
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from tinybase.utils import utcnow

logger = logging.getLogger(__name__)


@dataclass
class WarmProcess:
    """Represents a warm function process ready for execution."""

    file_path: Path
    last_used: datetime
    process: subprocess.Popen | None = None  # None means environment is ready but no process


class FunctionProcessPool:
    """
    Pool of warm function processes to reduce cold start latency.

    Maintains a pool of pre-warmed environments per function file.
    When a function is called, reuses a warm environment if available,
    otherwise creates a new one and adds it to the pool.
    """

    def __init__(self, max_pool_size: int = 3, ttl_seconds: int = 300):
        """
        Initialize the process pool.

        Args:
            max_pool_size: Maximum number of warm processes per function
            ttl_seconds: Time to keep processes warm after last use (0 = disabled)
        """
        self.max_pool_size = max_pool_size
        self.ttl_seconds = ttl_seconds
        self._pools: dict[str, deque[WarmProcess]] = {}
        self._lock = threading.Lock()
        self._cleanup_thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        """Start the cleanup thread."""
        if self.max_pool_size == 0 or self.ttl_seconds == 0:
            return  # Pool disabled

        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("Function process pool started")

    def stop(self) -> None:
        """Stop the cleanup thread and clear all pools."""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)

        with self._lock:
            self._pools.clear()
        logger.info("Function process pool stopped")

    def get_warm_process(self, file_path: Path) -> WarmProcess | None:
        """
        Get a warm process from the pool, if available.

        Args:
            file_path: Path to the function file

        Returns:
            WarmProcess if available, None otherwise
        """
        if self.max_pool_size == 0:
            return None

        key = str(file_path)
        with self._lock:
            pool = self._pools.get(key)
            if pool:
                warm = pool.popleft()
                # Check if still valid
                if self.ttl_seconds > 0:
                    age = (utcnow() - warm.last_used).total_seconds()
                    if age > self.ttl_seconds:
                        # Too old, discard
                        return None
                return warm
        return None

    def return_warm_process(self, file_path: Path, warm: WarmProcess) -> None:
        """
        Return a warm process to the pool for reuse.

        Args:
            file_path: Path to the function file
            warm: The warm process to return
        """
        if self.max_pool_size == 0:
            return

        key = str(file_path)
        warm.last_used = utcnow()

        with self._lock:
            pool = self._pools.setdefault(key, deque())
            if len(pool) < self.max_pool_size:
                pool.append(warm)
            # If pool is full, discard the oldest
            elif pool:
                pool.popleft()
                pool.append(warm)

    def prewarm_function(self, file_path: Path) -> None:
        """
        Pre-warm a function by creating a warm environment entry.

        This doesn't actually start a process, but marks the environment
        as "ready" so the first call can skip dependency installation.

        Args:
            file_path: Path to the function file
        """
        if self.max_pool_size == 0:
            return

        key = str(file_path)
        warm = WarmProcess(file_path=file_path, last_used=utcnow())

        with self._lock:
            pool = self._pools.setdefault(key, deque())
            if len(pool) < self.max_pool_size:
                pool.append(warm)
            # If pool is full, replace oldest
            elif pool:
                pool.popleft()
                pool.append(warm)

    def _cleanup_loop(self) -> None:
        """Background thread to clean up expired warm processes."""
        while self._running:
            try:
                time.sleep(60)  # Check every minute
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"Error in process pool cleanup: {e}")

    def _cleanup_expired(self) -> None:
        """Remove expired warm processes from pools."""
        if self.ttl_seconds == 0:
            return

        now = utcnow()
        with self._lock:
            for key, pool in list(self._pools.items()):
                # Remove expired entries
                valid = deque()
                for warm in pool:
                    age = (now - warm.last_used).total_seconds()
                    if age <= self.ttl_seconds:
                        valid.append(warm)

                if valid:
                    self._pools[key] = valid
                else:
                    # Pool is empty, remove it
                    del self._pools[key]


# Global pool instance
_pool: FunctionProcessPool | None = None


def get_pool() -> FunctionProcessPool:
    """Get the global function process pool."""
    global _pool
    if _pool is None:
        from tinybase.config import settings

        config = settings()
        _pool = FunctionProcessPool(
            max_pool_size=config.function_cold_start_pool_size,
            ttl_seconds=config.function_cold_start_ttl_seconds,
        )
    return _pool
