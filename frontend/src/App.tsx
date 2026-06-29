import { FormEvent, useEffect, useMemo, useState } from "react";

type HealthStatus = {
  status: "idle" | "loading" | "ok" | "error";
  message: string;
  service?: string;
};

type Persona = {
  id: string;
  name: string;
  role: string;
  provider: string;
  model: string;
  system_prompt: string;
  goals: string[];
  constraints: string[];
};

type CouncilMode = "ask_council" | "council_discussion" | "ask_one";

type CouncilSession = {
  id: string;
  title: string;
  topic: string;
  mode: CouncilMode;
  selected_persona_ids: string[];
  status: string;
  created_at: string;
  updated_at: string;
};

type CouncilMessage = {
  id: string;
  session_id: string;
  persona_id: string;
  persona_name: string;
  role: "user" | "persona" | "moderator" | "system";
  provider?: string | null;
  model?: string | null;
  content: string;
  created_at: string;
  metadata?: Record<string, unknown> | null;
};

type CouncilRunResult = {
  session_id: string;
  status: string;
  mode: CouncilMode;
  topic: string;
  messages: CouncilMessage[];
  summary?: string | null;
  errors: Array<Record<string, unknown>>;
  created_at: string;
  completed_at: string;
};

type ChatTargetType = "council" | "persona";

type ChatResponse = {
  session_id: string;
  status: string;
  user_message: CouncilMessage;
  responses: CouncilMessage[];
  summary?: CouncilMessage | null;
  errors: Array<Record<string, unknown>>;
  messages: CouncilMessage[];
};

type CouncilEvent = {
  id: string;
  session_id: string;
  type:
    | "run_started"
    | "chat_started"
    | "persona_started"
    | "persona_completed"
    | "moderator_started"
    | "moderator_completed"
    | "message_appended"
    | "error"
    | "run_completed"
    | "chat_completed";
  status: "started" | "in_progress" | "completed" | "failed";
  message: string;
  persona_id?: string | null;
  persona_name?: string | null;
  role?: string | null;
  provider?: string | null;
  model?: string | null;
  content?: string | null;
  metadata?: Record<string, unknown> | null;
  created_at: string;
};

type ProviderName = "mock" | "openai";

type ProviderResponse = {
  provider: string;
  model: string;
  persona_id: string;
  persona_name: string;
  content: string;
  raw_response_id?: string | null;
  usage?: Record<string, unknown> | null;
  finish_reason?: string | null;
};

type ExportFormat = "markdown" | "json";

type SessionExportResponse = {
  session_id: string;
  format: ExportFormat;
  filename: string;
  content_type: string;
  content: string;
};

type LoadStatus = "idle" | "loading" | "ok" | "error";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const normalizedApiBaseUrl = apiBaseUrl.replace(/\/$/, "");

const defaultSelectedPersonaIds = [
  "moderator",
  "strategist",
  "skeptic",
  "builder",
  "customer_advocate",
];

const modes: Array<{ value: CouncilMode; label: string }> = [
  { value: "ask_council", label: "Ask council" },
  { value: "council_discussion", label: "Council discussion" },
  { value: "ask_one", label: "Ask one" },
];

const eventTypes: CouncilEvent["type"][] = [
  "run_started",
  "chat_started",
  "persona_started",
  "persona_completed",
  "moderator_started",
  "moderator_completed",
  "message_appended",
  "error",
  "run_completed",
  "chat_completed",
];

async function readApiError(response: Response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (body.detail) {
      return JSON.stringify(body.detail);
    }
  } catch {
    return `Request failed with ${response.status}`;
  }

  return `Request failed with ${response.status}`;
}

