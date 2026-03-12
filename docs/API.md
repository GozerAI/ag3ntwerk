# ag3ntwerk API Reference

This document provides a comprehensive reference for the ag3ntwerk Command Center REST API.

## Base URL

```
http://localhost:3737
```

Most resource endpoints are prefixed with `/api/v1`. Health, metrics, and learning routes live at the root or under their own prefixes.

## Authentication

ag3ntwerk supports two authentication methods. Authentication is **optional by default** and can be enforced by setting the environment variable `AGENTWERK_AUTH_REQUIRED=true`.

### API Key Authentication

Include your API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: cskey_your_api_key_here" http://localhost:3737/api/v1/status
```

### JWT Bearer Token

Include a JWT token in the Authorization header:

```bash
curl -H "Authorization: Bearer your_jwt_token" http://localhost:3737/api/v1/status
```

### Permissions

When authentication is enabled, endpoints may require specific permissions:

| Permission | Description |
|------------|-------------|
| `READ` | Read-only access |
| `WRITE` | Create/update resources |
| `EXECUTE_TASK` | Execute tasks and approve actions |
| `EXECUTE_WORKFLOW` | Execute workflows |
| `ADMIN` | Administrative operations (start/stop Nexus, fleet enrollment, etc.) |

---

## Health & Status

### GET /api

API root information.

**Response:**
```json
{
  "name": "ag3ntwerk Command Center",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs"
}
```

### GET /health

Basic health check (Kubernetes liveness probe compatible).

**Response:**
```json
{
  "status": "healthy",
  "llm_connected": true,
  "coo_ready": true,
  "timestamp": "2025-01-15T10:30:00"
}
```

### GET /health/live

Kubernetes liveness probe. Returns `200` with `{"status": "alive"}` or `503` with `{"status": "dead"}`.

### GET /health/ready

Kubernetes readiness probe. Returns `200` with `{"status": "ready"}` or `503` with `{"status": "not_ready"}`.

### GET /health/detailed

Aggregated health from all subsystems. Returns `200` (healthy/degraded) or `503` (unhealthy).

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| force_refresh | bool | Bypass health cache (default: false) |

### GET /metrics

Returns a JSON summary of collected metrics (request counts, task durations, etc.).

### GET /api/v1/status

Comprehensive system status.

**Response:**
```json
{
  "initialized": true,
  "llm_connected": true,
  "coo_ready": true,
  "agents": [
    {"code": "Nexus", "codename": "Nexus", "available": true},
    {"code": "Forge", "codename": "Forge", "available": true}
  ],
  "tasks": {
    "total": 50,
    "pending": 5,
    "completed": 40
  },
  "websocket_clients": 2,
  "timestamp": "2025-01-15T10:30:00"
}
```

---

## Agents

### GET /api/v1/agents

List all available ag3ntwerk agents.

**Response:**
```json
{
  "agents": [
    {"code": "Nexus", "codename": "Nexus", "available": true},
    {"code": "Forge", "codename": "Forge", "available": true},
    {"code": "Keystone", "codename": "Keystone", "available": true},
    {"code": "Echo", "codename": "Vox", "available": true},
    {"code": "Sentinel", "codename": "Sentinel", "available": true}
  ],
  "count": 5
}
```

---

## Tasks

### GET /api/v1/tasks

List all tasks.

**Response:**
```json
{
  "tasks": [
    {
      "id": "task_abc123",
      "description": "Analyze Q1 sales data",
      "task_type": "general",
      "priority": "medium",
      "status": "completed",
      "created_at": "2025-01-15T10:30:00"
    }
  ],
  "count": 1
}
```

### POST /api/v1/tasks

Create and execute a new task. Requires `EXECUTE_TASK` permission when auth is enabled.

**Request Body:**
```json
{
  "description": "Analyze the security of the authentication module",
  "task_type": "security_analysis",
  "priority": "high",
  "context": {
    "target_module": "auth",
    "depth": "comprehensive"
  }
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| description | string | Yes | Task description (1-10000 chars) |
| task_type | string | No | Type of task, lowercase with underscores (default: `general`) |
| priority | string | No | `low`, `medium`, `high`, or `critical` (default: `medium`) |
| context | object | No | Additional context (max 100KB serialized, max 10 levels deep) |

**Response:**
```json
{
  "id": "task_abc123",
  "description": "Analyze the security of the authentication module",
  "task_type": "security_analysis",
  "priority": "high",
  "status": "completed",
  "context": {},
  "result": {"summary": "Analysis complete", "findings": []},
  "routed_to": "Sentinel",
  "created_at": "2025-01-15T10:30:00"
}
```

---

## Dashboard

### GET /api/v1/dashboard/stats

Get dashboard statistics.

**Response:**
```json
{
  "tasks": {
    "total": 500,
    "active": 10,
    "completed": 450
  },
  "goals": {
    "total": 5,
    "active": 3
  },
  "memory": {"total_chunks": 0},
  "knowledge": {"total_entities": 0, "total_facts": 0},
  "decisions": {"total": 0},
  "coo": {
    "state": "running",
    "mode": "supervised"
  },
  "timestamp": "2025-01-15T10:30:00"
}
```

---

## Nexus (Overwatch)

The Nexus endpoints control the Overwatch agent (codename Nexus) which serves as the central coordination layer.

### GET /api/v1/coo/status

Get Nexus status including mode, uptime, and execution statistics.

### POST /api/v1/coo/start

Start the Nexus agent. Requires `ADMIN` permission.

**Response:**
```json
{"success": true, "message": "Nexus started"}
```

### POST /api/v1/coo/stop

Stop the Nexus agent. Requires `ADMIN` permission.

### POST /api/v1/coo/mode

Set the Nexus operating mode. Requires `ADMIN` permission.

**Request Body:**
```json
{"mode": "supervised"}
```

**Valid modes:** `autonomous`, `supervised`, `approval`, `observe`, `paused`

### GET /api/v1/coo/suggestions

Get the next suggested action from the Nexus.

### POST /api/v1/coo/suggestions/{id}/approve

Approve and execute a Nexus suggestion. Requires `EXECUTE_TASK` permission.

### POST /api/v1/coo/suggestions/{id}/reject

Reject a Nexus suggestion. Requires `EXECUTE_TASK` permission.

---

## Agenda Engine

The Autonomous Agenda Engine is a subsystem of the Nexus that generates, prioritizes, and executes work items toward goals. All agenda endpoints require the Nexus to be running (return `503` otherwise).

### GET /api/v1/coo/agenda

Get the current agenda status.

### POST /api/v1/coo/agenda/generate

Generate a new autonomous agenda.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| period_hours | int | Duration of agenda period, 1-168 (default: 24) |

### GET /api/v1/coo/agenda/items

Get agenda items.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| count | int | Max items to return, 1-50 (default: 10) |
| include_awaiting_approval | bool | Include items awaiting approval (default: true) |

### POST /api/v1/coo/agenda/items/{item_id}/execute

Execute a specific agenda item. Requires `EXECUTE_TASK` permission.

### POST /api/v1/coo/agenda/items/{item_id}/approve

Approve an agenda item for execution. Requires `EXECUTE_TASK` permission.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| notes | string | Optional approval notes (max 500 chars) |

### POST /api/v1/coo/agenda/items/{item_id}/reject

Reject an agenda item. Requires `EXECUTE_TASK` permission.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| reason | string | Required rejection reason (1-500 chars) |

### GET /api/v1/coo/agenda/obstacles

Get obstacles identified by the agenda engine.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| goal_id | string | Filter by goal ID |
| status | string | Filter by status (`active`, `resolved`) |

### GET /api/v1/coo/agenda/strategies

Get strategies generated by the agenda engine.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| obstacle_id | string | Filter by obstacle ID |

### GET /api/v1/coo/agenda/workstreams

Get workstreams from the agenda engine.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| goal_id | string | Filter by goal ID |

### POST /api/v1/coo/agenda/batch-approve

Batch approve multiple agenda items. Requires `EXECUTE_TASK` permission.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| item_ids | list[string] | List of item IDs to approve (1-50) |

---

## Goals

### GET /api/v1/goals

List all goals.

### POST /api/v1/goals

Create a new goal. Requires `WRITE` permission.

**Request Body:**
```json
{
  "title": "Increase monthly revenue by 20%",
  "description": "Focus on upselling existing customers and acquiring new enterprise clients",
  "milestones": [
    {"title": "Complete market analysis"},
    {"title": "Launch upsell campaign"}
  ]
}
```

### GET /api/v1/goals/{goal_id}

Get a specific goal by ID.

### PUT /api/v1/goals/{goal_id}

Update a goal. Requires `WRITE` permission.

**Request Body:**
```json
{
  "title": "Updated title",
  "status": "completed",
  "progress": 100.0
}
```

**Valid statuses:** `active`, `completed`, `abandoned`, `paused`

### POST /api/v1/goals/{goal_id}/milestones

Add a milestone to a goal. Requires `WRITE` permission.

**Request Body:**
```json
{"title": "New milestone"}
```

### PUT /api/v1/goals/{goal_id}/milestones/{milestone_id}

Update a milestone status. Requires `WRITE` permission.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | `pending` or `completed` |

---

## Memory & Knowledge

### GET /api/v1/memory/search

Search the memory/knowledge base.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| query | string | Search query (1-1000 chars, required) |
| n_results | int | Number of results, 1-100 (default: 10) |

**Response:**
```json
{
  "results": [
    {"content": "...", "score": 0.95, "metadata": {}}
  ],
  "query": "authentication patterns",
  "count": 3
}
```

### GET /api/v1/memory/stats

Get memory/knowledge statistics.

---

## Chat

### POST /api/v1/chat

Chat with a ag3ntwerk agent. Requires `WRITE` permission.

**Request Body:**
```json
{
  "message": "What are the current project priorities?",
  "agent": "Nexus"
}
```

**Valid agents:** `Overwatch`, `Nexus`, `Forge`, `Keystone`, `Echo`, `Blueprint`, `Beacon`, `Sentinel`, `Axiom`, `Compass`, `Index`, `Vector`, `Accord`, `Aegis`, `Foundry`, `Citadel`

---

## Workflows

### GET /api/v1/workflows

List all available workflows.

**Response:**
```json
{
  "workflows": [
    {
      "name": "product_launch",
      "description": "Coordinate a product launch across teams",
      "steps": 5
    }
  ],
  "count": 1
}
```

### GET /api/v1/workflows/{workflow_name}

Get details about a specific workflow including its steps.

**Response:**
```json
{
  "name": "product_launch",
  "description": "Coordinate a product launch across teams",
  "steps": [
    {
      "name": "market_analysis",
      "agent": "Echo",
      "task_type": "market_analysis",
      "description": "Analyze market positioning",
      "required": true,
      "depends_on": []
    }
  ],
  "step_count": 5
}
```

### POST /api/v1/workflows/execute

Execute a workflow. Requires `EXECUTE_WORKFLOW` permission.

**Request Body:**
```json
{
  "workflow_name": "product_launch",
  "params": {
    "product_name": "New Feature",
    "target_date": "2025-02-01"
  }
}
```

### GET /api/v1/workflows/history

Get recent workflow execution history.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| limit | int | Max results, 1-100 (default: 10) |

### GET /api/v1/workflows/executions/{workflow_id}

Get details of a specific workflow execution by its ID.

---

## Workflow Library

Analytics and management for the harvested workflow library. These endpoints share the `/api/v1/workflows` prefix.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/workflows/stats` | Aggregate library statistics |
| GET | `/api/v1/workflows/stats/by-tool` | Breakdown by tool type |
| GET | `/api/v1/workflows/stats/quality-trends` | Quality score trends by month |
| GET | `/api/v1/workflows/stats/deployments` | Deployment counts and success rates |
| GET | `/api/v1/workflows/stats/popular` | Most deployed/recommended workflows |
| GET | `/api/v1/workflows/stats/recommendations` | Recommendation effectiveness |
| GET | `/api/v1/workflows/stats/harvest-runs` | Recent harvest run history |
| GET | `/api/v1/workflows/{workflow_id}/similar` | Find similar workflows by vector embedding |

---

## WebSocket

### WS /ws

Real-time event stream. Connects to receive live updates about task completions, Nexus events, webhook events, and more.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:3737/ws');
// With optional token authentication:
const ws = new WebSocket('ws://localhost:3737/ws?token=your_token');
```

WebSocket authentication is controlled by `AGENTWERK_WEBSOCKET_AUTH_ENABLED` (default: `false`).

**Message format (server to client):**
```json
{
  "type": "connected",
  "data": {"message": "Connected to ag3ntwerk Command Center"},
  "timestamp": "2025-01-15T10:30:00"
}
```

**Ping/pong:**
```json
// Client sends:
{"type": "ping"}
// Server responds:
{"type": "pong", "timestamp": "2025-01-15T10:30:00"}
```

**Event types broadcast through WebSocket:**
- `task_created`, `task_completed`, `task_failed`
- `coo_started`, `coo_stopped`
- `gumroad_sale`, `gumroad_refund`
- `twitter_mention`, `twitter_follow`
- `linkedin_engagement`

---

## Webhooks

Endpoints for receiving external webhook events from third-party platforms.

### POST /webhooks/gumroad/{event_type}

Receive Gumroad webhook events (form-encoded data). Supported event types: `sale`, `refund`, `cancelled_subscription`, `subscription_updated`.

### GET /webhooks/twitter

Twitter CRC challenge-response check (query param: `crc_token`).

### POST /webhooks/twitter

Receive Twitter Account Activity webhook events (mentions, likes, follows, DMs).

### POST /webhooks/linkedin

Receive LinkedIn webhook events (likes, comments, shares, mentions).

---

## Content Pipeline

Manage content pieces, distribution pipelines, and distribution history.

**Prefix:** `/api/v1/content`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/pieces` | List content pieces (filter by format) |
| POST | `/pieces` | Create a content piece |
| GET | `/pieces/{id}` | Get a content piece |
| DELETE | `/pieces/{id}` | Delete a content piece |
| POST | `/pieces/{id}/distribute` | Mark content as distributed to a platform |
| GET | `/pipeline/executions` | List pipeline executions |
| POST | `/pipeline/start` | Start a content distribution pipeline |
| GET | `/pipeline/executions/{id}` | Get pipeline execution details |
| POST | `/pipeline/executions/{id}/advance` | Advance pipeline to next step |
| POST | `/pipeline/executions/{id}/cancel` | Cancel a pipeline execution |
| GET | `/distribution/history` | Get distribution history |
| GET | `/stats` | Get content pipeline statistics |

---

## Interviews

AI-guided interview management: scripts, sessions, and results.

**Prefix:** `/api/v1/interviews`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/scripts` | List interview scripts |
| POST | `/scripts` | Create an interview script |
| GET | `/scripts/{id}` | Get a specific script |
| DELETE | `/scripts/{id}` | Delete a script |
| GET | `/sessions` | List all interview sessions |
| POST | `/sessions` | Start a new session from a script |
| GET | `/sessions/{id}` | Get session details |
| POST | `/sessions/{id}/answer` | Submit a text answer |
| POST | `/sessions/{id}/answer/audio` | Submit an audio answer (placeholder) |
| POST | `/sessions/{id}/finish` | Finish session and extract insights |
| POST | `/sessions/{id}/cancel` | Cancel a session |
| GET | `/results` | List interview results |
| GET | `/results/{session_id}` | Get full interview result |
| GET | `/results/{session_id}/transcript` | Get transcript only |

---

## Voice & Transcription

Audio transcription powered by Whisper.

**Prefix:** `/api/v1/voice`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | Whisper service status and supported formats |
| POST | `/transcribe` | Upload and transcribe an audio file |
| GET | `/transcriptions` | List recent transcriptions |
| GET | `/transcriptions/{id}` | Get a specific transcription |
| POST | `/transcribe-for-interview` | Transcribe audio for an interview session |

Supported audio formats: `wav`, `mp3`, `ogg`, `webm`, `m4a`, `flac`. Max file size: 25MB.

---

## Modules

### Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/modules/` | List all autonomous modules |
| GET | `/api/v1/modules/status` | Status of all module services |

### Trends Module

**Prefix:** `/api/v1/modules/trends`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Module overview and stats |
| POST | `/analyze` | Run trend analysis cycle |
| GET | `/trending` | Get trending topics (filter by category, min_score, limit) |
| GET | `/opportunities` | Get niche opportunities |
| GET | `/correlations` | Get trend correlations |
| GET | `/report/{executive_code}` | Agent-tailored trend report |

### Commerce Module

**Prefix:** `/api/v1/modules/commerce`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Module overview and stats |
| GET | `/storefronts` | List all storefronts |
| GET | `/storefronts/{id}` | Get storefront details |
| GET | `/storefronts/{id}/products` | Get products from a storefront |
| GET | `/analytics` | Cross-storefront analytics |
| GET | `/margins` | Margin analysis |
| GET | `/inventory/alerts` | Inventory alerts |
| POST | `/pricing/optimize/{storefront_id}` | Pricing optimization recommendations |
| GET | `/report/{executive_code}` | Agent-tailored commerce report |

### Brand Module

**Prefix:** `/api/v1/modules/brand`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Module overview and stats |
| GET | `/identity` | Get current brand identity |
| POST | `/identity` | Create brand identity |
| POST | `/validate` | Validate content against brand guidelines |
| POST | `/consistency` | Check brand consistency across samples |
| GET | `/guidelines` | Get brand guidelines (filter by category) |
| POST | `/guidelines` | Add a brand guideline |
| GET | `/kit` | Get complete brand kit |
| GET | `/report/{executive_code}` | Agent-tailored brand report |

### Scheduler Module

**Prefix:** `/api/v1/modules/scheduler`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Module overview and stats |
| GET | `/tasks` | List scheduled tasks (filter by owner, category, status) |
| POST | `/tasks` | Schedule a new task |
| POST | `/tasks/template/{template_name}` | Schedule from a template |
| POST | `/tasks/{task_id}/run` | Run a task immediately |
| POST | `/tasks/{task_id}/enable` | Enable a paused task |
| POST | `/tasks/{task_id}/disable` | Disable a task |
| GET | `/workflows` | List available workflows |
| POST | `/workflows/{workflow_id}/execute` | Execute a workflow |
| POST | `/autonomous-cycle` | Run autonomous operational cycle |
| GET | `/report/{executive_code}` | Agent-tailored scheduler report |

### Workbench Module

**Prefix:** `/api/v1/modules/workbench`

Development environment management with sandboxed runtimes, IDE integration, and deployment pipelines.

**Workspace Management:**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Module overview |
| GET | `/health` | Service health check |
| GET | `/stats` | Workbench statistics |
| POST | `/workspaces` | Create a workspace |
| GET | `/workspaces` | List workspaces (filter by status, runtime) |
| GET | `/workspaces/{id}` | Get workspace details |
| DELETE | `/workspaces/{id}` | Delete a workspace |
| POST | `/workspaces/{id}/start` | Start workspace runtime container |
| POST | `/workspaces/{id}/stop` | Stop workspace runtime container |

**Command Execution:**
| Method | Path | Description |
|--------|------|-------------|
| POST | `/workspaces/{id}/run` | Run command (async, returns run_id) |
| POST | `/workspaces/{id}/run/sync` | Run command and wait for completion |
| GET | `/runs/{run_id}` | Get command execution result |
| GET | `/runs/{run_id}/logs` | Get command execution logs |

**File Operations:**
| Method | Path | Description |
|--------|------|-------------|
| POST | `/workspaces/{id}/files` | Write files to workspace |
| GET | `/workspaces/{id}/files` | List files (glob pattern) |
| POST | `/workspaces/{id}/files/read` | Read files from workspace |

**IDE Integration (code-server):**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/workspaces/{id}/ide` | Get IDE URL |
| POST | `/workspaces/{id}/ide/start` | Start browser IDE |
| POST | `/workspaces/{id}/ide/stop` | Stop browser IDE |
| GET | `/workspaces/{id}/ide/status` | Get IDE status |

**Deployment:**
| Method | Path | Description |
|--------|------|-------------|
| POST | `/workspaces/{id}/deploy/oneclick` | One-click deploy (auto-detect and deploy) |
| GET | `/workspaces/{id}/deploy/preview` | Preview what deployment would do |
| POST | `/deploy/vercel` | Deploy to Vercel |
| POST | `/deploy/docker` | Build and push to Docker registry |

**Code Pipelines:**
| Method | Path | Description |
|--------|------|-------------|
| POST | `/pipeline/evaluate` | Code evaluation only |
| POST | `/pipeline/full` | Full pipeline: Evaluate, Correct, Secure, Test, Build, Deploy |
| POST | `/pipeline/with-database` | Full pipeline + database provisioning |
| POST | `/pipeline/with-secrets` | Full pipeline + secrets management |
| POST | `/pipeline/complete` | Complete pipeline: Code + Database + Secrets + Deploy |
| GET | `/pipeline/{id}/status` | Get pipeline execution status |
| GET | `/pipeline/{id}/logs` | Get pipeline execution logs |
| POST | `/pipeline/{id}/cancel` | Cancel a running pipeline |

---

## Automation

### Research Automation

**Prefix:** `/api/v1/automation/research`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Module overview and status |
| POST | `/market-scan` | Run autonomous market intelligence scan |
| POST | `/competitive-analysis` | Run competitive intelligence analysis |
| POST | `/trend-research` | Run trend deep research |
| POST | `/technology-scan` | Run technology radar scan |
| GET | `/history` | Get research execution history |
| GET | `/insights` | Get aggregated insights from recent research |
| POST | `/schedule` | Schedule recurring research |
| POST | `/run-recurring` | Execute all due recurring research |

### Data Harvesting

**Prefix:** `/api/v1/automation/harvesting`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Module overview and status |
| POST | `/sources` | Register a new data source |
| DELETE | `/sources/{name}` | Remove a data source |
| GET | `/sources` | List all registered data sources |
| POST | `/harvest` | Execute a harvest cycle |
| GET | `/history` | Get harvest execution history |
| GET | `/quality` | Get data quality metrics |
| POST | `/schedule` | Schedule recurring harvesting |

### Security Automation

**Prefix:** `/api/v1/automation/security`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Module overview and security posture |
| POST | `/scan` | Run autonomous security scan |
| GET | `/threat-assessment` | Get current threat assessment |
| GET | `/posture` | Get detailed security posture report |
| GET | `/alerts` | Get security alert history |
| POST | `/alerts/acknowledge` | Acknowledge and resolve an alert |
| GET | `/compliance` | Get compliance audit status |
| POST | `/full-audit` | Run comprehensive security audit |
| POST | `/incident-response` | Trigger automated incident response |
| POST | `/access-review` | Run automated access review |
| POST | `/monitoring/schedule` | Configure continuous monitoring schedule |

---

## Fleet Orchestration

Distributed fleet management: network discovery, device enrollment, resource profiling, workload distribution, deployment planning, and relay management.

**Prefix:** `/api/v1/fleet`

### Fleet Status & Nodes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Fleet overview and status |
| POST | `/initialize` | Initialize fleet and profile controller |
| GET | `/health` | Run health check across all nodes |
| GET | `/nodes` | List all fleet nodes |
| DELETE | `/nodes/{node_id}` | Remove a node from the fleet |
| GET | `/events` | Get fleet event log |

### Network Discovery

| Method | Path | Description |
|--------|------|-------------|
| POST | `/discover` | Discover devices on a network CIDR |
| GET | `/discover/devices` | Get all discovered devices |
| GET | `/discover/targets` | List configured scan targets |
| POST | `/discover/targets` | Add a new scan target |
| GET | `/discover/history` | Get network scan history |

### Enrollment & Provisioning

| Method | Path | Description |
|--------|------|-------------|
| POST | `/enroll` | Enroll a discovered device (requires explicit approval) |
| POST | `/reject` | Reject a device from enrollment |
| POST | `/provision` | Provision an enrolled node |
| GET | `/provision/manifest` | Get the standard provisioning manifest |
| GET | `/provision/plans` | List provisioning plans |
| GET | `/provision/history` | Get provisioning history |

### Resources

| Method | Path | Description |
|--------|------|-------------|
| GET | `/resources` | Aggregate fleet resource summary |
| GET | `/resources/profiles` | Resource profiles for all nodes |
| GET | `/resources/{node_id}` | Resource profile for a specific node |
| GET | `/resources/search/{workload_type}` | Find suitable nodes for a workload type |

### Workloads

| Method | Path | Description |
|--------|------|-------------|
| POST | `/workloads` | Submit a workload for distributed execution |
| POST | `/workloads/complete` | Mark a workload as completed/failed |
| GET | `/workloads/pending` | Get pending workloads |
| GET | `/workloads/active` | Get currently running workloads |
| GET | `/workloads/{id}` | Get workload details |
| GET | `/workloads/stats/summary` | Get allocation statistics |
| POST | `/strategy` | Set fleet-wide allocation strategy |
| GET | `/allocations/history` | Get allocation decision history |
| GET | `/loads` | Get current resource load on all nodes |

### Deployment Plans

| Method | Path | Description |
|--------|------|-------------|
| POST | `/plans/generate` | Generate a deployment plan (review only, nothing executed) |
| GET | `/plans` | List deployment plans |
| GET | `/plans/{plan_id}` | Get plan details |
| GET | `/plans/{plan_id}/guide` | Get plan as human-readable text |
| POST | `/plans/{plan_id}/phases/{phase_id}/approve` | Approve a phase |
| POST | `/plans/{plan_id}/phases/{phase_id}/skip` | Skip a phase |
| POST | `/plans/{plan_id}/phases/{phase_id}/execute` | Execute an approved phase |
| POST | `/plans/{plan_id}/cancel` | Cancel a deployment plan |

### Relay Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/relays/token` | Generate a pre-shared token for a relay agent |
| GET | `/relays` | List all relay agents |
| GET | `/relays/connected` | List actively connected relays |
| GET | `/relays/{relay_id}` | Get relay details |
| GET | `/relays/health` | Check health of all connected relays |
| POST | `/relays/revoke` | Revoke a relay agent's token |
| GET | `/relays/commands` | Get recent command history across relays |
| WS | `/ws/relay` | WebSocket tunnel endpoint for relay agents |

---

## Learning System

The learning system detects patterns, runs experiments, and continuously optimizes agent routing and behavior.

**Prefix:** `/learning`

### Dashboard & Stats

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard` | Aggregated learning dashboard |
| GET | `/stats` | Detailed learning system statistics |

### Patterns

| Method | Path | Description |
|--------|------|-------------|
| GET | `/patterns` | List learned patterns (filter by type, scope, active status) |
| GET | `/patterns/{id}` | Get pattern details |
| POST | `/patterns/{id}/activate` | Activate a pattern |
| POST | `/patterns/{id}/deactivate` | Deactivate a pattern |

### Approvals

| Method | Path | Description |
|--------|------|-------------|
| GET | `/approvals` | List pending approval requests |
| POST | `/approvals/{id}/approve` | Approve a pending action |
| POST | `/approvals/{id}/reject` | Reject a pending action |

### Agent Insights

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents` | Learning insights for all agents |
| GET | `/agents/{code}` | Detailed insight for a specific agent |
| GET | `/agents/{code}/calibration` | Calibration data for an agent |

### Pipeline Control

| Method | Path | Description |
|--------|------|-------------|
| GET | `/pipeline/status` | Get pipeline status |
| POST | `/pipeline/start` | Start continuous learning pipeline |
| POST | `/pipeline/stop` | Stop the pipeline |
| POST | `/pipeline/pause` | Pause the pipeline |
| POST | `/pipeline/resume` | Resume the pipeline |
| POST | `/pipeline/trigger` | Manually trigger a single learning cycle |
| GET | `/pipeline/history` | Get recent pipeline cycle history |

### Experiments

| Method | Path | Description |
|--------|------|-------------|
| GET | `/experiments` | List pattern experiments |
| GET | `/experiments/results` | Get recent experiment results |

### Opportunities & Routing

| Method | Path | Description |
|--------|------|-------------|
| GET | `/opportunities` | List detected improvement opportunities |
| GET | `/routing/decisions` | Get recent routing decisions |
| POST | `/routing/simulate` | Simulate a routing decision |

---

## Error Responses

All error responses follow this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid task description",
    "details": {
      "field": "description",
      "issue": "Must be at least 1 character"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Request validation failed |
| UNAUTHORIZED | 401 | Missing or invalid authentication |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| RATE_LIMITED | 429 | Too many requests |
| SERVICE_UNAVAILABLE | 503 | Service not initialized (e.g., Nexus not running) |
| INTERNAL_ERROR | 500 | Server error |

---

## Rate Limiting

Rate limiting is available when the `slowapi` package is installed. Rate limit information is included in response headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1705320600
```

---

## Request Tracing

Every request receives a unique `X-Request-ID` header in the response. You can also pass your own `X-Request-ID` header to correlate requests across systems.

---

## CORS

Allowed origins: `http://localhost:3000`, `http://localhost:5173`, `http://127.0.0.1:3000`, `http://127.0.0.1:5173`

---

## Interactive Docs

FastAPI auto-generates interactive API documentation:

- **Swagger UI:** [http://localhost:3737/docs](http://localhost:3737/docs)
- **ReDoc:** [http://localhost:3737/redoc](http://localhost:3737/redoc)
- **OpenAPI JSON:** [http://localhost:3737/openapi.json](http://localhost:3737/openapi.json)

---

## SDK Examples

### Python

```python
import httpx

client = httpx.Client(
    base_url="http://localhost:3737",
    headers={"X-API-Key": "your_api_key"}
)

# Submit a task
response = client.post("/api/v1/tasks", json={
    "description": "Analyze codebase security",
    "task_type": "security_analysis",
    "priority": "high"
})
task = response.json()
print(f"Task created: {task['id']}")

# Chat with an agent
response = client.post("/api/v1/chat", json={
    "message": "What are today's priorities?",
    "agent": "Nexus"
})
print(response.json())

# Start the Nexus
client.post("/api/v1/coo/start")

# Generate an agenda
client.post("/api/v1/coo/agenda/generate?period_hours=24")

# Create a goal
client.post("/api/v1/goals", json={
    "title": "Launch v2.0",
    "milestones": [{"title": "Complete beta testing"}]
})
```

### JavaScript

```javascript
const API_BASE = 'http://localhost:3737';
const API_KEY = 'your_api_key';

const headers = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY
};

// Submit a task
const task = await fetch(`${API_BASE}/api/v1/tasks`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    description: 'Review authentication code',
    task_type: 'code_review',
    priority: 'medium'
  })
}).then(r => r.json());

console.log(`Task ID: ${task.id}`);

// WebSocket connection
const ws = new WebSocket(`ws://localhost:3737/ws`);
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log(`Event: ${msg.type}`, msg.data);
};
```

### cURL

```bash
# Check system status
curl http://localhost:3737/api/v1/status

# Submit a task
curl -X POST http://localhost:3737/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "description": "Analyze code quality",
    "task_type": "code_review",
    "priority": "medium"
  }'

# Chat with the Nexus
curl -X POST http://localhost:3737/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Status report", "agent": "Nexus"}'

# Start the Nexus
curl -X POST http://localhost:3737/api/v1/coo/start

# List goals
curl http://localhost:3737/api/v1/goals

# Search memory
curl "http://localhost:3737/api/v1/memory/search?query=authentication&n_results=5"

# Execute a workflow
curl -X POST http://localhost:3737/api/v1/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow_name": "product_launch", "params": {"product_name": "Widget"}}'
```
