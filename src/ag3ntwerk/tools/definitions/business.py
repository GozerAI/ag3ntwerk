"""
Business Tool Definitions.

Tools for CRM, Payments, Projects, and Workflows.
"""

from typing import Any, Dict, List, Optional

from ag3ntwerk.tools.base import (
    BaseTool,
    ToolCategory,
    ToolMetadata,
    ToolParameter,
    ToolResult,
    ParameterType,
)


class CreateCRMContactTool(BaseTool):
    """Create contacts in CRM systems."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_crm_contact",
            description="Create a new contact in the CRM",
            category=ToolCategory.BUSINESS,
            tags=["crm", "contact", "customer", "salesforce", "hubspot"],
            examples=[
                "Add a new contact to CRM",
                "Create a lead in Salesforce",
                "Add customer to HubSpot",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="email",
                description="Contact email address",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="first_name",
                description="First name",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="last_name",
                description="Last name",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="company",
                description="Company name",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="phone",
                description="Phone number",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="properties",
                description="Additional properties (JSON object)",
                param_type=ParameterType.DICT,
                required=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        email = kwargs.get("email")
        first_name = kwargs.get("first_name")
        last_name = kwargs.get("last_name")
        company = kwargs.get("company")
        phone = kwargs.get("phone")
        properties = kwargs.get("properties", {})

        try:
            from ag3ntwerk.integrations.business.crm import CRMIntegration

            crm = CRMIntegration()

            contact = await crm.create_contact(
                email=email,
                first_name=first_name,
                last_name=last_name,
                company=company,
                phone=phone,
                properties=properties,
            )

            return ToolResult(
                success=True,
                data={
                    "contact_id": contact.id,
                    "email": email,
                    "name": f"{first_name} {last_name}",
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class ProcessPaymentTool(BaseTool):
    """Process payments via Stripe."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="process_payment",
            description="Process a payment through Stripe",
            category=ToolCategory.BUSINESS,
            tags=["payment", "stripe", "charge", "transaction"],
            examples=[
                "Charge the customer $50",
                "Process a payment",
                "Create a Stripe charge",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="amount",
                description="Amount in cents",
                param_type=ParameterType.INTEGER,
                required=True,
            ),
            ToolParameter(
                name="currency",
                description="Currency code (e.g., 'usd')",
                param_type=ParameterType.STRING,
                required=False,
                default="usd",
            ),
            ToolParameter(
                name="customer_id",
                description="Stripe customer ID",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="description",
                description="Payment description",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="payment_method",
                description="Payment method ID",
                param_type=ParameterType.STRING,
                required=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        amount = kwargs.get("amount")
        currency = kwargs.get("currency", "usd")
        customer_id = kwargs.get("customer_id")
        description = kwargs.get("description", "")
        payment_method = kwargs.get("payment_method")

        try:
            from ag3ntwerk.integrations.business.payments import PaymentsIntegration

            payments = PaymentsIntegration()

            result = await payments.create_payment(
                amount=amount,
                currency=currency,
                customer=customer_id,
                description=description,
                payment_method=payment_method,
            )

            return ToolResult(
                success=True,
                data={
                    "payment_id": result.id,
                    "amount": amount,
                    "currency": currency,
                    "status": result.status,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class CreateProjectTaskTool(BaseTool):
    """Create tasks in project management tools."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_project_task",
            description="Create a task in Jira or Linear",
            category=ToolCategory.BUSINESS,
            tags=["jira", "linear", "task", "project", "ticket"],
            examples=[
                "Create a Jira ticket",
                "Add a task to Linear",
                "Create a bug ticket",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="title",
                description="Task title",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="description",
                description="Task description",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="project",
                description="Project key or ID",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="type",
                description="Issue type (bug, task, story)",
                param_type=ParameterType.STRING,
                required=False,
                default="task",
            ),
            ToolParameter(
                name="priority",
                description="Priority (high, medium, low)",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="assignee",
                description="Assignee username or ID",
                param_type=ParameterType.STRING,
                required=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        title = kwargs.get("title")
        description = kwargs.get("description")
        project = kwargs.get("project")
        issue_type = kwargs.get("type", "task")
        priority = kwargs.get("priority")
        assignee = kwargs.get("assignee")

        try:
            from ag3ntwerk.integrations.business.projects import ProjectsIntegration

            projects = ProjectsIntegration()

            task = await projects.create_issue(
                project=project,
                title=title,
                description=description,
                issue_type=issue_type,
                priority=priority,
                assignee=assignee,
            )

            return ToolResult(
                success=True,
                data={
                    "task_id": task.id,
                    "key": task.key,
                    "title": title,
                    "url": task.url,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class TriggerWorkflowTool(BaseTool):
    """Trigger automation workflows."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="trigger_workflow",
            description="Trigger a Zapier or n8n workflow",
            category=ToolCategory.BUSINESS,
            tags=["zapier", "n8n", "workflow", "automation"],
            examples=[
                "Trigger the onboarding workflow",
                "Run the Zapier automation",
                "Execute n8n workflow",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="webhook_url",
                description="Webhook URL to trigger",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="data",
                description="Data to send (JSON object)",
                param_type=ParameterType.DICT,
                required=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        webhook_url = kwargs.get("webhook_url")
        data = kwargs.get("data", {})

        try:
            from ag3ntwerk.integrations.business.workflows import WorkflowIntegration, WorkflowProvider

            workflows = WorkflowIntegration(provider=WorkflowProvider.ZAPIER)

            result = await workflows.trigger_webhook(
                webhook_url=webhook_url,
                data=data,
            )

            return ToolResult(
                success=True,
                data={
                    "status": "triggered",
                    "response": result,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )
