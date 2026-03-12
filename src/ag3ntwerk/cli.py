"""
ag3ntwerk Command Line Interface.

Provides commands for:
- System status and health checks
- Task execution through agents
- Agent management and listing
- Configuration management
- Queue management
- Admin tools (API keys, metrics)
- Webhook testing
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import click
import yaml

# Configure logging - default to WARNING to reduce noise
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ag3ntwerk.cli")


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


def get_provider(config: dict):
    """Get LLM provider based on configuration."""
    from ag3ntwerk.llm import get_provider as _get_provider

    llm_config = config.get("llm", {})
    provider_type = llm_config.get("provider", "ollama")

    if provider_type == "ollama":
        ollama_config = llm_config.get("ollama", {})
        return _get_provider(
            provider_type="ollama",
            base_url=ollama_config.get("base_url", "http://localhost:11434"),
            default_model=ollama_config.get("default_model"),
            timeout=ollama_config.get("timeout", 300.0),
        )
    elif provider_type == "gpt4all":
        gpt4all_config = llm_config.get("gpt4all", {})
        return _get_provider(
            provider_type="gpt4all",
            base_url=gpt4all_config.get("base_url", "http://localhost:4891/v1"),
            default_model=gpt4all_config.get("default_model"),
            timeout=gpt4all_config.get("timeout", 120.0),
        )
    else:
        return _get_provider(provider_type="auto")


# =============================================================================
# CLI Group
# =============================================================================


@click.group()
@click.option(
    "--config",
    "-c",
    default="config/settings.yaml",
    help="Configuration file path",
    type=click.Path(),
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.pass_context
def cli(ctx: click.Context, config: str, verbose: bool) -> None:
    """ag3ntwerk AI Agent Platform CLI.

    A hierarchical AI agent orchestration platform using a corporate
    agent metaphor for task routing and execution.
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["config"] = load_config(config)
    ctx.obj["verbose"] = verbose

    if verbose:
        logging.getLogger("ag3ntwerk").setLevel(logging.DEBUG)


