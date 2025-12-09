"""
Background scheduler for TinyBase.

Runs as a background task and executes scheduled functions
when their next_run_at time is reached.
"""

import asyncio
import logging
from datetime import datetime

from sqlmodel import Session, select

from tinybase.auth import cleanup_expired_tokens
from tinybase.config import settings
from tinybase.db.core import get_engine
from tinybase.db.models import FunctionSchedule, InstanceSettings
from tinybase.functions.core import execute_function, get_global_registry
from tinybase.utils import utcnow, TriggerType

from .utils import parse_schedule_config

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Background scheduler for TinyBase functions.
    
    The scheduler runs as an asyncio task and periodically checks
    for due schedules. When a schedule's next_run_at time is reached,
    the associated function is executed and the schedule is updated.
    
    Also handles periodic cleanup tasks like removing expired tokens.
    """
    
    def __init__(self) -> None:
        """Initialize the scheduler."""
        self._running = False
        self._task: asyncio.Task | None = None
        self._tick_count = 0
    
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
        
        logger.info("Scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """
        Main scheduler loop.
        
        Runs every `scheduler_interval_seconds` and processes any due schedules.
        Also performs periodic maintenance tasks like token cleanup.
        """
        interval = settings().scheduler_interval_seconds
        
        while self._running:
            try:
                await self._process_due_schedules()
                
                # Periodic token cleanup
                self._tick_count += 1
                # Get token cleanup interval from instance settings
                cleanup_interval = self._get_token_cleanup_interval()
                if self._tick_count >= cleanup_interval:
                    self._tick_count = 0
                    await self._run_maintenance()
                    
            except Exception as e:
                logger.exception(f"Error in scheduler loop: {e}")
            
            await asyncio.sleep(interval)
    
    def _get_token_cleanup_interval(self) -> int:
        """Get token cleanup interval from instance settings, with fallback to config."""
        try:
            engine = get_engine()
            with Session(engine) as session:
                instance_settings = session.get(InstanceSettings, 1)
                if instance_settings and instance_settings.token_cleanup_interval:
                    return instance_settings.token_cleanup_interval
        except Exception as e:
            logger.warning(f"Failed to get token cleanup interval from settings: {e}")
        # Fallback to config setting, then hardcoded default
        return getattr(settings(), "scheduler_token_cleanup_interval", 60)
    
    async def _run_maintenance(self) -> None:
        """Run periodic maintenance tasks."""
        engine = get_engine()
        with Session(engine) as session:
            try:
                cleanup_expired_tokens(session)
            except Exception as e:
                logger.exception(f"Error during token cleanup: {e}")
    
    async def _process_due_schedules(self) -> None:
        """Find and execute all due schedules."""
        now = utcnow()
        engine = get_engine()
        
        with Session(engine) as session:
            # Find all active schedules that are due
            statement = select(FunctionSchedule).where(
                FunctionSchedule.is_active == True,  # noqa: E712
                FunctionSchedule.next_run_at <= now,
            )
            due_schedules = list(session.exec(statement).all())
            
            for schedule in due_schedules:
                await self._execute_schedule(session, schedule, now)
    
    async def _execute_schedule(
        self,
        session: Session,
        schedule: FunctionSchedule,
        now: datetime
    ) -> None:
        """
        Execute a scheduled function and update the schedule.
        
        Args:
            session: Database session
            schedule: The schedule to execute
            now: Current time
        """
        logger.info(f"Executing scheduled function: {schedule.function_name}")
        
        # Get the function from registry
        registry = get_global_registry()
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
        
        # Execute the function
        # Note: We run this synchronously in the async context
        # For CPU-intensive functions, consider using run_in_executor
        try:
            execute_function(
                meta=meta,
                payload=schedule.input_data or {},
                session=session,
                trigger_type=TriggerType.SCHEDULE,
                trigger_id=schedule.id,
            )
        except Exception as e:
            logger.exception(f"Error executing scheduled function {schedule.function_name}: {e}")
        
        # Update schedule timing
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
        
        session.add(schedule)
        session.commit()


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
    if settings().scheduler_enabled:
        scheduler = get_scheduler()
        await scheduler.start()


async def stop_scheduler() -> None:
    """Stop the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.stop()

