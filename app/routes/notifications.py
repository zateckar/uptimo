from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.notification import NotificationChannel, NotificationType
from app.models.monitor import Monitor
from app.forms.notification import (
    NotificationChannelForm,
    NotificationChannelEditForm,
)

bp = Blueprint("notifications", __name__)


@bp.route("/channels")
@login_required
def channels():
    """List all notification channels"""
    channels = (
        NotificationChannel.query.filter_by(user_id=current_user.id)
        .order_by(NotificationChannel.created_at.desc())
        .all()
    )
    return render_template(
        "notifications/channels.html",
        channels=channels,
        notification_types=NotificationType,
    )


@bp.route("/channels/create", methods=["GET", "POST"])
@login_required
def create_channel():
    """Create a new notification channel"""
    form = NotificationChannelForm()
    form.user_id = current_user.id

    if form.validate_on_submit():
        try:
            channel = NotificationChannel(
                user_id=current_user.id,
                name=form.name.data,
                type=NotificationType(form.type.data),
                config=form.get_config(),
                is_active=form.is_active.data,
            )

            db.session.add(channel)
            db.session.commit()

            flash(
                f'Notification channel "{channel.name}" created successfully!',
                "success",
            )
            return redirect(url_for("notifications.channels"))

        except Exception:
            db.session.rollback()
            flash("Failed to create notification channel.", "error")

    return render_template("notifications/create_channel.html", form=form)


@bp.route("/channels/<int:channel_id>/edit", methods=["GET", "POST"])
@login_required
def edit_channel(channel_id):
    """Edit an existing notification channel"""
    channel = NotificationChannel.query.filter_by(
        id=channel_id, user_id=current_user.id
    ).first_or_404()

    form = NotificationChannelEditForm(obj=channel)
    form.user_id = current_user.id
    form.obj = channel

    # Convert enum to string for form field
    if request.method == "GET":
        form.type.data = channel.type.value
        # Set configuration from existing channel after type is properly set
        form.set_config(channel.config)

    if form.validate_on_submit():
        try:
            channel.name = form.name.data
            channel.type = NotificationType(form.type.data)
            channel.config = form.get_config()
            channel.is_active = form.is_active.data

            db.session.commit()

            flash(
                f'Notification channel "{channel.name}" updated successfully!',
                "success",
            )
            return redirect(url_for("notifications.channels"))

        except Exception:
            db.session.rollback()
            flash("Failed to update notification channel.", "error")

    return render_template(
        "notifications/edit_channel.html", form=form, channel=channel
    )


@bp.route("/channels/<int:channel_id>/delete", methods=["POST"])
@login_required
def delete_channel(channel_id):
    """Delete a notification channel"""
    channel = NotificationChannel.query.filter_by(
        id=channel_id, user_id=current_user.id
    ).first_or_404()

    try:
        db.session.delete(channel)
        db.session.commit()
        flash(f'Notification channel "{channel.name}" deleted.', "success")
    except Exception:
        db.session.rollback()
        flash("Failed to delete notification channel.", "error")

    return redirect(url_for("notifications.channels"))


@bp.route("/channels/<int:channel_id>/test", methods=["POST"])
@login_required
def test_channel(channel_id):
    """Test a notification channel"""
    NotificationChannel.query.filter_by(
        id=channel_id, user_id=current_user.id
    ).first_or_404()

    try:
        from app.notification.service import notification_service

        success, message = notification_service.test_notification_channel(channel_id)

        if success:
            flash("Test notification sent successfully!", "success")
        else:
            flash(f"Test failed: {message}", "error")

    except Exception:
        flash("Failed to send test notification.", "error")

    return redirect(url_for("notifications.channels"))


# Monitor notification functionality has been moved to dashboard/edit
# These routes are no longer needed as notifications are now integrated
# into the main monitor edit page at /dashboard/monitor/<id>/edit


@bp.route("/history")
@login_required
def history():
    """Show notification history"""
    page = request.args.get("page", 1, type=int)
    per_page = 50

    from app.models.notification import NotificationLog

    notifications = (
        NotificationLog.query.join(Monitor)
        .filter(Monitor.user_id == current_user.id)
        .join(NotificationChannel)
        .filter(NotificationChannel.user_id == current_user.id)
        .order_by(NotificationLog.sent_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return render_template("notifications/history.html", notifications=notifications)
