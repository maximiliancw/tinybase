"""
Tests for the Activity Logging System.

Covers:
- log_activity() helper function
- GET /api/admin/activity endpoint
- GET /api/admin/activity/recent endpoint
- Activity logging integration in auth and collections routes
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from tests.utils import (
    create_collection,
    create_record,
    get_admin_token,
    get_user_token,
)


# =============================================================================
# Helper Function Tests
# =============================================================================


def test_log_activity_creates_record(client):
    """Test that log_activity creates an ActivityLog record in the database."""
    from tinybase.activity import Actions, log_activity
    from tinybase.db.core import get_db_engine
    from tinybase.db.models import ActivityLog, User

    # Get the admin user ID (created by client fixture)
    engine = get_db_engine()
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.email == "admin@test.com")).first()
        user_id = admin.id

    log_activity(
        action=Actions.USER_LOGIN,
        resource_type="user",
        resource_id=str(user_id),
        user_id=user_id,
        meta_data={"test": "value"},
        ip_address="192.168.1.1",
    )

    # Verify the record was created
    with Session(engine) as session:
        activity = session.exec(
            select(ActivityLog)
            .where(ActivityLog.user_id == user_id)
            .where(ActivityLog.meta_data == {"test": "value"})
        ).first()

        assert activity is not None
        assert activity.action == Actions.USER_LOGIN
        assert activity.resource_type == "user"
        assert activity.resource_id == str(user_id)
        assert activity.meta_data == {"test": "value"}
        assert activity.ip_address == "192.168.1.1"


def test_log_activity_handles_optional_parameters(client):
    """Test that log_activity works with minimal parameters."""
    from tinybase.activity import log_activity
    from tinybase.db.core import get_db_engine
    from tinybase.db.models import ActivityLog

    log_activity(action="test.action")

    # Verify the record was created with defaults
    engine = get_db_engine()
    with Session(engine) as session:
        activity = session.exec(
            select(ActivityLog).where(ActivityLog.action == "test.action")
        ).first()

        assert activity is not None
        assert activity.resource_type is None
        assert activity.resource_id is None
        assert activity.user_id is None
        assert activity.meta_data == {}
        assert activity.ip_address is None


def test_log_activity_does_not_raise_on_error(client):
    """Test that log_activity catches errors and doesn't propagate them."""
    from tinybase.activity import log_activity

    # Mock get_db_engine to raise an error
    with patch("tinybase.activity.get_db_engine") as mock_engine:
        mock_engine.side_effect = Exception("Database connection failed")

        # Should not raise - activity logging is fire-and-forget
        log_activity(action="test.action")


# =============================================================================
# API Endpoint Tests - GET /api/admin/activity
# =============================================================================


def test_list_activity_requires_admin(client):
    """Test that listing activity logs requires admin authentication."""
    user_token = get_user_token(client)

    response = client.get(
        "/api/admin/activity",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_list_activity_returns_paginated_response(client, admin_token):
    """Test that list activity returns proper paginated response structure."""
    from tinybase.activity import Actions, log_activity

    # Create some activity entries
    for i in range(3):
        log_activity(action=f"test.action.{i}")

    response = client.get(
        "/api/admin/activity",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert "activities" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["limit"] == 50  # default
    assert data["offset"] == 0  # default


def test_list_activity_filter_by_action(client, admin_token):
    """Test filtering activity logs by action type."""
    from tinybase.activity import log_activity

    # Create activities with different actions
    log_activity(action="user.login")
    log_activity(action="record.create")
    log_activity(action="user.login")

    response = client.get(
        "/api/admin/activity",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"action": "user.login"},
    )
    assert response.status_code == 200

    data = response.json()
    # All returned activities should have the filtered action
    for activity in data["activities"]:
        assert activity["action"] == "user.login"


def test_list_activity_filter_by_resource_type(client, admin_token):
    """Test filtering activity logs by resource type."""
    from tinybase.activity import log_activity

    # Create activities with different resource types
    log_activity(action="test.action", resource_type="user")
    log_activity(action="test.action", resource_type="record")
    log_activity(action="test.action", resource_type="user")

    response = client.get(
        "/api/admin/activity",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"resource_type": "record"},
    )
    assert response.status_code == 200

    data = response.json()
    for activity in data["activities"]:
        assert activity["resource_type"] == "record"


def test_list_activity_filter_by_user_id(client, admin_token):
    """Test filtering activity logs by user ID."""
    from tinybase.db.core import get_db_engine
    from tinybase.db.models import User

    # Get admin user ID
    engine = get_db_engine()
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.email == "admin@test.com")).first()
        admin_id = admin.id

    # The admin login already created activity, filter by admin user ID
    response = client.get(
        "/api/admin/activity",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"user_id": str(admin_id)},
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["activities"]) > 0
    for activity in data["activities"]:
        assert activity["user_id"] == str(admin_id)


def test_list_activity_pagination(client, admin_token):
    """Test pagination with limit and offset."""
    from tinybase.activity import log_activity

    # Create 10 activities
    for i in range(10):
        log_activity(action=f"pagination.test.{i}")

    # Get first page
    response = client.get(
        "/api/admin/activity",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"limit": 3, "offset": 0, "action": "pagination.test.0"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 3
    assert data["offset"] == 0

    # Get second page
    response = client.get(
        "/api/admin/activity",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"limit": 3, "offset": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["offset"] == 3


def test_list_activity_user_email_lookup(client, admin_token):
    """Test that user email is populated for activities with user_id."""
    from tinybase.db.core import get_db_engine
    from tinybase.db.models import User

    # Get admin user ID
    engine = get_db_engine()
    with Session(engine) as session:
        admin_user = session.exec(
            select(User).where(User.email == "admin@test.com")
        ).first()
        admin_id = admin_user.id

    # The login to get admin_token already created an activity
    response = client.get(
        "/api/admin/activity",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"user_id": str(admin_id)},
    )
    assert response.status_code == 200

    data = response.json()
    # At least one activity should have the admin email
    admin_activities = [a for a in data["activities"] if a["user_email"] == "admin@test.com"]
    assert len(admin_activities) > 0


def test_list_activity_ordering_newest_first(client, admin_token):
    """Test that activities are ordered newest first."""
    from tinybase.activity import log_activity
    import time

    # Create activities in sequence
    log_activity(action="ordering.test.first")
    time.sleep(0.01)  # Small delay to ensure different timestamps
    log_activity(action="ordering.test.second")
    time.sleep(0.01)
    log_activity(action="ordering.test.third")

    response = client.get(
        "/api/admin/activity",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    activities = data["activities"]

    # Find our test activities
    ordering_activities = [a for a in activities if a["action"].startswith("ordering.test")]
    
    if len(ordering_activities) >= 3:
        # Should be in reverse order (newest first)
        assert ordering_activities[0]["action"] == "ordering.test.third"
        assert ordering_activities[1]["action"] == "ordering.test.second"
        assert ordering_activities[2]["action"] == "ordering.test.first"


def test_list_activity_response_fields(client, admin_token):
    """Test that activity response contains all expected fields."""
    from tinybase.activity import log_activity

    # Log activity without user_id (system action) to avoid FK constraint
    log_activity(
        action="field.test",
        resource_type="test_resource",
        resource_id="test-123",
        user_id=None,
        meta_data={"key": "value"},
        ip_address="10.0.0.1",
    )

    response = client.get(
        "/api/admin/activity",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"action": "field.test"},
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["activities"]) > 0

    activity = data["activities"][0]
    assert "id" in activity
    assert activity["action"] == "field.test"
    assert activity["resource_type"] == "test_resource"
    assert activity["resource_id"] == "test-123"
    assert activity["user_id"] is None
    assert activity["metadata"] == {"key": "value"}  # API response uses "metadata"
    assert activity["ip_address"] == "10.0.0.1"
    assert "created_at" in activity


# =============================================================================
# API Endpoint Tests - GET /api/admin/activity/recent
# =============================================================================


def test_recent_activity_requires_admin(client):
    """Test that getting recent activity requires admin authentication."""
    user_token = get_user_token(client)

    response = client.get(
        "/api/admin/activity/recent",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_recent_activity_returns_list(client, admin_token):
    """Test that recent activity returns a list of activities."""
    from tinybase.activity import log_activity

    # Create some activities
    for i in range(5):
        log_activity(action=f"recent.test.{i}")

    response = client.get(
        "/api/admin/activity/recent",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


def test_recent_activity_limit_parameter(client, admin_token):
    """Test that limit parameter controls number of returned entries."""
    from tinybase.activity import log_activity

    # Create more activities than the limit
    for i in range(15):
        log_activity(action=f"limit.test.{i}")

    response = client.get(
        "/api/admin/activity/recent",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"limit": 5},
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data) <= 5


def test_recent_activity_default_limit(client, admin_token):
    """Test that default limit is 10."""
    from tinybase.activity import log_activity

    # Create more activities than default limit
    for i in range(15):
        log_activity(action=f"default.limit.test.{i}")

    response = client.get(
        "/api/admin/activity/recent",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data) <= 10


# =============================================================================
# Integration Tests - Activity Logging in Auth Routes
# =============================================================================


def test_login_creates_activity_log(client):
    """Test that successful login creates an activity log entry."""
    from tinybase.activity import Actions
    from tinybase.db.core import get_db_engine
    from tinybase.db.models import ActivityLog

    # Login as admin
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "testpassword"},
    )
    assert response.status_code == 200

    # Check activity log
    engine = get_db_engine()
    with Session(engine) as session:
        activities = list(
            session.exec(
                select(ActivityLog)
                .where(ActivityLog.action == Actions.USER_LOGIN)
                .where(ActivityLog.resource_type == "user")
            ).all()
        )

        assert len(activities) > 0
        activity = activities[-1]  # Most recent
        assert activity.action == Actions.USER_LOGIN
        assert activity.resource_type == "user"
        assert activity.user_id is not None


