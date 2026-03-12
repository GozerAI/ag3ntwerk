"""
Predefined Workflows for ag3ntwerk.

Agent-ready workflows for common business operations.
"""

from ag3ntwerk.tools.workflows import (
    Workflow,
    ToolStep,
    FunctionStep,
    ParallelStep,
    BranchStep,
    WorkflowContext,
    get_workflow_registry,
)


def create_daily_briefing_workflow() -> Workflow:
    """
    Create a daily agent briefing workflow.

    Gathers news, calendar, and key metrics for agent review.
    """
    workflow = Workflow(
        name="daily_briefing",
        description="Generate daily agent briefing with news, calendar, and metrics",
    )

    # Gather information in parallel
    workflow.add_parallel_steps(
        name="gather_info",
        steps=[
            ToolStep(
                name="get_news",
                tool_name="search_news",
                parameters={
                    "query": "business technology AI",
                    "limit": 5,
                },
                output_key="news",
            ),
            FunctionStep(
                name="format_date",
                func=lambda ctx: __import__("datetime").date.today().isoformat(),
                output_key="today",
            ),
        ],
    )

    # Format briefing
    def format_briefing(ctx: WorkflowContext) -> dict:
        news = ctx.get("news", {})
        articles = news.get("articles", []) if isinstance(news, dict) else []

        briefing = {
            "date": ctx.get("today"),
            "news_summary": [
                {"title": a.get("title"), "source": a.get("source")} for a in articles[:5]
            ],
            "action_items": [],
        }
        return briefing

    workflow.add_function_step(
        name="format_briefing",
        func=format_briefing,
        output_key="briefing",
    )

    return workflow


def create_customer_onboarding_workflow() -> Workflow:
    """
    Create a customer onboarding workflow.

    Creates CRM contact, sends welcome email, and creates follow-up task.
    """
    workflow = Workflow(
        name="customer_onboarding",
        description="Onboard a new customer with CRM, email, and follow-up task",
    )

    # Create CRM contact
    workflow.add_tool_step(
        name="create_contact",
        tool_name="create_crm_contact",
        parameter_mapping={
            "email": "customer_email",
            "first_name": "customer_first_name",
            "last_name": "customer_last_name",
            "company": "customer_company",
        },
        output_key="crm_contact",
    )

    # Send welcome email
    workflow.add_tool_step(
        name="send_welcome_email",
        tool_name="send_email",
        parameter_mapping={
            "to": "customer_email",
        },
        parameters={
            "subject": "Welcome to Our Platform!",
            "body": "Thank you for signing up. We're excited to have you on board.",
        },
        output_key="welcome_email",
    )

    # Notify team on Slack
    workflow.add_tool_step(
        name="notify_team",
        tool_name="send_slack_message",
        parameters={
            "channel": "#sales",
        },
        parameter_mapping={
            "message": "notification_message",
        },
        output_key="slack_notification",
    )

    return workflow


def create_report_generation_workflow() -> Workflow:
    """
    Create a report generation workflow.

    Queries data, creates visualizations, and generates PDF report.
    """
    workflow = Workflow(
        name="generate_report",
        description="Generate a data report with charts and PDF output",
    )

    # Load and analyze data
    workflow.add_tool_step(
        name="analyze_data",
        tool_name="analyze_dataframe",
        parameter_mapping={
            "file_path": "data_file",
        },
        parameters={
            "operations": ["describe", "head"],
        },
        output_key="data_analysis",
    )

    # Create visualization
    workflow.add_tool_step(
        name="create_chart",
        tool_name="create_visualization",
        parameter_mapping={
            "data_file": "data_file",
            "x_column": "x_column",
            "y_column": "y_column",
            "output_path": "chart_output",
        },
        parameters={
            "chart_type": "bar",
            "title": "Data Analysis",
        },
        output_key="chart",
    )

    # Generate PDF report
    def prepare_report_data(ctx: WorkflowContext) -> dict:
        analysis = ctx.get("data_analysis", {})
        return {
            "title": ctx.get("report_title", "Data Report"),
            "summary": analysis.get("describe", {}),
            "charts": [ctx.get("chart", {}).get("chart_path")],
        }

    workflow.add_function_step(
        name="prepare_report_data",
        func=prepare_report_data,
        output_key="report_data",
    )

    return workflow


def create_meeting_scheduler_workflow() -> Workflow:
    """
    Create a meeting scheduling workflow.

    Creates calendar event and sends invitations.
    """
    workflow = Workflow(
        name="schedule_meeting",
        description="Schedule a meeting with calendar event and notifications",
    )

    # Create calendar event
    workflow.add_tool_step(
        name="create_event",
        tool_name="create_calendar_event",
        parameter_mapping={
            "title": "meeting_title",
            "start_time": "start_time",
            "end_time": "end_time",
            "description": "meeting_description",
            "attendees": "attendees",
            "location": "location",
        },
        output_key="calendar_event",
    )

    # Send notification
    workflow.add_tool_step(
        name="notify_slack",
        tool_name="send_slack_message",
        parameters={
            "channel": "#team",
        },
        parameter_mapping={
            "message": "slack_message",
        },
    )

    return workflow


def create_issue_triage_workflow() -> Workflow:
    """
    Create an issue triage workflow.

    Creates GitHub issue and notifies team based on priority.
    """
    workflow = Workflow(
        name="triage_issue",
        description="Triage an issue with ticket creation and team notification",
    )

    # Create GitHub issue
    workflow.add_tool_step(
        name="create_issue",
        tool_name="create_github_issue",
        parameter_mapping={
            "repo": "repo",
            "title": "issue_title",
            "body": "issue_body",
            "labels": "labels",
        },
        output_key="github_issue",
    )

    # Create project task
    workflow.add_tool_step(
        name="create_task",
        tool_name="create_project_task",
        parameter_mapping={
            "title": "issue_title",
            "description": "issue_body",
            "project": "project_key",
            "priority": "priority",
        },
        output_key="project_task",
    )

    # Notify based on priority
    def select_notification_channel(ctx: WorkflowContext) -> str:
        priority = ctx.get("priority", "medium")
        if priority == "high":
            return "urgent"
        return "normal"

    workflow.add_branch(
        name="notify_by_priority",
        selector=select_notification_channel,
        branches={
            "urgent": ToolStep(
                name="urgent_notification",
                tool_name="send_slack_message",
                parameters={
                    "channel": "#alerts",
                    "message": "🚨 Urgent issue created!",
                },
            ),
            "normal": ToolStep(
                name="normal_notification",
                tool_name="send_slack_message",
                parameters={
                    "channel": "#engineering",
                    "message": "New issue created.",
                },
            ),
        },
    )

    return workflow


def create_document_processing_workflow() -> Workflow:
    """
    Create a document processing workflow.

    Extracts text from documents, summarizes, and stores results.
    """
    workflow = Workflow(
        name="process_document",
        description="Process a document with OCR/PDF extraction and summarization",
    )

    # Determine document type and extract
    def is_pdf(ctx: WorkflowContext) -> str:
        file_path = ctx.get("file_path", "")
        if file_path.lower().endswith(".pdf"):
            return "pdf"
        return "image"

    workflow.add_branch(
        name="extract_content",
        selector=is_pdf,
        branches={
            "pdf": ToolStep(
                name="extract_pdf",
                tool_name="extract_pdf_text",
                parameter_mapping={"file_path": "file_path"},
                output_key="extracted_content",
            ),
            "image": ToolStep(
                name="ocr_image",
                tool_name="ocr_image",
                parameter_mapping={"file_path": "file_path"},
                output_key="extracted_content",
            ),
        },
    )

    # Process extracted content
    def summarize_content(ctx: WorkflowContext) -> dict:
        content = ctx.get("extracted_content", {})
        text = content.get("text") or content.get("full_text", "")

        # Simple summarization (first 500 chars)
        summary = text[:500] + "..." if len(text) > 500 else text

        return {
            "original_length": len(text),
            "summary": summary,
            "processed": True,
        }

    workflow.add_function_step(
        name="summarize",
        func=summarize_content,
        output_key="summary",
    )

    return workflow


def create_research_workflow() -> Workflow:
    """
    Create a research workflow.

    Searches news and papers on a topic, compiles findings.
    """
    workflow = Workflow(
        name="research_topic",
        description="Research a topic with news and academic paper search",
    )

    # Search in parallel
    workflow.add_parallel_steps(
        name="search_sources",
        steps=[
            ToolStep(
                name="search_news",
                tool_name="search_news",
                parameter_mapping={"query": "topic"},
                parameters={"limit": 10},
                output_key="news_results",
            ),
            ToolStep(
                name="search_papers",
                tool_name="search_papers",
                parameter_mapping={"query": "topic"},
                parameters={"limit": 10},
                output_key="paper_results",
            ),
        ],
    )

    # Compile research
    def compile_research(ctx: WorkflowContext) -> dict:
        news = ctx.get("news_results", {})
        papers = ctx.get("paper_results", {})

        return {
            "topic": ctx.get("topic"),
            "news_articles": news.get("articles", [])[:5],
            "academic_papers": papers.get("papers", [])[:5],
            "total_sources": (len(news.get("articles", [])) + len(papers.get("papers", []))),
        }

    workflow.add_function_step(
        name="compile_research",
        func=compile_research,
        output_key="research_results",
    )

    return workflow


def create_weekly_summary_workflow() -> Workflow:
    """
    Create a weekly summary workflow.

    Compiles metrics, creates report, and sends to stakeholders.
    """
    workflow = Workflow(
        name="weekly_summary",
        description="Generate and distribute weekly summary report",
    )

    # Gather metrics (placeholder - would connect to real data sources)
    def gather_metrics(ctx: WorkflowContext) -> dict:
        return {
            "week_ending": ctx.get("week_ending"),
            "key_metrics": {
                "revenue": ctx.get("revenue", 0),
                "users": ctx.get("users", 0),
                "tasks_completed": ctx.get("tasks_completed", 0),
            },
            "highlights": ctx.get("highlights", []),
        }

    workflow.add_function_step(
        name="gather_metrics",
        func=gather_metrics,
        output_key="weekly_metrics",
    )

    # Send to email and Slack in parallel
    workflow.add_parallel_steps(
        name="distribute_summary",
        steps=[
            ToolStep(
                name="email_summary",
                tool_name="send_email",
                parameter_mapping={
                    "to": "stakeholder_emails",
                },
                parameters={
                    "subject": "Weekly Summary Report",
                    "body": "Please find attached the weekly summary.",
                },
            ),
            ToolStep(
                name="slack_summary",
                tool_name="send_slack_message",
                parameters={
                    "channel": "#leadership",
                    "message": "📊 Weekly summary is now available!",
                },
            ),
        ],
    )

    return workflow


def register_predefined_workflows() -> None:
    """Register all predefined workflows."""
    registry = get_workflow_registry()

    workflows = [
        create_daily_briefing_workflow(),
        create_customer_onboarding_workflow(),
        create_report_generation_workflow(),
        create_meeting_scheduler_workflow(),
        create_issue_triage_workflow(),
        create_document_processing_workflow(),
        create_research_workflow(),
        create_weekly_summary_workflow(),
    ]

    for workflow in workflows:
        registry.register(workflow)


# Convenience function to get all workflow builders
def get_workflow_builders() -> dict:
    """Get all workflow builder functions."""
    return {
        "daily_briefing": create_daily_briefing_workflow,
        "customer_onboarding": create_customer_onboarding_workflow,
        "generate_report": create_report_generation_workflow,
        "schedule_meeting": create_meeting_scheduler_workflow,
        "triage_issue": create_issue_triage_workflow,
        "process_document": create_document_processing_workflow,
        "research_topic": create_research_workflow,
        "weekly_summary": create_weekly_summary_workflow,
    }
