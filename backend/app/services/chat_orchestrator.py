from datetime import datetime, timezone
from typing import Any

from app.models.chat import ChatRequest, ChatResponse
from app.models.council import CouncilMessage
from app.models.persona import Persona
from app.models.provider import ProviderError, ProviderRequest
from app.models.session import CouncilSession
from app.providers.factory import get_provider
from app.services.persona_registry import PersonaRegistry
from app.services.transcript_store import TranscriptStore


RECENT_CONTEXT_MESSAGE_LIMIT = 12
RECENT_CONTEXT_CHAR_LIMIT = 6000


class ChatOrchestrator:
    def __init__(
        self,
        persona_registry: PersonaRegistry,
        transcript_store: TranscriptStore,
    ) -> None:
        self.persona_registry = persona_registry
        self.transcript_store = transcript_store

    def chat(
        self,
        session: CouncilSession,
        chat_request: ChatRequest,
    ) -> ChatResponse:
        existing_messages = self.transcript_store.list_messages(session.id) or []
        next_index = len(existing_messages) + 1
        new_messages: list[CouncilMessage] = []
        errors: list[dict[str, Any]] = []

        def create_message(
            persona_id: str,
            persona_name: str,
            role: str,
            content: str,
            provider: str | None = None,
            model: str | None = None,
            metadata: dict[str, Any] | None = None,
        ) -> CouncilMessage:
            nonlocal next_index
            message = CouncilMessage(
                id=f"msg-{next_index:04d}",
                session_id=session.id,
                persona_id=persona_id,
                persona_name=persona_name,
                role=role,  # type: ignore[arg-type]
                provider=provider,
                model=model,
                content=content,
                created_at=self._now(),
                metadata=metadata,
            )
            next_index += 1
            return message

        user_message = create_message(
            persona_id="user",
            persona_name="User",
            role="user",
            content=chat_request.message,
            metadata={"follow_up": True},
        )
        new_messages.append(user_message)

        selected_personas = self._selected_personas(session)
        moderator = self._moderator(selected_personas)
        responders = self._responders(session, selected_personas, chat_request)
        responses: list[CouncilMessage] = []

        for persona in responders:
            provider_response = self._generate_response(
                persona=persona,
                session=session,
                chat_request=chat_request,
                messages=existing_messages + new_messages,
                errors=errors,
                is_summary=False,
            )
            if provider_response is None:
                continue

            response_message = create_message(
                persona_id=persona.id,
                persona_name=persona.name,
                role="moderator" if persona.id == "moderator" else "persona",
                provider=provider_response.provider,
                model=provider_response.model,
                content=provider_response.content,
                metadata={
                    "follow_up": True,
                    "target": chat_request.target.type,
                    "raw_response_id": provider_response.raw_response_id,
                    "usage": provider_response.usage,
                    "finish_reason": provider_response.finish_reason,
                },
            )
            responses.append(response_message)
            new_messages.append(response_message)

        summary_message: CouncilMessage | None = None
        if (
            chat_request.include_moderator_summary
            and moderator is not None
            and responses
        ):
            provider_response = self._generate_response(
                persona=moderator,
                session=session,
                chat_request=chat_request,
                messages=existing_messages + new_messages,
                errors=errors,
                is_summary=True,
            )
            if provider_response is not None:
                summary_message = create_message(
                    persona_id=moderator.id,
                    persona_name=moderator.name,
                    role="moderator",
                    provider=provider_response.provider,
                    model=provider_response.model,
                    content=provider_response.content,
                    metadata={
                        "follow_up": True,
                        "summary": True,
                        "raw_response_id": provider_response.raw_response_id,
                        "usage": provider_response.usage,
                        "finish_reason": provider_response.finish_reason,
                    },
                )
                new_messages.append(summary_message)

        self.transcript_store.append_messages(session.id, new_messages)
        all_messages = self.transcript_store.list_messages(session.id) or []

        status = "completed" if responses or summary_message is not None else "failed"
        return ChatResponse(
            session_id=session.id,
            status=status,
            user_message=user_message,
            responses=responses,
            summary=summary_message,
            errors=errors,
            messages=all_messages,
        )

    def _responders(
        self,
        session: CouncilSession,
        selected_personas: list[Persona],
        chat_request: ChatRequest,
    ) -> list[Persona]:
        if chat_request.target.type == "council":
            return [
                persona for persona in selected_personas if persona.id != "moderator"
            ]

        persona_id = chat_request.target.persona_id
        if persona_id is None:
            return []

        persona = self.persona_registry.get_persona(persona_id)
        if persona is None or persona.id not in session.selected_persona_ids:
            return []
        return [persona]

    def _generate_response(
        self,
        persona: Persona,
        session: CouncilSession,
        chat_request: ChatRequest,
        messages: list[CouncilMessage],
        errors: list[dict[str, Any]],
        is_summary: bool,
    ):
        provider_name = chat_request.provider_override or persona.provider
        model = None if persona.model == "default" else persona.model

        try:
            provider = get_provider(provider_name)
            return provider.generate(
                ProviderRequest(
                    persona_id=persona.id,
                    persona_name=persona.name,
                    system_prompt=persona.system_prompt,
                    user_prompt=self._build_prompt(
                        persona=persona,
                        session=session,
                        chat_request=chat_request,
                        messages=messages,
                        is_summary=is_summary,
                    ),
                    model=model,
                )
            )
        except ProviderError as exc:
            errors.append(
                {
                    "persona_id": persona.id,
                    "persona_name": persona.name,
                    "provider": exc.provider,
                    "message": exc.message,
                    "error_type": exc.error_type,
                }
            )
        except Exception as exc:
            errors.append(
                {
                    "persona_id": persona.id,
                    "persona_name": persona.name,
                    "provider": provider_name,
                    "message": "Provider call failed.",
                    "error_type": exc.__class__.__name__,
                }
            )

        return None

    def _build_prompt(
        self,
        persona: Persona,
        session: CouncilSession,
        chat_request: ChatRequest,
        messages: list[CouncilMessage],
        is_summary: bool,
    ) -> str:
        context = self._compact_context(messages)
        if is_summary:
            persona_responses = [
                message
                for message in messages
                if message.role in {"persona", "moderator"}
                and message.metadata
                and message.metadata.get("follow_up")
            ]
            exchange = self._compact_context(persona_responses)
            return (
                "Produce a short moderator summary of this follow-up exchange.\n"
                f"Original session topic: {session.topic}\n"
                f"User follow-up: {chat_request.message}\n"
                "Include key agreement or disagreement and a suggested next "
                "question or next step.\n\n"
                f"Persona responses:\n{exchange}"
            )

        return (
            "Respond as this persona only.\n"
            f"Persona: {persona.name}\n"
            f"Original session topic: {session.topic}\n"
            f"User follow-up message: {chat_request.message}\n"
            "Use the recent transcript context when relevant. Keep the response "
            "focused and concise.\n\n"
            f"Recent transcript context:\n{context}"
        )

    def _compact_context(self, messages: list[CouncilMessage]) -> str:
        if not messages:
            return "(none)"

        lines: list[str] = []
        total_chars = 0
        for message in messages[-RECENT_CONTEXT_MESSAGE_LIMIT:]:
            line = (
                f"{message.persona_name} [{message.role}]: "
                f"{self._compact_content(message.content)}"
            )
            if total_chars + len(line) > RECENT_CONTEXT_CHAR_LIMIT:
                break
            lines.append(line)
            total_chars += len(line)

        return "\n".join(lines) if lines else "(context omitted)"

    def _compact_content(self, content: str, limit: int = 420) -> str:
        normalized = " ".join(content.split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[:limit].rstrip()}..."

    def _selected_personas(self, session: CouncilSession) -> list[Persona]:
        personas: list[Persona] = []
        for persona_id in session.selected_persona_ids:
            persona = self.persona_registry.get_persona(persona_id)
            if persona is not None:
                personas.append(persona)
        return personas

    def _moderator(self, personas: list[Persona]) -> Persona | None:
        for persona in personas:
            if persona.id == "moderator":
                return persona
        return None

    def _now(self) -> datetime:
        return datetime.now(timezone.utc).replace(microsecond=0)
