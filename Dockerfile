# syntax=docker/dockerfile:1
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    iputils-ping \
    ca-certificates \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create app user and directory
RUN useradd -m -u 1000 uptimo && \
    mkdir -p /app/instance && \
    chown -R uptimo:uptimo /app

WORKDIR /app

# Copy dependency files
COPY --chown=uptimo:uptimo pyproject.toml uv.lock ./

# Copy application code
COPY --chown=uptimo:uptimo . .

# Install dependencies as uptimo user
USER uptimo
RUN uv sync --frozen --no-dev

# Set environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    DATABASE_URL=sqlite:///instance/uptimo.db

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/auth/login').read()"

# Run migrations and start app
CMD ["sh", "-c", "uv run alembic upgrade head && uv run gunicorn -w 1 -b 0.0.0.0:5000 --timeout 120 --access-logfile - --error-logfile - wsgi:app"]