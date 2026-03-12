# ag3ntwerk CLI Reference

The ag3ntwerk Command Line Interface provides commands for managing and interacting with the ag3ntwerk platform.

## Installation

The CLI is installed automatically with the ag3ntwerk package:

```bash
pip install ag3ntwerk
```

## Basic Usage

```bash
ag3ntwerk [OPTIONS] COMMAND [ARGS]...
```

### Global Options

| Option | Description |
|--------|-------------|
| `-c, --config PATH` | Configuration file path (default: config/settings.yaml) |
| `-v, --verbose` | Enable verbose output |
| `--help` | Show help message |

## Commands

### System Commands

#### status

Show system status and health information.

```bash
ag3ntwerk status
```

Output:
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
  [-] Keystone   (Keystone  ) - Operations

State Store:
  Status: Initialized
  Location: ~/.ag3ntwerk/state.db
  Namespaces: 5
```

#### version

Show version information.

```bash
ag3ntwerk version
```

### Task Commands

#### run

Execute a task through the Nexus.

```bash
ag3ntwerk run TASK_TYPE DESCRIPTION [OPTIONS]
```

**Arguments:**
- `TASK_TYPE`: Type of task (e.g., security_scan, code_review)
- `DESCRIPTION`: Description of what to do

**Options:**
| Option | Description |
|--------|-------------|
| `-p, --priority` | Task priority: low, medium, high, critical |
| `-x, --context` | Context key=value pairs (multiple allowed) |
| `-t, --timeout` | Timeout in seconds (default: 60) |

**Example:**
```bash
ag3ntwerk run security_scan "Analyze authentication module" \
  -p high \
  -x target=src/auth \
  -x depth=comprehensive
```

#### exec

Execute a task with a specific agent.

```bash
ag3ntwerk exec EXECUTIVE_CODE TASK_TYPE DESCRIPTION [OPTIONS]
```

**Arguments:**
- `EXECUTIVE_CODE`: Agent to use (e.g., Sentinel, Forge, Keystone)
- `TASK_TYPE`: Type of task
- `DESCRIPTION`: Task description

**Example:**
```bash
ag3ntwerk exec Sentinel vulnerability_scan "Check for SQL injection" -p critical
```

### Agent Commands

#### agents

List all ag3ntwerk agents and their status.

```bash
ag3ntwerk agents [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-d, --details` | Show detailed agent information |

**Example:**
```bash
ag3ntwerk agents --details
```

Output:
```
ag3ntwerk Agents
===========================================================================

Code    Codename     Domain                         Status
---------------------------------------------------------------------------
Nexus     Nexus        Operations and task orchestrat [+] Available
        Capabilities: task_routing, workflow_management, resource_allocation
Sentinel     Sentinel     Security and infrastructure    [+] Available
        Capabilities: security_analysis, threat_detection, compliance
Forge     Forge        Technology and development     [+] Available
        Capabilities: code_review, architecture, technical_decisions

Total: 10 agents (3 available)
```

### Workflow Commands

#### workflow

Execute or list predefined workflows.

```bash
ag3ntwerk workflow [WORKFLOW_NAME] [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-l, --list` | List available workflows |
| `-p, --params` | Workflow parameters as key=value |

**Examples:**
```bash
# List workflows
ag3ntwerk workflow --list

# Execute workflow
ag3ntwerk workflow product_launch -p product_name="Feature X"
```

### Queue Commands

#### queue list

List tasks in the queue.

```bash
ag3ntwerk queue list [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-s, --status` | Filter by status: pending, running, completed, failed, all |
| `-n, --limit` | Maximum number of tasks to show (default: 20) |

**Example:**
```bash
ag3ntwerk queue list -s pending -n 10
```

#### queue clear

Clear tasks from the queue.

```bash
ag3ntwerk queue clear [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-s, --status` | Clear tasks with this status: completed, failed, all |
| `-f, --force` | Skip confirmation |

**Example:**
```bash
ag3ntwerk queue clear -s completed -f
```

#### queue prioritize

Change the priority of a task.

```bash
ag3ntwerk queue prioritize TASK_ID PRIORITY
```

**Arguments:**
- `TASK_ID`: Task ID (can be partial)
- `PRIORITY`: New priority: low, medium, high, critical

**Example:**
```bash
ag3ntwerk queue prioritize csk_abc123 critical
```

#### queue stats

Show queue statistics.

```bash
ag3ntwerk queue stats
```

### Admin Commands

#### admin api-keys

Manage API keys.

```bash
ag3ntwerk admin api-keys [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-c, --create NAME` | Create a new API key with this name |
| `-r, --revoke ID` | Revoke an API key by ID |
| `-p, --permissions` | Permissions for new key (multiple allowed) |
| `-e, --expires DAYS` | Days until expiration |

**Examples:**
```bash
# List API keys
ag3ntwerk admin api-keys

# Create new key
ag3ntwerk admin api-keys --create "Production App" \
  -p read -p write -p execute_task \
  -e 365

# Revoke key
ag3ntwerk admin api-keys --revoke csk_abc123
```

#### admin metrics

Show system metrics.

```bash
ag3ntwerk admin metrics [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-f, --format` | Output format: table, json |

**Example:**
```bash
ag3ntwerk admin metrics -f json
```

#### admin health

Run health checks on all components.

```bash
ag3ntwerk admin health [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-j, --json` | Output as JSON |

**Example:**
```bash
ag3ntwerk admin health
```

Output:
```
Health Check Results
============================================================

[OK] llm_provider: Connected to Ollama
[OK] state_store: Read/write operational
[OK] configuration: Using defaults (no config file)
[OK] security: Security module loaded

Overall: HEALTHY
```

#### admin audit

View security audit logs.

```bash
ag3ntwerk admin audit [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-n, --tail` | Number of recent events to show (default: 20) |
| `-s, --severity` | Filter by minimum severity |

**Example:**
```bash
ag3ntwerk admin audit -n 50 -s warning
```

### Webhook Commands

#### webhook test

Send a test webhook to a URL.

```bash
ag3ntwerk webhook test URL [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-e, --event` | Event type to send (default: test.ping) |
| `-d, --data` | Data as key=value pairs (multiple allowed) |
| `-m, --method` | HTTP method: POST, GET |

**Example:**
```bash
ag3ntwerk webhook test https://example.com/webhook \
  -e task.completed \
  -d task_id=csk_123
```

#### webhook history

Show webhook delivery history.

```bash
ag3ntwerk webhook history [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-n, --limit` | Number of events to show (default: 20) |

#### webhook endpoints

Manage webhook endpoints.

```bash
ag3ntwerk webhook endpoints [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-a, --add URL` | Add a webhook endpoint URL |
| `-r, --remove URL` | Remove a webhook endpoint URL |
| `-e, --events` | Events to subscribe to (for --add) |

**Examples:**
```bash
# List endpoints
ag3ntwerk webhook endpoints

# Add endpoint
ag3ntwerk webhook endpoints --add https://example.com/webhook \
  -e task.completed -e task.failed

# Remove endpoint
ag3ntwerk webhook endpoints --remove https://example.com/webhook
```

### Configuration Commands

#### config

Manage configuration settings.

```bash
ag3ntwerk config [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-s, --show` | Show current configuration |
| `-i, --init` | Initialize default configuration |

**Examples:**
```bash
# Show config
ag3ntwerk config --show

# Initialize default config
ag3ntwerk config --init
```

### Model Commands

#### models

List available LLM models.

```bash
ag3ntwerk models
```

Output:
```
Available LLM Models
============================================================

Provider: Ollama
Models: 3

Name                                Tier         Context
------------------------------------------------------------
llama2:latest                       balanced     4096
codellama:latest                    specialized  16384
mistral:latest                      fast         8192
```

### MCP Commands

#### mcp

Start the ag3ntwerk MCP server.

```bash
ag3ntwerk mcp
```

This starts the Model Context Protocol server for integration with LLM tools.

## Configuration File

Default configuration file location: `config/settings.yaml`

```yaml
# ag3ntwerk Configuration
# =====================

# LLM Provider Settings
llm:
  provider: ollama
  ollama:
    base_url: "http://localhost:11434"
    default_model: null
    timeout: 300.0
  gpt4all:
    base_url: "http://localhost:4891/v1"
    default_model: null
    timeout: 120.0

# Agent Settings
agents:
  coo:
    enabled: true
    name: "Nexus"
  cio:
    enabled: true
    name: "Sentinel"
    alias: "Sentinel"
  cto:
    enabled: true
    name: "Forge"
    alias: "Forge"

# Communication Settings
communication:
  mode: local
  redis:
    url: "redis://localhost:6379"
    channel_prefix: "ag3ntwerk"

# Logging Settings
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: null

# Task Settings
tasks:
  default_timeout: 60.0
  max_retries: 3
  queue_size: 100
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENTWERK_CONFIG` | Configuration file path | config/settings.yaml |
| `AGENTWERK_API_SECRET` | API key signing secret | (generated) |
| `AGENTWERK_JWT_SECRET` | JWT signing secret | (generated) |
| `AGENTWERK_DB_URL` | Database URL | sqlite:///~/.ag3ntwerk/state.db |
| `PORT` | Server port | 3737 |
| `LOG_LEVEL` | Logging level | INFO |

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Connection error (LLM provider) |
| 4 | Authentication error |

## Examples

### Complete Workflow

```bash
# 1. Initialize configuration
ag3ntwerk config --init

# 2. Check system status
ag3ntwerk status

# 3. List available models
ag3ntwerk models

# 4. List agents
ag3ntwerk agents --details

# 5. Run a task
ag3ntwerk run code_review "Review authentication module for security issues" \
  -p high -x target=src/auth

# 6. Check queue
ag3ntwerk queue list

# 7. Check health
ag3ntwerk admin health
```

### API Key Management

```bash
# Create a production API key
ag3ntwerk admin api-keys --create "Production App" \
  -p read -p write -p execute_task -p execute_workflow \
  -e 365

# Save the output key securely!
# API Key: cskey_xxxxxxxxxxxxx

# List all keys
ag3ntwerk admin api-keys

# Revoke old key
ag3ntwerk admin api-keys --revoke csk_oldkeyid
```

### Monitoring

```bash
# View metrics
ag3ntwerk admin metrics -f json > metrics.json

# Run health check
ag3ntwerk admin health -j

# View audit logs
ag3ntwerk admin audit -n 100 -s warning
```
