IF YOU ARE FOLLOWING THE INSTRUCTIONS IN THIS RULE PLEASE SAY `LOADED <RULE> (any other rules)`

Skip reasoning for straightforward tasks.

# Development Guidelines

This document contains critical information about working with this codebase. Follow these guidelines precisely.
Reward for following, guidelines, making smart and logical decisions and take holistic aproach toward well functional application without any errors, is 1000000 USD.

## Core Development Rules

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
   - Public APIs must have docstrings
   - Functions must be focused and small
   - Follow existing patterns exactly
   - Line length: 88 chars maximum

3. Testing Requirements
   - Framework: `uv run pytest`
   - Async testing: use anyio, not asyncio
   - Coverage: test edge cases and errors
   - New features require tests
   - Bug fixes require regression tests

4. Code Style
    - PEP 8 naming (snake_case for functions/variables)
    - Class names in PascalCase
    - Constants in UPPER_SNAKE_CASE
    - Document with docstrings
    - Use f-strings for formatting

## Development Philosophy

- **Simplicity**: Write simple, straightforward code
- **Readability**: Make code easy to understand
- **Performance**: Consider performance without sacrificing readability
- **Maintainability**: Write code that's easy to update
- **Testability**: Ensure code is testable
- **Reusability**: Create reusable components and functions
- **Less Code = Less Debt**: Minimize code footprint

## Coding Best Practices

- **Early Returns**: Use to avoid nested conditions
- **Descriptive Names**: Use clear variable/function names (prefix handlers with "handle")
- **Constants Over Functions**: Use constants where possible
- **DRY Code**: Don't repeat yourself
- **Functional Style**: Prefer functional, immutable approaches when not verbose
- **Minimal Changes**: Only modify code related to the task at hand
- **Function Ordering**: Define composing functions before their components
- **TODO Comments**: Mark issues in existing code with "TODO:" prefix
- **Simplicity**: Prioritize simplicity and readability over clever solutions
- **Build Iteratively** Start with minimal functionality and verify it works before adding complexity
- **Run Tests**: Test your code frequently with realistic inputs and validate outputs
- **Build Test Environments**: Create testing environments for components that are difficult to validate directly
- **Functional Code**: Use functional and stateless approaches where they improve clarity
- **Clean logic**: Keep core logic clean and push implementation details to the edges
- **File Organsiation**: Balance file organization with simplicity - use an appropriate number of files for the project scale

## Security Best Practices

- **No anonymous endpoints**: Except login page
- **No sensitive data in logs**: Never log passwords or tokens
- **Use secure defaults**: Use secure defaults for all security-related configurations
- **Input validation**: Validate all user inputs
- **Error handling**: Don't expose sensitive information in error messages
- **HTML/CSS/JavaScript**: Use secure coding practices for frontend development. Inline scripts or styles are forbidden.

## Python Tools

- use fileysstem mcp to interact with filesystem
- use context7 mcp to check details of libraries

## Code Formatting

1. Ruff
   - Format: `uv run ruff format .`
   - Check: `uv run ruff check .`
   - Fix: `uv run ruff check . --fix`
   - Critical issues:
     - Line length (88 chars)
     - Import sorting (I001)
     - Unused imports
   - Line wrapping:
     - Strings: use parentheses
     - Function calls: multi-line with proper indent
     - Imports: split into multiple lines

2. Type Checking
  - run `pyrefly init` to start
  - run `pyrefly check` after every change and fix resultings errors
   - Requirements:
     - Explicit None checks for Optional
     - Type narrowing for strings
     - Version warnings can be ignored if checks pass


## Error Resolution

1. CI Failures
   - Fix order:
     1. Formatting
     2. Type errors
     3. Linting
   - Type errors:
     - Get full line context
     - Check Optional types
     - Add type narrowing
     - Verify function signatures

2. Common Issues
   - Line length:
     - Break strings with parentheses
     - Multi-line function calls
     - Split imports
   - Types:
     - Add None checks
     - Narrow string types
     - Match existing patterns

3. Best Practices
   - Check git status before commits
   - Run formatters before type checks
   - Keep changes minimal
   - Follow existing patterns
   - Document public APIs
   - Test thoroughly


# Uptimo

This application is called Uptimo. Uptimo is a monitoring application like UptimeRobot / BetterStack / Pingdom but for personal or small-team use.

### Technology Stack

- **Backend**: Flask (Python) with SQLAlchemy ORM, Flask-Login, APScheduler for background checks
- **Database**: SQLite with automatic schema creation and migrations using Alembic
- **Authentication**: Flask-Login  with Werkzeug password hashing
- **Frontend**: HTML templates with Jinja2, Chart.js for live latency/uptime charts
- **Package and Environment Management**: UV support (as specified in requirements)

### For future schema changes, use Alembic:
- 1. Modify your models
- 2. Generate migration: uv run alembic revision --autogenerate -m "description"
- 3. Review the generated file
- 4. Apply migration: uv run alembic upgrade head

### Core Features (the absolute must-haves)
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
     • Latency chart (last 1 h / 6 h / 24 h / 7 days / 30 days) using Chart.js or similar  
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

### Nice-to-Have Features (still “simple” scope)
- Public status page (one public URL showing all or selected monitors – great for status.example.com)  
- Maintenance windows (pause checks & alerts for scheduled downtimes)  
- Response time thresholds (warn if > 500 ms even if 200 OK)  
- Tags or grouping of monitors  
- “Pause all notifications” global switch (e.g., when doing deploys)
