# ag3ntwerk Deployment Guide

Comprehensive deployment documentation for the ag3ntwerk AI Agent Platform.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Configuration Reference](#configuration-reference)
4. [Docker Deployment](#docker-deployment)
5. [Production Checklist](#production-checklist)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Component | Version | Required | Notes |
|-----------|---------|----------|-------|
| Python | 3.10+ | Yes | 3.14 recommended for development |
| Docker / Docker Compose | 24+ / v2 | Optional | For containerized deployment |
| PostgreSQL | 16+ | Optional | SQLite is the default; PostgreSQL for production persistence |
| Redis | 7+ | Optional | Required for Nexus bridge, distributed mode, and caching |
| Ollama | latest | Recommended | Local LLM inference; other providers supported |
| Node.js | 18+ | Optional | Only for building the web dashboard |

---

## Quick Start

### Local Development (no Docker)

```bash
# Clone and install
cd /path/to/ag3ntwerk
pip install -e ".[dev]"

# Start the API server (SQLite, Ollama on localhost)
python -m uvicorn ag3ntwerk.api.app:app --host 127.0.0.1 --port 3737 --reload

# Or use the CLI entry point
ag3ntwerk
```

The server starts at `http://localhost:3737` with:
- API docs at `/docs` (Swagger UI)
- Health check at `/health`
- Web dashboard at `/` (if built)

### With Docker Compose

```bash
cd /path/to/ag3ntwerk

# Copy and edit environment file
cp .env.example .env
# Edit .env with your passwords and API keys

# Start core services (API + PostgreSQL + Redis)
docker compose up -d

# With local LLM (Ollama)
docker compose --profile llm up -d

# With federated services (Nexus, Forge, Sentinel)
docker compose --profile federated up -d

# With monitoring (Prometheus + Grafana)
docker compose --profile monitoring up -d

# All profiles at once
docker compose --profile llm --profile federated --profile monitoring up -d
```

---

## Configuration Reference

All configuration is driven by environment variables. The application reads these
at startup via `ag3ntwerk.core.config.Config.from_env()` and
`ag3ntwerk.persistence.database.DatabaseConfig.from_env()`.

### Application Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTWERK_ENV` | `development` | Environment: `development`, `testing`, `staging`, `production` |
| `ENVIRONMENT` | `development` | Alias for `AGENTWERK_ENV` (lower precedence) |
| `DEBUG` | `false` | Enable debug mode. Automatically `true` in development |
| `APP_NAME` | `ag3ntwerk Command Center` | Application display name |
| `APP_VERSION` | `1.0.0` | Application version string |

### Server / API

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTWERK_HOST` | `0.0.0.0` | API server bind address |
| `AGENTWERK_PORT` | `3737` | API server port |
| `HOST` | `0.0.0.0` | Alias for `AGENTWERK_HOST` (lower precedence) |
| `PORT` | `3737` | Alias for `AGENTWERK_PORT` (lower precedence) |
| `WORKERS` | `1` | Number of uvicorn worker processes |
| `RELOAD` | `false` | Enable auto-reload on code changes |
| `CORS_ORIGINS` | *(localhost:3000,3737,5173)* | Comma-separated list of allowed CORS origins |
| `AGENTWERK_DRAIN_TIMEOUT` | `30` | Seconds to wait for in-flight requests during shutdown |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | `console` | Log output format: `console` or `json` |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_BACKEND` | `sqlite` | Database backend: `sqlite` or `postgresql` |
| `DATABASE_PATH` | `~/.ag3ntwerk/data/ag3ntwerk.db` | SQLite database file path |
| `PG_HOST` | `localhost` | PostgreSQL hostname |
| `PG_PORT` | `5432` | PostgreSQL port |
| `PG_DATABASE` | `ag3ntwerk` | PostgreSQL database name |
| `PG_USER` | `ag3ntwerk` | PostgreSQL username |
| `PG_PASSWORD` | *(empty)* | PostgreSQL password (**required** in production with PostgreSQL) |
| `AGENTWERK_DB_POOL_SIZE` | `10` | Connection pool size |
| `DATABASE_POOL_SIZE` | `10` | Alias for `AGENTWERK_DB_POOL_SIZE` (lower precedence) |
| `AGENTWERK_DB_MAX_OVERFLOW` | `20` | Maximum pool overflow connections |
| `DATABASE_MAX_OVERFLOW` | `20` | Alias for `AGENTWERK_DB_MAX_OVERFLOW` (lower precedence) |
| `DATABASE_ECHO` | `false` | Log all SQL statements (debug) |
| `AGENTWERK_USE_MIGRATIONS` | `true` | Use Alembic migrations for schema management |

### Security / Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTWERK_AUTH_REQUIRED` | `false` | Enforce authentication on API endpoints |
| `AGENTWERK_JWT_SECRET` | *(ephemeral)* | JWT signing secret (**required** in production) |
| `AGENTWERK_API_SECRET` | *(ephemeral)* | API key hashing secret (**required** in production) |
| `AGENTWERK_SECRETS_KEY` | *(none)* | Encryption key for the file-based secrets backend |
| `SECRET_BACKEND` | *(none)* | Secrets storage backend (`file`, etc.) |
| `AGENTWERK_WEBSOCKET_AUTH_ENABLED` | `false` | Require token authentication for WebSocket connections |

### LLM Providers

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | LLM provider: `ollama`, `gpt4all`, `openai`, `anthropic`, `google`, `openrouter`, `huggingface`, `github`, `perplexity` |
| `LLM_BASE_URL` | *(per provider)* | Override the provider's base URL |
| `LLM_DEFAULT_MODEL` | *(none)* | Default model name |
| `LLM_TIMEOUT` | `300` | Request timeout in seconds |
| `LLM_MAX_RETRIES` | `3` | Maximum retry attempts |
| `LLM_RETRY_DELAY` | `1.0` | Delay between retries in seconds |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL (also used as `LLM_BASE_URL` fallback for Ollama) |
| `OLLAMA_MODEL` | *(none)* | Ollama model name (fallback for `LLM_DEFAULT_MODEL`) |
| `OPENAI_API_KEY` | *(none)* | OpenAI API key |
| `ANTHROPIC_API_KEY` | *(none)* | Anthropic API key |
| `GOOGLE_API_KEY` | *(none)* | Google (Gemini) API key |
| `OPENROUTER_API_KEY` | *(none)* | OpenRouter API key |
| `HUGGINGFACE_API_KEY` | *(none)* | Hugging Face API key |
| `GITHUB_TOKEN` | *(none)* | GitHub Models API key |
| `PERPLEXITY_API_KEY` | *(none)* | Perplexity API key |

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL (used by Nexus bridge) |
| `REDIS_PASSWORD` | *(none)* | Redis password (used in Docker Compose) |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable global rate limiting |
| `RATE_LIMIT_TASKS` | `10` | Tasks per minute per client |
| `RATE_LIMIT_CHAT` | `20` | Chat messages per minute per client |
| `RATE_LIMIT_WORKFLOWS` | `5` | Workflow executions per minute per client |
| `RATE_LIMIT_GLOBAL` | `100` | Global requests per minute |

### Graceful Shutdown

| Variable | Default | Description |
|----------|---------|-------------|
| `SHUTDOWN_DRAIN_TIMEOUT` | `30` | Seconds to wait for in-flight requests to complete |
| `SHUTDOWN_FORCE_TIMEOUT` | `60` | Hard timeout before forced shutdown |
| `SHUTDOWN_CHECK_INTERVAL` | `0.5` | Seconds between drain checks |

### Health Checks

| Variable | Default | Description |
|----------|---------|-------------|
| `HEALTH_CACHE_INTERVAL` | `30` | Seconds to cache health check results |
| `HEALTH_TIMEOUT` | `5` | Seconds before health check times out |
| `HEALTH_DETAILED` | `true` | Enable detailed health endpoint |

### Integrations (Revenue Stack)

| Variable | Default | Description |
|----------|---------|-------------|
| `LINKEDIN_ACCESS_TOKEN` | *(none)* | LinkedIn OAuth access token |
| `LINKEDIN_PERSON_URN` | *(none)* | LinkedIn person URN |
| `TWITTER_BEARER_TOKEN` | *(none)* | Twitter/X bearer token |
| `TWITTER_API_KEY` | *(none)* | Twitter/X API key |
| `TWITTER_API_SECRET` | *(none)* | Twitter/X API secret |
| `TWITTER_ACCESS_TOKEN` | *(none)* | Twitter/X user access token |
| `TWITTER_ACCESS_SECRET` | *(none)* | Twitter/X user access secret |
| `GUMROAD_ACCESS_TOKEN` | *(none)* | Gumroad access token |
| `WHISPER_BACKEND` | `auto` | Voice backend: `auto`, `openai-whisper`, `faster-whisper`, `buzz` |

### Workbench

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTWERK_WORKBENCH_ENABLED` | *(none)* | Enable the workbench module |
| `AGENTWERK_WORKBENCH_ROOT` | *(none)* | Workbench root directory |
| `AGENTWERK_WORKBENCH_RUNNER` | *(none)* | Workbench code runner backend |
| `AGENTWERK_WORKBENCH_AUTH_TOKEN` | *(none)* | Workbench authentication token |
| `AGENTWERK_WORKBENCH_LOCALHOST_ONLY` | *(none)* | Restrict workbench to localhost |
| `AGENTWERK_WORKBENCH_IDE_MODE` | *(none)* | IDE integration mode |
| `AGENTWERK_WORKBENCH_CPU_LIMIT` | *(none)* | CPU limit for workbench tasks |
| `AGENTWERK_WORKBENCH_MEMORY_LIMIT` | *(none)* | Memory limit for workbench tasks |

### Tool Execution

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTWERK_TOOL_TIMEOUT` | *(none)* | Default tool execution timeout |
| `AGENTWERK_TOOL_MAX_RETRIES` | *(none)* | Maximum tool retry attempts |
| `AGENTWERK_TOOL_RATE_LIMIT` | *(none)* | Tool invocation rate limit |

### GUI (PySide6 Desktop)

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTWERK_GUI_REFRESH_MS` | `5000` | Dashboard refresh interval in milliseconds |

### Service Bridges (Docker Compose)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXUS_ENABLED` | `true` | Enable Nexus (Nexus) bridge |
| `NEXUS_CHANNEL_PREFIX` | `ag3ntwerk:nexus` | Redis channel prefix for Nexus |
| `FORGE_ENABLED` | `true` | Enable Forge (Forge) bridge |
| `FORGE_CHANNEL_PREFIX` | `ag3ntwerk:forge` | Redis channel prefix for Forge |
| `SENTINEL_ENABLED` | `true` | Enable Sentinel (Sentinel/Citadel) bridge |
| `SENTINEL_CHANNEL_PREFIX` | `ag3ntwerk:sentinel` | Redis channel prefix for Sentinel |

### Data Directory

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTWERK_DATA_DIR` | `~/.ag3ntwerk` | Root data directory for state files, phase5 state, metacognition data |

### Monitoring (Docker Compose)

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAFANA_USER` | `admin` | Grafana admin username |
| `GRAFANA_PASSWORD` | `admin` | Grafana admin password |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | *(none)* | OpenTelemetry collector endpoint |

---

## Docker Deployment

### Architecture Overview

The `docker-compose.yml` defines these services:

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| `ag3ntwerk` | ag3ntwerk-api | 3737 | Main API server (FastAPI/uvicorn) |
| `postgres` | ag3ntwerk-postgres | 5432 | PostgreSQL 16 database |
| `redis` | ag3ntwerk-redis | 6379 | Redis 7 for bridges and caching |
| `nexus` | ag3ntwerk-nexus | -- | Nexus Nexus strategic service (profile: `federated`) |
| `forge` | ag3ntwerk-forge | -- | Forge Forge development service (profile: `federated`) |
| `sentinel` | ag3ntwerk-sentinel | -- | Sentinel Sentinel/Citadel security service (profile: `federated`) |
| `ollama` | ag3ntwerk-ollama | 11434 | Local LLM inference (profile: `llm`) |
| `prometheus` | ag3ntwerk-prometheus | 9090 | Metrics collection (profile: `monitoring`) |
| `grafana` | ag3ntwerk-grafana | 3000 | Metrics dashboards (profile: `monitoring`) |

### Profiles

Docker Compose profiles allow selective service startup:

```bash
# Core only (ag3ntwerk + postgres + redis)
docker compose up -d

# Core + local LLM
docker compose --profile llm up -d

# Core + federated services
docker compose --profile federated up -d

# Core + monitoring stack
docker compose --profile monitoring up -d
```

### Environment File

Copy `.env.example` to `.env` before starting:

```bash
cp .env.example .env
```

At minimum, set:

```env
PG_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>
```

### Development Override

The `docker-compose.override.yml` automatically applies when present. It:

- Switches to **SQLite** (removes PostgreSQL dependency for local development)
- Enables **debug logging** and **auto-reload**
- Mounts source code into the container for live editing
- Exposes port **5678** for `debugpy` remote debugging
- Disables **authentication enforcement**

To use PostgreSQL in development, edit the override or remove it:

```bash
# Temporarily ignore the override
docker compose -f docker-compose.yml up -d
```

### Building Images

```bash
# Development image (includes dev tools, reload enabled)
docker compose build ag3ntwerk

# Production-only image
docker build --target production -t ag3ntwerk:latest .

# With build cache
docker build --target production --build-arg BUILDKIT_INLINE_CACHE=1 -t ag3ntwerk:latest .
```

### Volumes

| Volume | Purpose |
|--------|---------|
| `ag3ntwerk-data` | Application data (SQLite DB, state files, logs) |
| `postgres-data` | PostgreSQL data directory |
| `redis-data` | Redis AOF persistence |
| `ollama-data` | Downloaded LLM models |
| `prometheus-data` | Metrics time series data |
| `grafana-data` | Dashboard configurations |

---

## Production Checklist

### Required Environment Variables

These variables **must** be set in production (`AGENTWERK_ENV=production`):

| Variable | Why |
|----------|-----|
| `AGENTWERK_ENV=production` | Activates production validations and security headers |
| `AGENTWERK_JWT_SECRET` | JWT tokens use ephemeral secrets otherwise (tokens lost on restart) |
| `AGENTWERK_API_SECRET` | API key hashing uses ephemeral secrets otherwise |
| `DATABASE_BACKEND` | Must be explicitly set; validated at startup |
| `PG_HOST` | Required when `DATABASE_BACKEND=postgresql` |
| `PG_PASSWORD` | Required when `DATABASE_BACKEND=postgresql` |

### Security Hardening

1. **Enable authentication**:
   ```env
   AGENTWERK_AUTH_REQUIRED=true
   AGENTWERK_JWT_SECRET=<64-char-hex-string>
   AGENTWERK_API_SECRET=<64-char-hex-string>
   ```
   Generate secrets with: `python -c "import secrets; print(secrets.token_hex(32))"`

2. **Restrict CORS origins** to your production domains:
   ```env
   CORS_ORIGINS=https://dashboard.example.com,https://api.example.com
   ```

3. **Install `slowapi`** for full rate limiting (auth endpoints have a built-in
   fallback, but the rest of the API requires slowapi):
   ```bash
   pip install slowapi
   ```

4. **Enable HSTS** (automatic when `AGENTWERK_ENV=production`).

5. **Use non-default database credentials**:
   ```env
   PG_USER=ag3ntwerk_prod
   PG_PASSWORD=<strong-random-password>
   ```

6. **Bind Redis to internal networks only**. The default `docker-compose.yml`
   already binds Redis to `127.0.0.1:6379` on the host.

7. **Set secrets encryption key** if using the file-based secrets backend:
   ```env
   SECRET_BACKEND=file
   AGENTWERK_SECRETS_KEY=<encryption-key>
   ```

8. **Enable WebSocket authentication** if exposing WebSockets:
   ```env
   AGENTWERK_WEBSOCKET_AUTH_ENABLED=true
   ```

9. **Run behind a reverse proxy** (nginx, Caddy, Traefik) with TLS termination.

10. **Disable debug mode** (automatic when `AGENTWERK_ENV=production`, but verify):
    ```env
    DEBUG=false
    ```

### Database Migrations

In production, use Alembic migrations instead of auto-schema creation:

```bash
# Check migration status
alembic current
alembic history

# Apply pending migrations
alembic upgrade head

# Or set auto-migrate in the application (not recommended for production)
# The application warns about pending migrations at startup when
# AGENTWERK_USE_MIGRATIONS=true (the default).
```

### Scaling

- Increase `WORKERS` for multi-process serving (e.g., `WORKERS=4`)
- Increase `AGENTWERK_DB_POOL_SIZE` proportionally to worker count
- Use `AGENTWERK_DB_MAX_OVERFLOW` for burst capacity
- Consider running federated services (`--profile federated`) for workload
  isolation

---

## Monitoring

### Health Check Endpoints

| Endpoint | Method | Purpose | Response Codes |
|----------|--------|---------|----------------|
| `/health` | GET | Basic health check (liveness) | 200 |
| `/health/live` | GET | Kubernetes liveness probe | 200 / 503 |
| `/health/ready` | GET | Kubernetes readiness probe | 200 / 503 |
| `/health/detailed` | GET | Aggregated subsystem health | 200 / 503 |
| `/metrics` | GET | Application metrics summary | 200 |

The basic `/health` endpoint returns:
```json
{
  "status": "healthy",
  "llm_connected": true,
  "coo_ready": true,
  "timestamp": "2026-02-11T12:00:00"
}
```

The detailed health endpoint (`/health/detailed?force_refresh=true`) returns
status for every subsystem (database, LLM, learning pipeline, metacognition,
etc.) and reports `HEALTHY`, `DEGRADED`, or `UNHEALTHY`.

### Docker Health Check

The Dockerfile includes a built-in health check:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3737/health || exit 1
```

### Prometheus + Grafana

Enable the monitoring profile:

```bash
docker compose --profile monitoring up -d
```

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (default login: `admin` / `admin`)

Prometheus scrape configuration is expected at
`deploy/monitoring/prometheus/prometheus.yml`. Grafana provisioning at
`deploy/monitoring/grafana/provisioning/`.

### Structured Logging

Set `LOG_FORMAT=json` for machine-parseable log output suitable for
log aggregation pipelines (ELK, Loki, CloudWatch, etc.):

```env
LOG_FORMAT=json
LOG_LEVEL=INFO
```

Every log entry includes structured fields: `request_id`, `component`, `phase`,
and contextual data from the current request.

### OpenTelemetry

The Docker Compose configuration supports an OpenTelemetry collector:

```env
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

---

## Troubleshooting

### Application Will Not Start

**Symptom**: `ConfigurationError: Configuration validation failed`

**Cause**: Missing or invalid environment variables.

**Solution**: Check the error message for specifics. Common issues:
- `AGENTWERK_JWT_SECRET` not set in production
- `AGENTWERK_API_SECRET` not set in production
- `DATABASE_BACKEND` not set in production
- Invalid `LLM_PROVIDER` value

```bash
# Validate configuration without starting
python -c "from ag3ntwerk.core.config import validate_config; print(validate_config())"
```

### LLM Provider Not Reachable

**Symptom**: `Cannot reach LLM provider at localhost:11434`

**Solution**:
- Ensure Ollama is running: `ollama serve`
- If using Docker, ensure the Ollama container is started:
  ```bash
  docker compose --profile llm up -d ollama
  ```
- Check the `OLLAMA_HOST` or `LLM_BASE_URL` environment variable
- For cloud providers, verify the API key is set

### Database Connection Failed

**Symptom**: `Cannot connect to PostgreSQL at ...`

**Solution**:
- Verify PostgreSQL is running and accepting connections
- Check `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`
- For Docker: ensure the postgres service is healthy:
  ```bash
  docker compose ps postgres
  docker compose logs postgres
  ```

### Redis Connection Failed

**Symptom**: Nexus bridge errors or distributed mode failures

**Solution**:
- Verify Redis is running: `redis-cli ping`
- Check `REDIS_URL` format: `redis://:password@host:port`
- For Docker: ensure the redis service is healthy:
  ```bash
  docker compose ps redis
  docker compose logs redis
  ```

### Rate Limiting Not Working

**Symptom**: No rate limit headers in responses (except on auth endpoints)

**Solution**: Install `slowapi`:
```bash
pip install slowapi
```
Auth endpoints (`/api/v1/fleet/relays/token`, etc.) always have built-in rate
limiting regardless of `slowapi` availability.

### Port Already in Use

**Symptom**: `[Errno 98] Address already in use` or `[WinError 10048]`

**Solution**:
```bash
# Find what's using port 3737
# Linux/macOS:
lsof -i :3737
# Windows:
netstat -ano | findstr :3737

# Use a different port
AGENTWERK_PORT=3738 python -m uvicorn ag3ntwerk.api.app:app --port 3738
```

### Pending Database Migrations

**Symptom**: `Database has N pending migration(s). Run 'alembic upgrade head'`

**Solution**:
```bash
# Apply migrations
alembic upgrade head

# If alembic is not installed
pip install alembic
```

### WebSocket Connection Refused

**Symptom**: WebSocket connects but immediately closes with code 1008

**Solution**: If `AGENTWERK_WEBSOCKET_AUTH_ENABLED=true`, a valid token must be
provided as a query parameter:
```
ws://localhost:3737/ws?token=<your-token>
```

### Container OOM (Out of Memory)

**Symptom**: Container killed unexpectedly

**Solution**: Increase Docker memory limits. For Ollama with large models,
ensure at least 8 GB is available:
```yaml
# In docker-compose.override.yml
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 8g
```

### Graceful Shutdown Timeout

**Symptom**: `Drain timeout exceeded with requests still in flight`

**Solution**: Increase the drain timeout:
```env
AGENTWERK_DRAIN_TIMEOUT=60
SHUTDOWN_DRAIN_TIMEOUT=60
SHUTDOWN_FORCE_TIMEOUT=120
```

---

## Quick Reference

### Common Commands

```bash
# Start development stack
docker compose up -d

# View logs
docker compose logs -f ag3ntwerk

# Restart a service
docker compose restart ag3ntwerk

# Stop everything
docker compose down

# Stop and remove volumes (destructive!)
docker compose down -v

# Run tests inside container
docker compose exec ag3ntwerk pytest tests/unit/ -q

# Open a shell inside the running container
docker compose exec ag3ntwerk bash

# Check database migrations
docker compose exec ag3ntwerk alembic current
```

### Default Ports

| Service | Port | URL |
|---------|------|-----|
| ag3ntwerk API | 3737 | http://localhost:3737 |
| API Docs | 3737 | http://localhost:3737/docs |
| PostgreSQL | 5432 | -- |
| Redis | 6379 | -- |
| Ollama | 11434 | http://localhost:11434 |
| Prometheus | 9090 | http://localhost:9090 |
| Grafana | 3000 | http://localhost:3000 |
| Debugpy | 5678 | -- |
