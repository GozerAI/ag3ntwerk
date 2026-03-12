# ag3ntwerk Architecture

This document describes the architecture of the ag3ntwerk AI Agent Platform.

## Overview

ag3ntwerk is a hierarchical AI agent orchestration platform that uses a corporate agent metaphor for task routing and execution. The system models an organizational structure where 16 specialized AI "agents" handle domain-specific tasks, coordinated by a Overwatch (Overwatch) layer. An external strategic brain (Nexus / AutonomousCOO) provides high-level directives via a Redis bridge, while the Overwatch handles all internal routing, health monitoring, drift detection, and learning-based optimization.

```
                          ┌──────────────────┐
                          │  Nexus (External) │
                          │  AutonomousCOO    │
                          │  Redis Bridge     │
                          └────────┬─────────┘
                                   │ strategic context / directives
                                   ▼
                          ┌──────────────────┐
                          │   Overwatch (Overwatch) │
                          │   Coordination    │
                          │   Layer           │
                          └────────┬─────────┘
                                   │
        ┌──────────┬──────────┬────┼────┬──────────┬──────────┐
        │          │          │         │          │          │
   ┌────┴───┐ ┌───┴────┐ ┌───┴───┐ ┌───┴───┐ ┌───┴────┐ ┌───┴───┐
   │  Sentinel   │ │  Forge   │ │  Keystone  │ │  Compass  │ │  Echo   │ │  Beacon  │
   │Sentinel│ │ Forge  │ │Keyston│ │Compass│ │  Echo  │ │Beacon │
   └────────┘ └────────┘ └───────┘ └───────┘ └────────┘ └───────┘
        │          │          │         │          │          │
   ┌────┴───┐ ┌───┴────┐ ┌───┴───┐ ┌───┴───┐ ┌───┴────┐ ┌───┴───┐
   │  Axiom   │ │  Index   │ │  Blueprint  │ │ Foundry │ │ Citadel  │ │ Aegis  │
   │ Axiom  │ │ Index  │ │Blueprt│ │Foundry│ │Citadel │ │ Aegis │
   └────────┘ └────────┘ └───────┘ └───────┘ └────────┘ └───────┘
                              │         │          │
                         ┌────┴───┐ ┌───┴────┐ ┌───┴───┐
                         │ Accord  │ │ Vector  │ │  Nexus  │
                         │ Accord │ │ Vector │ │(depr.)│
                         └────────┘ └────────┘ └───────┘
```

## Core Components

### 1. Agent Agents

Each agent is a specialized AI agent with:

- **Domain expertise**: Specific area of focus (security, technology, finance, etc.)
- **Capabilities**: Set of task types it can handle
- **Manager/Specialist hierarchy**: Internal managers and specialists for delegation
- **Codename**: Operational alias used in routing and communication

#### Agent Hierarchy

| Code | Codename | Domain | Notes |
|------|----------|--------|-------|
| Overwatch | Overwatch | Operations, Coordination, Task Routing | Internal coordination layer |
| Sentinel | Sentinel | Information Security Governance | Policies, audits, strategic security |
| Forge | Forge | Development, Engineering, Architecture | Code, testing, DevOps |
| Keystone | Keystone | Finance, Budgeting, Cost Analysis | Financial modeling, ROI |
| Compass | Compass | Strategic Planning, Market Analysis | Strategy, competitive intelligence |
| Axiom | Axiom | Research & Innovation | Deep research, experiments |
| Index | Index | Data Governance, Knowledge Management | Data quality, analytics, documentation |
| Blueprint | Blueprint | Product Strategy, Feature Planning | Roadmap, requirements, specs |
| Echo | Echo | Marketing, Campaigns, Brand | Content, social, demand gen |
| Beacon | Beacon | Customer Success, Feedback | NPS, churn, customer health |
| Foundry | Foundry | Engineering Delivery, Release Management | Sprint, CI/CD, QA |
| Citadel | Citadel | Security Operations | Scanning, incident response, threat hunting |
| Aegis | Aegis | Risk Management | Risk assessment, BCP, threat modeling |
| Accord | Accord | Compliance, Audit, Policy | Regulatory, licensing, ethics |
| Vector | Vector | Revenue Optimization, Growth | Conversion, LTV, expansion revenue |
| Nexus | Nexus | *(Deprecated alias for Overwatch)* | Backward compatibility only |

