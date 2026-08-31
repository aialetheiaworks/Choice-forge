# Tooltip Integration Plan — LLM builds the master prompt, Bucket Matching Engine drives reflection

**Status:** Phase A in progress (started 2026-08-30). Phases B–D not started.

## Why

CHOICE was never meant to hand the user an answer — its job is to make the
user think harder about their own decision (CLAUDE.md: "reasoning
integrity, not predictive accuracy").

- The final LLM "generate an answer" step (Phase 4 / "Step 6") is removed.
- The same LLM budget is repurposed to **assemble the master prompt**: take
  the user's confirmed extraction fields + original query and produce one
  well-formed objective statement — rephrasing only, never inventing.
- That master prompt is sent to the **CHOICE Bucket Matching Engine**
  (`POST /tooltip`), which returns 5–7 "if you're talking about X, also
  consider Y" nudges. Those nudges are the product's think-harder
  mechanism.

## What does NOT change

The entire extraction pipeline: spaCy → CRF → T5 → polarity guard → 9
fields with confidence/blanks. No retraining, no `pipeline.py` changes, no
`prompt_synthesis.py` template changes. The template still produces the
draft the user reviews and edits in the Phase 3 confirm/fill UI.

## New end-to-end flow

1. User submits query.
2. Pipeline extracts 9 fields (unchanged).
3. Template renders a draft master prompt + flags blanks (unchanged).
4. User fills blanks / edits fields / confirms (unchanged Phase 3 UI).
5. **NEW** — on confirm, send (query + confirmed fields) to the LLM **once**
   → polished master prompt. Missing / not-applicable fields are omitted,
   not guessed. Falls back to the template sentence if the call fails.
6. **NEW** — POST that master prompt to the Bucket Matching API → render
   the returned tooltip lines as the "think about this" panel.
7. No answer is generated.

**Decisions locked (2026-08-30):**
- LLM runs *after* the user fills blanks — one call, on confirm.
- Think-harder mechanism for now = bucket tooltips only. No step-by-step
  guided build yet.
- The raw-query bypass ("just answer me directly" after 2 rejects) is
  **removed** — the product never generates an answer anywhere.
- After the LLM assembles the master prompt there is a **"looks right?"
  gate** (`review_prompt` mode) before it's logged / sent to the buckets.

## Phases

### Phase A — swap Step 6 for master-prompt synthesis  ← DONE (2026-08-30, not yet click-tested)

Files:
- `llm_providers/_shared.py` — `MASTER_PROMPT_SYSTEM_PROMPT` (assemble only
  what's given, never invent, omit what's absent, output only the
  statement).
- `llm_client.py` — `generate_master_prompt(prompt)` using it.
- `master_prompt_llm.py` (new) — `build_user_message(query, final_fields)`
  builds a compact `role: value | MISSING | NOT APPLICABLE` payload;
  `generate_master_prompt(query, final_fields)` returns `(text, error)`,
  never raises (falls back to template on any provider error).
- `app.py`:
  - confirm is now 2 steps — `_prepare_review()` makes the one LLM call and
    parks the flow in `review_prompt` mode; the user approves the assembled
    sentence ("✅ Looks right") before `_log_and_finish()` logs it.
  - "✏️ Not quite — fix the fields" from the gate returns to the edit form
    with the user's edits preserved.
  - the confirmed view shows the LLM master prompt (template sentence is the
    fallback, noted in a caption when used).
  - the "Answer" / "Send to {provider}" block and the 2-reject raw-query
    bypass are both removed; the reject path now offers only "🔁 Rephrase
    and try again".
- correction-log entries gain `master_prompt_llm` + `master_prompt_llm_error`
  (extra Phase 5 training signal). `correction_log.py` itself unchanged.

`llm_client.generate_output()` is now unused (kept for now; Phase D may or
may not want it).

Left for the next session: live click-through of the full flow (browser
extension was offline when Phase A was built).

### Phase B — Bucket Matching API integration  ← DONE (2026-08-30, not yet click-tested)

Service: `https://choice-bucket-matching.onrender.com` — `POST /tooltip`
`{"master_prompt": "..."}` → `{tooltip_lines, ranked}`. Free-tier Render,
cold-starts slowly (~1 min after idle). No auth. `GET /health` →
`{"status":"ok","buckets_loaded":80}`.

- `bucket_client.py` (new) — stdlib `urllib` (no new dep), 150s timeout for
  cold starts, certifi SSL context (the python.org macOS build ships no CA
  bundle), `get_tooltips(master_prompt) -> (ranked, error)`, never raises.
- `app.py` — on the confirmed screen, fetch once per `run_id` (spinner +
  cold-start note) and render `ranked` as a card grid under the master
  prompt: bucket name + its prompt + matched terms. Error → non-blocking
  caption + "Try again" button. `[]` → "no prompts surfaced".
- `BUCKET_API_URL` env override (optional — default is baked in),
  `.env.example` + `API_KEYS.md` documented. `certifi` added to
  `requirements.txt` (was already transitive).
- Verified: `/health` + a real `/tooltip` call return correctly;
  `bucket_client.get_tooltips()` tested directly against the live service
  and the empty-input guard.
- Not click-tested in the UI (browser offline this session).

Not done in Phase B: logging which prompts the user saw for a given master
prompt back to the correction log (the entry is already written at confirm,
before the fetch) — a candidate for Phase C.

### Phase C — token & prompt hardening  ← DONE (2026-08-31)

- Payload was already lean (compact `role: value | MISSING | N/A` list) —
  no trim needed.
- `max_tokens` cap plumbed through all three providers
  (`generate(..., max_tokens=None)`): anthropic `max_tokens`, gemini
  `generation_config.max_output_tokens`, ollama `options.num_predict`.
  `llm_client.MASTER_PROMPT_MAX_TOKENS = 2048` — a safety ceiling, not a
  tight budget: it has to leave room for a reasoning model's thinking
  tokens (256 truncated `gemini-3.6-flash` mid-sentence).
- One retry in `master_prompt_llm.generate_master_prompt` (`_MAX_ATTEMPTS`).
- The LLM call already happened exactly once per confirm (the
  `review_prompt` refactor did that); added a `(query, resolved fields)`
  signature cache in `_prepare_review` so bouncing gate↔edit-form without
  changing anything doesn't re-bill.
- `data/eval_master_prompt_faithfulness.py` (new) — runs 12 queries
  (multi-field, sparse, compound, negation, dense-number holdout rows)
  through pipeline → assemble, and flags any number / % / money / year in
  the output that can't be traced to the query or a field value.
  **First run: 5/12 completed clean (0 unbacked specifics); the other 7
  hit the Gemini free-tier daily cap (20 req/day) — re-run next quota
  window.** The 5 that landed introduced no fabricated specifics; one
  ("Acme Corp… expand into three new markets") came back vague because
  the pipeline extracted nothing for intent/object, not because the LLM
  invented — correct "omit what's missing" behavior.
- **Operational finding:** master-prompt assembly now fires on every
  confirm. The Gemini free tier is **20 requests/day** AND highly variable
  latency (measured 6s / 14s / 68s on identical calls — the 68s is
  free-tier throttling/queueing, not our code). `thinking_level="minimal"`
  is now set for this call (gemini-3.x are reasoning models; default
  thinking took ~37s for a one-sentence rephrase) which fixes the base
  case, but the tail latency is a free-tier property. A paid key or a
  different provider is a hard prerequisite before the app is shared
  again.
- Latency-fix follow-up: `generate(..., thinking_level=None)` added to all
  three providers (gemini maps it to
  `generation_config.thinking_level`; anthropic/ollama accept + ignore).
- `render_sentence()` (the template fallback) hardened: no longer stutters
  when `intent` already contains the object ("cut ticket backlog ticket
  backlog"), and drops a clause whose field is blank with empty text
  instead of emitting a dangling "because ." (only bit api.py's
  `/assemble` — Streamlit blanks carry a placeholder string and still
  render so the user sees what's missing).

Not done: logging which bucket prompts the user saw back to the correction
log — the entry is written at confirm, before the (slow, cold-startable)
tooltip fetch; a second durable write isn't worth it pre-real-users.

### Phase D — API-ify everything + new frontend

**Backend — DONE (2026-08-31), `api.py`:**
- FastAPI, every endpoint a thin wrapper over an already-tested function:
  - `POST /extract` — query → raw `fields` + `display_fields` + template
    master prompt + blanks/needs_review + compound-query flag.
  - `POST /assemble` — query + confirmed fields → LLM master prompt (with
    `template_master_prompt` fallback, `used_llm`, `error`).
  - `POST /tooltip` — proxy to `bucket_client.get_tooltips`.
  - `POST /log` — `correction_log.log_correction` (returns github /
    local_fallback).
  - `GET /health`.
- CORS open (`*`) — lock to the real frontend origin before anything
  public.
- `fastapi` + `uvicorn[standard]` added to `requirements.txt`. Run:
  `uvicorn api:app --reload`.
- `app.py` (Streamlit) untouched — parallel interface until the frontend
  exists.
- Verified: full `/extract → /assemble → /tooltip` flow via
  `fastapi.testclient`; 422 on empty input.

**Frontend — NOT STARTED, needs decisions:**
- Stack (React/Next, Svelte, plain?), hosting, how the "field survey
  instrument" design system ports over.
- Then: retire Streamlit; `api.py` becomes the only backend.

**Local master-prompt generation** (no API LLM) drops in here as a provider
swap when the team grows — no flow change. Also relevant now given the
Gemini free-tier cap found in Phase C.

## Open decisions

1. ~~Bucket Matching API URL~~ — **resolved** (2026-08-30):
   `https://choice-bucket-matching.onrender.com`. Phase B built.
2. ~~Raw-query bypass~~ — **removed** (2026-08-30).
3. ~~Re-confirm the LLM master prompt~~ — **yes, "looks right?" gate added**
   (2026-08-30).

## Safety note

The stakeholder rule "never assume a value for an empty or low-confidence
field" still holds: the LLM only rephrases fields the user already vetted,
is instructed to omit anything MISSING / NOT APPLICABLE, and is tested in
Phase C against that exact failure mode. If Phase C testing shows it
inventing specifics, the fix is a stricter system prompt or reverting to
the deterministic template — not shipping it.
