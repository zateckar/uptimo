from datetime import datetime, timedelta, timezone
from typing import Dict, Any

import json
import time
from flask import (
    Blueprint,
    render_template,
    jsonify,
    redirect,
    url_for,
    flash,
    Response,
    request,
    current_app,
)
from flask_login import login_required, current_user

from app import db
from app.models.monitor import Monitor, MonitorType, CheckInterval
from app.models.check_result import CheckResult
from app.models.incident import Incident
from app.models.notification import NotificationChannel
from app.forms.monitor import MonitorForm, MonitorEditForm
from app.forms.monitor_notification import MonitorNotificationForm
from app.schedulers.monitor_scheduler import monitor_scheduler

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    """Main dashboard with master/detail layout."""
    # Get all monitors for the current user
    monitors = (
        Monitor.query.filter_by(user_id=current_user.id).order_by(Monitor.name).all()
    )

    # Summary statistics
    total_monitors = len(monitors)
    active_monitors = sum(1 for m in monitors if m.is_active)
    up_monitors = sum(1 for m in monitors if m.is_up() and m.is_active)
    down_monitors = sum(1 for m in monitors if m.is_down() and m.is_active)

    # Get active incidents
    active_incidents = (
        Incident.query.join(Monitor)
        .filter(Monitor.user_id == current_user.id, Incident.resolved_at.is_(None))
        .order_by(Incident.started_at.desc())
        .all()
    )

    stats: Dict[str, Any] = {
        "total_monitors": total_monitors,
        "active_monitors": active_monitors,
        "up_monitors": up_monitors,
        "down_monitors": down_monitors,
        "active_incidents": len(active_incidents),
    }

    return render_template(
        "dashboard/index.html",
        monitors=monitors,
        stats=stats,
        active_incidents=active_incidents,
    )


@bp.route("/monitors")
@login_required
def monitors():
    """Get all monitors for current user with statistics for dashboard sidebar."""
    monitors = (
        Monitor.query.filter_by(user_id=current_user.id).order_by(Monitor.name).all()
    )

    # Calculate statistics
    total_monitors = len(monitors)
    up_monitors = sum(1 for m in monitors if m.is_up() and m.is_active)
    down_monitors = sum(1 for m in monitors if m.is_down() and m.is_active)

    stats = {
        "total": total_monitors,
        "up": up_monitors,
        "down": down_monitors,
    }

    return jsonify(
        {"monitors": [monitor.to_dict() for monitor in monitors], "stats": stats}
    )


@bp.route("/monitor/<int:id>")
@login_required
def monitor_detail(id: int):
    """AJAX endpoint for monitor detail view."""
    monitor = Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    # Get timespan parameter (default to 24h)
    timespan = request.args.get("timespan", "24h")

    # Convert timespan to hours
    timespan_hours = {
        "1h": 1,
        "6h": 6,
        "24h": 24,
        "7d": 24 * 7,
        "30d": 24 * 30,
    }.get(timespan, 24)

    # Get recent checks based on timespan for the chart
    recent_checks = monitor.get_checks_by_timespan(timespan_hours)

    # Get recent checks for heartbeat (last 50)
    heartbeat_checks = monitor.get_recent_checks(50)

    # Get incidents
    incidents = monitor.incidents.order_by(Incident.started_at.desc()).limit(10).all()

    # Get latest check with additional data for SSL/Domain info
    # This ensures we have the info even if it's not in the recent_checks list (e.g. due to timespan)
    latest_check_with_data = (
        CheckResult.query.filter_by(monitor_id=id)
        .filter(CheckResult.additional_data.isnot(None))
        .order_by(CheckResult.timestamp.desc())
        .first()
    )

    ssl_info = None
    domain_info = None
    dns_info = None

    if latest_check_with_data:
        data = latest_check_with_data.get_additional_data()
        ssl_info = data.get("ssl_info")
        domain_info = data.get("domain_info")
        dns_info = data.get("dns_info")

    # Render action buttons HTML
    action_buttons_html = render_template(
        "dashboard/_monitor_actions.html", monitor=monitor
    )

    return jsonify(
        {
            "monitor": monitor.to_dict(
                include_recent_checks=False, include_incidents=True
            ),
            "recent_checks": [check.to_dict() for check in recent_checks],
            "heartbeat_checks": [check.to_dict() for check in heartbeat_checks],
            "incidents": [incident.to_dict() for incident in incidents],
            "ssl_info": ssl_info,
            "domain_info": domain_info,
            "dns_info": dns_info,
            "action_buttons_html": action_buttons_html,
        }
    )


@bp.route("/monitor/<int:id>/heartbeat")
@login_required
def monitor_heartbeat(id: int):
    """Get heartbeat data for a specific monitor."""
    monitor = Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    # Get recent checks for heartbeat (last 50)
    recent_checks = monitor.get_recent_checks(50)

    return jsonify({"checks": [check.to_dict() for check in recent_checks]})


