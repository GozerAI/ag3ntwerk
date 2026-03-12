"""
Workbench Runner Package - Container runtime abstraction.

Provides interfaces and implementations for running workspaces in
isolated containers.
"""

from ag3ntwerk.modules.workbench.runner.base import BaseRunner, RunnerCapabilities
from ag3ntwerk.modules.workbench.runner.docker_runner import DockerRunner
from ag3ntwerk.modules.workbench.runner.fake_runner import FakeRunner

__all__ = [
    "BaseRunner",
    "RunnerCapabilities",
    "DockerRunner",
    "FakeRunner",
]
