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
| `ollama` | — (local server, no key) | `OLLAMA_HOST`, `OLLAMA_MODEL` | `qwen2.5:7b-instruct` @ `http://localhost:11434` | No — but the model must already be pulled locally (`ollama pull qwen2.5:7b-instruct`) |

### Current default

**`LLM_PROVIDER=ollama`** (`OLLAMA_MODEL=qwen2.5:7b-instruct`) — switched
2026-09-03 for a fully-local, always-available master-prompt assembler
(the Gemini free tier's 20 req/day cap made it unusable for real traffic).
`qwen2.5:7b-instruct` was chosen for strong constraint-following on a short
rephrase task, non-reasoning (no wasted latency), and fitting an M4/16GB
next to the extraction pipeline. Swap to `gemini` / `anthropic` (or another
Ollama model) just by changing `LLM_PROVIDER` / `OLLAMA_MODEL` and setting
that provider's key; nothing else in the code needs to move.

**Previous default: `LLM_PROVIDER=gemini`** — set that way while a Gemini
key was on hand for testing.

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

## CHOICE Bucket Matching Engine (not an LLM, no key)

After a master prompt is confirmed, `bucket_client.py` POSTs it to the
CHOICE Bucket Matching Engine (`POST /tooltip`) to get the "also consider
thinking about…" reflection prompts shown on the confirmed screen. This is
a separate REST service, not an LLM and not this repo.

- **No key / no auth** (the endpoint is currently open).
- **`BUCKET_API_URL`** — optional env var; overrides the hardcoded default
  base URL (`https://choice-bucket-matching.onrender.com`). Set it only to
  point at a different deployment or a local run of that service.
- The service is on a free tier that spins down when idle, so the first
  call after a lull can take up to a minute — `bucket_client.py` uses a
  150s timeout and `app.py` shows a loading state. A failure here is
  non-blocking: the confirmed master prompt still shows, just without the
  prompts.

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
