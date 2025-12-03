from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_compress import Compress
import logging
import time
from typing import Any

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
compress = Compress()

# Cache for favicon status to reduce database queries
_favicon_cache = {
    "user_id": None,
    "status": None,
    "favicon_name": None,
    "timestamp": 0.0,
}

# Global flag to prevent repeated SQLite WAL configuration
_sqlite_configured = False


def invalidate_favicon_cache(user_id: int) -> None:
    """Invalidate favicon cache for a specific user when monitor status changes."""
    global _favicon_cache
    if _favicon_cache["user_id"] == user_id:
        _favicon_cache["timestamp"] = 0.0


__all__ = [
    "create_app",
    "db",
    "login_manager",
    "csrf",
    "invalidate_favicon_cache",
    "init_database",
    "import_all_models",
]


def init_database() -> None:
    """Initialize database tables using SQLAlchemy create_all.

    This function creates all database tables based on the current models.
    It's used for fresh database initialization without Alembic migrations.
    """
    import_all_models()
    db.create_all()
    print("[OK] Database initialized using db.create_all()")


def import_all_models() -> None:
    """Import all models to ensure they are registered with SQLAlchemy.

    This function imports all model modules to ensure SQLAlchemy is aware
    of all tables before calling db.create_all().
    """
    from app.models import User, AppSettings

    # Reference models to ensure they are imported and registered with SQLAlchemy
    _ = User, AppSettings


def configure_sqlite(app):
    """Configure SQLite for optimal performance with WAL mode."""
    global _sqlite_configured

    if _sqlite_configured:
        return  # Already configured, skip

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        try:
            # Enable WAL mode for better concurrency
            from sqlalchemy import text

            db.session.execute(text("PRAGMA journal_mode=WAL"))
            db.session.execute(text("PRAGMA synchronous=NORMAL"))
            db.session.execute(text("PRAGMA cache_size=10000"))  # 10MB cache
            db.session.execute(text("PRAGMA temp_store=MEMORY"))
            db.session.execute(
                text("PRAGMA mmap_size=268435456")
            )  # 256MB memory mapping
            db.session.execute(text("PRAGMA busy_timeout=30000"))  # 30 second timeout
            db.session.commit()

            # Verify WAL mode was enabled
            result = db.session.execute(text("PRAGMA journal_mode")).scalar()
            if result and result.lower() == "wal":
                print("[OK] SQLite WAL mode and optimizations configured")
                _sqlite_configured = True  # Mark as configured
            else:
                print(f"[WARNING] SQLite journal mode: {result} (WAL not enabled)")

        except Exception as e:
            app.logger.error(f"Failed to configure SQLite WAL mode: {e}")


