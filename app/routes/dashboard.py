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
)
from flask_login import login_required, current_user

from app import db
from app.models.monitor import Monitor, MonitorType, CheckInterval
from app.models.incident import Incident
from app.models.notification import NotificationChannel
from app.models.check_result import CheckResult
from app.forms.monitor import MonitorForm, MonitorEditForm
from app.forms.monitor_notification import MonitorNotificationForm
from app.schedulers.monitor_scheduler import monitor_scheduler
from app.utils.cache import api_cache

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
@api_cache(max_age=600)  # Cache for 10 minutes - static/semi-static data
def monitor_detail(id: int):
    """AJAX endpoint for monitor detail view.

    Optimized endpoint that returns only static and semi-static data.
    Dynamic check data (recent_checks, heartbeat_checks) should be fetched
    from dedicated endpoints: /monitor/{id}/checks and /monitor/{id}/heartbeat.
    """
    from app.models.deduplication import DomainInfo, TLSCertificate
    from urllib.parse import urlparse

    monitor = Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    # Get incidents (semi-static - doesn't change frequently)
    incidents = monitor.incidents.order_by(Incident.started_at.desc()).limit(10).all()

    # Fetch TLS/domain data directly from deduplication tables (updated daily)
    cert_info = None
    domain_check = None

    # Extract domain from target based on monitor type
    domain = monitor.target
    if monitor.type.value in ["http", "https"]:
        # Extract domain from URL
        parsed = urlparse(monitor.target)
        domain = parsed.hostname or monitor.target
    elif ":" in monitor.target:
        # Strip port from domain/IP
        domain = monitor.target.split(":")[0]

    # Fetch TLS certificate data if available (show even if monitoring disabled)
    if domain:
        tls_cert = TLSCertificate.query.filter_by(domain=domain).first()
        if tls_cert:
            cert_info = tls_cert.get_cert_data()

    # Fetch domain info if domain checking is enabled
    if monitor.check_domain and domain and not monitor.domain_check_failed:
        domain_info = DomainInfo.query.filter_by(domain=domain).first()
        if domain_info:
            domain_check = domain_info.get_dns_info()

    # Render action buttons HTML (static - only changes when monitor settings change)
    action_buttons_html = render_template(
        "dashboard/_monitor_actions.html", monitor=monitor
    )

    # Render TLS/DNS/Domain HTML server-side (static - only changes when cert/domain data updates)
    tls_html = render_template(
        "dashboard/_tls_dns_render.html",
        cert_info=cert_info,
        monitor=monitor,
        render_type="tls",
    )
    tls_summary_html = render_template(
        "dashboard/_tls_dns_render.html",
        cert_info=cert_info,
        monitor=monitor,
        render_type="tls_summary",
    )
    domain_html = render_template(
        "dashboard/_tls_dns_render.html",
        domain_check=domain_check,
        monitor=monitor,
        render_type="domain",
    )
    domain_summary_html = render_template(
        "dashboard/_tls_dns_render.html",
        domain_check=domain_check,
        monitor=monitor,
        render_type="domain_summary",
    )
    dns_html = render_template(
        "dashboard/_tls_dns_render.html",
        domain_check=domain_check,
        monitor=monitor,
        render_type="dns",
    )
    dns_summary_html = render_template(
        "dashboard/_tls_dns_render.html",
        domain_check=domain_check,
        monitor=monitor,
        render_type="dns_summary",
    )

    return jsonify(
        {
            "monitor": monitor.to_dict(
                include_recent_checks=False, include_incidents=True
            ),
            # Removed: recent_checks - use /monitor/{id}/checks endpoint
            # Removed: heartbeat_checks - use /monitor/{id}/heartbeat endpoint
            "incidents": [incident.to_dict() for incident in incidents],
            "cert_info": cert_info,
            "domain_check": domain_check,
            "action_buttons_html": action_buttons_html,
            "tls_html": tls_html,
            "tls_summary_html": tls_summary_html,
            "domain_html": domain_html,
            "domain_summary_html": domain_summary_html,
            "dns_html": dns_html,
            "dns_summary_html": dns_summary_html,
        }
    )


@bp.route("/monitor/<int:id>/heartbeat")
@login_required
def monitor_heartbeat(id: int):
    """Get heartbeat data for a specific monitor using optimized columnar format."""
    monitor = Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    # Get recent checks for heartbeat (last 50)
    recent_checks = monitor.get_recent_checks(50)

    # Use columnar format for better compression
    return jsonify({"checks": CheckResult.to_columnar_dict(recent_checks)})


