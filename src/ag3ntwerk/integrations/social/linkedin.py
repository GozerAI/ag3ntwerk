"""
LinkedIn API v2 client for ag3ntwerk social integration.

Requires OAuth 2.0 token with permissions:
- w_member_social (post as member)
- r_liteprofile (read profile)
- r_organization_social (if posting as org)

Environment variables:
- LINKEDIN_ACCESS_TOKEN
- LINKEDIN_PERSON_URN (urn:li:person:xxx)
- LINKEDIN_ORG_URN (optional, urn:li:organization:xxx)

Requirements:
    pip install httpx
"""

import logging
import os
from typing import Any, Dict, Optional

import httpx

from ag3ntwerk.integrations.social.base import SocialClient
from ag3ntwerk.models.social import Platform, SocialPost

logger = logging.getLogger(__name__)


class LinkedInClient(SocialClient):
    """
    LinkedIn API v2 client.

    Publishes posts as a person or organization, retrieves
    engagement metrics, and manages content lifecycle.
    """

    BASE_URL = "https://api.linkedin.com/v2"
    platform = Platform.LINKEDIN

    def __init__(
        self,
        access_token: Optional[str] = None,
        person_urn: Optional[str] = None,
        org_urn: Optional[str] = None,
    ):
        self.access_token = access_token or os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.person_urn = person_urn or os.getenv("LINKEDIN_PERSON_URN")
        self.org_urn = org_urn or os.getenv("LINKEDIN_ORG_URN")
        self._authenticated = False

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202401",
        }

    async def authenticate(self) -> bool:
        """Verify token validity by calling userinfo endpoint."""
        if not self.access_token:
            raise ValueError("LINKEDIN_ACCESS_TOKEN not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/userinfo",
                headers=self._headers,
            )
            self._authenticated = resp.status_code == 200
            if not self._authenticated:
                logger.warning(
                    "LinkedIn auth failed: %d %s",
                    resp.status_code,
                    resp.text[:200],
                )
            return self._authenticated

    async def publish(self, post: SocialPost) -> Dict[str, Any]:
        """Publish a post to LinkedIn via UGC Posts API."""
        author = self.org_urn or self.person_urn

        payload: Dict[str, Any] = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post.content},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        # Attach article link if present
        if post.link:
            share_content = payload["specificContent"]["com.linkedin.ugc.ShareContent"]
            share_content["shareMediaCategory"] = "ARTICLE"
            share_content["media"] = [{"status": "READY", "originalUrl": post.link}]

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/ugcPosts",
                headers=self._headers,
                json=payload,
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                post_id = data.get("id", "")
                return {
                    "success": True,
                    "post_id": post_id,
                    "post_url": f"https://www.linkedin.com/feed/update/{post_id}",
                }

            logger.error(
                "LinkedIn publish failed: %d %s",
                resp.status_code,
                resp.text[:300],
            )
            return {
                "success": False,
                "error": resp.text,
                "status_code": resp.status_code,
            }

    async def schedule(self, post: SocialPost) -> Dict[str, Any]:
        """LinkedIn doesn't support native scheduling."""
        return {
            "success": True,
            "scheduled": True,
            "scheduled_time": post.scheduled_time.isoformat() if post.scheduled_time else None,
            "requires_local_scheduler": True,
        }

    async def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get post engagement metrics."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/socialActions/{post_id}",
                headers=self._headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "likes": data.get("likesSummary", {}).get("totalLikes", 0),
                    "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
                    "shares": data.get("sharesSummary", {}).get("totalShares", 0),
                }
            return {"error": resp.text}

    async def delete(self, post_id: str) -> bool:
        """Delete a LinkedIn post."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                f"{self.BASE_URL}/ugcPosts/{post_id}",
                headers=self._headers,
            )
            return resp.status_code == 204

    async def get_profile_metrics(self) -> Dict[str, Any]:
        """Get profile/page metrics."""
        # LinkedIn follower stats require Marketing API access
        return {
            "platform": "linkedin",
            "authenticated": self._authenticated,
            "note": "Follower API requires Marketing Developer Platform access",
        }
