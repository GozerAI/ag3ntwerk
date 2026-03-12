# ag3ntwerk Troubleshooting Runbook

## Quick Diagnostics

### 1. Check Overall Health

```bash
# Health endpoint
curl -s http://localhost:3737/health | jq

# Kubernetes pod status
kubectl get pods -n ag3ntwerk -o wide

# Recent events
kubectl get events -n ag3ntwerk --sort-by='.lastTimestamp' | tail -20
```

### 2. Check Logs

```bash
# Kubernetes - all pods
kubectl logs -l app.kubernetes.io/name=ag3ntwerk -n ag3ntwerk --tail=100

# Kubernetes - specific pod
kubectl logs ag3ntwerk-xxx-yyy -n ag3ntwerk --tail=100

# Docker
docker-compose logs --tail=100 ag3ntwerk

# Search for errors
kubectl logs -l app.kubernetes.io/name=ag3ntwerk -n ag3ntwerk | grep -i error
```

### 3. Check Resource Usage

```bash
# Kubernetes
kubectl top pods -n ag3ntwerk
kubectl top nodes

# Docker
docker stats ag3ntwerk-api
```

---

## Common Issues

### High Latency

**Symptoms**: Response times exceed SLO thresholds

**Diagnosis**:
```bash
# Check current latency
curl -w "@curl-format.txt" -s http://localhost:3737/health

# Check database connection pool
kubectl exec -it ag3ntwerk-xxx -n ag3ntwerk -- python -c "
from ag3ntwerk.persistence.database import get_database
import asyncio
async def check():
    db = await get_database()
    # Check pool stats
asyncio.run(check())
"
```

**Resolution**:
1. Scale up replicas if CPU > 70%
2. Check database query performance
3. Verify LLM provider latency
4. Check for network issues

### High Error Rate

**Symptoms**: 5xx errors > 0.1%

**Diagnosis**:
```bash
# Check error logs
kubectl logs -l app.kubernetes.io/name=ag3ntwerk -n ag3ntwerk | grep -E "(ERROR|Exception|Traceback)"

# Check metrics for error patterns
curl http://localhost:3737/metrics | grep -E "(error|exception)"
```

**Resolution**:
1. Identify error type from logs
2. Check for resource exhaustion
3. Verify external service availability
4. Check for recent deployments

### Memory Issues

**Symptoms**: OOMKilled, increasing memory usage

**Diagnosis**:
```bash
# Check memory usage
kubectl top pods -n ag3ntwerk

# Check for memory trends
kubectl describe pod ag3ntwerk-xxx -n ag3ntwerk | grep -A5 "Memory"
```

**Resolution**:
1. Increase memory limits
2. Reduce connection pool size
3. Check for memory leaks (long-running requests)
4. Restart pods to clear memory

### Database Connection Issues

**Symptoms**: "Cannot connect to database" errors

**Diagnosis**:
```bash
# Test database connectivity
kubectl exec -it ag3ntwerk-xxx -n ag3ntwerk -- python -c "
import socket
s = socket.socket()
s.settimeout(5)
try:
    s.connect(('$PG_HOST', 5432))
    print('Connection successful')
except Exception as e:
    print(f'Connection failed: {e}')
finally:
    s.close()
"

# Check PostgreSQL status
psql -h $PG_HOST -U $PG_USER -c "SELECT 1"
```

**Resolution**:
1. Verify database is running
2. Check network policies/security groups
3. Verify credentials are correct
4. Check connection pool exhaustion
5. Restart database if needed

### LLM Provider Issues

**Symptoms**: Slow or failed AI completions

**Diagnosis**:
```bash
# Check LLM provider connectivity
curl -s https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY" | head

# For Ollama
curl -s http://localhost:11434/api/tags
```

**Resolution**:
1. Verify API key is valid
2. Check provider status page
3. Fallback to alternate provider
4. Implement request retry with backoff

### Pod Stuck in Pending

**Symptoms**: Pod status shows "Pending"

**Diagnosis**:
```bash
# Check events
kubectl describe pod ag3ntwerk-xxx -n ag3ntwerk | grep -A20 "Events:"

# Check node resources
kubectl describe nodes | grep -A5 "Allocated resources"
```

**Resolution**:
1. Check for resource constraints
2. Verify node has available capacity
3. Check PersistentVolumeClaim status
4. Review node selectors/affinity rules

### Pod CrashLoopBackOff

**Symptoms**: Pod keeps restarting

**Diagnosis**:
```bash
# Check previous container logs
kubectl logs ag3ntwerk-xxx -n ag3ntwerk --previous

# Check exit code
kubectl describe pod ag3ntwerk-xxx -n ag3ntwerk | grep -A5 "Last State"
```

**Resolution**:
1. Check for configuration errors
2. Verify required secrets exist
3. Check for missing dependencies
4. Review liveness probe configuration

---

## Debugging Commands

### Interactive Shell

```bash
# Kubernetes
kubectl exec -it ag3ntwerk-xxx -n ag3ntwerk -- /bin/bash

# Docker
docker exec -it ag3ntwerk-api /bin/bash
```

### Python Debug Console

```bash
kubectl exec -it ag3ntwerk-xxx -n ag3ntwerk -- python -c "
from ag3ntwerk.core.config import get_config
config = get_config()
print(config.to_dict())
"
```

### Network Debugging

```bash
# Install debugging tools
kubectl exec -it ag3ntwerk-xxx -n ag3ntwerk -- apt-get update && apt-get install -y curl netcat dnsutils

# Test DNS resolution
kubectl exec -it ag3ntwerk-xxx -n ag3ntwerk -- nslookup ag3ntwerk-postgresql

# Test TCP connectivity
kubectl exec -it ag3ntwerk-xxx -n ag3ntwerk -- nc -zv ag3ntwerk-postgresql 5432
```

### Database Queries

```bash
# Connect to PostgreSQL
kubectl exec -it ag3ntwerk-postgresql-0 -n ag3ntwerk -- psql -U ag3ntwerk -d ag3ntwerk

# Check active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'ag3ntwerk';

# Check long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 seconds';
```

---

## Escalation

### When to Escalate

- Error rate > 1% for 10+ minutes
- Complete service outage
- Data corruption suspected
- Security incident
- Error budget exhausted

### Escalation Contacts

| Severity | Response Time | Contact |
|----------|---------------|---------|
| Critical | 15 minutes | On-call engineer |
| High | 1 hour | Team lead |
| Medium | 4 hours | Relevant team |

### Information to Gather

1. When did the issue start?
2. What changed recently? (deployments, config changes)
3. What is the impact? (users affected, errors/min)
4. What troubleshooting has been done?
5. Relevant log snippets and metrics screenshots
