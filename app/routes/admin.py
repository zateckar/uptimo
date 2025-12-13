"""Admin routes for user management."""

import json
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
from flask import Response
from flask_login import login_required, current_user

from app import db
from app.decorators import admin_required
from app.forms.auth import AdminPasswordResetForm, UserCreateForm, UserEditForm
from app.forms.color_customization import ColorCustomizationForm
from app.forms.oidc import OIDCProviderForm
from app.forms.public_status import PublicStatusPageForm, PublicStatusPageEditForm
from app.forms.settings import AppSettingsForm, DeleteOldRecordsForm
from app.models.app_settings import AppSettings
from app.models.check_result import CheckResult
from app.models.oidc_provider import OIDCProvider
from app.models.public_status_page import PublicStatusPage
from app.models.user import User
from app.services.public_status_service import PublicStatusService

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
    if settings_form.validate_on_submit():
        # Update general settings only
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

        flash("General settings updated successfully.", "success")
        db.session.commit()
        return redirect(url_for("admin.settings"))

    # Pre-populate form with current settings
    if request.method == "GET":
        settings_form.log_level.data = app_settings.log_level
        settings_form.timezone.data = app_settings.timezone
        settings_form.data_retention_days.data = app_settings.data_retention_days

    # Get public status page counts
    public_status_count = PublicStatusPage.query.count()
    active_public_status_count = PublicStatusPage.query.filter(
        PublicStatusPage.is_active.is_(True)
    ).count()

    return render_template(
        "admin/settings.html",
        settings_form=settings_form,
        delete_form=delete_form,
        db_size=db_size_formatted,
        db_path=db_file_path,
        public_status_count=public_status_count,
        active_public_status_count=active_public_status_count,
    )


