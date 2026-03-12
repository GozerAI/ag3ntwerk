# Getting Started with ag3ntwerk

This guide will help you get up and running with the ag3ntwerk AI Agent Platform.

## Prerequisites

- Python 3.10 or higher
- One of the following LLM providers:
  - [Ollama](https://ollama.ai/) (recommended for local use)
  - [GPT4All](https://gpt4all.io/)
  - OpenAI API key (for cloud usage)

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/your-org/ag3ntwerk.git
cd ag3ntwerk

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### From PyPI (when available)

```bash
pip install ag3ntwerk
```

## Quick Start

### 1. Start your LLM Provider

#### Using Ollama (Recommended)

```bash
# Install Ollama from https://ollama.ai/

# Pull a model
ollama pull llama2

# Start Ollama (if not running as service)
ollama serve
```

#### Using GPT4All

```bash
# Download GPT4All from https://gpt4all.io/
# Start the local API server
gpt4all --api
```

### 2. Initialize Configuration

```bash
ag3ntwerk config --init
```

This creates a default configuration file at `config/settings.yaml`.

### 3. Verify Setup

```bash
ag3ntwerk status
```

You should see:
```
ag3ntwerk System Status
==================================================

LLM Provider:
  Status: Connected
  Provider: Ollama
  Models: 3 available

Agents:
  [+] Nexus   (Nexus     ) - Operations
  [+] Sentinel   (Sentinel  ) - Operations
  [+] Forge   (Forge     ) - Technology
  ...
```

### 4. Run Your First Task

```bash
ag3ntwerk run analysis "Summarize the main features of this project"
```

## Using the API

### Start the Server

```bash
# Development mode
uvicorn ag3ntwerk.api.app:app --reload --port 3737

# Or using the CLI
python -m ag3ntwerk.api.app
```

### Make API Requests

```bash
# Check health
curl http://localhost:3737/health

# Get system status
curl http://localhost:3737/api/v1/status

# Submit a task
curl -X POST http://localhost:3737/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Analyze code quality",
    "task_type": "code_review",
    "priority": "medium"
  }'
```

## Key Concepts

### Agents

ag3ntwerk organizes AI agents as corporate agents, each specializing in different domains:

| Agent | Domain | Example Tasks |
|-----------|--------|---------------|
| Nexus (Nexus) | Operations | Task routing, workflow coordination |
| Sentinel (Sentinel) | Security | Security scans, vulnerability assessment |
| Forge (Forge) | Technology | Code review, architecture decisions |
| Keystone (Keystone) | Finance | Cost analysis, budget planning |
| Echo (Catalyst) | Marketing | Campaign planning, market analysis |

### Tasks

Tasks are the basic unit of work in ag3ntwerk:

```python
from ag3ntwerk.core.base import Task, TaskPriority

task = Task(
    description="Review authentication module",
    task_type="security_review",
    priority=TaskPriority.HIGH,
    context={"target": "src/auth"}
)
```

### Workflows

Workflows coordinate multiple agents for complex operations:

```bash
# List available workflows
ag3ntwerk workflow --list

# Execute a workflow
ag3ntwerk workflow product_launch -p product_name="Feature X"
```

## Configuration

### Basic Configuration

Edit `config/settings.yaml`:

```yaml
llm:
  provider: ollama
  ollama:
    base_url: "http://localhost:11434"
    default_model: llama2

agents:
  coo:
    enabled: true
  cio:
    enabled: true
  cto:
    enabled: true

server:
  port: 3737
```

### Environment Variables

```bash
# Override configuration with environment variables
export AGENTWERK_API_SECRET="your-secret-key"
export PORT=8080
export LOG_LEVEL=DEBUG
```

## Using with Python

```python
import asyncio
from ag3ntwerk.agents.nexus import Nexus
from ag3ntwerk.agents.sentinel import Sentinel
from ag3ntwerk.core.base import Task, TaskPriority
from ag3ntwerk.llm import get_provider

async def main():
    # Connect to LLM provider
    provider = get_provider(provider_type="ollama")
    await provider.connect()

    # Create Nexus and register subordinates
    coo = Nexus(llm_provider=provider)
    coo.register_subordinate(Sentinel(llm_provider=provider))

    # Create and execute task
    task = Task(
        description="Analyze security of authentication module",
        task_type="security_analysis",
        priority=TaskPriority.HIGH,
    )

    result = await coo.execute(task)

    if result.success:
        print("Task completed:", result.output)
    else:
        print("Task failed:", result.error)

    await provider.disconnect()

asyncio.run(main())
```

## Common Use Cases

### Security Analysis

```bash
ag3ntwerk exec Sentinel security_scan "Analyze application for vulnerabilities" \
  -x target=src/ \
  -x scan_type=comprehensive
```

### Code Review

```bash
ag3ntwerk exec Forge code_review "Review pull request #123" \
  -x pr_number=123 \
  -x focus=security,performance
```

### Cost Analysis

```bash
ag3ntwerk exec Keystone cost_analysis "Estimate infrastructure costs for Q1" \
  -x period=Q1-2024 \
  -x include_forecast=true
```

## Troubleshooting

### LLM Provider Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check ag3ntwerk can connect
ag3ntwerk status
```

### Task Failures

```bash
# Run with verbose output
ag3ntwerk run analysis "Test task" -v

# Check queue status
ag3ntwerk queue list -s failed

# View logs
ag3ntwerk admin audit -n 50
```

### Performance Issues

```bash
# Check metrics
ag3ntwerk admin metrics

# Run health check
ag3ntwerk admin health
```

## Next Steps

- Read the [API Reference](API.md) for detailed endpoint documentation
- Explore the [Architecture Guide](ARCHITECTURE.md) to understand the system design
- Check the [CLI Reference](CLI.md) for all available commands
- Review [Security Best Practices](SECURITY.md) for production deployments

## Getting Help

- Open an issue on GitHub
- Check the documentation at `/docs`
- Join our community Discord

## Example Projects

### Security Scanner

```python
# security_scan.py
import asyncio
from ag3ntwerk.agents.sentinel import Sentinel
from ag3ntwerk.core.base import Task, TaskPriority
from ag3ntwerk.llm import get_provider

async def scan_codebase(target_path: str):
    provider = get_provider(provider_type="ollama")
    await provider.connect()

    cio = Sentinel(llm_provider=provider)

    task = Task(
        description=f"Perform comprehensive security scan of {target_path}",
        task_type="security_scan",
        priority=TaskPriority.HIGH,
        context={
            "target": target_path,
            "scan_types": ["sql_injection", "xss", "auth_bypass"],
        }
    )

    result = await cio.execute(task)

    await provider.disconnect()
    return result

# Run
result = asyncio.run(scan_codebase("src/"))
print(result.output)
```

### Automated Code Review

```python
# code_review.py
import asyncio
from ag3ntwerk.agents.forge import Forge
from ag3ntwerk.core.base import Task
from ag3ntwerk.llm import get_provider

async def review_changes(diff_content: str):
    provider = get_provider(provider_type="ollama")
    await provider.connect()

    cto = Forge(llm_provider=provider)

    task = Task(
        description="Review code changes for quality and best practices",
        task_type="code_review",
        context={
            "diff": diff_content,
            "focus_areas": ["security", "performance", "maintainability"],
        }
    )

    result = await cto.execute(task)

    await provider.disconnect()
    return result.output

# Usage with git diff
import subprocess
diff = subprocess.check_output(["git", "diff", "HEAD~1"])
review = asyncio.run(review_changes(diff.decode()))
print(review)
```
