"""Admin routes for user management."""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from app import db
from app.decorators import admin_required
from app.forms.auth import AdminPasswordResetForm, UserCreateForm, UserEditForm
from app.forms.settings import AppSettingsForm, DeleteOldRecordsForm
from app.models.app_settings import AppSettings
from app.models.check_result import CheckResult
from app.models.user import User

bp = Blueprint("admin", __name__)


@bp.route("/users")
@login_required
@admin_required
def users() -> Any:
    """List all users (admin only)."""
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@bp.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_user() -> Any:
    """Create a new user (admin only)."""
    form = UserCreateForm()

    if form.validate_on_submit():
        user = User(
            username=form.username.data or "",
            email=form.email.data or "",
            is_admin=form.is_admin.data,
            is_active=form.is_active.data,
        )

        password = form.password.data or ""
        if not password:
            flash("Password is required", "danger")
            return render_template("admin/create_user.html", form=form)

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(
            f"User {user.username} created successfully.",
            "success",
        )
        return redirect(url_for("admin.users"))

    return render_template("admin/create_user.html", form=form)


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id: int) -> Any:
    """Edit an existing user (admin only)."""
    user = User.query.get_or_404(user_id)

    form = UserEditForm(
        original_username=user.username,
        original_email=user.email,
        obj=user,
    )

    if form.validate_on_submit():
        user.username = form.username.data or user.username
        user.email = form.email.data or user.email
        user.is_admin = form.is_admin.data
        user.is_active = form.is_active.data

        db.session.commit()

        flash(f"User {user.username} updated successfully.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/edit_user.html", form=form, user=user)


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id: int) -> Any:
    """Delete a user (admin only)."""
    user = User.query.get_or_404(user_id)

    # Prevent deleting yourself
    from flask_login import current_user

    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin.users"))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    flash(f"User {username} deleted successfully.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_user_active(user_id: int) -> Any:
    """Toggle user active status (admin only)."""
    user = User.query.get_or_404(user_id)

    # Prevent deactivating yourself
    from flask_login import current_user

    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for("admin.users"))

    user.is_active = not user.is_active
    db.session.commit()

    status = "activated" if user.is_active else "deactivated"
    flash(f"User {user.username} {status} successfully.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/reset-password", methods=["GET", "POST"])
@login_required
@admin_required
def reset_user_password(user_id: int) -> Any:
    """Reset a user's password (admin only)."""
    user = User.query.get_or_404(user_id)

    form = AdminPasswordResetForm()

    if form.validate_on_submit():
        password = form.new_password.data or ""
        if not password:
            flash("Password is required", "danger")
            return render_template("admin/reset_password.html", form=form, user=user)

        user.set_password(password)
        db.session.commit()

        flash(
            f"Password for user {user.username} has been reset successfully.",
            "success",
        )
        return redirect(url_for("admin.users"))

    return render_template("admin/reset_password.html", form=form, user=user)