**16 agents total.** The Nexus package (`src/ag3ntwerk/agents/nexus/`) exists as a deprecated compatibility stub. The true Nexus intelligence lives externally in the Nexus service.

### 2. Agent Class Hierarchy

All agents inherit from the base classes defined in `src/ag3ntwerk/core/base.py`:

```
Agent (ABC)           # Base: code, name, domain, execute(), can_handle(), reason()
  ├── Manager               # Has subordinates, can delegate(), delegate_with_retry()
  │     ├── Overwatch             # Top-level coordinator (Overwatch)
  │     ├── Forge             # Forge - manages ArchitectureManager, CodeQualityManager, etc.
  │     ├── Sentinel             # Sentinel
  │     ├── Keystone             # Keystone
  │     ├── Compass             # Compass
  │     ├── Axiom             # Axiom
  │     ├── Index             # Index
  │     ├── Blueprint             # Blueprint
  │     ├── Echo             # Echo
  │     ├── Beacon             # Beacon
  │     ├── Foundry           # Foundry
  │     ├── Citadel           # Citadel
  │     ├── Aegis            # Aegis
  │     ├── Accord           # Accord
  │     └── Vector           # Vector
  └── Specialist            # Leaf worker: capabilities list, no subordinates
        ├── SeniorDeveloper
        ├── CodeReviewer
        ├── SystemArchitect
        ├── QAEngineer
        ├── DevOpsEngineer
        ├── TechnicalWriter
        └── ... (per-agent specialists)
```

Each agent agent extends `Manager` (not `BaseExecutive`). Agents contain internal managers, and managers contain specialists:

```python
# Example: Forge hierarchy
Forge (Manager)
  ├── ArchitectureManager (Manager)
  │     └── SystemArchitect (Specialist)
  ├── CodeQualityManager (Manager)
  │     ├── SeniorDeveloper (Specialist)
  │     ├── CodeReviewer (Specialist)
  │     └── TechnicalWriter (Specialist)
  ├── TestingManager (Manager)
  │     └── QAEngineer (Specialist)
  └── DevOpsManager (Manager)
        └── DevOpsEngineer (Specialist)
```

### 3. Agent Package Structure

Each agent lives under `src/ag3ntwerk/agents/` as a package:

```
src/ag3ntwerk/agents/
├── __init__.py
├── base_handlers.py         # Shared handler utilities
├── bridges/                 # External service bridges
│   ├── nexus_bridge.py      # Redis bridge to Nexus (AutonomousCOO)
│   ├── forge_bridge.py      # Forge integration bridge
│   └── sentinel_bridge.py   # Sentinel integration bridge
├── cos/                     # Overwatch (Overwatch)
│   ├── agent.py             # Overwatch class - coordination layer
│   ├── managers.py          # WorkflowManager, TaskRoutingManager, ProcessManager, CoordinationManager
│   ├── specialists.py       # WorkflowDesigner, TaskAnalyst, MetricsAnalyst, etc.
│   ├── models.py            # DriftType, DriftSignal, StrategicContext, etc.
│   └── routing_rules.py     # ROUTING_RULES and FALLBACK_ROUTES tables
├── cto/                     # Forge (Forge)
│   ├── agent.py             # Forge class
│   ├── managers.py          # ArchitectureManager, CodeQualityManager, TestingManager, DevOpsManager
│   ├── specialists.py       # SeniorDeveloper, CodeReviewer, SystemArchitect, etc.
│   └── models.py
├── cio/                     # Sentinel (Sentinel)
├── cfo/                     # Keystone (Keystone)
├── cso/                     # Compass (Compass)
├── cro/                     # Axiom (Axiom)
├── cdo/                     # Index (Index)
├── cpo/                     # Blueprint (Blueprint)
├── cmo/                     # Echo (Echo)
├── cco/                     # Beacon (Beacon)
├── cengo/                   # Foundry (Foundry)
├── cseco/                   # Citadel (Citadel)
├── crio/                    # Aegis (Aegis)
├── ccomo/                   # Accord (Accord)
├── crevo/                   # Vector (Vector)
└── coo/                     # Nexus (deprecated alias)
```

Every agent package follows the same convention: `agent.py`, `managers.py`, `specialists.py`, `models.py`.

### 4. Task Routing (5-Phase Pipeline)

Tasks flow through the system via a 5-phase routing pipeline inside the Overwatch:

```
┌──────────────────┐
│  Incoming Task   │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│  PHASE 1: Dynamic (Learning) Routing                 │
│  - Query LearningOrchestrator for routing decision   │
│  - Apply learned patterns and confidence calibration  │
│  - Use if confidence >= 0.6 and not static fallback  │
└────────┬───────────────────────────────┬─────────────┘
         │ (confident)                   │ (not confident / unavailable)
         ▼                               ▼
┌──────────────────┐     ┌──────────────────────────────┐
│  Route to agent  │     │  PHASE 2: Health-Aware        │
│  (learning-      │     │  - Circuit breaker checks     │
│   informed)      │     │  - Health score thresholds    │
└──────────────────┘     │  - Fallback route selection   │
                         └────────┬───────────┬─────────┘
                                  │ (found)   │ (no healthy agent)
                                  ▼           ▼
                    ┌──────────────┐  ┌──────────────────────────┐
                    │ Route to     │  │  PHASE 3: Static Routing  │
                    │ healthy agent│  │  - ROUTING_RULES table    │
                    └──────────────┘  │  - Direct task_type map   │
                                      └────────┬────────┬────────┘
                                               │(found) │(not found)
                                               ▼        ▼
                                 ┌──────────────┐ ┌────────────────────┐
                                 │ Route via    │ │ PHASE 4: Capability│
                                 │ static rules │ │ - can_handle() on  │
                                 └──────────────┘ │   all subordinates │
                                                  └───────┬────┬──────┘
                                                          │    │(multiple)
                                                          │    ▼
                                                          │ ┌──────────────────┐
                                                          │ │ PHASE 5: LLM     │
                                                          │ │ - LLM picks best │
                                                          │ │   from candidates │
                                                          │ └──────────────────┘
                                                          │(single)
                                                          ▼
                                                  ┌──────────────┐
                                                  │ Execute task  │
                                                  └──────────────┘
```

The routing rules live in `src/ag3ntwerk/agents/overwatch/routing_rules.py` and map hundreds of task types to agents, with fallback chains for health-aware rerouting.

### 5. Communication Layer

Agents communicate through a message-based system defined in `src/ag3ntwerk/communication/base.py`:

- **Local mode**: `LocalCommunicator` -- direct in-process method calls for single-instance deployments
- **Distributed mode**: Redis pub/sub for multi-instance deployments

```python
# Message structure
{
    "id": "msg_123",
    "sender": "Overwatch",
    "recipient": "Forge",
    "message_type": "task",        # task, result, query, broadcast
    "payload": {
        "task_id": "csk_abc",
        "description": "Security audit",
        "priority": "high"
    },
    "created_at": "2025-01-15T10:30:00Z",
    "correlation_id": "req_456"
}
```

### 6. Nexus (External Strategic Service)

Nexus is the AutonomousCOO -- an **external** strategic service that communicates with ag3ntwerk via a Redis bridge (`src/ag3ntwerk/agents/bridges/nexus_bridge.py`).

**Nexus provides:**
- Strategic context (routing priorities, SLOs, drift tolerances)
- Performance thresholds and escalation rules
- Cross-system learning and guidance

**Overwatch communicates with Nexus via:**
- `connect_to_nexus(redis_url)` -- establishes Redis pub/sub channel
- `escalate_to_nexus(drift_context)` -- sends drift data, receives updated `StrategicContext`
- `report_outcome_to_nexus(task_result)` -- feeds execution results for cross-system learning
- `sync_context_from_nexus()` -- pulls latest strategic context
- `subscribe_to_nexus_directives(callback)` -- real-time directive subscription
- Nexus can send execution requests that Overwatch routes to appropriate agents

```python
# Connect Overwatch to Nexus
cos = Overwatch(llm_provider=llm)
connected = await cos.connect_to_nexus("redis://localhost:6379")

# Escalate drift
if cos.get_drift_status()["should_escalate"]:
    new_context = await cos.escalate_to_nexus()
```

## System Layers

### API Layer

The API layer is a single FastAPI application with route modules:

```
src/ag3ntwerk/api/
├── app.py                   # FastAPI application (single entry point)
├── auth.py                  # Authentication (JWT, API keys)
├── dashboard.py             # Dashboard endpoints
├── models.py                # Request/response Pydantic models
├── state.py                 # Application state management
├── services.py              # TaskService, ChatService, WorkflowService, GoalService, etc.
├── webhooks.py              # Webhook endpoints
├── interview_routes.py      # Interview workflow routes
├── content_routes.py        # Content management routes
├── voice_routes.py          # Voice interaction routes
├── workflow_routes.py       # Workflow execution routes
├── automation_routes.py     # Automation/scheduling routes
├── fleet_routes.py          # Fleet management routes
├── learning_routes.py       # Learning system routes
├── module_routes.py         # Module management routes
├── websocket_events.py      # WebSocket event handling
├── test_runner.py           # Test execution endpoints
└── autonomous_test_tasks.py # Autonomous test task definitions
```

Features:
- JWT and API key authentication
- Structured logging and request tracing
- Health checks (liveness, readiness, aggregated)
- CORS support with configurable origins
- OpenAPI documentation
- Static file serving for React frontend

### Orchestration Layer

The orchestration layer manages multi-agent workflows:

```
src/ag3ntwerk/orchestration/
├── base.py                  # Orchestrator base class
├── registry.py              # ExecutiveRegistry (lazy initialization, codename lookup)
├── workflows/               # Workflow implementations
│   ├── business.py
│   ├── customer.py
│   ├── data.py
│   ├── engineering.py
│   ├── incident.py
│   ├── infrastructure.py
│   ├── research.py
│   └── security.py
├── definitions/             # Workflow definition DSL
│   ├── aggregation.py
│   ├── cross_functional.py
│   ├── pipelines.py
│   ├── single_agent.py
│   └── specialist.py
├── aggregation_workflows.py # Multi-agent aggregation patterns
├── specialist_workflows.py  # Single-specialist focused workflows
└── factory/                 # Workflow factory utilities
```

The `ExecutiveRegistry` provides lazy initialization and lookup by code or codename:

```python
registry = ExecutiveRegistry(llm_provider=provider)

# Get by code
cto = registry.get("Forge")

# Get by codename
blueprint = registry.get_by_codename("Blueprint")

# Find by capability
capable = registry.get_by_capability("code_review")
```

### Learning System

The learning system provides adaptive intelligence through continuous pattern detection and optimization:

```
src/ag3ntwerk/learning/
├── orchestrator.py           # LearningOrchestrator - central coordinator
├── continuous_pipeline.py    # Never-ending learning cycle (7 phases)
├── models.py                 # Core models (HierarchyPath, LearnedPattern, etc.)
├── outcome_tracker.py        # Records task outcomes
├── pattern_store.py          # Stores and retrieves learned patterns
├── pattern_tracker.py        # Tracks pattern effectiveness
├── pattern_experiment.py     # A/B testing for patterns
├── pattern_propagator.py     # Propagates patterns across agents
├── dynamic_router.py         # Learning-informed routing decisions
├── confidence_calibrator.py  # Calibrates agent confidence scores
├── meta_learner.py           # Learns about learning effectiveness
├── context_optimizer.py      # Optimizes task context
├── task_modifier.py          # Modifies tasks based on patterns
├── handler_generator.py      # Generates handlers for new task types
├── failure_predictor.py      # Predicts task failures
├── failure_investigator.py   # Investigates failure root causes
├── cascade_predictor.py      # Predicts cascade failures
├── load_balancer.py          # Learning-aware load balancing
├── demand_forecaster.py      # Forecasts task demand
├── capability_evolver.py     # Evolves agent capabilities
├── opportunity_detector.py   # Detects optimization opportunities
├── proactive_generator.py    # Generates proactive tasks
├── autonomy_controller.py    # Controls autonomous action levels
├── goal_aligner.py           # Aligns learning with goals
├── handoff_optimizer.py      # Optimizes inter-agent handoffs
├── self_architect.py         # Self-modification proposals
├── issue_manager.py          # Manages learning-detected issues
├── nexus_sync.py             # Syncs learning data with Nexus
├── service_adapter.py        # Config recommendations
├── plugin_telemetry.py       # Plugin performance tracking
├── workbench_bridge.py       # Workbench dashboard integration
└── facades/                  # Focused API facades for subsystems
    └── ...
```

**Continuous Pipeline Phases:**
1. Outcome collection
2. Pattern detection
3. Experiment management (A/B testing)
4. Pattern activation
5. Parameter tuning
6. Opportunity detection
7. Proactive task generation

