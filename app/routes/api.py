from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.monitor import Monitor, MonitorType, CheckInterval
from app.models.check_result import CheckResult
from app.models.incident import Incident
from app.models.notification import (
    NotificationChannel,
    NotificationType,
    MonitorNotification,
    NotificationLog,
)
from app.notification.service import notification_service
from datetime import datetime, timedelta, timezone

bp = Blueprint("api", __name__)


@bp.route("/monitors", methods=["GET"])
@login_required
def get_monitors():
    """Get all monitors for current user"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status_filter = request.args.get("status", "")

    query = Monitor.query.filter_by(user_id=current_user.id)

    if status_filter:
        if status_filter == "up":
            query = query.filter(Monitor.last_status == "up")
        elif status_filter == "down":
            query = query.filter(Monitor.last_status == "down")
        elif status_filter == "unknown":
            query = query.filter(Monitor.last_status == "unknown")

    monitors = query.order_by(Monitor.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "monitors": [monitor.to_dict() for monitor in monitors.items],
            "pagination": {
                "page": monitors.page,
                "pages": monitors.pages,
                "per_page": monitors.per_page,
                "total": monitors.total,
                "has_next": monitors.has_next,
                "has_prev": monitors.has_prev,
            },
        }
    )


@bp.route("/monitors", methods=["POST"])
@login_required
def create_monitor():
    """Create a new monitor"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate required fields
    required_fields = ["name", "type", "target"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try:
        monitor = Monitor(
            user_id=current_user.id,
            name=data["name"],
            type=MonitorType(data["type"]),
            target=data["target"],
            port=data.get("port"),
            check_interval=CheckInterval(int(data.get("check_interval", 300))),
            timeout=data.get("timeout", 30),
            verify_ssl=data.get("verify_ssl", True),
            check_cert_expiration=data.get("check_cert_expiration", True),
            check_domain=data.get("check_domain", True),
            expected_domain=data.get("expected_domain"),
            response_time_threshold=data.get("response_time_threshold"),
            string_match=data.get("string_match"),
            expected_status_codes=data.get("expected_status_codes"),
            is_active=data.get("is_active", True),
        )

        db.session.add(monitor)
        db.session.commit()

        return jsonify(monitor.to_dict()), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to create monitor"}), 500


@bp.route("/monitors/<int:id>", methods=["GET"])
@login_required
def get_monitor(id):
    """Get specific monitor"""
    monitor = Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return jsonify(monitor.to_dict(include_recent_checks=True, include_incidents=True))


@bp.route("/monitors/<int:id>", methods=["PUT"])
@login_required
def update_monitor(id):
    """Update existing monitor"""
    monitor = Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Update allowed fields
        updatable_fields = [
            "name",
            "target",
            "port",
            "check_interval",
            "timeout",
            "verify_ssl",
            "check_cert_expiration",
            "check_domain",
            "expected_domain",
            "response_time_threshold",
            "string_match",
            "expected_status_codes",
            "is_active",
        ]

        for field in updatable_fields:
            if field in data:
                if field == "type":
                    monitor.type = MonitorType(data[field])
                elif field == "check_interval":
                    monitor.check_interval = CheckInterval(int(data[field]))
                else:
                    setattr(monitor, field, data[field])

        monitor.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify(monitor.to_dict())

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update monitor"}), 500


@bp.route("/monitors/<int:id>", methods=["DELETE"])
@login_required
def delete_monitor(id):
    """Delete a monitor"""
    monitor = Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    try:
        db.session.delete(monitor)
        db.session.commit()
        return jsonify({"message": "Monitor deleted successfully"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to delete monitor"}), 500


@bp.route("/monitors/<int:id>/check-results")
@login_required
def get_monitor_check_results(id):
    """Get check results for a specific monitor"""
    Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 100, type=int)
    hours = request.args.get("hours", 24, type=int)

    start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    check_results = (
        CheckResult.query.filter_by(monitor_id=id)
        .filter(CheckResult.timestamp >= start_time)
        .order_by(CheckResult.timestamp.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify(
        {
            "check_results": [result.to_dict() for result in check_results.items],
            "pagination": {
                "page": check_results.page,
                "pages": check_results.pages,
                "per_page": check_results.per_page,
                "total": check_results.total,
                "has_next": check_results.has_next,
                "has_prev": check_results.has_prev,
            },
        }
    )


@bp.route("/incidents")
@login_required
def get_incidents():
    """Get incidents for current user"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status = request.args.get("status", "")  # active, resolved, or empty for all

    query = Incident.query.join(Monitor).filter(Monitor.user_id == current_user.id)

    if status == "active":
        query = query.filter(Incident.resolved_at.is_(None))
    elif status == "resolved":
        query = query.filter(Incident.resolved_at.isnot(None))

    incidents = query.order_by(Incident.started_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "incidents": [incident.to_dict() for incident in incidents.items],
            "pagination": {
                "page": incidents.page,
                "pages": incidents.pages,
                "per_page": incidents.per_page,
                "total": incidents.total,
                "has_next": incidents.has_next,
                "has_prev": incidents.has_prev,
            },
        }
    )


@bp.route("/dashboard/overview")
@login_required
def dashboard_overview():
    """Get dashboard overview data"""
    from typing import Dict, Any

    monitors = Monitor.query.filter_by(user_id=current_user.id).all()

    overview: Dict[str, Any] = {
        "total_monitors": len(monitors),
        "active_monitors": sum(1 for m in monitors if m.is_active),
        "monitors_by_status": {
            "up": sum(1 for m in monitors if m.last_status == "up" and m.is_active),
            "down": sum(1 for m in monitors if m.last_status == "down" and m.is_active),
            "unknown": sum(
                1 for m in monitors if m.last_status == "unknown" and m.is_active
            ),
        },
        "monitors_by_type": {},
        "active_incidents": 0,
        "overall_uptime_7d": 0.0,
    }

    if monitors:
        # Count by type
        monitors_by_type: Dict[str, int] = {}
        for monitor in monitors:
            if monitor.is_active:
                type_name = monitor.type.value.upper()
                monitors_by_type[type_name] = monitors_by_type.get(type_name, 0) + 1
        overview["monitors_by_type"] = monitors_by_type

        # Calculate overall uptime
        active_monitors = [m for m in monitors if m.is_active]
        if active_monitors:
            total_uptime = sum(m.get_uptime_percentage(7) for m in active_monitors)
            overview["overall_uptime_7d"] = round(
                total_uptime / len(active_monitors), 2
            )

    # Count active incidents
    overview["active_incidents"] = (
        Incident.query.join(Monitor)
        .filter(Monitor.user_id == current_user.id, Incident.resolved_at.is_(None))
        .count()
    )

    return jsonify(overview)


# Notification Channel API endpoints
@bp.route("/notification-channels", methods=["GET"])
@login_required
def get_notification_channels():
    """Get all notification channels for current user"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    channel_type = request.args.get("type", "")

    query = NotificationChannel.query.filter_by(user_id=current_user.id)

    if channel_type:
        query = query.filter(NotificationChannel.type == NotificationType(channel_type))

    channels = query.order_by(NotificationChannel.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "channels": [channel.to_dict() for channel in channels.items],
            "pagination": {
                "page": channels.page,
                "pages": channels.pages,
                "per_page": channels.per_page,
                "total": channels.total,
                "has_next": channels.has_next,
                "has_prev": channels.has_prev,
            },
        }
    )


@bp.route("/notification-channels", methods=["POST"])
@login_required
def create_notification_channel():
    """Create a new notification channel"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate required fields
    required_fields = ["name", "type", "config"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try:
        channel = NotificationChannel(
            user_id=current_user.id,
            name=data["name"],
            type=NotificationType(data["type"]),
            config=data["config"],
            is_active=data.get("is_active", True),
        )

        db.session.add(channel)
        db.session.commit()

        return jsonify(channel.to_dict()), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to create notification channel"}), 500


@bp.route("/notification-channels/<int:channel_id>", methods=["GET"])
@login_required
def get_notification_channel(channel_id):
    """Get specific notification channel"""
    channel = NotificationChannel.query.filter_by(
        id=channel_id, user_id=current_user.id
    ).first_or_404()
    return jsonify(channel.to_dict())


@bp.route("/notification-channels/<int:channel_id>", methods=["PUT"])
@login_required
def update_notification_channel(channel_id):
    """Update existing notification channel"""
    channel = NotificationChannel.query.filter_by(
        id=channel_id, user_id=current_user.id
    ).first_or_404()
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Update allowed fields
        if "name" in data:
            channel.name = data["name"]
        if "config" in data:
            channel.config = data["config"]
        if "is_active" in data:
            channel.is_active = data["is_active"]

        db.session.commit()
        return jsonify(channel.to_dict())

    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update notification channel"}), 500


@bp.route("/notification-channels/<int:channel_id>", methods=["DELETE"])
@login_required
def delete_notification_channel(channel_id):
    """Delete a notification channel"""
    channel = NotificationChannel.query.filter_by(
        id=channel_id, user_id=current_user.id
    ).first_or_404()

    try:
        db.session.delete(channel)
        db.session.commit()
        return jsonify({"message": "Notification channel deleted successfully"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to delete notification channel"}), 500


@bp.route("/notification-channels/<int:channel_id>/test", methods=["POST"])
@login_required
def test_notification_channel(channel_id):
    """Test a notification channel"""
    NotificationChannel.query.filter_by(
        id=channel_id, user_id=current_user.id
    ).first_or_404()

    try:
        success, message = notification_service.test_notification_channel(channel_id)
        return jsonify({"success": success, "message": message})
    except Exception:
        return jsonify({"success": False, "message": "Test failed"}), 500


# Monitor Notification Settings API endpoints
@bp.route("/monitors/<int:monitor_id>/notifications", methods=["GET"])
@login_required
def get_monitor_notifications(monitor_id):
    """Get notification settings for a monitor"""
    Monitor.query.filter_by(id=monitor_id, user_id=current_user.id).first_or_404()

    monitor_notifications = (
        MonitorNotification.query.filter_by(monitor_id=monitor_id)
        .join(NotificationChannel)
        .filter(NotificationChannel.user_id == current_user.id)
        .all()
    )

    return jsonify([notification.to_dict() for notification in monitor_notifications])


@bp.route("/monitors/<int:monitor_id>/notifications", methods=["POST"])
@login_required
def create_monitor_notification(monitor_id):
    """Create notification settings for a monitor"""
    Monitor.query.filter_by(id=monitor_id, user_id=current_user.id).first_or_404()
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate required fields
    required_fields = ["channel_id"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Check if channel belongs to user
    NotificationChannel.query.filter_by(
        id=data["channel_id"], user_id=current_user.id
    ).first_or_404()

    # Check if already exists
    existing = MonitorNotification.query.filter_by(
        monitor_id=monitor_id, channel_id=data["channel_id"]
    ).first()
    if existing:
        return jsonify(
            {"error": "Notification settings already exist for this channel"}
        ), 400

    try:
        monitor_notification = MonitorNotification(
            monitor_id=monitor_id,
            channel_id=data["channel_id"],
            is_enabled=data.get("is_enabled", True),
            notify_on_down=data.get("notify_on_down", True),
            notify_on_up=data.get("notify_on_up", True),
            notify_on_ssl_warning=data.get("notify_on_ssl_warning", True),
            escalate_after_minutes=data.get("escalate_after_minutes"),
        )

        db.session.add(monitor_notification)
        db.session.commit()

        return jsonify(monitor_notification.to_dict()), 201

    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to create notification settings"}), 500


@bp.route(
    "/monitors/<int:monitor_id>/notifications/<int:notification_id>", methods=["PUT"]
)
@login_required
def update_monitor_notification(monitor_id, notification_id):
    """Update notification settings for a monitor"""
    Monitor.query.filter_by(id=monitor_id, user_id=current_user.id).first_or_404()

    monitor_notification = (
        MonitorNotification.query.filter_by(id=notification_id, monitor_id=monitor_id)
        .join(NotificationChannel)
        .filter(NotificationChannel.user_id == current_user.id)
        .first_or_404()
    )

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Update allowed fields
        if "is_enabled" in data:
            monitor_notification.is_enabled = data["is_enabled"]
        if "notify_on_down" in data:
            monitor_notification.notify_on_down = data["notify_on_down"]
        if "notify_on_up" in data:
            monitor_notification.notify_on_up = data["notify_on_up"]
        if "notify_on_ssl_warning" in data:
            monitor_notification.notify_on_ssl_warning = data["notify_on_ssl_warning"]
        if "escalate_after_minutes" in data:
            monitor_notification.escalate_after_minutes = data["escalate_after_minutes"]

        db.session.commit()
        return jsonify(monitor_notification.to_dict())

    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update notification settings"}), 500


@bp.route(
    "/monitors/<int:monitor_id>/notifications/<int:notification_id>", methods=["DELETE"]
)
@login_required
def delete_monitor_notification(monitor_id, notification_id):
    """Delete notification settings for a monitor"""
    Monitor.query.filter_by(id=monitor_id, user_id=current_user.id).first_or_404()

    monitor_notification = (
        MonitorNotification.query.filter_by(id=notification_id, monitor_id=monitor_id)
        .join(NotificationChannel)
        .filter(NotificationChannel.user_id == current_user.id)
        .first_or_404()
    )

    try:
        db.session.delete(monitor_notification)
        db.session.commit()
        return jsonify({"message": "Notification settings deleted successfully"})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to delete notification settings"}), 500


# Notification History API endpoints
@bp.route("/notification-history", methods=["GET"])
@login_required
def get_notification_history():
    """Get notification history for current user"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    monitor_id = request.args.get("monitor_id", type=int)
    channel_id = request.args.get("channel_id", type=int)
    event_type = request.args.get("event_type", "")

    # Build query
    query = (
        NotificationLog.query.join(Monitor)
        .filter(Monitor.user_id == current_user.id)
        .join(NotificationChannel)
        .filter(NotificationChannel.user_id == current_user.id)
    )

    # Apply filters
    if monitor_id:
        query = query.filter(NotificationLog.monitor_id == monitor_id)
    if channel_id:
        query = query.filter(NotificationLog.channel_id == channel_id)
    if event_type:
        query = query.filter(NotificationLog.event_type == event_type)

    # Order by most recent first and paginate
    notifications = query.order_by(NotificationLog.sent_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "notifications": [
                notification.to_dict() for notification in notifications.items
            ],
            "pagination": {
                "page": notifications.page,
                "pages": notifications.pages,
                "per_page": notifications.per_page,
                "total": notifications.total,
                "has_next": notifications.has_next,
                "has_prev": notifications.has_prev,
            },
        }
    )


@bp.route("/notification-stats", methods=["GET"])
@login_required
def get_notification_stats():
    """Get notification statistics for current user"""
    days = request.args.get("days", 7, type=int)
    return jsonify(notification_service.get_notification_stats(days))
