"""
Workflow Integrations for ag3ntwerk.

This package provides integrations with external workflow and automation platforms:
- Flowise: Visual workflow builder for LLM chains
- n8n: Workflow automation and external service integration
"""

from ag3ntwerk.integrations.workflow.flowise import FlowiseClient, FlowiseWorkflow
from ag3ntwerk.integrations.workflow.n8n import N8nClient, N8nWorkflow, N8nWebhook

__all__ = [
    # Flowise
    "FlowiseClient",
    "FlowiseWorkflow",
    # n8n
    "N8nClient",
    "N8nWorkflow",
    "N8nWebhook",
]