The learning system connects to Overwatch:

```python
from ag3ntwerk.learning.orchestrator import LearningOrchestrator

orchestrator = LearningOrchestrator()
await cos.connect_learning_system(orchestrator)

# Learning now influences routing, calibrates confidence,
# detects patterns, and records outcomes automatically
```

### Persistence Layer

```
src/ag3ntwerk/persistence/
├── database.py              # DatabaseManager (SQLite)
├── analytics.py             # Metrics and analytics storage
├── audit.py                 # Audit trail
├── plugin_config.py         # Plugin configuration storage
└── migrations/              # Database migrations
```

### Memory & State

#### State Store

SQLite-based state management at `src/ag3ntwerk/memory/state_store.py`:

```python
store = StateStore()
await store.initialize()

# Store state with namespace isolation
await store.set("task_status", {"id": "123", "status": "running"})
await store.set("config", {"key": "value"}, namespace="cio")

# Retrieve with TTL support
status = await store.get("task_status")
```

#### Memory Systems

Agents access different memory types:

1. **Short-term memory**: Current context and conversation
2. **Working memory**: Active task state
3. **Long-term memory**: Historical decisions and patterns (learning system)

### Security Layer

```
src/ag3ntwerk/security/
├── validation.py            # Input validation (SQL injection, XSS, command injection)
├── secrets.py               # Secrets management with multiple backends
├── encryption.py            # Encryption utilities
└── audit_logger.py          # Security event auditing
```

### Observability Layer

```
src/ag3ntwerk/observability/
├── metrics.py               # Prometheus metrics
├── tracing.py               # Distributed tracing
└── middleware.py             # FastAPI integration middleware
```

Metrics collected:
- HTTP request count and duration
- Task execution metrics per agent
- Queue depth and routing decisions
- Error rates and circuit breaker state
- Learning system effectiveness

### Health System

The health system uses a circuit breaker pattern integrated into the Overwatch routing layer:

```python
class HealthAwareRouter:
    FAILURE_THRESHOLD = 3          # Consecutive failures to open circuit
    CIRCUIT_TIMEOUT_SECONDS = 60   # Time before half-open retry
    HEALTH_DECAY_FACTOR = 0.9      # Health score decay on failure
    HEALTH_RECOVERY_FACTOR = 1.05  # Health score recovery on success
```

Each agent has an `AgentHealthStatus` tracking:
- Health score (0.0 to 1.0)
- Success rate
- Consecutive failures
- Average latency
- Circuit breaker state (open/closed)
- Availability status

When an agent's circuit breaker opens, the Overwatch automatically routes to fallback agents defined in `FALLBACK_ROUTES`.

### Drift Detection

The `DriftMonitor` in Overwatch tracks operational drift and escalates to Nexus:

- **Performance drift**: Success rate below threshold
- **Routing drift**: Unknown task types appearing
- **Load drift**: Sustained imbalance across agents
- **Conflict drift**: Contradictory results from agents
- **Latency drift**: Response times exceeding SLOs

When drift severity exceeds tolerance, Overwatch escalates to Nexus for updated strategic context:

```python
# Automatic escalation in Overwatch.execute()
if self._drift_monitor.should_escalate():
    await self._escalate_to_coo()  # Requests guidance from Nexus
```

## LLM Integration

ag3ntwerk integrates with multiple LLM providers:

```
src/ag3ntwerk/llm/
├── base.py                  # LLMProvider ABC, ModelInfo, ModelTier
├── ollama_provider.py       # Ollama (primary local provider)
├── gpt4all_provider.py      # GPT4All (fallback local provider)
├── openai_provider.py       # OpenAI
├── anthropic_provider.py    # Anthropic
├── google_provider.py       # Google
├── openrouter_provider.py   # OpenRouter
├── huggingface_provider.py  # HuggingFace
├── perplexity_provider.py   # Perplexity
├── github_provider.py       # GitHub Models
└── circuit_breaker.py       # LLM-level circuit breaker
```

**Primary**: Ollama (local inference)
**Fallback**: GPT4All (local, no network)

Provider selection:
```python
provider = OllamaProvider(
    base_url="http://localhost:11434",
    default_model="llama2"
)
await provider.connect()
```

Model tiers: `FAST`, `BALANCED`, `POWERFUL`, `SPECIALIZED`.

## Frontend Interfaces

