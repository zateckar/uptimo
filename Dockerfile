# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Install system dependencies
# build-essential and python3-dev are added to ensure packages can be built from source if wheels are missing
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    iputils-ping \
    ca-certificates \
    curl \
    build-essential \
    python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# Copy source code
COPY . .

# Install project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Create non-root user and set ownership
RUN useradd -m -u 1000 uptimo && \
    mkdir -p instance && \
    chown -R uptimo:uptimo /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER uptimo

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    DATABASE_URL=sqlite:///instance/uptimo.db

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/auth/login').read()"

# Run migrations and start app
CMD ["sh", "-c", "uv run alembic upgrade head && uv run gunicorn -w 1 -b 0.0.0.0:5000 --timeout 120 --access-logfile - --error-logfile - wsgi:app"]