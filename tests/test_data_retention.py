"""Tests for data retention functionality."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app import create_app, db
from app.models.monitor import Monitor, MonitorType, CheckInterval
from app.models.user import User
from app.models.check_result import CheckResult
from app.models.incident import Incident
from app.models.notification import NotificationLog
from app.services.data_retention import DataRetentionService


class TestDataRetentionService:
    """Test cases for DataRetentionService."""

    @pytest.fixture
    def app(self):
        """Create test application."""
        app = create_app("testing")
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()

    @pytest.fixture
    def admin_user(self, app):
        """Create admin user for testing."""
        user = User(username="admin", email="admin@test.com", is_admin=True)
        user.set_password("test123")
        db.session.add(user)
        db.session.commit()
        return user

    @pytest.fixture
    def test_monitor(self, app, admin_user):
        """Create test monitor."""
        monitor = Monitor(
            user_id=admin_user.id,
            name="Test Monitor",
            type=MonitorType.HTTP,
            target="https://example.com",
            check_interval=CheckInterval.ONE_MINUTE,
        )
        db.session.add(monitor)
        db.session.commit()
        return monitor

    @pytest.fixture
    def retention_service(self):
        """Create data retention service with short retention for testing."""
        return DataRetentionService(default_retention_days=30)

    def test_retention_policy_management(self, retention_service):
        """Test setting and getting retention policies."""
        # Test default policies
        assert retention_service.get_retention_policy("check_results") == 30
        assert retention_service.get_retention_policy("incidents") == 60  # 2x default

        # Test setting custom policy
        retention_service.set_retention_policy("check_results", 90)
        assert retention_service.get_retention_policy("check_results") == 90

        # Test invalid policy
        with pytest.raises(ValueError, match="Retention days must be at least 1"):
            retention_service.set_retention_policy("check_results", 0)

        # Test unknown policy returns default
        assert retention_service.get_retention_policy("unknown") == 30

    def test_cleanup_old_check_results(self, app, test_monitor, retention_service):
        """Test cleaning up old check results."""
        now = datetime.now(timezone.utc)

        # Create recent check results (should not be deleted)
        recent_result = CheckResult(
            monitor_id=test_monitor.id,
            status="up",
            timestamp=now - timedelta(days=10),
            response_time=100.0,
        )
        db.session.add(recent_result)

        # Create old check results (should be deleted)
        old_result = CheckResult(
            monitor_id=test_monitor.id,
            status="down",
            timestamp=now - timedelta(days=40),
            response_time=5000.0,
            error_message="Timeout",
        )
        db.session.add(old_result)
        db.session.commit()

        # Verify initial state
        assert CheckResult.query.count() == 2

        # Run cleanup
        deleted_count, info = retention_service.cleanup_old_check_results()

        # Verify cleanup results
        assert deleted_count == 1
        assert info["deleted_count"] == 1
        assert info["retention_days"] == 30
        assert info["total_before"] == 2
        assert info["total_after"] == 1

        # Verify database state
        assert CheckResult.query.count() == 1
        remaining = CheckResult.query.first()
        if remaining is not None:
            assert remaining.status == "up"  # Only recent result remains

    def test_cleanup_old_incidents(self, app, test_monitor, retention_service):
        """Test cleaning up old resolved incidents."""
        now = datetime.now(timezone.utc)

        # Create recent incident (should not be deleted)
        recent_incident = Incident(
            monitor_id=test_monitor.id,
            started_at=now - timedelta(days=5),
            resolved_at=now - timedelta(days=3),
            status="resolved",
        )
        db.session.add(recent_incident)

        # Create old resolved incident (should be deleted)
        old_resolved_incident = Incident(
            monitor_id=test_monitor.id,
            started_at=now - timedelta(days=80),
            resolved_at=now - timedelta(days=75),
            status="resolved",
        )
        db.session.add(old_resolved_incident)

        # Create active incident (should never be deleted)
        active_incident = Incident(
            monitor_id=test_monitor.id,
            started_at=now - timedelta(days=100),
            resolved_at=None,
            status="active",
        )
        db.session.add(active_incident)
        db.session.commit()

        # Verify initial state
        assert Incident.query.count() == 3

        # Run cleanup
        deleted_count, info = retention_service.cleanup_old_incidents()

        # Verify cleanup results
        assert deleted_count == 1
        assert info["deleted_count"] == 1
        assert info["note"] == "Only resolved incidents were cleaned up"

        # Verify database state
        assert Incident.query.count() == 2

        # Check that active and recent incidents remain
        remaining = Incident.query.order_by(Incident.started_at.asc()).all()
        assert len(remaining) == 2
        assert remaining[0].resolved_at is None  # Active remains
        assert remaining[1].resolved_at is not None  # Recent resolved remains

    def test_get_database_stats(self, app, test_monitor, retention_service):
        """Test database statistics collection."""
        now = datetime.now(timezone.utc)

        # Add some test data
        check_result = CheckResult(
            monitor_id=test_monitor.id, status="up", timestamp=now, response_time=100.0
        )
        db.session.add(check_result)

        incident = Incident(
            monitor_id=test_monitor.id,
            started_at=now - timedelta(days=1),
            resolved_at=None,
            status="active",
        )
        db.session.add(incident)
        db.session.commit()

        # Get stats
        stats = retention_service.get_database_stats()

        # Verify stats structure
        assert "check_results" in stats
        assert "incidents" in stats
        assert "notification_logs" in stats
        assert "retention_policies" in stats

        # Verify check results stats
        assert stats["check_results"]["total_count"] == 1
        assert stats["check_results"]["oldest_record"] is not None
        assert stats["check_results"]["newest_record"] is not None

        # Verify incidents stats
        assert stats["incidents"]["total_count"] == 1
        assert stats["incidents"]["active_count"] == 1

        # Verify retention policies
        assert stats["retention_policies"]["check_results"] == 30
        assert stats["retention_policies"]["incidents"] == 60

    def test_estimate_cleanup_impact(self, app, test_monitor, retention_service):
        """Test cleanup impact estimation."""
        now = datetime.now(timezone.utc)

        # Add old data that would be cleaned up
        old_check_result = CheckResult(
            monitor_id=test_monitor.id,
            status="down",
            timestamp=now - timedelta(days=40),
            error_message="Error",
        )
        db.session.add(old_check_result)
        db.session.commit()

        # Get estimate
        estimate = retention_service.estimate_cleanup_impact()

        # Verify estimate structure
        assert "estimated_deletions" in estimate
        assert "total_estimated_deletions" in estimate
        assert "generated_at" in estimate

        # Should estimate 1 check result deletion
        assert estimate["total_estimated_deletions"] == 1
        assert estimate["estimated_deletions"]["check_results"]["count"] == 1
        assert estimate["estimated_deletions"]["check_results"]["retention_days"] == 30

    def test_cleanup_all_old_data(self, app, test_monitor, retention_service):
        """Test full cleanup of all data types."""
        now = datetime.now(timezone.utc)

        # Add old data for all types
        old_check_result = CheckResult(
            monitor_id=test_monitor.id,
            status="down",
            timestamp=now - timedelta(days=40),
        )
        db.session.add(old_check_result)

        old_incident = Incident(
            monitor_id=test_monitor.id,
            started_at=now - timedelta(days=80),
            resolved_at=now - timedelta(days=75),
            status="resolved",
        )
        db.session.add(old_incident)

        old_notification_log = NotificationLog(
            monitor_id=test_monitor.id,
            channel_id=1,  # Mock channel
            event_type="test",
            title="Test",
            message="Test message",
            sent_successfully=True,
            sent_at=now - timedelta(days=100),  # Older than 90 day default
        )
        db.session.add(old_notification_log)
        db.session.commit()

        # Run full cleanup
        result = retention_service.cleanup_all_old_data()

        # Verify cleanup results
        assert result["success"] is True
        assert (
            result["total_deleted"] == 1
        )  # Only check result (others are too new or not deleted)
        assert "results" in result
        assert "started_at" in result
        assert "completed_at" in result

    def test_cleanup_with_custom_days(self, app, test_monitor, retention_service):
        """Test cleanup with custom retention days override."""
        now = datetime.now(timezone.utc)

        # Create moderately old data
        check_result = CheckResult(
            monitor_id=test_monitor.id,
            status="up",
            timestamp=now - timedelta(days=20),  # Newer than default 30 days
        )
        db.session.add(check_result)
        db.session.commit()

        # Should not delete with default policy
        deleted_count, _ = retention_service.cleanup_old_check_results()
        assert deleted_count == 0

        # Should delete with custom shorter policy
        deleted_count, info = retention_service.cleanup_old_check_results(
            days_to_keep=10
        )
        assert deleted_count == 1
        assert info["retention_days"] == 10

    def test_cleanup_error_handling(self, app, test_monitor, retention_service):
        """Test error handling during cleanup."""
        # Mock database operation to raise exception
        with patch.object(
            db.session, "commit", side_effect=Exception("Database error")
        ):
            with pytest.raises(Exception, match="Database error"):
                retention_service.cleanup_old_check_results()

    def test_empty_cleanup(self, retention_service):
        """Test cleanup when there's no data to delete."""
        deleted_count, info = retention_service.cleanup_old_check_results()

        assert deleted_count == 0
        assert info["deleted_count"] == 0
        assert info["total_before"] == 0
        assert info["total_after"] == 0