function TranscriptView({ messages }: { messages: CouncilMessage[] }) {
  if (messages.length === 0) {
    return <div className="inline-note">No messages yet.</div>;
  }

  return (
    <div className="transcript">
      {messages.map((message) => (
        <article
          className={`transcript-message message-${message.role}`}
          key={message.id}
        >
          <header>
            <div>
              <strong>{message.persona_name}</strong>
              <span>{message.role}</span>
            </div>
            {(message.provider || message.model) && (
              <span className="message-provider">
                {[message.provider, message.model].filter(Boolean).join(" / ")}
              </span>
            )}
          </header>
          <p>{message.content}</p>
        </article>
      ))}
    </div>
  );
}

function eventToMessage(event: CouncilEvent): CouncilMessage | null {
  if (event.type !== "message_appended" || !event.content) {
    return null;
  }

  const messageId =
    typeof event.metadata?.message_id === "string"
      ? event.metadata.message_id
      : event.id;
  const role =
    event.role === "user" ||
    event.role === "persona" ||
    event.role === "moderator" ||
    event.role === "system"
      ? event.role
      : "system";

  return {
    id: messageId,
    session_id: event.session_id,
    persona_id: event.persona_id ?? "system",
    persona_name: event.persona_name ?? "System",
    role,
    provider: event.provider,
    model: event.model,
    content: event.content,
    created_at: event.created_at,
    metadata: event.metadata,
  };
}

