"""
Repository Operations Abstraction.

Provides git repository management capabilities for ag3ntwerk agents,
particularly Foundry (Foundry) for engineering operations.
"""

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class CommitInfo:
    """Represents a git commit."""

    sha: str = ""
    short_sha: str = ""
    message: str = ""
    author: str = ""
    author_email: str = ""
    date: str = ""
    files_changed: List[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


@dataclass
class BranchInfo:
    """Represents a git branch."""

    name: str = ""
    is_current: bool = False
    last_commit: str = ""
    tracking: Optional[str] = None  # Remote tracking branch
    ahead: int = 0
    behind: int = 0


@dataclass
class TagInfo:
    """Represents a git tag."""

    name: str = ""
    commit_sha: str = ""
    message: str = ""
    tagger: Optional[str] = None
    date: Optional[str] = None
    is_annotated: bool = False


@dataclass
class PullRequest:
    """Represents a pull request."""

    id: str = field(default_factory=lambda: str(uuid4()))
    number: int = 0
    title: str = ""
    description: str = ""
    source_branch: str = ""
    target_branch: str = ""
    status: str = "open"  # open, merged, closed
    author: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    merged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    reviewers: List[str] = field(default_factory=list)
    approvals: List[str] = field(default_factory=list)
    commits: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RepositoryStats:
    """Repository statistics."""

    total_commits: int = 0
    total_branches: int = 0
    total_tags: int = 0
    contributors: int = 0
    open_prs: int = 0
    files_count: int = 0
    lines_of_code: int = 0
    last_commit_date: Optional[str] = None
    created_at: Optional[str] = None


class GitError(Exception):
    """Git operation error."""

    pass


class RepositoryManager:
    """
    Manages git repository operations.

    Used by Foundry (Foundry) and other agents for repository
    management, versioning, and release operations.
    """

    def __init__(self, repo_path: Path):
        """
        Initialize repository manager.

        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = Path(repo_path)
        if not self._is_git_repo():
            raise GitError(f"Not a git repository: {repo_path}")

    def _is_git_repo(self) -> bool:
        """Check if path is a git repository."""
        git_dir = self.repo_path / ".git"
        return git_dir.exists() and git_dir.is_dir()

    def _run_git(self, *args: str, check: bool = True) -> str:
        """
        Execute git command.

        Args:
            *args: Git command arguments
            check: Whether to raise on non-zero exit

        Returns:
            Command stdout

        Raises:
            GitError: If command fails and check is True
        """
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if check and result.returncode != 0:
                raise GitError(f"Git error: {result.stderr.strip()}")
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise GitError("Git command timed out")
        except FileNotFoundError:
            raise GitError("Git is not installed or not in PATH")

    def get_current_branch(self) -> str:
        """Get current branch name."""
        return self._run_git("branch", "--show-current")

    def get_branches(self, include_remote: bool = False) -> List[BranchInfo]:
        """
        List branches.

        Args:
            include_remote: Include remote tracking branches

        Returns:
            List of branch info
        """
        args = ["branch", "-vv"]
        if include_remote:
            args.append("-a")

        output = self._run_git(*args)
        branches = []

        for line in output.split("\n"):
            if not line.strip():
                continue

            is_current = line.startswith("*")
            line = line.lstrip("* ").strip()
            parts = line.split()

            if parts:
                name = parts[0]
                last_commit = parts[1] if len(parts) > 1 else ""

                # Parse tracking info if present
                tracking = None
                ahead = 0
                behind = 0

                if "[" in line and "]" in line:
                    tracking_start = line.index("[")
                    tracking_end = line.index("]")
                    # Ensure proper bounds
                    if tracking_end > tracking_start:
                        tracking_info = line[tracking_start + 1 : tracking_end]
                    else:
                        tracking_info = ""

                    if tracking_info and ":" in tracking_info:
                        tracking = tracking_info.split(":")[0]
                        status = tracking_info.split(":")[1].strip()
                        if "ahead" in status:
                            ahead = int(status.split("ahead")[1].split()[0].rstrip(","))
                        if "behind" in status:
                            behind = int(status.split("behind")[1].split()[0])
                    else:
                        tracking = tracking_info

                branches.append(
                    BranchInfo(
                        name=name,
                        is_current=is_current,
                        last_commit=last_commit,
                        tracking=tracking,
                        ahead=ahead,
                        behind=behind,
                    )
                )

        return branches

    def get_recent_commits(
        self,
        count: int = 10,
        branch: Optional[str] = None,
        since: Optional[str] = None,
    ) -> List[CommitInfo]:
        """
        Get recent commits.

        Args:
            count: Number of commits to retrieve
            branch: Branch to get commits from (default: current)
            since: Get commits since this date (e.g., "2024-01-01")

        Returns:
            List of commit info
        """
        args = ["log", f"-{count}", "--pretty=format:%H|%h|%s|%an|%ae|%ai"]

        if branch:
            args.append(branch)
        if since:
            args.append(f"--since={since}")

        output = self._run_git(*args)
        commits = []

        for line in output.split("\n"):
            if not line.strip():
                continue

            parts = line.split("|")
            if len(parts) >= 6:
                commits.append(
                    CommitInfo(
                        sha=parts[0],
                        short_sha=parts[1],
                        message=parts[2],
                        author=parts[3],
                        author_email=parts[4],
                        date=parts[5],
                        files_changed=[],
                    )
                )

        return commits

    def get_commit_details(self, sha: str) -> CommitInfo:
        """
        Get detailed commit information.

        Args:
            sha: Commit SHA

        Returns:
            Detailed commit info
        """
        # Get basic info
        output = self._run_git("show", sha, "--pretty=format:%H|%h|%s|%an|%ae|%ai", "--stat")

        lines = output.split("\n")
        if not lines:
            raise GitError(f"Commit not found: {sha}")

        parts = lines[0].split("|")
        commit = CommitInfo(
            sha=parts[0],
            short_sha=parts[1],
            message=parts[2],
            author=parts[3],
            author_email=parts[4],
            date=parts[5],
        )

        # Parse file stats
        for line in lines[1:]:
            if "|" in line and ("++" in line or "--" in line or "Bin" in line):
                file_name = line.split("|")[0].strip()
                commit.files_changed.append(file_name)
            elif "insertions" in line or "deletions" in line:
                stats = line.strip()
                if "insertion" in stats:
                    commit.insertions = int(stats.split()[0])
                if "deletion" in stats:
                    for part in stats.split(","):
                        if "deletion" in part:
                            commit.deletions = int(part.strip().split()[0])

        return commit

    def get_tags(self, pattern: Optional[str] = None) -> List[TagInfo]:
        """
        Get all tags.

        Args:
            pattern: Optional pattern to filter tags (e.g., "v*")

        Returns:
            List of tag info
        """
        args = [
            "tag",
            "-l",
            "--format=%(refname:short)|%(objectname:short)|%(subject)|%(taggername)|%(taggerdate:iso-strict)|%(objecttype)",
        ]
        if pattern:
            args.append(pattern)

        output = self._run_git(*args)
        tags = []

        for line in output.split("\n"):
            if not line.strip():
                continue

            parts = line.split("|")
            if parts:
                tags.append(
                    TagInfo(
                        name=parts[0],
                        commit_sha=parts[1] if len(parts) > 1 else "",
                        message=parts[2] if len(parts) > 2 else "",
                        tagger=parts[3] if len(parts) > 3 and parts[3] else None,
                        date=parts[4] if len(parts) > 4 and parts[4] else None,
                        is_annotated=parts[5] == "tag" if len(parts) > 5 else False,
                    )
                )

        return tags

    def get_latest_tag(self) -> Optional[str]:
        """Get the latest tag."""
        try:
            return self._run_git("describe", "--tags", "--abbrev=0")
        except GitError:
            return None

    def get_file_structure(
        self,
        path: str = ".",
        depth: int = 2,
        include_hidden: bool = False,
    ) -> Dict[str, Any]:
        """
        Get repository file structure.

        Args:
            path: Path relative to repo root
            depth: Maximum depth to traverse
            include_hidden: Include hidden files/directories

        Returns:
            Dictionary representing file structure
        """
        result: Dict[str, Any] = {}
        target = self.repo_path / path

        if not target.exists():
            return result

        def _traverse(current: Path, current_depth: int) -> Dict[str, Any]:
            if current_depth > depth:
                return {}

            items: Dict[str, Any] = {}
            try:
                for item in current.iterdir():
                    if not include_hidden and item.name.startswith("."):
                        continue

                    if item.is_dir():
                        items[item.name] = {
                            "type": "directory",
                            "children": (
                                _traverse(item, current_depth + 1) if current_depth < depth else {}
                            ),
                        }
                    else:
                        items[item.name] = {
                            "type": "file",
                            "size": item.stat().st_size,
                        }
            except PermissionError:
                pass

            return items

        return _traverse(target, 1)

    def generate_changelog(
        self,
        from_ref: str,
        to_ref: str = "HEAD",
        group_by_type: bool = True,
    ) -> str:
        """
        Generate changelog between refs.

        Args:
            from_ref: Starting reference (tag, branch, commit)
            to_ref: Ending reference
            group_by_type: Group commits by conventional commit type

        Returns:
            Formatted changelog
        """
        output = self._run_git("log", f"{from_ref}..{to_ref}", "--pretty=format:- %s (%h)")

        if not group_by_type:
            return output

        # Group by conventional commit types
        groups: Dict[str, List[str]] = {
            "Features": [],
            "Bug Fixes": [],
            "Documentation": [],
            "Performance": [],
            "Refactoring": [],
            "Tests": [],
            "Chores": [],
            "Other": [],
        }

        type_map = {
            "feat": "Features",
            "fix": "Bug Fixes",
            "docs": "Documentation",
            "perf": "Performance",
            "refactor": "Refactoring",
            "test": "Tests",
            "chore": "Chores",
        }

        for line in output.split("\n"):
            if not line.strip():
                continue

            # Try to extract conventional commit type
            commit_line = line.lstrip("- ")
            category = "Other"

            for prefix, group_name in type_map.items():
                if commit_line.lower().startswith(prefix + ":") or commit_line.lower().startswith(
                    prefix + "("
                ):
                    category = group_name
                    break

            groups[category].append(line)

        # Build grouped changelog
        changelog_parts = []
        for group_name, commits in groups.items():
            if commits:
                changelog_parts.append(f"\n### {group_name}\n")
                changelog_parts.extend(commits)

        return "\n".join(changelog_parts)

    def get_diff_stats(
        self,
        from_ref: str,
        to_ref: str = "HEAD",
    ) -> Dict[str, Any]:
        """
        Get diff statistics between refs.

        Args:
            from_ref: Starting reference
            to_ref: Ending reference

        Returns:
            Diff statistics
        """
        output = self._run_git("diff", "--stat", f"{from_ref}..{to_ref}")

        stats = {
            "files_changed": 0,
            "insertions": 0,
            "deletions": 0,
            "files": [],
        }

        lines = output.split("\n")
        for line in lines:
            if "|" in line:
                file_name = line.split("|")[0].strip()
                stats["files"].append(file_name)
            elif "files changed" in line or "file changed" in line:
                parts = line.strip().split(",")
                for part in parts:
                    if "file" in part and "changed" in part:
                        stats["files_changed"] = int(part.split()[0])
                    elif "insertion" in part:
                        stats["insertions"] = int(part.strip().split()[0])
                    elif "deletion" in part:
                        stats["deletions"] = int(part.strip().split()[0])

        return stats

    def get_contributors(self) -> List[Dict[str, Any]]:
        """
        Get repository contributors.

        Returns:
            List of contributor info
        """
        output = self._run_git("shortlog", "-sne", "HEAD")
        contributors = []

        for line in output.split("\n"):
            if not line.strip():
                continue

            parts = line.strip().split("\t")
            if len(parts) >= 2:
                count = int(parts[0].strip())
                name_email = parts[1]

                # Parse name and email
                if "<" in name_email and ">" in name_email:
                    name = name_email.split("<")[0].strip()
                    email = name_email.split("<")[1].rstrip(">")
                else:
                    name = name_email
                    email = ""

                contributors.append(
                    {
                        "name": name,
                        "email": email,
                        "commits": count,
                    }
                )

        return contributors

    def get_repository_stats(self) -> RepositoryStats:
        """
        Get overall repository statistics.

        Returns:
            Repository statistics
        """
        stats = RepositoryStats()

        # Total commits
        try:
            stats.total_commits = int(self._run_git("rev-list", "--count", "HEAD"))
        except (GitError, ValueError):
            pass

        # Branches
        stats.total_branches = len(self.get_branches())

        # Tags
        stats.total_tags = len(self.get_tags())

        # Contributors
        stats.contributors = len(self.get_contributors())

        # Last commit
        commits = self.get_recent_commits(count=1)
        if commits:
            stats.last_commit_date = commits[0].date

        return stats

    def create_branch(self, name: str, from_ref: str = "HEAD") -> None:
        """
        Create a new branch.

        Args:
            name: Branch name
            from_ref: Reference to branch from
        """
        self._run_git("branch", name, from_ref)

    def checkout_branch(self, name: str, create: bool = False) -> None:
        """
        Checkout a branch.

        Args:
            name: Branch name
            create: Create branch if it doesn't exist
        """
        if create:
            self._run_git("checkout", "-b", name)
        else:
            self._run_git("checkout", name)

    def create_tag(
        self,
        name: str,
        message: Optional[str] = None,
        ref: str = "HEAD",
    ) -> None:
        """
        Create a tag.

        Args:
            name: Tag name
            message: Tag message (creates annotated tag)
            ref: Reference to tag
        """
        if message:
            self._run_git("tag", "-a", name, "-m", message, ref)
        else:
            self._run_git("tag", name, ref)

    def get_uncommitted_changes(self) -> Dict[str, List[str]]:
        """
        Get uncommitted changes.

        Returns:
            Dictionary with staged, unstaged, and untracked files
        """
        result = {
            "staged": [],
            "unstaged": [],
            "untracked": [],
        }

        # Staged changes
        staged_output = self._run_git("diff", "--cached", "--name-only")
        result["staged"] = [f for f in staged_output.split("\n") if f.strip()]

        # Unstaged changes
        unstaged_output = self._run_git("diff", "--name-only")
        result["unstaged"] = [f for f in unstaged_output.split("\n") if f.strip()]

        # Untracked files
        untracked_output = self._run_git("ls-files", "--others", "--exclude-standard")
        result["untracked"] = [f for f in untracked_output.split("\n") if f.strip()]

        return result
