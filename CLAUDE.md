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
|---|---|
| `choice_forge_dataset_full_100_v2.json` | Original 100-row dataset. **LLM-generated, not real text** (confirmed by user). Treat as immutable — don't hand-edit; combine via new files instead. |
| `choice_forge_dataset_combined_120.json` | Current training dataset: original 100 + 20 real rows. Regenerate via `data/build_combined_dataset.py` (don't hand-build with a one-off script — that's how this file was first created and it's not reproducible). |
| `role_tagger.joblib`, `value_synthesizer/` | Trained model artifacts. Always regenerate via the retrain commands in `README.md`, never hand-edit. |
| `data/real_world_eval_holdout.json` | **Permanent, frozen real-world benchmark. NEVER train on this file.** It's the only trustworthy way this project can measure itself against real (non-synthetic) text. May only grow via deliberate, validated curation — never silently regenerated. |
| `data/real_world_training_augment.json` | Real, source-verified rows approved for training. Grows over time as more batches are sourced. |
| `data/build_real_world_pilot.py` | Template for constructing new real-sourced, hand-labeled rows (with `_source_url` provenance). Copy/extend this pattern for new batches rather than writing raw JSON by hand. |
| `data/validate_real_world_pilot.py` | Checks new rows against the *actual* `row_to_bio` training function: source_text substring correctness + no cross-role span overlap. Run this on any new batch before trusting it. |
| `data/split_real_world_pilot.py` | Stratified eval/train split logic (rare roles get spread across both sets). |
| `data/eval_on_real_world.py` | The only end-to-end, real-world scoring harness. Run after every retrain. |
| `data/real_world_eval_report.json` | Latest eval run's per-row, per-field detail. Regenerated each run — not hand-edited. |
| `Doc/` | Pre-existing human-reference explainer PDFs (one per layer). Not auto-generated, don't touch without reason. |
| `app.py` | Streamlit stakeholder UI. Also hosts the Phase 3 fill-in-blank/confirm-reject "Master Prompt" section (calls `prompt_synthesis.py` + `correction_log.py`). |
| `prompt_synthesis.py` | Phase 1 of the Product vision below: deterministic-template master-prompt synthesis from a `Pipeline.run()` result. `render_sentence()` (the sentence-assembly core) is shared with `app.py`'s confirm/reject re-render step. |
| `correction_log.py` | Phase 3: appends one JSON object per confirm/reject decision from `app.py` to `data/corrections_log.jsonl`. This is the training data Phase 5 will retrain the prompt-synthesis model on. |
| `data/corrections_log.jsonl` | Append-only log of every confirm/reject decision (written by `correction_log.py`). Versioned like `data/seq2seq_pairs.jsonl` — not gitignored, not hand-edited. |
| `llm_client.py` | Phase 4: thin wrapper around the Anthropic API (`client.messages.create`, model `claude-opus-5`). Sends a confirmed master prompt, returns Claude's answer. Reads `ANTHROPIC_API_KEY` from the environment via the SDK's default resolution — never hardcode a key here. |

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
  CHOICE does not judge whether the user's inputs are *true* — only
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
     trade-offs/risks/dependencies/missing evidence, explain *why* one
     option looks stronger under the *stated* assumptions.

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
4. **Never assume a value for an empty or low-confidence field.** Any
   field the pipeline didn't fill, or filled with low confidence, becomes
   an explicit blank in the master prompt text rather than a guess. This
   reuses the pipeline's existing confidence signals (e.g.
   `MIN_JOIN_OPEN_CONFIDENCE` in `pipeline.py`) as the "blank this field"
   trigger, gated by the Phase 2 calibration audit (done — see Current
   status).
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
  (pattern matching — explicitly *not* the CRF field-extractor, a separate
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
  most for *this* decision — driven by whichever buckets the classifier
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
  a deterministic *template*, not a trained model. There is no dataset yet
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
  both measures how often the system gets it right *and* is the training
  data needed for Phase 5 — do not train a prompt-synthesis model before
  this data exists. **Built — see Current status, 2026-08-03 session.**
- **Phase 4** — wire the final LLM API call (default to Claude via the
  Anthropic API for this) on the confirmed master prompt. **Built — see
  Current status, 2026-08-04 session.**
- **Phase 5** (later) — once accept/reject + fill logs accumulate, train
  the real prompt-synthesis model on them, replacing the Phase 1 template.
  Gate any new version against a frozen holdout, the same way model
  promotion already works for the extraction layer.
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

## Current status (as of 2026-08-04 — not-applicable fields + Phase 4 build session)

**2026-08-04 session:** started from a discussion of real gaps in the Phase
3 UI: a blank field collapses "the pipeline failed to extract this" and
"this genuinely doesn't apply to the query" (e.g. no constraint was ever
stated) into one identical placeholder, which also meant scoring had no way
to exclude inapplicable fields from a denominator. Discussed and agreed the
fix, then built it, then built Phase 4.

- **Checked actual repo state before doing anything** — `CLAUDE.md`'s
  "still on branch, not yet merged" note from the 2026-08-03 session was
  stale: `git branch --merged main` showed `phase-3-master-prompt-ui` was
  already merged into `main` (just not pushed to `origin/main`, which was 7
  commits behind). No merge needed this session, just eventually a push.
- **Added a "not applicable" state**, distinct from `blank`, for the 5
  trailing-clause roles where a query can legitimately never mention one
  (`scope`, `magnitude`, `time`, `constraints`, `context`). `actor`/`intent`/
  `object`/`measure` stay fill-or-blank only — they're structural to the
  sentence (subject/verb/target), not droppable clauses.
  `prompt_synthesis.py`: added `NOT_APPLICABLE_ELIGIBLE_ROLES`, a
  `not_applicable` key on every field (default `False`, never set by the
  pipeline — only the user can know this), and rewrote `render_sentence()`
  to drop each not-applicable clause entirely instead of rendering its
  blank placeholder — verified byte-identical output to the pre-change
  version when nothing is marked not-applicable. `app.py`: a "Not
  applicable" checkbox next to each eligible blank field; at submit time,
  a checked box forces `blank=True, not_applicable=True` for that field
  regardless of what (if anything) was typed into it.
  `correction_log.py`'s entries (via `app.py`'s `log_fields`) now carry
  `not_applicable` per field, distinct from `blank` — this is the input
  a future scoring pass needs to divide by "applicable fields" instead of
  always 9, and it's now available going forward (not retrofitted onto
  old log entries).