def test_registration_creates_activity_log(client):
    """Test that user registration creates an activity log entry."""
    from tinybase.activity import Actions
    from tinybase.db.core import get_db_engine
    from tinybase.db.models import ActivityLog

    # Register a new user
    response = client.post(
        "/api/auth/register",
        json={"email": "newuser@test.com", "password": "securepassword123"},
    )
    assert response.status_code == 201

    # Check activity log
    engine = get_db_engine()
    with Session(engine) as session:
        activities = list(
            session.exec(
                select(ActivityLog)
                .where(ActivityLog.action == Actions.USER_REGISTER)
                .where(ActivityLog.resource_type == "user")
            ).all()
        )

        assert len(activities) > 0
        activity = activities[-1]
        assert activity.action == Actions.USER_REGISTER
        assert activity.resource_type == "user"
        assert activity.user_id is not None


# =============================================================================
# Integration Tests - Activity Logging in Collections Routes
# =============================================================================


def test_record_create_activity_log(client, admin_token, test_collection):
    """Test that creating a record creates an activity log entry with collection metadata."""
    from tinybase.activity import Actions
    from tinybase.db.core import get_db_engine
    from tinybase.db.models import ActivityLog

    # Create a record
    response = client.post(
        "/api/collections/test_collection/records",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"title": "Test Record"}},
    )
    assert response.status_code == 201
    record_id = response.json()["id"]

    # Check activity log
    engine = get_db_engine()
    with Session(engine) as session:
        activity = session.exec(
            select(ActivityLog)
            .where(ActivityLog.action == Actions.RECORD_CREATE)
            .where(ActivityLog.resource_id == record_id)
        ).first()

        assert activity is not None
        assert activity.action == Actions.RECORD_CREATE
        assert activity.resource_type == "record"
        assert activity.meta_data.get("collection") == "test_collection"


def test_record_update_activity_log(client, admin_token, test_collection, test_record):
    """Test that updating a record creates an activity log entry with collection metadata."""
    from tinybase.activity import Actions
    from tinybase.db.core import get_db_engine
    from tinybase.db.models import ActivityLog

    record_id = test_record["id"]

    # Update the record
    response = client.patch(
        f"/api/collections/test_collection/records/{record_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"data": {"title": "Updated Title"}},
    )
    assert response.status_code == 200

    # Check activity log
    engine = get_db_engine()
    with Session(engine) as session:
        activity = session.exec(
            select(ActivityLog)
            .where(ActivityLog.action == Actions.RECORD_UPDATE)
            .where(ActivityLog.resource_id == record_id)
        ).first()

        assert activity is not None
        assert activity.action == Actions.RECORD_UPDATE
        assert activity.resource_type == "record"
        assert activity.meta_data.get("collection") == "test_collection"


def test_record_delete_activity_log(client, admin_token, test_collection, test_record):
    """Test that deleting a record creates an activity log entry with collection metadata."""
    from tinybase.activity import Actions
    from tinybase.db.core import get_db_engine
    from tinybase.db.models import ActivityLog

    record_id = test_record["id"]

    # Delete the record
    response = client.delete(
        f"/api/collections/test_collection/records/{record_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    # Check activity log
    engine = get_db_engine()
    with Session(engine) as session:
        activity = session.exec(
            select(ActivityLog)
            .where(ActivityLog.action == Actions.RECORD_DELETE)
            .where(ActivityLog.resource_id == record_id)
        ).first()

        assert activity is not None
        assert activity.action == Actions.RECORD_DELETE
        assert activity.resource_type == "record"
        assert activity.meta_data.get("collection") == "test_collection"
