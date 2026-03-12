"""
DevOps Tool Definitions.

Tools for GitHub, Docker, and Cloud operations.
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


class CreateGitHubIssueTool(BaseTool):
    """Create issues on GitHub."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_github_issue",
            description="Create a new issue on a GitHub repository",
            category=ToolCategory.DEVOPS,
            tags=["github", "issue", "bug", "feature"],
            examples=[
                "Create a bug report on GitHub",
                "Open a feature request issue",
                "File a GitHub issue",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="repo",
                description="Repository in format owner/repo",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="title",
                description="Issue title",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="body",
                description="Issue description",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="labels",
                description="Labels to apply (comma-separated)",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="assignees",
                description="Assignees (comma-separated usernames)",
                param_type=ParameterType.STRING,
                required=False,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        repo = kwargs.get("repo")
        title = kwargs.get("title")
        body = kwargs.get("body")
        labels = kwargs.get("labels", "")
        assignees = kwargs.get("assignees", "")

        try:
            from ag3ntwerk.integrations.devops.github import GitHubIntegration

            github = GitHubIntegration()

            label_list = [l.strip() for l in labels.split(",")] if labels else []
            assignee_list = [a.strip() for a in assignees.split(",")] if assignees else []

            issue = await github.create_issue(
                repo=repo,
                title=title,
                body=body,
                labels=label_list,
                assignees=assignee_list,
            )

            return ToolResult(
                success=True,
                data={
                    "issue_number": issue.number,
                    "url": issue.url,
                    "title": title,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class CreatePullRequestTool(BaseTool):
    """Create pull requests on GitHub."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="create_pull_request",
            description="Create a pull request on GitHub",
            category=ToolCategory.DEVOPS,
            tags=["github", "pr", "pull request", "merge"],
            examples=[
                "Create a PR for the feature branch",
                "Open a pull request",
                "Submit code for review",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="repo",
                description="Repository in format owner/repo",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="title",
                description="PR title",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="body",
                description="PR description",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="head",
                description="Source branch",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="base",
                description="Target branch",
                param_type=ParameterType.STRING,
                required=False,
                default="main",
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        repo = kwargs.get("repo")
        title = kwargs.get("title")
        body = kwargs.get("body")
        head = kwargs.get("head")
        base = kwargs.get("base", "main")

        try:
            from ag3ntwerk.integrations.devops.github import GitHubIntegration

            github = GitHubIntegration()

            pr = await github.create_pull_request(
                repo=repo,
                title=title,
                body=body,
                head=head,
                base=base,
            )

            return ToolResult(
                success=True,
                data={
                    "pr_number": pr.number,
                    "url": pr.url,
                    "title": title,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )


class RunDockerContainerTool(BaseTool):
    """Run Docker containers."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="run_docker_container",
            description="Run a Docker container",
            category=ToolCategory.DEVOPS,
            tags=["docker", "container", "deploy", "run"],
            examples=[
                "Run nginx container",
                "Start a Redis instance",
                "Deploy the app container",
            ],
        )

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="image",
                description="Docker image name",
                param_type=ParameterType.STRING,
                required=True,
            ),
            ToolParameter(
                name="name",
                description="Container name",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="ports",
                description="Port mappings (e.g., '8080:80,443:443')",
                param_type=ParameterType.STRING,
                required=False,
            ),
            ToolParameter(
                name="environment",
                description="Environment variables (JSON object)",
                param_type=ParameterType.DICT,
                required=False,
            ),
            ToolParameter(
                name="detach",
                description="Run in background",
                param_type=ParameterType.BOOLEAN,
                required=False,
                default=True,
            ),
        ]

    async def _execute(self, **kwargs) -> ToolResult:
        image = kwargs.get("image")
        name = kwargs.get("name")
        ports = kwargs.get("ports", "")
        environment = kwargs.get("environment", {})
        detach = kwargs.get("detach", True)

        try:
            from ag3ntwerk.integrations.devops.docker import DockerIntegration

            docker = DockerIntegration()

            # Parse port mappings
            port_dict = {}
            if ports:
                for mapping in ports.split(","):
                    if ":" in mapping:
                        host, container = mapping.split(":")
                        port_dict[container] = host

            container = await docker.run(
                image=image,
                name=name,
                ports=port_dict,
                environment=environment,
                detach=detach,
            )

            return ToolResult(
                success=True,
                data={
                    "container_id": container.id,
                    "name": container.name,
                    "status": container.status,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )
