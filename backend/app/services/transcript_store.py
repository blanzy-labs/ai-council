from threading import Lock

from app.models.council import CouncilMessage, CouncilRunResult


class TranscriptStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._results: dict[str, CouncilRunResult] = {}

    def save_run_result(
        self,
        session_id: str,
        result: CouncilRunResult,
    ) -> CouncilRunResult:
        with self._lock:
            self._results[session_id] = result
            return result

    def get_run_result(self, session_id: str) -> CouncilRunResult | None:
        return self._results.get(session_id)

    def list_messages(self, session_id: str) -> list[CouncilMessage] | None:
        result = self.get_run_result(session_id)
        if result is None:
            return None
        return result.messages

    def clear(self) -> None:
        with self._lock:
            self._results.clear()


transcript_store = TranscriptStore()
