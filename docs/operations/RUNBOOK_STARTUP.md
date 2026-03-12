# ag3ntwerk Startup Runbook

## Prerequisites

Before starting ag3ntwerk, ensure:

1. **Database is running and accessible**
   ```bash
   # PostgreSQL
   pg_isready -h $PG_HOST -p $PG_PORT -U $PG_USER -d $PG_DATABASE

   # SQLite (check directory exists)
   ls -la ~/.ag3ntwerk/data/
   ```

2. **Required environment variables are set**
   ```bash
   # Minimum required for production
   export ENVIRONMENT=production
   export DATABASE_BACKEND=postgresql
   export PG_HOST=your-db-host
   export PG_PORT=5432
   export PG_DATABASE=ag3ntwerk
   export PG_USER=ag3ntwerk
   export PG_PASSWORD=your-secure-password
   export AGENTWERK_SECRETS_KEY=your-encryption-key
   ```

3. **Database migrations are applied**
   ```bash
   alembic upgrade head
   ```

## Startup Procedures

### Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Start with hot reload
python -m uvicorn ag3ntwerk.api.app:app --host 0.0.0.0 --port 3737 --reload
```

### Docker Compose

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose logs -f ag3ntwerk
```

### Kubernetes

```bash
# Apply manifests (using kustomize)
kubectl apply -k deploy/kubernetes/overlays/prod

# Or using Helm
helm upgrade --install ag3ntwerk deploy/helm/ag3ntwerk \
  --namespace ag3ntwerk \
  --set secrets.create=true \
  --set-string secrets.database.password=$PG_PASSWORD \
  --set-string secrets.encryptionKey=$AGENTWERK_SECRETS_KEY \
  --set config.database.host=$PG_HOST

# Watch rollout
kubectl rollout status deployment/ag3ntwerk -n ag3ntwerk
```

## Health Verification

### 1. Check Pod Status (Kubernetes)

```bash
kubectl get pods -n ag3ntwerk
# All pods should show Running and Ready

kubectl describe pod -l app.kubernetes.io/name=ag3ntwerk -n ag3ntwerk
# Check Events for any issues
```

### 2. Check Health Endpoint

```bash
# Local/Docker
curl http://localhost:3737/health

# Kubernetes (port-forward)
kubectl port-forward svc/ag3ntwerk 3737:80 -n ag3ntwerk
curl http://localhost:3737/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "checks": {
    "database": "ok",
    "llm": "ok"
  }
}
```

### 3. Check Logs

```bash
# Docker
docker-compose logs --tail=100 ag3ntwerk

# Kubernetes
kubectl logs -l app.kubernetes.io/name=ag3ntwerk -n ag3ntwerk --tail=100
```

Look for:
- ✅ "Configuration validated successfully"
- ✅ "Database initialized"
- ✅ "Application startup complete"

Watch for:
- ❌ "Configuration validation failed"
- ❌ "Cannot connect to database"
- ❌ "Migration pending"

### 4. Verify API Endpoints

```bash
# OpenAPI docs
curl http://localhost:3737/docs

# Metrics (if enabled)
curl http://localhost:3737/metrics

# Agent status
curl http://localhost:3737/api/v1/agents/status
```

## Troubleshooting Startup Issues

### Database Connection Failed

**Symptoms**: "Cannot connect to PostgreSQL" in logs

**Resolution**:
1. Verify database is running: `pg_isready -h $PG_HOST -p $PG_PORT`
2. Check credentials: `psql -h $PG_HOST -U $PG_USER -d $PG_DATABASE`
3. Verify network connectivity from pod/container
4. Check firewall rules allow port 5432

### Migration Errors

**Symptoms**: "alembic.util.exc.CommandError" in logs

**Resolution**:
1. Check current migration state: `alembic current`
2. Check for pending migrations: `alembic history`
3. Run migrations manually: `alembic upgrade head`
4. If corrupted, check `alembic_version` table

### Configuration Validation Failed

**Symptoms**: "Configuration validation failed" with specific errors

**Resolution**:
1. Check all required environment variables are set
2. Verify LLM provider API key is valid
3. Ensure log level is valid (DEBUG, INFO, WARNING, ERROR)
4. Check CORS origins format

### Out of Memory

**Symptoms**: OOMKilled, container restarts

**Resolution**:
1. Increase memory limits in deployment
2. Check for memory leaks in application
3. Reduce worker count or connection pool size
4. Enable swap (not recommended for production)

## Rollback Procedures

### Quick Rollback (Kubernetes)

```bash
# Rollback to previous revision
kubectl rollout undo deployment/ag3ntwerk -n ag3ntwerk

# Rollback to specific revision
kubectl rollout undo deployment/ag3ntwerk -n ag3ntwerk --to-revision=2

# Check rollout history
kubectl rollout history deployment/ag3ntwerk -n ag3ntwerk
```

### Helm Rollback

```bash
# List revisions
helm history ag3ntwerk -n ag3ntwerk

# Rollback
helm rollback ag3ntwerk 2 -n ag3ntwerk
```

### Database Rollback

```bash
# Downgrade one migration
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade abc123

# Check current state
alembic current
```

## Post-Startup Checklist

- [ ] Health endpoint returns 200
- [ ] All pods are Running and Ready
- [ ] No errors in application logs
- [ ] Database connectivity verified
- [ ] Metrics endpoint accessible (if enabled)
- [ ] API documentation accessible at /docs
- [ ] Load balancer health checks passing
- [ ] Monitoring dashboards showing data
- [ ] Alerting configured and tested
