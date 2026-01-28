"""
Tests for function execution metrics endpoint.
"""

from datetime import timedelta

from tinybase.db.models import FunctionCall
from tinybase.utils import FunctionCallStatus, TriggerType, utcnow


class TestFunctionMetrics:
    """Test function metrics aggregation endpoint."""

    def test_metrics_endpoint_requires_admin(self, client, user_token):
        """Test that metrics endpoint requires admin authentication."""
        response = client.get(
            "/api/admin/functions/metrics",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403

    def test_metrics_endpoint_no_data(self, client, admin_token):
        """Test metrics endpoint with no function calls."""
        response = client.get(
            "/api/admin/functions/metrics",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["period_hours"] == 24
        assert data["functions"] == {}

    def test_metrics_aggregation(self, client, admin_token):
        """Test that metrics are properly aggregated by function name."""
        from sqlmodel import Session
        from tinybase.db.core import get_db_engine

        now = utcnow()

        # Get database session
        engine = get_db_engine()
        with Session(engine) as session:
            # Create function calls
            calls = [
                FunctionCall(
                    function_name="test_func1",
                    status=FunctionCallStatus.SUCCEEDED,
                    trigger_type=TriggerType.MANUAL,
                    started_at=now,
                    finished_at=now + timedelta(milliseconds=100),
                    duration_ms=100,
                ),
                FunctionCall(
                    function_name="test_func1",
                    status=FunctionCallStatus.SUCCEEDED,
                    trigger_type=TriggerType.MANUAL,
                    started_at=now,
                    finished_at=now + timedelta(milliseconds=200),
                    duration_ms=200,
                ),
                FunctionCall(
                    function_name="test_func1",
                    status=FunctionCallStatus.FAILED,
                    trigger_type=TriggerType.MANUAL,
                    started_at=now,
                    finished_at=now + timedelta(milliseconds=50),
                    duration_ms=50,
                    error_message="Test error",
                    error_type="TestError",
                ),
                FunctionCall(
                    function_name="test_func2",
                    status=FunctionCallStatus.SUCCEEDED,
                    trigger_type=TriggerType.MANUAL,
                    started_at=now,
                    finished_at=now + timedelta(milliseconds=300),
                    duration_ms=300,
                ),
            ]

            for call in calls:
                session.add(call)
            session.commit()

        response = client.get(
            "/api/admin/functions/metrics",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check test_func1 metrics
        assert "test_func1" in data["functions"]
        func1 = data["functions"]["test_func1"]
        assert func1["total_calls"] == 3
        assert func1["succeeded"] == 2
        assert func1["failed"] == 1
        # Average of 100, 200, 50 = 116.67
        assert 110 < func1["avg_duration_ms"] < 120

        # Check test_func2 metrics
        assert "test_func2" in data["functions"]
        func2 = data["functions"]["test_func2"]
        assert func2["total_calls"] == 1
        assert func2["succeeded"] == 1
        assert func2["failed"] == 0
        assert func2["avg_duration_ms"] == 300

    def test_metrics_time_range_filtering(self, client, admin_token):
        """Test that metrics respect time range parameter."""
        from sqlmodel import Session
        from tinybase.db.core import get_db_engine

        now = utcnow()

        engine = get_db_engine()
        with Session(engine) as session:
            # Create old call (beyond 24 hours)
            old_call = FunctionCall(
                function_name="old_func",
                status=FunctionCallStatus.SUCCEEDED,
                trigger_type=TriggerType.MANUAL,
                started_at=now - timedelta(hours=48),
                finished_at=now - timedelta(hours=48) + timedelta(milliseconds=100),
                duration_ms=100,
            )

            # Create recent call
            recent_call = FunctionCall(
                function_name="recent_func",
                status=FunctionCallStatus.SUCCEEDED,
                trigger_type=TriggerType.MANUAL,
                started_at=now - timedelta(hours=1),
                finished_at=now - timedelta(hours=1) + timedelta(milliseconds=100),
                duration_ms=100,
            )

            session.add(old_call)
            session.add(recent_call)
            session.commit()

        # Query last 24 hours
        response = client.get(
            "/api/admin/functions/metrics?hours=24",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should only see recent function
        assert "recent_func" in data["functions"]
        assert "old_func" not in data["functions"]

    def test_metrics_custom_time_range(self, client, admin_token):
        """Test metrics with custom time range parameter."""
        from sqlmodel import Session
        from tinybase.db.core import get_db_engine

        now = utcnow()

        engine = get_db_engine()
        with Session(engine) as session:
            # Create call within 1 hour
            recent_call = FunctionCall(
                function_name="recent",
                status=FunctionCallStatus.SUCCEEDED,
                trigger_type=TriggerType.MANUAL,
                started_at=now - timedelta(minutes=30),
                finished_at=now - timedelta(minutes=30) + timedelta(milliseconds=100),
                duration_ms=100,
            )

            session.add(recent_call)
            session.commit()

        # Query last 1 hour
        response = client.get(
            "/api/admin/functions/metrics?hours=1",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["period_hours"] == 1
        assert "recent" in data["functions"]

    def test_metrics_avg_duration_no_durations(self, client, admin_token):
        """Test average duration calculation when no durations exist."""
        from sqlmodel import Session
        from tinybase.db.core import get_db_engine

        now = utcnow()

        engine = get_db_engine()
        with Session(engine) as session:
            # Create call without duration
            call = FunctionCall(
                function_name="no_duration",
                status=FunctionCallStatus.RUNNING,
                trigger_type=TriggerType.MANUAL,
                started_at=now,
            )

            session.add(call)
            session.commit()

        response = client.get(
            "/api/admin/functions/metrics",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Function should exist but avg should be 0
        assert "no_duration" in data["functions"]
        assert data["functions"]["no_duration"]["avg_duration_ms"] == 0

    def test_metrics_parameter_validation(self, client, admin_token):
        """Test that hours parameter is validated."""
        # Test minimum
        response = client.get(
            "/api/admin/functions/metrics?hours=0",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422

        # Test maximum
        response = client.get(
            "/api/admin/functions/metrics?hours=1000",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422

        # Test valid values
        response = client.get(
            "/api/admin/functions/metrics?hours=48",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
