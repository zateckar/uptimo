# Deployment Guide for Uptimo

This guide covers deploying Uptimo to production environments.

## Quick Start with Docker

The easiest way to deploy Uptimo is using Docker:

```bash
# Pull the latest image from GitHub Container Registry
docker pull ghcr.io/YOUR_USERNAME/uptimo:latest

# Run the container
docker run -d \
  -p 5000:5000 \
  -v uptimo-data:/app/instance \
  -e SECRET_KEY=$(openssl rand -hex 32) \
  -e FLASK_ENV=production \
  --name uptimo \
  --restart unless-stopped \
  ghcr.io/YOUR_USERNAME/uptimo:latest

# View logs
docker logs -f uptimo

# Create admin user
docker exec -it uptimo uv run python -c "
from app import create_app, db
from app.models.user import User
app = create_app()
with app.app_context():
    user = User(username='admin', email='admin@example.com', is_admin=True)
    user.set_password('CHANGE_ME_IMMEDIATELY')
    db.session.add(user)
    db.session.commit()
    print('Admin user created')
"
```

## Production Environment Variables

Create a `.env` file with these required variables:

```bash
# Required
SECRET_KEY=<generate-with-openssl-rand-hex-32>
FLASK_ENV=production

# Database (optional, defaults to SQLite)
DATABASE_URL=sqlite:///instance/uptimo.db

# Email Notifications (optional)
SENDGRID_API_KEY=your_sendgrid_key
# OR
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_password
SMTP_USE_TLS=true
```

## Docker Compose Deployment

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  uptimo:
    image: ghcr.io/YOUR_USERNAME/uptimo:latest
    container_name: uptimo
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - uptimo-data:/app/instance
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - FLASK_ENV=production
      - SENDGRID_API_KEY=${SENDGRID_API_KEY:-}
      - SMTP_SERVER=${SMTP_SERVER:-}
      - SMTP_PORT=${SMTP_PORT:-587}
      - SMTP_USERNAME=${SMTP_USERNAME:-}
      - SMTP_PASSWORD=${SMTP_PASSWORD:-}
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/auth/login').read()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  uptimo-data:
    driver: local
