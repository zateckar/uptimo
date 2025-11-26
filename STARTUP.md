# Uptimo - Application Startup Guide

## Overview

Uptimo has been consolidated to use a unified scheduler initialization approach through the app factory pattern. Both development and production entry points now work correctly with automated background monitoring checks.

## Entry Points

### 1. Development Mode (`run.py`)

**Recommended for local development and testing**

```bash
uv run python run.py
```

**Features:**
- Automatically starts the Flask development server
- Initializes the monitor scheduler
- Creates test data (admin user + sample monitors) if database is empty
- Runs on `http://localhost:5000`
- Debug mode enabled
- Auto-reload disabled to prevent duplicate scheduler instances

**Default credentials:**
- Username: `admin`
- Password: `admin123`

### 2. Production Mode (`wsgi.py`)

**Recommended for production deployment with WSGI servers**

```bash
# Using Gunicorn (recommended)
uv run gunicorn -w 1 -b 0.0.0.0:5000 wsgi:app

# Using uWSGI
uv run uwsgi --http :5000 --wsgi-file wsgi.py --callable app --processes 1

# Direct execution (also starts scheduler!)
uv run python wsgi.py
```

**Important:**
- Use only **1 worker/process** to prevent duplicate scheduler instances
- Running `wsgi.py` directly **DOES start the scheduler** - you should see a confirmation message

**Configuration:**
- Uses `FLASK_CONFIG` environment variable (defaults to `production`)
- **Scheduler starts automatically** (same as development mode)
- No test data creation in production

**Important Note:**
When you run `uv run python wsgi.py` directly, you should see:
```
✓ Monitor scheduler started in production mode
```

This confirms the scheduler is running. If you don't see this message, there may be an issue.

## Scheduler Behavior

### Automatic Initialization

The scheduler is now automatically initialized in [`app/__init__.py`](app/__init__.py:44) when creating the Flask app:

```python
app = create_app(config_name)  # Scheduler starts automatically
```

### Manual Control (Optional)

If you need to disable the scheduler (e.g., for testing):

```python
from app import create_app

# Create app without scheduler
app = create_app("development", start_scheduler=False)
```

### Scheduler Lifecycle

1. **Startup:** Scheduler starts when app is created
2. **Scheduling:** All active monitors are scheduled based on their check intervals
3. **Checks:** Background jobs execute monitor checks at configured intervals
4. **Shutdown:** Scheduler stops when app terminates (handled automatically)

## Architecture Changes

### Before (Issue)

- **run.py:** Manually initialized and started scheduler ✅ **Worked**
- **wsgi.py:** Only created app, NO scheduler initialization ❌ **Checks didn't fire**
- **Duplicate code:** Scheduler logic scattered across multiple files

### After (Fixed)

- **Unified approach:** Scheduler initialization in [`app/__init__.py`](app/__init__.py:58)
- **Both entry points work:** Scheduler starts automatically for both dev and prod
- **Clean code:** Removed redundant scheduler management
- **Proper cleanup:** Automatic scheduler shutdown on app teardown

## Key Files Modified

### [`app/__init__.py`](app/__init__.py:1)
- Added `start_scheduler` parameter to `create_app()`
- Automatic scheduler initialization and startup
- Proper teardown handler for cleanup

### [`wsgi.py`](wsgi.py:1)
- Updated with production configuration
- Documentation on WSGI server usage
- Scheduler now starts automatically

### [`run.py`](run.py:1)
- Simplified to remove redundant scheduler code
- Focuses on development-specific setup (test data)
- Cleaner, more maintainable code

## Environment Variables

### FLASK_CONFIG

Controls which configuration to use:

- `development` - Development mode (debug enabled, verbose logging)
- `production` - Production mode (optimized, minimal logging)
- `default` - Alias for production

**Example:**
```bash
export FLASK_CONFIG=production
uv run gunicorn -w 1 -b 0.0.0.0:5000 wsgi:app
```

## Troubleshooting

### Checks not firing

**Symptoms:** Monitor checks don't execute in the background

**Solutions:**
1. Verify scheduler is running (check logs for "Monitor scheduler started")
2. Ensure only 1 worker/process (multiple workers create duplicate schedulers)
3. Check that monitors are marked as active in database

### Duplicate scheduler instances

**Symptoms:** Multiple check executions, log spam, database conflicts

**Solutions:**
1. Use `-w 1` with Gunicorn
2. Disable Flask auto-reloader in development (`use_reloader=False`)
3. Don't manually start scheduler if using default app creation

### Database issues

**Symptoms:** Missing tables, schema errors

**Solutions:**
```bash
# Run Alembic migrations
uv run alembic upgrade head

# Or recreate database (development only)
rm instance/uptimo.db
uv run python run.py
```

## Best Practices

### Development

1. **Use run.py:** `uv run python run.py`
2. **Check logs:** Monitor console for scheduler activity
3. **Test monitors:** Create monitors and verify checks execute

### Production

1. **Use WSGI server:** Never use Flask development server
2. **Single worker:** Always configure 1 worker to prevent scheduler duplication
3. **Environment config:** Set `FLASK_CONFIG=production`
4. **Monitor logs:** Track scheduler startup and check execution
5. **Database backups:** Regular backups of `instance/uptimo.db`

## Quick Start

### First Time Setup

```bash
# Clone repository
git clone <repo-url>
cd uptimo

# Install dependencies
uv sync

# Run development server
uv run python run.py
```

### Production Deployment

```bash
# Set environment
export FLASK_CONFIG=production

# Run database migrations
uv run alembic upgrade head

# Start with Gunicorn (1 worker)
uv run gunicorn -w 1 -b 0.0.0.0:5000 wsgi:app
```

## Summary

The application now has a **single, unified approach** to scheduler initialization:

✅ **Both entry points work correctly**  
✅ **Scheduler starts automatically**  
✅ **Clean, maintainable code**  
✅ **Proper lifecycle management**  
✅ **Production-ready**

You no longer need to worry about manual scheduler initialization - just run the appropriate entry point for your use case!