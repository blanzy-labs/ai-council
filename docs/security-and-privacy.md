# Security And Privacy Notes

AI Council v0.1.x is intended for local testing and demos.

## Local-First Design

- The app is designed to run locally.
- There is no login.
- There is no database.
- There is no telemetry.
- There is no intentional persistence.
- In-memory session, transcript, and event data disappears when the backend restarts.

## Secrets And API Keys

- `.env` is gitignored.
- `.env.example` contains placeholders only.
- API keys stay server-side in the backend environment.
- The frontend does not need `OPENAI_API_KEY`.
- The mock provider works without any API key.

## Provider Privacy

- The mock provider does not call external services.
- The OpenAI provider sends prompts/transcript context to OpenAI only when OpenAI is selected or configured for a provider flow.
- Users should not paste secrets, private credentials, or sensitive personal data into prompts.

## Exposure Limits

- v0.1.x is not hardened for public internet exposure.
- It has no authentication or authorization layer.
- It is intended for local testing/demo use on trusted machines and networks.

## Disclaimer

Read the [project disclaimer](disclaimer.md). Users are responsible for their own usage, costs, data, decisions, and outcomes.