- **Verified end-to-end in a running streamlit session**: ran a real query,
  checked `scope`/`magnitude`/`context` as not-applicable and left `time`/
  `constraints` filled, confirmed, and got a clean sentence with the three
  not-applicable clauses cleanly absent (no dangling "while subject to this
  constraint: [blank]" text). Checked `data/corrections_log.jsonl` — the
  three fields logged `blank: true, not_applicable: true, final_value:
  null`, correctly distinguished from the filled fields. Kept this as
  verification data in the log, same convention as the prior phase-3
  session.
- **Built Phase 4**: new `llm_client.py` sends a confirmed master prompt to
  Claude (`claude-opus-5` via the Anthropic API) and returns the answer.
  Reads `ANTHROPIC_API_KEY` from the environment via the SDK's default
  client resolution — never hardcoded. Added a "Generate Output" section to
  `app.py`, shown only once a query is confirmed (tracked in
  `st.session_state.last_decision`, reset on every new Run so it can't
  leak across queries), with a "Send to Claude" button. Verified in a
  running streamlit session with no API key present: confirmed a query,
  the section appeared correctly, and clicking through produced a clean
  caught `AuthenticationError` displayed in the UI (not a crash) pointing
  at the missing key — confirms the wiring is correct up to the network
  call itself, which needs a real key to verify further. Added `anthropic`
  to `requirements.txt` and documented the env var in `README.md`.
- **Push blocked, not attempted further**: `git push origin main` failed —
  the `alethiaworks` deploy key (`~/.ssh/id_ed25519_alethiaworks`) is
  passphrase-protected and the local ssh-agent had no identities loaded.
  Did not attempt to enter or work around the passphrase (that's
  credential handling). Commits are made locally (`cd34a77`, `b5bc360`);
  pushing to `origin/main` is left for the user to do themselves
  (`ssh-add ~/.ssh/id_ed25519_alethiaworks` then `git push`).

## Current status (as of 2026-08-03 — Phase 1 + Phase 3 build session)

**2026-08-03 session:** resumed from the 2026-08-02 pause. First, caught
up git state left over from the two prior planning-only sessions —
committed `CLAUDE.md`'s 2026-08-01/2026-08-02 doc edits and the untracked
`Doc/` explainer PDFs (`93d2b62`). Then built Phase 1: `prompt_synthesis.py`,
a new module (kept separate from `pipeline.py`, which stays pure
extraction).

- `synthesize_master_prompt(pipeline_result)` assembles one flowing
  "Objective Statement" sentence from the 9 extraction fields, following
  the Product vision's Step 1 item 3 (actor/intent/measure-or-object
  fused subject+verb+target, then magnitude/time/scope clauses, then
  constraints/context as trailing clauses).
