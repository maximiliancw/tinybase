"""
Metrics collection service for TinyBase.

Collects periodic snapshots of system metrics:
- Collection sizes (record counts per collection)
- Function execution statistics (average runtime, error rate)
"""

import logging
from datetime import timedelta

from sqlalchemy import func
from sqlmodel import Session, select

from tinybase.db.models import Collection, FunctionCall, Metrics, Record
from tinybase.utils import FunctionCallStatus, utcnow

logger = logging.getLogger(__name__)

# How long to look back for function stats (default: 24 hours)
FUNCTION_STATS_LOOKBACK_HOURS = 24

# Maximum number of old metric snapshots to keep (to prevent unbounded growth)
MAX_METRIC_SNAPSHOTS = 1000


def collect_metrics(session: Session) -> None:
    """
    Collect and store current system metrics.

    This function is called periodically by the scheduler to collect:
    1. Collection sizes (record counts per collection)
    2. Function execution statistics (average runtime, error rate)

    Args:
        session: Database session.
    """
    try:
        # Collect collection sizes
        collection_sizes = _collect_collection_sizes(session)
        if collection_sizes:
            metrics = Metrics(
                metric_type="collection_sizes",
                data=collection_sizes,
                collected_at=utcnow(),
            )
            session.add(metrics)

        # Collect function stats
        function_stats = _collect_function_stats(session)
        if function_stats:
            metrics = Metrics(
                metric_type="function_stats",
                data=function_stats,
                collected_at=utcnow(),
            )
            session.add(metrics)

        # Cleanup old metrics (keep only recent ones)
        _cleanup_old_metrics(session)

        session.commit()
        logger.debug("Metrics collected successfully")

    except Exception as e:
        logger.exception(f"Error collecting metrics: {e}")
        session.rollback()
        raise


def _collect_collection_sizes(session: Session) -> dict[str, int]:
    """
    Collect record counts for each collection.

    Returns:
        Dictionary mapping collection names to record counts.
    """
    # Get all collections
    collections = session.exec(select(Collection)).all()

    sizes = {}
    for collection in collections:
        # Count records efficiently using SQL COUNT
        count_stmt = select(func.count(Record.id)).where(Record.collection_id == collection.id)
        count = session.exec(count_stmt).one()
        sizes[collection.name] = count

    return sizes


def _collect_function_stats(session: Session) -> dict[str, dict]:
    """
    Collect function execution statistics.

    Calculates for each function:
    - Average runtime (in milliseconds)
    - Error rate (percentage of failed calls)
    - Total number of calls

    Only considers calls from the last FUNCTION_STATS_LOOKBACK_HOURS hours.

    Returns:
        Dictionary mapping function names to their statistics.
    """
    # Calculate cutoff time
    cutoff_time = utcnow() - timedelta(hours=FUNCTION_STATS_LOOKBACK_HOURS)

    # Get all function calls from the lookback period
    statement = select(FunctionCall).where(FunctionCall.created_at >= cutoff_time)
    calls = session.exec(statement).all()

    # Group by function name
    function_data: dict[str, list[FunctionCall]] = {}
    for call in calls:
        if call.function_name not in function_data:
            function_data[call.function_name] = []
        function_data[call.function_name].append(call)

    # Calculate statistics for each function
    stats = {}
    for function_name, function_calls in function_data.items():
        total_calls = len(function_calls)

        # Calculate average runtime (only for completed calls with duration)
        runtimes = [call.duration_ms for call in function_calls if call.duration_ms is not None]
        avg_runtime_ms = sum(runtimes) / len(runtimes) if runtimes else None

        # Calculate error rate
        failed_calls = sum(1 for call in function_calls if call.status == FunctionCallStatus.FAILED)
        error_rate = (failed_calls / total_calls * 100) if total_calls > 0 else 0.0

        stats[function_name] = {
            "avg_runtime_ms": round(avg_runtime_ms, 2) if avg_runtime_ms is not None else None,
            "error_rate": round(error_rate, 2),
            "total_calls": total_calls,
        }

    return stats


def _cleanup_old_metrics(session: Session) -> None:
    """
    Remove old metric snapshots to prevent unbounded database growth.

    Keeps only the most recent MAX_METRIC_SNAPSHOTS snapshots.
    """
    # Count total metrics
    count_stmt = select(func.count(Metrics.id))
    total_count = session.exec(count_stmt).one()

    if total_count <= MAX_METRIC_SNAPSHOTS:
        return

    # Delete oldest metrics
    to_delete = total_count - MAX_METRIC_SNAPSHOTS
    statement = select(Metrics).order_by(Metrics.collected_at.asc()).limit(to_delete)
    old_metrics = session.exec(statement).all()

    for metric in old_metrics:
        session.delete(metric)

    logger.info(f"Cleaned up {to_delete} old metric snapshots")