@bp.route("/color-customization", methods=["GET", "POST"])
@login_required
@admin_required
def color_customization() -> Any:
    """Color customization page (admin only)."""
    color_form = ColorCustomizationForm()

    # Get current settings
    app_settings = AppSettings.get_settings()

    # Handle color form submission
    if color_form.validate_on_submit():
        # Determine which submit button was clicked
        save_colors_button = request.form.get("save_colors")
        reset_colors_button = request.form.get("reset_colors")

        if reset_colors_button:
            # Reset to default colors
            app_settings.enable_custom_colors = False
            app_settings.primary_color = "#59bc87"
            app_settings.primary_hover_color = "#45a676"
            app_settings.primary_subtle_color = "rgba(168, 255, 204, 0.15)"
            app_settings.success_color = "#22c55e"
            app_settings.success_bg_color = "#f0fdf4"
            app_settings.danger_color = "#dc2626"
            app_settings.danger_bg_color = "#fef2f2"
            app_settings.warning_color = "#f59e0b"
            app_settings.warning_bg_color = "#fffbeb"
            app_settings.info_color = "#06b6d4"
            app_settings.info_bg_color = "#ecfeff"
            app_settings.unknown_color = "#6b7280"
            app_settings.unknown_bg_color = "#f3f4f6"
            app_settings.dark_primary_color = "#3b82f6"
            app_settings.dark_primary_hover_color = "#60a5fa"
            app_settings.dark_primary_subtle_color = "rgba(59, 130, 246, 0.15)"
            app_settings.dark_success_color = "#4ade80"
            app_settings.dark_success_bg_color = "#052e16"
            app_settings.dark_danger_color = "#f87171"
            app_settings.dark_danger_bg_color = "#1f0713"
            app_settings.dark_warning_color = "#fbbf24"
            app_settings.dark_warning_bg_color = "#1c1305"
            app_settings.dark_info_color = "#38bdf8"
            app_settings.dark_info_bg_color = "#071926"
            app_settings.dark_unknown_color = "#9ca3af"
            app_settings.dark_unknown_bg_color = "#1f2937"

            flash("Color settings reset to defaults successfully.", "success")

        elif save_colors_button:
            # Update color settings - properly handle None/empty values
            app_settings.enable_custom_colors = color_form.enable_custom_colors.data

            # Light mode colors - use form data or keep current value
            app_settings.primary_color = (
                color_form.primary_color.data or app_settings.primary_color
            )
            app_settings.primary_hover_color = (
                color_form.primary_hover_color.data or app_settings.primary_hover_color
            )
            app_settings.primary_subtle_color = (
                color_form.primary_subtle_color.data
                or app_settings.primary_subtle_color
            )
            app_settings.success_color = (
                color_form.success_color.data or app_settings.success_color
            )
            app_settings.success_bg_color = (
                color_form.success_bg_color.data or app_settings.success_bg_color
            )
            app_settings.danger_color = (
                color_form.danger_color.data or app_settings.danger_color
            )
            app_settings.danger_bg_color = (
                color_form.danger_bg_color.data or app_settings.danger_bg_color
            )
            app_settings.warning_color = (
                color_form.warning_color.data or app_settings.warning_color
            )
            app_settings.warning_bg_color = (
                color_form.warning_bg_color.data or app_settings.warning_bg_color
            )
            app_settings.info_color = (
                color_form.info_color.data or app_settings.info_color
            )
            app_settings.info_bg_color = (
                color_form.info_bg_color.data or app_settings.info_bg_color
            )
            app_settings.unknown_color = (
                color_form.unknown_color.data or app_settings.unknown_color
            )
            app_settings.unknown_bg_color = (
                color_form.unknown_bg_color.data or app_settings.unknown_bg_color
            )

            # Dark mode colors - allow empty to disable dark mode override
            app_settings.dark_primary_color = color_form.dark_primary_color.data or None
            app_settings.dark_primary_hover_color = (
                color_form.dark_primary_hover_color.data or None
            )
            app_settings.dark_primary_subtle_color = (
                color_form.dark_primary_subtle_color.data or None
            )
            app_settings.dark_success_color = color_form.dark_success_color.data or None
            app_settings.dark_success_bg_color = (
                color_form.dark_success_bg_color.data or None
            )
            app_settings.dark_danger_color = color_form.dark_danger_color.data or None
            app_settings.dark_danger_bg_color = (
                color_form.dark_danger_bg_color.data or None
            )
            app_settings.dark_warning_color = color_form.dark_warning_color.data or None
            app_settings.dark_warning_bg_color = (
                color_form.dark_warning_bg_color.data or None
            )
            app_settings.dark_info_color = color_form.dark_info_color.data or None
            app_settings.dark_info_bg_color = color_form.dark_info_bg_color.data or None
            app_settings.dark_unknown_color = color_form.dark_unknown_color.data or None
            app_settings.dark_unknown_bg_color = (
                color_form.dark_unknown_bg_color.data or None
            )

            flash("Color settings updated successfully.", "success")

        db.session.commit()
        return redirect(url_for("admin.color_customization"))

    # Pre-populate form with current settings
    if request.method == "GET":
        color_form.enable_custom_colors.data = app_settings.enable_custom_colors
        color_form.primary_color.data = app_settings.primary_color or "#59bc87"
        color_form.primary_hover_color.data = (
            app_settings.primary_hover_color or "#45a676"
        )
        color_form.primary_subtle_color.data = (
            app_settings.primary_subtle_color or "rgba(168, 255, 204, 0.15)"
        )
        color_form.success_color.data = app_settings.success_color or "#22c55e"
        color_form.success_bg_color.data = app_settings.success_bg_color or "#f0fdf4"
        color_form.danger_color.data = app_settings.danger_color or "#dc2626"
        color_form.danger_bg_color.data = app_settings.danger_bg_color or "#fef2f2"
        color_form.warning_color.data = app_settings.warning_color or "#f59e0b"
        color_form.warning_bg_color.data = app_settings.warning_bg_color or "#fffbeb"
        color_form.info_color.data = app_settings.info_color or "#06b6d4"
        color_form.info_bg_color.data = app_settings.info_bg_color or "#ecfeff"
        color_form.unknown_color.data = app_settings.unknown_color or "#6b7280"
        color_form.unknown_bg_color.data = app_settings.unknown_bg_color or "#f3f4f6"
        color_form.dark_primary_color.data = (
            app_settings.dark_primary_color or "#3b82f6"
        )
        color_form.dark_primary_hover_color.data = (
            app_settings.dark_primary_hover_color or "#60a5fa"
        )
        color_form.dark_primary_subtle_color.data = (
            app_settings.dark_primary_subtle_color or "rgba(59, 130, 246, 0.15)"
        )
        color_form.dark_success_color.data = (
            app_settings.dark_success_color or "#4ade80"
        )
        color_form.dark_success_bg_color.data = (
            app_settings.dark_success_bg_color or "#052e16"
        )
        color_form.dark_danger_color.data = app_settings.dark_danger_color or "#f87171"
        color_form.dark_danger_bg_color.data = (
            app_settings.dark_danger_bg_color or "#1f0713"
        )
        color_form.dark_warning_color.data = (
            app_settings.dark_warning_color or "#fbbf24"
        )
        color_form.dark_warning_bg_color.data = (
            app_settings.dark_warning_bg_color or "#1c1305"
        )
        color_form.dark_info_color.data = app_settings.dark_info_color or "#38bdf8"
        color_form.dark_info_bg_color.data = (
            app_settings.dark_info_bg_color or "#071926"
        )
        color_form.dark_unknown_color.data = (
            app_settings.dark_unknown_color or "#9ca3af"
        )
        color_form.dark_unknown_bg_color.data = (
            app_settings.dark_unknown_bg_color or "#1f2937"
        )

    return render_template(
        "admin/color_customization.html",
        color_form=color_form,
        app_settings=app_settings,
    )


