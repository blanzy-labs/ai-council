import asyncio
from collections import deque
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from app.models.events import CouncilEvent, CouncilEventStatus, CouncilEventType


@dataclass
class _Subscriber:
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[CouncilEvent]


class EventBus:
    def __init__(self, buffer_size: int = 100) -> None:
        self._buffer_size = buffer_size
        self._buffers: dict[str, deque[CouncilEvent]] = {}
        self._subscribers: dict[str, list[_Subscriber]] = {}
        self._next_id = 1
        self._lock = Lock()

    def publish(self, session_id: str, event: CouncilEvent) -> CouncilEvent:
        with self._lock:
            buffer = self._buffers.setdefault(
                session_id,
                deque(maxlen=self._buffer_size),
            )
            buffer.append(event)
            subscribers = list(self._subscribers.get(session_id, []))

        for subscriber in subscribers:
            subscriber.loop.call_soon_threadsafe(
                subscriber.queue.put_nowait,
                event,
            )

        return event

    def publish_event(
        self,
        session_id: str,
        event_type: CouncilEventType,
        status: CouncilEventStatus,
        message: str,
        persona_id: str | None = None,
        persona_name: str | None = None,
        role: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CouncilEvent:
        with self._lock:
            event_id = f"evt-{self._next_id:06d}"
            self._next_id += 1

        event = CouncilEvent(
            id=event_id,
            session_id=session_id,
            type=event_type,
            status=status,
            message=message,
            persona_id=persona_id,
            persona_name=persona_name,
            role=role,
            provider=provider,
            model=model,
            content=content,
            metadata=metadata,
            created_at=datetime.now(timezone.utc).replace(microsecond=0),
        )
        return self.publish(session_id, event)

    async def subscribe(
        self,
        session_id: str,
        include_recent: bool = True,
    ) -> AsyncGenerator[CouncilEvent, None]:
        loop = asyncio.get_running_loop()
        subscriber = _Subscriber(loop=loop, queue=asyncio.Queue())

        with self._lock:
            recent_events = (
                list(self._buffers.get(session_id, [])) if include_recent else []
            )
            self._subscribers.setdefault(session_id, []).append(subscriber)

        try:
            for event in recent_events:
                yield event

            while True:
                yield await subscriber.queue.get()
        finally:
            with self._lock:
                subscribers = self._subscribers.get(session_id)
                if subscribers is None:
                    return
                self._subscribers[session_id] = [
                    current
                    for current in subscribers
                    if current is not subscriber
                ]
                if not self._subscribers[session_id]:
                    self._subscribers.pop(session_id, None)

    def list_events(self, session_id: str) -> list[CouncilEvent]:
        with self._lock:
            return list(self._buffers.get(session_id, []))

    def clear(self) -> None:
        with self._lock:
            self._buffers.clear()
            self._subscribers.clear()
            self._next_id = 1


event_bus = EventBus()
