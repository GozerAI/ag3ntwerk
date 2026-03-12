"""
Workbench Deployers Package.

Provides deployment implementations for different targets:
- Vercel: Deploy to Vercel platform
- Docker: Push to Docker registry
- Local: Local preview (existing port exposure)
"""

from typing import TYPE_CHECKING

from ag3ntwerk.modules.workbench.deployers.base import BaseDeployer, DeployOptions
from ag3ntwerk.modules.workbench.deployers.docker import DockerRegistryDeployer
from ag3ntwerk.modules.workbench.deployers.local import LocalDeployer
from ag3ntwerk.modules.workbench.deployers.vercel import VercelDeployer
from ag3ntwerk.modules.workbench.pipeline_schemas import DeploymentTarget

if TYPE_CHECKING:
    pass


def get_deployer(target: DeploymentTarget) -> BaseDeployer:
    """
    Get the appropriate deployer for a deployment target.

    Args:
        target: Deployment target type

    Returns:
        Configured deployer instance

    Raises:
        ValueError: If target is not supported
    """
    deployers = {
        DeploymentTarget.VERCEL: VercelDeployer,
        DeploymentTarget.DOCKER_REGISTRY: DockerRegistryDeployer,
        DeploymentTarget.LOCAL_PREVIEW: LocalDeployer,
    }

    deployer_class = deployers.get(target)
    if deployer_class is None:
        raise ValueError(f"Unsupported deployment target: {target}")

    return deployer_class()


__all__ = [
    "BaseDeployer",
    "DeployOptions",
    "VercelDeployer",
    "DockerRegistryDeployer",
    "LocalDeployer",
    "get_deployer",
]
