"""
GitHub Integration for ag3ntwerk.

Provides repository management, PR reviews, and issue tracking.

Requirements:
    - pip install PyGithub

GitHub is ideal for:
    - Code review automation
    - Issue management
    - Release tracking
    - Repository analytics
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class PRState(str, Enum):
    """Pull request states."""

    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"
    ALL = "all"


class IssueState(str, Enum):
    """Issue states."""

    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"


@dataclass
class GitHubConfig:
    """Configuration for GitHub integration."""

    token: str = ""
    base_url: str = "https://api.github.com"  # For GitHub Enterprise


@dataclass
class GitHubUser:
    """Represents a GitHub user."""

    login: str
    id: int
    name: str = ""
    email: str = ""
    avatar_url: str = ""
    url: str = ""


@dataclass
class Repository:
    """Represents a GitHub repository."""

    name: str
    full_name: str
    owner: str
    description: str = ""
    url: str = ""
    clone_url: str = ""
    default_branch: str = "main"
    is_private: bool = False
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PullRequest:
    """Represents a pull request."""

    number: int
    title: str
    body: str = ""
    state: PRState = PRState.OPEN
    author: Optional[GitHubUser] = None
    head_branch: str = ""
    base_branch: str = ""
    url: str = ""
    mergeable: Optional[bool] = None
    merged: bool = False
    merged_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    labels: List[str] = field(default_factory=list)
    reviewers: List[GitHubUser] = field(default_factory=list)
    comments_count: int = 0
    commits_count: int = 0
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0


@dataclass
class Issue:
    """Represents an issue."""

    number: int
    title: str
    body: str = ""
    state: IssueState = IssueState.OPEN
    author: Optional[GitHubUser] = None
    url: str = ""
    labels: List[str] = field(default_factory=list)
    assignees: List[GitHubUser] = field(default_factory=list)
    milestone: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    comments_count: int = 0


@dataclass
class Commit:
    """Represents a commit."""

    sha: str
    message: str
    author: Optional[GitHubUser] = None
    date: Optional[datetime] = None
    url: str = ""
    additions: int = 0
    deletions: int = 0


@dataclass
class Release:
    """Represents a release."""

    tag_name: str
    name: str
    body: str = ""
    draft: bool = False
    prerelease: bool = False
    created_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    url: str = ""
    assets: List[Dict[str, Any]] = field(default_factory=list)


class GitHubIntegration:
    """
    Integration with GitHub for repository operations.

    Provides repository management, PR reviews, and issue tracking.

    Example:
        integration = GitHubIntegration(GitHubConfig(
            token="ghp_...",
        ))

        # Get repository info
        repo = await integration.get_repository("owner/repo")

        # List open PRs
        prs = await integration.list_pull_requests("owner/repo", state=PRState.OPEN)

        # Create an issue
        issue = await integration.create_issue(
            "owner/repo",
            title="Bug report",
            body="Description...",
            labels=["bug"],
        )
    """

    def __init__(self, config: GitHubConfig):
        """Initialize GitHub integration."""
        self.config = config
        self._github = None

    def _get_github(self):
        """Get GitHub client."""
        if self._github is None:
            try:
                from github import Github

                if self.config.base_url != "https://api.github.com":
                    self._github = Github(
                        self.config.token,
                        base_url=self.config.base_url,
                    )
                else:
                    self._github = Github(self.config.token)
            except ImportError:
                raise ImportError("PyGithub not installed. Install with: pip install PyGithub")
        return self._github

    def _user_from_github(self, user) -> GitHubUser:
        """Convert GitHub user to GitHubUser."""
        return GitHubUser(
            login=user.login,
            id=user.id,
            name=user.name or "",
            email=user.email or "",
            avatar_url=user.avatar_url or "",
            url=user.html_url or "",
        )

    async def get_repository(self, repo_name: str) -> Repository:
        """
        Get repository information.

        Args:
            repo_name: Repository name (owner/repo)

        Returns:
            Repository object
        """
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _fetch():
            repo = gh.get_repo(repo_name)
            return Repository(
                name=repo.name,
                full_name=repo.full_name,
                owner=repo.owner.login,
                description=repo.description or "",
                url=repo.html_url,
                clone_url=repo.clone_url,
                default_branch=repo.default_branch,
                is_private=repo.private,
                stars=repo.stargazers_count,
                forks=repo.forks_count,
                open_issues=repo.open_issues_count,
                created_at=repo.created_at,
                updated_at=repo.updated_at,
            )

        return await loop.run_in_executor(None, _fetch)

    async def list_repositories(
        self,
        user: Optional[str] = None,
        org: Optional[str] = None,
    ) -> List[Repository]:
        """
        List repositories for a user or organization.

        Args:
            user: Username (uses authenticated user if None)
            org: Organization name

        Returns:
            List of Repositories
        """
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _fetch():
            if org:
                repos = gh.get_organization(org).get_repos()
            elif user:
                repos = gh.get_user(user).get_repos()
            else:
                repos = gh.get_user().get_repos()

            return [
                Repository(
                    name=repo.name,
                    full_name=repo.full_name,
                    owner=repo.owner.login,
                    description=repo.description or "",
                    url=repo.html_url,
                    clone_url=repo.clone_url,
                    default_branch=repo.default_branch,
                    is_private=repo.private,
                    stars=repo.stargazers_count,
                    forks=repo.forks_count,
                )
                for repo in repos
            ]

        return await loop.run_in_executor(None, _fetch)

    async def list_pull_requests(
        self,
        repo_name: str,
        state: PRState = PRState.OPEN,
        base: Optional[str] = None,
        head: Optional[str] = None,
    ) -> List[PullRequest]:
        """
        List pull requests.

        Args:
            repo_name: Repository name
            state: PR state filter
            base: Base branch filter
            head: Head branch filter

        Returns:
            List of PullRequests
        """
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _fetch():
            repo = gh.get_repo(repo_name)
            prs = repo.get_pulls(
                state=state.value if state != PRState.ALL else "all",
                base=base or "",
                head=head or "",
            )

            return [
                PullRequest(
                    number=pr.number,
                    title=pr.title,
                    body=pr.body or "",
                    state=PRState(pr.state),
                    author=self._user_from_github(pr.user) if pr.user else None,
                    head_branch=pr.head.ref,
                    base_branch=pr.base.ref,
                    url=pr.html_url,
                    mergeable=pr.mergeable,
                    merged=pr.merged,
                    merged_at=pr.merged_at,
                    created_at=pr.created_at,
                    updated_at=pr.updated_at,
                    labels=[l.name for l in pr.labels],
                    comments_count=pr.comments,
                    commits_count=pr.commits,
                    additions=pr.additions,
                    deletions=pr.deletions,
                    changed_files=pr.changed_files,
                )
                for pr in prs
            ]

        return await loop.run_in_executor(None, _fetch)

    async def get_pull_request(
        self,
        repo_name: str,
        pr_number: int,
    ) -> PullRequest:
        """Get a specific pull request."""
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _fetch():
            repo = gh.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            return PullRequest(
                number=pr.number,
                title=pr.title,
                body=pr.body or "",
                state=PRState(pr.state),
                author=self._user_from_github(pr.user) if pr.user else None,
                head_branch=pr.head.ref,
                base_branch=pr.base.ref,
                url=pr.html_url,
                mergeable=pr.mergeable,
                merged=pr.merged,
                merged_at=pr.merged_at,
                created_at=pr.created_at,
                updated_at=pr.updated_at,
                labels=[l.name for l in pr.labels],
                comments_count=pr.comments,
                commits_count=pr.commits,
                additions=pr.additions,
                deletions=pr.deletions,
                changed_files=pr.changed_files,
            )

        return await loop.run_in_executor(None, _fetch)

    async def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head: str,
        base: str,
        draft: bool = False,
    ) -> PullRequest:
        """
        Create a pull request.

        Args:
            repo_name: Repository name
            title: PR title
            body: PR description
            head: Head branch
            base: Base branch
            draft: Create as draft

        Returns:
            Created PullRequest
        """
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _create():
            repo = gh.get_repo(repo_name)
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base,
                draft=draft,
            )

            return PullRequest(
                number=pr.number,
                title=pr.title,
                body=pr.body or "",
                state=PRState(pr.state),
                head_branch=pr.head.ref,
                base_branch=pr.base.ref,
                url=pr.html_url,
                created_at=pr.created_at,
            )

        return await loop.run_in_executor(None, _create)

    async def merge_pull_request(
        self,
        repo_name: str,
        pr_number: int,
        merge_method: str = "merge",  # merge, squash, rebase
        commit_message: Optional[str] = None,
    ) -> bool:
        """
        Merge a pull request.

        Args:
            repo_name: Repository name
            pr_number: PR number
            merge_method: Merge method
            commit_message: Custom commit message

        Returns:
            True if merged successfully
        """
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _merge():
            repo = gh.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            result = pr.merge(
                merge_method=merge_method,
                commit_message=commit_message,
            )
            return result.merged

        return await loop.run_in_executor(None, _merge)

    async def add_pr_review(
        self,
        repo_name: str,
        pr_number: int,
        body: str,
        event: str = "COMMENT",  # APPROVE, REQUEST_CHANGES, COMMENT
    ) -> bool:
        """
        Add a review to a PR.

        Args:
            repo_name: Repository name
            pr_number: PR number
            body: Review comment
            event: Review event type

        Returns:
            True if review added
        """
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _review():
            repo = gh.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            pr.create_review(body=body, event=event)
            return True

        return await loop.run_in_executor(None, _review)

    async def list_issues(
        self,
        repo_name: str,
        state: IssueState = IssueState.OPEN,
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None,
    ) -> List[Issue]:
        """
        List issues.

        Args:
            repo_name: Repository name
            state: Issue state filter
            labels: Label filter
            assignee: Assignee filter

        Returns:
            List of Issues
        """
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _fetch():
            repo = gh.get_repo(repo_name)
            issues = repo.get_issues(
                state=state.value if state != IssueState.ALL else "all",
                labels=labels or [],
                assignee=assignee or "",
            )

            return [
                Issue(
                    number=issue.number,
                    title=issue.title,
                    body=issue.body or "",
                    state=IssueState(issue.state),
                    author=self._user_from_github(issue.user) if issue.user else None,
                    url=issue.html_url,
                    labels=[l.name for l in issue.labels],
                    assignees=[self._user_from_github(a) for a in issue.assignees],
                    milestone=issue.milestone.title if issue.milestone else "",
                    created_at=issue.created_at,
                    updated_at=issue.updated_at,
                    closed_at=issue.closed_at,
                    comments_count=issue.comments,
                )
                for issue in issues
                if issue.pull_request is None  # Exclude PRs
            ]

        return await loop.run_in_executor(None, _fetch)

    async def create_issue(
        self,
        repo_name: str,
        title: str,
        body: str = "",
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None,
    ) -> Issue:
        """
        Create an issue.

        Args:
            repo_name: Repository name
            title: Issue title
            body: Issue description
            labels: Labels to add
            assignees: Usernames to assign
            milestone: Milestone number

        Returns:
            Created Issue
        """
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _create():
            repo = gh.get_repo(repo_name)
            issue = repo.create_issue(
                title=title,
                body=body,
                labels=labels or [],
                assignees=assignees or [],
            )

            return Issue(
                number=issue.number,
                title=issue.title,
                body=issue.body or "",
                state=IssueState(issue.state),
                url=issue.html_url,
                labels=[l.name for l in issue.labels],
                created_at=issue.created_at,
            )

        return await loop.run_in_executor(None, _create)

    async def close_issue(
        self,
        repo_name: str,
        issue_number: int,
        comment: Optional[str] = None,
    ) -> bool:
        """Close an issue."""
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _close():
            repo = gh.get_repo(repo_name)
            issue = repo.get_issue(issue_number)
            if comment:
                issue.create_comment(comment)
            issue.edit(state="closed")
            return True

        return await loop.run_in_executor(None, _close)

    async def add_comment(
        self,
        repo_name: str,
        issue_number: int,
        body: str,
    ) -> bool:
        """Add a comment to an issue or PR."""
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _comment():
            repo = gh.get_repo(repo_name)
            issue = repo.get_issue(issue_number)
            issue.create_comment(body)
            return True

        return await loop.run_in_executor(None, _comment)

    async def list_commits(
        self,
        repo_name: str,
        branch: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        path: Optional[str] = None,
    ) -> List[Commit]:
        """
        List commits.

        Args:
            repo_name: Repository name
            branch: Branch name
            since: Start date
            until: End date
            path: File path filter

        Returns:
            List of Commits
        """
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _fetch():
            repo = gh.get_repo(repo_name)
            kwargs = {}
            if branch:
                kwargs["sha"] = branch
            if since:
                kwargs["since"] = since
            if until:
                kwargs["until"] = until
            if path:
                kwargs["path"] = path

            commits = repo.get_commits(**kwargs)

            return [
                Commit(
                    sha=commit.sha,
                    message=commit.commit.message,
                    author=self._user_from_github(commit.author) if commit.author else None,
                    date=commit.commit.author.date,
                    url=commit.html_url,
                )
                for commit in list(commits)[:100]  # Limit to 100
            ]

        return await loop.run_in_executor(None, _fetch)

    async def get_file_content(
        self,
        repo_name: str,
        path: str,
        ref: Optional[str] = None,
    ) -> str:
        """
        Get file content from repository.

        Args:
            repo_name: Repository name
            path: File path
            ref: Branch, tag, or commit SHA

        Returns:
            File content as string
        """
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _fetch():
            repo = gh.get_repo(repo_name)
            content = repo.get_contents(path, ref=ref)
            return content.decoded_content.decode("utf-8")

        return await loop.run_in_executor(None, _fetch)

    async def list_releases(
        self,
        repo_name: str,
    ) -> List[Release]:
        """List releases."""
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _fetch():
            repo = gh.get_repo(repo_name)
            releases = repo.get_releases()

            return [
                Release(
                    tag_name=release.tag_name,
                    name=release.title or "",
                    body=release.body or "",
                    draft=release.draft,
                    prerelease=release.prerelease,
                    created_at=release.created_at,
                    published_at=release.published_at,
                    url=release.html_url,
                    assets=[
                        {
                            "name": asset.name,
                            "url": asset.browser_download_url,
                            "size": asset.size,
                        }
                        for asset in release.get_assets()
                    ],
                )
                for release in releases
            ]

        return await loop.run_in_executor(None, _fetch)

    async def create_release(
        self,
        repo_name: str,
        tag_name: str,
        name: str,
        body: str = "",
        draft: bool = False,
        prerelease: bool = False,
        target: str = "main",
    ) -> Release:
        """Create a release."""
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _create():
            repo = gh.get_repo(repo_name)
            release = repo.create_git_release(
                tag=tag_name,
                name=name,
                message=body,
                draft=draft,
                prerelease=prerelease,
                target_commitish=target,
            )

            return Release(
                tag_name=release.tag_name,
                name=release.title or "",
                body=release.body or "",
                draft=release.draft,
                prerelease=release.prerelease,
                url=release.html_url,
            )

        return await loop.run_in_executor(None, _create)

    async def get_workflow_runs(
        self,
        repo_name: str,
        workflow_name: Optional[str] = None,
        branch: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get GitHub Actions workflow runs.

        Args:
            repo_name: Repository name
            workflow_name: Workflow file name
            branch: Branch filter
            status: Status filter

        Returns:
            List of workflow run dicts
        """
        loop = asyncio.get_running_loop()
        gh = self._get_github()

        def _fetch():
            repo = gh.get_repo(repo_name)
            kwargs = {}
            if branch:
                kwargs["branch"] = branch
            if status:
                kwargs["status"] = status

            if workflow_name:
                workflow = repo.get_workflow(workflow_name)
                runs = workflow.get_runs(**kwargs)
            else:
                runs = repo.get_workflow_runs(**kwargs)

            return [
                {
                    "id": run.id,
                    "name": run.name,
                    "status": run.status,
                    "conclusion": run.conclusion,
                    "branch": run.head_branch,
                    "event": run.event,
                    "created_at": run.created_at,
                    "updated_at": run.updated_at,
                    "url": run.html_url,
                }
                for run in list(runs)[:50]
            ]

        return await loop.run_in_executor(None, _fetch)