@bp.route("/custom-colors.css")
def custom_colors_css() -> Any:
    """Generate custom CSS with color overrides (public endpoint)."""
    app_settings = AppSettings.get_settings()

    if not app_settings.enable_custom_colors:
        # Return empty CSS if custom colors are disabled
        return Response("", mimetype="text/css")

    # Generate CSS with CORRECT variable names matching style.css
    # Light mode colors
    light_css_vars = [
        f"  --brand-primary: {app_settings.primary_color};",
        f"  --brand-primary-hover: {app_settings.primary_hover_color};",
        f"  --brand-primary-subtle: {app_settings.primary_subtle_color};",
        f"  --status-success: {app_settings.success_color};",
        f"  --status-success-bg: {app_settings.success_bg_color};",
        f"  --status-danger: {app_settings.danger_color};",
        f"  --status-danger-bg: {app_settings.danger_bg_color};",
        f"  --status-warning: {app_settings.warning_color};",
        f"  --status-warning-bg: {app_settings.warning_bg_color};",
        f"  --status-info: {app_settings.info_color};",
        f"  --status-info-bg: {app_settings.info_bg_color};",
        f"  --status-unknown: {app_settings.unknown_color};",
        f"  --status-unknown-bg: {app_settings.unknown_bg_color};",
    ]

    # Build the CSS content
    css_parts = [":root {", *light_css_vars, "}"]

    # Add dark mode overrides if any dark mode color is set
    if app_settings.dark_primary_color:
        dark_css_vars = [
            '[data-theme="dark"] {',
            f"  --brand-primary: {app_settings.dark_primary_color};",
            f"  --brand-primary-hover: {app_settings.dark_primary_hover_color or app_settings.dark_primary_color};",
            f"  --brand-primary-subtle: {app_settings.dark_primary_subtle_color or 'rgba(59, 130, 246, 0.15)'};",
            f"  --status-success: {app_settings.dark_success_color or app_settings.success_color};",
            f"  --status-success-bg: {app_settings.dark_success_bg_color or 'rgba(34, 197, 94, 0.15)'};",
            f"  --status-danger: {app_settings.dark_danger_color or app_settings.danger_color};",
            f"  --status-danger-bg: {app_settings.dark_danger_bg_color or 'rgba(220, 38, 38, 0.15)'};",
            f"  --status-warning: {app_settings.dark_warning_color or app_settings.warning_color};",
            f"  --status-warning-bg: {app_settings.dark_warning_bg_color or 'rgba(245, 158, 11, 0.15)'};",
            f"  --status-info: {app_settings.dark_info_color or app_settings.info_color};",
            f"  --status-info-bg: {app_settings.dark_info_bg_color or 'rgba(6, 182, 212, 0.15)'};",
            f"  --status-unknown: {app_settings.dark_unknown_color or app_settings.unknown_color};",
            f"  --status-unknown-bg: {app_settings.dark_unknown_bg_color or 'rgba(107, 114, 128, 0.15)'};",
            "}",
        ]
        css_parts.extend(["", *dark_css_vars])

    css_content = "\n".join(css_parts)
    return Response(css_content, mimetype="text/css")


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


