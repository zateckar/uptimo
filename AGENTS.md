You MUST follow these guidelines precisely at ALL TIMES.

# Development Guidelines
- IF YOU ARE FOLLOWING THE INSTRUCTIONS IN THIS RULE PLEASE SAY `LOADED <RULE> (any other rules)`
- You are an experienced senior developer and application architect with 10+ years of experience
- ALWAYS critically review all ideas and plans. Only then proceed with their implementation.
- Always do reality check for all your suggestions and propose alternative solutions if needed.

## Development Rules
1. Package Management
   - ONLY use uv, NEVER pip
   - Installation: `uv add package`
   - Running tools: `uv run tool`
   - Upgrading: `uv add --dev package --upgrade-package package`
   - FORBIDDEN: `uv pip install`, `@latest` syntax

2. Code Quality
   - Type hints required for all code
   - use pyrefly for type checking
     - run `pyrefly init` to start
     - run `pyrefly check` after every change and fix resultings errors
   - use ruff for linting and formatting
      - Format: `uv run ruff format .`
      - Check: `uv run ruff check .`
      - Fix: `uv run ruff check . --fix`

3. Testing Requirements
   - Framework: `uv run pytest`
   - Async testing: use anyio, not asyncio
   - Coverage: test edge cases and errors
   - New features require tests
   - Bug fixes require regression tests

## Security Best Practices
- **No anonymous endpoints**: Except login and status pages
- **No sensitive data in logs**: Never log passwords or tokens
- **Use secure defaults**: Use secure defaults for all security-related configurations
- **Input validation**: Validate all user inputs
- **Error handling**: Don't expose sensitive information in error messages
- **HTML/CSS/JavaScript**: Use secure coding practices for frontend development. Do NOT use inline scripts or styles.

## Available Tools
- use fileysstem mcp to interact with filesystem
- use context7 mcp to check details of libraries
- use sqlite mcp to work with the database
- use playwright mcp for browser internaction, debug and testing


# Application requirements and design
This application is called Uptimo. Uptimo is a monitoring application like UptimeRobot / BetterStack / Pingdom but for personal or small-team use.

## Technology Stack
- **Backend**: Flask (Python) with SQLAlchemy ORM, Flask-Login, APScheduler for background checks
- **Database**: SQLite with automatic schema creation and migrations using Alembic
- **Authentication**: Flask-Login  with Werkzeug password hashing
- **Frontend**: 
      - HTML templates with Jinja2, Chart.js for live latency/uptime charts
      - Where possible use server-side rendering using HTML templates with Jinja2 instead of client-side Javascript
      - SSE (Server-Sent Events) for real-time updates
      - Do not use inline scripts or styles
      - Use CFRS tokens
- **Package and Environment Management**: UV support (as specified in requirements)

## For future schema changes, use Alembic:
- 1. Modify your models
- 2. Generate migration: uv run alembic revision --autogenerate -m "description"
- 3. Review the generated file
- 4. Apply migration: uv run alembic upgrade head

## Core Features (the absolute must-haves)
1. User Management  
   - Sign-up / login / logout
   - CRUD users, reset passwords  

2. Monitor Management (CRUD)  
   - Create, edit, delete monitors  
   - Supported check types (at launch):  
     • HTTP(S) endpoints (status code, response time, optional string/JSON matching, TLS cert validation and expiration check, domain check)  
     • Kafka broker connectivity (can connect using TLS client certificate + basic metadata fetch, TLS cert validation and expiration check, domain check)  
     • TCP port check (+ domain check)
     • Ping (ICMP) + domain check
   - Check interval per monitor (30 s, 60 s, 5 min, configurable)
   - Each monitor must define criteria for outage. Will depend on kind of monitor. Typically timeout, latency higher than, status codes, specific responses.

3. Dashboard – Master/Detail Layout  
   - Left sidebar: list of all monitors (name + current status badge: green/red/gray + recent heartbeat + uptime percentage)  
   - Right pane: when you click a monitor → detailed view  
     • Current status & latency  
     • Latency chart (last 1 h / 6 h / 24 h / 7 days / 30 days) using Chart.js 
     • Recent heartbeat visualisation
     • Uptime percentage (24 h, 7 d, 30 d)  
     • Recent check history table (timestamp, status, latency, response time/error)  
     • Outage timeline (visual bar showing when it was down, the reason and total outage time)
     • Aditional data from monitors (like TLS validation and expiration date, domain check)

4. History & Incident Log  
   - Every single check result stored (forever or configurable retention)  
   - Incident auto-creation: when a monitor goes from up → down, create an incident  
   - Incident page shows start/end time, duration, and all check logs during the outage

5. Notification Management  
   - Per-monitor notification settings (enable/disable independently)  
   - Supported channels (simple to implement):  
     • Email via SendGrid / SMTP  
     • Telegram (via bot + chat ID or simple /start link)  
     • Slack webhook (bonus)  
   - Smart alerting:  
     • Notify only once when it goes down  
     • Notify again when it comes back up  
     • Optional escalation after X minutes
6. - Public status page (one public URL showing all or selected monitors)  

## Nice-to-Have Features (still “simple” scope)
- Maintenance windows (pause checks & alerts for scheduled downtimes)  
- Response time thresholds (warn if > 500 ms even if 200 OK)  
- Tags or grouping of monitors  
- “Pause all notifications” global switch (e.g., when doing deploys)