function App() {
  const [health, setHealth] = useState<HealthStatus>({
    status: "idle",
    message: "Waiting to check backend health.",
  });
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [personaStatus, setPersonaStatus] = useState<LoadStatus>("idle");
  const [personaError, setPersonaError] = useState("");
  const [selectedPersonaIds, setSelectedPersonaIds] = useState<string[]>(
    defaultSelectedPersonaIds,
  );
  const [title, setTitle] = useState("Slice E test council");
  const [topic, setTopic] = useState("Review the chat room follow-up flow.");
  const [mode, setMode] = useState<CouncilMode>("ask_council");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [session, setSession] = useState<CouncilSession | null>(null);
  const [sessionError, setSessionError] = useState("");
  const [runProviderOverride, setRunProviderOverride] =
    useState<ProviderName>("mock");
  const [runMaxRounds, setRunMaxRounds] = useState(1);
  const [includeModeratorSummary, setIncludeModeratorSummary] = useState(true);
  const [isRunningCouncil, setIsRunningCouncil] = useState(false);
  const [runResult, setRunResult] = useState<CouncilRunResult | null>(null);
  const [runError, setRunError] = useState("");
  const [transcriptMessages, setTranscriptMessages] = useState<CouncilMessage[]>(
    [],
  );
  const [chatMessage, setChatMessage] = useState(
    "What is the riskiest assumption in this plan?",
  );
  const [chatTargetType, setChatTargetType] =
    useState<ChatTargetType>("council");
  const [chatPersonaId, setChatPersonaId] = useState("");
  const [chatProviderOverride, setChatProviderOverride] =
    useState<ProviderName>("mock");
  const [chatIncludeModeratorSummary, setChatIncludeModeratorSummary] =
    useState(false);
  const [isSendingChat, setIsSendingChat] = useState(false);
  const [chatErrors, setChatErrors] = useState<Array<Record<string, unknown>>>([]);
  const [chatError, setChatError] = useState("");
  const [liveEvents, setLiveEvents] = useState<CouncilEvent[]>([]);
  const [eventConnectionStatus, setEventConnectionStatus] =
    useState("idle");
  const [exportFormat, setExportFormat] =
    useState<ExportFormat>("markdown");
  const [exportIncludeEvents, setExportIncludeEvents] = useState(false);
  const [exportIncludeMetadata, setExportIncludeMetadata] = useState(true);
  const [isGeneratingExport, setIsGeneratingExport] = useState(false);
  const [exportResponse, setExportResponse] =
    useState<SessionExportResponse | null>(null);
  const [exportError, setExportError] = useState("");
  const [copyStatus, setCopyStatus] = useState("");
  const [isClearingTranscript, setIsClearingTranscript] = useState(false);
  const [isClearingEvents, setIsClearingEvents] = useState(false);
  const [managementError, setManagementError] = useState("");
  const [providerPersonaId, setProviderPersonaId] = useState("skeptic");
  const [providerName, setProviderName] = useState<ProviderName>("mock");
  const [providerPrompt, setProviderPrompt] = useState(
    "What is the biggest risk in this idea?",
  );
  const [isTestingProvider, setIsTestingProvider] = useState(false);
  const [providerResponse, setProviderResponse] =
    useState<ProviderResponse | null>(null);
  const [providerError, setProviderError] = useState("");

  const healthUrl = useMemo(() => `${normalizedApiBaseUrl}/health`, []);
  const visibleSelectedPersonaIds = useMemo(
    () =>
      personas
        .map((persona) => persona.id)
        .filter((personaId) => selectedPersonaIds.includes(personaId)),
    [personas, selectedPersonaIds],
  );
  const selectedCount = visibleSelectedPersonaIds.length;
  const sessionPersonas = useMemo(
    () =>
      session
        ? personas.filter((persona) =>
            session.selected_persona_ids.includes(persona.id),
          )
        : [],
    [personas, session],
  );
  const sessionNonModeratorPersonas = useMemo(
    () => sessionPersonas.filter((persona) => persona.id !== "moderator"),
    [sessionPersonas],
  );

  useEffect(() => {
    const controller = new AbortController();

    async function checkHealth() {
      setHealth({
        status: "loading",
        message: "Checking backend health...",
      });

      try {
        const response = await fetch(healthUrl, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`);
        }

        const data = (await response.json()) as { status?: string; service?: string };

        if (data.status !== "ok") {
          throw new Error("Backend health response was not ok.");
        }

        setHealth({
          status: "ok",
          message: "Backend is reachable.",
          service: data.service,
        });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        setHealth({
          status: "error",
          message:
            error instanceof Error
              ? error.message
              : "Backend health check failed.",
        });
      }
    }

    checkHealth();

    return () => controller.abort();
  }, [healthUrl]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPersonas() {
      setPersonaStatus("loading");
      setPersonaError("");

      try {
        const response = await fetch(`${normalizedApiBaseUrl}/personas`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(await readApiError(response));
        }

        const data = (await response.json()) as Persona[];
        setPersonas(data);
        if (!data.some((persona) => persona.id === providerPersonaId)) {
          setProviderPersonaId(data[0]?.id ?? "");
        }
        setPersonaStatus("ok");
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        setPersonaStatus("error");
        setPersonaError(
          error instanceof Error ? error.message : "Could not load personas.",
        );
      }
    }

    loadPersonas();

    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!session) {
      setChatPersonaId("");
      return;
    }

    if (sessionNonModeratorPersonas.length === 0) {
      setChatPersonaId("");
      return;
    }

    if (!sessionNonModeratorPersonas.some((persona) => persona.id === chatPersonaId)) {
      setChatPersonaId(sessionNonModeratorPersonas[0].id);
    }
  }, [chatPersonaId, session, sessionNonModeratorPersonas]);

  useEffect(() => {
    if (!session) {
      setLiveEvents([]);
      setEventConnectionStatus("idle");
      return;
    }

    if (typeof EventSource === "undefined") {
      setEventConnectionStatus("unavailable");
      return;
    }

    setLiveEvents([]);
    setEventConnectionStatus("connecting");

    const source = new EventSource(
      `${normalizedApiBaseUrl}/sessions/${session.id}/events`,
    );

    function handleEvent(eventMessage: MessageEvent<string>) {
      const event = JSON.parse(eventMessage.data) as CouncilEvent;
      setLiveEvents((current) => {
        if (current.some((existing) => existing.id === event.id)) {
          return current;
        }
        return [...current, event].slice(-100);
      });

      const message = eventToMessage(event);
      if (message) {
        setTranscriptMessages((current) => {
          if (current.some((existing) => existing.id === message.id)) {
            return current;
          }
          return [...current, message];
        });
      }
    }

    source.onopen = () => setEventConnectionStatus("open");
    source.onerror = () => setEventConnectionStatus("reconnecting");

    eventTypes.forEach((eventType) => {
      source.addEventListener(eventType, handleEvent as EventListener);
    });

    return () => {
      eventTypes.forEach((eventType) => {
        source.removeEventListener(eventType, handleEvent as EventListener);
      });
      source.close();
    };
  }, [session?.id]);

  function togglePersona(personaId: string) {
    setSelectedPersonaIds((current) =>
      current.includes(personaId)
        ? current.filter((id) => id !== personaId)
        : [...current, personaId],
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setSession(null);
    setSessionError("");
    setRunResult(null);
    setRunError("");
    setTranscriptMessages([]);
    setChatErrors([]);
    setChatError("");
    setLiveEvents([]);
    setExportResponse(null);
    setExportError("");
    setCopyStatus("");
    setManagementError("");

    try {
      const response = await fetch(`${normalizedApiBaseUrl}/sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title,
          topic,
          mode,
          selected_persona_ids: visibleSelectedPersonaIds,
        }),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      const data = (await response.json()) as CouncilSession;
      setSession(data);
      setRunMaxRounds(data.mode === "council_discussion" ? 2 : 1);
      const firstNonModeratorPersonaId =
        data.selected_persona_ids.find((personaId) => personaId !== "moderator") ??
        "";
      setChatPersonaId(firstNonModeratorPersonaId);
    } catch (error) {
      setSessionError(
        error instanceof Error ? error.message : "Could not create session.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRunCouncil(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) {
      return;
    }

    setIsRunningCouncil(true);
    setRunResult(null);
    setRunError("");
    setExportResponse(null);
    setCopyStatus("");

    try {
      const response = await fetch(
        `${normalizedApiBaseUrl}/sessions/${session.id}/run`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            provider_override: runProviderOverride,
            max_rounds: runMaxRounds,
            include_moderator_summary: includeModeratorSummary,
          }),
        },
      );

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      const data = (await response.json()) as CouncilRunResult;
      setRunResult(data);
      setTranscriptMessages(data.messages);
      setChatErrors(data.errors);
      setChatError("");
      setSession((current) =>
        current ? { ...current, status: data.status } : current,
      );
    } catch (error) {
      setRunError(
        error instanceof Error ? error.message : "Council run failed.",
      );
    } finally {
      setIsRunningCouncil(false);
    }
  }

  async function handleSendChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) {
      return;
    }

    setIsSendingChat(true);
    setChatError("");
    setChatErrors([]);

    try {
      const response = await fetch(
        `${normalizedApiBaseUrl}/sessions/${session.id}/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: chatMessage,
            target:
              chatTargetType === "council"
                ? { type: "council" }
                : { type: "persona", persona_id: chatPersonaId },
            provider_override: chatProviderOverride,
            include_moderator_summary: chatIncludeModeratorSummary,
          }),
        },
      );

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      const data = (await response.json()) as ChatResponse;
      setTranscriptMessages(data.messages);
      setChatErrors(data.errors);
      setChatMessage("");
      setExportResponse(null);
      setCopyStatus("");
    } catch (error) {
      setChatError(error instanceof Error ? error.message : "Chat failed.");
    } finally {
      setIsSendingChat(false);
    }
  }

  async function handleGenerateExport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) {
      return;
    }

    setIsGeneratingExport(true);
    setExportError("");
    setCopyStatus("");

    try {
      const response = await fetch(
        `${normalizedApiBaseUrl}/sessions/${session.id}/export`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            format: exportFormat,
            include_events: exportIncludeEvents,
            include_metadata: exportIncludeMetadata,
          }),
        },
      );

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      const data = (await response.json()) as SessionExportResponse;
      setExportResponse(data);
    } catch (error) {
      setExportError(
        error instanceof Error ? error.message : "Could not generate export.",
      );
    } finally {
      setIsGeneratingExport(false);
    }
  }

  function handleDownloadExport(format: ExportFormat) {
    if (!session) {
      return;
    }

    const link = document.createElement("a");
    link.href = `${normalizedApiBaseUrl}/sessions/${session.id}/export/${format}`;
    link.rel = "noreferrer";
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  async function handleCopyExport() {
    if (!exportResponse) {
      return;
    }

    try {
      await navigator.clipboard.writeText(exportResponse.content);
      setCopyStatus("Copied");
    } catch {
      setCopyStatus("Copy failed");
    }
  }

  async function handleClearTranscript() {
    if (!session) {
      return;
    }

    const confirmed = window.confirm(
      "Clear the transcript for this in-memory session?",
    );
    if (!confirmed) {
      return;
    }

    setIsClearingTranscript(true);
    setManagementError("");

    try {
      const response = await fetch(
        `${normalizedApiBaseUrl}/sessions/${session.id}/messages`,
        {
          method: "DELETE",
        },
      );

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      setTranscriptMessages([]);
      setRunResult(null);
      setChatErrors([]);
      setExportResponse(null);
      setCopyStatus("");
    } catch (error) {
      setManagementError(
        error instanceof Error ? error.message : "Could not clear transcript.",
      );
    } finally {
      setIsClearingTranscript(false);
    }
  }

  async function handleClearEvents() {
    if (!session) {
      return;
    }

    const confirmed = window.confirm(
      "Clear recent live events for this in-memory session?",
    );
    if (!confirmed) {
      return;
    }

    setIsClearingEvents(true);
    setManagementError("");

    try {
      const response = await fetch(
        `${normalizedApiBaseUrl}/sessions/${session.id}/events`,
        {
          method: "DELETE",
        },
      );

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      setLiveEvents([]);
      setExportResponse(null);
      setCopyStatus("");
    } catch (error) {
      setManagementError(
        error instanceof Error ? error.message : "Could not clear events.",
      );
    } finally {
      setIsClearingEvents(false);
    }
  }

  async function handleProviderTest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsTestingProvider(true);
    setProviderResponse(null);
    setProviderError("");

    try {
      const response = await fetch(`${normalizedApiBaseUrl}/providers/test-generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          provider: providerName,
          persona_id: providerPersonaId,
          user_prompt: providerPrompt,
        }),
      });

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      const data = (await response.json()) as ProviderResponse;
      setProviderResponse(data);
    } catch (error) {
      setProviderError(
        error instanceof Error ? error.message : "Provider test failed.",
      );
    } finally {
      setIsTestingProvider(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="intro">
        <p className="eyebrow">Mythadis Labs</p>
        <h1>AI Council</h1>
        <p className="tagline">Local text-based multi-persona council room</p>
        <p className="scope">v0.1.0: OpenAI-only, no voice</p>
      </section>

      <section className="health-panel" aria-labelledby="health-title">
        <div>
          <p className="eyebrow">Backend</p>
          <h2 id="health-title">Health check</h2>
        </div>
        <div className={`status status-${health.status}`} role="status">
          <span className="status-dot" aria-hidden="true" />
          <div>
            <strong>{health.message}</strong>
            <span>{health.service ?? healthUrl}</span>
          </div>
        </div>
      </section>

      <section className="workspace-grid">
        <section className="panel personas-panel" aria-labelledby="personas-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Council roster</p>
              <h2 id="personas-title">Available personas</h2>
            </div>
            <span className="count-badge">{personas.length}</span>
          </div>

          {personaStatus === "loading" && (
            <div className="inline-note">Loading personas...</div>
          )}

          {personaStatus === "error" && (
            <div className="inline-note inline-note-error">{personaError}</div>
          )}

          <div className="persona-grid">
            {personas.map((persona) => {
              const checked = selectedPersonaIds.includes(persona.id);

              return (
                <label
                  className={`persona-card ${checked ? "is-selected" : ""}`}
                  key={persona.id}
                >
                  <input
                    checked={checked}
                    onChange={() => togglePersona(persona.id)}
                    type="checkbox"
                  />
                  <span>
                    <strong>{persona.name}</strong>
                    <span>{persona.role}</span>
                  </span>
                </label>
              );
            })}
          </div>
        </section>

        <section className="panel session-panel" aria-labelledby="session-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Session</p>
              <h2 id="session-title">Create Test Council Session</h2>
            </div>
            <span className="count-badge">{selectedCount} selected</span>
          </div>

          <form className="session-form" onSubmit={handleSubmit}>
            <label>
              <span>Title</span>
              <input
                onChange={(event) => setTitle(event.target.value)}
                required
                type="text"
                value={title}
              />
            </label>

            <label>
              <span>Topic</span>
              <textarea
                onChange={(event) => setTopic(event.target.value)}
                required
                rows={4}
                value={topic}
              />
            </label>

            <label>
              <span>Mode</span>
              <select
                onChange={(event) => setMode(event.target.value as CouncilMode)}
                value={mode}
              >
                {modes.map((modeOption) => (
                  <option key={modeOption.value} value={modeOption.value}>
                    {modeOption.label}
                  </option>
                ))}
              </select>
            </label>

            <button
              disabled={isSubmitting || personaStatus !== "ok" || selectedCount === 0}
              type="submit"
            >
              {isSubmitting ? "Creating..." : "Create session"}
            </button>
          </form>

          {session && (
            <div className="session-result" role="status">
              <span>Created</span>
              <strong>{session.id}</strong>
              <span>Status: {session.status}</span>
            </div>
          )}

          {sessionError && (
            <div className="session-result session-result-error" role="alert">
              <span>Error</span>
              <strong>{sessionError}</strong>
            </div>
          )}
        </section>
      </section>

      {session && (
        <section className="panel run-panel" aria-labelledby="run-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Council run</p>
              <h2 id="run-title">Run Council</h2>
            </div>
            <span className="count-badge">{session.id}</span>
          </div>

          <form className="run-form" onSubmit={handleRunCouncil}>
            <label>
              <span>Provider override</span>
              <select
                onChange={(event) =>
                  setRunProviderOverride(event.target.value as ProviderName)
                }
                value={runProviderOverride}
              >
                <option value="mock">mock</option>
                <option value="openai">openai</option>
              </select>
            </label>

            <label>
              <span>Max rounds</span>
              <select
                onChange={(event) => setRunMaxRounds(Number(event.target.value))}
                value={runMaxRounds}
              >
                <option value={1}>1</option>
                <option value={2}>2</option>
              </select>
            </label>

            <label className="checkbox-row">
              <input
                checked={includeModeratorSummary}
                onChange={(event) =>
                  setIncludeModeratorSummary(event.target.checked)
                }
                type="checkbox"
              />
              <span>Include moderator summary</span>
            </label>

            <button disabled={isRunningCouncil} type="submit">
              {isRunningCouncil ? "Running..." : "Run Council"}
            </button>
          </form>

          {runError && (
            <div className="run-error" role="alert">
              <strong>Error</strong>
              <p>{runError}</p>
            </div>
          )}

          {runResult && (
            <div className="run-result" role="status">
              <div className="provider-meta">
                <span>{runResult.status}</span>
                <span>{runResult.mode}</span>
                <span>{runResult.messages.length} messages</span>
              </div>

              <TranscriptView messages={runResult.messages} />

              {runResult.errors.length > 0 && (
                <div className="run-error-list">
                  {runResult.errors.map((error, index) => (
                    <div className="run-error" key={`${error.persona_id}-${index}`}>
                      <strong>{String(error.persona_name ?? "Persona error")}</strong>
                      <p>
                        {String(error.message ?? "The persona call failed.")}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {session && (
        <section className="panel events-panel" aria-labelledby="events-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Live stream</p>
              <h2 id="events-title">Activity</h2>
            </div>
            <span className="count-badge">{eventConnectionStatus}</span>
          </div>

          <div className="event-list" role="log" aria-live="polite">
            {liveEvents.length === 0 && (
              <div className="inline-note">Waiting for session events...</div>
            )}

            {liveEvents.map((event) => (
              <article
                className={`event-row event-${event.status}`}
                key={event.id}
              >
                <div>
                  <strong>{event.message}</strong>
                  <span>{event.type}</span>
                </div>
                {(event.persona_name || event.provider || event.model) && (
                  <span className="event-meta">
                    {[event.persona_name, event.provider, event.model]
                      .filter(Boolean)
                      .join(" / ")}
                  </span>
                )}
              </article>
            ))}
          </div>
        </section>
      )}

      {session && (
        <section className="panel chat-panel" aria-labelledby="chat-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Chat room</p>
              <h2 id="chat-title">Follow-up Chat</h2>
            </div>
            <span className="count-badge">
              {transcriptMessages.length} messages
            </span>
          </div>

          <TranscriptView messages={transcriptMessages} />

          <form className="chat-form" onSubmit={handleSendChat}>
            <label className="chat-message-field">
              <span>Message</span>
              <textarea
                onChange={(event) => setChatMessage(event.target.value)}
                placeholder="Ask a follow-up..."
                required
                rows={4}
                value={chatMessage}
              />
            </label>

            <label>
              <span>Target</span>
              <select
                onChange={(event) =>
                  setChatTargetType(event.target.value as ChatTargetType)
                }
                value={chatTargetType}
              >
                <option value="council">Ask whole council</option>
                <option value="persona">Ask one persona</option>
              </select>
            </label>

            {chatTargetType === "persona" && (
              <label>
                <span>Persona</span>
                <select
                  disabled={sessionNonModeratorPersonas.length === 0}
                  onChange={(event) => setChatPersonaId(event.target.value)}
                  required
                  value={chatPersonaId}
                >
                  {sessionNonModeratorPersonas.map((persona) => (
                    <option key={persona.id} value={persona.id}>
                      {persona.name}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <label>
              <span>Provider override</span>
              <select
                onChange={(event) =>
                  setChatProviderOverride(event.target.value as ProviderName)
                }
                value={chatProviderOverride}
              >
                <option value="mock">mock</option>
                <option value="openai">openai</option>
              </select>
            </label>

            <label className="checkbox-row">
              <input
                checked={chatIncludeModeratorSummary}
                onChange={(event) =>
                  setChatIncludeModeratorSummary(event.target.checked)
                }
                type="checkbox"
              />
              <span>Include moderator summary</span>
            </label>

            <button
              disabled={
                isSendingChat ||
                !chatMessage.trim() ||
                (chatTargetType === "persona" && !chatPersonaId)
              }
              type="submit"
            >
              {isSendingChat ? "Sending..." : "Send"}
            </button>
          </form>

          {chatError && (
            <div className="run-error" role="alert">
              <strong>Error</strong>
              <p>{chatError}</p>
            </div>
          )}

          {chatErrors.length > 0 && (
            <div className="run-error-list">
              {chatErrors.map((error, index) => (
                <div className="run-error" key={`${error.persona_id}-${index}`}>
                  <strong>{String(error.persona_name ?? "Persona error")}</strong>
                  <p>{String(error.message ?? "The persona call failed.")}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {session && (
        <section className="panel export-panel" aria-labelledby="export-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Session archive</p>
              <h2 id="export-title">Export Session</h2>
            </div>
            <span className="count-badge">{exportFormat}</span>
          </div>

          <form className="export-form" onSubmit={handleGenerateExport}>
            <label>
              <span>Format</span>
              <select
                onChange={(event) =>
                  setExportFormat(event.target.value as ExportFormat)
                }
                value={exportFormat}
              >
                <option value="markdown">Markdown</option>
                <option value="json">JSON</option>
              </select>
            </label>

            <label className="checkbox-row">
              <input
                checked={exportIncludeEvents}
                onChange={(event) =>
                  setExportIncludeEvents(event.target.checked)
                }
                type="checkbox"
              />
              <span>Include events</span>
            </label>

            <label className="checkbox-row">
              <input
                checked={exportIncludeMetadata}
                onChange={(event) =>
                  setExportIncludeMetadata(event.target.checked)
                }
                type="checkbox"
              />
              <span>Include metadata</span>
            </label>

            <button disabled={isGeneratingExport} type="submit">
              {isGeneratingExport ? "Generating..." : "Generate Export"}
            </button>

            <button
              onClick={() => handleDownloadExport("markdown")}
              type="button"
            >
              Download Markdown
            </button>

            <button onClick={() => handleDownloadExport("json")} type="button">
              Download JSON
            </button>
          </form>

          <div className="management-actions">
            <button
              disabled={isClearingTranscript}
              onClick={handleClearTranscript}
              type="button"
            >
              {isClearingTranscript ? "Clearing..." : "Clear Transcript"}
            </button>
            <button
              disabled={isClearingEvents}
              onClick={handleClearEvents}
              type="button"
            >
              {isClearingEvents ? "Clearing..." : "Clear Events"}
            </button>
          </div>

          {exportError && (
            <div className="run-error" role="alert">
              <strong>Error</strong>
              <p>{exportError}</p>
            </div>
          )}

          {managementError && (
            <div className="run-error" role="alert">
              <strong>Error</strong>
              <p>{managementError}</p>
            </div>
          )}

          {exportResponse && (
            <div className="export-result" role="status">
              <div className="provider-meta">
                <span>{exportResponse.filename}</span>
                <span>{exportResponse.content_type}</span>
                <button onClick={handleCopyExport} type="button">
                  {copyStatus || "Copy"}
                </button>
              </div>
              <textarea
                className="export-output"
                readOnly
                value={exportResponse.content}
              />
            </div>
          )}
        </section>
      )}

      <section className="panel provider-panel" aria-labelledby="provider-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Provider adapter</p>
            <h2 id="provider-title">Provider Test</h2>
          </div>
          <span className="count-badge">{providerName}</span>
        </div>

        <form className="provider-form" onSubmit={handleProviderTest}>
          <label>
            <span>Persona</span>
            <select
              disabled={personaStatus !== "ok"}
              onChange={(event) => setProviderPersonaId(event.target.value)}
              required
              value={providerPersonaId}
            >
              {personas.map((persona) => (
                <option key={persona.id} value={persona.id}>
                  {persona.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Provider</span>
            <select
              onChange={(event) => setProviderName(event.target.value as ProviderName)}
              value={providerName}
            >
              <option value="mock">mock</option>
              <option value="openai">openai</option>
            </select>
          </label>

          <label className="provider-prompt">
            <span>User prompt</span>
            <textarea
              onChange={(event) => setProviderPrompt(event.target.value)}
              required
              rows={4}
              value={providerPrompt}
            />
          </label>

          <button
            disabled={
              isTestingProvider ||
              personaStatus !== "ok" ||
              !providerPersonaId ||
              !providerPrompt.trim()
            }
            type="submit"
          >
            {isTestingProvider ? "Testing..." : "Test Provider"}
          </button>
        </form>

        {providerResponse && (
          <div className="provider-result" role="status">
            <div className="provider-meta">
              <span>{providerResponse.provider}</span>
              <span>{providerResponse.model}</span>
              <span>{providerResponse.persona_name}</span>
            </div>
            <p>{providerResponse.content}</p>
          </div>
        )}

        {providerError && (
          <div className="provider-result provider-result-error" role="alert">
            <strong>Error</strong>
            <p>{providerError}</p>
          </div>
        )}
      </section>
    </main>
  );
}

export default App;
