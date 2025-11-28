# Uptimo

A self-hosted monitoring application for personal or small-team use. Monitor HTTP endpoints, Kafka brokers, TCP ports, and more with real-time dashboards, incident tracking, and flexible notification channels.

<img width="2361" height="1386" alt="{8B93D352-237A-4106-8BE4-28A59C6A3D30}" src="https://github.com/user-attachments/assets/b465c5fc-eaa5-42d5-9732-3f2b995e0c65" />


## Features

### Core Monitoring
- **HTTP/HTTPS Monitoring**: Status codes, response time, SSL/TLS validation, domain verification, content matching
- **Kafka Broker Monitoring**: Connection health, SSL/TLS certificate validation, SASL authentication support
- **TCP Port Monitoring**: Port availability and response time tracking
- **Ping (ICMP) Monitoring**: Network reachability checks
- **Configurable Intervals**: 30s, 60s, 5min check frequencies

### Dashboard & Reporting
- Real-time monitor status with live updates via Server-Sent Events (SSE)
- Interactive latency charts (1h, 6h, 24h, 7d, 30d views)
- Visual heartbeat timeline showing recent check results
- Uptime percentage tracking (24h, 7d, 30d)
- Incident timeline with detailed outage tracking

### Notifications
- **Multi-Channel Support**: Email (SMTP/SendGrid), Telegram, Slack
- **Smart Alerting**: Configurable thresholds, escalation timers
- **Event Types**: Down alerts, recovery notifications, SSL warnings
- Per-monitor notification configuration

### Security
- User authentication with Flask-Login
- Password hashing with Werkzeug
- Admin-only user management
- Protected API endpoints

## Technology Stack

- **Backend**: Flask, SQLAlchemy, APScheduler
- **Database**: SQLite with Alembic migrations
- **Frontend**: Jinja2 templates, Chart.js, Server-Sent Events
- **Package Management**: UV (Python package manager)

## Installation

### Prerequisites

- Python 3.11+
- UV package manager
- Git (optional)

### Quick Start

1. **Clone the repository** (or download the source):
   ```bash
   git clone <repository-url>
   cd uptimo
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize database**:
   ```bash
   uv run alembic upgrade head
   ```

5. **Create admin user**:
   ```bash
   uv run python -c "
   from app import create_app, db
   from app.models.user import User
   app = create_app()
   with app.app_context():
       user = User(username='admin', email='admin@example.com', is_admin=True)
       user.set_password('change_me_immediately')
       db.session.add(user)
       db.session.commit()
       print('Admin user created')
   "
   ```

6. **Run the application**:
   ```bash
   uv run python run.py
   ```

7. **Access the application**:
   Open http://localhost:5000 and login with the admin credentials

### Production Deployment

#### Using Docker

1. **Build the image**:
   ```bash
   docker build -t uptimo:latest .
   ```

2. **Run the container**:
   ```bash
   docker run -d \
     -p 5000:5000 \
     -v uptimo-data:/app/instance \
     -e SECRET_KEY=your-secret-key \
     -e FLASK_ENV=production \
     --name uptimo \
     uptimo:latest
   ```

3. **Access logs**:
   ```bash
   docker logs -f uptimo
   ```

#### Manual Production Setup

1. **Set production environment variables** in `.env`:
   ```bash
   FLASK_ENV=production
   SECRET_KEY=<generate-strong-random-key>
   DATABASE_URL=sqlite:///instance/uptimo.db
   ```

2. **Use production WSGI server**:
   ```bash
   uv add gunicorn
   uv run gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
   ```

3. **Configure reverse proxy** (nginx example):
   ```nginx
   server {
       listen 80;
       server_name monitor.example.com;
       
       location / {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           
           # SSE support
           proxy_buffering off;
           proxy_cache off;
           proxy_read_timeout 86400s;
       }
   }
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions | *Required* |
| `DATABASE_URL` | Database connection string | `sqlite:///instance/uptimo.db` |
| `FLASK_ENV` | Environment (development/production) | `production` |
| `SENDGRID_API_KEY` | SendGrid API key for email | - |
| `SMTP_SERVER` | SMTP server for email | - |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USERNAME` | SMTP username | - |
| `SMTP_PASSWORD` | SMTP password | - |
| `SMTP_USE_TLS` | Use TLS for SMTP | `true` |

### Data Retention

Configure data retention via the admin panel to automatically clean up old check results and maintain database performance.

### Database Migrations

When upgrading or making schema changes:

```bash
# Check current migration
uv run alembic current