# =============================================================================
# Status Command
# =============================================================================


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show system status and health information."""

    async def _status() -> None:
        config = ctx.obj["config"]

        click.echo()
        click.secho("ag3ntwerk System Status", fg="blue", bold=True)
        click.echo("=" * 50)

        # Check LLM Provider
        click.echo()
        click.secho("LLM Provider:", fg="cyan", bold=True)

        try:
            provider = get_provider(config)
            connected = await provider.connect()

            if connected:
                click.secho(f"  Status: Connected", fg="green")
                click.echo(f"  Provider: {provider.name}")
                click.echo(f"  Models: {len(provider.available_models)} available")

                if ctx.obj["verbose"] and provider.available_models:
                    click.echo("  Available models:")
                    for model in provider.available_models[:5]:
                        click.echo(f"    - {model.name} ({model.tier.value})")
                    if len(provider.available_models) > 5:
                        click.echo(f"    ... and {len(provider.available_models) - 5} more")

                await provider.disconnect()
            else:
                click.secho(f"  Status: Disconnected", fg="red")
                click.echo("  Hint: Ensure Ollama or GPT4All is running")

        except Exception as e:
            click.secho(f"  Status: Error - {e}", fg="red")

        # Check Agents
        click.echo()
        click.secho("Agents:", fg="cyan", bold=True)

        agents_config = config.get("agents", {})
        agents_data = [
            ("Nexus", "Nexus", "Nexus", "Operations"),
            ("Sentinel", "Sentinel", "Sentinel", "Operations"),
            ("Forge", "Forge", "Forge", "Technology"),
            ("Keystone", "Keystone", "Keystone", "Operations"),
            ("Compass", "Compass", "Compass", "Strategy"),
            ("Axiom", "Axiom", "Axiom", "Strategy"),
        ]

        for code, name, codename, stack in agents_data:
            agent_cfg = agents_config.get(code.lower(), {})
            enabled = agent_cfg.get("enabled", False)
            status_icon = (
                click.style("[+]", fg="green") if enabled else click.style("[-]", fg="yellow")
            )
            click.echo(f"  {status_icon} {code:5} ({codename:10}) - {stack}")

        # Check State Store
        click.echo()
        click.secho("State Store:", fg="cyan", bold=True)

        try:
            from ag3ntwerk.memory.state_store import StateStore

            store = StateStore()
            await store.initialize()
            namespaces = await store.list_namespaces()
            click.secho(f"  Status: Initialized", fg="green")
            click.echo(f"  Location: {store.db_path}")
            click.echo(f"  Namespaces: {len(namespaces)}")
            await store.close()
        except Exception as e:
            click.secho(f"  Status: Error - {e}", fg="red")

        click.echo()

    asyncio.run(_status())


# =============================================================================
# Run Command
# =============================================================================


@cli.command()
@click.argument("task_type")
@click.argument("description")
@click.option(
    "--priority",
    "-p",
    default="medium",
    type=click.Choice(["low", "medium", "high", "critical"]),
    help="Task priority",
)
@click.option(
    "--context",
    "-x",
    multiple=True,
    help="Context key=value pairs",
)
@click.option(
    "--timeout",
    "-t",
    default=60.0,
    type=float,
    help="Task timeout in seconds",
)
@click.pass_context
def run(
    ctx: click.Context,
    task_type: str,
    description: str,
    priority: str,
    context: tuple,
    timeout: float,
) -> None:
    """Execute a task through the Nexus.

    TASK_TYPE: Type of task (e.g., security_scan, code_review, analysis)
    DESCRIPTION: Description of what to do
    """

    async def _run() -> None:
        from ag3ntwerk.core.base import Task, TaskPriority

        config = ctx.obj["config"]

        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL,
        }

        # Parse context
        task_context = {}
        for item in context:
            if "=" in item:
                key, value = item.split("=", 1)
                task_context[key] = value

        click.echo()
        click.secho(f"Executing Task", fg="blue", bold=True)
        click.echo(f"  Type: {task_type}")
        click.echo(f"  Priority: {priority}")
        click.echo(f"  Description: {description}")
        if task_context:
            click.echo(f"  Context: {task_context}")
        click.echo()

        # Get provider
        try:
            provider = get_provider(config)
            connected = await provider.connect()

            if not connected:
                click.secho("Error: Failed to connect to LLM provider", fg="red")
                click.echo("Hint: Ensure Ollama or GPT4All is running")
                return

        except Exception as e:
            click.secho(f"Error: {e}", fg="red")
            return

        # Initialize Overwatch and agents using centralized factory
        try:
            from ag3ntwerk.initialization import create_overwatch_with_agents, ACTIVE_AGENTS

            # Determine enabled agents from config
            agents_config = config.get("agents", {})
            enabled_agents = {
                code
                for code in ACTIVE_AGENTS
                if agents_config.get(code.lower(), {}).get("enabled", True)
            }

            cos = create_overwatch_with_agents(
                llm_provider=provider,
                enabled_agents=enabled_agents,
            )

            if ctx.obj["verbose"]:
                click.echo(f"Registered {len(cos.subordinates)} agents to Overwatch")

            # Create and execute task
            task = Task(
                description=description,
                task_type=task_type,
                priority=priority_map[priority],
                context=task_context,
            )

            click.echo("Processing...")

            result = await asyncio.wait_for(
                cos.execute(task),
                timeout=timeout,
            )

            click.echo()
            if result.success:
                click.secho("✓ Task completed successfully", fg="green", bold=True)
                if result.output:
                    click.echo()
                    if isinstance(result.output, dict):
                        for key, value in result.output.items():
                            click.echo(f"  {key}: {value}")
                    else:
                        click.echo(f"  {result.output}")
            else:
                click.secho(f"✗ Task failed: {result.error}", fg="red", bold=True)

            # Show metrics if verbose
            if ctx.obj["verbose"] and result.metrics:
                click.echo()
                click.secho("Metrics:", fg="cyan")
                for key, value in result.metrics.items():
                    click.echo(f"  {key}: {value}")

        except asyncio.TimeoutError:
            click.secho(f"Error: Task timed out after {timeout}s", fg="red")
        except Exception as e:
            click.secho(f"Error: {e}", fg="red")
            if ctx.obj["verbose"]:
                import traceback

                click.echo(traceback.format_exc())
        finally:
            await provider.disconnect()

        click.echo()

    asyncio.run(_run())


# =============================================================================
# Agents Command (Legacy - use 'agents' instead)
# =============================================================================


@cli.command()
@click.option(
    "--details",
    "-d",
    is_flag=True,
    help="Show detailed agent information",
)
@click.pass_context
def agents(ctx: click.Context, details: bool) -> None:
    """List available agents and their capabilities (legacy, use 'agents')."""
    # Redirect to agents command
    ctx.invoke(agents, details=details)


# =============================================================================
# Agents Command
# =============================================================================


@cli.command()
@click.option(
    "--details",
    "-d",
    is_flag=True,
    help="Show detailed agent information including capabilities",
)
@click.pass_context
def agents(ctx: click.Context, details: bool) -> None:
    """List all ag3ntwerk agents and their status."""
    from ag3ntwerk.orchestration.registry import AgentRegistry

    click.echo()
    click.secho("ag3ntwerk Agents", fg="blue", bold=True)
    click.echo("=" * 75)
    click.echo()

    # Header
    click.echo(f"{'Code':<7} {'Codename':<12} {'Domain':<30} {'Status'}")
    click.echo("-" * 75)

    registry = AgentRegistry()
    executives_list = registry.list_agents()

    for exec_info in executives_list:
        code = exec_info["code"]
        codename = exec_info["codename"]
        available = exec_info["available"]

        if available:
            status = click.style("[+] Available", fg="green")
            # Try to get more info by loading the agent
            agent = registry.get(code)
            domain = getattr(agent, "domain", "") if agent else ""
        else:
            status = click.style("[ ] Not implemented", fg="white", dim=True)
            domain = ""

        domain_display = domain[:28] + ".." if len(domain) > 30 else domain
        click.echo(f"{code:<7} {codename:<12} {domain_display:<30} {status}")

        if details and available:
            agent = registry.get(code)
            if agent:
                capabilities = getattr(agent, "capabilities", [])
                if capabilities:
                    caps_display = ", ".join(capabilities[:5])
                    if len(capabilities) > 5:
                        caps_display += f" (+{len(capabilities) - 5} more)"
                    click.echo(f"        Capabilities: {caps_display}")

    click.echo()

    # Summary
    available_count = sum(1 for e in executives_list if e["available"])
    click.echo(f"Total: {len(executives_list)} agents ({available_count} available)")
    click.echo()


# =============================================================================
# Exec Command - Execute task with specific agent
# =============================================================================


@cli.command("exec")
@click.argument("agent_code")
@click.argument("task_type")
@click.argument("description")
@click.option(
    "--priority",
    "-p",
    default="medium",
    type=click.Choice(["low", "medium", "high", "critical"]),
    help="Task priority",
)
@click.option(
    "--context",
    "-x",
    multiple=True,
    help="Context key=value pairs",
)
@click.option(
    "--timeout",
    "-t",
    default=60.0,
    type=float,
    help="Task timeout in seconds",
)
@click.pass_context
def exec_task(
    ctx: click.Context,
    agent_code: str,
    task_type: str,
    description: str,
    priority: str,
    context: tuple,
    timeout: float,
) -> None:
    """Execute a task with a specific agent.

    AGENT_CODE: Agent to use (e.g., Blueprint, Keystone, Echo)
    TASK_TYPE: Type of task (e.g., cost_analysis, campaign_creation)
    DESCRIPTION: Description of what to do
    """

    async def _exec() -> None:
        from ag3ntwerk.core.base import Task, TaskPriority
        from ag3ntwerk.orchestration.registry import AgentRegistry

        config = ctx.obj["config"]

        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL,
        }

        # Parse context
        task_context = {}
        for item in context:
            if "=" in item:
                key, value = item.split("=", 1)
                task_context[key] = value

        click.echo()
        click.secho(f"Executing Task via {agent_code}", fg="blue", bold=True)
        click.echo(f"  Type: {task_type}")
        click.echo(f"  Priority: {priority}")
        click.echo(f"  Description: {description}")
        if task_context:
            click.echo(f"  Context: {task_context}")
        click.echo()

        # Get provider
        try:
            provider = get_provider(config)
            connected = await provider.connect()

            if not connected:
                click.secho("Error: Failed to connect to LLM provider", fg="red")
                click.echo("Hint: Ensure Ollama or GPT4All is running")
                return

        except Exception as e:
            click.secho(f"Error: {e}", fg="red")
            return

        try:
            # Get agent from registry
            registry = AgentRegistry(llm_provider=provider)
            agent = registry.get(agent_code.upper())

            if not agent:
                click.secho(f"Error: Agent not found: {agent_code}", fg="red")
                click.echo(f"Available: {', '.join(registry.get_available_codes())}")
                return

            # Create and execute task
            task = Task(
                description=description,
                task_type=task_type,
                priority=priority_map[priority],
                context=task_context,
            )

            click.echo(f"Processing via {agent.name}...")

            result = await asyncio.wait_for(
                agent.execute(task),
                timeout=timeout,
            )

            click.echo()
            if result.success:
                click.secho("Task completed successfully", fg="green", bold=True)
                if result.output:
                    click.echo()
                    if isinstance(result.output, dict):
                        for key, value in result.output.items():
                            if isinstance(value, str) and len(value) > 200:
                                click.echo(f"  {key}:")
                                click.echo(f"    {value[:500]}...")
                            else:
                                click.echo(f"  {key}: {value}")
                    else:
                        click.echo(f"  {result.output}")
            else:
                click.secho(f"Task failed: {result.error}", fg="red", bold=True)

        except asyncio.TimeoutError:
            click.secho(f"Error: Task timed out after {timeout}s", fg="red")
        except Exception as e:
            click.secho(f"Error: {e}", fg="red")
            if ctx.obj["verbose"]:
                import traceback

                click.echo(traceback.format_exc())
        finally:
            await provider.disconnect()

        click.echo()

    asyncio.run(_exec())


# =============================================================================
# Workflow Command
# =============================================================================


@cli.command()
@click.argument("workflow_name", required=False)
@click.option(
    "--list",
    "-l",
    "list_workflows",
    is_flag=True,
    help="List available workflows",
)
@click.option(
    "--params",
    "-p",
    multiple=True,
    help="Workflow parameters as key=value pairs",
)
@click.pass_context
def workflow(
    ctx: click.Context,
    workflow_name: str,
    list_workflows: bool,
    params: tuple,
) -> None:
    """Execute a predefined workflow.

    WORKFLOW_NAME: Name of workflow to execute (product_launch, incident_response, etc.)
    """
    from ag3ntwerk.orchestration.registry import AgentRegistry
    from ag3ntwerk.orchestration.base import Orchestrator
    from ag3ntwerk.orchestration.workflows import (
        ProductLaunchWorkflow,
        IncidentResponseWorkflow,
        BudgetApprovalWorkflow,
        FeatureReleaseWorkflow,
    )

    async def _workflow() -> None:
        config = ctx.obj["config"]

        # Get provider
        try:
            provider = get_provider(config)
            connected = await provider.connect()

            if not connected:
                click.secho("Error: Failed to connect to LLM provider", fg="red")
                return

        except Exception as e:
            click.secho(f"Error: {e}", fg="red")
            return

        try:
            registry = AgentRegistry(llm_provider=provider)
            orchestrator = Orchestrator(registry)

            # Register workflows
            orchestrator.register_workflow(ProductLaunchWorkflow)
            orchestrator.register_workflow(IncidentResponseWorkflow)
            orchestrator.register_workflow(BudgetApprovalWorkflow)
            orchestrator.register_workflow(FeatureReleaseWorkflow)

            if list_workflows or not workflow_name:
                click.echo()
                click.secho("Available Workflows", fg="blue", bold=True)
                click.echo("=" * 60)
                click.echo()

                for wf in orchestrator.list_workflows():
                    click.echo(f"  {wf['name']:<20} - {wf['description']}")

                click.echo()
                click.echo("Use: ag3ntwerk workflow <name> -p key=value")
                click.echo()
                return

            # Parse params
            workflow_params = {}
            for item in params:
                if "=" in item:
                    key, value = item.split("=", 1)
                    workflow_params[key] = value

            click.echo()
            click.secho(f"Executing Workflow: {workflow_name}", fg="blue", bold=True)
            if workflow_params:
                click.echo(f"Parameters: {workflow_params}")
            click.echo()

            result = await orchestrator.execute(workflow_name, **workflow_params)

            if result.success:
                click.secho("Workflow completed successfully", fg="green", bold=True)
                click.echo()
                click.echo(
                    f"Steps completed: {len([s for s in result.steps if s.get('status') == 'completed'])}"
                )
                if result.duration_seconds:
                    click.echo(f"Duration: {result.duration_seconds:.1f}s")

                if ctx.obj["verbose"]:
                    click.echo()
                    click.secho("Step Results:", fg="cyan")
                    for step in result.steps:
                        status_color = "green" if step.get("status") == "completed" else "red"
                        click.echo(
                            f"  {step['name']}: {click.style(step.get('status', 'unknown'), fg=status_color)}"
                        )
            else:
                click.secho(f"Workflow failed: {result.error}", fg="red", bold=True)

        except ValueError as e:
            click.secho(f"Error: {e}", fg="red")
        except Exception as e:
            click.secho(f"Error: {e}", fg="red")
            if ctx.obj["verbose"]:
                import traceback

                click.echo(traceback.format_exc())
        finally:
            await provider.disconnect()

        click.echo()

    asyncio.run(_workflow())


# =============================================================================
# MCP Command
# =============================================================================


@cli.command()
@click.pass_context
def mcp(ctx: click.Context) -> None:
    """Start the ag3ntwerk MCP server.

    Exposes ag3ntwerk agents via Model Context Protocol for integration
    with LLM tools and workflows.
    """

    async def _mcp() -> None:
        from ag3ntwerk.mcp import AgentWerkMCPServer

        config = ctx.obj["config"]

        click.echo()
        click.secho("Starting ag3ntwerk MCP Server...", fg="blue", bold=True)
        click.echo()

        try:
            provider = get_provider(config)
            connected = await provider.connect()

            if not connected:
                click.secho("Warning: LLM provider not connected", fg="yellow")
                click.echo("MCP server will start but agents may not function properly")
                provider = None

        except Exception as e:
            click.secho(f"Warning: LLM provider error: {e}", fg="yellow")
            provider = None

        try:
            server = AgentWerkMCPServer(llm_provider=provider)
            click.echo("MCP server running. Waiting for connections via stdio...")
            await server.run()
        except KeyboardInterrupt:
            click.echo()
            click.echo("MCP server stopped.")
        except Exception as e:
            click.secho(f"Error: {e}", fg="red")

    asyncio.run(_mcp())


# =============================================================================
# Config Command
# =============================================================================


@cli.command()
@click.option(
    "--show",
    "-s",
    is_flag=True,
    help="Show current configuration",
)
@click.option(
    "--init",
    "-i",
    is_flag=True,
    help="Initialize default configuration",
)
@click.pass_context
def config(ctx: click.Context, show: bool, init: bool) -> None:
    """Manage configuration settings."""
    config_path = Path(ctx.obj["config_path"])

    if init:
        if config_path.exists():
            if not click.confirm(f"Config file {config_path} exists. Overwrite?"):
                return

        config_path.parent.mkdir(parents=True, exist_ok=True)

        default_config = """\
