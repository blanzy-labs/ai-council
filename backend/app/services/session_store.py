from datetime import datetime, timezone
from threading import Lock

from app.models.session import CouncilSession, CouncilSessionCreate


class SessionStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: dict[str, CouncilSession] = {}
        self._next_id = 1

    def create_session(self, session_create: CouncilSessionCreate) -> CouncilSession:
        with self._lock:
            now = datetime.now(timezone.utc).replace(microsecond=0)
            session = CouncilSession(
                id=f"session-{self._next_id:04d}",
                title=session_create.title,
                topic=session_create.topic,
                mode=session_create.mode,
                selected_persona_ids=session_create.selected_persona_ids,
                status="created",
                created_at=now,
                updated_at=now,
            )
            self._sessions[session.id] = session
            self._next_id += 1
            return session

    def get_session(self, session_id: str) -> CouncilSession | None:
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[CouncilSession]:
        return list(self._sessions.values())

    def update_status(self, session_id: str, status: str) -> CouncilSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            updated_session = session.model_copy(
                update={
                    "status": status,
                    "updated_at": datetime.now(timezone.utc).replace(microsecond=0),
                }
            )
            self._sessions[session_id] = updated_session
            return updated_session

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._next_id = 1


session_store = SessionStore()