# Public Status Page Management
@bp.route("/public-status")
@login_required
@admin_required
def public_status_pages() -> Any:
    """List all public status pages (admin only)."""
    status_pages = PublicStatusPage.query.order_by(
        PublicStatusPage.created_at.desc()
    ).all()
    return render_template("admin/public_status_pages.html", status_pages=status_pages)


@bp.route("/public-status/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_public_status_page() -> Any:
    """Create a new public status page (admin only)."""
    form = PublicStatusPageForm(user_id=current_user.id)

    if form.validate_on_submit():
        try:
            PublicStatusService.create_status_page(
                user_id=current_user.id,
                url_type=form.url_type.data,
                selected_monitors=[int(m) for m in form.selected_monitors.data]
                if form.selected_monitors.data
                else [],
                custom_header=form.custom_header.data,
                description=form.description.data,
                is_active=form.is_active.data,
            )

            flash("Public status page created successfully.", "success")
            return redirect(url_for("admin.public_status_pages"))

        except ValueError as e:
            flash(str(e), "danger")
        except Exception:
            flash("Error creating status page. Please try again.", "danger")

    return render_template("admin/create_public_status_page.html", form=form)


@bp.route("/public-status/<int:page_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_public_status_page(page_id: int) -> Any:
    """Edit an existing public status page (admin only)."""
    status_page = PublicStatusPage.query.get_or_404(page_id)

    form = PublicStatusPageEditForm(obj=status_page, user_id=current_user.id)

    # Pre-populate selected monitors
    if request.method == "GET" and status_page.selected_monitors:
        try:
            selected_monitors = json.loads(status_page.selected_monitors)
            # Convert to strings for form field compatibility
            form.selected_monitors.data = [
                str(monitor_id) for monitor_id in selected_monitors
            ]
        except (json.JSONDecodeError, TypeError):
            form.selected_monitors.data = []

    if form.validate_on_submit():
        try:
            PublicStatusService.update_status_page(
                status_page=status_page,
                selected_monitors=[int(m) for m in form.selected_monitors.data]
                if form.selected_monitors.data
                else [],
                custom_header=form.custom_header.data,
                description=form.description.data,
            )

            flash("Public status page updated successfully.", "success")
            return redirect(url_for("admin.public_status_pages"))

        except ValueError as e:
            flash(str(e), "danger")
        except Exception:
            flash("Error updating status page. Please try again.", "danger")

    return render_template(
        "admin/edit_public_status_page.html", form=form, status_page=status_page
    )


@bp.route("/public-status/<int:page_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_public_status_page(page_id: int) -> Any:
    """Delete a public status page (admin only)."""
    status_page = PublicStatusPage.query.get_or_404(page_id)

    page_header = status_page.custom_header or f"Status Page {status_page.id}"
    db.session.delete(status_page)
    db.session.commit()

    flash(f"Public status page '{page_header}' deleted successfully.", "success")
    return redirect(url_for("admin.public_status_pages"))


@bp.route("/public-status/<int:page_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_public_status_page_active(page_id: int) -> Any:
    """Toggle public status page active status (admin only)."""
    from flask import jsonify

    status_page = PublicStatusPage.query.get_or_404(page_id)

    status_page.is_active = not status_page.is_active
    db.session.commit()

    return jsonify({"success": True, "is_active": status_page.is_active})


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    size_float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_float < 1024.0:
            return f"{size_float:.2f} {unit}"
        size_float /= 1024.0
    return f"{size_float:.2f} PB"


# OIDC Provider Management
@bp.route("/oidc-providers")
@login_required
@admin_required
def oidc_providers() -> Any:
    """List all OIDC providers (admin only)."""
    providers = OIDCProvider.query.order_by(OIDCProvider.created_at.desc()).all()
    return render_template("admin/oidc_providers.html", providers=providers)


@bp.route("/oidc-providers/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_oidc_provider() -> Any:
    """Create a new OIDC provider (admin only)."""
    form = OIDCProviderForm()

    if form.validate_on_submit():
        # Determine configuration type and set appropriate fields
        provider = OIDCProvider(
            name=form.name.data,
            display_name=form.display_name.data,
            client_id=form.client_id.data,
            client_secret=form.client_secret.data,
            scope=form.scope.data,
            is_active=form.is_active.data,
        )

        # Set configuration based on type
        if form.config_type.data == "discovery":
            provider.issuer_url = form.issuer_url.data
        else:
            provider.auth_url = form.auth_url.data
            provider.token_url = form.token_url.data
            provider.jwks_url = form.jwks_url.data
            provider.userinfo_url = form.userinfo_url.data

        db.session.add(provider)
        db.session.commit()

        flash(
            f"OIDC provider '{provider.display_name}' created successfully.", "success"
        )
        return redirect(url_for("admin.oidc_providers"))

    return render_template("admin/create_oidc_provider.html", form=form)


@bp.route("/oidc-providers/<int:provider_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_oidc_provider(provider_id: int) -> Any:
    """Edit an existing OIDC provider (admin only)."""
    provider = OIDCProvider.query.get_or_404(provider_id)

    # Get connected users for this provider
    connected_users = User.query.filter_by(
        auth_type="oidc", oidc_provider=provider.name
    ).all()

    form = OIDCProviderForm(obj=provider)

    # Pre-populate configuration type and mask client secret
    if request.method == "GET":
        form.config_type.data = "discovery" if provider.issuer_url else "manual"
        # Mask the client secret for display
        if provider.client_secret:
            form.client_secret.data = "*" * len(provider.client_secret)

    if form.validate_on_submit():
        # Update basic fields
        provider.name = form.name.data
        provider.display_name = form.display_name.data
        provider.client_id = form.client_id.data
        provider.scope = form.scope.data
        provider.is_active = form.is_active.data

        # Only update client secret if it's not masked (doesn't consist of only asterisks)
        if form.client_secret.data and not (
            form.client_secret.data.startswith("*")
            and form.client_secret.data.count("*") > len(form.client_secret.data) / 2
        ):
            provider.client_secret = form.client_secret.data

        # Clear all configuration fields first
        provider.issuer_url = None
        provider.auth_url = None
        provider.token_url = None
        provider.jwks_url = None
        provider.userinfo_url = None

        # Set configuration based on type
        if form.config_type.data == "discovery":
            provider.issuer_url = form.issuer_url.data
        else:
            provider.auth_url = form.auth_url.data
            provider.token_url = form.token_url.data
            provider.jwks_url = form.jwks_url.data
            provider.userinfo_url = form.userinfo_url.data

        db.session.commit()

        flash(
            f"OIDC provider '{provider.display_name}' updated successfully.", "success"
        )
        return redirect(url_for("admin.oidc_providers"))

    return render_template(
        "admin/edit_oidc_provider.html",
        form=form,
        provider=provider,
        connected_users=connected_users,
    )


@bp.route("/oidc-providers/<int:provider_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_oidc_provider(provider_id: int) -> Any:
    """Delete an OIDC provider (admin only)."""
    provider = OIDCProvider.query.get_or_404(provider_id)

    # Check if any users are connected to this provider
    connected_users = User.query.filter_by(
        auth_type="oidc", oidc_provider=provider.name
    ).count()

    if connected_users > 0:
        flash(
            f"Cannot delete provider '{provider.display_name}' because {connected_users} user(s) are connected to it. "
            f"Please disable the provider instead.",
            "danger",
        )
        return redirect(url_for("admin.oidc_providers"))

    provider_name = provider.display_name
    db.session.delete(provider)
    db.session.commit()

    flash(f"OIDC provider '{provider_name}' deleted successfully.", "success")
    return redirect(url_for("admin.oidc_providers"))


@bp.route("/oidc-providers/<int:provider_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_oidc_provider_active(provider_id: int) -> Any:
    """Toggle OIDC provider active status (admin only)."""
    provider = OIDCProvider.query.get_or_404(provider_id)

    provider.is_active = not provider.is_active
    db.session.commit()

    status = "enabled" if provider.is_active else "disabled"
    flash(f"OIDC provider '{provider.display_name}' {status} successfully.", "success")
    return redirect(url_for("admin.oidc_providers"))
