import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Get the base directory (project root)
BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    # Use instance folder for database (Flask best practice)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        f"sqlite:///{BASE_DIR / 'instance' / 'uptimo.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SQLite-specific optimizations
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 5,  # Smaller pool for WAL mode
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 1800,  # 30 minutes
        "connect_args": {
            "timeout": 30,
            "check_same_thread": False,
            "isolation_level": None,  # Autocommit for WAL
        },
    }

    # Security settings
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() in [
        "true",
        "on",
        "1",
    ]
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # Content Security Policy
    CSP_DEFAULT_SRC = "'self'"
    CSP_SCRIPT_SRC = "'self'"
    CSP_STYLE_SRC = "'self'"
    CSP_IMG_SRC = "'self' data: https:"
    CSP_CONNECT_SRC = "'self'"
    CSP_FONT_SRC = "'self'"
    CSP_OBJECT_SRC = "'none'"
    CSP_MEDIA_SRC = "'self'"
    CSP_FRAME_SRC = "'none'"

    # Email configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ["true", "on", "1"]
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")

    # SendGrid
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")

    # Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

    # Slack
    SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

    # Initial admin user setup (for production deployment)
    INITIAL_ADMIN_USERNAME = os.environ.get("INITIAL_ADMIN_USERNAME")
    INITIAL_ADMIN_EMAIL = os.environ.get("INITIAL_ADMIN_EMAIL")
    INITIAL_ADMIN_PASSWORD = os.environ.get("INITIAL_ADMIN_PASSWORD")

    # Application settings
    CHECK_TIMEOUT = int(os.environ.get("CHECK_TIMEOUT") or 30)
    MAX_CONCURRENT_CHECKS = int(os.environ.get("MAX_CONCURRENT_CHECKS") or 10)
    DATA_RETENTION_DAYS = int(os.environ.get("DATA_RETENTION_DAYS") or 365)

    # Pagination
    MONITORS_PER_PAGE = 50
    CHECK_RESULTS_PER_PAGE = 100

    # Scheduler
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "UTC"

    # Compression settings
    COMPRESS_MIMETYPES = [
        "application/json",
        "text/html",
        "text/css",
        "text/xml",
        "application/javascript",
    ]
    COMPRESS_LEVEL = 6  # Balanced compression/speed
    COMPRESS_MIN_SIZE = 1024  # Compress responses larger than 1KB


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"


class ProductionConfig(Config):
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
