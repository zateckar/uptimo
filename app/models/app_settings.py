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