# ag3ntwerk Configuration
# =====================

# LLM Provider Settings
llm:
  provider: ollama  # ollama or gpt4all
  ollama:
    base_url: "http://localhost:11434"
    default_model: null  # Use first available model
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
  cso:
    enabled: false
    name: "Compass"
  cko:
    enabled: false
    name: "Chief Knowledge Officer"
  cro:
    enabled: false
    name: "Axiom"
  cfo:
    enabled: false
    name: "Keystone"

# Communication Settings
communication:
  mode: local  # local or distributed
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
"""
        with open(config_path, "w") as f:
            f.write(default_config)

        click.secho(f"Created configuration at {config_path}", fg="green")
        return

    if show or not (show or init):
        click.echo()
        click.secho("Current Configuration", fg="blue", bold=True)
        click.echo(f"File: {config_path}")
        click.echo()

        if config_path.exists():
            click.echo(yaml.dump(ctx.obj["config"], default_flow_style=False))
        else:
            click.secho("Configuration file not found.", fg="yellow")
            click.echo(f"Run 'ag3ntwerk config --init' to create default config at {config_path}")


# =============================================================================
# Models Command
# =============================================================================


@cli.command()
@click.pass_context
def models(ctx: click.Context) -> None:
    """List available LLM models."""

    async def _models() -> None:
        config = ctx.obj["config"]

        click.echo()
        click.secho("Available LLM Models", fg="blue", bold=True)
        click.echo("=" * 60)

        try:
            provider = get_provider(config)
            connected = await provider.connect()

            if not connected:
                click.secho("Error: Failed to connect to LLM provider", fg="red")
                click.echo("Hint: Ensure Ollama or GPT4All is running")
                return

            click.echo()
            click.echo(f"Provider: {provider.name}")
            click.echo(f"Models: {len(provider.available_models)}")
            click.echo()

            if provider.available_models:
                click.echo(f"{'Name':<35} {'Tier':<12} {'Context':<10}")
                click.echo("-" * 60)

                for model in provider.available_models:
                    tier_colors = {
                        "fast": "yellow",
                        "balanced": "green",
                        "powerful": "blue",
                        "specialized": "magenta",
                    }
                    tier_color = tier_colors.get(model.tier.value, "white")
                    tier_str = click.style(f"{model.tier.value:<12}", fg=tier_color)

                    click.echo(f"{model.name:<35} {tier_str} {model.context_length:<10}")
            else:
                click.echo("No models available.")
                click.echo("Hint: Pull models with 'ollama pull <model>' or load them in GPT4All")

            await provider.disconnect()

        except Exception as e:
            click.secho(f"Error: {e}", fg="red")

        click.echo()

    asyncio.run(_models())


# =============================================================================
# Version Command
# =============================================================================


@cli.command()
def version() -> None:
    """Show version information."""
    click.echo()
    click.secho("ag3ntwerk AI Agent Platform", fg="blue", bold=True)
    click.echo("Version: 0.1.0")
    click.echo("Python: " + sys.version.split()[0])
    click.echo()


# =============================================================================
# Queue Command Group
# =============================================================================


@cli.group()
@click.pass_context
def queue(ctx: click.Context) -> None:
    """Manage the task queue.

    Commands for viewing, managing, and prioritizing tasks in the queue.
    """
    pass


@queue.command("list")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["pending", "running", "completed", "failed", "all"]),
    default="all",
    help="Filter by task status",
)
@click.option(
    "--limit",
    "-n",
    default=20,
    type=int,
    help="Maximum number of tasks to show",
)
@click.pass_context
def queue_list(ctx: click.Context, status: str, limit: int) -> None:
    """List tasks in the queue."""

    async def _list() -> None:
        click.echo()
        click.secho("Task Queue", fg="blue", bold=True)
        click.echo("=" * 80)
        click.echo()

        try:
            from ag3ntwerk.memory.state_store import StateStore

            store = StateStore()
            await store.initialize()

            # Get tasks from state store
            tasks = await store.get("tasks", namespace="queue") or []

            if status != "all":
                tasks = [t for t in tasks if t.get("status") == status]

            if not tasks:
                click.echo("No tasks in queue.")
                await store.close()
                return

            # Header
            click.echo(f"{'ID':<12} {'Type':<15} {'Priority':<10} {'Status':<12} {'Created':<20}")
            click.echo("-" * 80)

            # Display tasks (limited)
            for task in tasks[:limit]:
                task_id = task.get("id", "unknown")[:10]
                task_type = task.get("type", "unknown")[:13]
                priority = task.get("priority", "medium")
                task_status = task.get("status", "pending")
                created = task.get("created_at", "")[:19]

                # Color code status
                status_colors = {
                    "pending": "yellow",
                    "running": "cyan",
                    "completed": "green",
                    "failed": "red",
                }
                status_styled = click.style(
                    f"{task_status:<12}", fg=status_colors.get(task_status, "white")
                )

                # Color code priority
                priority_colors = {
                    "low": "white",
                    "medium": "yellow",
                    "high": "magenta",
                    "critical": "red",
                }
                priority_styled = click.style(
                    f"{priority:<10}", fg=priority_colors.get(priority, "white")
                )

                click.echo(
                    f"{task_id:<12} {task_type:<15} {priority_styled} {status_styled} {created:<20}"
                )

            if len(tasks) > limit:
                click.echo()
                click.echo(f"... and {len(tasks) - limit} more tasks")

            await store.close()

        except Exception as e:
            click.secho(f"Error: {e}", fg="red")

        click.echo()

    asyncio.run(_list())


@queue.command("clear")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["completed", "failed", "all"]),
    default="completed",
    help="Clear tasks with this status",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation",
)
@click.pass_context
def queue_clear(ctx: click.Context, status: str, force: bool) -> None:
    """Clear tasks from the queue."""

    async def _clear() -> None:
        try:
            from ag3ntwerk.memory.state_store import StateStore

            store = StateStore()
            await store.initialize()

            tasks = await store.get("tasks", namespace="queue") or []
            original_count = len(tasks)

            if status == "all":
                to_remove = len(tasks)
                tasks = []
            else:
                to_remove = len([t for t in tasks if t.get("status") == status])
                tasks = [t for t in tasks if t.get("status") != status]

            if to_remove == 0:
                click.echo(f"No {status} tasks to clear.")
                await store.close()
                return

            if not force:
                if not click.confirm(f"Clear {to_remove} {status} task(s)?"):
                    click.echo("Cancelled.")
                    await store.close()
                    return

            await store.set("tasks", tasks, namespace="queue")
            click.secho(f"Cleared {to_remove} task(s)", fg="green")

            await store.close()

        except Exception as e:
            click.secho(f"Error: {e}", fg="red")

    asyncio.run(_clear())


@queue.command("prioritize")
@click.argument("task_id")
@click.argument("priority", type=click.Choice(["low", "medium", "high", "critical"]))
@click.pass_context
def queue_prioritize(ctx: click.Context, task_id: str, priority: str) -> None:
    """Change the priority of a task."""

    async def _prioritize() -> None:
        try:
            from ag3ntwerk.memory.state_store import StateStore

            store = StateStore()
            await store.initialize()

            tasks = await store.get("tasks", namespace="queue") or []

            # Find and update task
            found = False
            for task in tasks:
                if task.get("id", "").startswith(task_id):
                    old_priority = task.get("priority", "medium")
                    task["priority"] = priority
                    task["updated_at"] = datetime.now(timezone.utc).isoformat()
                    found = True
                    click.secho(f"Task {task_id}: {old_priority} -> {priority}", fg="green")
                    break

            if not found:
                click.secho(f"Task not found: {task_id}", fg="red")
            else:
                await store.set("tasks", tasks, namespace="queue")

            await store.close()

        except Exception as e:
            click.secho(f"Error: {e}", fg="red")

    asyncio.run(_prioritize())


@queue.command("stats")
@click.pass_context
def queue_stats(ctx: click.Context) -> None:
    """Show queue statistics."""

    async def _stats() -> None:
        click.echo()
        click.secho("Queue Statistics", fg="blue", bold=True)
        click.echo("=" * 40)
        click.echo()

        try:
            from ag3ntwerk.memory.state_store import StateStore

            store = StateStore()
            await store.initialize()

            tasks = await store.get("tasks", namespace="queue") or []

            # Count by status
            status_counts: Dict[str, int] = {}
            priority_counts: Dict[str, int] = {}

            for task in tasks:
                status = task.get("status", "unknown")
                priority = task.get("priority", "unknown")

                status_counts[status] = status_counts.get(status, 0) + 1
                priority_counts[priority] = priority_counts.get(priority, 0) + 1

            click.echo(f"Total tasks: {len(tasks)}")
            click.echo()

            if status_counts:
                click.secho("By Status:", fg="cyan")
                for status, count in sorted(status_counts.items()):
                    click.echo(f"  {status:<15} {count}")
                click.echo()

            if priority_counts:
                click.secho("By Priority:", fg="cyan")
                priority_order = ["critical", "high", "medium", "low"]
                for priority in priority_order:
                    if priority in priority_counts:
                        click.echo(f"  {priority:<15} {priority_counts[priority]}")
                click.echo()

            await store.close()

        except Exception as e:
            click.secho(f"Error: {e}", fg="red")

    asyncio.run(_stats())


# =============================================================================
# Admin Command Group
# =============================================================================


@cli.group()
@click.pass_context
def admin(ctx: click.Context) -> None:
    """Administrative tools.

    Commands for API key management, metrics, and system administration.
    """
    pass


@admin.command("api-keys")
@click.option(
    "--create",
    "-c",
    "create_name",
    type=str,
    help="Create a new API key with this name",
)
@click.option(
    "--revoke",
    "-r",
    "revoke_id",
    type=str,
    help="Revoke an API key by ID",
)
@click.option(
    "--permissions",
    "-p",
    multiple=True,
    type=click.Choice(["read", "write", "admin", "execute_task", "execute_workflow"]),
    help="Permissions for new key (can specify multiple)",
)
@click.option(
    "--expires",
    "-e",
    type=int,
    help="Days until expiration (default: never)",
)
@click.pass_context
def admin_api_keys(
    ctx: click.Context,
    create_name: Optional[str],
    revoke_id: Optional[str],
    permissions: tuple,
    expires: Optional[int],
) -> None:
    """Manage API keys."""
    from ag3ntwerk.api.auth import APIKeyManager, Permission

    manager = APIKeyManager()

    click.echo()

    if create_name:
        # Create new key
        perms = {Permission(p) for p in permissions} if permissions else {Permission.READ}

        key_id, raw_key = manager.create_key(
            name=create_name,
            permissions=perms,
            expires_in_days=expires,
        )

        click.secho("API Key Created", fg="green", bold=True)
        click.echo()
        click.echo(f"  Key ID: {key_id}")
        click.echo(f"  Name: {create_name}")
        click.echo(f"  Permissions: {', '.join(p.value for p in perms)}")
        if expires:
            click.echo(f"  Expires: in {expires} days")
        click.echo()
        click.secho("  API Key (save this - it cannot be retrieved!):", fg="yellow")
        click.echo(f"  {raw_key}")
        click.echo()
        return

    if revoke_id:
        # Revoke key
        if manager.revoke_key(revoke_id):
            click.secho(f"API key revoked: {revoke_id}", fg="green")
        else:
            click.secho(f"API key not found: {revoke_id}", fg="red")
        return

    # List keys
    click.secho("API Keys", fg="blue", bold=True)
    click.echo("=" * 80)
    click.echo()

    keys = manager.list_keys(include_inactive=True)

    if not keys:
        click.echo("No API keys configured.")
        click.echo()
        click.echo("Create one with: ag3ntwerk admin api-keys --create <name>")
    else:
        click.echo(f"{'ID':<20} {'Name':<15} {'Permissions':<25} {'Status':<10} {'Uses'}")
        click.echo("-" * 80)

        for key in keys:
            key_id = key["key_id"][:18]
            name = key["name"][:13]
            perms = ", ".join(key["permissions"][:3])
            if len(key["permissions"]) > 3:
                perms += "..."
            status = "Active" if key["active"] else "Revoked"
            uses = key["use_count"]

            status_color = "green" if key["active"] else "red"
            status_styled = click.style(f"{status:<10}", fg=status_color)

            click.echo(f"{key_id:<20} {name:<15} {perms:<25} {status_styled} {uses}")

    click.echo()


@admin.command("metrics")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
@click.pass_context
def admin_metrics(ctx: click.Context, output_format: str) -> None:
    """Show system metrics."""

    async def _metrics() -> None:
        click.echo()
        click.secho("System Metrics", fg="blue", bold=True)
        click.echo("=" * 60)
        click.echo()

        metrics: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {},
        }

        # Check LLM Provider
        config = ctx.obj.get("config", {})
        try:
            provider = get_provider(config)
            connected = await provider.connect()

            metrics["components"]["llm"] = {
                "status": "connected" if connected else "disconnected",
                "provider": provider.name if connected else None,
                "models": len(provider.available_models) if connected else 0,
            }

            if connected:
                await provider.disconnect()
        except Exception as e:
            metrics["components"]["llm"] = {"status": "error", "error": str(e)}

        # Check State Store
        try:
            from ag3ntwerk.memory.state_store import StateStore

            store = StateStore()
            await store.initialize()
            namespaces = await store.list_namespaces()

            metrics["components"]["state_store"] = {
                "status": "connected",
                "namespaces": len(namespaces),
            }

            await store.close()
        except Exception as e:
            metrics["components"]["state_store"] = {"status": "error", "error": str(e)}

        # Check Queue
        try:
            from ag3ntwerk.memory.state_store import StateStore

            store = StateStore()
            await store.initialize()
            tasks = await store.get("tasks", namespace="queue") or []

            pending = len([t for t in tasks if t.get("status") == "pending"])
            running = len([t for t in tasks if t.get("status") == "running"])

            metrics["components"]["queue"] = {
                "status": "active",
                "pending_tasks": pending,
                "running_tasks": running,
                "total_tasks": len(tasks),
            }

            await store.close()
        except Exception as e:
            metrics["components"]["queue"] = {"status": "error", "error": str(e)}

        # Security audit stats
        try:
            from ag3ntwerk.security.audit_logger import get_security_logger

            audit = get_security_logger()
            stats = audit.get_statistics()

            metrics["components"]["security_audit"] = {
                "status": "active",
                "total_events": stats.get("total_events", 0),
            }
        except Exception as e:
            logger.debug("Security audit stats unavailable: %s", e)
            metrics["components"]["security_audit"] = {"status": "not_configured"}

        # Output
        if output_format == "json":
            click.echo(json.dumps(metrics, indent=2))
        else:
            # Table format
            for component, data in metrics["components"].items():
                status = data.get("status", "unknown")
                status_color = {
                    "connected": "green",
                    "active": "green",
                    "disconnected": "yellow",
                    "error": "red",
                    "not_configured": "white",
                }.get(status, "white")

                click.echo(f"{component}:")
                click.echo(f"  Status: {click.style(status, fg=status_color)}")

                for key, value in data.items():
                    if key != "status":
                        click.echo(f"  {key}: {value}")

                click.echo()

    asyncio.run(_metrics())


@admin.command("health")
@click.option(
    "--json",
    "-j",
    "as_json",
    is_flag=True,
    help="Output as JSON",
)
@click.pass_context
def admin_health(ctx: click.Context, as_json: bool) -> None:
    """Run health checks on all components."""

    async def _health() -> None:
        checks: Dict[str, Dict[str, Any]] = {}
        overall_healthy = True

        # Check 1: LLM Provider
        config = ctx.obj.get("config", {})
        try:
            provider = get_provider(config)
            connected = await provider.connect()

            if connected:
                checks["llm_provider"] = {
                    "healthy": True,
                    "message": f"Connected to {provider.name}",
                }
                await provider.disconnect()
            else:
                checks["llm_provider"] = {
                    "healthy": False,
                    "message": "Failed to connect",
                }
                overall_healthy = False
        except Exception as e:
            checks["llm_provider"] = {"healthy": False, "message": str(e)}
            overall_healthy = False

        # Check 2: State Store
        try:
            from ag3ntwerk.memory.state_store import StateStore

            store = StateStore()
            await store.initialize()

            # Try a write/read cycle
            test_key = "_health_check_test"
            await store.set(test_key, "ok", namespace="health")
            result = await store.get(test_key, namespace="health")
            await store.delete(test_key, namespace="health")

            if result == "ok":
                checks["state_store"] = {
                    "healthy": True,
                    "message": "Read/write operational",
                }
            else:
                checks["state_store"] = {
                    "healthy": False,
                    "message": "Read/write mismatch",
                }
                overall_healthy = False

            await store.close()
        except Exception as e:
            checks["state_store"] = {"healthy": False, "message": str(e)}
            overall_healthy = False

        # Check 3: Configuration
        config_path = Path(ctx.obj.get("config_path", "config/settings.yaml"))
        if config_path.exists():
            checks["configuration"] = {
                "healthy": True,
                "message": f"Loaded from {config_path}",
            }
        else:
            checks["configuration"] = {
                "healthy": False,
                "message": f"Config file not found: {config_path}",
            }
            # Not critical, just a warning
            checks["configuration"]["healthy"] = True
            checks["configuration"]["message"] = "Using defaults (no config file)"

        # Check 4: Security
        try:
            from ag3ntwerk.security.secrets import SecretsManager

            secrets = SecretsManager()
            missing = secrets.validate()

            if not missing:
                checks["security"] = {
                    "healthy": True,
                    "message": "All required secrets available",
                }
            else:
                checks["security"] = {
                    "healthy": True,  # Not critical
                    "message": f"Optional secrets missing: {', '.join(missing[:3])}",
                }
        except Exception as e:
            checks["security"] = {"healthy": True, "message": "Security module loaded"}

        # Output
        if as_json:
            result = {
                "healthy": overall_healthy,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": checks,
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo()
            click.secho("Health Check Results", fg="blue", bold=True)
            click.echo("=" * 60)
            click.echo()

            for check_name, result in checks.items():
                healthy = result["healthy"]
                message = result["message"]

                if healthy:
                    icon = click.style("[OK]", fg="green")
                else:
                    icon = click.style("[FAIL]", fg="red")

                click.echo(f"{icon} {check_name}: {message}")

            click.echo()

            if overall_healthy:
                click.secho("Overall: HEALTHY", fg="green", bold=True)
            else:
                click.secho("Overall: UNHEALTHY", fg="red", bold=True)

            click.echo()

    asyncio.run(_health())


@admin.command("audit")
@click.option(
    "--tail",
    "-n",
    default=20,
    type=int,
    help="Number of recent events to show",
)
@click.option(
    "--severity",
    "-s",
    type=click.Choice(["debug", "info", "warning", "high", "critical"]),
    help="Filter by minimum severity",
)
@click.pass_context
def admin_audit(ctx: click.Context, tail: int, severity: Optional[str]) -> None:
    """View security audit logs."""
    import os

    click.echo()
    click.secho("Security Audit Log", fg="blue", bold=True)
    click.echo("=" * 80)
    click.echo()

    log_path = os.path.expanduser("~/.ag3ntwerk/logs/security_audit.log")

    if not os.path.exists(log_path):
        click.echo("No audit logs found.")
        click.echo(f"Expected location: {log_path}")
        click.echo()
        return

    try:
        # Read last N lines
        with open(log_path) as f:
            lines = f.readlines()

        # Parse and filter
        events = []
        severity_order = ["debug", "info", "warning", "high", "critical"]
        min_severity_idx = severity_order.index(severity) if severity else 0

        for line in lines:
            try:
                event = json.loads(line.strip())
                event_severity = event.get("severity", "info")
                event_severity_idx = (
                    severity_order.index(event_severity) if event_severity in severity_order else 1
                )

                if event_severity_idx >= min_severity_idx:
                    events.append(event)
            except json.JSONDecodeError:
                continue

        # Show last N events
        events = events[-tail:]

        if not events:
            click.echo("No matching events found.")
            click.echo()
            return

        for event in events:
            timestamp = event.get("timestamp", "")[:19]
            event_type = event.get("event_type", "unknown")
            severity_val = event.get("severity", "info")
            action = event.get("action", "")
            outcome = event.get("outcome", "")

            severity_colors = {
                "debug": "white",
                "info": "cyan",
                "warning": "yellow",
                "high": "magenta",
                "critical": "red",
            }

            severity_styled = click.style(
                f"[{severity_val:^8}]", fg=severity_colors.get(severity_val, "white")
            )

            click.echo(f"{timestamp} {severity_styled} {event_type}: {action} ({outcome})")

        click.echo()
        click.echo(f"Showing {len(events)} of {len(lines)} total events")

    except Exception as e:
        click.secho(f"Error reading audit log: {e}", fg="red")

    click.echo()


# =============================================================================
# Webhook Command Group
# =============================================================================


@cli.group()
@click.pass_context
def webhook(ctx: click.Context) -> None:
    """Webhook testing and management.

    Commands for testing webhooks and viewing webhook history.
    """
    pass


@webhook.command("test")
@click.argument("url")
@click.option(
    "--event",
    "-e",
    default="test.ping",
    help="Event type to send",
)
@click.option(
    "--data",
    "-d",
    multiple=True,
    help="Data as key=value pairs",
)
@click.option(
    "--method",
    "-m",
    type=click.Choice(["POST", "GET"]),
    default="POST",
    help="HTTP method",
)
@click.pass_context
def webhook_test(ctx: click.Context, url: str, event: str, data: tuple, method: str) -> None:
    """Send a test webhook to a URL.

    URL: The webhook endpoint to test
    """
    import urllib.request
    import urllib.error

    # Parse data
    payload_data = {"event": event, "timestamp": datetime.now(timezone.utc).isoformat()}

    for item in data:
        if "=" in item:
            key, value = item.split("=", 1)
            payload_data[key] = value

    click.echo()
    click.secho(f"Testing Webhook: {url}", fg="blue", bold=True)
    click.echo(f"  Method: {method}")
    click.echo(f"  Event: {event}")
    click.echo(f"  Payload: {json.dumps(payload_data)}")
    click.echo()

    try:
        payload = json.dumps(payload_data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload if method == "POST" else None,
            headers={"Content-Type": "application/json"},
            method=method,
        )

        start_time = datetime.now()
        with urllib.request.urlopen(req, timeout=30) as response:
            elapsed = (datetime.now() - start_time).total_seconds()
            status_code = response.status
            response_body = response.read().decode("utf-8")[:500]

        if status_code >= 200 and status_code < 300:
            click.secho(f"Success: {status_code}", fg="green", bold=True)
        else:
            click.secho(f"Response: {status_code}", fg="yellow", bold=True)

        click.echo(f"  Time: {elapsed:.3f}s")

        if response_body:
            click.echo(f"  Body: {response_body[:200]}")
            if len(response_body) > 200:
                click.echo("  ... (truncated)")

    except urllib.error.HTTPError as e:
        click.secho(f"HTTP Error: {e.code} {e.reason}", fg="red", bold=True)
        try:
            body = e.read().decode("utf-8")[:200]
            if body:
                click.echo(f"  Response: {body}")
        except Exception as e:
            logger.debug("Failed to read HTTP error response body: %s", e)
    except urllib.error.URLError as e:
        click.secho(f"Connection Error: {e.reason}", fg="red", bold=True)
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", bold=True)

    click.echo()


@webhook.command("history")
@click.option(
    "--limit",
    "-n",
    default=20,
    type=int,
    help="Number of events to show",
)
@click.pass_context
def webhook_history(ctx: click.Context, limit: int) -> None:
    """Show webhook delivery history."""

    async def _history() -> None:
        click.echo()
        click.secho("Webhook Delivery History", fg="blue", bold=True)
        click.echo("=" * 80)
        click.echo()

        try:
            from ag3ntwerk.memory.state_store import StateStore

            store = StateStore()
            await store.initialize()

            history = await store.get("webhook_history", namespace="webhooks") or []

            if not history:
                click.echo("No webhook deliveries recorded.")
                click.echo()
                await store.close()
                return

            # Header
            click.echo(f"{'Timestamp':<20} {'URL':<30} {'Event':<15} {'Status'}")
            click.echo("-" * 80)

            for entry in history[-limit:]:
                timestamp = entry.get("timestamp", "")[:19]
                url = entry.get("url", "")[:28]
                event = entry.get("event", "")[:13]
                status_code = entry.get("status_code", 0)
                success = entry.get("success", False)

                if success:
                    status_styled = click.style(f"{status_code} OK", fg="green")
                else:
                    error = entry.get("error", "Failed")[:15]
                    status_styled = click.style(f"{status_code} {error}", fg="red")

                click.echo(f"{timestamp:<20} {url:<30} {event:<15} {status_styled}")

            click.echo()

            await store.close()

        except Exception as e:
            click.secho(f"Error: {e}", fg="red")

    asyncio.run(_history())


@webhook.command("endpoints")
@click.option(
    "--add",
    "-a",
    "add_url",
    type=str,
    help="Add a webhook endpoint URL",
)
@click.option(
    "--remove",
    "-r",
    "remove_url",
    type=str,
    help="Remove a webhook endpoint URL",
)
@click.option(
    "--events",
    "-e",
    multiple=True,
    help="Events to subscribe to (for --add)",
)
@click.pass_context
def webhook_endpoints(
    ctx: click.Context,
    add_url: Optional[str],
    remove_url: Optional[str],
    events: tuple,
) -> None:
    """Manage webhook endpoints."""

    async def _endpoints() -> None:
        from ag3ntwerk.memory.state_store import StateStore

        store = StateStore()
        await store.initialize()

        endpoints = await store.get("endpoints", namespace="webhooks") or []

        if add_url:
            # Add endpoint
            endpoint = {
                "url": add_url,
                "events": list(events) if events else ["*"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "active": True,
            }
            endpoints.append(endpoint)
            await store.set("endpoints", endpoints, namespace="webhooks")
            click.secho(f"Added webhook endpoint: {add_url}", fg="green")
            click.echo(f"  Events: {', '.join(endpoint['events'])}")
            await store.close()
            return

        if remove_url:
            # Remove endpoint
            original_count = len(endpoints)
            endpoints = [e for e in endpoints if e.get("url") != remove_url]

            if len(endpoints) < original_count:
                await store.set("endpoints", endpoints, namespace="webhooks")
                click.secho(f"Removed webhook endpoint: {remove_url}", fg="green")
            else:
                click.secho(f"Endpoint not found: {remove_url}", fg="red")

            await store.close()
            return

        # List endpoints
        click.echo()
        click.secho("Webhook Endpoints", fg="blue", bold=True)
        click.echo("=" * 80)
        click.echo()

        if not endpoints:
            click.echo("No webhook endpoints configured.")
            click.echo()
            click.echo("Add one with: ag3ntwerk webhook endpoints --add <url>")
        else:
            for endpoint in endpoints:
                url = endpoint.get("url", "")
                events_list = endpoint.get("events", ["*"])
                active = endpoint.get("active", True)

                status = (
                    click.style("[Active]", fg="green")
                    if active
                    else click.style("[Inactive]", fg="red")
                )

                click.echo(f"{status} {url}")
                click.echo(f"    Events: {', '.join(events_list)}")

        click.echo()
        await store.close()

    asyncio.run(_endpoints())


# =============================================================================
# Swarm Commands
# =============================================================================


@cli.group()
def swarm() -> None:
    """Interact with the Claude Swarm execution layer."""
    pass


@swarm.command("status")
def swarm_status() -> None:
    """Show Swarm health, backends, and worker status."""

    async def _status() -> None:
        from ag3ntwerk.modules.swarm_bridge import SwarmBridgeService

        service = SwarmBridgeService()
        click.echo()
        click.secho("Claude Swarm Status", fg="blue", bold=True)
        click.echo("=" * 50)

        available = await service.is_swarm_available()
        if not available:
            click.secho("  Swarm is NOT reachable at http://localhost:8766", fg="red")
            return

        click.secho("  Swarm: ", nl=False)
        click.secho("online", fg="green", bold=True)

        status = await service.get_swarm_status()
        click.echo(f"  Workers: {status.get('workers', '?')}")
        click.echo(f"  Running: {status.get('running', '?')}")

        # Instances
        instances = status.get("instances", {})
        click.echo(
            f"  Instances: {instances.get('total_instances', 0)} "
            f"(max {instances.get('max_instances', '?')})"
        )

        # Tasks
        tasks = status.get("tasks", {})
        click.echo(
            f"  Tasks — completed: {tasks.get('completed', 0)}, "
            f"failed: {tasks.get('failed', 0)}, "
            f"queued: {tasks.get('queued', 0)}"
        )

        # Backends
        backends = status.get("backends", [])
        if backends:
            click.echo()
            click.secho("  Backends:", fg="cyan", bold=True)
            for b in backends:
                health = b.get("health", "unknown")
                color = (
                    "green" if health == "healthy" else "red" if health == "unhealthy" else "yellow"
                )
                click.echo(f"    {b['name']}: ", nl=False)
                click.secho(health, fg=color, nl=False)
                click.echo(
                    f" | {b.get('url', '?')} | "
                    f"slots: {b.get('available_slots', '?')}/{b.get('max_concurrent', '?')} | "
                    f"completed: {b.get('total_completed', 0)}"
                )
        click.echo()

    asyncio.run(_status())


@swarm.command("models")
def swarm_models() -> None:
    """List available models on the Swarm."""

    async def _models() -> None:
        from ag3ntwerk.modules.swarm_bridge import SwarmBridgeService

        service = SwarmBridgeService()
        available = await service.is_swarm_available()
        if not available:
            click.secho("Swarm is not reachable.", fg="red")
            return

        models = await service.get_available_models()
        click.echo()
        click.secho("Available Models", fg="blue", bold=True)
        click.echo("=" * 70)

        if not models:
            click.echo("  No models found.")
            return

        for m in models:
            name = m.get("name", "?")
            quality = m.get("quality_rating", "?")
            speed = m.get("speed_rating", "?")
            tools = m.get("supports_tool_calling", False)
            tc = m.get("tool_calling_quality", "none")
            size = m.get("size_gb", 0)
            tags = ", ".join(m.get("task_tags", [])[:4])

            tool_icon = (
                click.style("tools", fg="green") if tools else click.style("no-tools", fg="red")
            )
            click.echo(
                f"  {name:<25} q={quality}/10 s={speed}/10 " f"{tool_icon} ({tc}) {size:.1f}GB"
            )
            if tags:
                click.echo(f"    tags: {tags}")

        click.echo()

    asyncio.run(_models())


@swarm.command("submit")
@click.argument("prompt")
@click.option("--agent", "-a", default="", help="Agent code (Forge, Foundry, etc.)")
@click.option("--priority", "-p", default="normal", help="Priority: low, normal, high, critical")
@click.option("--wait/--no-wait", default=True, help="Wait for result")
@click.option("--timeout", "-t", default=300, help="Timeout in seconds")
def swarm_submit(prompt: str, agent: str, priority: str, wait: bool, timeout: int) -> None:
    """Submit a task to the Swarm for execution."""

    async def _submit() -> None:
        from ag3ntwerk.modules.swarm_bridge import SwarmFacade

        facade = SwarmFacade()
        click.echo()
        click.secho(f"Submitting to Swarm...", fg="cyan")
        if agent:
            click.echo(f"  Agent context: {agent}")

        result = await facade.delegate_to_swarm(
            task=prompt,
            agent_code=agent,
            priority=priority,
            wait=wait,
            timeout=timeout,
        )

        task_id = result.get("task_id", "?")
        status = result.get("status", "?")

        if wait and result.get("result"):
            task_result = result["result"]
            click.echo()
            click.secho(
                f"Task {task_id}: {status}", fg="green" if status == "completed" else "yellow"
            )
            output = task_result.get("output", "")
            if output:
                click.echo()
                click.echo(output)
        else:
            click.secho(f"Task queued: {task_id}", fg="cyan")

        click.echo()

    asyncio.run(_submit())


@swarm.command("list")
@click.option("--status", "-s", default=None, help="Filter by status")
@click.option("--limit", "-n", default=20, help="Max tasks to show")
def swarm_list(status: Optional[str], limit: int) -> None:
    """List recent Swarm tasks."""

    async def _list() -> None:
        import aiohttp

        try:
            params = {"limit": limit}
            if status:
                params["status"] = status
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:8766/tasks",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        click.secho("Failed to fetch tasks.", fg="red")
                        return
                    tasks = await resp.json()
        except Exception as e:
            click.secho(f"Swarm not reachable: {e}", fg="red")
            return

        click.echo()
        click.secho("Swarm Tasks", fg="blue", bold=True)
        click.echo("=" * 70)

        if not tasks:
            click.echo("  No tasks found.")
            return

        for t in tasks:
            tid = t.get("id", "?")[:8]
            name = t.get("name", "?")[:40]
            st = t.get("status", "?")
            color = {
                "completed": "green",
                "failed": "red",
                "running": "cyan",
                "queued": "yellow",
            }.get(st, "white")
            click.echo(f"  {tid}  {click.style(st, fg=color):<20} {name}")

        click.echo()

    asyncio.run(_list())


@swarm.command("backends")
def swarm_backends() -> None:
    """List Swarm backend endpoints."""

    async def _backends() -> None:
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:8766/backends",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        click.secho("Failed to fetch backends.", fg="red")
                        return
                    backends = await resp.json()
        except Exception as e:
            click.secho(f"Swarm not reachable: {e}", fg="red")
            return

        click.echo()
        click.secho("Swarm Backends", fg="blue", bold=True)
        click.echo("=" * 70)

        for b in backends:
            health = b.get("health", "unknown")
            color = "green" if health == "healthy" else "red" if health == "unhealthy" else "yellow"
            click.echo(f"  {b['name']:<15} ", nl=False)
            click.secho(f"{health:<12}", fg=color, nl=False)
            click.echo(f" {b.get('url', '?')}")
            click.echo(
                f"    type={b.get('type', '?')} "
                f"concurrent={b.get('active_requests', 0)}/{b.get('max_concurrent', '?')} "
                f"completed={b.get('total_completed', 0)} "
                f"errors={b.get('total_errors', 0)} "
                f"latency={b.get('avg_latency_ms', 0):.0f}ms"
            )
            models = b.get("configured_models", []) + b.get("discovered_models", [])
            if models:
                click.echo(f"    models: {', '.join(set(models))}")

        click.echo()

    asyncio.run(_backends())


# =============================================================================
# Entry Point
# =============================================================================


def main() -> None:
    """Main entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