@bp.route("/monitor/<int:id>/checks")
@login_required
def monitor_checks(id: int):
    """Get check data for a specific monitor with timespan filtering."""
    monitor = Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    # Get timespan parameter (default to 24h)
    timespan = request.args.get("timespan", "24h")

    # Convert timespan to hours
    timespan_hours = {
        "1h": 1,
        "6h": 6,
        "24h": 24,
        "7d": 24 * 7,
        "30d": 24 * 30,
    }.get(timespan, 24)

    # Get recent checks based on timespan
    filtered_checks = monitor.get_checks_by_timespan(timespan_hours)

    return jsonify({"checks": [check.to_dict() for check in filtered_checks]})


@bp.route("/overview-stats")
@login_required
def overview_stats():
    """AJAX endpoint for dashboard overview statistics."""
    monitors = Monitor.query.filter_by(user_id=current_user.id, is_active=True).all()

    stats: Dict[str, Any] = {
        "monitors_by_type": {},
        "overall_uptime": 0,
        "total_checks_today": 0,
        "recent_incidents_24h": 0,
    }

    if monitors:
        # Count monitors by type
        for monitor in monitors:
            type_name = monitor.type.value.upper()
            if type_name not in stats["monitors_by_type"]:
                stats["monitors_by_type"][type_name] = 0
            stats["monitors_by_type"][type_name] += 1

        # Calculate overall uptime
        total_uptime = sum(monitor.get_uptime_percentage(7) for monitor in monitors)
        stats["overall_uptime"] = round(total_uptime / len(monitors), 2)

        # Count recent incidents
        yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
        stats["recent_incidents_24h"] = (
            Incident.query.join(Monitor)
            .filter(
                Monitor.user_id == current_user.id, Incident.started_at >= yesterday
            )
            .count()
        )

    return jsonify(stats)


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new monitor."""
    form = MonitorForm()

    if form.validate_on_submit():
        # Convert form data to monitor object
        monitor = Monitor(
            user_id=current_user.id,
            name=form.name.data or "",
            type=MonitorType(form.type.data),
            target=form.target.data or "",
            port=form.port.data,
            check_interval=CheckInterval(int(form.check_interval.data)),
            timeout=form.timeout.data or 30,
            expected_status_codes=str(form.get_status_codes_list())
            if form.get_status_codes_list()
            else None,
            response_time_threshold=form.response_time_threshold.data,
            string_match=form.string_match.data,
            string_match_type=form.string_match_type.data,
            json_path_match=form.json_path_match.data,
            verify_ssl=form.verify_ssl.data,
            check_cert_expiration=form.check_cert_expiration.data,
            cert_expiration_threshold=form.cert_expiration_threshold.data or 30,
            check_domain=form.check_domain.data,
            expected_domain=form.expected_domain.data,
            kafka_security_protocol=form.kafka_security_protocol.data,
            kafka_sasl_mechanism=form.kafka_sasl_mechanism.data,
            kafka_sasl_username=form.kafka_sasl_username.data,
            kafka_sasl_password=form.kafka_sasl_password.data,
            kafka_oauth_token_url=form.kafka_oauth_token_url.data,
            kafka_oauth_client_id=form.kafka_oauth_client_id.data,
            kafka_oauth_client_secret=form.kafka_oauth_client_secret.data,
            kafka_ssl_ca_cert=form.kafka_ssl_ca_cert.data,
            kafka_ssl_client_cert=form.kafka_ssl_client_cert.data,
            kafka_ssl_client_key=form.kafka_ssl_client_key.data,
            kafka_topic=form.kafka_topic.data,
            kafka_consumer_group=form.kafka_consumer_group.data,
            kafka_read_message=form.kafka_read_message.data,
            kafka_write_message=form.kafka_write_message.data,
            kafka_message_payload=form.kafka_message_payload.data,
            kafka_autocommit=form.kafka_autocommit.data,
            is_active=form.is_active.data,
        )

        db.session.add(monitor)
        db.session.commit()

        # Schedule the monitor if it's active
        if monitor.is_active:
            monitor_scheduler.schedule_monitor(monitor)

        flash(f'Monitor "{monitor.name}" has been created successfully!', "success")
        return redirect(url_for("dashboard.index"))

    return render_template("dashboard/create.html", form=form)


@bp.route("/create/http", methods=["GET", "POST"])
@login_required
def create_http():
    """Create a new HTTP/HTTPS monitor."""
    form = MonitorForm()
    # Pre-set monitor type to http and default status codes
    if request.method == "GET":
        form.type.data = "http"
        form.expected_status_codes.data = "200"

    if form.validate_on_submit():
        try:
            monitor = Monitor(
                user_id=current_user.id,
                name=form.name.data or "",
                type=MonitorType(form.type.data),
                target=form.target.data or "",
                port=form.port.data,
                check_interval=CheckInterval(int(form.check_interval.data)),
                timeout=form.timeout.data or 30,
                expected_status_codes=(
                    str(form.get_status_codes_list())
                    if form.get_status_codes_list()
                    else None
                ),
                response_time_threshold=form.response_time_threshold.data,
                string_match=form.string_match.data,
                string_match_type=form.string_match_type.data,
                json_path_match=form.json_path_match.data,
                verify_ssl=form.verify_ssl.data,
                check_cert_expiration=form.check_cert_expiration.data,
                cert_expiration_threshold=form.cert_expiration_threshold.data or 30,
                check_domain=form.check_domain.data,
                expected_domain=form.expected_domain.data,
                is_active=form.is_active.data,
            )
            db.session.add(monitor)
            db.session.commit()

            if monitor.is_active:
                monitor_scheduler.schedule_monitor(monitor)

            flash(f'Monitor "{monitor.name}" has been created successfully!', "success")
            return redirect(url_for("dashboard.index"))
        except Exception as e:
            db.session.rollback()
            flash(f"Failed to create monitor: {str(e)}", "error")
            return render_template("dashboard/form_http.html", form=form, monitor=None)
    elif request.method == "POST":
        # Form validation failed - flash errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")

    return render_template("dashboard/form_http.html", form=form, monitor=None)


@bp.route("/create/kafka", methods=["GET", "POST"])
@login_required
def create_kafka():
    """Create a new Kafka monitor."""
    form = MonitorForm()
    # Pre-set monitor type to kafka
    if request.method == "GET":
        form.type.data = "kafka"

    if form.validate_on_submit():
        try:
            monitor = Monitor(
                user_id=current_user.id,
                name=form.name.data or "",
                type=MonitorType(form.type.data),
                target=form.target.data or "",
                port=form.port.data,
                check_interval=CheckInterval(int(form.check_interval.data)),
                timeout=form.timeout.data or 30,
                response_time_threshold=form.response_time_threshold.data,
                verify_ssl=form.verify_ssl.data,
                check_cert_expiration=form.check_cert_expiration.data,
                cert_expiration_threshold=form.cert_expiration_threshold.data or 30,
                check_domain=form.check_domain.data,
                expected_domain=form.expected_domain.data,
                kafka_security_protocol=form.kafka_security_protocol.data,
                kafka_sasl_mechanism=form.kafka_sasl_mechanism.data,
                kafka_sasl_username=form.kafka_sasl_username.data,
                kafka_sasl_password=form.kafka_sasl_password.data,
                kafka_oauth_token_url=form.kafka_oauth_token_url.data,
                kafka_oauth_client_id=form.kafka_oauth_client_id.data,
                kafka_oauth_client_secret=form.kafka_oauth_client_secret.data,
                kafka_ssl_ca_cert=form.kafka_ssl_ca_cert.data,
                kafka_ssl_client_cert=form.kafka_ssl_client_cert.data,
                kafka_ssl_client_key=form.kafka_ssl_client_key.data,
                kafka_topic=form.kafka_topic.data,
                kafka_consumer_group=form.kafka_consumer_group.data,
                kafka_read_message=form.kafka_read_message.data,
                kafka_write_message=form.kafka_write_message.data,
                kafka_message_payload=form.kafka_message_payload.data,
                kafka_autocommit=form.kafka_autocommit.data,
                is_active=form.is_active.data,
            )
            db.session.add(monitor)
            db.session.commit()

            if monitor.is_active:
                monitor_scheduler.schedule_monitor(monitor)

            flash(f'Monitor "{monitor.name}" has been created successfully!', "success")
            return redirect(url_for("dashboard.index"))
        except Exception as e:
            db.session.rollback()
            flash(f"Failed to create monitor: {str(e)}", "error")
            return render_template("dashboard/form_kafka.html", form=form, monitor=None)
    elif request.method == "POST":
        # Form validation failed - flash errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")

    return render_template("dashboard/form_kafka.html", form=form, monitor=None)


@bp.route("/create/tcp", methods=["GET", "POST"])
@login_required
def create_tcp():
    """Create a new TCP monitor."""
    form = MonitorForm()
    # Pre-set monitor type to tcp
    if request.method == "GET":
        form.type.data = "tcp"

    if form.validate_on_submit():
        try:
            monitor = Monitor(
                user_id=current_user.id,
                name=form.name.data or "",
                type=MonitorType(form.type.data),
                target=form.target.data or "",
                port=form.port.data,
                check_interval=CheckInterval(int(form.check_interval.data)),
                timeout=form.timeout.data or 30,
                response_time_threshold=form.response_time_threshold.data,
                check_domain=form.check_domain.data,
                expected_domain=form.expected_domain.data,
                is_active=form.is_active.data,
            )
            db.session.add(monitor)
            db.session.commit()

            if monitor.is_active:
                monitor_scheduler.schedule_monitor(monitor)

            flash(f'Monitor "{monitor.name}" has been created successfully!', "success")
            return redirect(url_for("dashboard.index"))
        except Exception as e:
            db.session.rollback()
            flash(f"Failed to create monitor: {str(e)}", "error")
            return render_template("dashboard/form_tcp.html", form=form, monitor=None)
    elif request.method == "POST":
        # Form validation failed - flash errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")

    return render_template("dashboard/form_tcp.html", form=form, monitor=None)


@bp.route("/create/ping", methods=["GET", "POST"])
@login_required
def create_ping():
    """Create a new Ping monitor."""
    form = MonitorForm()
    # Pre-set monitor type to ping
    if request.method == "GET":
        form.type.data = "ping"

    if form.validate_on_submit():
        try:
            monitor = Monitor(
                user_id=current_user.id,
                name=form.name.data or "",
                type=MonitorType(form.type.data),
                target=form.target.data or "",
                port=form.port.data,
                check_interval=CheckInterval(int(form.check_interval.data)),
                timeout=form.timeout.data or 30,
                response_time_threshold=form.response_time_threshold.data,
                check_domain=form.check_domain.data,
                expected_domain=form.expected_domain.data,
                is_active=form.is_active.data,
            )
            db.session.add(monitor)
            db.session.commit()

            if monitor.is_active:
                monitor_scheduler.schedule_monitor(monitor)

            flash(f'Monitor "{monitor.name}" has been created successfully!', "success")
            return redirect(url_for("dashboard.index"))
        except Exception as e:
            db.session.rollback()
            flash(f"Failed to create monitor: {str(e)}", "error")
            return render_template("dashboard/form_ping.html", form=form, monitor=None)
    elif request.method == "POST":
        # Form validation failed - flash errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")

    return render_template("dashboard/form_ping.html", form=form, monitor=None)


@bp.route("/monitor/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id: int):
    """Edit an existing monitor."""
    monitor = Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = MonitorEditForm(obj=monitor)
    notification_form = MonitorNotificationForm(monitor=monitor, user=current_user)

    # Handle notification form submission
    if request.method == "POST" and request.form.get("form_type") == "notifications":
        # Update notification form data from request
        notification_form.channel_ids.data = request.form.getlist("channel_ids")
        notification_form.notify_on_down.data = "notify_on_down" in request.form
        notification_form.notify_on_up.data = "notify_on_up" in request.form
        notification_form.notify_on_ssl_warning.data = (
            "notify_on_ssl_warning" in request.form
        )
        notification_form.consecutive_checks_threshold.data = request.form.get(
            "consecutive_checks_threshold", type=int, default=1
        )
        notification_form.escalate_after_minutes.data = request.form.get(
            "escalate_after_minutes", type=int
        )

        # Validate and save notification settings
        is_valid, errors = notification_form.validate()
        if is_valid:
            try:
                success, message = notification_form.save_settings(monitor)
                if success:
                    flash(message, "success")
                else:
                    flash(message, "error")
            except Exception:
                db.session.rollback()
                flash("Failed to update notification settings.", "error")
        else:
            for error in errors:
                flash(error, "error")

        return redirect(url_for("dashboard.edit", id=id))

    # Handle monitor form submission
    if form.validate_on_submit() and request.form.get("form_type") != "notifications":
        try:
            # Update monitor with form data
            monitor.name = form.name.data or ""
            monitor.type = MonitorType(form.type.data)
            monitor.target = form.target.data or ""
            monitor.port = form.port.data
            monitor.check_interval = CheckInterval(int(form.check_interval.data))
            monitor.timeout = form.timeout.data or 30
            monitor.expected_status_codes = (
                str(form.get_status_codes_list())
                if form.get_status_codes_list()
                else None
            )
            monitor.response_time_threshold = form.response_time_threshold.data
            monitor.string_match = form.string_match.data
            monitor.string_match_type = form.string_match_type.data
            monitor.json_path_match = form.json_path_match.data
            monitor.verify_ssl = form.verify_ssl.data
            monitor.check_cert_expiration = form.check_cert_expiration.data
            monitor.cert_expiration_threshold = (
                form.cert_expiration_threshold.data or 30
            )
            monitor.check_domain = form.check_domain.data
            monitor.expected_domain = form.expected_domain.data
            monitor.kafka_security_protocol = form.kafka_security_protocol.data
            monitor.kafka_sasl_mechanism = form.kafka_sasl_mechanism.data
            monitor.kafka_sasl_username = form.kafka_sasl_username.data
            monitor.kafka_sasl_password = form.kafka_sasl_password.data
            monitor.kafka_oauth_token_url = form.kafka_oauth_token_url.data
            monitor.kafka_oauth_client_id = form.kafka_oauth_client_id.data
            monitor.kafka_oauth_client_secret = form.kafka_oauth_client_secret.data
            monitor.kafka_ssl_ca_cert = form.kafka_ssl_ca_cert.data
            monitor.kafka_ssl_client_cert = form.kafka_ssl_client_cert.data
            monitor.kafka_ssl_client_key = form.kafka_ssl_client_key.data
            monitor.kafka_topic = form.kafka_topic.data
            monitor.kafka_consumer_group = form.kafka_consumer_group.data
            monitor.kafka_read_message = form.kafka_read_message.data
            monitor.kafka_write_message = form.kafka_write_message.data
            monitor.kafka_message_payload = form.kafka_message_payload.data
            monitor.kafka_autocommit = form.kafka_autocommit.data
            monitor.is_active = form.is_active.data

            db.session.commit()

            # Reschedule the monitor with updated settings
            if monitor.is_active:
                monitor_scheduler.schedule_monitor(monitor)
            else:
                # Unschedule if monitor was deactivated
                monitor_scheduler.unschedule_monitor(monitor.id)

            flash(f'Monitor "{monitor.name}" has been updated successfully!', "success")
            return redirect(url_for("dashboard.index"))
        except Exception as e:
            db.session.rollback()
            flash(f"Failed to update monitor: {str(e)}", "error")
    elif request.method == "POST" and request.form.get("form_type") != "notifications":
        # Form validation failed - flash errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")

    # Get available notification channels for the form
    available_channels = (
        NotificationChannel.query.filter_by(user_id=current_user.id, is_active=True)
        .order_by(NotificationChannel.name)
        .all()
    )

    # Determine which template to use based on monitor type
    template_map = {
        "http": "dashboard/form_http.html",
        "https": "dashboard/form_http.html",
        "kafka": "dashboard/form_kafka.html",
        "tcp": "dashboard/form_tcp.html",
        "ping": "dashboard/form_ping.html",
    }
    template = template_map.get(monitor.type.value, "dashboard/edit.html")

    return render_template(
        template,
        form=form,
        notification_form=notification_form,
        monitor=monitor,
        available_channels=available_channels,
    )


@bp.route("/monitor/<int:id>/delete", methods=["POST"])
@login_required
def delete(id: int):
    """Delete a monitor."""
    monitor = Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    # Unschedule the monitor before deletion
    monitor_scheduler.unschedule_monitor(monitor.id)

    db.session.delete(monitor)
    db.session.commit()
    flash(f'Monitor "{monitor.name}" has been deleted.', "success")
    return redirect(url_for("dashboard.index"))


@bp.route("/monitor/<int:id>/clone", methods=["POST"])
@login_required
def clone(id: int):
    """Clone a monitor with all its settings."""
    monitor = Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    # Create new monitor with same settings but new ID
    cloned_monitor = Monitor(
        user_id=current_user.id,
        name=f"{monitor.name} (Copy)",
        type=monitor.type,
        target=monitor.target,
        port=monitor.port,
        check_interval=monitor.check_interval,
        timeout=monitor.timeout,
        expected_status_codes=monitor.expected_status_codes,
        response_time_threshold=monitor.response_time_threshold,
        string_match=monitor.string_match,
        string_match_type=monitor.string_match_type,
        json_path_match=monitor.json_path_match,
        http_method=monitor.http_method,
        http_headers=monitor.http_headers,
        http_body=monitor.http_body,
        verify_ssl=monitor.verify_ssl,
        check_cert_expiration=monitor.check_cert_expiration,
        cert_expiration_threshold=monitor.cert_expiration_threshold,
        http_ssl_ca_cert=monitor.http_ssl_ca_cert,
        http_ssl_client_cert=monitor.http_ssl_client_cert,
        http_ssl_client_key=monitor.http_ssl_client_key,
        check_domain=monitor.check_domain,
        expected_domain=monitor.expected_domain,
        kafka_security_protocol=monitor.kafka_security_protocol,
        kafka_sasl_mechanism=monitor.kafka_sasl_mechanism,
        kafka_sasl_username=monitor.kafka_sasl_username,
        kafka_sasl_password=monitor.kafka_sasl_password,
        kafka_oauth_token_url=monitor.kafka_oauth_token_url,
        kafka_oauth_client_id=monitor.kafka_oauth_client_id,
        kafka_oauth_client_secret=monitor.kafka_oauth_client_secret,
        kafka_ssl_ca_cert=monitor.kafka_ssl_ca_cert,
        kafka_ssl_client_cert=monitor.kafka_ssl_client_cert,
        kafka_ssl_client_key=monitor.kafka_ssl_client_key,
        kafka_topic=monitor.kafka_topic,
        kafka_consumer_group=monitor.kafka_consumer_group,
        kafka_read_message=monitor.kafka_read_message,
        kafka_write_message=monitor.kafka_write_message,
        kafka_message_payload=monitor.kafka_message_payload,
        kafka_autocommit=monitor.kafka_autocommit,
        is_active=False,  # Start as inactive to avoid immediate checks
    )

    db.session.add(cloned_monitor)
    db.session.commit()

    flash(
        f'Monitor "{monitor.name}" has been cloned as "{cloned_monitor.name}".',
        "success",
    )
    return redirect(url_for("dashboard.edit", id=cloned_monitor.id))


@bp.route("/monitor/<int:id>/toggle", methods=["POST"])
@login_required
def toggle(id: int):
    """Toggle monitor active status."""
    monitor = Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    monitor.is_active = not monitor.is_active
    db.session.commit()

    # Schedule or unschedule based on new status
    if monitor.is_active:
        monitor_scheduler.schedule_monitor(monitor)
    else:
        monitor_scheduler.unschedule_monitor(monitor.id)

    status = "activated" if monitor.is_active else "deactivated"
    flash(f'Monitor "{monitor.name}" has been {status}.', "success")
    return redirect(url_for("dashboard.index"))


@bp.route("/monitor/<int:id>/check-now", methods=["POST"])
@login_required
def check_now(id: int):
    """Trigger immediate check for monitor."""
    monitor = Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    # Run immediate check
    success = monitor_scheduler.run_check_now(monitor.id)

    if success:
        flash(f'Monitor "{monitor.name}" check triggered successfully.', "success")
    else:
        flash(f'Failed to trigger check for monitor "{monitor.name}".', "error")

    return redirect(url_for("dashboard.index"))


@bp.route("/stream")
@login_required
def stream():
    """SSE endpoint for real-time monitor updates."""
    # Capture user ID and app object outside the generator function
    # to ensure they're available in the separate thread context
    user_id = current_user.id
    from flask import current_app as app_context
    app = app_context._get_current_object()  # type: ignore

    def generate():
        # Store the last known meaningful state to avoid sending duplicate data
        # We separate volatile data (timestamps) from meaningful data
        last_meaningful_state: Dict[str, Any] = {}

        try:
            # Send initial connection message
            initial_data = {
                "status": "connected",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"data: {json.dumps(initial_data)}\n\n"

            # Initial state send
            with app.app_context():
                # Get monitors for current user
                monitors = Monitor.query.filter_by(user_id=user_id).all()

                # Create meaningful state (excluding volatile timestamps)
                meaningful_state: Dict[str, Any] = {
                    "monitors": {},
                    "stats": {},
                }

                # Update monitor states (include recent_checks for heartbeat visualization)
                for monitor in monitors:
                    monitor_data = monitor.to_dict(include_recent_checks=False)
                    # Always include recent_checks for heartbeat visualization
                    # Get actual recent checks - don't create fake data
                    recent_checks = [
                        {
                            "timestamp": check.timestamp.isoformat(),
                            "status": check.status,
                            "response_time": check.response_time,
                        }
                        for check in monitor.get_recent_checks(25)
                    ]
                    monitor_data["recent_checks"] = recent_checks

                    meaningful_state["monitors"][str(monitor.id)] = monitor_data

                # Update stats
                total_monitors = len(monitors)
                active_monitors = sum(1 for m in monitors if m.is_active)
                up_monitors = sum(1 for m in monitors if m.is_up() and m.is_active)
                down_monitors = sum(1 for m in monitors if m.is_down() and m.is_active)

                meaningful_state["stats"] = {
                    "total_monitors": total_monitors,
                    "active_monitors": active_monitors,
                    "up_monitors": up_monitors,
                    "down_monitors": down_monitors,
                    "active_incidents": (
                        Incident.query.join(Monitor)
                        .filter(
                            Monitor.user_id == user_id,
                            Incident.resolved_at.is_(None),
                        )
                        .count()
                    ),
                }

                # Create full response with current timestamp
                current_state: Dict[str, Any] = {
                    **meaningful_state,
                    "last_update": datetime.now(timezone.utc).isoformat(),
                }

                # Send initial state
                yield f"data: {json.dumps(current_state)}\n\n"
                last_meaningful_state = meaningful_state.copy()

            # Main loop with periodic updates
            while True:
                try:
                    with app.app_context():
                        # Get monitors for current user
                        monitors = Monitor.query.filter_by(user_id=user_id).all()

                        # Create meaningful state (excluding volatile timestamps)
                        meaningful_state: Dict[str, Any] = {
                            "monitors": {},
                            "stats": {},
                        }

                        # Update monitor states
                        for monitor in monitors:
                            monitor_data = monitor.to_dict(include_recent_checks=False)
                            # Always include recent_checks for heartbeat visualization
                            # Get actual recent checks - don't create fake data
                            recent_checks = [
                                {
                                    "timestamp": check.timestamp.isoformat(),
                                    "status": check.status,
                                    "response_time": check.response_time,
                                }
                                for check in monitor.get_recent_checks(25)
                            ]
                            monitor_data["recent_checks"] = recent_checks
                            meaningful_state["monitors"][str(monitor.id)] = monitor_data

                        # Update stats
                        total_monitors = len(monitors)
                        active_monitors = sum(1 for m in monitors if m.is_active)
                        up_monitors = sum(
                            1 for m in monitors if m.is_up() and m.is_active
                        )
                        down_monitors = sum(
                            1 for m in monitors if m.is_down() and m.is_active
                        )

                        meaningful_state["stats"] = {
                            "total_monitors": total_monitors,
                            "active_monitors": active_monitors,
                            "up_monitors": up_monitors,
                            "down_monitors": down_monitors,
                            "active_incidents": (
                                Incident.query.join(Monitor)
                                .filter(
                                    Monitor.user_id == user_id,
                                    Incident.resolved_at.is_(None),
                                )
                                .count()
                            ),
                        }

                        # Only send update if meaningful state has changed
                        if meaningful_state != last_meaningful_state:
                            # Create full response with current timestamp
                            current_state: Dict[str, Any] = {
                                **meaningful_state,
                                "last_update": datetime.now(timezone.utc).isoformat(),
                            }
                            yield f"data: {json.dumps(current_state)}\n\n"
                            last_meaningful_state = meaningful_state.copy()

                    # Wait before next check
                    time.sleep(5)  # Check every 5 seconds

                except GeneratorExit:
                    # Client disconnected
                    break
                except Exception as e:
                    # Log error and continue
                    print(f"SSE Error: {e}")
                    yield f"data: {json.dumps({'error': 'SSE stream error'})}\n\n"
                    time.sleep(10)  # Wait longer on error

        except GeneratorExit:
            print(f"SSE: Client {user_id} disconnected")
        except Exception as e:
            print(f"SSE Error for user {user_id}: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
            "Access-Control-Allow-Credentials": "true",
            "X-Accel-Buffering": "no",  # Disable buffering for nginx
        },
    )


@bp.route("/monitor/<int:id>/stream")
@login_required
def monitor_stream(id: int):
    """SSE endpoint for specific monitor updates."""
    # Capture user ID, monitor ID and app object outside the generator function
    # to ensure they're available in the separate thread context
    user_id = current_user.id
    monitor_id = id
    from flask import current_app as app_context
    app = app_context._get_current_object()  # type: ignore

    # Get timespan parameter (default to 24h)
    timespan = request.args.get("timespan", "24h")

    # Convert timespan to hours
    timespan_hours = {
        "1h": 1,
        "6h": 6,
        "24h": 24,
        "7d": 24 * 7,
        "30d": 24 * 30,
    }.get(timespan, 24)

    # Verify monitor exists before starting stream
    Monitor.query.filter_by(id=monitor_id, user_id=user_id).first_or_404()

    def generate():
        # Store last known state for meaningful comparison
        # We separate volatile data (timestamps) from meaningful data
        last_meaningful_state: Dict[str, Any] = {}
        last_heartbeat_hash: str = ""

        try:
            # Send initial connection message
            initial_data = {
                "status": "connected",
                "monitor_id": monitor_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"data: {json.dumps(initial_data)}\n\n"

            # Initial state send
            with app.app_context():
                # Query monitor fresh
                monitor = Monitor.query.filter_by(
                    id=monitor_id, user_id=user_id
                ).first()

                if monitor:
                    # Get recent checks for heartbeat (always show last 50, no timespan filter)
                    recent_checks_heartbeat = monitor.get_recent_checks(50)

                    # Get recent checks and filter by timespan for charts
                    filtered_checks = monitor.get_checks_by_timespan(timespan_hours)

                    # Get latest check with additional data for SSL/Domain info
                    latest_check_with_data = (
                        CheckResult.query.filter_by(monitor_id=monitor_id)
                        .filter(CheckResult.additional_data.isnot(None))
                        .order_by(CheckResult.timestamp.desc())
                        .first()
                    )

                    ssl_info = None
                    domain_info = None
                    dns_info = None

                    if latest_check_with_data:
                        data = latest_check_with_data.get_additional_data()
                        ssl_info = data.get("ssl_info")
                        domain_info = data.get("domain_info")
                        dns_info = data.get("dns_info")

                    # Get incidents
                    incidents = (
                        monitor.incidents.order_by(Incident.started_at.desc())
                        .limit(10)
                        .all()
                    )

                    # Create stable hash for heartbeat data to detect meaningful changes
                    heartbeat_data = [
                        {
                            "timestamp": check.timestamp.isoformat(),
                            "status": check.status,
                            "response_time": check.response_time,
                        }
                        for check in recent_checks_heartbeat
                    ]
                    current_heartbeat_hash = str(
                        hash(json.dumps(heartbeat_data, sort_keys=True))
                    )

                    # Create meaningful state (excluding volatile timestamps)
                    meaningful_state: Dict[str, Any] = {
                        "monitor": monitor.to_dict(include_recent_checks=False),
                        "recent_checks": [
                            {
                                "timestamp": check.timestamp.isoformat(),
                                "status": check.status,
                                "response_time": check.response_time,
                            }
                            for check in filtered_checks
                        ],
                        "heartbeat_checks": heartbeat_data,
                        "incidents": [incident.to_dict() for incident in incidents],
                        "ssl_info": ssl_info,
                        "domain_info": domain_info,
                        "dns_info": dns_info,
                    }

                    # Create full response with current timestamp
                    current_state: Dict[str, Any] = {
                        **meaningful_state,
                        "last_update": datetime.now(timezone.utc).isoformat(),
                    }

                    # Send initial state
                    yield f"data: {json.dumps(current_state)}\n\n"
                    last_meaningful_state = meaningful_state.copy()
                    last_heartbeat_hash = current_heartbeat_hash

            # Main loop
            heartbeat_counter = 0
            while True:
                try:
                    with app.app_context():
                        # Query monitor fresh in each iteration
                        monitor = Monitor.query.filter_by(
                            id=monitor_id, user_id=user_id
                        ).first()

                        if not monitor:
                            # Monitor was deleted, send deletion message and close the stream
                            yield f"data: {json.dumps({'monitor_deleted': True, 'monitor_id': monitor_id})}\n\n"
                            break

                        # Get recent checks for heartbeat (always show last 50, no timespan filter)
                        recent_checks_heartbeat = monitor.get_recent_checks(50)

                        # Get recent checks and filter by timespan for charts
                        filtered_checks = monitor.get_checks_by_timespan(timespan_hours)

                        # Get latest check with additional data for SSL/Domain info
                        latest_check_with_data = (
                            CheckResult.query.filter_by(monitor_id=monitor_id)
                            .filter(CheckResult.additional_data.isnot(None))
                            .order_by(CheckResult.timestamp.desc())
                            .first()
                        )

                        ssl_info = None
                        domain_info = None
                        dns_info = None

                        if latest_check_with_data:
                            data = latest_check_with_data.get_additional_data()
                            ssl_info = data.get("ssl_info")
                            domain_info = data.get("domain_info")
                            dns_info = data.get("dns_info")

                        # Get incidents
                        incidents = (
                            monitor.incidents.order_by(Incident.started_at.desc())
                            .limit(10)
                            .all()
                        )

                        # Create stable hash for heartbeat data to detect meaningful changes
                        heartbeat_data = [
                            {
                                "timestamp": check.timestamp.isoformat(),
                                "status": check.status,
                                "response_time": check.response_time,
                            }
                            for check in recent_checks_heartbeat
                        ]
                        current_heartbeat_hash = str(
                            hash(json.dumps(heartbeat_data, sort_keys=True))
                        )

                        # Create meaningful state (excluding volatile timestamps)
                        meaningful_state: Dict[str, Any] = {
                            "monitor": monitor.to_dict(include_recent_checks=False),
                            "recent_checks": [
                                {
                                    "timestamp": check.timestamp.isoformat(),
                                    "status": check.status,
                                    "response_time": check.response_time,
                                }
                                for check in filtered_checks
                            ],
                            "heartbeat_checks": heartbeat_data,
                            "incidents": [incident.to_dict() for incident in incidents],
                            "ssl_info": ssl_info,
                            "domain_info": domain_info,
                            "dns_info": dns_info,
                        }

                        # Only send update if meaningful state has changed
                        # We compare the meaningful data, not the full state with timestamps
                        state_changed = (
                            meaningful_state != last_meaningful_state
                            or current_heartbeat_hash != last_heartbeat_hash
                        )

                        if state_changed:
                            # Create full response with current timestamp
                            current_state: Dict[str, Any] = {
                                **meaningful_state,
                                "last_update": datetime.now(timezone.utc).isoformat(),
                            }

                            data = json.dumps(current_state)
                            yield f"data: {data}\n\n"
                            last_meaningful_state = meaningful_state.copy()
                            last_heartbeat_hash = current_heartbeat_hash
                            heartbeat_counter = 0  # Reset counter on actual update
                        else:
                            # Send heartbeat every 30 seconds if no state change
                            heartbeat_counter += 1
                            if heartbeat_counter >= 10:  # 10 * 3 seconds = 30 seconds
                                yield f": heartbeat {datetime.now(timezone.utc).isoformat()}\n\n"
                                heartbeat_counter = 0

                    # Wait before next check
                    time.sleep(3)  # Check every 3 seconds for specific monitor

                except GeneratorExit:
                    # Client disconnected
                    print(
                        f"SSE Monitor: Client {user_id} disconnected cleanly from monitor {monitor_id}"
                    )
                    break
                except Exception as e:
                    # Log error and continue
                    print(
                        f"SSE Monitor Error for user {user_id}, monitor {monitor_id}: {e}"
                    )
                    yield f"data: {json.dumps({'error': 'Monitor stream error', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                    time.sleep(10)  # Wait longer on error

        except GeneratorExit:
            print(
                f"SSE Monitor: Client {user_id} disconnected from monitor {monitor_id}"
            )
        except Exception as e:
            print(f"SSE Monitor Error for user {user_id}, monitor {monitor_id}: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
            "Access-Control-Allow-Credentials": "true",
            "X-Accel-Buffering": "no",  # Disable buffering for nginx
        },
    )
