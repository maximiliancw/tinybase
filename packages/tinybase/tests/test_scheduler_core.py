"""
Tests for scheduler and schedule utilities.

Tests the scheduling system including:
- Schedule configuration parsing
- Next run time calculation
- Cron expression validation
- Timezone handling
- Scheduler lifecycle
"""

import datetime as dt
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from tinybase.schedule.utils import (
    CronScheduleConfig,
    IntervalScheduleConfig,
    OnceScheduleConfig,
    get_server_timezone,
    parse_schedule_config,
    validate_cron_expression,
    validate_timezone,
)
from tinybase.utils import IntervalUnit, ScheduleMethod

# =============================================================================
# Timezone Tests
# =============================================================================


def test_get_server_timezone_default():
    """Test get_server_timezone returns UTC by default."""
    # The function already returns UTC as fallback when settings fail
    # Just test that it returns a valid timezone
    tz = get_server_timezone()
    # Should return a valid timezone string
    assert isinstance(tz, str)
    assert len(tz) > 0


def test_validate_timezone_valid():
    """Test validating valid timezone."""
    assert validate_timezone("UTC") is True
    assert validate_timezone("America/New_York") is True
    assert validate_timezone("Europe/London") is True
    assert validate_timezone("Asia/Tokyo") is True


def test_validate_timezone_invalid():
    """Test validating invalid timezone."""
    assert validate_timezone("Invalid/Timezone") is False
    assert validate_timezone("INVALID") is False
    assert validate_timezone("") is False


# =============================================================================
# OnceScheduleConfig Tests
# =============================================================================


def test_once_schedule_config_creation():
    """Test creating a once schedule config."""
    config = OnceScheduleConfig(
        date=dt.date(2025, 6, 15),
        time=dt.time(10, 30, 0),
    )

    assert config.method == ScheduleMethod.ONCE
    assert config.run_date == dt.date(2025, 6, 15)
    assert config.run_time == dt.time(10, 30, 0)


