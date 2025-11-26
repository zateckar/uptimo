# Multi-stage build for Uptimo monitoring application
FROM python:3.11-slim as builder

# Install UV package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim

# Install required system packages for monitoring features
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    iputils-ping \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 uptimo && \
    mkdir -p /app/instance && \
    chown -R uptimo:uptimo /app

# Set working directory
WORKDIR /app

# Copy UV and virtual environment from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=uptimo:uptimo . .

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    DATABASE_URL=sqlite:///instance/uptimo.db

# Create instance directory with proper permissions
RUN mkdir -p instance && \
    chown -R uptimo:uptimo instance

# Switch to non-root user
USER uptimo

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/auth/login').read()"

# Run database migrations and start application
CMD ["sh", "-c", "uv run alembic upgrade head && uv run gunicorn -w 1 -b 0.0.0.0:5000 --timeout 120 --access-logfile - --error-logfile - wsgi:app"]