- Blank-insertion reuses `pipeline.MIN_JOIN_OPEN_CONFIDENCE` (0.4) exactly
  as the Phase 2 audit decision specified: a field is blanked (shown as a
  `[role — please fill in]` placeholder in the prompt text) whenever
  `status == "missing"` or `confidence < 0.4`. `intent` is additionally
  **always** marked `needs_review` even when non-blank, per the Phase 2
  finding that confidence doesn't separate right/wrong for `intent`.
- Returns structured `{master_prompt, fields, blanks, mandatory_review}` —
  the `blanks`/`mandatory_review` lists are what Phase 3's fill-in/confirm
  UI will consume; not wired into `app.py` yet.
- `time`/`magnitude` values from T5 often already carry their own
  preposition ("within the next sprint", "by 40%"); a fixed template
  prefix would have doubled up ("within within..."). Added
  `_prefixed_clause()` to skip the template's own prefix when the value
  already opens with a known preposition word — verified against several
  hand-run queries.
- Manually tested against all 7 example queries from `app.py`. Confirms
  the design works as intended (confidence-driven blanking correctly
  fires, e.g. `scope` at 0.391 confidence blanked as expected) but also
  surfaces — faithfully, not incorrectly — existing pipeline noise
  documented in Known gaps #0/#3 (e.g. `intent` sometimes bundles its own
  object, "increase market share" + a separately-extracted `object` field
  producing a redundant-sounding sentence). Deliberately did not add
  fusion heuristics to paper over this: `intent` is already
  `mandatory_review`, and the whole design principle here is "surface
  uncertainty, let the human fix it" rather than guessing grammar the
  pipeline output doesn't actually support.
- **Found and fixed a small unrelated bug** in `polarity_guard.py`
  (Layer 4) while test-driving queries: `VERB_BASE`'s fallback stemmer did
  a naive `verb[:-3]` strip for gerunds not in its lookup table, so
  doubled-consonant verbs came out wrong (`"letting"` → `"lett"`,
  `"cutting"` → `"cutt"`). Added `_degeminate()` to undo the doubled
  consonant when the fallback fires. Re-ran
  `python3 data/eval_on_real_world.py` after the fix — frozen holdout
  score unchanged (77.8% / 63.0% / 90% actor), confirming no regression.