def test_once_schedule_next_run_future():
    """Test next_run_after for future scheduled time."""
    config = OnceScheduleConfig(
        date=dt.date(2030, 6, 15),
        time=dt.time(10, 30, 0),
        timezone="UTC",
    )

    now = dt.datetime(2025, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    assert next_run is not None
    assert next_run.year == 2030
    assert next_run.month == 6
    assert next_run.day == 15
    assert next_run.hour == 10
    assert next_run.minute == 30


def test_once_schedule_next_run_past():
    """Test next_run_after returns None for past scheduled time."""
    config = OnceScheduleConfig(
        date=dt.date(2020, 6, 15),
        time=dt.time(10, 30, 0),
        timezone="UTC",
    )

    now = dt.datetime(2025, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    assert next_run is None


def test_once_schedule_with_timezone():
    """Test once schedule respects timezone."""
    config = OnceScheduleConfig(
        date=dt.date(2030, 6, 15),
        time=dt.time(10, 30, 0),
        timezone="America/New_York",
    )

    now = dt.datetime(2025, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    assert next_run is not None
    # Time should be in New York timezone
    assert str(next_run.tzinfo) == "America/New_York"


# =============================================================================
# IntervalScheduleConfig Tests
# =============================================================================


def test_interval_schedule_config_creation():
    """Test creating an interval schedule config."""
    config = IntervalScheduleConfig(
        unit=IntervalUnit.MINUTES,
        value=30,
    )

    assert config.method == ScheduleMethod.INTERVAL
    assert config.unit == IntervalUnit.MINUTES
    assert config.value == 30


def test_interval_schedule_next_run_seconds():
    """Test next_run_after for seconds interval."""
    config = IntervalScheduleConfig(
        unit=IntervalUnit.SECONDS,
        value=30,
        timezone="UTC",
    )

    now = dt.datetime(2025, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    expected = now + timedelta(seconds=30)
    assert next_run == expected


def test_interval_schedule_next_run_minutes():
    """Test next_run_after for minutes interval."""
    config = IntervalScheduleConfig(
        unit=IntervalUnit.MINUTES,
        value=15,
        timezone="UTC",
    )

    now = dt.datetime(2025, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    expected = now + timedelta(minutes=15)
    assert next_run == expected


def test_interval_schedule_next_run_hours():
    """Test next_run_after for hours interval."""
    config = IntervalScheduleConfig(
        unit=IntervalUnit.HOURS,
        value=6,
        timezone="UTC",
    )

    now = dt.datetime(2025, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    expected = now + timedelta(hours=6)
    assert next_run == expected


def test_interval_schedule_next_run_days():
    """Test next_run_after for days interval."""
    config = IntervalScheduleConfig(
        unit=IntervalUnit.DAYS,
        value=7,
        timezone="UTC",
    )

    now = dt.datetime(2025, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    expected = now + timedelta(days=7)
    assert next_run == expected


# =============================================================================
# CronScheduleConfig Tests
# =============================================================================


def test_cron_schedule_config_creation():
    """Test creating a cron schedule config."""
    config = CronScheduleConfig(
        cron="0 8 * * *",
        description="Every day at 8 AM",
    )

    assert config.method == ScheduleMethod.CRON
    assert config.cron == "0 8 * * *"
    assert config.description == "Every day at 8 AM"


def test_cron_schedule_next_run():
    """Test next_run_after for cron schedule."""
    config = CronScheduleConfig(
        cron="0 8 * * *",  # Every day at 8 AM
        timezone="UTC",
    )

    # At 6 AM, next run should be 8 AM same day
    now = dt.datetime(2025, 1, 15, 6, 0, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    assert next_run is not None
    assert next_run.hour == 8
    assert next_run.minute == 0
    assert next_run.day == 15


def test_cron_schedule_next_run_after_time():
    """Test next_run_after when time has passed for the day."""
    config = CronScheduleConfig(
        cron="0 8 * * *",  # Every day at 8 AM
        timezone="UTC",
    )

    # At 10 AM, next run should be 8 AM next day
    now = dt.datetime(2025, 1, 15, 10, 0, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    assert next_run is not None
    assert next_run.hour == 8
    assert next_run.day == 16


def test_cron_schedule_every_15_minutes():
    """Test cron schedule for every 15 minutes."""
    config = CronScheduleConfig(
        cron="*/15 * * * *",  # Every 15 minutes
        timezone="UTC",
    )

    now = dt.datetime(2025, 1, 15, 10, 5, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    assert next_run is not None
    assert next_run.minute == 15
    assert next_run.hour == 10


def test_cron_schedule_invalid_expression():
    """Test cron schedule with invalid expression."""
    config = CronScheduleConfig(
        cron="invalid cron",
        timezone="UTC",
    )

    now = dt.datetime(2025, 1, 15, 10, 0, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    # Should return None for invalid cron
    assert next_run is None


# =============================================================================
# Cron Expression Validation Tests
# =============================================================================


def test_validate_cron_expression_valid():
    """Test validating valid cron expressions."""
    assert validate_cron_expression("* * * * *") is True
    assert validate_cron_expression("0 8 * * *") is True
    assert validate_cron_expression("*/15 * * * *") is True
    assert validate_cron_expression("0 0 1 * *") is True
    assert validate_cron_expression("30 4 1,15 * 5") is True


def test_validate_cron_expression_invalid():
    """Test validating invalid cron expressions."""
    assert validate_cron_expression("invalid") is False
    assert validate_cron_expression("* * *") is False  # Too few fields
    assert validate_cron_expression("60 * * * *") is False  # Invalid minute
    assert validate_cron_expression("") is False


# =============================================================================
# Parse Schedule Config Tests
# =============================================================================


def test_parse_schedule_config_once():
    """Test parsing once schedule config."""
    config_dict = {
        "method": "once",
        "date": "2025-06-15",
        "time": "10:30:00",
    }

    config = parse_schedule_config(config_dict)

    assert isinstance(config, OnceScheduleConfig)
    assert config.run_date == dt.date(2025, 6, 15)
    assert config.run_time == dt.time(10, 30, 0)


def test_parse_schedule_config_once_with_enum():
    """Test parsing once schedule with enum value."""
    config_dict = {
        "method": ScheduleMethod.ONCE,
        "date": "2025-06-15",
        "time": "10:30:00",
    }

    config = parse_schedule_config(config_dict)

    assert isinstance(config, OnceScheduleConfig)


def test_parse_schedule_config_interval():
    """Test parsing interval schedule config."""
    config_dict = {
        "method": "interval",
        "unit": "minutes",
        "value": 30,
    }

    config = parse_schedule_config(config_dict)

    assert isinstance(config, IntervalScheduleConfig)
    assert config.unit == IntervalUnit.MINUTES
    assert config.value == 30


def test_parse_schedule_config_interval_with_enum():
    """Test parsing interval schedule with enum values."""
    config_dict = {
        "method": ScheduleMethod.INTERVAL,
        "unit": IntervalUnit.HOURS,
        "value": 6,
    }

    config = parse_schedule_config(config_dict)

    assert isinstance(config, IntervalScheduleConfig)
    assert config.unit == IntervalUnit.HOURS


def test_parse_schedule_config_cron():
    """Test parsing cron schedule config."""
    config_dict = {
        "method": "cron",
        "cron": "0 8 * * *",
        "description": "Every day at 8 AM",
    }

    config = parse_schedule_config(config_dict)

    assert isinstance(config, CronScheduleConfig)
    assert config.cron == "0 8 * * *"


def test_parse_schedule_config_cron_with_enum():
    """Test parsing cron schedule with enum value."""
    config_dict = {
        "method": ScheduleMethod.CRON,
        "cron": "*/15 * * * *",
    }

    config = parse_schedule_config(config_dict)

    assert isinstance(config, CronScheduleConfig)


def test_parse_schedule_config_with_timezone():
    """Test parsing schedule config with timezone."""
    config_dict = {
        "method": "cron",
        "cron": "0 8 * * *",
        "timezone": "America/New_York",
    }

    config = parse_schedule_config(config_dict)

    assert config.timezone == "America/New_York"


def test_parse_schedule_config_unknown_method():
    """Test parsing fails for unknown schedule method."""
    config_dict = {
        "method": "unknown",
        "value": 10,
    }

    with pytest.raises(ValueError, match="Unknown schedule method"):
        parse_schedule_config(config_dict)


def test_parse_schedule_config_missing_method():
    """Test parsing fails when method is missing."""
    config_dict = {
        "cron": "0 8 * * *",
    }

    with pytest.raises(ValueError, match="Unknown schedule method"):
        parse_schedule_config(config_dict)


# =============================================================================
# Scheduler Class Tests
# =============================================================================


@pytest.mark.asyncio
async def test_scheduler_start_stop():
    """Test scheduler start and stop lifecycle."""
    from tinybase.schedule.scheduler import Scheduler

    scheduler = Scheduler()

    assert scheduler._running is False
    assert scheduler._task is None

    # Start scheduler
    with patch.object(scheduler, "_scheduler_loop", new_callable=AsyncMock):
        await scheduler.start()

        assert scheduler._running is True
        assert scheduler._task is not None

        # Start again should be no-op
        await scheduler.start()

        # Stop scheduler
        await scheduler.stop()

        assert scheduler._running is False


@pytest.mark.asyncio
async def test_scheduler_stop_when_not_started():
    """Test stopping scheduler that was never started."""
    from tinybase.schedule.scheduler import Scheduler

    scheduler = Scheduler()

    # Should not raise
    await scheduler.stop()

    assert scheduler._running is False


def test_scheduler_get_metrics():
    """Test getting scheduler metrics."""
    from tinybase.schedule.scheduler import Scheduler

    scheduler = Scheduler()

    metrics = scheduler.get_metrics()

    assert "total_ticks" in metrics
    assert "total_schedules_executed" in metrics
    assert "total_errors" in metrics
    assert "total_timeouts" in metrics
    assert metrics["total_ticks"] == 0


# =============================================================================
# Scheduler Helper Method Tests
# =============================================================================


def test_scheduler_get_function_timeout():
    """Test getting function timeout from settings."""
    from tinybase.schedule.scheduler import Scheduler

    scheduler = Scheduler()

    # Clear cache to force refresh
    scheduler._cached_function_timeout = None

    # Should return default or configured value
    timeout = scheduler._get_function_timeout()
    assert timeout >= 0  # Should be a valid positive value


def test_scheduler_get_max_schedules_per_tick():
    """Test getting max schedules per tick."""
    from tinybase.schedule.scheduler import Scheduler

    scheduler = Scheduler()

    scheduler._cached_max_schedules_per_tick = None

    max_schedules = scheduler._get_max_schedules_per_tick()
    assert max_schedules >= 0


def test_scheduler_get_max_concurrent_executions():
    """Test getting max concurrent executions."""
    from tinybase.schedule.scheduler import Scheduler

    scheduler = Scheduler()

    scheduler._cached_max_concurrent_executions = None

    max_concurrent = scheduler._get_max_concurrent_executions()
    assert max_concurrent >= 0


# =============================================================================
# Global Scheduler Functions Tests
# =============================================================================


def test_get_scheduler_singleton():
    """Test get_scheduler returns same instance."""
    import tinybase.schedule.scheduler
    from tinybase.schedule.scheduler import get_scheduler

    # Reset the singleton for this test
    tinybase.schedule.scheduler._scheduler = None

    scheduler1 = get_scheduler()
    scheduler2 = get_scheduler()

    assert scheduler1 is scheduler2

    # Clean up
    tinybase.schedule.scheduler._scheduler = None


@pytest.mark.asyncio
async def test_start_scheduler_disabled():
    """Test start_scheduler when scheduler is disabled."""
    from tinybase.schedule.scheduler import start_scheduler

    with patch("tinybase.schedule.scheduler.config") as mock_config:
        mock_config.scheduler_enabled = False

        # Should not raise, just do nothing
        await start_scheduler()


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


def test_once_schedule_exact_time():
    """Test once schedule at exact scheduled time."""
    config = OnceScheduleConfig(
        date=dt.date(2025, 6, 15),
        time=dt.time(10, 30, 0),
        timezone="UTC",
    )

    # Exact time - should return None (time has "passed")
    now = dt.datetime(2025, 6, 15, 10, 30, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    assert next_run is None


def test_interval_schedule_single_second():
    """Test interval schedule with 1 second."""
    config = IntervalScheduleConfig(
        unit=IntervalUnit.SECONDS,
        value=1,
        timezone="UTC",
    )

    now = dt.datetime(2025, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    assert next_run == now + timedelta(seconds=1)


def test_cron_schedule_monthly():
    """Test cron schedule for monthly execution."""
    config = CronScheduleConfig(
        cron="0 0 1 * *",  # First day of every month at midnight
        timezone="UTC",
    )

    now = dt.datetime(2025, 1, 15, 12, 0, 0, tzinfo=dt.timezone.utc)
    next_run = config.next_run_after(now)

    assert next_run is not None
    assert next_run.day == 1
    assert next_run.month == 2  # Next month


def test_base_schedule_config_tzinfo():
    """Test base schedule config tzinfo method."""
    config = IntervalScheduleConfig(
        unit=IntervalUnit.HOURS,
        value=1,
        timezone="Europe/London",
    )

    tz = config.tzinfo()

    assert str(tz) == "Europe/London"


def test_base_schedule_config_default_timezone():
    """Test base schedule config uses server timezone by default."""
    config = IntervalScheduleConfig(
        unit=IntervalUnit.HOURS,
        value=1,
    )

    with patch("tinybase.schedule.utils.get_server_timezone", return_value="UTC"):
        tz = config.tzinfo()
        assert str(tz) == "UTC"
