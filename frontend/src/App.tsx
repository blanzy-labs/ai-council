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
  const [title, setTitle] = useState("Slice B test council");
  const [topic, setTopic] = useState("Review the persona and session model slice.");
  const [mode, setMode] = useState<CouncilMode>("ask_council");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [session, setSession] = useState<CouncilSession | null>(null);
  const [sessionError, setSessionError] = useState("");
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
    } catch (error) {
      setSessionError(
        error instanceof Error ? error.message : "Could not create session.",
      );
    } finally {
      setIsSubmitting(false);
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
