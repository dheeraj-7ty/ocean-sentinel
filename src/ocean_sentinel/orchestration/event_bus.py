"""In-Process Event Bus and Subscriber Hub (Phase 7B).

Provides an in-process, non-blocking pub/sub hub distributing investigation events
from the execution engine to active SSE clients and operational listeners.

Guarantees:
- Strict run-level isolation: subscribers only receive events for their subscribed run.
- Non-blocking execution: slow or broken subscribers never block stage execution.
- Bounded memory: subscriber queues are bounded, dropping or logging overflows safely.
- Graceful cancellation and cleanup upon client disconnect.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set

from ocean_sentinel.orchestration.events import InvestigationEvent

logger = logging.getLogger(__name__)


class EventSubscription:
    """Subscription handle for an individual client listening to an investigation run."""

    def __init__(self, run_id: str, max_queue_size: int = 1000) -> None:
        self.run_id = run_id
        self.queue: asyncio.Queue[Optional[InvestigationEvent]] = asyncio.Queue(maxsize=max_queue_size)
        self.is_active = True
        self.has_overflowed = False

    def put_nowait(self, event: InvestigationEvent) -> bool:
        """Push an event to the subscriber queue without blocking."""
        if not self.is_active:
            return False
        try:
            self.queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            self.has_overflowed = True
            logger.warning(
                "Subscriber queue full for run '%s'. Dropping event seq=%d and setting overflow flag for disk resynchronization.",
                self.run_id,
                event.sequence,
            )
            return False

    def close(self) -> None:
        """Mark subscription inactive and signal completion to listener."""
        if self.is_active:
            self.is_active = False
            try:
                self.queue.put_nowait(None)
            except asyncio.QueueFull:
                pass


class EventBus:
    """Central in-process event hub for broadcasting investigation events."""

    def __init__(self) -> None:
        # Map run_id -> list of active async subscriptions
        self._async_subscribers: Dict[str, List[EventSubscription]] = {}
        # Map run_id -> list of sync callbacks
        self._sync_subscribers: Dict[str, List[Callable[[InvestigationEvent], None]]] = {}

    def subscribe(self, run_id: str, max_queue_size: int = 1000) -> EventSubscription:
        """Register an asynchronous queue-based subscription for a run."""
        sub = EventSubscription(run_id=run_id, max_queue_size=max_queue_size)
        if run_id not in self._async_subscribers:
            self._async_subscribers[run_id] = []
        self._async_subscribers[run_id].append(sub)
        logger.debug("Subscribed async client to run '%s'. Active listeners: %d", run_id, len(self._async_subscribers[run_id]))
        return sub

    def unsubscribe(self, sub: EventSubscription) -> None:
        """Unregister an async subscription and close it."""
        sub.close()
        subs = self._async_subscribers.get(sub.run_id)
        if subs and sub in subs:
            subs.remove(sub)
            if not subs:
                del self._async_subscribers[sub.run_id]
        logger.debug("Unsubscribed async client from run '%s'.", sub.run_id)

    def subscribe_sync(
        self,
        run_id: str,
        callback: Callable[[InvestigationEvent], None],
    ) -> Callable[[], None]:
        """Register a synchronous callback for a run. Returns an unregister callable."""
        if run_id not in self._sync_subscribers:
            self._sync_subscribers[run_id] = []
        self._sync_subscribers[run_id].append(callback)

        def _unsubscribe() -> None:
            cbs = self._sync_subscribers.get(run_id)
            if cbs and callback in cbs:
                cbs.remove(callback)
                if not cbs:
                    del self._sync_subscribers[run_id]

        return _unsubscribe

    def publish(self, event: InvestigationEvent) -> None:
        """Dispatch event to all registered listeners for event.run_id."""
        run_id = event.run_id

        # 1. Dispatch to async subscriber queues
        async_subs = list(self._async_subscribers.get(run_id, []))
        for sub in async_subs:
            if not sub.is_active:
                self.unsubscribe(sub)
            else:
                sub.put_nowait(event)

        # 2. Dispatch to synchronous callbacks with exception isolation
        sync_cbs = list(self._sync_subscribers.get(run_id, []))
        for cb in sync_cbs:
            try:
                cb(event)
            except Exception as err:
                logger.error(
                    "Error executing sync event callback for run '%s' (event %s): %s",
                    run_id,
                    event.event_type,
                    err,
                )

    def close_run(self, run_id: str) -> None:
        """Close and detach all subscriptions associated with a completed or closed run."""
        async_subs = self._async_subscribers.pop(run_id, [])
        for sub in async_subs:
            sub.close()
        self._sync_subscribers.pop(run_id, None)


# Default singleton instance for application runtime
_GLOBAL_EVENT_BUS: Optional[EventBus] = None


def get_global_event_bus() -> EventBus:
    """Access the global singleton event bus instance."""
    global _GLOBAL_EVENT_BUS
    if _GLOBAL_EVENT_BUS is None:
        _GLOBAL_EVENT_BUS = EventBus()
    return _GLOBAL_EVENT_BUS


def set_global_event_bus(bus: EventBus) -> None:
    """Override event bus instance (useful for testing)."""
    global _GLOBAL_EVENT_BUS
    _GLOBAL_EVENT_BUS = bus