@bp.route("/monitor/<int:id>/checks")
@login_required
@api_cache(max_age=60)  # Cache for 1 minute
def monitor_checks(id: int):
    """Get check data for a specific monitor with timespan filtering.

    Optimized endpoint that returns only essential fields for chart rendering.
    Uses selective field loading and columnar format for better compression.
    """

    Monitor.query.filter_by(id=id, user_id=current_user.id).first_or_404()

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

    # Calculate start time for filtering
    start_time = datetime.now(timezone.utc) - timedelta(hours=timespan_hours)

    # Calculate intelligent limit based on minimum check interval (30 seconds)
    minimum_interval = 30  # seconds - fastest possible check interval
    max_theoretical_checks = (timespan_hours * 3600) // minimum_interval
    intelligent_limit = min(max_theoretical_checks, 2000)

    # Fetch full CheckResult objects for columnar serialization
    # This allows us to use the optimized columnar format
    checks_query = (
        CheckResult.query.filter_by(monitor_id=id)
        .filter(CheckResult.timestamp >= start_time)
        .order_by(CheckResult.timestamp.desc())
        .limit(intelligent_limit)
    )

    # Execute query and get results
    checks = checks_query.all()

    # Use columnar format for better compression
    return jsonify({"checks": CheckResult.to_columnar_dict(checks)})


@bp.route("/overview-stats")
@login_required
@api_cache(max_age=60)  # Cache for 1 minute
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
            # Track if monitor was inactive before update
            was_inactive = not monitor.is_active

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

            # Reset TLS/DNS/domain timestamps when resuming a paused monitor
            if was_inactive and monitor.is_active:
                monitor.last_tls_check = None
                monitor.last_domain_check = None
                monitor.domain_check_failed = False

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
    was_inactive = not monitor.is_active
    monitor.is_active = not monitor.is_active

    # Reset TLS/DNS/domain timestamps when resuming a paused monitor
    if was_inactive and monitor.is_active:
        monitor.last_tls_check = None
        monitor.last_domain_check = None
        monitor.domain_check_failed = False

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
                    # Use columnar format for better compression
                    recent_checks = CheckResult.to_columnar_dict(
                        monitor.get_recent_checks(25)
                    )
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
                            # Use columnar format for better compression
                            recent_checks = CheckResult.to_columnar_dict(
                                monitor.get_recent_checks(25)
                            )
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
                    app.logger.warning(f"SSE Error: {e}")
                    yield f"data: {json.dumps({'error': 'SSE stream error'})}\n\n"
                    time.sleep(10)  # Wait longer on error

        except GeneratorExit:
            app.logger.info(f"SSE: Client {user_id} disconnected")
        except Exception as e:
            app.logger.error(f"SSE Error for user {user_id}: {e}")
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

                    # Get incidents
                    incidents = (
                        monitor.incidents.order_by(Incident.started_at.desc())
                        .limit(10)
                        .all()
                    )

                    # Use columnar format for better compression
                    recent_checks_columnar = CheckResult.to_columnar_dict(
                        recent_checks_heartbeat
                    )
                    filtered_checks_columnar = CheckResult.to_columnar_dict(
                        filtered_checks
                    )

                    # Create stable hash for heartbeat data to detect meaningful changes
                    current_heartbeat_hash = str(
                        hash(json.dumps(recent_checks_columnar, sort_keys=True))
                    )

                    # Create meaningful state (excluding volatile timestamps)
                    # Note: TLS/domain data is NOT included in SSE stream
                    # as it only updates once per day and is fetched via monitor_detail endpoint
                    meaningful_state: Dict[str, Any] = {
                        "monitor": monitor.to_dict(include_recent_checks=False),
                        "recent_checks": filtered_checks_columnar,
                        "heartbeat_checks": recent_checks_columnar,
                        "incidents": [incident.to_dict() for incident in incidents],
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

                        # Get incidents
                        incidents = (
                            monitor.incidents.order_by(Incident.started_at.desc())
                            .limit(10)
                            .all()
                        )

                        # Use columnar format for better compression
                        recent_checks_columnar = CheckResult.to_columnar_dict(
                            recent_checks_heartbeat
                        )
                        filtered_checks_columnar = CheckResult.to_columnar_dict(
                            filtered_checks
                        )

                        # Create stable hash for heartbeat data to detect meaningful changes
                        current_heartbeat_hash = str(
                            hash(json.dumps(recent_checks_columnar, sort_keys=True))
                        )

                        # Create meaningful state (excluding volatile timestamps)
                        # Note: TLS/domain data is NOT included in SSE stream
                        # as it only updates once per day and is fetched via monitor_detail endpoint
                        meaningful_state: Dict[str, Any] = {
                            "monitor": monitor.to_dict(include_recent_checks=False),
                            "recent_checks": filtered_checks_columnar,
                            "heartbeat_checks": recent_checks_columnar,
                            "incidents": [incident.to_dict() for incident in incidents],
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
                    app.logger.info(
                        f"SSE Monitor: Client {user_id} disconnected cleanly from monitor {monitor_id}"
                    )
                    break
                except Exception as e:
                    # Log error and continue
                    app.logger.warning(
                        f"SSE Monitor Error for user {user_id}, monitor {monitor_id}: {e}"
                    )
                    yield f"data: {json.dumps({'error': 'Monitor stream error', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                    time.sleep(10)  # Wait longer on error

        except GeneratorExit:
            app.logger.info(
                f"SSE Monitor: Client {user_id} disconnected from monitor {monitor_id}"
            )
        except Exception as e:
            app.logger.error(
                f"SSE Monitor Error for user {user_id}, monitor {monitor_id}: {e}"
            )
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
