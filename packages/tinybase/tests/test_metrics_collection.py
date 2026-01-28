"""
Tests for metrics collection functionality.

Tests the metrics collection service including:
- Collection sizes metrics
- Function execution statistics
- Metrics cleanup
- Latest metrics retrieval
"""

from datetime import timedelta

import pytest
from sqlmodel import Session, select
from tinybase.db.models import Collection, FunctionCall, Metrics, Record
from tinybase.metrics import (
    _cleanup_old_metrics,
    _collect_collection_sizes,
    _collect_function_stats,
    collect_metrics,
    get_function_stats_lookback_hours,
    get_latest_metrics,
    get_max_metric_snapshots,
)
from tinybase.utils import FunctionCallStatus, utcnow

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def db_session(client):
    """Get a database session for testing."""
    from tinybase.db.core import get_db_engine

    engine = get_db_engine()
    with Session(engine) as session:
        yield session


@pytest.fixture
def sample_collections(db_session):
    """Create sample collections with records."""
    collections = []

    # Collection 1 with 3 records
    coll1 = Collection(
        name="test_collection_1",
        label="Test Collection 1",
        schema_={"fields": [{"name": "title", "type": "string"}]},
    )
    db_session.add(coll1)
    db_session.commit()
    db_session.refresh(coll1)
    collections.append(coll1)

    for i in range(3):
        record = Record(
            collection_id=coll1.id,
            data={"title": f"Record {i}"},
        )
        db_session.add(record)

    # Collection 2 with 5 records
    coll2 = Collection(
        name="test_collection_2",
        label="Test Collection 2",
        schema_={"fields": [{"name": "name", "type": "string"}]},
    )
    db_session.add(coll2)
    db_session.commit()
    db_session.refresh(coll2)
    collections.append(coll2)

    for i in range(5):
        record = Record(
            collection_id=coll2.id,
            data={"name": f"Name {i}"},
        )
        db_session.add(record)

    db_session.commit()
    return collections


@pytest.fixture
def sample_function_calls(db_session):
    """Create sample function calls for testing."""
    calls = []
    now = utcnow()

    # Successful calls for function_a
    for i in range(5):
        call = FunctionCall(
            function_name="function_a",
            status=FunctionCallStatus.SUCCEEDED,
            duration_ms=100 + i * 10,  # 100, 110, 120, 130, 140
            created_at=now - timedelta(hours=i),
        )
        db_session.add(call)
        calls.append(call)

    # Mixed calls for function_b (2 success, 2 failed)
    for i in range(4):
        status = FunctionCallStatus.SUCCEEDED if i < 2 else FunctionCallStatus.FAILED
        call = FunctionCall(
            function_name="function_b",
            status=status,
            duration_ms=200 if status == FunctionCallStatus.SUCCEEDED else None,
            created_at=now - timedelta(hours=i),
        )
        db_session.add(call)
        calls.append(call)

    db_session.commit()
    return calls


# =============================================================================
# Configuration Tests
# =============================================================================


def test_get_function_stats_lookback_hours():
    """Test getting function stats lookback hours."""
    hours = get_function_stats_lookback_hours()
    assert hours == 24


def test_get_max_metric_snapshots():
    """Test getting max metric snapshots."""
    max_snapshots = get_max_metric_snapshots()
    assert max_snapshots == 1000


# =============================================================================
# Collection Sizes Tests
# =============================================================================


def test_collect_collection_sizes_empty(db_session):
    """Test collecting collection sizes when no collections exist."""
    sizes = _collect_collection_sizes(db_session)
    assert sizes == {}


def test_collect_collection_sizes(db_session, sample_collections):
    """Test collecting collection sizes."""
    sizes = _collect_collection_sizes(db_session)

    assert "test_collection_1" in sizes
    assert "test_collection_2" in sizes
    assert sizes["test_collection_1"] == 3
    assert sizes["test_collection_2"] == 5


def test_collect_collection_sizes_empty_collection(db_session):
    """Test collecting sizes for an empty collection."""
    # Create collection without records
    coll = Collection(
        name="empty_collection",
        label="Empty Collection",
        schema_={"fields": []},
    )
    db_session.add(coll)
    db_session.commit()

    sizes = _collect_collection_sizes(db_session)

    assert "empty_collection" in sizes
    assert sizes["empty_collection"] == 0


# =============================================================================
# Function Stats Tests
# =============================================================================


def test_collect_function_stats_empty(db_session):
    """Test collecting function stats when no function calls exist."""
    stats = _collect_function_stats(db_session)
    assert stats == {}


