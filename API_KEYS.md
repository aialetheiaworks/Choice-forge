# LLM provider & API key reference

This is the **one file** to read when you want to switch which LLM answers
the confirmed master prompt (Phase 4), or add a new provider. Nothing else
in the codebase needs to change for a provider switch — `app.py` only ever
calls `llm_client.generate_output(prompt)`, and that function reads the
`LLM_PROVIDER` environment variable to decide who actually gets called.

```
app.py --calls--> llm_client.generate_output()
                       |
                       | reads LLM_PROVIDER env var
                       v
              llm_providers/{provider}.py
```

## Switching providers

Set two things and nothing else:

1. `LLM_PROVIDER` — which provider to use (see table below).
2. That provider's own env var(s) — also below.

Either `export` them in your shell, or copy `.env.example` to `.env` and
fill it in (`.env` is gitignored and loaded automatically — never commit
it, and never paste a real key into a chat, a doc, or a commit).

## Providers

| `LLM_PROVIDER` value | Required env var(s) | Optional env var (model override) | Default model | Needs a key? |
|---|---|---|---|---|
| `gemini` | `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) | `GEMINI_MODEL` | `gemini-3.6-flash` | Yes |
| `anthropic` | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` | `claude-opus-5` | Yes |
| `ollama` | — (local server, no key) | `OLLAMA_HOST`, `OLLAMA_MODEL` | `llama3.1` @ `http://localhost:11434` | No — but the model must already be pulled locally (`ollama pull llama3.1`) |

### Current default

**`LLM_PROVIDER=gemini`** — set this way temporarily for testing, since a
Gemini key was already on hand. Swap to `anthropic` (or anything else)
just by changing `LLM_PROVIDER` and setting that provider's key; nothing
else in the code needs to move.

## Security

- **Never hardcode a key anywhere in this repo.** Every provider module
  under `llm_providers/` reads its key from the environment only, via
  each SDK's own default credential resolution — the same pattern for
  every provider, so there's nothing provider-specific to remember.
- **Never commit `.env`.** It's in `.gitignore`; only `.env.example`
  (no real values) is tracked.
- **Never paste a real key into chat, a commit message, an issue, or this
  file.** If a key is ever accidentally exposed (chat, log, screenshot),
  treat it as compromised and rotate it at the provider's console —
  don't just "not use it."
- `app.py` never imports a provider SDK directly, and never touches an
  env var itself — it only calls `llm_client.generate_output()`. All key
  handling stays inside `llm_providers/`.

## Adding a new provider

1. Create `llm_providers/<name>_provider.py` with one function:
   ```python
   def generate(master_prompt: str) -> str:
       ...  # call the provider, return its answer as plain text
   ```
   Read that provider's key/model from `os.environ` the same way the
   existing providers do — never hardcode. Reuse
   `llm_providers._shared.SYSTEM_PROMPT` for the system prompt so wording
   doesn't drift between providers.
2. Register it in `llm_client.py`'s `PROVIDERS` dict.
3. Add a row to the table above and to `.env.example`.

That's the whole contract — `llm_client.py` and `app.py` don't need to
change.
