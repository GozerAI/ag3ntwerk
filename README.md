# ag3ntwerk

[![GozerAI](https://img.shields.io/badge/GozerAI-ecosystem-5eead4?style=flat-square&labelColor=0b0e14)](https://github.com/GozerAI) [![License](https://img.shields.io/badge/license-AGPL--3.0-3b82f6?style=flat-square)](LICENSE) [![Python](https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org) [![Pro & Enterprise](https://img.shields.io/badge/Pro%20%26%20Enterprise-gozerai.com-fbbf24?style=flat-square)](https://gozerai.com/pricing)

AI agent framework and orchestration toolkit. Build, coordinate, and deploy hierarchical multi-agent systems with 16 specialized agents managed by a central routing layer.

Part of the [GozerAI](https://gozerai.com) ecosystem.

## Features

- **16 specialized agents** covering technology, finance, marketing, security, data, and more
- **Hierarchical orchestration** with central task routing and health monitoring
- **REST API** with JWT and API key authentication
- **MCP server** for tool integration with LLM clients
- **Workflow engine** with automation pipelines
- **Learning system** with agent improvement over time
- **Web dashboard** for monitoring and management

## Agents

| Agent | Domain | Description |
|-------|--------|-------------|
| **Overwatch** | Coordination | Task routing, health monitoring, drift detection |
| **Forge** | Technology | Development, architecture, DevOps |
| **Keystone** | Finance | Budgeting, cost analysis, financial reporting |
| **Echo** | Marketing | Content strategy, campaigns, brand |
| **Sentinel** | Information | Infrastructure governance, security policy |
| **Blueprint** | Product | Roadmap, feature planning, prioritization |
| **Axiom** | Research | Deep analysis, innovation, investigation |
| **Index** | Data | Data governance, knowledge management |
| **Foundry** | Engineering | Delivery, QA, CI/CD pipelines |
| **Citadel** | Security | Threat response, vulnerability management |
| **Beacon** | Customer | Experience, support, satisfaction |
| **Vector** | Revenue | Sales enablement, partnerships |
| **Aegis** | Risk | Risk assessment, BCP/DR |
| **Accord** | Compliance | Regulatory, audit, governance |
| **Compass** | Strategy | Strategic planning, market analysis |

## Quick Start

```bash
git clone https://github.com/GozerAI/ag3ntwerk.git
cd ag3ntwerk
pip install -e .

# With distributed support (Redis)
pip install -e ".[distributed]"

# Start the API server
uvicorn ag3ntwerk.api.app:app --host 0.0.0.0 --port 8000
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTWERK_AUTH_REQUIRED` | `true` | Enable/disable API authentication |
| `AGENTWERK_API_KEY` | — | API key for `X-API-Key` header auth |
| `AGENTWERK_JWT_SECRET` | — | JWT signing secret |
| `AGENTWERK_LLM_PROVIDER` | `ollama` | LLM backend (`ollama`, `openai`, `gpt4all`) |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | — | Default model for agent reasoning |

## API Reference

Authentication: `X-API-Key: <key>` or `Authorization: Bearer <jwt_token>`. Auth is enabled by default.

### Tasks & Workflows

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/tasks` | Submit a task for agent processing |
| GET | `/api/v1/tasks/:id` | Get task status and result |
| POST | `/api/v1/workflows` | Create a workflow |
| GET | `/api/v1/workflows` | List workflows |
| POST | `/api/v1/workflows/:id/run` | Execute a workflow |

### Agents & Fleet

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/agents` | List all agents |
| GET | `/api/v1/agents/:name` | Get agent details |
| GET | `/api/v1/fleet` | Fleet status overview |
| GET | `/api/v1/fleet/health` | Agent health checks |

### Dashboard & Metrics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dashboard` | Dashboard summary |
| GET | `/api/v1/metrics` | System metrics |
| GET | `/api/v1/learning/progress` | Agent learning progress |

### Conversations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat` | Chat with an agent |
| GET | `/api/v1/conversations` | List conversations |

## MCP Server

ag3ntwerk includes an MCP (Model Context Protocol) server for integration with LLM clients:

```bash
# Start the MCP server
python -m ag3ntwerk.mcp.server
```

The MCP server exposes agent capabilities as tools, allowing LLM clients to dispatch tasks, run workflows, and query agent status.

## Usage Example

```python
from ag3ntwerk.core import AgentOrchestrator

orchestrator = AgentOrchestrator()

# Route a task to the best agent
result = await orchestrator.execute_task(
    "Analyze our Q1 revenue trends and identify growth opportunities"
)
print(result.agent)   # "Vector" or "Keystone"
print(result.output)
```

## Docker

```bash
docker compose up -d
```

See `docker-compose.yml` for the full stack configuration.

## License

AGPL-3.0 — see [LICENSE](LICENSE) for details. Commercial licenses available at [gozerai.com](https://gozerai.com).
