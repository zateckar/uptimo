"""
WSGI entry point for production deployment.

This file is used by production WSGI servers (Gunicorn, uWSGI, etc.).
The scheduler will be automatically started by the app factory.

Example usage with Gunicorn:
    gunicorn -w 1 -b 0.0.0.0:5000 wsgi:app

Note: Use only 1 worker (-w 1) to prevent duplicate scheduler instances.
"""

import os
from app import create_app, init_database, db

# Create Flask app using factory pattern
# Scheduler starts automatically by default
config_name = os.getenv("FLASK_CONFIG", "production")
app = create_app(config_name)

# Initialize database if it doesn't exist (for production deployments)
with app.app_context():
    # Check if database is empty (no tables)
    inspector = db.inspect(db.engine)
    existing_tables = inspector.get_table_names()

    if not existing_tables:
        print("Initializing fresh database for production...")
        init_database()

        # Create default app settings
        from app.models.app_settings import AppSettings

        settings = AppSettings.get_settings()
        print(
            f"[OK] Production database initialized with timezone: {settings.timezone}"
        )

    # Check if there are no users and create initial admin from environment variables
    from app.models.user import User

    user_count = User.query.count()
    if user_count == 0:
        # Try to create initial admin user from environment variables
        username = app.config.get("INITIAL_ADMIN_USERNAME")
        email = app.config.get("INITIAL_ADMIN_EMAIL")
        password = app.config.get("INITIAL_ADMIN_PASSWORD")

        if username and email and password:
            # All required environment variables are present
            admin_user = User(
                username=username,
                email=email,
                is_admin=True,
                is_active=True,
            )
            admin_user.set_password(password)
            db.session.add(admin_user)
            db.session.commit()
            print(
                f"[OK] Initial admin user '{username}' created successfully from environment variables"
            )
        else:
            print(
                "[SECURITY] No users found and incomplete environment variables for initial admin setup."
            )
            print(
                "To create an admin user automatically, set all three environment variables:"
            )
            print("  - INITIAL_ADMIN_USERNAME")
            print("  - INITIAL_ADMIN_EMAIL")
            print("  - INITIAL_ADMIN_PASSWORD")
            print("Alternatively, create an admin user manually using the CLI:")
            print("  uv run flask create-admin --username <username> --email <email>")

if __name__ == "__main__":
    # This is only for direct execution (not recommended for production)
    app.run(host="0.0.0.0", port=5000)