- **Multi-actor/multi-object handling, addressed same session (not
  deferred):** discussed what happens when a field legitimately has more
  than one value (e.g. two actors) or the input is long/compound (~300+
  chars). Two separate findings: (1) there's no length cutoff anywhere in
  the pipeline — spaCy/CRF process the full token sequence and T5 only
  normalizes short per-field spans, so the real risk on long/compound
  input is quality (known gaps #3/#4), not truncation; (2) `pipeline.py`
  already collected all surviving spans per role (`decode_bio_multi`) but
  silently `"; "`-joined multiples into one string before Phase 1 ever saw
  it, and `prompt_synthesis.py`'s template has exactly one slot per field
  — so "CEO; Regional Sales Director" would've rendered as a single
  awkward value with no signal that it's actually plural. Decided to fix
  immediately rather than defer: the surviving-multi-span info already
  existed in `Pipeline.run()`, discarding it and re-deriving it later would
  cost the same effort twice for no benefit (unlike Phases 6-8, which are
  genuinely deferred because they're large and still unscoped). Exposed it
  as a new `multi_span: bool` field on every role in `Pipeline.run()`'s
  output (`pipeline.py`), and `prompt_synthesis.py` now includes
  `multi_span` in `needs_review` the same way `intent` always is — a
  multi-actor/object field surfaces for human review instead of silently
  reading as one fused value. Re-ran the eval after — unchanged (purely
  additive field, no scoring-path change).
- **Phase 3 built, same session:** extracted `render_sentence(fields)` out
  of `prompt_synthesis.py`'s `synthesize_master_prompt()` (pure refactor,
  no behavior change) so the sentence-assembly logic — the
  `_prefixed_clause` preposition-skip, measure/object fusion — can be
  reused both for the pipeline-extracted prompt and for re-rendering after
  user edits. Added `correction_log.py` (append-only JSONL writer, same
  convention as `data/seq2seq_pairs.jsonl`). Added a "Master Prompt"
  section to `app.py` below the existing per-field diagnostic grid (that
  grid is unchanged, stays as the raw-extraction view): shows the
  assembled sentence, then an `st.form` with one editable text input per
  role (all 9 editable, not just blank/flagged ones — a correction on a
  field the pipeline was confident about is valuable signal too), blank
  fields shown via `placeholder=` rather than pre-filled `value=`, and
  Confirm/Reject submit buttons. Widget keys are suffixed with a
  `run_id` counter (bumped on every Run click) so a second query's form
  doesn't inherit the first query's edited text — Streamlit only honors a
  widget's `value=` on first creation of a given key, not on reruns. On
  submit, resolves each field's final text (edited value if the user typed
  something, else the original), explicitly flips `blank` to `False` for
  edited fields so `render_sentence()`'s preposition-skip logic applies
  correctly to user-typed text (not doing this would double up
  prepositions like "within within Q4" on a filled-in blank), re-renders
  the sentence via `render_sentence()`, and logs one JSON entry via
  `correction_log.log_correction()` with the original per-field pipeline
  output, the resolved final value, whether it was user-edited, both
  prompt versions, and the confirm/reject decision (+ reason on reject).
  **Provenance note:** this was actually built by a cloud Ultraplan session
  (planned in-session, then handed off), which timed out waiting for
  approval after 90 minutes and was reported as "failed" — but it had
  already committed the work to a new branch, `phase-3-master-prompt-ui`
  (commit `257ec05`), on top of the Phase 1 work. Treated that as
  unverified until independently checked: reviewed the full diff against
  the approved plan (matched — clean `render_sentence()` refactor, no
  behavior change; `correction_log.py` as specified), reran the
  `prompt_synthesis.py` CLI smoke query (byte-identical output pre/post
  refactor), and drove the actual running `streamlit run app.py` in a real
  browser end-to-end: filled blanks + edited fields + Confirm (matches the
  two pre-existing log entries in `data/corrections_log.jsonl` from the
  cloud session's own testing), a fresh Reject with a typed reason
  (blank fields correctly logged as `final_value: null`, edited fields
  correct, reason captured), and running a second, different query to
  confirm the form doesn't inherit the first query's edited text (the
  `run_id` key-namespacing fix works as designed). All confirmed working.
  **Still on the `phase-3-master-prompt-ui` branch, not yet merged to
  `main`** — that's the next step, pending user go-ahead.

## Previous status (as of 2026-08-02 — feasibility/timeline discussion, paused)

**2026-08-02 session:** re-read `Knowledge_Bucket_Library.pdf` for a
second pass (confirmed it matched what was already folded into Product
vision on 2026-08-01 — no doc changes needed from that re-read). Then
discussed solo feasibility/timeline for the full Phase 1-8 build order.
**No code changed this session.** Conclusions, for next session to pick
up from:

- All 8 phases are technically feasible solo — nothing in the spec needs
  exotic tech (Intent Classifier is pattern-matching per the source doc,
  not ML; graph UI is a solved problem via existing libraries like
  react-flow/cytoscape/vis.js; the LLM call is a thin API wrapper). The
  constraint is bandwidth/time, not feasibility.
- Rough solo, part-time-pace estimate for an MVP through Phase 8:
  **~3-5 months** (or ~6-10 weeks if worked closer to full-time). Phase 5
  is additionally gated on calendar time to accumulate 20-30+ logged
  corrections, not just work-hours.
- **Phase 8 (Knowledge Graph) is the long pole** — node/edge construction,
  a real interactive graph UI, and edit-triggers-resummarize logic is
  3-6+ weeks alone and easy to let scope-creep (partial views, node
  editing, relationship editing all in the spec).
- **Recommendation (not yet acted on):** don't march through all 8 phases
  serially. Ship Phases 1-4 as a usable, demoable v1 first (objective in →
  confirmed master prompt → LLM output out) before starting Phase 8. Scope
  a bare-bones first cut of the Knowledge Graph rather than building the
  full editable-graph spec (partial views + add/remove nodes + edit
  relationships + resummarize) in one pass.
- Session paused here by user request ("we will continue with this later
  in a while") — **Phase 1 (deterministic template master-prompt
  synthesis) is still the agreed next actual build step**, unstarted.

## Previous status (as of 2026-08-01 — framework-scope digest session)

**2026-08-01 session:** user shared two external planning docs (see
Product vision section above for exact paths) laying out the full CHOICE
framework philosophy (reasoning integrity, not predictive accuracy; the
3-step Clarify/Structure/Guide flow) and a large new scope item — the
Intent Classifier + ~60-entry Knowledge Bucket Library + Knowledge Graph
persistence. Merged this into the Product vision section above (Phases
6-8, all unscoped/not started). **No code changed this session** — this
was a documentation/alignment pass only. Agreed with user: keep building
toward Phase 1 (deterministic template master-prompt synthesis) next,
unaffected by the new scope discovered today.

## Previous status (as of 2026-07-29 — planning + calibration audit session)

**2026-07-29 session:** agreed the Product vision above (full workflow),
then ran the Phase 2 confidence-calibration audit against
`data/real_world_eval_report.json` (10-row frozen holdout) before writing
any Phase 1 code. Result, split by field:

- **Every field except `intent`**: 28/28 non-missing predictions were
  correct, regardless of confidence (down to 0.256). Confidence barely
  matters here — once the pipeline commits to a non-missing value for
  actor/object/scope/measure/magnitude/time/constraints/context, it has
  been right every time in this holdout.
- **`intent` only**: 3 of 4 non-missing predictions were wrong, and the
  wrong ones spanned confidence 0.184–0.543 while the one correct one sat
  at 0.358 — right in the middle of the wrong range. **Confidence does not
  separate right from wrong for `intent`.** This is the T5-hallucination
  gap (old gap #3) showing up exactly where expected.
- **Decision for Phase 1:** use per-field confidence thresholds for
  blanking (safe, since non-intent fields are reliable), but **do not
  trust any threshold for `intent`** — instead always surface `intent` in
  the master prompt as a mandatory user-reviewed/editable field regardless
  of confidence, until the underlying T5 hallucination is fixed at the
  model level.
- **Caveat:** n=10 rows / 32 non-missing field predictions / only 4 for
  intent. Directionally strong (100% vs 25% correct is a stark gap) but
  statistically thin — worth re-checking once the eval holdout grows.

Also this session: hand-tested the live pipeline on fresh (non-eval-set)
queries. Confirmed the frozen eval score reproduces exactly (no drift).
Found the `README.md` worked-example output is now stale relative to the
current retrained model (not regenerated per user instruction — flagged,
not fixed). Redesigned `app.py`'s UI (card-based field layout, confidence
badges/progress bars, example query pills, download-JSON button) and
updated its footer caption to state the real current eval numbers instead
of the old "100-row v1" description.

Previous session (2026-07-27, commit `db3e52e` + `e0b5782`):

**Not yet ready to ship for unreviewed/autonomous use.** Meaningfully
improved this session with measured before/after numbers, but still needs
human review of every field until the gaps below close further.

What happened in the 2026-07-27 session:

1. **Found real failures via adversarial testing.** Two hand-written
   compound/negated queries exposed silent field-dropping (actor, scope,
   measure often missing even when clearly present in text) and a worse
   failure: a decode-time bug where a low-confidence spurious span got
   averaged with a confident one, producing plausible-looking *wrong* output
   at misleadingly medium confidence (e.g. intent resolving to `"reduce;
   creep above where it was last quarter"` at confidence 0.55).

2. **Root-caused and fixed the decode bug** in `pipeline.py`
   (`decode_bio_multi` / `Pipeline.run`). Was: mean-of-all-tokens confidence,
   unconditional "; "-join of any same-role spans. Now: tracks each span's
   own B-tag "opening confidence" separately, drops spans below
   `MIN_JOIN_OPEN_CONFIDENCE` (0.4) when multiple spans exist for one role,
   uses min (not mean) across surviving spans, flags when it drops
   something. Verified fixed against the original bug query. **Caveat:**
   this only bites on compound/conditional queries ("do X unless Y") — the
   real eval set doesn't contain that sentence shape yet, so the fix is
   verified but doesn't move the tracked eval number below.

3. **Built a real-data pipeline from scratch** (project had zero real ground
   truth before this). Sourced 30 hand-labeled rows from real public
   earnings-call transcripts and shareholder letters (Target, PNC, FIS,
   Wells Fargo, D.R. Horton, Citizens Financial, Buffer), each with a
   `_source_url` and independently fact-checked against the live source.

4. **Split into a permanent eval holdout (10 rows) + training augmentation
   (20 rows)** — see folder map above for exact files.

5. **Retrained** CRF + T5 on `choice_forge_dataset_combined_120.json` (100
   synthetic + 20 real). Measured effect on the frozen real eval set:

   | metric | before | after |
   |---|---|---|
   | overall status accuracy | 55.6% | 77.8% |
   | overall value accuracy | 19.6% | 63.0% |
   | actor detection accuracy | 10% | 90% |

   This confirms the "needs real data" hypothesis decisively, and shows the
   fix is efficient — 20 real rows moved the number a lot.

## Known gaps, in priority order for next session

0. **`actor` is actually the thinnest-trained role, not previously flagged.**
   Discovered 2026-07-30 via a Gemini-generated adversarial batch (5 fresh
   queries, Gemini wrote both the expected answers and the scoring — treat
   as directional stress-test signal, not the same evidentiary weight as
   the frozen `real_world_eval_holdout`). `actor` dropped to `missing` and
   bled into `object` on 2/5 novel queries with generic role/team phrasing
   ("Tier-1 support team", "field sales representatives") despite similar
   patterns existing in training data. Checked `choice_forge_dataset_combined_120.json`:
   `actor` is explicit in only 44/120 rows — the least of all 9 fields
   (vs. measure 55, context 55). Checked `train_crf.py`'s `token_features`:
   dependency-parse features (`dep`, `head_dep`, `head_lemma`) are already
   fed to the CRF, so this is a data-volume/generalization gap, not a
   missing-feature gap — same lesson as the 07-27 retrain. Also from this
   same batch: `measure` was missing on 5/5 (consistent with, but starker
   than, its known 28.6% value accuracy); `context` specifically misses
   causal ("because X") and purpose ("to hit X") clauses — a concrete
   target for the next real-data sourcing pass, not just "context is thin."
1. **`measure`, `scope`, `context` roles still thin**, even in the real
   30-row batch (scope: 4 rows total). Need more real sourcing targeted
   specifically at these. Per item 0 above, `actor` belongs on this list
   too now, and the next sourcing pass should specifically target:
   generic team/role-phrased actors (not just company names), explicit
   measure/KPI phrasing, and causal/purpose context clauses.
2. **Negation-cue phrasing may not exist in real corporate language.**
   Checked 7 public companies' earnings calls specifically hunting for
   "without increasing X" style constraints — found zero. Executives phrase
   constraints as "subject to X", "while maintaining Y" instead. This means
   the negation pattern `polarity_guard.py` targets may be more an artifact
   of the original LLM-generated dataset's phrasing than of real usage — or
   it just needs a different real source (internal informal business
   asks / Slack-style requests, not formal earnings calls). Unresolved.
3. **T5 still hallucinates on short or compound source spans** even
   post-retrain (e.g. bare "increase" -> wrong object "sales"; a query with
   two legitimate actions in one sentence produces a fused, partly
   hallucinated intent value). May be a T5-small capacity ceiling rather
   than a pure data-volume problem — not yet disentangled from the data gap.
4. **Eval set has no compound/conditional-clause query yet**, so the
   join-coherence fix (item 2 above) is verified on a hand-written example
   but not reflected in the tracked eval score.
5. **Longer-term, agreed direction: self-learning correction flywheel.**
   Now scoped in full under "Product vision" above — capture stakeholder
   corrections via `app.py`'s fill-in-blank/confirm-reject flow, prioritize
   review by model confidence (active learning), periodically retrain and
   gate every new model against a frozen real eval set before promoting it.
   Not yet built. Start with Phase 1 (template-based prompt synthesis) from
   the Product vision section, not with the model — there's no training
   data for the prompt-synthesis model yet.

Full detail and reasoning for all of the above lives in git history — see
commit `db3e52e`'s message specifically.
