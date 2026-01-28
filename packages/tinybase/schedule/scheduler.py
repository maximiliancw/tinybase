"""
Background scheduler for TinyBase.

Runs as a background task and executes scheduled functions
when their next_run_at time is reached.
"""

import asyncio
import concurrent.futures
import logging
from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from tinybase.auth import cleanup_expired_tokens
from tinybase.db.core import get_db_engine
from tinybase.db.models import FunctionSchedule
from tinybase.functions.core import execute_function, get_function_registry
from tinybase.metrics import collect_metrics
from tinybase.settings import config, settings
from tinybase.utils import TriggerType, utcnow

from .utils import parse_schedule_config

logger = logging.getLogger(__name__)

# Default values (used as fallback if not configured)
DEFAULT_FUNCTION_TIMEOUT_SECONDS = 1800
DEFAULT_MAX_SCHEDULES_PER_TICK = 100
DEFAULT_MAX_CONCURRENT_EXECUTIONS = 10


class Scheduler:
    """
    Background scheduler for TinyBase functions.

    The scheduler runs as an asyncio task and periodically checks
    for due schedules. When a schedule's next_run_at time is reached,
    the associated function is executed and the schedule is updated.

    Also handles periodic cleanup tasks like removing expired tokens.

    Features:
    - Concurrent execution of schedules (with limits)
    - Timeout protection for long-running functions
    - Cached configuration to reduce database queries
    - Error isolation between schedules
    - Performance metrics and logging
    """

    def __init__(self) -> None:
        """Initialize the scheduler."""
        self._running = False
        self._task: asyncio.Task | None = None
        self._tick_count = 0
        # Cache for settings (refreshed periodically)
        self._cached_cleanup_interval: int | None = None
        self._cached_metrics_interval: int | None = None
        self._cached_function_timeout: int | None = None
        self._cached_max_schedules_per_tick: int | None = None
        self._cached_max_concurrent_executions: int | None = None
        self._cached_admin_report_enabled: bool | None = None
        self._cached_admin_report_interval_days: int | None = None
        self._last_admin_report_sent: datetime | None = None
        self._settings_cache_ticks = 0
        self._settings_cache_ttl = 60  # Refresh every 60 ticks
        # Semaphore to limit concurrent executions (will be updated when settings change)
        # Initialize with default, will be updated on first settings load
        self._execution_semaphore = asyncio.Semaphore(DEFAULT_MAX_CONCURRENT_EXECUTIONS)
        # Thread pool for CPU-intensive operations (will be recreated if max_concurrent changes)
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=DEFAULT_MAX_CONCURRENT_EXECUTIONS, thread_name_prefix="scheduler-exec"
        )
        # Performance metrics
        self._metrics = {
            "total_ticks": 0,
            "total_schedules_executed": 0,
            "total_errors": 0,
            "total_timeouts": 0,
        }

    async def start(self) -> None:
        """Start the scheduler background task."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler background task."""
        self._running = False

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        # Shutdown thread pool
        # Note: timeout parameter removed in Python 3.14
        try:
            self._executor.shutdown(wait=True, timeout=30)
        except TypeError:
            # Python 3.14+ doesn't support timeout parameter
            self._executor.shutdown(wait=True)

        logger.info("Scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """
        Main scheduler loop.

        Runs every `scheduler_interval_seconds` and processes any due schedules.
        Also performs periodic maintenance tasks like token cleanup.
        """
        interval = config.scheduler_interval_seconds

        while self._running:
            loop_start = utcnow()
            try:
                await self._process_due_schedules()

                # Periodic token cleanup
                # Use modulo to prevent overflow (reset every 1M ticks)
                self._tick_count = (self._tick_count + 1) % 1_000_000
                self._metrics["total_ticks"] += 1

                # Get intervals from instance settings (cached)
                cleanup_interval = self._get_token_cleanup_interval()
                metrics_interval = self._get_metrics_collection_interval()

                # Run maintenance tasks at their respective intervals
                if self._tick_count % cleanup_interval == 0:
                    await self._run_token_cleanup()
                if self._tick_count % metrics_interval == 0:
                    await self._run_metrics_collection()

                # Check and send admin report emails if needed
                await self._check_and_send_admin_report()

            except Exception as e:
                logger.exception(f"Error in scheduler loop: {e}")
                self._metrics["total_errors"] += 1

            # Calculate sleep time to maintain consistent interval
            # Account for processing time to keep ticks on schedule
            elapsed = (utcnow() - loop_start).total_seconds()
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            elif elapsed > interval * 2:
                # Warn if we're falling behind significantly
                logger.warning(
                    f"Scheduler tick took {elapsed:.2f}s (interval: {interval}s). "
                    "Consider increasing scheduler_interval_seconds or reducing load."
                )

    def _refresh_settings_cache(self) -> None:
        """
        Refresh cached scheduler settings from instance settings or config.

        Caches all scheduler-related settings and refreshes them periodically
        to reduce database queries. Also updates semaphore and executor if needed.
        """
        # Refresh cache periodically
        if (
            self._cached_cleanup_interval is None
            or self._settings_cache_ticks >= self._settings_cache_ttl
        ):
            try:
                # Token cleanup interval
                self._cached_cleanup_interval = settings.jobs.token_cleanup.interval

                # Metrics collection interval
                self._cached_metrics_interval = settings.jobs.metrics.interval

                # Function timeout
                self._cached_function_timeout = settings.scheduler.function_timeout_seconds

                # Max schedules per tick
                self._cached_max_schedules_per_tick = settings.scheduler.max_schedules_per_tick

                # Max concurrent executions
                new_max_concurrent = settings.scheduler.max_concurrent_executions

                # Update semaphore and executor if max_concurrent changed
                if self._cached_max_concurrent_executions != new_max_concurrent:
                    logger.info(
                        f"Updating max concurrent executions from "
                        f"{self._cached_max_concurrent_executions} to {new_max_concurrent}"
                    )
                    # Shutdown old executor
                    self._executor.shutdown(wait=False)
                    # Create new semaphore and executor
                    self._execution_semaphore = asyncio.Semaphore(new_max_concurrent)
                    self._executor = concurrent.futures.ThreadPoolExecutor(
                        max_workers=new_max_concurrent, thread_name_prefix="scheduler-exec"
                    )

                self._cached_max_concurrent_executions = new_max_concurrent

                # Admin report email settings
                self._cached_admin_report_enabled = settings.jobs.admin_report.enabled
                self._cached_admin_report_interval_days = settings.jobs.admin_report.interval_days

                self._settings_cache_ticks = 0

            except Exception as e:
                logger.warning(f"Failed to refresh scheduler settings: {e}")
                # Use fallback if query fails
                if self._cached_cleanup_interval is None:
                    self._cached_cleanup_interval = 60
                    self._cached_metrics_interval = 360
                    self._cached_function_timeout = DEFAULT_FUNCTION_TIMEOUT_SECONDS
                    self._cached_max_schedules_per_tick = DEFAULT_MAX_SCHEDULES_PER_TICK
                    self._cached_max_concurrent_executions = DEFAULT_MAX_CONCURRENT_EXECUTIONS
                self._settings_cache_ticks = 0
        else:
            self._settings_cache_ticks += 1

    def _get_token_cleanup_interval(self) -> int:
        """Get token cleanup interval from cache."""
        self._refresh_settings_cache()
        return self._cached_cleanup_interval or 60

    def _get_metrics_collection_interval(self) -> int:
        """Get metrics collection interval from cache."""
        self._refresh_settings_cache()
        return self._cached_metrics_interval or 360

    def _get_function_timeout(self) -> int:
        """Get function timeout from cache."""
        self._refresh_settings_cache()
        return self._cached_function_timeout or DEFAULT_FUNCTION_TIMEOUT_SECONDS

    def _get_max_schedules_per_tick(self) -> int:
        """Get max schedules per tick from cache."""
        self._refresh_settings_cache()
        return self._cached_max_schedules_per_tick or DEFAULT_MAX_SCHEDULES_PER_TICK

    def _get_max_concurrent_executions(self) -> int:
        """Get max concurrent executions from cache."""
        self._refresh_settings_cache()
        return self._cached_max_concurrent_executions or DEFAULT_MAX_CONCURRENT_EXECUTIONS

    async def _run_token_cleanup(self) -> None:
        """Run token cleanup maintenance task."""
        engine = get_db_engine()
        with Session(engine) as session:
            try:
                cleanup_expired_tokens(session)
            except Exception as e:
                logger.exception(f"Error during token cleanup: {e}")

    async def _run_metrics_collection(self) -> None:
        """Run metrics collection task."""
        engine = get_db_engine()
        with Session(engine) as session:
            try:
                collect_metrics(session)
            except Exception as e:
                logger.exception(f"Error during metrics collection: {e}")

    async def _check_and_send_admin_report(self) -> None:
        """Check if it's time to send admin report emails and send them if needed."""
        # Check if admin reports are enabled
        if not self._cached_admin_report_enabled:
            return

        try:
            # Check if email is enabled and configured
            if not config.email_enabled or not config.email_from_address:
                return

            now = utcnow()
            interval_days = self._cached_admin_report_interval_days or 7

            # Check if it's time to send based on internal tracking
            if self._last_admin_report_sent is not None:
                time_since_last = (now - self._last_admin_report_sent).total_seconds()
                interval_seconds = interval_days * 24 * 60 * 60
                if time_since_last < interval_seconds:
                    return

            # Send report
            engine = get_db_engine()
            with Session(engine) as session:
                await self._send_admin_report_emails(session, now)
                self._last_admin_report_sent = now

        except Exception as e:
            logger.exception(f"Error checking admin report email schedule: {e}")

    async def _send_admin_report_emails(self, session: Session, report_date: datetime) -> None:
        """Send admin report emails to all admin users."""
        from sqlalchemy import func
        from sqlmodel import select

        from tinybase.db.models import User
        from tinybase.email import send_admin_report_email
        from tinybase.metrics import get_latest_metrics

        try:
            # Get all admin users
            admin_users = session.exec(select(User).where(User.is_admin == True)).all()  # noqa: E712

            if not admin_users:
                logger.debug("No admin users found, skipping admin report email")
                return

            # Get latest metrics
            metrics = get_latest_metrics(session)

            # Prepare report data
            summary = {}
            collections = {}
            functions = {}
            users = {"total": 0, "admins": 0, "regular": 0}

            # Get collection sizes from metrics
            if metrics and "collection_sizes" in metrics:
                collection_metric = metrics["collection_sizes"]
                if collection_metric and collection_metric.data:
                    collections = collection_metric.data

            # Get function stats from metrics
            if metrics and "function_stats" in metrics:
                function_metric = metrics["function_stats"]
                if function_metric and function_metric.data:
                    for func_name, stats in function_metric.data.items():
                        error_rate = stats.get("error_rate", 0.0)
                        functions[func_name] = {
                            "total_calls": stats.get("total_calls", 0),
                            "success_rate": 1.0
                            - (error_rate / 100.0),  # Convert percentage to decimal
                            "avg_duration_ms": stats.get("avg_runtime_ms"),
                        }

            # Get user statistics
            total_users = session.exec(select(func.count(User.id))).one()
            admin_count = session.exec(
                select(func.count(User.id)).where(User.is_admin == True)  # noqa: E712
            ).one()
            users = {
                "total": total_users,
                "admins": admin_count,
                "regular": total_users - admin_count,
            }

            # Calculate summary
            total_collections = len(collections)
            total_records = sum(collections.values()) if collections else 0
            total_functions = len(functions)
            total_function_calls = sum(f.get("total_calls", 0) for f in functions.values())

            summary = {
                "Total Collections": total_collections,
                "Total Records": total_records,
                "Total Functions": total_functions,
                "Total Function Calls": total_function_calls,
                "Total Users": users["total"],
            }

            # Format report date
            report_date_str = report_date.strftime("%Y-%m-%d %H:%M:%S UTC")

            # Send email to each admin
            for admin in admin_users:
                try:
                    send_admin_report_email(
                        to_email=admin.email,
                        report_date=report_date_str,
                        summary=summary,
                        collections=collections,
                        functions=functions,
                        users=users,
                    )
                    logger.info(f"Sent admin report email to {admin.email}")
                except Exception as e:
                    logger.error(f"Failed to send admin report email to {admin.email}: {e}")

        except Exception as e:
            logger.exception(f"Error sending admin report emails: {e}")

    async def _process_due_schedules(self) -> None:
        """
        Find and execute all due schedules.

        Processes schedules concurrently (with limits) and batches execution
        to prevent overload. Each schedule is executed in isolation with its
        own error handling.
        """
        now = utcnow()
        engine = get_db_engine()

        try:
            with Session(engine) as session:
                # Find all active schedules that are due
                # Limit to prevent processing too many at once
                max_per_tick = self._get_max_schedules_per_tick()
                statement = (
                    select(FunctionSchedule)
                    .where(
                        FunctionSchedule.is_active == True,  # noqa: E712
                        FunctionSchedule.next_run_at <= now,
                    )
                    .limit(max_per_tick)
                )
                due_schedules = list(session.exec(statement).all())

                if not due_schedules:
                    return

                logger.debug(f"Processing {len(due_schedules)} due schedule(s)")

                # Execute schedules concurrently (with semaphore limit)
                # Each schedule gets its own database session for isolation
                tasks = [
                    self._execute_schedule_isolated(schedule.id, now) for schedule in due_schedules
                ]

                # Wait for all executions to complete (or timeout)
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Log any exceptions that occurred
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(
                            f"Schedule {due_schedules[i].id} execution failed: {result}",
                            exc_info=result,
                        )
                        self._metrics["total_errors"] += 1
                    else:
                        self._metrics["total_schedules_executed"] += 1

        except Exception as e:
            logger.exception(f"Error querying due schedules: {e}")
            self._metrics["total_errors"] += 1

    async def _execute_schedule_isolated(self, schedule_id: UUID, now: datetime) -> None:
        """
        Execute a schedule in isolation with its own database session.

        This ensures that errors in one schedule don't affect others,
        and each schedule gets a fresh database connection.

        Args:
            schedule_id: The schedule ID to execute
            now: Current time
        """
        # Acquire semaphore to limit concurrent executions
        async with self._execution_semaphore:
            engine = get_db_engine()
            with Session(engine) as session:
                # Reload schedule to ensure we have latest data
                schedule = session.get(FunctionSchedule, schedule_id)
                if schedule is None:
                    logger.warning(f"Schedule {schedule_id} not found")
                    return

                if not schedule.is_active:
                    logger.debug(f"Schedule {schedule_id} is not active, skipping")
                    return

                await self._execute_schedule(session, schedule, now)

    async def _execute_schedule(
        self, session: Session, schedule: FunctionSchedule, now: datetime
    ) -> None:
        """
        Execute a scheduled function and update the schedule.

        Args:
            session: Database session
            schedule: The schedule to execute
            now: Current time
        """
        logger.info(
            f"Executing scheduled function: {schedule.function_name} (schedule {schedule.id})"
        )

        # Get the function from registry
        registry = get_function_registry()
        meta = registry.get(schedule.function_name)

        if meta is None:
            logger.warning(
                f"Scheduled function not found: {schedule.function_name}, "
                f"deactivating schedule {schedule.id}"
            )
            schedule.is_active = False
            session.add(schedule)
            session.commit()
            return

        # Execute the function with timeout protection
        # Note: execute_function is synchronous and uses the session directly
        # We run it in a thread pool to avoid blocking the event loop, but we
        # must create a new session in the executor thread since SQLAlchemy
        # sessions are not thread-safe.
        timeout_seconds = self._get_function_timeout()

        def _execute_in_thread() -> None:
            """Execute function in thread with its own database session."""
            engine = get_db_engine()
            with Session(engine) as exec_session:
                execute_function(
                    meta=meta,
                    payload=schedule.input_data or {},
                    session=exec_session,
                    user_id=None,
                    is_admin=False,
                    trigger_type=TriggerType.SCHEDULE,
                    trigger_id=schedule.id,
                    request=None,
                )

        try:
            # Run function execution in thread pool with timeout
            loop = asyncio.get_event_loop()
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(self._executor, _execute_in_thread),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"Function {schedule.function_name} (schedule {schedule.id}) "
                    f"exceeded timeout of {timeout_seconds}s"
                )
                self._metrics["total_timeouts"] += 1
                # Schedule will still be updated below, but function execution failed

        except Exception as e:
            logger.exception(
                f"Error executing scheduled function {schedule.function_name} "
                f"(schedule {schedule.id}): {e}"
            )
            self._metrics["total_errors"] += 1

        # Update schedule timing (always update, even on error)
        schedule.last_run_at = now

        # Calculate next run time
        try:
            config = parse_schedule_config(schedule.schedule)
            next_run = config.next_run_after(now)

            if next_run is None:
                # Schedule is exhausted (e.g., "once" schedule that has run)
                schedule.is_active = False
                schedule.next_run_at = None
                logger.info(f"Schedule {schedule.id} completed (no more runs)")
            else:
                schedule.next_run_at = next_run
                logger.debug(f"Schedule {schedule.id} next run: {next_run}")

        except Exception as e:
            logger.error(f"Error calculating next run for schedule {schedule.id}: {e}")
            schedule.is_active = False
            schedule.next_run_at = None

        try:
            session.add(schedule)
            session.commit()
        except Exception as e:
            logger.exception(f"Error committing schedule {schedule.id} update: {e}")
            session.rollback()
            self._metrics["total_errors"] += 1

    def get_metrics(self) -> dict:
        """
        Get scheduler performance metrics.

        Returns:
            Dictionary with metrics including:
            - total_ticks: Total scheduler ticks
            - total_schedules_executed: Total schedules executed
            - total_errors: Total errors encountered
            - total_timeouts: Total function timeouts
        """
        return self._metrics.copy()


# Global scheduler instance
_scheduler: Scheduler | None = None


def get_scheduler() -> Scheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler


async def start_scheduler() -> None:
    """Start the global scheduler."""
    if config.scheduler_enabled:
        scheduler = get_scheduler()
        await scheduler.start()


async def stop_scheduler() -> None:
    """Stop the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.stop()
