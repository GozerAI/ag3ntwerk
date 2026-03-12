"""
Project Management Integration for ag3ntwerk.

Provides integration with Jira and Linear.

Requirements:
    - Jira: pip install jira
    - Linear: pip install gql aiohttp

Projects is ideal for:
    - Task tracking
    - Sprint management
    - Team workload
    - Progress reporting
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ProjectProvider(str, Enum):
    """Project management providers."""

    JIRA = "jira"
    LINEAR = "linear"


@dataclass
class JiraConfig:
    """Configuration for Jira."""

    server: str = ""
    email: str = ""
    api_token: str = ""


@dataclass
class LinearConfig:
    """Configuration for Linear."""

    api_key: str = ""


@dataclass
class ProjectIssue:
    """Represents a project issue/task."""

    id: str
    key: str
    title: str
    description: str = ""
    status: str = ""
    priority: str = ""
    issue_type: str = ""
    assignee: str = ""
    reporter: str = ""
    project: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    labels: List[str] = field(default_factory=list)
    story_points: Optional[float] = None
    url: str = ""


@dataclass
class Sprint:
    """Represents a sprint."""

    id: str
    name: str
    state: str = ""  # active, closed, future
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    goal: str = ""
    issues: List[ProjectIssue] = field(default_factory=list)


class ProjectIntegration:
    """
    Integration with project management tools.

    Supports Jira and Linear.

    Example:
        # Jira
        projects = ProjectIntegration(
            provider=ProjectProvider.JIRA,
            jira_config=JiraConfig(
                server="https://company.atlassian.net",
                email="user@company.com",
                api_token="...",
            ),
        )

        # Get sprint issues
        issues = await projects.get_sprint_issues()

        # Create an issue
        issue = await projects.create_issue(ProjectIssue(
            title="Implement feature",
            description="...",
            project="PROJ",
            issue_type="Story",
        ))
    """

    def __init__(
        self,
        provider: ProjectProvider,
        jira_config: Optional[JiraConfig] = None,
        linear_config: Optional[LinearConfig] = None,
    ):
        """Initialize project integration."""
        self.provider = provider
        self.jira_config = jira_config
        self.linear_config = linear_config
        self._client = None

    def _get_jira(self):
        """Get Jira client."""
        if self._client is None:
            try:
                from jira import JIRA

                self._client = JIRA(
                    server=self.jira_config.server,
                    basic_auth=(
                        self.jira_config.email,
                        self.jira_config.api_token,
                    ),
                )
            except ImportError:
                raise ImportError("jira not installed. Install with: pip install jira")
        return self._client

    async def list_issues(
        self,
        project: Optional[str] = None,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        limit: int = 50,
    ) -> List[ProjectIssue]:
        """
        List issues.

        Args:
            project: Project key
            status: Filter by status
            assignee: Filter by assignee
            limit: Maximum issues

        Returns:
            List of ProjectIssues
        """
        if self.provider == ProjectProvider.JIRA:
            return await self._list_jira_issues(project, status, assignee, limit)
        else:
            return await self._list_linear_issues(project, status, assignee, limit)

    async def _list_jira_issues(
        self,
        project: Optional[str],
        status: Optional[str],
        assignee: Optional[str],
        limit: int,
    ) -> List[ProjectIssue]:
        """List Jira issues."""
        loop = asyncio.get_running_loop()
        jira = self._get_jira()

        def _list():
            jql_parts = []
            if project:
                jql_parts.append(f"project = {project}")
            if status:
                jql_parts.append(f"status = '{status}'")
            if assignee:
                jql_parts.append(f"assignee = '{assignee}'")

            jql = " AND ".join(jql_parts) if jql_parts else "ORDER BY created DESC"

            issues = jira.search_issues(jql, maxResults=limit)
            return [
                ProjectIssue(
                    id=issue.id,
                    key=issue.key,
                    title=issue.fields.summary,
                    description=issue.fields.description or "",
                    status=str(issue.fields.status),
                    priority=str(issue.fields.priority) if issue.fields.priority else "",
                    issue_type=str(issue.fields.issuetype),
                    assignee=str(issue.fields.assignee) if issue.fields.assignee else "",
                    reporter=str(issue.fields.reporter) if issue.fields.reporter else "",
                    project=str(issue.fields.project),
                    created_at=datetime.fromisoformat(issue.fields.created.replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(issue.fields.updated.replace("Z", "+00:00")),
                    labels=issue.fields.labels or [],
                    url=f"{self.jira_config.server}/browse/{issue.key}",
                )
                for issue in issues
            ]

        return await loop.run_in_executor(None, _list)

    async def _list_linear_issues(
        self,
        project: Optional[str],
        status: Optional[str],
        assignee: Optional[str],
        limit: int,
    ) -> List[ProjectIssue]:
        """List Linear issues."""
        # Linear uses GraphQL API
        try:
            import aiohttp
        except ImportError:
            raise ImportError("aiohttp not installed. Install with: pip install aiohttp")

        query = (
            """
        query {
            issues(first: %d) {
                nodes {
                    id
                    identifier
                    title
                    description
                    state { name }
                    priority
                    assignee { name }
                    project { name }
                    createdAt
                    updatedAt
                    url
                }
            }
        }
        """
            % limit
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.linear.app/graphql",
                json={"query": query},
                headers={
                    "Authorization": self.linear_config.api_key,
                    "Content-Type": "application/json",
                },
            ) as response:
                data = await response.json()

        issues = []
        for node in data.get("data", {}).get("issues", {}).get("nodes", []):
            issues.append(
                ProjectIssue(
                    id=node["id"],
                    key=node["identifier"],
                    title=node["title"],
                    description=node.get("description", ""),
                    status=node.get("state", {}).get("name", ""),
                    priority=str(node.get("priority", "")),
                    assignee=(
                        node.get("assignee", {}).get("name", "") if node.get("assignee") else ""
                    ),
                    project=node.get("project", {}).get("name", "") if node.get("project") else "",
                    created_at=datetime.fromisoformat(node["createdAt"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(node["updatedAt"].replace("Z", "+00:00")),
                    url=node.get("url", ""),
                )
            )

        return issues

    async def create_issue(self, issue: ProjectIssue) -> ProjectIssue:
        """Create an issue."""
        if self.provider == ProjectProvider.JIRA:
            return await self._create_jira_issue(issue)
        else:
            return await self._create_linear_issue(issue)

    async def _create_jira_issue(self, issue: ProjectIssue) -> ProjectIssue:
        """Create Jira issue."""
        loop = asyncio.get_running_loop()
        jira = self._get_jira()

        def _create():
            fields = {
                "project": {"key": issue.project},
                "summary": issue.title,
                "description": issue.description,
                "issuetype": {"name": issue.issue_type or "Task"},
            }

            if issue.priority:
                fields["priority"] = {"name": issue.priority}
            if issue.labels:
                fields["labels"] = issue.labels

            result = jira.create_issue(fields=fields)
            issue.id = result.id
            issue.key = result.key
            issue.url = f"{self.jira_config.server}/browse/{result.key}"
            return issue

        return await loop.run_in_executor(None, _create)

    async def _create_linear_issue(self, issue: ProjectIssue) -> ProjectIssue:
        """Create Linear issue."""
        try:
            import aiohttp
        except ImportError:
            raise ImportError("aiohttp not installed")

        mutation = """
        mutation CreateIssue($title: String!, $description: String, $teamId: String!) {
            issueCreate(input: {
                title: $title
                description: $description
                teamId: $teamId
            }) {
                success
                issue {
                    id
                    identifier
                    url
                }
            }
        }
        """

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.linear.app/graphql",
                json={
                    "query": mutation,
                    "variables": {
                        "title": issue.title,
                        "description": issue.description,
                        "teamId": issue.project,
                    },
                },
                headers={
                    "Authorization": self.linear_config.api_key,
                    "Content-Type": "application/json",
                },
            ) as response:
                data = await response.json()

        result = data.get("data", {}).get("issueCreate", {}).get("issue", {})
        issue.id = result.get("id", "")
        issue.key = result.get("identifier", "")
        issue.url = result.get("url", "")

        return issue

    async def get_sprints(
        self,
        board_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[Sprint]:
        """
        Get sprints.

        Args:
            board_id: Jira board ID
            state: Sprint state filter

        Returns:
            List of Sprints
        """
        if self.provider != ProjectProvider.JIRA:
            logger.warning("Sprints are only supported in Jira")
            return []

        loop = asyncio.get_running_loop()
        jira = self._get_jira()

        def _get():
            if not board_id:
                boards = jira.boards()
                if not boards:
                    return []
                bid = boards[0].id
            else:
                bid = board_id

            sprints = jira.sprints(bid, state=state)
            return [
                Sprint(
                    id=str(sprint.id),
                    name=sprint.name,
                    state=sprint.state,
                    start_date=(
                        datetime.fromisoformat(sprint.startDate.replace("Z", "+00:00"))
                        if hasattr(sprint, "startDate") and sprint.startDate
                        else None
                    ),
                    end_date=(
                        datetime.fromisoformat(sprint.endDate.replace("Z", "+00:00"))
                        if hasattr(sprint, "endDate") and sprint.endDate
                        else None
                    ),
                    goal=getattr(sprint, "goal", "") or "",
                )
                for sprint in sprints
            ]

        return await loop.run_in_executor(None, _get)

    async def get_sprint_issues(
        self,
        sprint_id: str,
    ) -> List[ProjectIssue]:
        """Get issues in a sprint."""
        if self.provider != ProjectProvider.JIRA:
            return []

        return await self._list_jira_issues(
            project=None,
            status=None,
            assignee=None,
            limit=100,
        )

    async def get_team_workload(self) -> Dict[str, Any]:
        """
        Get team workload summary.

        Returns:
            Dict with workload metrics per assignee
        """
        issues = await self.list_issues(limit=200)

        workload = {}
        for issue in issues:
            assignee = issue.assignee or "Unassigned"
            if assignee not in workload:
                workload[assignee] = {
                    "total": 0,
                    "by_status": {},
                    "by_priority": {},
                }

            workload[assignee]["total"] += 1

            status = issue.status or "Unknown"
            workload[assignee]["by_status"][status] = (
                workload[assignee]["by_status"].get(status, 0) + 1
            )

            priority = issue.priority or "Unknown"
            workload[assignee]["by_priority"][priority] = (
                workload[assignee]["by_priority"].get(priority, 0) + 1
            )

        return workload
