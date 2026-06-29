import json
import re
from datetime import datetime, timezone
from typing import Any

from app.models.council import CouncilMessage
from app.models.events import CouncilEvent
from app.models.export import ExportMetadata, ExportRequest, ExportResponse
from app.models.session import CouncilSession
from app.services.event_bus import EventBus
from app.services.transcript_store import TranscriptStore


class ExportService:
    def __init__(
        self,
        transcript_store: TranscriptStore,
        event_bus: EventBus,
    ) -> None:
        self.transcript_store = transcript_store
        self.event_bus = event_bus

    def generate_export(
        self,
        session: CouncilSession,
        export_request: ExportRequest,
    ) -> ExportResponse:
        messages = self.transcript_store.list_messages(session.id) or []
        events = (
            self.event_bus.list_events(session.id)
            if export_request.include_events
            else []
        )
        latest_result = self.transcript_store.get_latest_result(session.id)
        metadata = self._build_metadata(session, messages, events, export_request)

        if export_request.format == "markdown":
            return ExportResponse(
                session_id=session.id,
                format=export_request.format,
                filename=self._filename(session, "md"),
                content_type="text/markdown",
                content=self._to_markdown(
                    session=session,
                    messages=messages,
                    events=events,
                    latest_result=latest_result,
                    metadata=metadata,
                    include_metadata=export_request.include_metadata,
                    include_events=export_request.include_events,
                ),
            )

        content = self._to_json(
            session=session,
            messages=messages,
            events=events,
            latest_result=latest_result,
            metadata=metadata,
            include_metadata=export_request.include_metadata,
            include_events=export_request.include_events,
        )
        return ExportResponse(
            session_id=session.id,
            format=export_request.format,
            filename=self._filename(session, "json"),
            content_type="application/json",
            content=content,
        )

    def _build_metadata(
        self,
        session: CouncilSession,
        messages: list[CouncilMessage],
        events: list[CouncilEvent],
        export_request: ExportRequest,
    ) -> ExportMetadata:
        return ExportMetadata(
            session_id=session.id,
            title=session.title,
            topic=session.topic,
            mode=session.mode,
            status=session.status,
            selected_persona_ids=session.selected_persona_ids,
            created_at=session.created_at,
            updated_at=session.updated_at,
            exported_at=datetime.now(timezone.utc).replace(microsecond=0),
            message_count=len(messages),
            event_count=len(events) if export_request.include_events else None,
        )

    def _to_markdown(
        self,
        session: CouncilSession,
        messages: list[CouncilMessage],
        events: list[CouncilEvent],
        latest_result: Any,
        metadata: ExportMetadata,
        include_metadata: bool,
        include_events: bool,
    ) -> str:
        lines = [f"# AI Council Session: {session.title}", ""]

        if include_metadata:
            lines.extend(
                [
                    "## Metadata",
                    "",
                    f"- Session ID: `{metadata.session_id}`",
                    f"- Topic: {metadata.topic}",
                    f"- Mode: `{metadata.mode}`",
                    f"- Status: `{metadata.status}`",
                    "- Selected personas: "
                    f"{', '.join(metadata.selected_persona_ids)}",
                    f"- Created: {self._format_dt(metadata.created_at)}",
                    f"- Updated: {self._format_dt(metadata.updated_at)}",
                    f"- Exported: {self._format_dt(metadata.exported_at)}",
                    f"- Message count: {metadata.message_count}",
                ]
            )
            if metadata.event_count is not None:
                lines.append(f"- Event count: {metadata.event_count}")
            lines.append("")

        lines.extend(["## Transcript", ""])
        if messages:
            for message in messages:
                lines.extend(self._message_markdown(message))
        else:
            lines.extend(["_No transcript messages yet._", ""])

        errors = getattr(latest_result, "errors", []) if latest_result else []
        if errors:
            lines.extend(["## Errors", ""])
            for error in errors:
                persona_name = error.get("persona_name", "Persona")
                error_type = error.get("error_type", "error")
                message = error.get("message", "Provider call failed.")
                lines.append(f"- **{persona_name}** (`{error_type}`): {message}")
            lines.append("")

        if include_events:
            lines.extend(["## Recent Events", ""])
            if events:
                for event in events:
                    lines.append(
                        "- "
                        f"{self._format_dt(event.created_at)} "
                        f"`{event.type}` `{event.status}` - {event.message}"
                    )
            else:
                lines.append("_No recent events._")
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def _message_markdown(self, message: CouncilMessage) -> list[str]:
        label = message.persona_name
        if message.role == "user":
            label = "User"
        elif message.role == "moderator":
            label = f"{message.persona_name} Moderator Summary"

        details = [message.role]
        if message.provider:
            details.append(message.provider)
        if message.model:
            details.append(message.model)

        return [
            f"### {label}",
            "",
            f"_Role/provider/model: {' / '.join(details)}_",
            "",
            message.content,
            "",
        ]

    def _to_json(
        self,
        session: CouncilSession,
        messages: list[CouncilMessage],
        events: list[CouncilEvent],
        latest_result: Any,
        metadata: ExportMetadata,
        include_metadata: bool,
        include_events: bool,
    ) -> str:
        payload: dict[str, Any] = {
            "session": session.model_dump(mode="json"),
            "messages": [message.model_dump(mode="json") for message in messages],
        }
        if include_metadata:
            payload["metadata"] = metadata.model_dump(mode="json")
        if include_events:
            payload["recent_events"] = [
                event.model_dump(mode="json") for event in events
            ]
        if latest_result is not None:
            payload["latest_result"] = latest_result.model_dump(mode="json")

        return json.dumps(payload, indent=2)

    def _filename(self, session: CouncilSession, extension: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", session.title.strip().lower())
        slug = slug.strip("-._")[:80] or "ai-council-session"
        return f"{slug}-{session.id}.{extension}"

    def _format_dt(self, value: datetime) -> str:
        return value.isoformat().replace("+00:00", "Z")