### PySide6 GUI Dashboard

Native desktop dashboard at `src/ag3ntwerk/gui/`:

```
src/ag3ntwerk/gui/
├── app.py                   # QMainWindow - task monitoring, chat interface
├── backend.py               # Backend data provider
└── styles.py                # Colors and agent theming
```

Overwatch-centric interface showing task status across all agents and a single chat interface routed through Overwatch.

### React/TypeScript Web Frontend

Vite-built web application served by FastAPI:

```
src/ag3ntwerk/web/
├── index.html
├── vite.config.ts
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── src/
    ├── App.tsx
    ├── main.tsx
    ├── store.ts
    ├── index.css
    ├── components/
    └── pages/
```

Built with Vite, styled with Tailwind CSS. The production build (`dist/`) is served as static files by the FastAPI backend.

## MCP Integration

ag3ntwerk exposes agents via Model Context Protocol:

```
src/ag3ntwerk/mcp/
├── server.py                # AgentWerkMCPServer (stdio-based MCP server)
├── module_tools.py          # Module-specific MCP tools
└── workflow_tools.py        # Workflow library MCP tools
```

Provides MCP tools for:
- Listing agents and capabilities
- Executing tasks via specific agents
- Routing tasks through Overwatch
- Running predefined workflows
- Managing modules (trends, commerce, brand, scheduler)

```python
from ag3ntwerk.mcp import AgentWerkMCPServer

server = AgentWerkMCPServer(llm_provider=provider)
await server.run()  # Starts stdio-based MCP server
```

## Additional Subsystems

### Modules

Domain-specific modules under `src/ag3ntwerk/modules/`:

- **VLS (Vertical Launch System)**: 10-stage product launch pipeline
- **Brand**: Brand management and identity
- **Commerce**: E-commerce integration
- **Trends**: Trend intelligence and monitoring
- **Scheduler**: Task scheduling and automation
- **Workbench**: Development workspace management

### Integrations

External service integrations at `src/ag3ntwerk/integrations/`:

- Browser automation
- Social media platforms
- Payment systems
- Research platforms
- Voice interfaces
- Webhook management
- ML/vector tooling

### Agenda Engine

Autonomous agenda system at `src/ag3ntwerk/agenda/`:

- Goal-based agenda generation
- Obstacle detection and strategy generation
- Human-in-the-loop approval checkpoints
- Connects to Overwatch via `connect_agenda_engine()`

### Products

Product management at `src/ag3ntwerk/products/`:

- Product repository
- Telemetry tracking
- Base product abstractions

### Core Infrastructure

```
src/ag3ntwerk/core/
├── base.py                  # Agent, Manager, Specialist, Task, TaskResult
├── config.py                # Configuration management
├── logging.py               # Structured logging
├── health.py                # Health check system (liveness, readiness)
├── metrics.py               # Metrics collection
├── errors.py                # Error handlers for FastAPI
├── exceptions.py            # Custom exception classes
├── identity.py              # Agent identity normalization
├── handlers.py              # Generic handlers
├── http_client.py           # Async HTTP client
├── resources.py             # Resource management
├── shutdown.py              # Graceful shutdown
├── analytics.py             # Analytics utilities
├── async_utils.py           # Async helper functions
├── plugins/                 # Plugin system
├── queue/                   # Task queue infrastructure
├── decisions/               # Decision framework
└── webhooks/                # Webhook infrastructure
```

## Deployment Architecture

### Single Instance

```
┌──────────────────────────────────────────┐
│             ag3ntwerk Server               │
│  ┌────────────────────────────────────┐  │
│  │     FastAPI + Uvicorn (API)        │  │
│  │     React Frontend (static)        │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │     Overwatch (Overwatch) + 15 Execs     │  │
│  │     Learning System Pipeline       │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │     SQLite State Store             │  │
│  │     LocalCommunicator              │  │
│  └────────────────────────────────────┘  │
└──────────────────────┬───────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│   Ollama     │ │ GPT4All  │ │    Redis     │
│  (primary)   │ │(fallback)│ │  (optional)  │
└──────────────┘ └──────────┘ └──────┬───────┘
                                     │
                              ┌──────┴───────┐
                              │    Nexus     │
                              │ (if deployed)│
                              └──────────────┘
```

### Distributed

