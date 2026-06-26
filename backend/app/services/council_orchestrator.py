from datetime import datetime, timezone
from typing import Any

from app.models.council import CouncilMessage, CouncilRunRequest, CouncilRunResult
from app.models.persona import Persona
from app.models.provider import ProviderError, ProviderRequest
from app.models.session import CouncilSession
from app.providers.factory import get_provider
from app.services.persona_registry import PersonaRegistry


class CouncilOrchestrator:
    def __init__(self, persona_registry: PersonaRegistry) -> None:
        self.persona_registry = persona_registry

    def run(
        self,
        session: CouncilSession,
        run_request: CouncilRunRequest,
    ) -> CouncilRunResult:
        run_started_at = self._now()
        messages: list[CouncilMessage] = []
        errors: list[dict[str, Any]] = []
        message_index = 1

        def add_message(
            persona_id: str,
            persona_name: str,
            role: str,
            content: str,
            provider: str | None = None,
            model: str | None = None,
            metadata: dict[str, Any] | None = None,
        ) -> None:
            nonlocal message_index
            messages.append(
                CouncilMessage(
                    id=f"msg-{message_index:04d}",
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
            )
            message_index += 1

        add_message(
            persona_id="user",
            persona_name="User",
            role="user",
            content=session.topic,
            metadata={"title": session.title},
        )

        selected_personas = self._selected_personas(session)
        moderator = self._moderator(selected_personas)
        participants = [
            persona for persona in selected_personas if persona.id != "moderator"
        ]

        if session.mode == "ask_one":
            participants = participants[:1]
            rounds = 1
        elif session.mode == "council_discussion":
            rounds = min(run_request.max_rounds or 2, 2)
        else:
            rounds = min(run_request.max_rounds or 1, 1)

        for round_number in range(1, rounds + 1):
            for persona in participants:
                provider_response = self._generate_persona_response(
                    persona=persona,
                    session=session,
                    run_request=run_request,
                    round_number=round_number,
                    messages=messages,
                    errors=errors,
                    is_summary=False,
                )
                if provider_response is None:
                    continue

                add_message(
                    persona_id=persona.id,
                    persona_name=persona.name,
                    role="persona",
                    provider=provider_response.provider,
                    model=provider_response.model,
                    content=provider_response.content,
                    metadata={
                        "round": round_number,
                        "raw_response_id": provider_response.raw_response_id,
                        "usage": provider_response.usage,
                        "finish_reason": provider_response.finish_reason,
                    },
                )

        summary: str | None = None
        if (
            moderator is not None
            and run_request.include_moderator_summary
            and messages
        ):
            provider_response = self._generate_persona_response(
                persona=moderator,
                session=session,
                run_request=run_request,
                round_number=rounds,
                messages=messages,
                errors=errors,
                is_summary=True,
            )
            if provider_response is not None:
                summary = provider_response.content
                add_message(
                    persona_id=moderator.id,
                    persona_name=moderator.name,
                    role="moderator",
                    provider=provider_response.provider,
                    model=provider_response.model,
                    content=provider_response.content,
                    metadata={
                        "summary": True,
                        "raw_response_id": provider_response.raw_response_id,
                        "usage": provider_response.usage,
                        "finish_reason": provider_response.finish_reason,
                    },
                )

        generated_messages = [
            message for message in messages if message.role in {"persona", "moderator"}
        ]
        result_status = "completed" if generated_messages else "failed"

        return CouncilRunResult(
            session_id=session.id,
            status=result_status,
            mode=session.mode,
            topic=session.topic,
            messages=messages,
            summary=summary,
            errors=errors,
            created_at=run_started_at,
            completed_at=self._now(),
        )

    def _generate_persona_response(
        self,
        persona: Persona,
        session: CouncilSession,
        run_request: CouncilRunRequest,
        round_number: int,
        messages: list[CouncilMessage],
        errors: list[dict[str, Any]],
        is_summary: bool,
    ):
        provider_name = run_request.provider_override or persona.provider
        model = None if persona.model == "default" else persona.model

        try:
            provider = get_provider(provider_name)
            return provider.generate(
                ProviderRequest(
                    persona_id=persona.id,
                    persona_name=persona.name,
                    system_prompt=persona.system_prompt,
                    user_prompt=self._build_prompt(
                        session=session,
                        round_number=round_number,
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
        session: CouncilSession,
        round_number: int,
        messages: list[CouncilMessage],
        is_summary: bool,
    ) -> str:
        transcript = self._compact_transcript(messages)
        if is_summary:
            return (
                "Produce a concise moderator summary for this council run.\n"
                f"Topic: {session.topic}\n"
                f"Mode: {session.mode}\n"
                "Include: concise summary, strongest points, disagreements, "
                "and suggested next step.\n\n"
                f"Transcript:\n{transcript}"
            )

        return (
            "Respond as your council persona.\n"
            f"Topic: {session.topic}\n"
            f"Council mode: {session.mode}\n"
            f"Current round: {round_number}\n"
            "Use the previous transcript as context when it is relevant.\n\n"
            f"Previous transcript:\n{transcript}"
        )

    def _compact_transcript(self, messages: list[CouncilMessage]) -> str:
        if not messages:
            return "(none)"

        return "\n".join(
            f"{message.persona_name} [{message.role}]: "
            f"{self._compact_content(message.content)}"
            for message in messages[-12:]
        )

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