def create_app(config_name: str = "default", start_scheduler: bool = True) -> Flask:
    """Create and configure Flask application.

    Args:
        config_name: Configuration name to use (default, development, production)
        start_scheduler: Whether to start the background scheduler (default: True)
    """
    app = Flask(__name__)

    # Load configuration
    from config import config

    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    compress.init_app(app)

    # Configure SQLite optimizations within app context
    with app.app_context():
        configure_sqlite(app)

    # Configure login manager
    login_manager.login_view = "auth.login"  # type: ignore
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # Custom unauthorized handler that returns 404 instead of redirect
    @login_manager.unauthorized_handler
    def unauthorized():
        """Return 404 for unauthorized access to prevent route enumeration."""
        from flask import abort

        abort(404)

    # Initialize and start scheduler if requested
    if start_scheduler:
        with app.app_context():
            from app.schedulers.monitor_scheduler import init_scheduler, scheduler

            init_scheduler()
            if not scheduler.running:
                scheduler.start()
                print(f"[OK] Monitor scheduler started in {config_name} mode")
                app.logger.info("Monitor scheduler started")
            else:
                print("[OK] Monitor scheduler already running")
                app.logger.info("Monitor scheduler already running")

    # Set up security headers
    @app.after_request
    def after_request(response):
        """Set security headers after each request."""
        # Content Security Policy
        csp_directives = [
            "default-src " + app.config.get("CSP_DEFAULT_SRC", "'self'"),
            "script-src " + app.config.get("CSP_SCRIPT_SRC", "'self'"),
            "style-src " + app.config.get("CSP_STYLE_SRC", "'self'"),
            "img-src " + app.config.get("CSP_IMG_SRC", "'self' data: https:"),
            "connect-src " + app.config.get("CSP_CONNECT_SRC", "'self'"),
            "font-src " + app.config.get("CSP_FONT_SRC", "'self'"),
            "object-src " + app.config.get("CSP_OBJECT_SRC", "'none'"),
            "media-src " + app.config.get("CSP_MEDIA_SRC", "'self'"),
            "frame-src " + app.config.get("CSP_FRAME_SRC", "'none'"),
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Additional security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response

    # Set up logging - load configured log level from database
    with app.app_context():
        try:
            from app.models.app_settings import AppSettings

            settings = AppSettings.get_settings()
            log_level = getattr(logging, settings.log_level, logging.INFO)
            logging.basicConfig(
                level=log_level,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            logging.getLogger().setLevel(log_level)
            app.logger.setLevel(log_level)
            # Also set werkzeug logger to respect the configured log level
            logging.getLogger("werkzeug").setLevel(log_level)
            app.logger.info(f"Log level set to {settings.log_level}")
        except Exception as e:
            # Fallback to INFO if settings can't be loaded
            logging.basicConfig(level=logging.INFO)
            app.logger.warning(f"Failed to load log settings, using INFO: {e}")

    # Register blueprints
    from app.routes import admin, api, auth, dashboard, notifications

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp, url_prefix="/dashboard")
    app.register_blueprint(api.bp, url_prefix="/api")
    app.register_blueprint(notifications.bp, url_prefix="/notifications")
    app.register_blueprint(admin.bp, url_prefix="/admin")

    # Register template filters
    from app import template_filters

    template_filters.register_filters(app)

    # Register CLI commands
    from app.cli import clear_tls_certs, create_admin, data_retention

    data_retention.register_cli_commands(app)
    create_admin.register_cli_commands(app)
    clear_tls_certs.register_cli_commands(app)

    # Register context processor for timezone info
    @app.context_processor
    def inject_timezone() -> dict[str, Any]:
        """Inject timezone information into all templates."""
        try:
            from app.models.app_settings import AppSettings

            settings = AppSettings.get_settings()
            return {"app_timezone": settings.timezone}
        except Exception:
            return {"app_timezone": "UTC"}

    # Add root route
    @app.route("/")
    def index() -> Any:
        from flask import redirect, url_for
        from flask_login import current_user

        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index"))
        else:
            return redirect(url_for("auth.login"))

    # Add static asset caching routes
    @app.route("/static/<path:filename>")
    def serve_static(filename):
        """Serve static assets with proper caching."""
        from flask import send_from_directory
        from werkzeug.exceptions import NotFound
        from app.utils.cache import static_cache

        # Security: Prevent directory traversal
        if ".." in filename or filename.startswith("/"):
            raise NotFound()

        # Apply static caching decorator
        @static_cache
        def _serve_static():
            # Static files are in app/static
            return send_from_directory("app/static", filename)

        return _serve_static()

    @app.route("/favicon.ico")
    def favicon() -> Any:
        from flask import send_from_directory, current_app
        from flask_login import current_user
        from app.models.monitor import Monitor
        from app.utils.cache import static_cache

        # Default to "up" favicon for non-authenticated users or guests
        favicon_name = "favicon-up.svg"

        # Only check monitor status for authenticated users
        if current_user.is_authenticated:
            global _favicon_cache
            current_time = time.time()
            cache_ttl = 5  # Cache for 5 seconds to reduce database queries

            # Check if we have a valid cache entry for this user
            if (
                cache_ttl > 0
                and _favicon_cache["user_id"] == current_user.id
                and _favicon_cache["timestamp"] is not None
                and _favicon_cache["timestamp"] > (current_time - cache_ttl)
                and _favicon_cache["favicon_name"] is not None
            ):
                favicon_name = _favicon_cache["favicon_name"]
            else:
                # Cache miss or expired, fetch from database
                try:
                    # Get all active monitors for the current user
                    monitors = Monitor.query.filter_by(
                        user_id=current_user.id, is_active=True
                    ).all()

                    if monitors:
                        # Check for any down monitors
                        has_down = any(monitor.is_down() for monitor in monitors)

                        if has_down:
                            favicon_name = "favicon-down.svg"
                        else:
                            # Check if all monitors are up
                            all_up = all(monitor.is_up() for monitor in monitors)

                            if all_up:
                                favicon_name = "favicon-up.svg"
                            else:
                                # Some monitors are unknown
                                favicon_name = "favicon-warning.svg"

                    # Update cache if caching is enabled
                    if cache_ttl > 0:
                        monitor_statuses = [
                            (monitor.id, monitor.last_status) for monitor in monitors
                        ]
                        _favicon_cache = {
                            "user_id": current_user.id,
                            "status": monitor_statuses,
                            "favicon_name": favicon_name,
                            "timestamp": current_time,
                        }
                except Exception as e:
                    app.logger.error(f"Error in favicon route: {e}")
                    # If there's any error, use the default "up" favicon
                    if cache_ttl > 0:
                        _favicon_cache = {
                            "user_id": current_user.id,
                            "status": None,
                            "favicon_name": favicon_name,
                            "timestamp": current_time,
                        }

        @static_cache
        def _serve_favicon():
            return send_from_directory(
                current_app.static_folder or "static",  # type: ignore
                f"images/{favicon_name}",
                mimetype="image/svg+xml",
            )

        return _serve_favicon()

    # Register error handlers
    register_error_handlers(app)

    # Register cleanup only on actual app shutdown (not per-request)
    if start_scheduler:
        import atexit
        from app.schedulers.monitor_scheduler import scheduler

        def cleanup_scheduler():
            """Cleanup scheduler on application exit."""
            if scheduler.running:
                scheduler.shutdown(wait=False)
                print("[OK] Monitor scheduler stopped")

        atexit.register(cleanup_scheduler)

    return app


def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the Flask application."""

    @app.errorhandler(404)
    def not_found_error(error: Any) -> Any:
        from flask import render_template

        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error: Any) -> Any:
        from flask import render_template

        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden_error(error: Any) -> Any:
        from flask import render_template

        return render_template("errors/403.html"), 403


@login_manager.user_loader
def load_user(user_id: str) -> Any:
    from app.models.user import User

    return User.query.get(int(user_id))