@bp.route("/settings", methods=["GET", "POST"])
@login_required
@admin_required
def settings() -> Any:
    """Application settings page (admin only)."""
    settings_form = AppSettingsForm()
    delete_form = DeleteOldRecordsForm()

    # Get current settings
    app_settings = AppSettings.get_settings()

    # Get database information - use more direct approach
    db_size = 0
    db_file_path = None

    try:
        # Try to get the database file path from SQLAlchemy engine
        engine = db.engine
        if engine and hasattr(engine, "url") and engine.url.drivername == "sqlite":
            # Get the actual database path from SQLAlchemy
            db_file_path = engine.url.database
            if db_file_path and os.path.exists(db_file_path):
                db_size = os.path.getsize(db_file_path)
    except Exception:
        # Fallback to manual URI parsing if SQLAlchemy method fails
        db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if db_uri.startswith("sqlite:///"):
            from pathlib import Path
            from urllib.parse import urlparse

            try:
                # Parse the URI properly for cross-platform compatibility
                parsed = urlparse(db_uri)
                db_file_path = parsed.path

                # Remove leading slash for Windows absolute paths
                if os.name == "nt" and db_file_path and db_file_path.startswith("/"):
                    db_file_path = db_file_path[1:]

                # Convert to absolute path if relative (works for both dev and prod)
                if db_file_path and not os.path.isabs(db_file_path):
                    # Use Flask's application root for better production compatibility
                    BASE_DIR = Path(current_app.root_path)
                    db_file_path = BASE_DIR / db_file_path

                if os.path.exists(str(db_file_path)):
                    db_size = os.path.getsize(str(db_file_path))
            except (OSError, ValueError):
                # Final fallback: try common production database locations
                common_paths = [
                    # Environment variable override
                    os.environ.get("UPTIMO_DB_PATH"),
                    # Flask instance folder
                    Path(current_app.instance_path) / "uptimo.db",
                    # Standard locations relative to app root
                    Path(current_app.root_path) / "instance" / "uptimo.db",
                    Path(current_app.root_path) / "uptimo.db",
                ]

                for path in common_paths:
                    if path and os.path.exists(str(path)):
                        db_size = os.path.getsize(str(path))
                        db_file_path = str(path)
                        break

    # Format database size
    db_size_formatted = format_file_size(db_size)

    # Handle settings form submission
    if settings_form.validate_on_submit() and "submit" in request.form:
        app_settings.log_level = settings_form.log_level.data or app_settings.log_level
        app_settings.timezone = settings_form.timezone.data or app_settings.timezone
        app_settings.data_retention_days = (
            settings_form.data_retention_days.data or app_settings.data_retention_days
        )

        # Update logging level
        log_level = settings_form.log_level.data
        if log_level:
            numeric_level = getattr(logging, log_level, logging.INFO)
            logging.getLogger().setLevel(numeric_level)
            current_app.logger.setLevel(numeric_level)

        db.session.commit()
        flash("Settings updated successfully.", "success")
        return redirect(url_for("admin.settings"))

    # Pre-populate form with current settings
    if request.method == "GET":
        settings_form.log_level.data = app_settings.log_level
        settings_form.timezone.data = app_settings.timezone
        settings_form.data_retention_days.data = app_settings.data_retention_days

    return render_template(
        "admin/settings.html",
        settings_form=settings_form,
        delete_form=delete_form,
        db_size=db_size_formatted,
        db_path=db_file_path,
    )


@bp.route("/settings/vacuum", methods=["POST"])
@login_required
@admin_required
def vacuum_database() -> Any:
    """Vacuum the SQLite database (admin only)."""
    try:
        db.session.execute(db.text("VACUUM"))
        db.session.commit()
        flash("Database vacuumed successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error vacuuming database: {e!s}", "danger")

    return redirect(url_for("admin.settings"))


@bp.route("/settings/delete-old-records", methods=["POST"])
@login_required
@admin_required
def delete_old_records() -> Any:
    """Delete old check records (admin only)."""
    delete_form = DeleteOldRecordsForm()

    if not delete_form.validate_on_submit():
        flash("Invalid form data.", "danger")
        return redirect(url_for("admin.settings"))

    days = delete_form.days.data
    if not days:
        flash("Number of days is required.", "danger")
        return redirect(url_for("admin.settings"))

    try:
        # Calculate cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Delete old check results
        deleted_count = CheckResult.query.filter(
            CheckResult.timestamp < cutoff_date
        ).delete(synchronize_session=False)

        db.session.commit()

        flash(
            f"Successfully deleted {deleted_count} check records older than {days} days.",
            "success",
        )
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting old records: {e!s}", "danger")

    return redirect(url_for("admin.settings"))


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    size_float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_float < 1024.0:
            return f"{size_float:.2f} {unit}"
        size_float /= 1024.0
    return f"{size_float:.2f} PB"
