"""
Twitter/X API v2 client for ag3ntwerk social integration.

Supports posting tweets, threads, analytics, and profile metrics.

Environment variables:
- TWITTER_BEARER_TOKEN (for read operations)
- TWITTER_API_KEY
- TWITTER_API_SECRET
- TWITTER_ACCESS_TOKEN
- TWITTER_ACCESS_SECRET

Requirements:
    pip install httpx
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from ag3ntwerk.integrations.social.base import SocialClient
from ag3ntwerk.models.social import Platform, SocialPost

logger = logging.getLogger(__name__)


class TwitterClient(SocialClient):
    """
    Twitter/X API v2 client.

    Handles single tweets, threads (for content > 280 chars),
    engagement analytics, and profile metrics.
    """

    BASE_URL = "https://api.twitter.com/2"
    platform = Platform.TWITTER

    def __init__(
        self,
        bearer_token: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_secret: Optional[str] = None,
    ):
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
        self.api_key = api_key or os.getenv("TWITTER_API_KEY")
        self.api_secret = api_secret or os.getenv("TWITTER_API_SECRET")
        self.access_token = access_token or os.getenv("TWITTER_ACCESS_TOKEN")
        self.access_secret = access_secret or os.getenv("TWITTER_ACCESS_SECRET")
        self._user_id: Optional[str] = None
        self._authenticated = False

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }

    async def authenticate(self) -> bool:
        """Verify credentials and retrieve user ID."""
        if not self.bearer_token:
            raise ValueError("TWITTER_BEARER_TOKEN not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/users/me",
                headers=self._headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                self._user_id = data.get("data", {}).get("id")
                self._authenticated = True
            else:
                logger.warning(
                    "Twitter auth failed: %d %s",
                    resp.status_code,
                    resp.text[:200],
                )
            return self._authenticated

    async def publish(self, post: SocialPost) -> Dict[str, Any]:
        """Publish a tweet. Automatically threads if > 280 chars."""
        if len(post.content) > 280:
            return await self._publish_thread(post)

        payload = {"text": post.content}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/tweets",
                headers=self._headers,
                json=payload,
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                tweet_id = data.get("data", {}).get("id")
                return {
                    "success": True,
                    "post_id": tweet_id,
                    "post_url": f"https://twitter.com/i/status/{tweet_id}",
                }

            logger.error(
                "Twitter publish failed: %d %s",
                resp.status_code,
                resp.text[:300],
            )
            return {"success": False, "error": resp.text}

    async def _publish_thread(self, post: SocialPost) -> Dict[str, Any]:
        """Publish long content as a tweet thread."""
        chunks = self._split_into_tweets(post.content)
        tweet_ids: List[str] = []
        reply_to: Optional[str] = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            for chunk in chunks:
                payload: Dict[str, Any] = {"text": chunk}
                if reply_to:
                    payload["reply"] = {"in_reply_to_tweet_id": reply_to}

                resp = await client.post(
                    f"{self.BASE_URL}/tweets",
                    headers=self._headers,
                    json=payload,
                )

                if resp.status_code in (200, 201):
                    tweet_id = resp.json().get("data", {}).get("id")
                    tweet_ids.append(tweet_id)
                    reply_to = tweet_id
                else:
                    return {
                        "success": False,
                        "error": resp.text,
                        "partial_ids": tweet_ids,
                    }

        return {
            "success": True,
            "post_id": tweet_ids[0],
            "thread_ids": tweet_ids,
            "post_url": f"https://twitter.com/i/status/{tweet_ids[0]}",
        }

    @staticmethod
    def _split_into_tweets(content: str, max_len: int = 275) -> List[str]:
        """Split content into tweet-sized chunks with thread indicators."""
        words = content.split()
        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        for word in words:
            word_len = len(word) + (1 if current else 0)
            if current_len + word_len > max_len:
                chunks.append(" ".join(current))
                current = [word]
                current_len = len(word)
            else:
                current.append(word)
                current_len += word_len

        if current:
            chunks.append(" ".join(current))

        # Add thread numbering if multiple chunks
        if len(chunks) > 1:
            total = len(chunks)
            chunks = [f"{c} ({i + 1}/{total})" for i, c in enumerate(chunks)]

        return chunks

    async def schedule(self, post: SocialPost) -> Dict[str, Any]:
        """Twitter API doesn't support native scheduling."""
        return {
            "success": True,
            "scheduled": True,
            "scheduled_time": post.scheduled_time.isoformat() if post.scheduled_time else None,
            "requires_local_scheduler": True,
        }

    async def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get tweet engagement metrics."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/tweets/{post_id}",
                params={"tweet.fields": "public_metrics"},
                headers=self._headers,
            )
            if resp.status_code == 200:
                metrics = resp.json().get("data", {}).get("public_metrics", {})
                return {
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "impressions": metrics.get("impression_count", 0),
                }
            return {"error": resp.text}

    async def delete(self, post_id: str) -> bool:
        """Delete a tweet."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                f"{self.BASE_URL}/tweets/{post_id}",
                headers=self._headers,
            )
            return resp.status_code == 200

    async def get_profile_metrics(self) -> Dict[str, Any]:
        """Get follower and tweet count."""
        if not self._user_id:
            return {"error": "Not authenticated"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/users/{self._user_id}",
                params={"user.fields": "public_metrics"},
                headers=self._headers,
            )
            if resp.status_code == 200:
                metrics = resp.json().get("data", {}).get("public_metrics", {})
                return {
                    "followers": metrics.get("followers_count", 0),
                    "following": metrics.get("following_count", 0),
                    "tweets": metrics.get("tweet_count", 0),
                }
            return {"error": resp.text}
