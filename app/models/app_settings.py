"""Application settings model."""

from datetime import datetime, timezone

from app import db


class AppSettings(db.Model):
    """Application-wide settings stored in database."""

    __tablename__ = "app_settings"

    id = db.Column(db.Integer, primary_key=True)
    log_level = db.Column(db.String(20), nullable=False, default="INFO")
    timezone = db.Column(db.String(50), nullable=False, default="UTC")
    data_retention_days = db.Column(db.Integer, nullable=False, default=365)

    # Color customization settings
    enable_custom_colors = db.Column(db.Boolean, nullable=False, default=False)

    # Brand colors
    primary_color = db.Column(db.String(7), nullable=False, default="#59bc87")
    primary_hover_color = db.Column(db.String(7), nullable=False, default="#45a676")
    primary_subtle_color = db.Column(
        db.String(20), nullable=False, default="rgba(168, 255, 204, 0.15)"
    )

    # Status colors
    success_color = db.Column(db.String(7), nullable=False, default="#22c55e")
    success_bg_color = db.Column(db.String(7), nullable=False, default="#f0fdf4")
    danger_color = db.Column(db.String(7), nullable=False, default="#dc2626")
    danger_bg_color = db.Column(db.String(7), nullable=False, default="#fef2f2")
    warning_color = db.Column(db.String(7), nullable=False, default="#f59e0b")
    warning_bg_color = db.Column(db.String(7), nullable=False, default="#fffbeb")
    info_color = db.Column(db.String(7), nullable=False, default="#06b6d4")
    info_bg_color = db.Column(db.String(7), nullable=False, default="#ecfeff")
    unknown_color = db.Column(db.String(7), nullable=False, default="#6b7280")
    unknown_bg_color = db.Column(db.String(7), nullable=False, default="#f3f4f6")

    # Dark mode specific colors (optional overrides)
    dark_primary_color = db.Column(db.String(7), nullable=True, default="#3b82f6")
    dark_primary_hover_color = db.Column(db.String(7), nullable=True, default="#60a5fa")
    dark_primary_subtle_color = db.Column(
        db.String(20), nullable=True, default="rgba(59, 130, 246, 0.15)"
    )

    # Dark mode status colors
    dark_success_color = db.Column(db.String(7), nullable=True, default="#4ade80")
    dark_success_bg_color = db.Column(db.String(7), nullable=True, default="#052e16")
    dark_danger_color = db.Column(db.String(7), nullable=True, default="#f87171")
    dark_danger_bg_color = db.Column(db.String(7), nullable=True, default="#1f0713")
    dark_warning_color = db.Column(db.String(7), nullable=True, default="#fbbf24")
    dark_warning_bg_color = db.Column(db.String(7), nullable=True, default="#1c1305")
    dark_info_color = db.Column(db.String(7), nullable=True, default="#38bdf8")
    dark_info_bg_color = db.Column(db.String(7), nullable=True, default="#071926")
    dark_unknown_color = db.Column(db.String(7), nullable=True, default="#9ca3af")
    dark_unknown_bg_color = db.Column(db.String(7), nullable=True, default="#1f2937")

    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @staticmethod
    def get_settings() -> "AppSettings":
        """Get the application settings, creating defaults if not exists."""
        settings = AppSettings.query.first()
        if not settings:
            settings = AppSettings()
            db.session.add(settings)
            db.session.commit()
        return settings

    def __repr__(self) -> str:
        return f"<AppSettings log_level={self.log_level} timezone={self.timezone}>"
