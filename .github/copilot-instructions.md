# ag3ntwerk AI Agent Platform - Copilot Instructions

## Architecture Overview

ag3ntwerk is a hierarchical AI agent orchestration platform using a corporate agent metaphor. The system consists of:

- **Control Plane (ag3ntwerk/)**: Central orchestration with C-level agents (Nexus, Sentinel, Forge, Keystone, etc.)
- **Forge (forge/)**: Forge module for development tasks with 3-tier hierarchy (Agent→Manager→Specialist)
- **Sentinel (sentinel/)**: Sentinel module for security and infrastructure management
- **Nexus (nexus/)**: Platform services with ensemble intelligence and advanced memory systems

## Core Patterns

### Agent Hierarchy
```python
# All agents inherit from Agent
class MyAgent(Agent):
    async def execute_task(self, task: Task) -> TaskResult:
        # Task execution logic
        pass

# Managers delegate to specialists
class ManagerAgent(Agent):
    def __init__(self):
        self.specialists = [SpecialistAgent(), ...]
```

### Task System
```python
# Create and execute tasks
task = Task(
    description="Analyze security vulnerabilities",
    task_type="security_scan",
    priority=TaskPriority.HIGH,
    context={"target": "src/auth"}
)

result = await agent.execute_task(task)
```

### Communication
```python
# Message passing between agents
message = AgentMessage(
    sender="Nexus",
    recipient="Sentinel",
    message_type="task_delegation",
    payload={"task_id": task.id}
)

await communicator.send_message(message)
```

### LLM Provider Usage
```python
# Auto-detect provider (prefers Ollama)
provider = get_provider()
await provider.connect()

response = await provider.generate("Analyze this code")
```

## Development Workflows

### Setup & Run
```bash
# Install dependencies
pip install -e ".[dev]"

# Setup LLM (Ollama recommended)
ollama pull qwen2.5:7b
ollama serve

# Run system
python src/ag3ntwerk/run.py

# Or use CLI
ag3ntwerk status
ag3ntwerk run security_scan "Check authentication"
```

### Testing
```bash
# Run all tests
pytest

# Run specific test types
pytest tests/unit/
pytest tests/integration/

# With coverage
pytest --cov=src --cov-report=html
```

### Configuration
- Config files in `config/` directory (YAML format)
- Environment variables for API keys
- Default model ensemble in `config.yaml`

## Key Files & Directories

- `src/ag3ntwerk/core/base.py`: Task, TaskResult, Agent classes
- `src/ag3ntwerk/communication/`: Message passing abstractions
- `src/ag3ntwerk/llm/`: Provider implementations (Ollama, OpenAI, etc.)
- `src/forge/agents/`: Development agent implementations
- `src/sentinel/src/sentinel/`: Security platform
- `src/nexus/src/nexus/`: Ensemble intelligence platform
- `tests/conftest.py`: Test fixtures and mocks
- `config/config.yaml`: Main configuration

## Conventions

- **Async everywhere**: All agent methods are async
- **Structured logging**: Use `get_logger()` with context
- **Provider pattern**: LLM abstraction supports multiple backends
- **Hierarchical delegation**: Managers route to specialists
- **YAML configuration**: Centralized config management
- **Task-based execution**: All work flows through Task objects

## Integration Points

- **LLM Providers**: Ollama (local), OpenAI, Anthropic, Google, etc.
- **Communication**: Local (in-process) or Redis (distributed)
- **Storage**: ChromaDB (vectors), SQLite (relational)
- **Web**: FastAPI backends with React frontends
- **External**: GitHub/JIRA integrations in Forge module

## Common Patterns

### Error Handling
```python
try:
    result = await agent.execute_task(task)
except TaskExecutionError as e:
    logger.error(f"Task failed: {e}")
    return TaskResult(task.id, success=False, error=str(e))
```

### Logging Context
```python
with LogContext(task_id=task.id, agent=self.name):
    logger.info("Starting task execution")
    # ... execution logic
```

### Configuration Loading
```python
import yaml
with open("config/config.yaml") as f:
    config = yaml.safe_load(f)
```

Remember: This is a hierarchical agent system where tasks flow from agents down to specialists, with communication via structured messages and LLM-powered reasoning at each level.</content>
<parameter name="filePath">f:\Projects\ag3ntwerk\.github\copilot-instructions.md