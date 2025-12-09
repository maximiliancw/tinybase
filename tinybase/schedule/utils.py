"""
Scheduling utilities for TinyBase.

Provides:
- Pydantic models for schedule configuration (once, interval, cron)
- Next run time calculation
- Helper functions for schedule validation
"""

import datetime as dt
import zoneinfo
from typing import Annotated, Union

from croniter import croniter
from pydantic import BaseModel, ConfigDict, Field

from tinybase.utils import IntervalUnit, ScheduleMethod

# =============================================================================
# Schedule Configuration Models
# =============================================================================


def get_server_timezone() -> str:
    """
    Get the server's configured timezone from InstanceSettings.

    Falls back to UTC if not configured or on error.
    """
    try:
        from sqlmodel import Session

        from tinybase.db.core import get_engine
        from tinybase.db.models import InstanceSettings

        engine = get_engine()
        with Session(engine) as session:
            settings = session.get(InstanceSettings, 1)
            if settings and settings.server_timezone:
                return settings.server_timezone
    except Exception:
        pass
    return "UTC"


class BaseScheduleConfig(BaseModel):
    """
    Base class for schedule configuration.

    All schedule types share timezone support and a method for
    calculating the next run time.

    If timezone is not specified, it defaults to the server's configured timezone.
    """

    model_config = ConfigDict(extra="forbid")

    method: ScheduleMethod
    timezone: str | None = Field(
        default=None, description="Timezone for schedule calculations (defaults to server timezone)"
    )

    def tzinfo(self) -> zoneinfo.ZoneInfo:
        """Get the timezone info object, falling back to server timezone."""
        tz = self.timezone or get_server_timezone()
        return zoneinfo.ZoneInfo(tz)

    def next_run_after(self, from_time: dt.datetime) -> dt.datetime | None:
        """
        Calculate the next run time after the given time.

        Args:
            from_time: The reference time (usually now)

        Returns:
            Next run datetime, or None if schedule is exhausted
        """
        raise NotImplementedError


class OnceScheduleConfig(BaseScheduleConfig):
    """
    Schedule configuration for a single execution.

    The function will run once at the specified date and time.
    After execution, the schedule becomes inactive.
    """

    method: ScheduleMethod = ScheduleMethod.ONCE
    run_date: dt.date = Field(alias="date", description="Date to run (YYYY-MM-DD)")
    run_time: dt.time = Field(alias="time", description="Time to run (HH:MM:SS)")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    def next_run_after(self, from_time: dt.datetime) -> dt.datetime | None:
        """
        Get the scheduled run time if it's in the future.

        Returns None if the scheduled time has passed.
        """
        tz = self.tzinfo()
        target = dt.datetime.combine(self.run_date, self.run_time, tzinfo=tz)

        # Convert from_time to same timezone for comparison
        from_time_tz = from_time.astimezone(tz)

        if target <= from_time_tz:
            # Scheduled time has passed
            return None

        return target


class IntervalScheduleConfig(BaseScheduleConfig):
    """
    Schedule configuration for repeated execution at fixed intervals.

    The function will run every N seconds/minutes/hours/days.
    """

    method: ScheduleMethod = ScheduleMethod.INTERVAL
    unit: IntervalUnit = Field(description="Time unit for interval")
    value: int = Field(gt=0, description="Interval value (must be positive)")

    def next_run_after(self, from_time: dt.datetime) -> dt.datetime | None:
        """Calculate the next run time based on interval."""
        tz = self.tzinfo()
        base = from_time.astimezone(tz)

        delta_map = {
            IntervalUnit.SECONDS: dt.timedelta(seconds=self.value),
            IntervalUnit.MINUTES: dt.timedelta(minutes=self.value),
            IntervalUnit.HOURS: dt.timedelta(hours=self.value),
            IntervalUnit.DAYS: dt.timedelta(days=self.value),
        }

        return base + delta_map[self.unit]


class CronScheduleConfig(BaseScheduleConfig):
    """
    Schedule configuration for cron-based execution.

    Uses standard cron expression syntax (5 fields):
    minute hour day_of_month month day_of_week

    Examples:
        "0 8 * * *" - Every day at 8:00 AM
        "*/15 * * * *" - Every 15 minutes
        "0 0 1 * *" - First day of each month at midnight
    """

    method: ScheduleMethod = ScheduleMethod.CRON
    cron: str = Field(description="Cron expression (5 fields)")
    description: str | None = Field(
        default=None, description="Human-readable description of the schedule"
    )

    def next_run_after(self, from_time: dt.datetime) -> dt.datetime | None:
        """Calculate the next run time based on cron expression."""
        tz = self.tzinfo()
        base = from_time.astimezone(tz)

        try:
            cron_iter = croniter(self.cron, base)
            next_time = cron_iter.get_next(dt.datetime)
            return next_time.replace(tzinfo=tz)
        except Exception:
            # Invalid cron expression
            return None


# Discriminated union type for schedule configurations
ScheduleConfig = Annotated[
    Union[OnceScheduleConfig, IntervalScheduleConfig, CronScheduleConfig],
    Field(discriminator="method"),
]


# =============================================================================
# Helper Functions
# =============================================================================


def parse_schedule_config(schedule_dict: dict) -> ScheduleConfig:
    """
    Parse a schedule configuration dictionary into a typed config object.

    Args:
        schedule_dict: Dictionary with schedule configuration

    Returns:
        Typed schedule config (OnceScheduleConfig, IntervalScheduleConfig, or CronScheduleConfig)

    Raises:
        ValueError: If the schedule is invalid
    """
    method = schedule_dict.get("method")

    # Support both string and enum values
    if method in (ScheduleMethod.ONCE, "once"):
        return OnceScheduleConfig.model_validate(schedule_dict)
    elif method in (ScheduleMethod.INTERVAL, "interval"):
        return IntervalScheduleConfig.model_validate(schedule_dict)
    elif method in (ScheduleMethod.CRON, "cron"):
        return CronScheduleConfig.model_validate(schedule_dict)
    else:
        raise ValueError(f"Unknown schedule method: {method}")


def validate_cron_expression(cron_expr: str) -> bool:
    """
    Validate a cron expression.

    Args:
        cron_expr: The cron expression to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        croniter(cron_expr)
        return True
    except Exception:
        return False


def validate_timezone(tz_name: str) -> bool:
    """
    Validate a timezone name.

    Args:
        tz_name: The timezone name to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        zoneinfo.ZoneInfo(tz_name)
        return True
    except Exception:
        return False