def test_collect_function_stats(db_session, sample_function_calls):
    """Test collecting function execution statistics."""
    stats = _collect_function_stats(db_session)

    assert "function_a" in stats
    assert "function_b" in stats

    # Function A: 5 successful calls, avg runtime = (100+110+120+130+140)/5 = 120
    func_a_stats = stats["function_a"]
    assert func_a_stats["total_calls"] == 5
    assert func_a_stats["error_rate"] == 0.0
    assert func_a_stats["avg_runtime_ms"] == 120.0

    # Function B: 4 calls, 2 failed = 50% error rate
    func_b_stats = stats["function_b"]
    assert func_b_stats["total_calls"] == 4
    assert func_b_stats["error_rate"] == 50.0
    # Only completed calls have duration, avg = 200
    assert func_b_stats["avg_runtime_ms"] == 200.0


def test_collect_function_stats_all_failed(db_session):
    """Test function stats when all calls failed."""
    now = utcnow()

    for i in range(3):
        call = FunctionCall(
            function_name="failing_func",
            status=FunctionCallStatus.FAILED,
            duration_ms=None,
            created_at=now - timedelta(hours=i),
        )
        db_session.add(call)
    db_session.commit()

    stats = _collect_function_stats(db_session)

    assert "failing_func" in stats
    assert stats["failing_func"]["total_calls"] == 3
    assert stats["failing_func"]["error_rate"] == 100.0
    assert stats["failing_func"]["avg_runtime_ms"] is None


def test_collect_function_stats_lookback_window(db_session):
    """Test that function stats only considers recent calls."""
    now = utcnow()
    lookback_hours = get_function_stats_lookback_hours()

    # Recent call (within lookback)
    recent_call = FunctionCall(
        function_name="recent_func",
        status=FunctionCallStatus.SUCCEEDED,
        duration_ms=100,
        created_at=now - timedelta(hours=1),
    )
    db_session.add(recent_call)

    # Old call (outside lookback)
    old_call = FunctionCall(
        function_name="old_func",
        status=FunctionCallStatus.SUCCEEDED,
        duration_ms=100,
        created_at=now - timedelta(hours=lookback_hours + 1),
    )
    db_session.add(old_call)
    db_session.commit()

    stats = _collect_function_stats(db_session)

    # Only recent function should be included
    assert "recent_func" in stats
    assert "old_func" not in stats


# =============================================================================
# Metrics Collection Tests
# =============================================================================


def test_collect_metrics(db_session, sample_collections, sample_function_calls):
    """Test full metrics collection."""
    collect_metrics(db_session)

    # Check collection_sizes metric was created
    collection_sizes = db_session.exec(
        select(Metrics).where(Metrics.metric_type == "collection_sizes")
    ).first()
    assert collection_sizes is not None
    assert "test_collection_1" in collection_sizes.data
    assert "test_collection_2" in collection_sizes.data

    # Check function_stats metric was created
    function_stats = db_session.exec(
        select(Metrics).where(Metrics.metric_type == "function_stats")
    ).first()
    assert function_stats is not None
    assert "function_a" in function_stats.data
    assert "function_b" in function_stats.data


def test_collect_metrics_no_data(db_session):
    """Test metrics collection when no data exists."""
    collect_metrics(db_session)

    # No metrics should be created if there's no data
    metrics_count = db_session.exec(select(Metrics)).all()
    # Both collection_sizes and function_stats are empty dicts, which are falsy
    # so no metrics records should be created
    assert len(metrics_count) == 0


def test_collect_metrics_error_handling(db_session):
    """Test metrics collection error handling."""
    from unittest.mock import patch

    with patch(
        "tinybase.metrics._collect_collection_sizes",
        side_effect=Exception("Test error"),
    ):
        with pytest.raises(Exception) as exc_info:
            collect_metrics(db_session)

        assert "Test error" in str(exc_info.value)


# =============================================================================
# Cleanup Tests
# =============================================================================


def test_cleanup_old_metrics_under_limit(db_session):
    """Test cleanup when under the limit."""
    # Create 5 metrics (under the 1000 limit)
    for i in range(5):
        metric = Metrics(
            metric_type="test",
            data={"test": i},
            collected_at=utcnow() - timedelta(hours=i),
        )
        db_session.add(metric)
    db_session.commit()

    initial_count = len(db_session.exec(select(Metrics)).all())
    assert initial_count == 5

    _cleanup_old_metrics(db_session)
    db_session.commit()

    # No metrics should be deleted
    final_count = len(db_session.exec(select(Metrics)).all())
    assert final_count == 5


