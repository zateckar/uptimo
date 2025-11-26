"""
WSGI entry point for production deployment.

This file is used by production WSGI servers (Gunicorn, uWSGI, etc.).
The scheduler will be automatically started by the app factory.

Example usage with Gunicorn:
    gunicorn -w 1 -b 0.0.0.0:5000 wsgi:app

Note: Use only 1 worker (-w 1) to prevent duplicate scheduler instances.
"""

import os
from app import create_app

# Create Flask app using factory pattern
# Scheduler starts automatically by default
config_name = os.getenv("FLASK_CONFIG", "production")
app = create_app(config_name)

if __name__ == "__main__":
    # This is only for direct execution (not recommended for production)
    app.run(host="0.0.0.0", port=5000)