```
                    ┌─────────────┐
                    │   Ingress   │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
      ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐
      │ ag3ntwerk   │  │ ag3ntwerk   │  │ ag3ntwerk   │
      │ Pod #1    │  │ Pod #2    │  │ Pod #3    │
      └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
      ┌────────────────────┼────────────────────┐
      │                    │                    │
┌─────┴─────┐        ┌─────┴─────┐        ┌─────┴─────┐
│   Redis   │        │  SQLite/  │        │  Ollama   │
│  (comms)  │        │   DB      │        │  (LLM)    │
└─────┬─────┘        └───────────┘        └───────────┘
      │
┌─────┴─────┐
│   Nexus   │
│  Service  │
└───────────┘
```

## Data Flow

### Task Execution Flow

```
1. Client submits task via API or MCP
   └── POST /api/v1/tasks  or  MCP tool call
        │
2. API validates and authenticates request
   └── JWT/API key, input validation, rate limiting
        │
3. Overwatch (Overwatch) receives task
   └── Checks for drift, updates metrics
        │
4. 5-phase routing pipeline
   └── Dynamic → Health-Aware → Static → Capability → LLM
        │
5. Target agent receives task
   └── Routes to internal manager, then specialist
        │
6. Specialist executes via LLM
   └── Ollama/GPT4All generates response
        │
7. Result bubbles up through hierarchy
   └── Specialist → Manager → Agent → Overwatch
        │
8. Overwatch records outcome
   └── Health metrics, drift signals, learning data
        │
9. Learning system processes outcome
   └── Pattern detection, confidence calibration, routing optimization
        │
10. Result returned to client
    └── Webhook notification (if configured) or direct response
```

## Configuration

Configuration hierarchy:
1. Environment variables (highest priority)
2. `.env` file (loaded via python-dotenv)
3. Configuration file
4. Default values

```yaml
llm:
  provider: ollama
  ollama:
    base_url: "http://localhost:11434"
    default_model: llama2
    timeout: 300.0

server:
  host: "0.0.0.0"
  port: 3737
  cors_origins:
    - "http://localhost:3000"
    - "http://localhost:5173"

nexus:
  redis_url: "redis://localhost:6379"
  channel_prefix: "ag3ntwerk:nexus"

learning:
  enabled: true
  pipeline_interval_seconds: 300

logging:
  level: INFO
```

## Extension Points

### Custom Agents

Create custom agents by extending `Manager`:

```python
from ag3ntwerk.core.base import Manager, Task, TaskResult

class CXO(Manager):
    """Chief Experience Officer."""

    def __init__(self, llm_provider=None):
        super().__init__(
            code="CXO",
            name="Chief Experience Officer",
            domain="Customer Experience",
            llm_provider=llm_provider,
        )
        self.codename = "Empathy"
        self.capabilities = [
            "customer_feedback_analysis",
            "ux_review",
            "journey_mapping",
        ]

    def can_handle(self, task: Task) -> bool:
        return task.task_type in self.capabilities

    async def execute(self, task: Task) -> TaskResult:
        # Custom implementation
        pass
```

Register with the registry:

```python
registry = ExecutiveRegistry(llm_provider=provider)
registry.register("CXO", CXO(llm_provider=provider), codename="Empathy")
```

### Custom Workflows

Define custom workflows using the orchestration layer:

```python
from ag3ntwerk.orchestration.workflows import Workflow, WorkflowStep

class OnboardingWorkflow(Workflow):
    name = "employee_onboarding"
    description = "Onboard new team members"

    steps = [
        WorkflowStep("create_accounts", agent="Forge"),
        WorkflowStep("security_briefing", agent="Sentinel"),
        WorkflowStep("team_introduction", agent="Overwatch"),
    ]
```

### Adding Routing Rules

Extend routing in `src/ag3ntwerk/agents/overwatch/routing_rules.py`:

```python
# Add to ROUTING_RULES
ROUTING_RULES["my_custom_task"] = "CXO"

# Add fallback routes
FALLBACK_ROUTES["my_custom_task"] = ["CXO", "Beacon", "Blueprint"]
```

### Learning System Hooks

Connect custom logic to the learning pipeline:

```python
# Connect learning system
orchestrator = LearningOrchestrator()
await cos.connect_learning_system(orchestrator)

# Trigger manual analysis
results = await cos.trigger_learning_analysis()

# Get learned patterns
patterns = await cos.get_learned_patterns(agent_code="Forge")
```
