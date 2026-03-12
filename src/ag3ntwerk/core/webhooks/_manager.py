"""
WebhookManager facade — thin coordinator that owns state and delegates to collaborators.
"""

import asyncio
import logging
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

import aiohttp

from ag3ntwerk.core.webhooks._types import (
    CircuitState,
    DeliveryRecord,
    DeliveryStatus,
    Webhook,
    WebhookEvent,
    WebhookFilter,
)
from ag3ntwerk.core.webhooks._url_validator import URLValidator
from ag3ntwerk.core.webhooks._signing import PayloadSigner
from ag3ntwerk.core.webhooks._delivery import DeliveryService
from ag3ntwerk.core.webhooks._batch import BatchProcessor
from ag3ntwerk.core.webhooks._monitoring import WebhookMonitor

logger = logging.getLogger(__name__)


class WebhookManager:
    """
    Central manager for webhook subscriptions and event dispatch.

    Delegates to internal collaborators for each responsibility:
    - URLValidator: SSRF protection and URL validation
    - PayloadSigner: HMAC-SHA256 signing and verification
    - DeliveryService: HTTP delivery with retry loop
    - BatchProcessor: Batch event queuing and flush
    - WebhookMonitor: History, stats, DLQ, health
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        history_size: int = 1000,
        allow_localhost: bool = False,
        allow_http: bool = True,
        batch_size: int = 100,
        batch_timeout: float = 1.0,
    ):
        # Owned shared state
        self._webhooks: Dict[str, Webhook] = {}
        self._delivery_history: deque[DeliveryRecord] = deque(maxlen=history_size)
        self._dead_letter_queue: deque[tuple[WebhookEvent, str, str]] = deque(maxlen=1000)
        self._paused_webhooks: Set[str] = set()
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()

        # Compose collaborators
        self._url_validator = URLValidator(
            allow_localhost=allow_localhost,
            allow_http=allow_http,
        )
        self._signer = PayloadSigner()
        self._delivery = DeliveryService(
            semaphore=self._semaphore,
            dead_letter_queue=self._dead_letter_queue,
            delivery_history=self._delivery_history,
            get_session=self._get_session,
            signer=self._signer,
        )
        self._batch = BatchProcessor(
            batch_size=batch_size,
            batch_timeout=batch_timeout,
            get_webhooks=lambda: self._webhooks,
            get_paused=lambda: self._paused_webhooks,
            deliver=self._delivery.deliver,
        )
        self._monitor = WebhookMonitor(
            webhooks=self._webhooks,
            delivery_history=self._delivery_history,
            dead_letter_queue=self._dead_letter_queue,
            paused_webhooks=self._paused_webhooks,
            deliver_fn=self._delivery.deliver,
            attempt_delivery_fn=self._delivery.attempt_delivery,
            get_batch_pending=lambda: self._batch.pending_count,
        )

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60),
                headers={"Content-Type": "application/json"},
            )
        return self._session

    async def close(self) -> None:
        """Close the manager and cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def register(
        self,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        description: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 30.0,
        rate_limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Webhook:
        """Register a new webhook subscription."""
        is_valid, error_msg = await self._url_validator.validate(url)
        if not is_valid:
            raise ValueError(f"Invalid webhook URL: {error_msg}")

        webhook_id = str(uuid.uuid4())

        webhook_filter = None
        if filters:
            webhook_filter = WebhookFilter(
                field_equals=filters.get("field_equals", {}),
                field_contains=filters.get("field_contains", {}),
                field_regex=filters.get("field_regex", {}),
            )

        webhook = Webhook(
            id=webhook_id,
            url=url,
            events=set(events),
            secret=secret,
            description=description,
            max_retries=max_retries,
            timeout=timeout,
            rate_limit=rate_limit,
            filters=webhook_filter,
            custom_headers=custom_headers or {},
        )

        async with self._lock:
            self._webhooks[webhook_id] = webhook

        logger.info(
            f"Registered webhook",
            webhook_id=webhook_id,
            url=url,
            events=events,
        )

        return webhook

    async def unregister(self, webhook_id: str) -> bool:
        """Unregister a webhook."""
        async with self._lock:
            if webhook_id in self._webhooks:
                del self._webhooks[webhook_id]
                logger.info(f"Unregistered webhook: {webhook_id}")
                return True
        return False

    async def update(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        active: Optional[bool] = None,
        secret: Optional[str] = None,
    ) -> Optional[Webhook]:
        """Update a webhook subscription."""
        async with self._lock:
            webhook = self._webhooks.get(webhook_id)
            if not webhook:
                return None

            if url is not None:
                is_valid, error_msg = await self._url_validator.validate(url)
                if not is_valid:
                    raise ValueError(f"Invalid webhook URL: {error_msg}")
                webhook.url = url
            if events is not None:
                webhook.events = set(events)
            if active is not None:
                webhook.active = active
            if secret is not None:
                webhook.secret = secret

            webhook.updated_at = datetime.now(timezone.utc)
            return webhook

    def get(self, webhook_id: str) -> Optional[Webhook]:
        """Get a webhook by ID."""
        return self._webhooks.get(webhook_id)

    def list_webhooks(self, active_only: bool = False) -> List[Webhook]:
        """List all registered webhooks."""
        webhooks = list(self._webhooks.values())
        if active_only:
            webhooks = [w for w in webhooks if w.active]
        return webhooks

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch(
        self,
        event_type: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Dispatch an event to all matching webhooks."""
        event = WebhookEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            payload=payload,
            metadata=metadata or {},
        )

        matching = []
        skipped_reasons: Dict[str, List[str]] = {
            "inactive": [],
            "paused": [],
            "circuit_open": [],
            "rate_limited": [],
            "filtered": [],
        }

        for w in self._webhooks.values():
            if not w.active:
                skipped_reasons["inactive"].append(w.id)
                continue
            if w.id in self._paused_webhooks:
                skipped_reasons["paused"].append(w.id)
                continue
            if not w.matches_event(event_type):
                continue
            if not w.circuit_breaker.can_execute():
                skipped_reasons["circuit_open"].append(w.id)
                continue
            if w.is_rate_limited():
                skipped_reasons["rate_limited"].append(w.id)
                continue
            if w.filters and not w.filters.matches(payload):
                skipped_reasons["filtered"].append(w.id)
                continue
            matching.append(w)

        if not matching:
            logger.debug(
                f"No webhooks matched event: {event_type}",
                skipped=skipped_reasons,
            )
            return event.id

        tasks = [self._delivery.deliver(webhook, event) for webhook in matching]
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(
            f"Dispatched event to {len(matching)} webhooks",
            event_id=event.id,
            event_type=event_type,
            skipped=sum(len(v) for v in skipped_reasons.values()),
        )

        return event.id

    async def dispatch_batch(
        self,
        events: List[tuple[str, Dict[str, Any], Optional[Dict[str, Any]]]],
    ) -> List[str]:
        """Dispatch multiple events efficiently."""
        event_ids = []
        for event_type, payload, metadata in events:
            event_id = await self.dispatch(event_type, payload, metadata)
            event_ids.append(event_id)
        return event_ids

    # ------------------------------------------------------------------
    # Batch (delegate)
    # ------------------------------------------------------------------

    def queue_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Queue an event for batch dispatch."""
        return self._batch.queue_event(event_type, payload, metadata)

    # ------------------------------------------------------------------
    # Signing (delegate)
    # ------------------------------------------------------------------

    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify a webhook signature."""
        return self._signer.verify(payload, signature, secret)

    # ------------------------------------------------------------------
    # Pause / Resume
    # ------------------------------------------------------------------

    async def pause_webhook(self, webhook_id: str) -> bool:
        """Pause a webhook (stop delivering events)."""
        if webhook_id not in self._webhooks:
            return False
        self._paused_webhooks.add(webhook_id)
        logger.info(f"Paused webhook: {webhook_id}")
        return True

    async def resume_webhook(self, webhook_id: str) -> bool:
        """Resume a paused webhook."""
        if webhook_id in self._paused_webhooks:
            self._paused_webhooks.discard(webhook_id)
            logger.info(f"Resumed webhook: {webhook_id}")
            return True
        return False

    async def reset_circuit_breaker(self, webhook_id: str) -> bool:
        """Reset a webhook's circuit breaker."""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return False

        webhook.circuit_breaker.state = CircuitState.CLOSED
        webhook.circuit_breaker.failure_count = 0
        webhook.circuit_breaker.success_count = 0
        logger.info(f"Reset circuit breaker for webhook: {webhook_id}")
        return True

    # ------------------------------------------------------------------
    # Monitoring (delegate)
    # ------------------------------------------------------------------

    def get_delivery_history(
        self,
        webhook_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[DeliveryRecord]:
        return self._monitor.get_delivery_history(webhook_id, event_type, limit)

    def get_stats(self) -> Dict[str, Any]:
        return self._monitor.get_stats()

    def get_dead_letter_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._monitor.get_dead_letter_queue(limit)

    async def retry_dead_letter(
        self,
        event_id: str,
        webhook_id: Optional[str] = None,
    ) -> bool:
        return await self._monitor.retry_dead_letter(event_id, webhook_id)

    async def clear_dead_letter_queue(self) -> int:
        return await self._monitor.clear_dead_letter_queue()

    async def test_webhook(self, webhook_id: str) -> Dict[str, Any]:
        return await self._monitor.test_webhook(webhook_id)

    def get_webhook_health(self, webhook_id: str) -> Dict[str, Any]:
        return self._monitor.get_webhook_health(webhook_id)

    def add_event_handler(
        self,
        event_type: str,
        handler: Callable[[WebhookEvent], Any],
    ) -> None:
        self._monitor.add_event_handler(event_type, handler, self._event_handlers)
