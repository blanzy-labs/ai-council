from threading import Lock

from app.models.council import CouncilMessage, CouncilRunResult


class TranscriptStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._results: dict[str, CouncilRunResult] = {}
        self._messages: dict[str, list[CouncilMessage]] = {}

    def save_run_result(
        self,
        session_id: str,
        result: CouncilRunResult,
    ) -> CouncilRunResult:
        with self._lock:
            self._results[session_id] = result
            self._messages[session_id] = list(result.messages)
            return result

    def get_run_result(self, session_id: str) -> CouncilRunResult | None:
        return self._results.get(session_id)

    def get_latest_result(self, session_id: str) -> CouncilRunResult | None:
        return self.get_run_result(session_id)

    def append_message(
        self,
        session_id: str,
        message: CouncilMessage,
    ) -> CouncilMessage:
        with self._lock:
            self._messages.setdefault(session_id, []).append(message)
            return message

    def append_messages(
        self,
        session_id: str,
        messages: list[CouncilMessage],
    ) -> list[CouncilMessage]:
        with self._lock:
            self._messages.setdefault(session_id, []).extend(messages)
            return messages

    def list_messages(self, session_id: str) -> list[CouncilMessage] | None:
        messages = self._messages.get(session_id)
        if messages is None:
            return None
        return list(messages)

    def clear_messages(self, session_id: str) -> int:
        with self._lock:
            messages = self._messages.pop(session_id, [])
            self._results.pop(session_id, None)
            return len(messages)

    def clear(self) -> None:
        with self._lock:
            self._results.clear()
            self._messages.clear()


transcript_store = TranscriptStore()
