"""
Event System and Webhook Management
Event-driven architecture with webhook support for integrations
"""

import asyncio
import hashlib
import hmac
import logging
import time
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import aiohttp

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """System event types"""
    # Session events
    SESSION_CREATED = "session.created"
    SESSION_UPDATED = "session.updated"
    SESSION_DELETED = "session.deleted"

    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"

    # Workflow events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_STEP_COMPLETED = "workflow.step.completed"

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"

    # File events
    FILE_UPLOADED = "file.uploaded"
    FILE_PROCESSED = "file.processed"
    FILE_DELETED = "file.deleted"

    # Cost events
    BUDGET_WARNING = "budget.warning"
    BUDGET_EXCEEDED = "budget.exceeded"

    # Plugin events
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"

    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"

    # Custom events
    CUSTOM = "custom"


class WebhookStatus(str, Enum):
    """Webhook delivery status"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class Event:
    """System event"""
    id: str
    type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source: str = "manus_ai"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "source": self.source,
            "metadata": self.metadata
        }


@dataclass
class WebhookEndpoint:
    """Webhook endpoint configuration"""
    id: str
    url: str
    secret: str  # For HMAC signature verification
    events: Set[EventType]
    active: bool = True
    description: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    retry_config: Dict[str, int] = field(default_factory=lambda: {
        "max_retries": 3,
        "retry_delay": 60,
        "timeout": 30
    })
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebhookDelivery:
    """Webhook delivery record"""
    id: str
    webhook_id: str
    event_id: str
    status: WebhookStatus
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


# ==================== Event Bus ====================

class EventBus:
    """Central event bus for pub/sub messaging"""

    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.logger = logging.getLogger(__name__)
        self.event_history: List[Event] = []
        self.max_history = 1000

    def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], None]
    ):
        """
        Subscribe to event type

        Args:
            event_type: Event type to subscribe to
            handler: Async function to handle event
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(handler)
        self.logger.info(f"Subscribed to {event_type.value}")

    def unsubscribe(
        self,
        event_type: EventType,
        handler: Callable
    ):
        """Unsubscribe from event type"""
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(handler)
                self.logger.info(f"Unsubscribed from {event_type.value}")
            except ValueError:
                pass

    async def publish(self, event: Event):
        """
        Publish event to all subscribers

        Args:
            event: Event to publish
        """
        self.logger.info(f"Publishing event: {event.type.value} (ID: {event.id})")

        # Store in history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        # Notify subscribers
        if event.type in self.subscribers:
            tasks = []
            for handler in self.subscribers[event.type]:
                tasks.append(self._safe_call_handler(handler, event))

            # Execute all handlers concurrently
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_call_handler(self, handler: Callable, event: Event):
        """Safely call event handler"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            self.logger.error(f"Error in event handler: {e}")

    def get_event_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get event history"""
        events = self.event_history

        if event_type:
            events = [e for e in events if e.type == event_type]

        return events[-limit:]


# ==================== Webhook Manager ====================

