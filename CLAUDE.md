# CHOICE Forge v1 — rules, folder map, and status

Claude Code reads this file automatically at the start of every session
opened in this directory — it does not need to be pointed at manually. Keep
the **Rules** section below stable and update it rarely; keep the
**Current status** section current every session that makes real progress.

## Rules for working in this repo

**When beginning a fresh session, read in this order:**

1. This file, fully (already done automatically).
2. `git log --oneline -10` and `git status` — this file is a snapshot at
   last commit; the repo may have moved since if edited outside a session.
3. `ABOUT.md` if you need the architecture rationale (why 4 layers, why
   CRF trains on `source_text` not `value`, known limitations).
4. `README.md` if you need setup/run/retrain commands.
5. `data/real_world_eval_report.json` if you need the latest measured
   real-world accuracy detail (regenerated each time the eval harness runs).

**Folder map — what lives where and why:**

| path | purpose |
| --- | --- |
| `choice_forge_dataset_full_100_v2.json` | Original 100-row dataset. **LLM-generated, not real text** (confirmed by user). Treat as immutable — don't hand-edit; combine via new files instead. |
| `choice_forge_dataset_combined_120.json` | Current training dataset: original 100 + 20 real rows. Regenerate via `data/build_combined_dataset.py` (don't hand-build with a one-off script — that's how this file was first created and it's not reproducible). |
| `role_tagger.joblib`, `value_synthesizer/` | Trained model artifacts. Always regenerate via the retrain commands in `README.md`, never hand-edit. |
| `data/real_world_eval_holdout.json` | **Permanent, frozen real-world benchmark. NEVER train on this file.** It's the only trustworthy way this project can measure itself against real (non-synthetic) text. May only grow via deliberate, validated curation — never silently regenerated. |
| `data/real_world_training_augment.json` | Real, source-verified rows approved for training. Grows over time as more batches are sourced. |
| `data/build_real_world_pilot.py` | Template for constructing new real-sourced, hand-labeled rows (with `_source_url` provenance). Copy/extend this pattern for new batches rather than writing raw JSON by hand. |
| `data/validate_real_world_pilot.py` | Checks new rows against the _actual_ `row_to_bio` training function: source_text substring correctness + no cross-role span overlap. Run this on any new batch before trusting it. |
| `data/split_real_world_pilot.py` | Stratified eval/train split logic (rare roles get spread across both sets). |
| `data/eval_on_real_world.py` | The only end-to-end, real-world scoring harness. Run after every retrain. |
| `data/real_world_eval_report.json` | Latest eval run's per-row, per-field detail. Regenerated each run — not hand-edited. |
| `Doc/` | Pre-existing human-reference explainer PDFs (one per layer). Not auto-generated, don't touch without reason. |
| `app.py` | Streamlit stakeholder UI. Also hosts the Phase 3 fill-in-blank/confirm-reject "Master Prompt" section (calls `prompt_synthesis.py` + `correction_log.py`). |
| `prompt_synthesis.py` | Phase 1 of the Product vision below: deterministic-template master-prompt synthesis from a `Pipeline.run()` result. `render_sentence()` (the sentence-assembly core) is shared with `app.py`'s confirm/reject re-render step. |
| `correction_log.py` | Phase 3: appends one JSON object per confirm/reject decision from `app.py` to `data/corrections_log.jsonl`. This is the training data Phase 5 will retrain the prompt-synthesis model on. |
| `data/corrections_log.jsonl` | Append-only log of every confirm/reject decision (written by `correction_log.py`). Versioned like `data/seq2seq_pairs.jsonl` — not gitignored, not hand-edited. |
| `llm_client.py` | Provider-agnostic router. Reads `LLM_PROVIDER` and dispatches to the matching module in `llm_providers/`. Callers use `generate_master_prompt()` (tooltip plan Phase A — the live path) or `generate_suggestions()` (`blank_suggestions.py`); `generate_output()` is the old Phase-4 answer call, now **unused** (kept for now). Never a provider SDK directly. |
| `llm_providers/` | One module per LLM provider (`anthropic_provider.py`, `gemini_provider.py`, `ollama_provider.py`), each a single `generate(prompt, system_prompt=SYSTEM_PROMPT) -> str` function reading its own key/model from the environment. Adding a provider = one new module + one registry line in `llm_client.py`. Never hardcode a key in any of these. |
| `blank_suggestions.py` | Optional, explicitly opt-in extension to Phase 3: on request (`app.py`'s "Suggest values for blanks" button), asks the configured LLM for plausible-but-unverified values for currently-blank master-prompt fields, using `SUGGESTION_SYSTEM_PROMPT` (`llm_providers/_shared.py`) -- a different, stricter system prompt than Phase 4's answer-generation call. Never auto-applied: the user must tick a box per field to pull a suggestion into the form, same as typing it themselves. Exists specifically to answer 2026-08-06 stakeholder feedback that wanted invented actor/context/constraint text folded in as if it were extracted fact, without breaking the "never assume a value for an empty field" rule below -- see that day's Current-status entry for the full reasoning. |
| `master_prompt_llm.py` | Tooltip-integration plan, Phase A: on confirm, sends (query + the user-confirmed 9 fields) to the configured LLM via `llm_client.generate_master_prompt()` to assemble a polished master-prompt sentence — rephrase only, never invent, omit MISSING/NOT APPLICABLE. Returns `(text, error)`, never raises; `app.py` falls back to `prompt_synthesis.render_sentence()` on error. This **replaced** the old Phase 4 "generate an answer" step — the product no longer produces answers. |
| `bucket_client.py` | Tooltip-integration plan, Phase B: `get_tooltips(master_prompt) -> (ranked, error)` — POSTs the confirmed master prompt to the external CHOICE Bucket Matching Engine (`BUCKET_API_URL`, default `https://choice-bucket-matching.onrender.com`), which returns up to ~7 "also consider thinking about X" reflection prompts. stdlib `urllib` + certifi SSL context, 150s timeout (free-tier cold start), never raises. |
| `api.py` | Tooltip-integration plan, Phase D (backend): the whole flow as a FastAPI JSON API (`/extract`, `/assemble`, `/tooltip`, `/log`, `/health`) — thin wrappers over the functions above, no new logic. `uvicorn api:app --port 8000`. `app.py` (Streamlit) is untouched and still works; `api.py` is what `frontend/` talks to. |
| `frontend/` | Tooltip-integration plan, Phase D (frontend): React + Vite + TS + Tailwind v4 app, built 2026-09-02/03 session — talks to `api.py` over HTTP (base URL entered at startup, remembered in `localStorage`, auto-reconnects). Mirrors `app.py`'s exact flow (extract → edit/blank-fill → LLM-assembled master prompt → confirm/reject) and adds the one thing Streamlit didn't have: matched bucket terms in the confirmed master prompt are underlined per-bucket-color with a hover tooltip (`src/lib/highlight.ts`, `src/components/HighlightedPrompt.tsx`). Reuses the Streamlit build's "field survey instrument" design tokens (`src/index.css`). Run: `npm run dev` (port 5173) alongside `uvicorn api:app --port 8000`. Streamlit (`app.py`) is untouched and still works in parallel. |
| `data/eval_master_prompt_faithfulness.py` | Repeatable check for the tooltip plan's safety premise: runs queries through pipeline → `master_prompt_llm` and flags any number / % / money / year in the assembled prompt that can't be traced to the query or a field value (i.e. the LLM invented a specific). Makes one real LLM call per query. |
| `TOOLTIP_INTEGRATION_PLAN.md` | The living plan for the 2026-08-30 product pivot (LLM builds the master prompt, Bucket Matching Engine drives reflection, no answer generation). Phases A–D, decisions, open items. |
| `API_KEYS.md` | The one file to read to switch providers, see every env var per provider, or add a new one. Security rules for keys live here too. Also documents `BUCKET_API_URL`. |
| `.env.example` | Template for `.env` (gitignored) — no real values, ever. |

**Standing safety rules:**

- Never add rows to or otherwise touch `data/real_world_eval_holdout.json`
  as part of a training step. If it ever needs to grow, that's a deliberate,
  separate decision, not a side effect of a retrain.
- Never claim a retrain "improved things" without re-running
  `python3 data/eval_on_real_world.py` and comparing numbers. Feelings about
  output quality are not a substitute for the frozen eval score.
- When sourcing new real-world rows, reuse the
  build → validate → split pattern rather than hand-writing JSON directly —
  the validator has already caught real mistakes (overlapping spans,
  mismatched source_text) that would otherwise silently corrupt training.
- Prefer updating this file's **Current status** section over creating new
  status/summary docs elsewhere in the repo — one living file, not several
  competing ones.

## Product vision — the full CHOICE framework (agreed 2026-07-29, expanded 2026-08-01)

CHOICE Forge (everything documented above) is layer 1 of a larger product,
not the end product itself. Two source docs (external to this repo, not
under version control here) define the full scope — read them if you need
the primary text instead of this summary:
`/Users/amaansaify/Desktop/alethiaworks.org/Plan/The CHOICE framework details_v1.pdf`
and `/Users/amaansaify/Desktop/alethiaworks.org/Plan/Knowledge_Bucket_Library.pdf`.

**Positioning:** CHOICE is one product inside a planned "Decision
Intelligence Platform" (sibling products: PESTLE, SWOT, TOWS, Porter's Five
Forces, Ansoff, JTBD, STP, Value Proposition Canvas). Those siblings are
**not in scope** for this repo — noted here only so "CHOICE" isn't mistaken
for the whole platform.

**CHOICE's philosophy — read this before designing any scoring or
confidence logic:**

- Success metric is **reasoning integrity, not predictive accuracy**.
  CHOICE does not judge whether the user's inputs are _true_ — only
  whether the reasoning built on top of them is internally consistent.
- CHOICE does NOT: predict outcomes, verify/fact-check every input (it
  trusts stated values like "my budget is ₹10 lakh" unless contradicted
  elsewhere), or make the decision for the user.
- CHOICE DOES three things, in order — the three steps below map directly
  onto the phases in the build order:
  1. **Clarify the Decision** — vague objective → precise decision
     statement + identified choices.
  2. **Structure the Reasoning** (the "Horizon") — surface what's known,
     unknown, assumed, and uncertain; check internal consistency across
     objective/assumptions/constraints/choices/success-criteria; ask the
     missing questions.
  3. **Guide the Decision, not predict it** — compare alternatives, surface
     trade-offs/risks/dependencies/missing evidence, explain _why_ one
     option looks stronger under the _stated_ assumptions.

**Naming note — do not conflate these two "bucket" concepts:**
the extraction pipeline's output fields (`actor`, `intent`, `measure`,
`scope`, `context`, `magnitude`, `time`, `constraints`, `object`) should be
called **extraction fields** in docs going forward. **"Knowledge Bucket"**
is a distinct, unrelated concept (see Step 2 / Phase 6 below) — one of
~60 business-analysis categories (Customer, Market, Pricing, Risk,
Technology, Stakeholders, ...) in a fixed library, selected per-query by a
separate Intent Classifier, used only for tooltip guidance text.

**Step 1 workflow (Clarify the Decision — this is what Phases 1-5 below
build):**

1. User inputs a raw business query (the "Objective Statement" raw input).
2. CHOICE Forge extracts it into structured extraction fields — this is
   the pipeline that exists today.
3. A **prompt-synthesis layer** (not built yet) takes the query + its
   extraction fields and generates a **master prompt** (= the framework
   doc's "Objective Statement", e.g. "Increase annual sales of premium
   office chairs by 30% within the next 12 months by targeting SMBs in
   India, while operating within a ₹20 lakh marketing budget and without
   expanding the sales team") — a well-formed, business-grade prompt
   scaffold, not just a template dump of the fields.
4. **Never assume a value for an empty field.** A field the pipeline
   didn't fill at all (`status == "missing"`, no CRF span) becomes an
   explicit `[please fill in]` blank rather than a guess.
   **AMENDED 2026-09-03 (product-owner decision — see that day's Current
   status):** a field the pipeline *did* fill but with *low confidence*
   (`confidence < MIN_JOIN_OPEN_CONFIDENCE`, 0.4) is **no longer blanked**
   — its predicted value is shown in the field, carried into the master
   prompt, and flagged `needs_review` + `low_confidence` for the user to
   check. The "surface uncertainty" guarantee now rests on the visible
   review flag and confidence gauge, not on withholding the value. Only
   genuinely-missing fields are still blanked. The Phase 2 calibration
   audit still stands as the reason low-confidence fields must stay
   flagged for review.
5. The user sees the full master prompt, blanks and all: fills in the
   blanks, and reads through the rest of the prompt. This does two jobs at
   once — real missing data comes from the user instead of being assumed,
   and the user reading the whole prompt is their implicit confirmation
   that the system understood the original query correctly. The framework
   doc also specifies a companion "Clarify Success" field set collected
   alongside the objective: **Success Metric** (must be a quantity
   `<=` what's derivable from the objective statement itself) and
   **Deadline** (assume mid-month if the user gives only a month name).
6. If the user continues, the prompt is confirmed correct and complete. If
   not, a fallback path is needed: curate/regenerate an alternate prompt, or
   diagnose where understanding went wrong before retrying. This
   accept/reject signal is exactly the correction-capture data the
   self-learning flywheel (gap 5 below) needs.
7. Once confirmed, the completed master prompt is sent via API to an LLM to
   produce the actual best-quality output for the user's original query.

**Step 2 workflow (Structure the Reasoning / "Horizon" — new scope from the
2026-08-01 docs, not yet phased into a build order):**

- Once the Step 1 objective is confirmed, an **Intent Classifier**
  (pattern matching — explicitly _not_ the CRF field-extractor, a separate
  component) reads the confirmed objective and selects **up to 5 Knowledge
  Buckets**, in priority order, from the fixed ~60-entry Knowledge Bucket
  Library (full table in `Knowledge_Bucket_Library.pdf` — e.g. Customer,
  Value Proposition, Market, Competition, Risk, Technology, Stakeholders).
  Each bucket contributes one line of guidance text ("Consider customer
  segment, persona, needs...") assembled into a ≤5-line tooltip.
- Each Knowledge Bucket's prompt text quietly embeds an established
  framework (PESTLE, SWOT, Porter's Five Forces, Ansoff, JTBD, STP, VPC)
  without naming it — a link to the relevant standalone tool lives in the
  same tooltip, which is the platform's cross-sell/engagement mechanism
  into the sibling products above.
- This is the mechanism that answers the Horizon questions: what do we
  know / what can we learn / what remains unknowable / which gaps matter
  most for _this_ decision — driven by whichever buckets the classifier
  selected, not a fixed generic checklist.

**Step 3 workflow (Guide the Decision — new scope, not yet phased into a
build order):**

- Compare alternatives using only the information gathered in Steps 1-2.
- Output a transparent recommendation that states its assumptions and
  confidence explicitly — never a bare "do X" without the reasoning
  attached. This is a direct consequence of the reasoning-integrity
  philosophy above: the recommendation must show its work, not just its
  conclusion.

**Knowledge Graph — persisted per session, cuts across all 3 steps (new
scope from the 2026-08-01 docs):**

For every framework session (CHOICE, and eventually PESTLE/TOWS/etc.),
persist four things: (1) the user's typed raw responses, (2) AI
prompts/summaries generated along the way, (3) decision tables /
knowledge-database rows, (4) a knowledge graph of all actors — including
"phantom"/hidden actors like political, economic, or legal-system forces —
and the relationships between them. Node types seen in the framework doc's
worked example: Objective, Internal/External Stakeholders, Customer
Segment, Product/Offering, Market/Geography, Internal Capability/Resource,
External Force (PESTLE), Industry Force (Porter's 5), Constraint, Enabler,
Strategic Option, Outcome/KPI. Relationship types: directly-influences,
related-to/affects, depends-on/enables, constrained-by/limits,
interacts-with/connected-to.

Editing rules for the graph (important — mirrors the "never silently
overwrite raw input" principle already used for extraction fields):

1. The graph can be viewed partially (e.g. "show only actors who are also
   stakeholders", "hide phantom actors", "hide Strategic Options and
   External Macro Environment") — the full graph still exists underneath,
   it's just not rendered.
2. Nodes can be added or removed by the user.
3. Relationships between actors can be edited directly in the graph. Doing
   so regenerates the corresponding AI summary. **The user's original
   typed responses never change** — only the derived summary/graph layers
   do. Edit the derived artifact, never the source-of-truth input.

**Sign-up flow fields (from the framework doc, scoped to `app.py` /
onboarding, independent of the phases below):** business profile fields
are all optional (business name, HQ, product/service description, firm
type, website, primary market B2B/B2C/etc., top 3 competitors); only the
user's own name, mobile number, and email are mandatory.

**Agreed build order:**

- **Phase 1** — build the prompt-synthesis step (Step 1, item 3 above) as
  a deterministic _template_, not a trained model. There is no dataset yet
  of (fields → ideal master prompt) pairs to train on, so a model isn't
  feasible yet. Wire blank-insertion to the existing per-field confidence
  scores. **Core template built — see Current status, 2026-08-03 session.
  Not yet wired into `app.py` (that's Phase 3).**
- **Phase 2** — audit whether those confidence scores are actually
  calibrated (low confidence ⇔ actually wrong/missing), using the same
  eval-harness discipline as `data/eval_on_real_world.py`. This is the
  linchpin of the whole safety design: if confidence is miscalibrated, a
  wrong field slips through as a confident answer instead of getting
  blanked, and the "never assume" guarantee breaks silently. **Done —
  see Current status, 2026-07-29 session.**
- **Phase 3** — build the fill-in-blank + confirm/reject UI in `app.py`, and
  log every accept/reject and every user-filled blank. This log is what
  both measures how often the system gets it right _and_ is the training
  data needed for Phase 5 — do not train a prompt-synthesis model before
  this data exists. **Built — see Current status, 2026-08-03 session.**
- **Phase 4** — wire the final LLM API call (default to Claude via the
  Anthropic API for this) on the confirmed master prompt. **Built — see
  Current status, 2026-08-04 session.**
- **Phase 5** (later) — once accept/reject + fill logs accumulate, train
  the real prompt-synthesis model on them, replacing the Phase 1 template.
  Gate any new version against a frozen holdout, the same way model
  promotion already works for the extraction layer.
- **Gate before Phase 6 (agreed 2026-08-05, senior-dev plan review):**
  do not start Phase 6 until both of the following are true, not just
  time-elapsed:
  1. A real-data sourcing pass has specifically targeted the Known gaps
     list below (`actor` generic role-phrasing, `measure`/`scope`/`context`
     thinness, `intent` hallucination) and `data/eval_on_real_world.py`
     shows measurable improvement over the current 77.8%/63.0% baseline.
  2. Phases 1-4 have real (non-solo-testing) usage generating actual
     correction-log volume — not just the mechanism existing. Building
     Intent Classifier / Knowledge Bucket / Knowledge Graph scope on top
     of an extraction layer that's still 63% value-accurate, before
     anyone outside this session has used the confirm/reject flow, risks
     months of solo effort on unvalidated foundations. **Reasoning:** the
     2026-08-02 session already flagged Phase 8 as the long pole and
     recommended shipping 1-4 as a demoable v1 before starting it — this
     gate makes that recommendation an explicit, checked precondition
     instead of an informal intent that scope-creep could quietly skip.
     This gate does not block continued Phase 1-4 hardening, deployment, or
     real-data sourcing work in the meantime — only the _start_ of Phase 6.
     **Condition 2, reclassified 2026-08-16:** every session from 2026-08-09
     through 2026-08-16 reported condition 2 as "not met, not enough real
     usage yet." That framing was wrong. A real user _did_ use the hosted
     app in this window — the correction data just never survived to reach
     `data/corrections_log.jsonl`, because of the persistence bug described
     in Known gap 11 below (every correction from the hosted deployment was
     written to that container's ephemeral filesystem and discarded on the
     next redeploy/restart). Condition 2 was never a traffic shortfall; it
     was a data-loss bug. Fixed 2026-08-16 (see Known gap 11) — corrections
     now commit straight to this repo via the GitHub Contents API, so they
     survive redeploys. **Condition 2's actual remaining requirement, as of
     the fix:** some minimum volume of real (post-2026-08-16) corrections
     need to actually accumulate and be retained — e.g. a rough floor of
     15-20 real entries, mirroring the "20-30 new rows" batch-retrain
     trigger this file already uses elsewhere — before treating condition 2
     as satisfied. The pre-fix entries in `data/corrections_log.jsonl`
     (21 as of 2026-08-16, all traceable to solo-testing sessions already
     documented in this file) do not count toward that floor.
- **Phase 6** (later, unscoped) — Step 2 / Horizon: build the Intent
  Classifier + wire up the Knowledge Bucket Library and tooltip assembly.
- **Phase 7** (later, unscoped) — Step 3 / Guide: alternative comparison
  and transparent-recommendation generation.
- **Phase 8** (later, unscoped) — Knowledge Graph: persistence of the four
  artifacts above, graph construction/rendering, partial-view toggles,
  node/relationship editing with AI-summary regeneration.
- **Retraining is always batched, never per-query.** Log every correction
  as it comes in, but only retrain on a count/time trigger (e.g. every
  20-30 new rows, or weekly), then gate before promoting. Neither the CRF
  (no incremental-fit mode) nor a per-query eval-gate cost makes retrain-
  per-correction workable — this applies to the extraction layer today and
  will apply to the prompt-synthesis model in Phase 5 too.

## Current status (as of 2026-09-10, continued — full stack deployed to self-hosted server; dropped-content bug found in LLM assembly)

**Deployed the whole stack to a self-hosted Ubuntu server** (not the
choiceforgev1 repo's own git history — this is infra, tracked here since
there's no other place for it). Hardware: Intel i7-4500U, 2 cores/4
threads, 8GB RAM, no usable GPU — a real capacity ceiling, already hit
once this session (an OOM-killed T5 training run, unrelated repo, see
below). SSH: `alethiaworks@192.168.1.70` (LAN) / `100.66.166.101`
(Tailscale), key-based auth (`~/.ssh/id_ed25519_alethiaworks_new` locally),
password auth still enabled for sudo only.

- **`/opt/choiceforge`**: this repo (minus `.git`/`node_modules`/dev
  artifacts), Python venv with CPU-only torch (`--index-url
  .../whl/cpu`, not the default CUDA-bundled wheel) + a trimmed
  `requirements-prod.txt` (no `streamlit`/`ollama` — not used by `api.py`).
  Frontend built (`npm run build`) and served by nginx at `/`, with `/api/`
  proxied (stripped) to `uvicorn api:app` on `127.0.0.1:8000`, managed by
  systemd (`choiceforge-api.service`).
- **LLM provider: local Ollama, `llama3.2:3b`** (not a hosted API — a
  deliberate override of this deployment's own earlier-stated decision to
  use a hosted API; see the dropped-content bug below for why that
  decision may need revisiting). Measured on this hardware: ~1.6s
  extraction (CRF+T5, no LLM), ~8s warm / ~25s cold master-prompt LLM call.
- **`~/choice-bucket-matching`**: the separate `choice-bucket-matching`
  repo (`/Users/amaansaify/Desktop/alethiaworks.org/tooltip` locally),
  deployed the same way (its own venv, `requirements-api.txt`, no torch),
  running as `choice-bucket-matching.service` on `127.0.0.1:8001`. Brought
  the pre-built `bucket_index_cache.pkl` along so it doesn't pay the ~14s
  (or much worse on this CPU) re-lemmatization cost on every restart —
  confirmed reused (1s load, 80 buckets). `choiceforge`'s `.env` now sets
  `BUCKET_API_URL=http://127.0.0.1:8001`, overriding the Render default —
  this replaces the Render free-tier dependency (150s cold-start timeout)
  entirely; everything now runs on one box. Verified end-to-end through
  `choiceforge-api`'s own `/tooltip` proxy: 0.53s, real bucket matches.
- **Real bug found and fixed along the way**: `llm_client.py` hard-imported
  `streamlit` at module level even though its only use (`st.secrets` for
  Streamlit Cloud) was already defensively wrapped in a try/except — broke
  `api.py` (FastAPI, no streamlit dependency) entirely on the trimmed prod
  install. Fixed by moving the import inside the try block. Committed.
- **Verified visually, not just via curl**: opened the deployed frontend in
  a real browser (`http://192.168.1.70/`), connected via
  `http://192.168.1.70/api` (note: the frontend's connect screen needs the
  full `/api` path, not just the bare origin, since nginx strips that
  prefix when proxying and `api.py`'s own routes aren't prefixed), ran a
  real query through the actual UI, confirmed no console errors.
- **New known issue, found via live click-testing, documented in full in
  `TOOLTIP_INTEGRATION_PLAN.md`'s new "Known issue" section**: the LLM
  master-prompt-assembly step silently *drops* confirmed content instead of
  just risking invented content — twice in a row on `llama3.2:3b` (a
  magnitude range's start value, then an entire negation-cue constraint
  clause). `data/eval_master_prompt_faithfulness.py` only checks for
  invented specifics, not omitted ones — doesn't currently catch this.
  Proposed fix (not yet built): extend that eval to check completeness too,
  and A/B test `qwen2.5:7b-instruct` (validated clean on this exact task in
  the 2026-09-03 Mac-based session) against `llama3.2:3b` on this server's
  actual hardware before deciding which model to keep. **Not yet fixed —
  explicitly deferred by the user ("we will work on it later").**
- **Not done yet**: ONNX+INT8 quantization for T5 (the deployment spec's
  own "worth doing" latency note — not attempted this session), Cloudflare
  Tunnel + domain for public access (still LAN/Tailscale-only, matches the
  user's "server is under construction" framing from earlier this session).

**Session paused here (2026-09-10 end) — exact open decision to resume
on:** the user wants a person in Mumbai to access the deployment.
Tailscale device-sharing (admin console, private, requires the other
person to install Tailscale) vs. Tailscale Funnel (`tailscale funnel --bg
80`, CLI-only, gives a real public HTTPS link
`https://amaanalethia.<tailnet>.ts.net`, no install needed on their end,
but genuinely reachable by anyone with the URL — no auth on the app).
Funnel command was prepared but **not run** — blocked by the permission
classifier (publishing to the public internet), correctly deferred for
the user's explicit go-ahead given there's no auth layer on the app yet.
Next session: get that decision, then either run the funnel command or
set up device-sharing instead. No code changes pending — repo is clean,
all committed through `e9d3635`.

## Current status (as of 2026-09-10, continued — regression gate built and proven; `time` data sourced but not yet promotable)

**Built `data/gate_retrain.py`**, a per-row/per-field regression gate:
compares a just-produced `data/real_world_eval_report.json` against the
same file at a baseline git ref (default `HEAD`) and fails if *anything*
previously correct flips to wrong, regardless of what the aggregate score
does. Exists because CRF (`sklearn-crfsuite`) has no warm-start/
incremental-fit mode — every CRF retrain starts from scratch, so unlike
T5's `--continual` (above), there's no way to protect an already-working
role during a CRF retrain.

**Proved its worth immediately.** Sourced 5 more real rows targeting
`time` (Known gap 7's bare "third quarter dividend" pattern — Conoco-
Phillips, Blue Owl Capital x2, Pfizer, Algonquin Power; validated,
committed in `d178a05`). Retraining the CRF on the expanded 160-row set
fixed the exact target bug (`rw_016`'s "third quarter" now detects
correctly) — **but the aggregate status_acc went UP to 83.33%** despite
the gate catching 12 regressions across `measure`/`object`/`context`/
`constraints`/`scope`. Without the gate, the aggregate number alone would
have looked like a promotable improvement. Reverted. A follow-up
`--continual` T5-only retrain on the same data (CRF left at baseline)
caught 1 smaller regression (`rw_044` time value) and was also reverted.
**Net result: the 5 sourced `time` rows are committed and validated, but
no model currently trained on them passes the gate.** Next session should
either try a smaller/isolated batch of this data, tune CRF regularization,
or accept this is CRF's 5th documented instance of the same
shared-capacity fragility (Known gaps 1, 7, 9, plus the two `scope`/`time`
attempts this session) and treat every CRF retrain as gated-by-default
from now on, never promoted on aggregate score alone.

**Also confirmed:** the pooled-CRF architecture question the user raised
(split into per-role models?) was answered from evidence, not guesswork —
see the note below in the 2026-09-10 (first) entry. Nothing about that
answer changed this round; the gate result above simply confirms the
diagnosis a fifth time.

## Current status (as of 2026-09-10 — sourced real `scope` data, fixed T5 retrain regression via warm-start continual fine-tuning)

**Checked the Phase 6 gate's condition 2 (real correction-log volume).**
`data/corrections_log.jsonl` has 38 total entries, 17 post-2026-08-16 (the
persistence fix). That numerically clears the 15-20 floor, but the content
is all traceable to the documented solo click-testing sessions (same
queries repeated across near-identical timestamps, matching commit
`48d92e8`'s "click-tests" log), not real external usage — so by the same
logic that disqualified the pre-fix 21 entries, **condition 2 is still not
honestly satisfied.** Needs actual non-solo usage, not more click-testing.

**Sourced 10 real, source-verified rows targeting `scope`** (`rw_062`-
`rw_071` in `data/build_real_world_pilot.py`), the most data-starved role
(only 4 real examples existed before this). Sourced from 3 companies new to
the dataset (Zscaler, Atlassian, CDW, all Q2/Q4 2026 earnings calls),
deliberately spanning 5 scope types the dataset had zero or thin coverage
of: geography, customer/account-tier ("Fortune 500", 2 companies), 4
industry verticals (healthcare/financial-services/government/education),
product edition, and user-role composition. Validated clean via
`data/validate_real_world_pilot.py`. All 10 went to
`data/real_world_training_augment.json` (55 rows now) — **the frozen
`data/real_world_eval_holdout.json` was deliberately left untouched** (still
16 rows) since growing it needs a separate, explicit decision per this
file's standing rule, not a side effect of a sourcing pass.

**Retraining from scratch on the expanded 155-row combined dataset
regressed the real-world eval** (82.64%/60.87% → 80.56%/55.07%) —
`magnitude`, `constraints`, `context`, and even `scope` itself got worse,
despite the new data only targeting `scope`. This is the same
shared-pooled-model fragility already logged in Known gaps 1/7/9, now
observed a 4th time. Root-caused this session: `train_seq2seq.py` always
restarted T5 fine-tuning from the pretrained `t5-small` base, discarding
everything the model had already learned each time, rather than building
on the last good checkpoint.

**Fix: added `--continual` to `train_seq2seq.py`** — warm-starts from the
current `value_synthesizer/` checkpoint instead of `t5-small`, with a lower
LR (5e-5 vs 3e-4) and fewer epochs (6 vs 20). Retrained this way (CRF left
untouched at the committed baseline, to isolate the T5-side effect) and got
a **clean improvement with zero regressions**: 82.64%/**62.32%** on the
frozen holdout. Only two things changed: one `intent` hallucination gone
(rw_012, "double occupancy" → correctly "double"), one `scope` multi-span
join fixed (rw_034, was garbled with cross-role bleed, now clean). Nothing
else moved. Committed in `870e702`.

**Known remaining gap, stated plainly:** this only fixes the T5 half of the
pipeline. `role_tagger.joblib` (CRF) has no equivalent warm-start/
incremental-fit mode — `sklearn-crfsuite` always trains from scratch — so
retraining the CRF to actually pick up the new `scope` rows' *span
detection* (not just value synthesis, which is all this session's fix
touched) still carries the original regression risk. Next session should
either find/build an incremental-training path for the CRF, or accept that
CRF retrains stay a gated gamble and keep batches small + always compare
against the frozen holdout before promoting (already this project's
practice, just not a solved problem).

Also (unrelated architecture tangent explored and rejected this session,
in case it comes up again): the user asked whether splitting into
per-role models (up to 9, instead of 1 pooled CRF + 1 pooled T5) would
fix the cross-role regression problem, and separately whether a larger
base model (t5-base/t5-large) would help. Both declined, and for
recorded reasons: per-role splitting would starve the already-thinnest
roles further (this dataset is ~155 rows total, some roles under 20
real examples — matches `ABOUT.md`'s own stated reason for pooling in
the first place). A bigger base model wasn't attempted — most
documented failures are CRF/data-volume-limited, not T5-capacity-limited,
and this machine (16GB RAM) already OOM-killed a `t5-small` training run
once this session under normal background load (Chrome/Spotify/WhatsApp),
making `t5-base`+ a real hardware risk, not just an unproven idea.

## Current status (as of 2026-09-03, continued — low-confidence fields now shown, not blanked; both servers running locally)

**Product-owner decision, implemented this session: stop blanking
low-confidence extractions.** The user asked that a field's predicted
value be shown "in its predicted bucket even if the score is low" instead
of being replaced by a `[please fill in]` placeholder. This **reverses**
the original Phase 1 item 4 / Phase 2 calibration-audit design ("never
assume a value for a low-confidence field"). New behaviour:

- `prompt_synthesis._is_blank()` now returns True **only** when
  `status == "missing"` (the CRF opened no span at all). A non-missing
  field below `MIN_JOIN_OPEN_CONFIDENCE` (0.4) is no longer blanked.
- New `_is_low_confidence()` + a `low_confidence` bool on every field in
  `build_fields()`, folded into `needs_review`. `synthesize_master_prompt()`
  returns a new `low_confidence` role list; `api.py /extract` exposes it.
- The low-confidence value **does** flow into the template master prompt
  and the LLM-assembled prompt now (it's a real prediction, just uncertain)
  — the safeguard is now the visible ⚠️ review flag + the rust-coloured
  confidence gauge, not withholding the value.
- **Both frontends updated to keep the "user must look at it" property:**
  the one-click "✅ Yes, this is right" path is suppressed whenever there
  are low-confidence fields (same as it already was for blanks) — the user
  is routed to the edit form, where low-confidence fields are pre-filled
  with the guess, marked "low confidence (0.xx) — check or correct",
  and (for the 5 not-applicable-eligible roles) get the "Not applicable"
  checkbox too. Clearing a pre-filled field now correctly blanks it
  (`cleared` handling added to both `EditForm.tsx` and `app.py`'s resolve
  loop — previously clearing a non-blank field silently kept the old
  value).
- Truly-missing fields (no span) are unchanged: still shown as
  `[role — please fill in]` blanks.
- Files touched: `prompt_synthesis.py`, `api.py`, `app.py`,
  `frontend/src/types.ts`, `App.tsx`, `components/InitialGate.tsx`,
  `components/EditForm.tsx`. `pipeline.py` and the models are untouched —
  `MIN_JOIN_OPEN_CONFIDENCE` still governs the multi-span-join drop inside
  `pipeline.py` exactly as before; only the display/blank layer changed.
- Verified: `prompt_synthesis` CLI + `fastapi.testclient` on a query with
  a genuine 0.36-confidence `scope` — it now renders "Southeast region"
  (blank=False, low_confidence=True, needs_review=True) instead of a
  placeholder; truly-missing fields still blank. `npx tsc --noEmit` clean.
  Not yet click-tested in the live browser UI.
- **`data/eval_on_real_world.py` unaffected** — it scores raw pipeline
  output and only imports `parse_value_items` (unchanged). No retrain, no
  eval-number change.

**Both servers restarted and running locally** (the user asked to "make
the backend and frontend live" = run locally): killed the stale
prior-session processes (were serving pre-change code) and started fresh:
- `python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload`
  (backend, now hot-reloads on edits) — `GET /health` OK.
- `npm run dev` from `frontend/` → http://localhost:5173/ (200).
- CORS is still open `*`; `LLM_PROVIDER=gemini` (free tier). In the
  frontend's startup gate, enter `http://localhost:8000` as the API base
  URL (remembered in localStorage).
Logs: `…/scratchpad/uvicorn.log`, `…/scratchpad/vite.log`.

**UI change, same session: the user's original query is now echoed back
on the extraction / fill-in-the-blanks screens** so they can see what they
typed while reviewing. Frontend: a "Your query" panel (verdigris left
border, muted text) at the top of `renderFlow()` while `decision === null`
(covers the extraction view, the edit form, and the review gate). Streamlit
`app.py`: `user_query_block()` + a `.cf-userquery` style, rendered right
above "Here's what we understood" (shows on every post-run screen there,
matching that section's own always-on behaviour). `tsc` clean, `app.py`
compiles.

**LLM provider switched to local Ollama, same session.** The
master-prompt-assembly call now runs on a local model instead of the
Gemini free tier (which was 20 req/day — unusable for real traffic).
- `.env`: `LLM_PROVIDER=ollama`, `OLLAMA_MODEL=qwen2.5:7b-instruct`
  (pulled locally, 4.7GB). Provider code default in
  `llm_providers/ollama_provider.py` also bumped `llama3.1` →
  `qwen2.5:7b-instruct`; `.env.example` + `API_KEYS.md` updated to match
  (default provider is now documented as `ollama`).
- **Model choice rationale:** the only live LLM job is a short,
  constraint-heavy rephrase (turn 9 confirmed fields into one sentence,
  omit MISSING/NOT APPLICABLE, invent nothing). `qwen2.5:7b-instruct` —
  strong instruction-following at 7B, non-reasoning (no wasted think
  tokens, unlike the gemini-3.x latency problem from the 2026-08-30
  session), fits the M4/16GB alongside the spaCy+CRF+T5 pipeline.
- **Gated on `data/eval_master_prompt_faithfulness.py`: 0/12 queries had
  an unbacked specific** — every number/%/date in the assembled prompts
  traced back to the query or a field. Outputs are clean business English,
  correctly drop missing fields. Warm call latency ~0.25s (cold ~8s for
  first model load); the 12-query eval ran in 29s total vs Gemini
  managing only 5/12 before hitting its daily cap.
- `blank_suggestions` (the opt-in "unverified guesses" path) also works
  and returns valid JSON — but qwen bent the "never invent a specific
  number" rule there once (`magnitude` → "10%"). Low stakes (opt-in,
  per-field checkbox, labelled unverified) and NOT the strict live path,
  but `SUGGESTION_SYSTEM_PROMPT` could be tightened if it matters.
- Gemini key is still in `.env` (unused now) — swap back any time via
  `LLM_PROVIDER`. Backend restarted so `llm_client`'s `load_dotenv()`
  picked up the change; `/assemble` confirmed `used_llm: true` through
  the API.

**Not committed** — everything above is local, uncommitted, same as the
rest of this 2026-09-03 work.

## Current status (as of 2026-09-03 — Phase D frontend built; cloud hosting shelved; graphify installed)

**Three threads this session.** (1) Tried to host the backend as a free API
and abandoned it: Hugging Face Spaces now needs PRO ($9/mo) for free Docker
CPU hosting; Google Cloud Run got as far as project `choice-forger-api`
(number `311671748612`) but its billing account shows `OPEN: False` and
`gcloud services enable` will keep failing until that's fixed on Google's
side. Decision: run locally for now (`uvicorn api:app --port 8000` +
frontend `npm run dev`), revisit hosting later. The `Dockerfile` in the
repo root is left in place, unused.

**(2) Phase D frontend — built in `frontend/`, driven live end-to-end via
claude-in-chrome, four real bugs found and fixed.** React + Vite + TS +
Tailwind v4; libs zustand / base-ui / clsx-cva / Sonner / motion; design
tokens reused from the Streamlit "field survey instrument" system. See the
`frontend/` folder-map row for what it does. Bugs fixed: base-ui
`Tooltip.Trigger` render-prop nesting was backwards (tooltips never
opened); Tailwind v4 tree-shook the 7 bucket accent colors (moved from
`@theme` to plain `:root`); "New query" didn't clear remembered query text
(added `startNewQuery()`); "Rephrase and try again" reopened the edit form
instead of returning to a pre-filled query box (now calls `resetFlow()`).
Also added auto-reconnect on page load from the remembered API URL.
Verified live: extract → edit/blank-fill → LLM master-prompt gate →
confirmed view with per-bucket-color highlighting + hover tooltips →
reject → rephrase → reject at streak 2 (no bypass button) → New query.
Zero console errors. One branch not exercised live: the no-blanks "Yes,
this is right" path (low risk — same functions as the edited path).

**Not committed:** `frontend/`, `Dockerfile`, `README.md` edits, this
CLAUDE.md. Servers may need restarting in a new terminal.

**(3) Installed `graphifyy` (`uv tool install graphifyy`) + its Claude
Code skill**, registered in `~/.claude/CLAUDE.md` (skill file reviewed,
nothing concerning). Ran `/graphify .` on the whole repo → 450 nodes / 683
edges / 29 communities at `graphify-out/` (not gitignored — decide whether
it should be; cheap to rebuild). Re-run with no changes costs 0 tokens.
Query it with `/graphify query "<question>"`.

## Current status (as of 2026-08-30 — product pivot: LLM builds the master prompt, no answer generation)

**User-driven pivot, written up in full in `TOOLTIP_INTEGRATION_PLAN.md`
(phases A–D).** CHOICE leans fully into its philosophy — make the user
think harder, don't hand them an answer. The extraction pipeline is
untouched (`pipeline.py` / `prompt_synthesis.py` templates unchanged,
models byte-identical to `042fa51`); only the flow from confirm onward
changed.

- **Phase A** (`master_prompt_llm.py`, `llm_client.generate_master_prompt()`,
  `MASTER_PROMPT_SYSTEM_PROMPT`): on confirm, (raw query + confirmed 9
  fields) → one LLM call that rephrases only, never invents, omits
  MISSING/NOT APPLICABLE. Falls back to `render_sentence()` on any error.
  `app.py` confirm is now 2-step: `_prepare_review()` (the call) parks in a
  new `review_prompt` mode → user approves ("✅ Looks right") →
  `_log_and_finish()`. **Removed** from `app.py`: the answer-generation
  block and the 2-reject raw-query bypass — the product generates no answer
  anywhere. `llm_client.generate_output()` now unused.
- **Phase B** (`bucket_client.py`): stdlib `urllib`, 150s timeout,
  certifi SSL. `get_tooltips(master_prompt) -> (ranked, error)` POSTs the
  master prompt to the CHOICE Bucket Matching Engine
  (`BUCKET_API_URL`, default `https://choice-bucket-matching.onrender.com`,
  `POST /tooltip`) → 5–7 "also consider X" nudges. `app.py` confirmed
  screen renders them as a card grid; failure is non-blocking.
- **Phase C** — token/prompt hardening: `max_tokens` plumbed through all
  three providers; `MASTER_PROMPT_MAX_TOKENS = 2048`;
  `thinking_level="minimal"` for this call (gemini-3.x default thinking
  took ~37s for a one-sentence rephrase); one retry; `_prepare_review`
  signature cache so gate↔edit bouncing doesn't re-bill;
  `data/eval_master_prompt_faithfulness.py` (new, repeatable — flags
  invented specifics; first run 5/12 clean, rest hit the Gemini cap).
  `render_sentence()` hardened against intent/object stutter and dangling
  clauses. **Operational finding:** Gemini free tier is 20 req/day with
  6–68s latency — unusable for real traffic; a paid key or different
  provider is a hard prerequisite before sharing the app again.
- **Phase D backend** (`api.py`): FastAPI, thin wrappers — `POST /extract`,
  `/assemble`, `/tooltip`, `/log`, `GET /health`. CORS open (`*`) — lock
  before public. `app.py` (Streamlit) untouched, runs in parallel.

**2026-09-01 continuation — full Streamlit flow click-tested end to end**
(claude-in-chrome). All working: extraction → blank detection → edit form
(⚠️ markers, not-applicable checkboxes) → LLM master prompt (~10s) →
`review_prompt` gate → "Master prompt confirmed" → bucket cards render
(live Render call). Reject → only "Rephrase"; second reject → still only
Rephrase (bypass removal confirmed). One sub-path not clicked: "fix the
fields" from the gate back to the edit form (low risk). Pre-existing T5
repetition bug surfaced on the "kirana stores" example query in the raw
"here's what we understood" view — cosmetic (the LLM assembly cleans it
up); belongs to Known gap 3.

**Still needs from the user:** a non-free LLM key, `GITHUB_TOKEN` on the
hosted app, and pushing the unpushed commits.

## Older status entries — archived

Per-session status logs for 2026-07-29 through 2026-08-16 have been moved to
`CLAUDE_HISTORY.md` to keep this file under the size limit. Read that file only
if you need to trace the reasoning behind a past decision; the Known gaps
section below and the two status entries above carry everything a fresh
session needs. Deeper detail still lives in git history (see commit `db3e52e`).

## Known gaps, in priority order for next session

Condensed 2026-09-03. Fuller per-session detail for these is in
`CLAUDE_HISTORY.md` and git history.

0. **`actor` is the thinnest-trained role; `context` fires unreliably.**
   `actor` is explicit in only 44/120 dataset rows (least of all 9 fields).
   It drops to `missing` or bleeds into `object` on generic team/role
   phrasing ("Tier-1 support team") and — per the 2026-08-12 36-sentence
   adversarial eval — whenever the actor phrase is not sentence-initial
   (after an opening clause, mid-"while X" compound, or as the 2nd of two
   actors). Data/generalization gap, not a missing-feature gap (dep-parse
   features already fed to the CRF). `context` fails in **both** directions:
   misses causal/purpose cues ("because X", "driven by X", "to hit X") 5/5
   times tested, but also dumps an entire plain non-causal sentence into
   `context` while every other field comes back blank. Its trigger behaves
   like "grab leftover subordinate-clause text", not "detect causation".

1. **`measure`, `scope`, `context` still thin** (`scope`: 4 real rows).
   Next sourcing pass should target generic team/role actors, explicit
   measure/KPI phrasing, and causal/purpose context clauses.
   **`measure` subject-position gap (diagnosed 2026-08-06):** the CRF never
   opened a span when the measure noun sat in subject position (after a
   possessive company name, or after "expects"). **Fixed & promoted
   2026-08-08** — sourced 7 rows (`rw_044`-`rw_050`), measure status
   66.67%→73.33%, value 44.44%→55.56%, both generalization-test rows now
   detect it. Introduced the `time` regression that became gap 7. NOTE:
   later retrain attempts (2026-08-10, 2026-08-12) regressed this measure
   fix again on `rw_012`/`rw_044` — it is fragile to any shared-CRF
   capacity shift.

2. ~~Negation-cue phrasing may not exist in real corporate language.~~
   **Corrected 2026-08-05:** it does — real "without X" constraints found
   at Trane, FactSet, EFC, Tesla, Climb Global (`rw_036`, `rw_039`-`rw_042`).
   Still unresolved: whether the model learns it reliably. One training
   example taught the CRF nothing; 5 got detection working but regressed
   other fields in aggregate. Needs more/better-balanced data.

3. **T5 hallucinates `intent` on short/compound spans — worst field in the
   eval** (33.3% correct-or-correctly-missing, 5 outright hallucinations
   across 36 sentences). Hallucinations resolve to a small fixed vocabulary
   ("reduce costs", "increase sales", "grow sales", "move to new
   locations") fired off surface verb-lemma matching (any "cut" → "reduce
   costs") regardless of the sentence's real topic — a gross-margin-% query
   came back "move to new locations". "Canned template, not topic
   understanding." `intent` is already always forced into `mandatory_review`
   (Phase 2 audit) — this argues for keeping that, not loosening it. Also
   reconfirmed the `time: "full-year recruitment"` fabrication verbatim.

4. **Tracked eval set still has no compound/conditional-clause query.**
   The 36-sentence adversarial eval covered this shape but was standalone
   and hand-scored — never added to `data/real_world_eval_holdout.json`
   (no gold JSON built; that file only grows via build→validate→split).

5. **Self-learning correction flywheel** — scoped under Product vision, not
   built. Start with Phase 1 template, not a model; no prompt-synthesis
   training data exists yet.

6. **No actor↔intent pairing across multiple spans.** `detect_possible_
   compound_query()` (in `prompt_synthesis.py`) flags when 2+ of
   `{actor,intent,object}` are independently `multi_span`; `app.py` shows a
   banner + "this is actually more than one decision" checkbox, logged for
   detector calibration. Verified live. **Open by design:** it only detects
   and asks — no auto-split into separate pipeline runs. Its trigger rate
   is bounded by the CRF's own multi-span maturity (gap 0): 6 genuine
   two-actor sentences in the adversarial eval never triggered it because
   the CRF only found one actor span.

7. **`time` under-detects (66.67% status on the 15-row holdout).**
   `rw_012`/`rw_016`/`rw_017` still miss — two CRF span-boundary bugs:
   `magnitude` swallows a leading "by <year>" clause before a dollar
   figure; `object` swallows a leading bare time-adjective ("third quarter
   common stock dividend"). Needs object-role and magnitude-role training
   signal, not measure-role. **2026-08-10:** real examples found
   (`rw_055`/`rw_056`, "declared a third quarter dividend") and a retrain
   genuinely fixed `rw_016` — but it regressed gap 1 (measure
   subject-position), net-negative, **not promoted**. Data kept; retry with
   `rw_055`/`rw_056` isolated from the gap-8 rows.

8. **T5 silently corrupts literal digits in joined multi-value
   `magnitude`.** `rw_027`: gold `["7.0%","10.0%","5.0%"]` → `["7.2%",
   "100%","5.10%"]` at 0.556 confidence (above the 0.4 blank threshold —
   renders as confident fact). Corruption is 100% in `Pipeline.synthesize()`
   (T5), not the CRF; each value normalizes fine alone. Root cause: all 21
   `;`-joined multi-value magnitude training pairs are 2-value; zero 3-way.
   **Partially fixed 2026-08-09 (round 5, promoted)** — one 3-way example
   (`rw_051`): whole-number % 3-way joins now clean, but decimal % joins
   still lose precision and any join touching a **decimal dollar-per-share**
   amount corrupts ($0.50→$50, a 100x error — `rw_016` proves it, 2-way
   included). Also the `eval_on_real_world.py` multi-value scorer was fixed
   2026-08-10 to require every gold element to match. New symptom from the
   adversarial eval: "same value restated in two units" produces a
   truncated/malformed list-repr string. **Open:** source more diverse
   3-way/4-way magnitude examples (decimal %, dollar amounts, unit
   restatements), isolated from gap-7 rows.

9. **`time` over-triggers on passive "will be finalized by <org>".** The
   real actor lands in `time` (source span "by the HR team"), `actor` comes
   back `missing`, the real time value vanishes. Cause: "by <X>" is a
   strong CRF deadline signal over-generalized to any "by <noun phrase>".
   Actively misleading (an actor name under a Deadline label). **2026-08-12:**
   root-caused (29/29 "by <X>"→time training examples are date-shaped),
   sourced `rw_057`-`rw_061`, retrained — partial fix but regressed
   `object` on 4 rows (net value 60.87%→52.17%), **not promoted**. Retry
   with those rows' `object` annotations removed (actor-only).

10. **Silent multi-value drop also hits `constraints`** (not just
    magnitude). Two joined constraint clauses → only the first survives;
    the second never appears. **Fixed 2026-08-12, committed `0cf0fb1`** —
    `build_fields()` now computes `dropped_values` (flagged_for_review +
    guard_note mentions a drop) and folds it into `needs_review`, reusing
    the ⚠️ UI mechanism. Pure code, no retrain, verified.

11. **Hosted-app corrections were silently discarded (2026-08-04 →
    2026-08-16) — persistence bug, now fixed.** Streamlit Community Cloud
    runs in an ephemeral container; `correction_log.py`'s plain local
    `open(...,"a")` write was wiped on every redeploy and never reached the
    repo. Every real-user correction in that window is unrecoverable.
    **Fixed 2026-08-16:** `correction_log.py` writes each correction to
    `data/corrections_log.jsonl` via the GitHub Contents API (GET SHA →
    append line → PUT), authed via a fine-grained `GITHUB_TOKEN` (setup in
    `README.md`); 409-race retry x2; local-append fallback with a visible UI
    warning if the token is unset. Verified live against the real repo.
    Reclassifies the Phase 6 gate's condition 2 — it was a data-loss bug,
    not a traffic shortfall; it needs ~15-20 retained real post-fix
    corrections. **Still outstanding:** the `GITHUB_TOKEN` secret must be
    created by the user and added to the hosted deployment before the fix
    is live there.

Full detail and reasoning for all of the above lives in git history — see
commit `db3e52e`'s message specifically, and `CLAUDE_HISTORY.md`.
