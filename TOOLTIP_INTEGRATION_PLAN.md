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

### Phase B — Bucket Matching API integration  (BLOCKED: need a reachable URL)

- `bucket_client.py` (new) — `POST {BUCKET_API_URL}/tooltip`,
  `{"master_prompt": ...}` → ranked buckets + tooltip lines, short timeout,
  graceful degrade (show prompt without nudges if the service is down).
- `app.py` — render tooltip lines under the confirmed master prompt.
- `BUCKET_API_URL` in `.env` / Streamlit secrets; document in `API_KEYS.md`.

### Phase C — token & prompt hardening

- Trim payload to essentials, pin `max_tokens`, cheap retry, cache
  identical (query+fields) calls within a session so re-renders don't
  re-bill.
- Test the system prompt against ≥10 existing eval queries; confirm it
  never introduces a specific (number / date / name / constraint) not
  present in the inputs.

### Phase D — API-ify everything + new frontend  (large, later)

- FastAPI backend: `POST /extract`, `POST /synthesize`, proxy `/tooltip`.
- New frontend calls those; Streamlit retired to prototype status.
- Local master-prompt generation drops in here as a provider swap when the
  team grows — no flow change.

## Open decisions

1. **Bucket Matching API** — deployed + reachable (URL)? Or still local
   code? Phase B blocked until callable.  ← STILL OPEN

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
