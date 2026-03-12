"""
HTTP delivery with retry logic for webhooks.
"""

import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

import aiohttp

from ag3ntwerk.core.webhooks._types import (
    DeliveryAttempt,
    DeliveryRecord,
    DeliveryStatus,
    Webhook,
    WebhookEvent,
)
from ag3ntwerk.core.webhooks._signing import PayloadSigner

logger = logging.getLogger(__name__)


class DeliveryService:
    """Handles HTTP delivery of webhook events with retries."""

    def __init__(
        self,
        semaphore: asyncio.Semaphore,
        dead_letter_queue: deque,
        delivery_history: deque,
        get_session: Callable[[], Awaitable[aiohttp.ClientSession]],
        signer: PayloadSigner,
    ):
        self._semaphore = semaphore
        self._dlq = dead_letter_queue
        self._history = delivery_history
        self._get_session = get_session
        self._signer = signer

    async def deliver(self, webhook: Webhook, event: WebhookEvent) -> DeliveryRecord:
        """
        Deliver an event to a webhook with retries.

        Args:
            webhook: Target webhook
            event: Event to deliver

        Returns:
            Delivery record
        """
        record = DeliveryRecord(
            event_id=event.id,
            webhook_id=webhook.id,
            status=DeliveryStatus.PENDING,
        )

        webhook.record_delivery()

        async with self._semaphore:
            for attempt in range(webhook.max_retries + 1):
                try:
                    result = await self.attempt_delivery(webhook, event, attempt + 1)
                    record.attempts.append(result)

                    if result.status_code and 200 <= result.status_code < 300:
                        record.status = DeliveryStatus.DELIVERED
                        record.delivered_at = datetime.now(timezone.utc)
                        webhook.successful_deliveries += 1
                        webhook.last_delivery_at = record.delivered_at
                        webhook.consecutive_failures = 0
                        webhook.circuit_breaker.record_success()
                        break
                    else:
                        webhook.circuit_breaker.record_failure()
                        webhook.consecutive_failures += 1

                        if attempt < webhook.max_retries:
                            record.status = DeliveryStatus.RETRYING
                            delay = webhook.retry_delay * (2**attempt)
                            await asyncio.sleep(min(delay, 60))
                        else:
                            record.status = DeliveryStatus.FAILED
                            webhook.failed_deliveries += 1
                            webhook.last_failure_at = datetime.now(timezone.utc)
                            self._dlq.append(
                                (event, webhook.id, f"Status code: {result.status_code}")
                            )

                except Exception as e:
                    webhook.circuit_breaker.record_failure()
                    webhook.consecutive_failures += 1

                    record.attempts.append(
                        DeliveryAttempt(
                            attempt_number=attempt + 1,
                            timestamp=datetime.now(timezone.utc),
                            status_code=None,
                            response_body=None,
                            error=str(e),
                            duration_ms=0,
                        )
                    )

                    if attempt < webhook.max_retries:
                        record.status = DeliveryStatus.RETRYING
                        delay = webhook.retry_delay * (2**attempt)
                        await asyncio.sleep(min(delay, 60))
                    else:
                        record.status = DeliveryStatus.FAILED
                        webhook.failed_deliveries += 1
                        webhook.last_failure_at = datetime.now(timezone.utc)
                        self._dlq.append((event, webhook.id, str(e)))

        webhook.total_deliveries += 1
        self._history.append(record)

        if record.status == DeliveryStatus.FAILED:
            logger.warning(
                f"Webhook delivery failed after {record.attempt_count} attempts",
                webhook_id=webhook.id,
                event_id=event.id,
                consecutive_failures=webhook.consecutive_failures,
            )

            if webhook.consecutive_failures >= 50:
                webhook.active = False
                logger.error(
                    f"Auto-disabled webhook after {webhook.consecutive_failures} consecutive failures",
                    webhook_id=webhook.id,
                )

        return record

    async def attempt_delivery(
        self,
        webhook: Webhook,
        event: WebhookEvent,
        attempt_number: int,
    ) -> DeliveryAttempt:
        """
        Attempt a single delivery.

        Args:
            webhook: Target webhook
            event: Event to deliver
            attempt_number: Current attempt number

        Returns:
            Delivery attempt record
        """
        start_time = datetime.now(timezone.utc)
        body = json.dumps(event.to_dict())

        headers = {
            "X-Webhook-Event": event.event_type,
            "X-Webhook-ID": webhook.id,
            "X-Event-ID": event.id,
            "X-Delivery-Attempt": str(attempt_number),
            "X-Webhook-Timestamp": event.timestamp.isoformat(),
        }

        headers.update(webhook.custom_headers)

        if webhook.secret:
            signature = self._signer.sign(body, webhook.secret)
            headers["X-Webhook-Signature"] = signature

        session = await self._get_session()

        try:
            async with session.post(
                webhook.url,
                data=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=webhook.timeout),
            ) as response:
                response_body = await response.text()
                duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

                return DeliveryAttempt(
                    attempt_number=attempt_number,
                    timestamp=start_time,
                    status_code=response.status,
                    response_body=response_body[:1000],
                    error=None,
                    duration_ms=duration,
                )

        except asyncio.TimeoutError:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return DeliveryAttempt(
                attempt_number=attempt_number,
                timestamp=start_time,
                status_code=None,
                response_body=None,
                error="Request timed out",
                duration_ms=duration,
            )
