"""
Abstract base class for social platform clients.

All social platform integrations implement this interface,
allowing the SocialDistributionGateway to treat them uniformly.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from ag3ntwerk.models.social import Platform, SocialPost


class SocialClient(ABC):
    """
    Abstract base for social platform clients.

    Each platform (LinkedIn, Twitter, etc.) provides a concrete
    implementation. The gateway uses these clients to publish,
    schedule, and track posts across platforms.
    """

    platform: Platform

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Verify credentials and establish connection.

        Returns:
            True if authentication succeeded.

        Raises:
            ValueError: If required credentials are missing.
        """

    @abstractmethod
    async def publish(self, post: SocialPost) -> Dict[str, Any]:
        """
        Publish a post immediately.

        Args:
            post: The post to publish.

        Returns:
            Dict with at least 'success' (bool), and on success
            'post_id' and 'post_url'.
        """

    @abstractmethod
    async def schedule(self, post: SocialPost) -> Dict[str, Any]:
        """
        Schedule a post for later publication.

        Platforms without native scheduling return a marker indicating
        the local scheduler should handle it.

        Args:
            post: The post to schedule (must have scheduled_time set).

        Returns:
            Dict with scheduling result.
        """

    @abstractmethod
    async def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """
        Get engagement metrics for a published post.

        Args:
            post_id: Platform-specific post identifier.

        Returns:
            Dict with engagement metrics (likes, comments, shares, etc.).
        """

    @abstractmethod
    async def delete(self, post_id: str) -> bool:
        """
        Delete a published post.

        Args:
            post_id: Platform-specific post identifier.

        Returns:
            True if deletion succeeded.
        """

    @abstractmethod
    async def get_profile_metrics(self) -> Dict[str, Any]:
        """
        Get account-level metrics (followers, etc.).

        Returns:
            Dict with profile/account metrics.
        """
