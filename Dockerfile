# ag3ntwerk AI Agent Platform
# Multi-stage Dockerfile for production deployment

# =============================================================================
# Stage 1: Builder - Install dependencies and build the package
# =============================================================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first for better caching
COPY pyproject.toml ./
COPY src/ ./src/

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install the package with all dependencies
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
    pip install --no-cache-dir -e ".[distributed]"

# =============================================================================
# Stage 2: Production - Minimal runtime image
# =============================================================================
FROM python:3.11-slim as production

# Labels for container metadata
LABEL org.opencontainers.image.title="ag3ntwerk AI Agent Platform"
LABEL org.opencontainers.image.description="Hierarchical AI Agent Orchestration Platform"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.vendor="GozerAI"

# Create non-root user for security
RUN groupadd --gid 1000 ag3ntwerk && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash ag3ntwerk

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=ag3ntwerk:ag3ntwerk src/ ./src/
COPY --chown=ag3ntwerk:ag3ntwerk config/ ./config/
COPY --chown=ag3ntwerk:ag3ntwerk alembic.ini ./

# Create data directories
RUN mkdir -p /app/data /app/logs && \
    chown -R ag3ntwerk:ag3ntwerk /app

# Switch to non-root user
USER ag3ntwerk

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    AGENTWERK_ENV=production \
    AGENTWERK_HOST=0.0.0.0 \
    AGENTWERK_PORT=3737 \
    DATABASE_PATH=/app/data/ag3ntwerk.db \
    AGENTWERK_USE_MIGRATIONS=true

# Expose API port
EXPOSE 3737

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3737/health || exit 1

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command - run the API server
CMD ["python", "-m", "uvicorn", "ag3ntwerk.api.app:app", "--host", "0.0.0.0", "--port", "3737"]

# =============================================================================
# Stage 3: Development - Includes dev tools
# =============================================================================
FROM production as development

USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install dev dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov black ruff mypy

USER ag3ntwerk

ENV AGENTWERK_ENV=development

# Override command for development
CMD ["python", "-m", "uvicorn", "ag3ntwerk.api.app:app", "--host", "0.0.0.0", "--port", "3737", "--reload"]