class WebhookManager:
    """Manages webhook endpoints and deliveries"""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.webhooks: Dict[str, WebhookEndpoint] = {}
        self.deliveries: Dict[str, WebhookDelivery] = {}
        self.logger = logging.getLogger(__name__)

        # Subscribe to all events for webhook delivery
        for event_type in EventType:
            event_bus.subscribe(event_type, self._handle_event)

    async def register_webhook(
        self,
        url: str,
        events: List[EventType],
        secret: Optional[str] = None,
        description: str = "",
        headers: Optional[Dict[str, str]] = None
    ) -> WebhookEndpoint:
        """
        Register new webhook endpoint

        Args:
            url: Webhook URL
            events: List of event types to subscribe to
            secret: Secret for HMAC signature
            description: Webhook description
            headers: Custom headers to include

        Returns:
            Webhook endpoint configuration
        """
        import uuid

        webhook_id = str(uuid.uuid4())
        secret = secret or self._generate_secret()

        webhook = WebhookEndpoint(
            id=webhook_id,
            url=url,
            secret=secret,
            events=set(events),
            description=description,
            headers=headers or {}
        )

        self.webhooks[webhook_id] = webhook
        self.logger.info(f"Registered webhook: {webhook_id} ({url})")

        return webhook

    def _generate_secret(self) -> str:
        """Generate webhook secret"""
        import secrets
        return secrets.token_urlsafe(32)

    async def unregister_webhook(self, webhook_id: str) -> bool:
        """Unregister webhook"""
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            self.logger.info(f"Unregistered webhook: {webhook_id}")
            return True
        return False

    async def update_webhook(
        self,
        webhook_id: str,
        **updates
    ) -> bool:
        """Update webhook configuration"""
        if webhook_id not in self.webhooks:
            return False

        webhook = self.webhooks[webhook_id]

        for key, value in updates.items():
            if hasattr(webhook, key):
                setattr(webhook, key, value)

        self.logger.info(f"Updated webhook: {webhook_id}")
        return True

    def get_webhook(self, webhook_id: str) -> Optional[WebhookEndpoint]:
        """Get webhook by ID"""
        return self.webhooks.get(webhook_id)

    def list_webhooks(
        self,
        active_only: bool = True
    ) -> List[WebhookEndpoint]:
        """List all webhooks"""
        webhooks = list(self.webhooks.values())

        if active_only:
            webhooks = [w for w in webhooks if w.active]

        return webhooks

    async def _handle_event(self, event: Event):
        """Handle event and trigger webhooks"""
        # Find webhooks subscribed to this event type
        matching_webhooks = [
            webhook for webhook in self.webhooks.values()
            if event.type in webhook.events and webhook.active
        ]

        if not matching_webhooks:
            return

        self.logger.info(f"Delivering event {event.id} to {len(matching_webhooks)} webhooks")

        # Deliver to all matching webhooks
        tasks = []
        for webhook in matching_webhooks:
            tasks.append(self._deliver_webhook(webhook, event))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _deliver_webhook(
        self,
        webhook: WebhookEndpoint,
        event: Event
    ):
        """Deliver event to webhook endpoint"""
        import uuid

        delivery_id = str(uuid.uuid4())

        delivery = WebhookDelivery(
            id=delivery_id,
            webhook_id=webhook.id,
            event_id=event.id,
            status=WebhookStatus.PENDING
        )

        self.deliveries[delivery_id] = delivery

        max_retries = webhook.retry_config.get("max_retries", 3)
        retry_delay = webhook.retry_config.get("retry_delay", 60)
        timeout = webhook.retry_config.get("timeout", 30)

        for attempt in range(max_retries + 1):
            delivery.attempts = attempt + 1
            delivery.last_attempt = datetime.utcnow()

            try:
                # Prepare payload
                payload = event.to_dict()

                # Generate HMAC signature
                signature = self._generate_signature(webhook.secret, payload)

                # Prepare headers
                headers = {
                    **webhook.headers,
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "X-Event-Type": event.type.value,
                    "X-Event-ID": event.id,
                    "X-Delivery-ID": delivery_id
                }

                # Send webhook
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        webhook.url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        delivery.response_code = response.status
                        delivery.response_body = await response.text()

                        if 200 <= response.status < 300:
                            delivery.status = WebhookStatus.SENT
                            self.logger.info(f"Webhook delivered: {delivery_id}")
                            return
                        else:
                            delivery.error = f"HTTP {response.status}"
                            self.logger.warning(f"Webhook failed: {delivery_id} - {delivery.error}")

            except asyncio.TimeoutError:
                delivery.error = "Request timeout"
                self.logger.warning(f"Webhook timeout: {delivery_id}")

            except Exception as e:
                delivery.error = str(e)
                self.logger.error(f"Webhook error: {delivery_id} - {e}")

            # Retry if not last attempt
            if attempt < max_retries:
                delivery.status = WebhookStatus.RETRY
                await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff

        # All retries failed
        delivery.status = WebhookStatus.FAILED
        self.logger.error(f"Webhook delivery failed after {max_retries} retries: {delivery_id}")

    def _generate_signature(
        self,
        secret: str,
        payload: Dict[str, Any]
    ) -> str:
        """Generate HMAC signature for webhook payload"""
        payload_json = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def verify_signature(
        self,
        secret: str,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """Verify webhook signature"""
        expected = self._generate_signature(secret, payload)
        return hmac.compare_digest(expected, signature)

    def get_delivery_status(
        self,
        delivery_id: str
    ) -> Optional[WebhookDelivery]:
        """Get webhook delivery status"""
        return self.deliveries.get(delivery_id)

    def get_webhook_deliveries(
        self,
        webhook_id: str,
        limit: int = 100
    ) -> List[WebhookDelivery]:
        """Get delivery history for webhook"""
        deliveries = [
            d for d in self.deliveries.values()
            if d.webhook_id == webhook_id
        ]

        # Sort by creation time (newest first)
        deliveries.sort(key=lambda d: d.created_at, reverse=True)

        return deliveries[:limit]

    async def retry_delivery(self, delivery_id: str) -> bool:
        """Manually retry failed delivery"""
        delivery = self.deliveries.get(delivery_id)

        if not delivery or delivery.status == WebhookStatus.SENT:
            return False

        webhook = self.webhooks.get(delivery.webhook_id)
        if not webhook:
            return False

        # Get original event from history
        event = next(
            (e for e in self.event_bus.event_history if e.id == delivery.event_id),
            None
        )

        if not event:
            return False

        # Retry delivery
        await self._deliver_webhook(webhook, event)
        return True


# ==================== Event Emitter ====================

class EventEmitter:
    """Helper for emitting events"""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)

    async def emit(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Event:
        """
        Emit event

        Args:
            event_type: Type of event
            data: Event data
            user_id: Optional user ID
            session_id: Optional session ID
            metadata: Optional metadata

        Returns:
            Emitted event
        """
        import uuid

        event = Event(
            id=str(uuid.uuid4()),
            type=event_type,
            timestamp=datetime.utcnow(),
            data=data,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {}
        )

        await self.event_bus.publish(event)
        return event

    # Convenience methods for common events
    async def agent_started(
        self,
        agent_name: str,
        task: Dict[str, Any],
        session_id: Optional[str] = None
    ):
        """Emit agent started event"""
        return await self.emit(
            EventType.AGENT_STARTED,
            {"agent": agent_name, "task": task},
            session_id=session_id
        )

    async def agent_completed(
        self,
        agent_name: str,
        result: Dict[str, Any],
        duration_ms: float,
        session_id: Optional[str] = None
    ):
        """Emit agent completed event"""
        return await self.emit(
            EventType.AGENT_COMPLETED,
            {"agent": agent_name, "result": result, "duration_ms": duration_ms},
            session_id=session_id
        )

    async def budget_warning(
        self,
        user_id: str,
        current_usage: float,
        limit: float,
        period: str
    ):
        """Emit budget warning event"""
        return await self.emit(
            EventType.BUDGET_WARNING,
            {
                "current_usage": current_usage,
                "limit": limit,
                "period": period,
                "usage_percent": (current_usage / limit) * 100
            },
            user_id=user_id
        )


# ==================== Global Instances ====================

_event_bus: Optional[EventBus] = None
_webhook_manager: Optional[WebhookManager] = None
_event_emitter: Optional[EventEmitter] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def get_webhook_manager() -> WebhookManager:
    """Get global webhook manager instance"""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager(get_event_bus())
    return _webhook_manager


def get_event_emitter() -> EventEmitter:
    """Get global event emitter instance"""
    global _event_emitter
    if _event_emitter is None:
        _event_emitter = EventEmitter(get_event_bus())
    return _event_emitter
