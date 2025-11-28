# syntax=docker/dockerfile:1.4
# Multi-stage build for Uptimo monitoring application

FROM python:3.13-slim AS builder

# Install UV package manager (copy and ensure executable)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

WORKDIR /app

# Install build-time system dependencies needed to build native Python extensions.
# If you need Rust for any dependency build, add rustc cargo to this list.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      gcc \
      libssl-dev \
      libffi-dev \
      libpq-dev \
      ca-certificates \
      curl && \
    rm -rf /var/lib/apt/lists/*

# Copy only dependency files first (cache-friendly)
COPY pyproject.toml uv.lock ./

# Use BuildKit cache mounts for pip and uv caches. Print versions and fail with extra debug if uv sync fails.
# This requires building with BuildKit (docker buildx) and the Dockerfile syntax directive above.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    uv --version && python --version && \
    uv sync --frozen --no-dev || ( \
      echo "=== uv sync failed ==="; \
      echo "uv/pip/python versions:"; uv --version || true; python --version || true; \
      echo "ls -la /app:"; ls -la /app || true; \
      echo "ls -la /root/.cache:"; ls -la /root/.cache || true; \
      false )

# Production stage
FROM python:3.13-slim

# Install required system packages for monitoring features
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      iputils-ping \
      ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user and app dirs (do this before copying files to set correct ownership)
RUN useradd -m -u 1000 uptimo && \
    mkdir -p /app/instance && \
    chown -R uptimo:uptimo /app

WORKDIR /app

# Copy UV binary and virtual environment from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

COPY --from=builder /app/.venv /app/.venv

# Copy application code and make sure files are owned by uptime user
COPY --chown=uptimo:uptimo . .

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    DATABASE_URL=sqlite:///instance/uptimo.db

# Ensure instance dir ownership
RUN mkdir -p instance && chown -R uptimo:uptimo instance

# Switch to non-root user
USER uptimo

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/auth/login').read()"

# Run database migrations and start application
CMD ["sh", "-c", "uv run alembic upgrade head && uv run gunicorn -w 1 -b 0.0.0.0:5000 --timeout 120 --access-logfile - --error-logfile - wsgi:app"]