# Upgrade to latest
uv run alembic upgrade head

# Downgrade if needed
uv run alembic downgrade -1
```

## Usage

### Creating Monitors

1. Navigate to **Dashboard** → **Create Monitor**
2. Select monitor type (HTTP, Kafka, TCP, Ping)
3. Configure target, interval, and check criteria
4. Set up notifications (optional)
5. Activate the monitor

### Setting Up Notifications

1. Go to **Notifications** → **Channels**
2. Create notification channel (Email, Telegram, or Slack)
3. Test the channel
4. Link channel to monitors via monitor settings

### Managing Users (Admin)

1. Navigate to **Admin** → **Users**
2. Create, edit, or deactivate users
3. Assign admin privileges
4. Reset passwords if needed

## Development

### Setup Development Environment

```bash
# Install dependencies
uv sync

# Install dev dependencies
uv add --dev pytest ruff pyright

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
│   ├── __init__.py           # Application factory
│   ├── models/               # Database models
│   ├── routes/               # API endpoints and views
│   ├── forms/                # WTForms definitions
│   ├── services/             # Business logic
│   ├── schedulers/           # Background check scheduler
│   ├── notification/         # Notification system
│   ├── templates/            # Jinja2 templates
│   └── static/               # CSS, JS, images
├── alembic/                  # Database migrations
├── tests/                    # Test suite
├── config.py                 # Configuration
├── run.py                    # Development server
├── wsgi.py                   # Production WSGI entry
└── pyproject.toml            # Project dependencies
```

### Adding New Monitor Types

1. Update [`MonitorType`](app/models/monitor.py) enum
2. Add checker logic in [`app/services/checker.py`](app/services/checker.py)
3. Update form validation in [`app/forms/monitor.py`](app/forms/monitor.py)
4. Add UI components in templates

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html

# Run specific test
uv run pytest tests/test_data_retention.py
```

## API Documentation

### Authentication

All API endpoints require authentication via Flask-Login session cookies.

### Endpoints

#### Monitors

- `GET /api/monitors` - List all monitors
- `POST /api/monitors` - Create monitor
- `GET /api/monitors/<id>` - Get monitor details
- `PUT /api/monitors/<id>` - Update monitor
- `DELETE /api/monitors/<id>` - Delete monitor

#### Incidents

- `GET /api/incidents` - List incidents
- `GET /api/incidents?status=active` - Filter by status

#### Notifications

- `GET /api/notification-channels` - List channels
- `POST /api/notification-channels` - Create channel
- `GET /api/notification-history` - Notification logs

See [API documentation](docs/api.md) for complete endpoint reference.

## Troubleshooting

### Common Issues

**Database locked errors**:
- SQLite doesn't handle high concurrency well
- Consider PostgreSQL for production
- Reduce check frequency if needed

**SSE connection drops**:
- Check proxy timeout settings
- Ensure `proxy_buffering off` in nginx
- Verify firewall rules

**Failed Kafka checks**:
- Verify SSL certificates are in PEM format
- Check SASL credentials
- Ensure broker is accessible

**Missing notifications**:
- Check channel configuration
- Verify notification is enabled for monitor
- Review notification history for errors

### Logs

Application logs are written to stdout/stderr:

```bash
# View logs in Docker
docker logs -f uptimo

# View systemd logs
journalctl -u uptimo -f
```

## Security Considerations

- Change default admin password immediately
- Use strong `SECRET_KEY` in production
- Enable HTTPS via reverse proxy
- Regular database backups
- Keep dependencies updated: `uv sync --upgrade`
- Review user access regularly
- Secure notification credentials

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run linting: `uv run ruff check .`
6. Submit a pull request

## License

This project is provided as-is for personal and small-team use.

## Support

For issues and questions:
- Check existing GitHub issues
- Review documentation in `/docs`
- Create a new issue with details

---

**Uptimo** - Simple, self-hosted monitoring for everyone.