def test_cleanup_old_metrics_over_limit(db_session):
    """Test cleanup when over the limit."""
    from datetime import timezone
    from unittest.mock import patch

    # Mock max_snapshots to a small number for testing
    with patch("tinybase.metrics.get_max_metric_snapshots", return_value=5):
        # Create 10 metrics (over the 5 limit)
        for i in range(10):
            metric = Metrics(
                metric_type="test",
                data={"test": i},
                collected_at=utcnow() - timedelta(hours=i),
            )
            db_session.add(metric)
        db_session.commit()

        _cleanup_old_metrics(db_session)
        db_session.commit()

        # Should be down to 5 metrics
        remaining = db_session.exec(select(Metrics)).all()
        assert len(remaining) == 5

        # The remaining should be the most recent ones (hours 0-4)
        now = utcnow()
        collected_hours = []
        for m in remaining:
            # Ensure collected_at is timezone-aware for comparison
            collected_at = m.collected_at
            if collected_at.tzinfo is None:
                collected_at = collected_at.replace(tzinfo=timezone.utc)
            diff = (now - collected_at).total_seconds() / 3600
            collected_hours.append(round(diff))

        # Most recent 5 should remain (within ~1 hour tolerance)
        assert max(collected_hours) <= 5


# =============================================================================
# Get Latest Metrics Tests
# =============================================================================


def test_get_latest_metrics_empty(db_session):
    """Test getting latest metrics when none exist."""
    result = get_latest_metrics(db_session)
    assert result is None


def test_get_latest_metrics(db_session):
    """Test getting latest metrics."""
    # Create some metrics with different timestamps
    old_collection_sizes = Metrics(
        metric_type="collection_sizes",
        data={"old_collection": 10},
        collected_at=utcnow() - timedelta(hours=2),
    )
    new_collection_sizes = Metrics(
        metric_type="collection_sizes",
        data={"new_collection": 20},
        collected_at=utcnow() - timedelta(hours=1),
    )
    function_stats = Metrics(
        metric_type="function_stats",
        data={"func": {"total_calls": 5}},
        collected_at=utcnow(),
    )
    db_session.add(old_collection_sizes)
    db_session.add(new_collection_sizes)
    db_session.add(function_stats)
    db_session.commit()

    result = get_latest_metrics(db_session)

    assert result is not None
    assert "collection_sizes" in result
    assert "function_stats" in result

    # Should get the newest collection_sizes
    assert result["collection_sizes"].data == {"new_collection": 20}
    assert result["function_stats"].data == {"func": {"total_calls": 5}}


def test_get_latest_metrics_partial(db_session):
    """Test getting latest metrics when only some types exist."""
    # Only create collection_sizes
    metric = Metrics(
        metric_type="collection_sizes",
        data={"collection": 5},
        collected_at=utcnow(),
    )
    db_session.add(metric)
    db_session.commit()

    result = get_latest_metrics(db_session)

    assert result is not None
    assert "collection_sizes" in result
    assert "function_stats" not in result


def test_get_latest_metrics_error_handling(db_session):
    """Test get_latest_metrics error handling."""
    from unittest.mock import patch

    with patch("tinybase.metrics.select", side_effect=Exception("DB error")):
        result = get_latest_metrics(db_session)
        assert result is None


# =============================================================================
# Integration Tests
# =============================================================================


def test_full_metrics_workflow(db_session, sample_collections, sample_function_calls):
    """Test complete metrics collection workflow."""
    # Collect metrics
    collect_metrics(db_session)

    # Retrieve latest metrics
    latest = get_latest_metrics(db_session)

    assert latest is not None
    assert "collection_sizes" in latest
    assert "function_stats" in latest

    # Verify collection sizes
    collection_data = latest["collection_sizes"].data
    assert collection_data["test_collection_1"] == 3
    assert collection_data["test_collection_2"] == 5

    # Verify function stats
    function_data = latest["function_stats"].data
    assert function_data["function_a"]["total_calls"] == 5
    assert function_data["function_b"]["error_rate"] == 50.0


def test_multiple_metrics_collections(db_session, sample_collections):
    """Test multiple metrics collection cycles."""
    # First collection
    collect_metrics(db_session)

    # Add more records
    coll = db_session.exec(select(Collection).where(Collection.name == "test_collection_1")).first()
    for i in range(2):
        record = Record(
            collection_id=coll.id,
            data={"title": f"New Record {i}"},
        )
        db_session.add(record)
    db_session.commit()

    # Second collection
    collect_metrics(db_session)

    # Get latest - should show updated count
    latest = get_latest_metrics(db_session)
    assert latest["collection_sizes"].data["test_collection_1"] == 5  # 3 + 2