```

Deploy with:

```bash
docker-compose up -d
```

## Nginx Reverse Proxy

Example nginx configuration for `monitor.example.com`:

```nginx
# /etc/nginx/sites-available/uptimo
server {
    listen 80;
    server_name monitor.example.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name monitor.example.com;
    
    # SSL Configuration (use certbot for Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/monitor.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/monitor.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy settings
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE support (critical for real-time updates)
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
    
    # Static files (optional optimization)
    location /static {
        proxy_pass http://localhost:5000/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable and test:

```bash
sudo ln -s /etc/nginx/sites-available/uptimo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d monitor.example.com
```

## Systemd Service (Manual Installation)

If not using Docker, create `/etc/systemd/system/uptimo.service`:

```ini
[Unit]
Description=Uptimo Monitoring Service
After=network.target

[Service]
Type=simple
User=uptimo
Group=uptimo
WorkingDirectory=/opt/uptimo
Environment="PATH=/opt/uptimo/.venv/bin"
Environment="FLASK_ENV=production"
EnvironmentFile=/opt/uptimo/.env
ExecStart=/opt/uptimo/.venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 wsgi:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Manage service:

```bash
sudo systemctl enable uptimo
sudo systemctl start uptimo
sudo systemctl status uptimo
```

## Database Backup

### Automated SQLite Backup

Create `/opt/uptimo/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/uptimo/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_PATH="/opt/uptimo/instance/uptimo.db"

mkdir -p "$BACKUP_DIR"

# Create backup
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/uptimo_$TIMESTAMP.db'"

# Keep only last 30 days
find "$BACKUP_DIR" -name "uptimo_*.db" -mtime +30 -delete

echo "Backup completed: uptimo_$TIMESTAMP.db"
```

Add to crontab (`crontab -e`):

```
0 2 * * * /opt/uptimo/backup.sh >> /var/log/uptimo-backup.log 2>&1
```

## Monitoring & Health Checks

### Health Check Endpoint

The application includes a built-in health check at `/auth/login` (returns 200 OK).

### Monitoring with uptime-kuma

You can monitor Uptimo itself using another monitoring tool:

```bash
docker run -d \
  -p 3001:3001 \
  -v uptime-kuma:/app/data \
  --name uptime-kuma \
  louislam/uptime-kuma:1
```

### Log Management

View application logs:

```bash
# Docker
docker logs -f --tail 100 uptimo

# Systemd
journalctl -u uptimo -f

# Export logs
docker logs uptimo > uptimo.log
```

## Scaling Considerations

### PostgreSQL Migration

For better performance under high load:

1. Install PostgreSQL:
```bash
sudo apt install postgresql postgresql-contrib
```

2. Create database:
```sql
CREATE DATABASE uptimo;
CREATE USER uptimo_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE uptimo TO uptimo_user;
```

3. Update `.env`:
```bash
DATABASE_URL=postgresql://uptimo_user:secure_password@localhost/uptimo
```

4. Migrate data:
```bash
uv run alembic upgrade head
```

### Redis for Caching (Future Enhancement)

For distributed deployments:

```bash
docker run -d \
  -p 6379:6379 \
  --name redis \
  redis:alpine
```

## Security Checklist

- [ ] Change default admin password immediately after deployment
- [ ] Use strong `SECRET_KEY` (minimum 32 characters)
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure firewall (allow only 80/443, block 5000 if using reverse proxy)
- [ ] Regular database backups
- [ ] Keep Docker image updated: `docker pull ghcr.io/YOUR_USERNAME/uptimo:latest`
- [ ] Review user access regularly
- [ ] Enable fail2ban for SSH protection
- [ ] Monitor system resources
- [ ] Set up log rotation

## Performance Tuning

### Gunicorn Workers

Adjust worker count based on CPU cores:

```bash
# Formula: (2 x CPU cores) + 1
gunicorn -w $((2 * $(nproc) + 1)) -b 0.0.0.0:5000 wsgi:app
```

### Database Optimization

For SQLite:

```bash
# In Python shell
from app import db
db.engine.execute('PRAGMA journal_mode=WAL')
db.engine.execute('PRAGMA synchronous=NORMAL')
```

### Data Retention

Configure via Admin panel or directly in database to prevent unbounded growth.

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs uptimo

# Verify environment variables
docker exec uptimo env

# Test database connection
docker exec uptimo uv run alembic current
```

### Database Migration Issues

```bash
# Check current version
uv run alembic current

# View migration history
uv run alembic history

# Downgrade if needed
uv run alembic downgrade -1

# Re-upgrade
uv run alembic upgrade head
```

### SSE Connections Dropping

Check nginx configuration:
- `proxy_buffering off`
- `proxy_read_timeout 86400s`
- `proxy_http_version 1.1`

### High Memory Usage

Monitor with:
```bash
docker stats uptimo
```

Reduce workers or implement caching.

## Updates and Maintenance

### Update to Latest Version

```bash
# Pull latest image
docker pull ghcr.io/YOUR_USERNAME/uptimo:latest

# Stop and remove old container
docker stop uptimo
docker rm uptimo

# Start new container (data persists in volume)
docker run -d \
  -p 5000:5000 \
  -v uptimo-data:/app/instance \
  -e SECRET_KEY=${SECRET_KEY} \
  --name uptimo \
  ghcr.io/YOUR_USERNAME/uptimo:latest
```

### Database Migrations

Always backup before running migrations:

```bash
# Backup
docker exec uptimo sqlite3 /app/instance/uptimo.db ".backup /app/instance/backup.db"

# Run migrations
docker exec uptimo uv run alembic upgrade head
```

## Support and Resources

- GitHub Issues: Report bugs and feature requests
- Documentation: See `/docs` directory
- Community: Join discussions on GitHub Discussions

---

**Last Updated:** 2024-01-20