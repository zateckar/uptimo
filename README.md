# Uptimo

A self-hosted monitoring application for personal or small-team use. Monitor HTTP endpoints, Kafka brokers, TCP ports, and more with real-time dashboards, incident tracking, and flexible notifications.

## Features

### Core Monitoring
- **HTTP/HTTPS**: Status codes, response time, SSL/TLS validation, content matching
- **Kafka**: Broker connectivity, SASL authentication, SSL/TLS support
- **TCP**: Port availability and response time
- **Ping**: Network reachability checks
- **Configurable intervals**: 30s, 1min, 5min, 15min, 30min, 1hour

### Dashboard & Analytics
- Real-time status with SSE updates
- Interactive latency charts (1h, 6h, 24h, 7d, 30d)
- Uptime percentage tracking
- Incident timeline and detailed outage tracking
- SSL certificate expiration monitoring

### Notifications
- **Email**: SMTP/SendGrid support
- **Telegram**: Bot integration
- **Slack**: Webhook support
- Smart alerting with configurable thresholds

### Security
- User authentication with Flask-Login
- Password hashing with Werkzeug
- CSRF protection
- Security headers
- Admin-only user management

## Technology Stack

- **Backend**: Flask, SQLAlchemy, APScheduler
- **Database**: SQLite with Alembic migrations
- **Frontend**: Jinja2 templates, Chart.js, SSE
- **Package Management**: UV

## Quick Start

### Prerequisites
- Python 3.8+
- UV package manager

### Installation

1. **Clone and install**:
   ```bash
   git clone <repository-url>
   cd uptimo
   uv sync
   ```

2. **Initialize database**:
   ```bash
   uv run alembic upgrade head
   ```

3. **Run development server**:
   ```bash
   uv run python run.py
   ```

### Production Deployment

```bash
# Pull and run with Docker
docker run -d \
  -p 5000:5000 \
  -v uptimo-data:/app/instance \
  -e SECRET_KEY=$(openssl rand -hex 32) \
  -e INITIAL_ADMIN_USERNAME=admin \
  -e INITIAL_ADMIN_EMAIL=admin@example.com \
  -e INITIAL_ADMIN_PASSWORD=your-secure-password \
  --name uptimo \
  --restart unless-stopped \
  ghcr.io/YOUR_USERNAME/uptimo:latest
```

## Configuration

### Environment Variables

Create a `.env` file with these settings:

```bash
# Required
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# Initial Admin (optional, for first deployment)
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_EMAIL=admin@example.com
INITIAL_ADMIN_PASSWORD=secure-password

# Database (optional, defaults to SQLite)
DATABASE_URL=sqlite:///instance/uptimo.db

# Email Notifications
SENDGRID_API_KEY=your_sendgrid_key
# OR SMTP settings
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_password
SMTP_USE_TLS=true

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# Slack
SLACK_WEBHOOK_URL=your_webhook_url
```

### Database Migrations

When upgrading:

```bash
# Check current version
uv run alembic current

# Upgrade to latest
uv run alembic upgrade head
```

## Usage

### Creating Monitors

1. Go to **Dashboard** → **Create Monitor**
2. Select type (HTTP, Kafka, TCP, Ping)
3. Configure target, interval, and check criteria
4. Set up notifications (optional)
5. Activate the monitor

### Setting Up Notifications

1. Navigate to **Notifications** → **Channels**
2. Create notification channel (Email, Telegram, or Slack)
3. Test the channel
4. Link to monitors via monitor settings

### Managing Users

1. Go to **Admin** → **Users**
2. Create, edit, or deactivate users
3. Assign admin privileges
4. Reset passwords as needed

## Development

### Setup

```bash
# Install dependencies
uv sync

# Install dev dependencies
uv add --dev pytest ruff pyrefly

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint code
uv run ruff check --fix .
```

### Project Structure

```
uptimo/
├── app/
│   ├── models/          # Database models
│   ├── routes/          # API endpoints and views
│   ├── forms/           # WTForms definitions
│   ├── services/        # Business logic
│   ├── schedulers/      # Background check scheduler
│   ├── notification/    # Notification system
│   ├── templates/       # Jinja2 templates
│   └── static/          # CSS, JS, images
├── alembic/             # Database migrations
├── tests/               # Test suite
├── config.py            # Configuration
├── run.py               # Development server
├── wsgi.py              # Production WSGI entry
└── pyproject.toml       # Project dependencies
```

## API Endpoints

### Authentication Required
All endpoints require login via Flask-Login session cookies.

### Monitors
- `GET /api/monitors` - List all monitors
- `POST /api/monitors` - Create monitor
- `GET /api/monitors/<id>` - Get monitor details
- `PUT /api/monitors/<id>` - Update monitor
- `DELETE /api/monitors/<id>` - Delete monitor

### Incidents
- `GET /api/incidents` - List incidents
- `GET /api/incidents?status=active` - Filter by status

### Notifications
- `GET /api/notification-channels` - List channels
- `POST /api/notification-channels` - Create channel
- `GET /api/notification-history` - Notification logs

## Troubleshooting

### Common Issues

**SSE connection drops**:
- Check proxy timeout settings
- Ensure `proxy_buffering off` in nginx
- Verify firewall rules

**Scheduler not running**:
- Check logs for "Monitor scheduler started"
- Use only 1 worker/process
- Verify monitors are marked as active

**Database issues**:
```bash
# Run migrations
uv run alembic upgrade head

# Reset database (development only)
rm instance/uptimo.db
uv run python run.py
```

### Logs

```bash
# Docker logs
docker logs -f uptimo

# Systemd logs
journalctl -u uptimo -f
```
---

**Uptimo** - Simple, self-hosted monitoring for everyone.