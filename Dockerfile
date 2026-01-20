# Multi-stage Dockerfile for xingest API
# Includes Playwright with Chromium for headless scraping

FROM python:3.12-slim AS base

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright system dependencies
RUN pip install playwright && playwright install-deps chromium

FROM base AS builder

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY xingest/ xingest/

# Install dependencies
RUN pip install --no-cache-dir . fastapi uvicorn[standard]

# Install Playwright browsers
RUN playwright install chromium

FROM builder AS runtime

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 scraper
USER scraper

# Environment variables
ENV XINGEST_HEADLESS=true
ENV XINGEST_CACHE_BACKEND=sqlite
ENV XINGEST_SQLITE_PATH=/tmp/xingest_cache.db
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8000/health || exit 1

# Run the API server
CMD ["python", "-m", "uvicorn", "xingest.api:app", "--host", "0.0.0.0", "--port", "8000"]
