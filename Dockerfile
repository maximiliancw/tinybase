# TinyBase Dockerfile
# 
# Multi-stage build that:
# 1. Builds the Vue admin UI
# 2. Creates a minimal Python runtime image

# =============================================================================
# Stage 1: Build Admin UI (includes auth portal)
# =============================================================================
FROM node:20-slim AS frontend-builder

# Enable corepack for yarn
RUN corepack enable

WORKDIR /app

# Copy frontend source
COPY apps/admin/package.json apps/admin/yarn.lock ./
RUN yarn install --immutable

COPY apps/admin/ ./
RUN yarn build

# =============================================================================
# Stage 2: Python Runtime
# =============================================================================
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy Python package files
COPY packages/tinybase/pyproject.toml ./
COPY README.md LICENSE ./
COPY packages/tinybase/tinybase/ ./tinybase/

# Copy built admin UI (includes auth portal) from frontend builder stage
COPY --from=frontend-builder /app/dist ./tinybase/static/app/

# Install TinyBase using uv
RUN uv pip install --no-cache .

# Create non-root user
RUN useradd --create-home --shell /bin/bash tinybase
USER tinybase

# Create data directory
RUN mkdir -p /home/tinybase/data
WORKDIR /home/tinybase/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command
CMD ["tinybase", "serve", "--host", "0.0.0.0", "--port", "8000"]

