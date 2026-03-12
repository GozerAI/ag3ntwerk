# ag3ntwerk
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)

Hierarchical AI Agent Orchestration Platform. A multi-agent system with 16 specialized agents coordinated by a central routing layer.

## Architecture

```
                    ┌──────────────────┐
                    │    Overwatch      │  ← Central coordinator
                    │  (routing/health) │
                    └────────┬─────────┘
                             │
        ┌────────┬───────┬───┴───┬────────┬────────┐
        │        │       │       │        │        │
   ┌────▼──┐ ┌──▼───┐ ┌─▼──┐ ┌──▼──┐ ┌───▼──┐ ┌──▼───┐
   │ Forge │ │Sentinel│ │Echo│ │Index│ │Citadel│ │ ...  │
   │(tech) │ │(infra)│ │(mkt)│ │(data)│ │(sec) │ │10more│
   └───────┘ └───────┘ └────┘ └─────┘ └──────┘ └──────┘
```

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
| **Nexus** | Ops (legacy) | Deprecated alias for Overwatch |

## Installation

```bash
pip install -e .

# With distributed support (Redis)
pip install -e ".[distributed]"

# With dev tools
pip install -e ".[dev]"
```

## Quick Start

```python
import asyncio
from ag3ntwerk.agents import Overwatch, Forge, Sentinel
from ag3ntwerk.core.base import Task

async def main():
    cos = Overwatch()
    cos.register_subordinate(Forge())
    cos.register_subordinate(Sentinel())

    task = Task(
        description="Review auth module security",
        task_type="security_scan",
    )
    result = await cos.execute(task)
    print(result.output)

asyncio.run(main())
```

## Configuration

Edit `config/settings.yaml`:

```yaml
llm:
  provider: ollama
  ollama:
    base_url: "http://localhost:11434"
    default_model: null

agents:
  overwatch:
    enabled: true
  forge:
    enabled: true
  sentinel:
    enabled: true
```

## CLI

```bash
ag3ntwerk status          # Show agent status
ag3ntwerk ask "question"  # Ask a question
ag3ntwerk --help          # Full command list
```

## API

```bash
uvicorn ag3ntwerk.api.app:app --port 3737
# GET /health
# POST /api/v1/tasks
# GET /api/v1/agents
```

## Deployment Modes

- **Local** (default): All agents in one process
- **Distributed**: Redis-based inter-agent communication
- **Hybrid**: Control plane centralized, specialist agents deployed separately

## Project Structure

```
src/ag3ntwerk/
├── core/           # Base classes, config, errors
├── agents/         # 16 agent implementations
├── orchestration/  # Workflows, registry, routing
├── learning/       # Pattern learning, experiments
├── api/            # FastAPI REST API
├── mcp/            # Model Context Protocol server
├── modules/        # Pluggable modules (commerce, trends, etc.)
├── gui/            # Desktop dashboard (PySide6)
└── integrations/   # External service bridges
```

## Testing

```bash
pytest tests/unit/ -q    # ~3700 unit tests
pytest tests/ -q         # Full suite
```

## License

This project is dual-licensed:

- **[AGPL-3.0](LICENSE)** for open-source use
- **[Commercial License](COMMERCIAL-LICENSE.md)** for proprietary use

See [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md) for details.
