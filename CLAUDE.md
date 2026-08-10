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
| `llm_client.py` | Phase 4: provider-agnostic router. Reads `LLM_PROVIDER` and dispatches to the matching module in `llm_providers/`. `app.py`/`blank_suggestions.py` only ever call `llm_client.generate_output()` / `generate_suggestions()` -- never a provider SDK directly. |
| `llm_providers/` | One module per LLM provider (`anthropic_provider.py`, `gemini_provider.py`, `ollama_provider.py`), each a single `generate(prompt, system_prompt=SYSTEM_PROMPT) -> str` function reading its own key/model from the environment. Adding a provider = one new module + one registry line in `llm_client.py`. Never hardcode a key in any of these. |
| `blank_suggestions.py` | Optional, explicitly opt-in extension to Phase 3: on request (`app.py`'s "Suggest values for blanks" button), asks the configured LLM for plausible-but-unverified values for currently-blank master-prompt fields, using `SUGGESTION_SYSTEM_PROMPT` (`llm_providers/_shared.py`) -- a different, stricter system prompt than Phase 4's answer-generation call. Never auto-applied: the user must tick a box per field to pull a suggestion into the form, same as typing it themselves. Exists specifically to answer 2026-08-06 stakeholder feedback that wanted invented actor/context/constraint text folded in as if it were extracted fact, without breaking the "never assume a value for an empty field" rule below -- see that day's Current-status entry for the full reasoning. |
| `API_KEYS.md` | The one file to read to switch providers, see every env var per provider, or add a new one. Security rules for keys live here too. |
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
  real-data sourcing work in the meantime — only the *start* of Phase 6.
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

## Current status (as of 2026-08-10 — eval scoring fix + gap 7/8 sourcing pass, not promoted)

**New session, user request: pick up from where the 2026-08-09 session left
off and fix the two open Known gaps (7, 8) without further check-ins where
possible.** Confirmed repo state matched CLAUDE.md exactly before starting
(clean, at `e41c7b1`, 4 commits ahead of origin — same as last documented).

- **Fixed a real, previously-flagged scoring bug in
  `data/eval_on_real_world.py` before doing anything else**, since it
  directly affects how any further retrain gets gated. The old
  `loose_value_match` scored a multi-value field correct if ANY single
  gold element substring-matched anywhere in the whole joined prediction
  string — so a 3-way join with 2 of 3 values wrong (exactly `rw_027`,
  the row Known gap 8 was diagnosed from) still scored 100% correct.
  Extracted `prompt_synthesis.humanize_value()`'s list-parsing logic into
  a new shared `parse_value_items()` (pure refactor, verified
  byte-identical `humanize_value()` output on 7 hand-picked edge cases
  before wiring it in), and added `value_matches_gold()` to
  `eval_on_real_world.py`: for multi-value gold, every gold element must
  now match some individually-parsed predicted item, not just the whole
  string once.
- **Re-ran the eval with the fixed scorer against the live (round 5)
  model to get an honest current baseline before any retraining.**
  Real, previously-hidden numbers: **status 83.70% (unchanged), value
  61.19% (down from the previously-reported 70.15%, which was inflated by
  the scoring bug)**. Directly confirmed via the raw predictions this
  wasn't a regression, just honesty: `rw_027` (magnitude, 2 of 3 values
  wrong) and a **newly surfaced case, `rw_016`** (magnitude
  `['11%','$0.50 per share']` → predicted `['11%','$50 per share']`, a
  100x digit-corruption error at 0.465 confidence, above the blank
  threshold) both flipped from incorrectly-scored-correct to
  correctly-scored-wrong.
- **This changed the understanding of Known gap 8 significantly.**
  `rw_016`'s corruption proved the bug isn't limited to 3-way percentage
  joins losing decimal precision (the 2026-08-09 characterization) — it's
  a broader T5 failure on **decimal dollar-per-share amounts inside any
  joined multi-value magnitude**, including plain 2-way joins. Confirmed
  directly via `pipe.synthesize('magnitude', ...)` calls: `$0.50` alone
  normalizes perfectly (0.97 confidence), but the moment it's joined with
  another value it corrupts (`$0.50`→`$50`, `$0.75`→garbled `"$100,
  '$100,'"`, `$1.25`→`$1,25`), all at 0.85-0.98 confidence — confidently
  wrong, not a rare hallucination. Checked training data: the one
  existing 2-way training pair with this exact shape (`"18%; $2 per
  share"`) uses a whole dollar amount, not a decimal — every one of the
  21 pre-existing 2-way-join pairs does. Zero training coverage for a
  sub-dollar-decimal value inside a join, same root cause as the 3-way
  gap, just a wider blast radius than previously known.
- **Sourced 5 new real, source-verified rows** (`rw_052`-`rw_056`) via
  `data/build_real_world_pilot.py`, validated clean, split (all 5
  train-only — `rw_016`, already frozen in the eval holdout, is the
  generalization test, so no new eval row was needed): 3 targeting gap 8
  (Equinox Gold, Alpine Income Property Trust, Ares Management — real
  dividend-increase quotes chosen for 3 different decimal-precision
  shapes: single-digit cents, two-digit cents + decimal percent, >$1
  decimal + an inexact "over X%" qualifier) and 2 targeting gap 7
  (Imperial Oil, Employers Holdings — both real "declared a third
  quarter dividend" quotes, the exact bare-time-adjective-before-object
  pattern the 2026-08-09 session searched 8 queries and 3 transcripts for
  and came up empty on). Confirmed via `git diff` the frozen holdout
  stayed byte-identical through the split. Rebuilt
  `choice_forge_dataset_combined_141.json` (100 + 41).
- **Retrained CRF + T5 on the full 141-row set, gated against the
  restored round-5 backup using the fixed scorer — failed the gate, not
  promoted.** Backed up round 5's artifacts first, per the standing
  pattern. Result: **status 83.70%→80.00%, value 61.19%→56.72%** — net
  negative on both tracked metrics. Diagnosed why via a full row-by-row
  diff against the round-5-with-fixed-scorer report (not just the
  aggregate number): the retrain delivered two real, verified fixes
  (`rw_016` magnitude now matches gold exactly — `$0.50` no longer
  corrupts; `rw_016` time now correctly detects `"third quarter"`) but at
  the cost of **regressing an earlier, already-gated fix** — Known gap 1
  (measure subject-position detection, fixed and promoted 2026-08-08) —
  on both `rw_012` and `rw_044` (`rw_044` is literally the row built
  specifically to test that fix): `"free cash flow"` now gets mislabeled
  `object` instead of `measure` on both. Also lost `rw_029`'s
  actor/scope (both previously correct, now missing entirely) and
  `rw_034`'s multi-span scope detection (3-item list → 1 item). Same
  "one shared CRF, reinforcing one pattern shifts decision boundaries
  elsewhere" mechanism this project has hit repeatedly (2026-08-05
  negation-cue rounds, 2026-08-08 measure/time rounds) — confirmed, not
  assumed, by direct comparison.
- **Decision: did not promote.** Restored round 5's `role_tagger.joblib`
  / `value_synthesizer/model.safetensors` from the backup and verified
  via diff the restored eval report is byte-identical to the
  pre-retrain baseline. Round 6's artifacts and eval report are saved to
  the session scratchpad (not the repo) in case a future session wants
  to pick this up. **Known reproducibility gap, same shape as
  2026-08-05's, flagged explicitly rather than hidden:** the dataset
  files on disk (`choice_forge_dataset_combined_141.json`,
  `data/real_world_training_augment.json`, 41 rows) now reflect all 5
  new sourced rows, but the **live model artifacts are still round 5's**
  (trained on the 136-row set). The data is real, validated, and worth
  keeping regardless of this retrain's outcome; whoever retrains next
  should do so from the current 141-row combined file.
- **Recommended next step for gap 7/8, left for a future session rather
  than force-fixed here:** don't retrain on all 5 new rows together again
  — isolate which addition (gap 7's dividend-declaration rows, gap 8's
  decimal-magnitude rows, or just general capacity redistribution from
  +5 rows) actually causes the measure/object confusion, most likely by
  retraining on each sub-batch separately against the same holdout, or by
  adding 1-2 more reinforcing `"expects <measure>"` examples alongside
  next time to counteract the shift the same way earlier sessions
  countered similar regressions.
- **Deliberately left untouched, per CLAUDE.md's own standing note that
  these are decision points for the user, not something to resolve
  unilaterally:** the missing automated test suite, and the Phase 6
  gate's condition 2 (real external usage — `data/corrections_log.jsonl`
  still shows zero entries since 2026-08-07).
- **Not committed yet** — the scoring fix (`prompt_synthesis.py`,
  `data/eval_on_real_world.py`), the 5 new sourced rows (all of
  `data/build_real_world_pilot.py`'s downstream files), and this
  CLAUDE.md update are all still local, uncommitted changes, pending a
  go-ahead. `role_tagger.joblib`/`value_synthesizer/` are unchanged from
  the last commit (round 5 restored to byte-identical), so nothing model-
  related needs re-committing.

## Current status (as of 2026-08-09 — senior-dev/architect plan audit)

**New session, user request: evaluate actual product state against the
agreed plan and expected outcomes, flag any needed plan changes, proceed
on anything low-risk without waiting for sign-off.** Pulled real numbers
rather than trusting the prose status entries above at face value.

- **Phase 6 gate, condition 2, checked directly: still not met, and not
  trending toward met.** `data/corrections_log.jsonl` has exactly 18
  entries, all dated 2026-08-03 through 2026-08-07, all traceable to this
  project's own documented live-testing sessions above — zero real
  external usage. Two full sessions of work have happened since
  (2026-08-08's two sessions) with no new entries. Condition 1 (targeted
  sourcing + measured improvement) is genuinely met, repeatedly. Condition
  2 is not, and nothing in the current plan actually drives it forward —
  building more extraction-layer fixes doesn't get anyone outside this
  session using the app. **This is a decision point for the user, not
  something to resolve unilaterally**: either get real usage before
  Phase 6 (share the Streamlit app with even one other person), or
  consciously revise what "real usage" means for a single-operator
  project instead of leaving the gate silently unmet indefinitely.
- **Found and fixed a real, previously-unchecked assumption: the Phase 2
  confidence-calibration audit (2026-07-29, round-1 model, 10-row
  holdout) was never re-run after ~5 retrains and holdout growth to 15
  rows.** The whole "never assume a value for an empty field" design
  rests on that one-time finding ("confidence separates right from wrong
  for every field except intent"). Built `data/check_confidence_calibration.py`
  (reads `data/real_world_eval_report.json`, flags any WRONG prediction
  at or above `pipeline.MIN_JOIN_OPEN_CONFIDENCE` — the exact blank
  threshold `prompt_synthesis.py` uses) as a **repeatable script**, same
  convention as every other audit tool in `data/`, so this becomes a
  standing per-retrain check instead of a one-time finding that silently
  goes stale again.
  Ran it against the current (round 4) model. Raw output flagged 5 wrong
  predictions at/above threshold across `object`, `intent`, `magnitude`
  (×2), `constraints` — but hand-checking each one (small n makes this
  feasible, and necessary: the eval harness's own docstring already
  flags its loose substring-match scoring as "a coarse proxy, not
  exact-match paraphrase scoring") separated real findings from scoring
  artifacts:
  - **2 were false alarms from the scoring proxy, not real calibration
    failures** — `rw_017` magnitude (`"approximately $50 billion"` vs
    gold `"about $50 billion"`) and `rw_021` constraints (`"retain
    rental inventory..."` vs gold `"keep rental inventory..."`) are
    synonym paraphrases the loose-match scorer counts as wrong but a
    human reader wouldn't.
  - **`rw_016` intent is the already-known, already-documented
    hallucination gap** — not a new finding, just reconfirmed.
  - **2 are genuinely new, and one is more serious than anything
    currently on the Known gaps list**: `rw_034` object span-selection
    error (picked the causal reason `"production rates"` instead of the
    actual subject `"Engineered Composites segment"`, at 0.582
    confidence) — related to the existing actor/object thinness gap
    (Known gap 0), not wholly new. **`rw_027` magnitude: T5 silently
    altered the literal digits of extracted numbers** —
    `"7.0%"→"7.2%"`, `"10.0%"→"100%"` (a 10x factual distortion from a
    dropped decimal point), `"5.0%"→"5.10%"` — at 0.556 confidence,
    above the blank threshold, would render as confident, unflagged fact
    in the product UI. This is categorically worse than the known
    text-hallucination gaps: it corrupts numbers, which read as precise
    and are the least likely thing a user double-checks. New Known gap 8
    below.
  - **Sample sizes remain small per field** (n=3 for intent/constraints,
    n=1 for context) — directional, not statistically definitive, same
    honest caveat the original 2026-07-29 audit carried. But directional
    "confidence-separates-correctness" no longer holds cleanly for
    `object`/`magnitude` the way it did for the round-1 model, and that
    matters regardless of exact n given what's built on top of it.
- **No automated test suite exists anywhere in this repo** — zero
  `test_*.py` files. The project's hardest invariants (never train on
  the frozen holdout, `source_text` must be an exact substring, no
  cross-role span overlap, blank-threshold behavior) are currently
  enforced only by remembering to run the right one-off script each
  session, not by anything that fails a build automatically. Flagged as
  real tech debt, **not fixed this session** — deliberately left as a
  decision for the user rather than assumed, since it's a real scope/time
  investment, unlike the calibration script above which was small,
  additive, and directly protected an already-stated safety design.
- Confirmed **no regression on the disk-space constraint** flagged
  2026-08-05 — `seq2seq_ckpt/` is back to a stable 1.4GB
  (`save_total_limit=2` holding as intended), not re-accumulating.
- **Assessment, stated plainly:** Phases 1-4 are real, working, and
  meaningfully iterated on — the plan has been followed faithfully and
  the extraction-layer retrain discipline (backup → retrain → gate →
  document, never touch the holdout) has held across every session
  without exception, including this one. The gap isn't process, it's
  that **two foundational checks were assumed-valid instead of
  re-verified as the system evolved** (usage-volume for the Phase 6
  gate, confidence calibration for the blank-threshold safety design) —
  exactly the kind of drift a solo, session-by-session build is prone to
  without an explicit recurring checklist. **No phase-plan overhaul
  recommended** — Phases 1-4 architecture, the gate-before-Phase-6
  structure, and the batched-retrain discipline are all still sound.
  Recommended addition, small and additive: run
  `data/check_confidence_calibration.py` alongside
  `data/eval_on_real_world.py` after every future retrain, so this
  doesn't go stale silently again.

## Current status (as of 2026-08-09, continued — live QA session, found and fixed a real rendering bug)

**Same-session continuation:** user asked me to actually run the app and
drive it myself via Chrome, rather than reason about it from code alone.
Flagged upfront that me driving the browser is still solo/self-testing
from this session's perspective — it doesn't move the Phase 6 usage-gate
finding above, which specifically needs usage from outside this session.
Did it anyway as another live QA pass, which is genuinely useful on its
own.

- Launched `streamlit run app.py` locally, drove it via
  `claude-in-chrome` in the user's actual Chrome.
- **Deliberately tested a fresh 3-way-magnitude-join query** (`"Our
  regional sales grew 12% in the West, 9% in the East, and 15% in the
  North this quarter."`) to see gap 8 (the digit-corruption bug found
  earlier this session) live. The digits weren't corrupted this
  particular time — consistent with gap 8 being an unseen-shape
  hallucination, not deterministic — but this run surfaced a **different,
  more visible bug**: both `magnitude` (`"[12%, 9%, 15%]"`) and `scope`
  (`"['in the West', 'in the East']"`) rendered raw Python-list-repr
  syntax directly in the master-prompt sentence — the exact "Here's what
  we understood" text a user reads first — and in the extraction-detail
  field cards.
- **Root-caused precisely**: `build_seq2seq_pairs.py` trains T5's
  multi-value normalization targets as literal `str(python_list)` text
  (e.g. target `"['new customers acquired', 'blended CAC']"`), so T5
  generates that bracket/quote syntax verbatim as its output string —
  confirmed via `pipeline.py` inspection that no `ast.literal_eval` or
  equivalent parsing ever converts it back to a real list downstream.
  `prompt_synthesis.py`'s `build_fields()` (`"text": ... str(r["value"])`)
  and `app.py`'s `_field_card_html()` (`str(r["value"])`,
  `str(r["source_text"])`) both passed this straight into user-facing
  HTML/text unchanged. This directly undermines the Product Vision's
  explicit Phase 1 goal — "a well-formed, business-grade prompt scaffold,
  not just a template dump of the fields" — on any query where a field
  has more than one surviving span, which is common (scope/magnitude/time
  regularly have 2-3 values in real queries).
- **Fixed at the rendering layer only, not retrained**: added
  `prompt_synthesis.humanize_value()` — parses a list or list-repr string
  back into real items (via `ast.literal_eval`, with a plain comma-split
  fallback for cases T5 leaves unquoted, e.g. `"[12%, 9%, 15%]"` where
  bare `%` breaks Python literal syntax) and joins them as natural prose
  (`"12%, 9%, and 15%"`, `"in the West and in the East"`). Wired into both
  `build_fields()` (covers the master-prompt sentence and the edit-form
  pre-fill, since both read from `fields[role]["text"]`) and `app.py`'s
  field-card display (`value_display`/`source_display`). Deliberately did
  **not** touch `correction_log.py`'s `original_value` logging — that
  correctly keeps the raw, true extracted value for data provenance;
  only the display layer needed fixing. Hand-tested edge cases (empty
  list, malformed brackets, single-item list, real list vs. list-repr
  string, `None`) before wiring it in.
- **Verified the fix live, restarting Streamlit fresh to clear a stale
  module-cache reload** (first hot-reload attempt threw
  `ImportError: cannot import name 'humanize_value'` even though the
  file was correct on disk — Streamlit's non-watchdog file poller
  desynced; a full process restart cleared it cleanly): re-ran the same
  3-way query end to end. Master-prompt sentence, edit-form fields, and
  the final confirmed "Got it" sentence all render clean natural prose
  now, zero brackets or quotes anywhere. Confirmed
  `data/corrections_log.jsonl`'s new entry is correct on both sides —
  `original_value` still shows the raw `"[12%, 9%, 15%]"` /
  `"['in the West', 'in the East']"` (provenance preserved) while
  `final_value` shows the humanized text (`"12%, 9%, and 15%"`, `"in the
  West and in the East"`) — confirming the fix is scoped to display only,
  as intended.
- Stopped the local Streamlit server and closed the browser tab when
  done — nothing left running.
- **Not committed yet**, same as everything else this session.

## Current status (as of 2026-08-09, continued again — gap 8 sourcing pass, round 5, partial fix)

**Same-session continuation, user asked to keep going and fix gaps
without further check-ins.** Targeted Known gap 8 (T5 magnitude digit
corruption on 3-way joins) since it was already precisely root-caused
earlier this session.

- **Sourced one real 3-way-magnitude quote** (`rw_051`, F5 Q2 2026:
  `"F5's revenue grew 3% in the Americas, 22% in EMEA, and 19% in
  APAC year over year."`) — same Americas/EMEA/APAC percentage-split
  shape as `rw_027` (the eval-holdout row this gap was diagnosed from),
  but a different company so the fix couldn't just memorize FactSet's
  numbers. Validated clean, split (train-only, `rw_051` not added to
  `EVAL_IDS`), rebuilt `choice_forge_dataset_combined_136.json` (100 + 36),
  confirmed via `git diff` the frozen holdout stayed byte-identical.
  Backed up round-4 model artifacts to scratchpad first.
- **Retrained CRF + T5, gated against the 15-row holdout — net positive,
  promoted, but with an important honesty caveat found only by checking
  the raw prediction, not trusting the eval script's summary number.**
  Aggregate: status 82.22%→**83.70%**, value 68.66%→**70.15%**. Real,
  confirmed fixes: `rw_017`'s hallucinated `object` (`"full-year
  guidance"`) now correctly returns missing; `rw_017` `magnitude` now
  matches gold exactly (`"about $50 billion"`, previously a synonym
  near-miss). One regression, concentrated entirely in `rw_035`
  (Albany International) — already flagged in the 2026-08-08 round-3
  entry as a noisy low-n row from the annotation re-split, not a new
  systemic issue.
  **The eval script initially reported `magnitude` at 100% value
  accuracy — this is partly a scoring-methodology artifact, caught by
  checking the raw prediction instead of trusting the summary table**:
  `rw_027`'s prediction is `['7.20%', '10.10%', '5.0%']` against gold
  `['7.0%', '10.0%', '5.0%']` — 2 of 3 numbers are still measurably wrong
  (formatting-level corruption now, not the prior 10x `"10.0%"→"100%"`
  distortion, but still wrong), yet `loose_value_match` scores the whole
  joined string as correct because the third value (`'5.0%'`) happens to
  appear as a substring of it. **This is a real, generalizable weakness
  in `data/eval_on_real_world.py`'s scoring for multi-value fields** —
  it can pass a partially-wrong list as fully correct if any single
  element matches — flagged here rather than silently trusted, and worth
  fixing in the harness itself before the next multi-value-heavy gap.
- **Precisely characterized how much gap 8 actually improved, via direct
  `pipe.synthesize()` calls on fresh (non-training) 3-way inputs rather
  than assuming the eval number told the whole story**: whole-number
  percentage joins are now clean (`"14%; 6%; 21%"` →
  `"['14%', '6%', '21%']"`, exact), but **decimal percentage joins still
  lose precision** (`"2.5%; 18.5%; 9.5%"` → `"['2.5%', '18%', '9.5%']"` —
  `18.5%` silently became `18%`; the original failing case, `rw_027`
  itself, still corrupts 2 of 3 values when re-run directly). **One
  training example generalized partially, not fully** — it taught the
  3-way-join *shape* but not decimal-precision preservation within it.
  This is the same lesson this project already learned once for the
  negation-cue constraint gap (2026-08-05: one example taught the CRF
  nothing; it took 4-5 diverse examples to actually generalize) —
  recurring here for a different field and a different model (T5, not
  CRF), same underlying mechanism (a reinforced pattern needs enough
  diverse examples to generalize, not just one).
- **Decision: promoted anyway.** Net aggregate is genuinely positive on
  both tracked metrics, the one regression is in an already-known noisy
  row, and severity of the original bug (10x factual distortions) is
  confirmed gone even where the fix is incomplete. Re-ran
  `data/check_confidence_calibration.py` — no new dangerous
  (wrong-but-above-threshold) findings introduced.
  `role_tagger.joblib`/`value_synthesizer/model.safetensors` now reflect
  round 5; round 4's artifacts backed up to scratchpad.
- **Gap 8 status: improved, not closed.** Known gap 8 below updated to
  reflect this precisely rather than marking it resolved — whoever picks
  it up next should source 2-3 more diverse 3-way (and ideally 4-way)
  magnitude examples, specifically including decimal percentages and
  dollar amounts, not just whole-number percentages like `rw_051`.
- **Not committed yet**, same as everything else this session.

## Current status (as of 2026-08-08, continued yet again — gap 7 diagnosis, round 4)

**New-session continuation, picked from the Known gaps list per user request.**
Diagnosed and partially fixed Known gap 7 (the `time`-field regression the
round-3 `measure` sourcing pass introduced), following the same
diagnose-one-field discipline the `measure` gap itself used.

- **Confirmed gap 7 was still open on the live (round 3) model**, not
  assumed from the prior session's notes: pulled the actual `time`-field
  numbers out of `data/real_world_eval_report.json` directly — 66.67%
  status (10/15), below the pre-regression 73.33% baseline. Verified
  `rw_044`/`rw_049` (the two rows round 3's annotation fix explicitly
  targeted) were genuinely fixed and matched gold verbatim, confirming
  the report reflects round 3 as documented. 5 rows still failed:
  3 false negatives (`rw_012`, `rw_016`, `rw_017` — gold `time` present,
  predicted `missing`) and 2 false positives (`rw_027`, `rw_035` — gold
  `time` missing, predicted a spurious span).
- **Root-caused the 3 false negatives to two distinct CRF span-boundary
  bugs**, both new patterns not seen in training: (1) `rw_012`'s
  `magnitude` span swallowed a leading `"by 2028"` time clause whole
  (`"by 2028 to more than $3 billion"`) — the mirror-image of the
  trailing-clause bug round 3 already fixed; (2) `rw_016`/`rw_017`'s
  `object` span swallowed a leading bare time-adjective directly modifying
  the following noun with no preposition (`"third quarter common stock
  dividend"`, `"full-year guidance"` — the latter is actually a
  hallucinated `object` span entirely, since gold has `object: missing`
  there).
- **Found a real, provable annotation bug behind failure mode (2)**: this
  same session's own `rw_050` (`"DexCom expects full-year revenue of
  $5.18 billion..."`, sourced in the 2026-08-08 `measure` pass) had
  `measure.value = "full-year revenue"` bundling the bare time-adjective
  whole, with `time: missing` — directly contradicting the established
  convention the eval holdout itself uses (`rw_017`'s gold splits
  `measure="net interest income"` / `time="full-year"`). This is the same
  *kind* of bug as the `rw_045`/`046`/`049` magnitude-swallowing-time bug
  fixed earlier the same day, just recurring in a different row the
  earlier fix pass didn't touch. Fixed in `data/build_real_world_pilot.py`
  (source of truth) — `measure="revenue"`, added `time="full-year"` — then
  regenerated `real_world_pilot_batch.json` via the script,
  re-validated (clean, zero errors), re-split (holdout confirmed
  byte-identical via `git diff` — `rw_050` is a training-only row, never
  touched the frozen holdout), rebuilt
  `choice_forge_dataset_combined_135.json` (same row count, only content
  changed).
- **Tested empirically before sourcing more data, per this project's own
  "never assume a retrain helped" discipline** — retrained CRF + T5 fresh
  on the fixed 135-row set and re-ran `data/eval_on_real_world.py` to see
  whether the single annotation fix was enough, before spending effort
  sourcing new rows for a hypothesis that might not have been necessary.
  Result: it wasn't enough — `rw_016`/`rw_017` still miss `time`
  (unchanged, still `missing`), confirming the object-role variant of this
  bug genuinely needs its own training signal, not just a measure-role
  fix. But the fix wasn't wasted: it had a real, unplanned side effect —
  diffing every field's `status_correct` between round 3 and this retrain
  showed exactly 4 flips, **all fixes, zero regressions**: `rw_027.scope`
  and three `rw_035` fields (`object`/`scope`/`context`) all corrected.
  Net result: **status 79.26%→82.22%, value unchanged at 68.66%** — a
  clean, unambiguous improvement with no trade-off to weigh, unlike every
  prior retrain this project has gated. **Promoted — this is now the live
  model** (`role_tagger.joblib` / `value_synthesizer/model.safetensors`).
  Round 3's artifacts backed up to the session scratchpad first, per the
  standing safety pattern, in case this decision needs revisiting.
- **Searched for real sourcing material to fix the remaining object-role
  gap, concluded genuinely data-scarce rather than under-searched**: 8 web
  searches plus full-transcript fetches of Quaker Chemical, Newell Brands,
  and a second pass over Wells Fargo's own transcript, specifically
  hunting for a bare time-adjective directly modifying an object-type noun
  (not measure) in real corporate speech. The one recurring real pattern
  that matches syntactically — "quarterly dividend" (PNC, Alphabet,
  Portland General) — turned out to be a *frequency* adjective ("paid
  every quarter"), not a *time-point* adjective ("this quarter"), and
  doesn't actually fit this schema's `time` semantics even if reused; the
  only real time-point match found (Wells Fargo's own sentence) is
  `rw_016`'s exact eval-holdout sentence, unusable as training data by the
  standing "never train on holdout" rule. Declined to force a
  borderline/ambiguous match into training data — the whole point of this
  session's `rw_050` fix was correcting exactly that kind of weak
  annotation. **`rw_012`/`rw_016`/`rw_017`'s failure mode remains
  genuinely open** — see Known gap 7 below, refined with this session's
  precise root-cause finding for whoever picks it up next.
- Nothing committed yet this session — pending user go-ahead, same as
  every prior local-only session.

## Current status (as of 2026-08-08, continued again — confirm/reject redesign)

**Same-day continuation:** user flagged real, concrete UX problems after
using the Phase 3 UI directly — nobody could tell the reject feature
existed or what it actually meant to reject, and (the important part)
rejecting produced nothing: no fallback, no next step. Read the actual
`app.py` code before proposing anything and confirmed this in the code,
not just from the report: `st.warning("Rejected: ...")` was the entire
reject behavior — the "Generate Output" section was gated on
`last_decision == "confirmed"` only, so a rejected query (even one where
every field had been carefully corrected) hit a dead end. This directly
contradicts the Product-vision section's own Step 1 item 6, written
2026-07-29 and never built: "If not, a fallback path is needed... this
accept/reject signal is exactly the correction-capture data the
self-learning flywheel needs."

Planned via `EnterPlanMode` (approved plan saved at
`~/.claude/plans/moonlit-wibbling-tulip.md`), then implemented, entirely
within `app.py` — `prompt_synthesis.py`, `correction_log.py`,
`llm_client.py`, and the pipeline/model layer needed no changes.

- **Restructured the whole confirm/reject section into a real state
  machine** (`initial` → `editing` → `confirmed`/`rejected`, keyed per
  `run_id` the same way existing widgets already were). The raw 9-field
  grid, confidence gauges, metric row, and JSON download — everything
  that used to render unconditionally above the fold — moved into a
  single collapsed `st.expander("🔧 See extraction details")`. The
  master-prompt sentence is now the first thing shown, under a plain
  "Here's what we understood" heading.
- **If there are no blanks**, the user sees a direct "Does this capture
  what you meant?" with two buttons — "✅ Yes, this is right" (confirms
  immediately, no form to submit) or "✏️ Not quite — let me fix it". **If
  blanks exist**, "Yes, this is right" is never offered at all — showing
  it would let someone one-click-confirm a sentence still containing
  literal `[actor — please fill in]` text, so only "✏️ Fill in the
  blanks" appears, forcing the edit form open. This wasn't explicitly
  speced but is a direct, low-risk consequence of the same "never assume
  a value for an empty field" principle already governing every other
  blank-handling decision in this codebase.
- **Real fallback loop on true reject**, per the user's explicit
  answer when asked what to hand back at that moment: "This is way off
  — start over" logs the rejection and increments a session-level
  `reject_streak`. The first reject offers only "🔁 Rephrase and try
  again" (pre-fills the query box with the original text + a one-line
  tip). Only once `reject_streak >= 2` — two rejects with no successful
  confirm in between — does "➡️ Just answer my original question
  directly" appear, clearly labeled "Skips CHOICE's structured
  understanding step," calling `llm_client.generate_output()` on the
  **raw query**, not the broken master prompt. Confirming (as-is or with
  edits) resets the streak to 0.
- **Logging schema extended, additively** (`correction_log.py` itself is
  unchanged — it just writes whatever dict it's given): every entry now
  carries `resolution_path` (`confirmed_as_is` / `confirmed_with_edits` /
  `rejected`) and `reject_streak_at_decision`, a real upgrade over the
  prior flat confirmed/rejected boolean for whatever eventually trains
  Phase 5.
- **Caught and fixed a real bug via live testing, not just code review**:
  the first version of the "Rephrase and try again" button set
  `st.session_state.query_text` directly inside the button's `if
  st.button(...):` block, which raised `StreamlitAPIException` — the
  `query_text` widget had already been instantiated earlier in that same
  script pass. Fixed by moving the mutation into a proper `on_click`
  callback (`_start_rephrase`), the same pattern `_apply_example()` and
  `_apply_suggestion()` already used correctly elsewhere in this file.
  Would not have been caught by reading the code alone — only surfaced
  by actually clicking through the flow in a live `streamlit run`
  session via browser automation.
- **Verified live, every branch, in a real running session**: blanks
  present → only "Fill in the blanks" shown (no premature "Yes, this is
  right"); edit → "This is way off — start over" → only rephrase offered
  (streak 1); rephrase → re-run → edit → reject again → bypass button
  now appears (streak 2) → clicked it → real Gemini call fired on the
  *raw query* and returned a genuinely relevant answer (confirms it
  wasn't sending the placeholder-filled master prompt by mistake); edit
  → "Continue with my corrections" (actor filled in, constraints/context
  marked not-applicable) → correctly rendered sentence with the
  not-applicable clauses cleanly dropped → "Answer" section appeared
  with a working "Send to Gemini" button. Checked
  `data/corrections_log.jsonl` after each step — `resolution_path`,
  `reject_streak_at_decision`, `not_applicable`, and `user_edited` all
  came through exactly as designed.
- Footer caption (previously stale — was still citing 126-row/13-row-set
  numbers from two sessions ago) rewritten with today's real 135-row/
  15-row-holdout figures and folded into a small "About this model"
  expander instead of running unconditionally on every page load.
- Nothing committed yet this session — pending go-ahead, same as the
  retrain work above.

## Current status (as of 2026-08-08 — targeted `measure` sourcing pass, promoted)

**2026-08-08 session:** picked up the recommended next step from the
2026-08-06 diagnosis (Known gap 1): the live model missed `measure` on
every real query where the measure noun phrase sat in subject position
(possessive-subject: `"PNC's operating target for its CET1 capital ratio
is..."`; or `"X expects <measure> to..."`), because the 130-row dataset
had zero possessive-subject training examples and only one `"expects"`
example.

- **Sourced 7 new real rows** (`rw_044`-`rw_050`) via
  `data/build_real_world_pilot.py`, from 4 companies new to the dataset
  (Thermo Fisher, AGCO, S&P Global, DexCom Q1/Q2 2026 earnings calls via
  fool.com transcripts) — deliberately new companies so the CRF can't
  just be memorizing a company name instead of the syntactic pattern.
  5 rows (`rw_045`-`rw_048`, `rw_050`) went to training; 2
  (`rw_044` — TMO `"expects free cash flow to be in the range of..."`,
  `rw_049` — DexCom `"'s gross margin was 64.1%..."`) held out in eval
  specifically to test whether the pattern generalized, one per phrasing
  shape. Validated via `data/validate_real_world_pilot.py` (clean on
  first pass — no overlap/substring errors), split via
  `data/split_real_world_pilot.py` (added the 2 new IDs to `EVAL_IDS`,
  left every prior ID untouched), rebuilt
  `choice_forge_dataset_combined_135.json` via
  `data/build_combined_dataset.py` (100 original + 35 real).
- **Backed up round-1's live model artifacts to the session scratchpad
  first** (same safety pattern as the 2026-08-05/06 sessions), then
  retrained CRF + T5 fresh on the full 135-row set and re-ran
  `data/eval_on_real_world.py`. This also **closes the reproducibility
  gap** flagged open at the end of the 2026-08-06 session (live model
  trained on a 126-row file while the combined-dataset file on disk said
  130) — both now reflect the same 135-row set again.
- **Gated the result — genuine, broad improvement, promoted.** On the
  now-15-row eval holdout (13 previous + the 2 new rows): status
  77.78%→**80.74%**, value 62.69%→**64.18%**, actor 93.33%→**100%**.
  The targeted field itself: measure status 66.67%→**73.33%**, value
  44.44%→**55.56%**. Directly confirmed the fix, not just the aggregate
  number: both held-out test rows (`rw_044`, `rw_049`) now correctly
  detect `measure` in subject position (0.452 and 0.699 confidence)
  where the round-1 model would have returned `missing` on this shape.
  `object`/`scope`/`context` status all improved or held; only `time`
  meaningfully regressed (73.33%→60.00% status) — one field paying a
  cost from the shared CRF's decision boundaries shifting, the same
  mechanism flagged in the 2026-08-05 negation-cue rounds, but this time
  isolated to a single field rather than the multi-field collapse that
  sank that earlier attempt (round 2 there regressed status *and* was
  net-negative overall; this pass is net-positive on every headline
  metric). Checked `seq2seq_ckpt/` disk usage before finishing —
  `save_total_limit=2` (set 2026-08-05) held at 1.4GB, no repeat of the
  27GB accumulation bug.
- **New known gap surfaced by this pass, diagnosed and fixed same
  session (see continuation below):** the `time` regression above looked
  at first like it hit 4 rows (`rw_012`, `rw_016`, `rw_017`, `rw_044`),
  but comparing directly against the round-1 model (restored from the
  scratchpad backup) showed 3 of those were **pre-existing misses**, not
  new — only `rw_035` and `rw_044` actually flipped from correct to
  wrong. Root-caused to a real annotation bug in this session's own new
  rows, not a generic capacity-sharing effect. Full fix in the
  continuation entry immediately below.

**Same-day continuation: root-caused and fixed the `time` regression
above, rather than accepting it as an unavoidable trade-off.** Comparing
the promoted model against the restored round-1 model on the identical
15-row holdout isolated the regression to exactly 2 rows (`rw_035`,
`rw_044`), not the 4 initially suspected — `rw_012`/`rw_016`/`rw_017`
were already wrong under round-1 too. Inspecting `rw_044`'s full
prediction showed why: `magnitude` had absorbed `"for the year"` whole
(`"$6.9 billion to $7.4 billion for the year"`), leaving nothing for
`time` to claim.

- **Found the actual cause: an annotation inconsistency in this
  session's own new rows.** The established dataset convention (see
  `rw_010`, `rw_020`) splits a bare number into `magnitude` and puts any
  trailing comparison/timing clause into `time` — e.g. `"up
  approximately 13%"` (magnitude) + `"compared to 2025"` (context). This
  session's `rw_045`/`rw_046`/`rw_049` broke that convention, bundling
  the whole comparison clause (`"90 basis points higher than a year
  ago"`) into a single `magnitude` value instead of splitting it. That
  taught the CRF that tokens ending in `"...year"` can continue a
  `magnitude` span, which is exactly what made it swallow `rw_044`'s
  genuine trailing `"for the year"` clause into `magnitude` instead of
  opening a new `time` span, and made it spuriously fire `time` on `"of
  the year"` inside `rw_035`'s unrelated `constraints` clause.
- **Fixed the 3 rows' annotation** to match the established convention
  (bare number in `magnitude`, comparison anchor in `time`), rebuilt,
  re-validated, re-split, and retrained fresh on the corrected 135-row
  set (labeled round 3 below to distinguish from the round-2 model this
  replaces).
- **Gated round 3 against round 2 on the identical (corrected) holdout —
  a genuine trade-off, not a clean win, decided and documented rather
  than left ambiguous.** Round 3: 79.26% status / **68.66%** value.
  Round 2: 80.74% status / 65.67% value. Directly confirmed the target
  fix: both `rw_044` and `rw_049` now match `time` **verbatim** against
  gold (previously `rw_044` returned nothing). The status dip traces to
  4 single-row flips concentrated in low-n fields (`object`: 6 rows,
  `scope`: 4 rows) — e.g. D.R. Horton's `"consolidated leverage"` now
  spuriously filling `object`, FactSet's Americas/APAC/EMEA list
  dropping from `scope` — plausible model-capacity noise from the
  re-annotation shifting boundaries, not a new systemic failure mode
  (unlike the 2026-08-05 round-2 negation-cue attempt, which regressed
  measure/magnitude/time/constraints *together*, a clear sign of genuine
  conflict rather than noise).
  **Decision: promoted round 3.** Reasoning: (1) leaving the annotation
  bug in place would corrupt every future retrain on this dataset, not
  just this one; (2) shipping round 2 would leave this session's actual
  goal only half-verified, since `rw_044`/`rw_049` — the two rows built
  specifically to test the `measure` fix generalized — still failed on
  an adjacent field; (3) value accuracy, arguably the more meaningful
  metric under this project's reasoning-integrity philosophy (is the
  extracted content actually *right*, not just present), improved more
  than status declined. Verified round 3 reproduces identically from a
  cold model-swap before finalizing (same discipline as every prior
  promotion this project has made).
- `role_tagger.joblib` / `value_synthesizer/model.safetensors` now
  reflect round 3. Round 2's artifacts remain backed up in the session
  scratchpad if this decision needs revisiting.
- Committed locally (not round-2's earlier commit — a fresh commit with
  round 3's corrected data + model on top). **Still not pushed** — same
  blocker as the 2026-08-04 session: the `alethiaworks` deploy key needs
  `ssh-add`, which needs the user's passphrase.
- **Live-tested round 3 on genuinely fresh queries, not just the frozen
  eval set** (same discipline as the 2026-08-05 session's live A/B test)
  — three queries with zero overlap with any training/eval row: (1)
  `"Verizon's operating margin was 24.3% in the third quarter, driven by
  cost discipline."` (possessive-subject measure, a company never in the
  dataset) correctly split into `measure`/`magnitude`/`time`/`context`
  with no swallowing; (2) `"Nike expects gross margin to expand by 150
  basis points for the full year."` (the `"expects X"` shape, also a new
  company) same clean split, confirming the fix generalizes beyond the
  4 sourced companies; (3) an unrelated general marketing query (no
  finance framing at all) confirmed actor/intent/scope/time and the
  negation-cue constraint pattern (`"without increasing the overall ad
  spend"`) still work correctly — no regression outside the earnings-call
  domain this pass focused on.

## Current status (as of 2026-08-06 — AI-suggested blank fills)

**2026-08-06 session:** user shared a stakeholder review doc (`CHOICE
Forge improvement suggestions_6-Aug.docx`) with 3 worked examples where a
human reviewer "corrected" the master prompt by inventing values for
blank Actor/Constraint/Context fields — e.g. adding "Marketing and Sales
team" as Actor and "service quality and SLA compliance must not be
compromised" as a Constraint, neither of which appeared anywhere in the
original query text. Checked each example against its source query before
reacting: confirmed none of the added content was actually stated, so
folding it in silently would directly break this file's own "never assume
a value for an empty field" rule. Flagged the tension to the user instead
of implementing the doc's suggestion as-is.

Agreed direction: offer the same kind of enrichment, but only as an
explicitly-labeled, opt-in AI suggestion the user must actively accept —
never silently presented as extracted fact. Built as an extension to
Phase 3, not a new phase:

- Gave the provider contract (`llm_providers/*.py`) a `system_prompt`
  parameter (`generate(prompt, system_prompt=SYSTEM_PROMPT)`, all three
  providers) so a second, stricter system prompt
  (`SUGGESTION_SYSTEM_PROMPT` in `llm_providers/_shared.py`) can be used
  for this call without touching Phase 4's answer-generation prompt.
  Wording explicitly bars inventing specific numbers/dates/names and
  instructs omitting a field rather than guessing.
- New `blank_suggestions.py` (build/parse/get suggestions) and
  `llm_client.generate_suggestions()` — see the folder-map entry above
  for the full contract.
- `app.py`: a "💡 Suggest values for blanks" button (shown only when
  blanks exist) fetches suggestions once, scoped to the current `run_id`
  so they can't leak onto a different query. Each suggested field gets a
  checkbox, outside the confirm/reject form, captioned "unverified
  guesses, not extracted from your query." Checking one pre-fills the
  corresponding form field via the same session-state-before-widget-
  creation trick `_apply_example()` already uses for the example pills —
  proven pattern in this file, not a new mechanism. Required dropping an
  explicit `value=""` on the blank-field `text_input` (it was silently
  overriding the pre-fill on the widget's first creation).
  `data/corrections_log.jsonl` entries now carry `ai_suggested` +
  `ai_suggestion_shown` per field, distinguishing "suggestion shown but
  declined" from "suggestion accepted" from "real user-typed knowledge" —
  data a future Phase 5 training pass will need to weight these
  differently.
- Verified live in a running Streamlit session using the doc's own
  example 1 query: suggestions rendered correctly labeled, accepting
  Actor ("Sales and Marketing Team") and Context ("regional market
  expansion strategy") pre-filled those fields while declined suggestions
  (object/scope/measure/magnitude/constraints) stayed blank, Confirm
  produced the correct final sentence, and `corrections_log.jsonl`'s new
  entry showed exactly the intended per-field provenance. Also confirmed
  a second, different query afterward showed no leftover suggestions from
  the first (the `run_id` scoping holds). Smoke-tested
  `blank_suggestions.parse_suggestions()` against well-formed,
  markdown-fenced, and garbage LLM output beforehand (degrades to `{}`
  safely in the last two cases, never raises).
- Committed (`900a89e`) and pushed to `origin/main`.

**Same-day continuation: attempted to close the round1/round2 dataset-vs-
model reproducibility gap flagged in the 2026-08-05 entry below.** Backed
up the live round-1 model artifacts to the session scratchpad first.
Rebuilt `data/seq2seq_pairs.jsonl` from the full, already-committed
`choice_forge_dataset_combined_130.json` (confirmed identical — it was
already built from that file), retrained the CRF fresh on the same
130-row set, then retrained T5 with `NEGATION_OVERSAMPLE_FACTOR` reduced
from 5 to 3 (a bounded regularization attempt, since round 2 already
tried 5x and still regressed non-negation fields — the goal was to test
whether the oversample multiplier itself was the cause). Note the current
frozen holdout has grown from 10 to 13 rows since round 1's original gate
(two round-1-sourced rows plus the round-2 Tesla row are now permanently
in it), so the fair comparison is round-1-vs-round-3 **on today's 13-row
set**, not against the previously-published 78.9%/67.4%/100% figures
(which were measured against the smaller 10-row set and are no longer
directly comparable).

Round 1 (currently live) on the 13-row set: **77.78% status / 61.02%
value / 92.31% actor**. Round 3 (fresh retrain, 3x oversample) on the
same set: **76.07% status / 55.93% value / 100% actor** — fixed `actor`
to 100% and improved `scope` (50%→75% value), but regressed `measure`,
`magnitude`, `time`, and `constraints`, the same shape of regression as
round 2. This rules out "the 5x oversample factor itself is the cause" —
reducing it to 3x didn't fix the aggregate regression, so the real driver
is more likely the CRF/T5-small's limited capacity redistributing
attention across a genuinely larger, more varied 130-row set, not a
tunable hyperparameter. **Did not promote** — restored round 1's model
from the scratchpad backup (verified via `git status`: zero diff, exact
byte match) and reverted the `NEGATION_OVERSAMPLE_FACTOR` code change.
Live model is still round 1's, dataset files still reflect the full
130-row set — the reproducibility gap remains open. Next attempt should
probably target one specific regressing field (e.g. `measure`, which
dropped 42.86%→14.29% value accuracy) with its own diagnostic pass rather
than another whole-dataset retrain sweep.

## Current status (as of 2026-08-05, continued again — compound-query detection)

**Same-day continuation, after committing the sourcing/retrain work
(commit `906f7bf`):** disk space cleanup (see below), then built the
detection half of Known gap 6 (actor↔intent pairing) — see the Known
gaps entry for the full technical description. Also fixed a stale
footer caption in `app.py` still citing the pre-retrain baseline
(77.8%/63.0%/90%) instead of the live model's real numbers
(78.9%/67.4%/100%), caught while live-testing the new feature in a
running Streamlit session (killed and cleaned up after).

**Disk space, unrelated but handled same session:** project folder had
grown to 28GB. Root cause: `seq2seq_ckpt/` (already gitignored) was 27GB
— `train_seq2seq.py` had no `save_total_limit`, so every epoch of every
retrain left a checkpoint behind permanently (2 retrains × 20 epochs = 40
checkpoints × ~695MB). Deleted the directory (safe: gitignored, never in
git history, and the actual deliverable is saved separately to
`value_synthesizer/`) and added `save_total_limit=2` so this can't
reaccumulate. Project folder is now ~930MB.

## Current status (as of 2026-08-05, continued — sourcing pass + retrain)

**2026-08-05 session:** user asked for a senior-dev sanity check on the
8-phase plan. Flagged two things, both now written into the "Agreed build
order" section above rather than left as informal opinion: (1) added an
explicit gate before Phase 6 requiring both a targeted real-data sourcing
pass on the Known gaps list (with a measured `eval_on_real_world.py`
improvement over the current 77.8%/63.0% baseline) and real (non-solo)
usage of Phases 1-4 generating actual correction-log volume; (2) this
formalizes — rather than changes — the 2026-08-02 session's existing
recommendation to ship 1-4 as a demoable v1 before starting Phase 8, since
an informal recommendation is easy for scope-creep to quietly skip.

Also flagged a real, previously-undocumented edge case: today's pipeline
has no actor↔intent pairing across multiple spans — `multi_span` is
per-role only, so a compound query with several bundled actor-intent
chains (e.g. two departments each with their own goal) has no mechanism
to keep pairings straight in one master prompt. Written up as Known gap 6
below with a recommended direction (detect and ask the user to confirm
one-decision-vs-several, rather than auto-pair) — not designed or built,
just captured so the upcoming real-data sourcing pass and any future
prompt-synthesis work keep it in mind.

**Same-day continuation: did the real-data sourcing pass the Phase 6 gate
requires, in two rounds, then retrained and gated the result.**

- **Round 1 (8 rows, `rw_031`-`rw_038`):** sourced real quotes from Intuit,
  FactSet, Albany International, and Trane Technologies Q1/Q2 2026 earnings
  calls, targeting Known gaps 0/1 — generic team/role-phrased `actor` (e.g.
  "Intuit's mid-market direct sales team", "The residential business team"
  with zero company-name anchor), `measure`/`scope` thinness, and
  causal/purpose `context` clauses. Also found a genuine "without X"
  negation-cue constraint at Trane, contradicting the prior "found zero"
  finding in Known gap 2. Validated via `data/validate_real_world_pilot.py`
  (one overlap bug in the FactSet workforce row, fixed), split 2 new rows
  into eval (rare-role picks) and 6 into training, rebuilt
  `choice_forge_dataset_combined_126.json`, retrained CRF + T5. Real
  before/after on the original 10 eval rows: status 77.8%→**78.9%**, value
  63.0%→**67.4%**, actor 90%→**100%**. Genuine improvement, verified by
  re-running `data/eval_on_real_world.py`, not assumed.
- **Live-tested the improvement, not just trusted the eval score:**
  swapped the pre-retrain model back in via `git show`/`git lfs smudge`
  (the LFS-tracked `.safetensors` needed the smudge filter — a plain
  `git show` silently produces the LFS pointer text, not the binary; caught
  this immediately when the swapped-in file was 134 bytes instead of
  ~230MB) to run the identical query through both models side by side.
  Concrete finding: on `rw_027`'s query, the old model returned `actor:
  missing` entirely; the new model returns a real span. Flagged the honest
  caveat too — the new prediction is at confidence 0.379, just under the
  0.4 Phase 1 blank-insertion threshold, so this specific case still
  renders as a blank in the product UI even though the raw model "found"
  something. Backed up both model states to the session scratchpad before
  any swap so nothing was ever at risk of being lost.
- **Round 2 (5 rows, `rw_039`-`rw_043`):** live-tested round 1's model
  against a fresh, novel query using the negation-cue pattern ("without
  increasing headcount") — `constraints` came back completely missing.
  One training example (`rw_036`) wasn't enough for the CRF to generalize
  the pattern. Sourced 4 more real "without X" examples across 4 more
  companies (FactSet Q1 2026, EFC, Tesla, Climb Global) plus one causal
  `context` example, giving the pattern 4 training examples instead of 1
  (kept Tesla's row eval-only to actually test generalization). Rebuilt
  `choice_forge_dataset_combined_130.json` (13 eval / 30 train), retrained
  both models again.
- **Gated the result — and it failed the gate, honestly reported.**
  Round 2's model did fix the target: the same novel test query now
  detects `constraints` (confidence 0.376, `guard_note: "direction-flip
  corrected via template"`), and the held-out Tesla eval row detected the
  right span at 0.723 confidence (T5's paraphrase had a typo/hallucinated
  "must not" framing, so value-match still failed — detection generalized,
  normalization quality on the new pattern didn't). But aggregate accuracy
  on the original 10 tracked rows *regressed below the original baseline*:
  status 78.9%→74.4% (baseline was 77.8%), value 67.4%→58.7% (baseline was
  63.0%) — one shared CRF across 9 roles, and reinforcing one pattern in a
  130-row dataset shifted decision boundaries elsewhere (`measure`
  specifically dropped hard). Per the standing rule to gate every model
  version against the frozen holdout before promoting, **did not keep this
  version live.**
- **Decision (user's call, asked directly, not assumed):** keep round 1's
  model live (strictly better than baseline on every tracked metric, no
  regressions) rather than round 2's (fixes one real pattern but regresses
  others) or reverting to pre-session baseline. Restored round 1's
  `role_tagger.joblib` / `value_synthesizer/model.safetensors` from the
  scratchpad backup and re-ran `eval_on_real_world.py` to confirm it
  reproduces 78.9%/67.4%/100% exactly before calling it done.
- **Known reproducibility gap this creates, flagged explicitly so a future
  session doesn't get confused:** `data/real_world_training_augment.json`,
  `data/real_world_eval_holdout.json`, and
  `choice_forge_dataset_combined_130.json` on disk all reflect **round 2's**
  43-row dataset (kept — it's good, validated, real-sourced data, no
  reason to discard it). But the **live model artifacts**
  (`role_tagger.joblib`, `value_synthesizer/`) were trained on **round 1's**
  38-row dataset (`choice_forge_dataset_combined_126.json`, no longer the
  literal current combined-dataset file, but the retrain command in
  `README.md` reproduces it exactly via `data/build_real_world_pilot.py`'s
  git history if ever needed). Whoever picks up the negation-cue
  constraint work next should retrain fresh on the full 130-row set with
  either more reinforcement examples or a regularization change, re-gate,
  and only then let the combined-dataset filename and the live model
  match again.
- **Nothing committed yet this session** — sourcing scripts, updated
  eval/split outputs, and the chosen model artifacts are all still local,
  uncommitted changes, pending a go-ahead.

## Current status (as of 2026-08-04, continued again — UI redesign + Cloud secrets)

**Third same-day session:** the Gemini key landed correctly this time (see
below), then two more asks: redesign the Streamlit UI ("doesn't look good
at all"), and figure out the path to a live Streamlit Community Cloud
deployment.

- **Near-miss on the Gemini key:** the user's first attempt pasted the
  real key into `.env.example` (tracked) instead of `.env` (gitignored).
  Caught before anything was staged/committed -- confirmed via
  `git status`/`git diff` that it never touched git history, moved the
  key into `.env`, restored `.env.example` to its clean template.
  Verified the real key works with a live `llm_client.generate_output()`
  call afterward. No exposure, but worth remembering: only ever edit
  `.env`, never `.env.example`.
- **UI redesign, invoked via the `frontend-design` skill.** Concept:
  "field survey instrument" -- CHOICE Forge reads a vague business ask
  like a surveyor's transit reads terrain, resolving it into precise
  bearings (the 9 fields) each with a stated confidence/tolerance; the
  existing compass mark and "Forge" name already pointed this way.
  Token system: ink-slate background, three accents each carrying real
  meaning (brass = primary/action, verdigris = confirmed/high-confidence,
  rust = flagged/missing/low-confidence) instead of one decorative color;
  type split three ways by role (Space Grotesk labels, Source Serif 4 for
  actual document content -- query/master-prompt/LLM output, JetBrains
  Mono for readout data). Signature element: a tick-mark confidence gauge
  (10 ticks, filled by decile, colored by tier) replacing the plain
  progress-bar-plus-badge combo, repeated across every field card.
  Self-critiqued against the generic-AI-default checklist from the skill
  (cream+serif+terracotta / near-black+neon / broadsheet-zero-radius)
  before building -- deliberately none of the three.
  **Process note:** inspected the actual live Streamlit 1.60 DOM via
  browser JS (`data-testid` attributes for every widget type) before
  writing CSS selectors, rather than guessing at internal class names --
  those are version-fragile and guessing wrong would have silently no-op'd
  half the redesign. Rebuilt the 9-field grid, metric row, and
  master-prompt display as custom HTML (pure display, no interactivity
  lost); left the query textarea, example pills, and the confirm/reject
  form's inputs/checkboxes/buttons as native Streamlit widgets, restyled
  via CSS on their confirmed `data-testid`s.
  Verified end-to-end in a live session: real query -> field grid/gauges
  render correctly -> filled/confirmed the master prompt -> real Gemini
  call -> generated output typesets correctly (even the LLM's own
  markdown headers pick up the Space Grotesk treatment). Also checked
  390px mobile width (cards stack to one column, tags/pills wrap) and
  caught one transient false alarm (two example pills briefly looked
  "selected" in one screenshot; confirmed via `aria-checked` + computed
  styles it was just a mouse-hover artifact at that exact screenshot
  moment, not a real state bug). Added focus-visible outlines and gated
  hover/transition animation behind `prefers-reduced-motion`.
- **Deployment groundwork for Streamlit Community Cloud.** Corrected an
  assumption: pushing to GitHub does not by itself make the app live --
  the first deployment needs a one-time manual connection at
  share.streamlit.io (the user's own GitHub OAuth session, not something
  doable from here). After that one-time link, subsequent pushes to
  `main` do auto-redeploy.
  Found and fixed a real gap before that matters: every `llm_providers/*.py`
  module reads config via `os.environ.get(...)`, which works locally via
  `.env`, but Streamlit Cloud only exposes deployment secrets through
  `st.secrets`, not as real environment variables. Confirmed locally that
  `st.secrets` raises `StreamlitSecretNotFoundError` when no
  `secrets.toml` exists anywhere (i.e. every local dev setup) -- added a
  guarded bridge in `llm_client.py` that mirrors `st.secrets` into
  `os.environ` via `setdefault` (never overwrites a real env var), wrapped
  in try/except so the normal local-dev case (no secrets.toml) is a clean
  no-op. Re-verified a real local Gemini call still works after adding it.
  Flagged two things that couldn't be confirmed from docs alone and are
  the user's call, not blockers: Community Cloud apps are public by
  default unless the sharing setting is changed (real cost exposure,
  since this app spends real API credits on whichever key is configured),
  and the app's `torch`/`transformers`/230MB-model dependency footprint
  may or may not fit comfortably in free-tier Community Cloud resource
  limits (couldn't get a current authoritative number via WebFetch).
- Confirmed via `git status` that `main` was back in sync with
  `origin/main` after this session's commits -- the user pushed
  independently between turns (SSH agent still had a key loaded from
  earlier in the day, checked via `ssh-add -l` rather than assumed).

## Current status (as of 2026-08-04, continued — provider-agnostic LLM architecture)

**Same-day follow-up session:** after Phase 4 shipped hardcoded to
Anthropic, the user asked for the LLM call to be provider-agnostic before
adding a real key -- they want to test now against a Gemini key they
already have on hand, add the Anthropic key later, and be able to point
at a local Ollama model later still, all without touching app.py or
re-architecting again each time.

- **Refactored `llm_client.py` from "the Anthropic client" into a
  router.** It now reads `LLM_PROVIDER` and dispatches to one of three
  new modules under `llm_providers/` (`anthropic_provider.py`,
  `gemini_provider.py`, `ollama_provider.py`), each exposing the same
  `generate(prompt) -> str` contract and sharing one system prompt
  (`llm_providers/_shared.py`) so wording can't drift between providers.
  `app.py`'s call site (`llm_client.generate_output(...)`) didn't change
  at all -- the whole point.
- **Did not trust the fetched Gemini docs at face value.** WebFetch
  described a `client.interactions.create(model=..., system_instruction=...,
  input=...)` / `.output_text` shape that doesn't match the
  `generate_content()` pattern in older training data. Installed
  `google-genai` locally and inspected the actual installed package's type
  definitions (`CreateModelInteractionParam`, `Interaction.output_text`)
  to confirm the field names before writing `gemini_provider.py` --
  matched exactly. Also cross-checked that `gemini-3.6-flash` (the model
  WebFetch reported) is a real, current model string by grepping the
  installed SDK's own model-name references, since a wrong model ID here
  would have been a much harder bug to spot than a wrong field name.
- **Added `API_KEYS.md`** as the single file to read for switching
  providers, seeing every provider's env vars, or adding a new one (just:
  one new module + one line in `llm_client.py`'s registry). Documents the
  security rules explicitly: never hardcode a key, never commit `.env`
  (added to `.gitignore`), never paste a real key into chat/docs/commits
  -- treat any accidental exposure as compromised and rotate it.
  `.env.example` (no real values) shows the shape; `llm_client.py`
  auto-loads a real `.env` via `python-dotenv` if present.
- **Set `LLM_PROVIDER=gemini` as the temporary default**, per the user's
  request, since a Gemini key was already available for testing. Switching
  to `anthropic` (once that key is ready) or `ollama` is a one-line env
  var change -- no code edit, by design.
- **Caught a real bug via manual testing, not by inspection**: after the
  refactor, the "Generate Output" section still hardcoded "Send to
  Claude" and "Claude API call failed: ..." in `app.py`, even though the
  call was actually routing to Gemini underneath. Fixed both the button
  label and the error message to name the active provider dynamically
  (`os.environ.get("LLM_PROVIDER", ...)`.capitalize()`). Re-verified in a
  live streamlit session: confirmed a query, clicked "Send to Gemini",
  got a genuine Gemini-specific `AuthenticationError` referencing
  `ai.google.dev` -- proof it's really calling Gemini, not a leftover
  Claude code path with relabeled text.
- Also directly exercised `llm_client.generate_output()` for all three
  providers plus an unknown `LLM_PROVIDER` value from the command line
  (no browser needed for this part) -- each produced a distinct, correct,
  informative error with no key/server present.

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
   **`measure` specifically diagnosed 2026-08-06** (after the failed
   reproducibility-gap retrain above surfaced it as the worst regressor):
   pulled every `measure` row out of `data/real_world_eval_report.json`
   for the currently-live (round-1) model. All 4 real-world misses on the
   13-row holdout (`rw_009`, `rw_012`, `rw_021`, `rw_027`) come back
   `status: missing` -- the CRF never opens a span at all, so this isn't a
   T5/normalization issue. All 4 share one shape: the measure noun phrase
   sits in **subject position**, either right after a possessive company
   name (`"PNC's operating target for its CET1 capital ratio is..."`,
   `"FactSet's organic ASV growth was..."`) or after `"expects"`
   (`"FIS expects free cash flow to double..."`). Checked
   `choice_forge_dataset_combined_130.json` directly: across 57 explicit
   `measure` training examples, **zero** use the possessive-subject
   pattern and only **one** uses `"expects <measure>"` -- not enough for
   the CRF to generalize even to a near-identical real query
   (`rw_012`/`rw_021` both miss despite closely matching that one
   example). Every correctly-detected real-world `measure` matches a
   pattern the training data has plenty of instead: object-of-verb
   (`"targets consolidated leverage"`) or trailing `"of X in/of ___"`
   clauses. This is a genuine data-coverage gap for one specific
   syntactic frame -- not a model-capacity or hyperparameter problem, so
   another blind retrain sweep won't fix it (see the two failed attempts
   directly above). ~~**Recommended next step:** a small, targeted sourcing
   pass of real possessive-subject and "expects X" measure examples
   (5-10 rows), same build -> validate -> split pattern as always, then
   retrain + re-gate -- not a broader/repeated sweep.~~ **Done 2026-08-08:**
   sourced 7 rows (`rw_044`-`rw_050`) hitting exactly these two shapes,
   retrained, gated. Measure status 66.67%→73.33%, value 44.44%→55.56%;
   both held-out generalization-test rows now correctly detect measure in
   subject position. See the 2026-08-08 Current-status entry for full
   detail, including the `time`-field regression this pass introduced
   (new gap 7 below).
2. ~~Negation-cue phrasing may not exist in real corporate language.~~
   **Corrected 2026-08-05: it does exist, the original 7-company search just
   didn't find it.** A broader search turned up real "without X" constraints
   at Trane Technologies, FactSet, EFC, Tesla, and Climb Global (5 companies,
   5 different phrasings: "without increasing costs", "without adding
   headcount", "without sacrificing range/performance", etc.) — see
   `rw_036`/`rw_039`-`rw_042` in `data/build_real_world_pilot.py`. So
   `polarity_guard.py`'s negation pattern is grounded in real usage after
   all. What's still genuinely unresolved: whether the *model* can reliably
   learn this pattern — see the 2026-08-05 status entry below for a direct
   test (one training example taught the CRF nothing; 5 examples got
   detection working but regressed other fields in aggregate — this needs
   more/better-balanced data, not just more of the same single pattern).
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
6. **No actor↔intent pairing across multiple spans (raised 2026-08-05,
   detection built same day — see status entry below).** `pipeline.py`
   already flags a role with more than one surviving span via
   `multi_span: bool` (`decode_bio_multi`), and `prompt_synthesis.py`
   forces any `multi_span` role into `needs_review` — but that alone is
   per-role only and doesn't link *which* actor goes with *which* intent.
   **What's built:** `prompt_synthesis.py`'s `detect_possible_compound_query()`
   flags when 2+ of `{actor, intent, object}` are independently `multi_span`
   at once (the signal that a query bundles more than one decision), and
   `app.py` surfaces this as a warning banner + an explicit "this is
   actually more than one decision" checkbox in the confirm form, logged
   via `correction_log.py` (`possible_compound_query_flagged`/`_confirmed`)
   as training signal for calibrating the detector later. Verified live:
   `detect_possible_compound_query` unit-tested directly (2+ roles
   triggers, 1 role or excluded roles like scope+magnitude correctly
   don't), and end-to-end in a running Streamlit session with
   "Target wants to increase market share and PNC wants to reduce costs
   this year." (real actor/intent multi_span from the live model) —
   confirmed the banner, checkbox, and logged entry all fire correctly.
   **What's still open, by design (not a punt, a real unscoped decision):**
   this only *detects and asks* — per the reasoning-integrity philosophy,
   a compound query is arguably two decisions, and surfacing that is
   itself a clarifying question, not a defect to paper over silently. It
   does NOT auto-split into separate pipeline runs. If confirmed as
   multiple decisions, each would still need to become its own Step 1 run
   (separate master prompt / separate confirm-reject cycle) — building
   that is the next piece, intersecting with Phase 1 template design and
   possibly Phase 5 training data shape. Also note: the detector's actual
   trigger rate is bounded by the CRF's own multi-span detection maturity
   (Known gap 0) — a real compound query the CRF only finds one span for
   (as happened with "Marketing... while Sales..." in live testing, where
   the CRF missed "Sales" as a second actor entirely) won't trigger the
   warning. This isn't a bug in the detector; it inherits the underlying
   data-thinness gap.
7. **`time` still under-detects on the live (round 4) model — 66.67%
   status on the 15-row holdout, below the pre-regression 73.33%
   baseline.** `rw_044` (round 3's target) is fixed; `rw_012`/`rw_016`/
   `rw_017` are not, and root-caused precisely by the 2026-08-08
   continuation session (see Current status above) to **two distinct CRF
   span-boundary bugs**, not a single shared-capacity effect: (1)
   `magnitude` swallows a leading `"by <year>"` time clause whole when it
   directly precedes a dollar figure (`rw_012`: `"by 2028 to more than $3
   billion"` predicted as one `magnitude` span) — the mirror-image of the
   trailing-clause bug round 3 already fixed for `rw_044`/`rw_049`; (2)
   `object` swallows a leading bare time-adjective with no preposition
   directly before its noun (`rw_016`: `"third quarter common stock
   dividend"`; `rw_017`: `object` hallucinates `"full-year guidance"`
   entirely, gold is `missing` there). Fixing an analogous `measure`-role
   annotation bug in `rw_050` (see Current status) did NOT fix either —
   confirmed empirically via retrain+eval before assuming it would — so
   this needs its own **object-role and magnitude-role** training
   signal, not just measure-role. **Sourcing attempt already made and
   came up empty**, not just unattempted: 8 real-earnings-call searches +
   3 full-transcript fetches found no usable non-eval-overlapping real
   example of a bare time-adjective directly modifying an object-type
   noun — the one real recurring match, `"quarterly dividend"`, is a
   *frequency* adjective, not a *time-point* one, and doesn't fit this
   field's semantics even if forced in. Next session should either widen
   the source corpus beyond earnings calls (shareholder letters, press
   releases, a different sourcing domain entirely) or accept this as a
   real long-tail gap and prioritize elsewhere — forcing a weak/ambiguous
   annotation to close it would repeat the exact mistake `rw_050`'s bug
   just came from. **2026-08-10 update: real examples found, but the
   retrain that included them wasn't promoted.** Widening past earnings
   calls wasn't even needed — 2 real "declared a third quarter dividend"
   quotes (Imperial Oil, Employers Holdings; `rw_055`/`rw_056`) turned up
   in a differently-worded search, the exact bare-time-adjective pattern.
   Sourced, validated, and retrained alongside 3 gap-8 rows in the same
   batch — the `rw_016` `time` false-negative this gap was diagnosed from
   is now genuinely fixed on that retrain (`"third quarter"` correctly
   detected). But the retrain wasn't promoted (see Current status,
   2026-08-10): it regressed the already-fixed Known gap 1 (measure
   subject-position) on `rw_012`/`rw_044`, a net-negative trade overall.
   The data and the row-level fix are real; they're just sitting in a
   non-promoted retrain in the session scratchpad rather than live. Next
   session should retry with `rw_055`/`rw_056` isolated from the gap-8
   rows (or paired with a reinforcing measure-pattern example) rather
   than assuming this combination will work again.
8. **T5 can silently alter the literal digits of a `magnitude` value, not
   just paraphrase it — found 2026-08-09 via the confidence-calibration
   re-audit** (see Current status above, `data/check_confidence_calibration.py`).
   `rw_027`: gold `["7.0%", "10.0%", "5.0%"]` came back as `["7.2%",
   "100%", "5.10%"]` at 0.556 confidence — above the 0.4 blank threshold,
   so this renders as confident, unflagged fact in the product UI. The
   `"10.0%"→"100%"` case is a dropped-decimal-point, 10x factual error,
   not a cosmetic paraphrase difference (unlike the false-alarm cases the
   same audit also surfaced, e.g. `"about"`→`"approximately"`). This is
   more severe than the existing `intent`-hallucination gap because
   numbers read as precise and are the value type a user is least likely
   to sanity-check by eye. **Root-caused precisely, same session**: ran
   `Pipeline.extract()` directly and confirmed the CRF's raw spans are
   perfect (`'7.0%'`, `'10.0%'`, `'5.0%'`, 0.637-0.856 open confidence)
   — the corruption is 100% in `Pipeline.synthesize()`'s T5 call. Called
   `pipe.synthesize("magnitude", ...)` directly: each value normalizes
   correctly alone (`'7.0%'→'7.0%'`, `'10.0%'→'10.0%'`,
   `'5.0%'→'5.0%'`, all high confidence), but the exact joined input
   `pipeline.py` actually sends (`"7.0%; 10.0%; 5.0%"`, `; `-joined
   per-multi-span handling) comes back as `"['7.2%', '100%',
   '5.10%']"` — confirming T5 is the sole culprit, not the CRF. Checked
   `data/seq2seq_pairs.jsonl` directly: T5 **was** trained on
   `;`-joined multi-value `magnitude` inputs (21 pairs), so the
   list-string output format itself isn't the problem — but **every one
   of those 21 pairs is a 2-value join**; zero are 3-way joins.
   `rw_027` is a 3-way join, the first one T5-small has ever had to
   produce at inference time, and it hallucinated digits rather than
   reproducing them faithfully — the same "reinforced pattern doesn't
   generalize to an unseen shape" mechanism as the `measure`/`time`
   fixes above, just found in T5 training data instead of CRF training
   data. **Partially fixed 2026-08-09 (round 5)** — sourced one real
   3-way example (`rw_051`, F5's Americas/EMEA/APAC revenue split),
   retrained, gated net-positive (see Current status above). But checking
   the raw prediction directly (not just the eval script's summary
   number, which has its own scoring blind spot on multi-value fields —
   see Current status) shows the fix is real but incomplete:
   **whole-number percentage 3-way joins are now clean**
   (`"14%; 6%; 21%"` → exact), **decimal percentage joins still lose
   precision** (`"2.5%; 18.5%; 9.5%"` → `18.5%` silently becomes `18%`),
   and `rw_027` itself, re-run directly, still corrupts 2 of 3 values
   (`7.0%`/`10.0%` → `7.20%`/`10.10%`) — smaller formatting-level errors
   now, not the original 10x `"10.0%"→"100%"` distortion, but still
   wrong. **One example taught the 3-way-join shape but not
   decimal-precision preservation within it** — the same "one example
   isn't enough to generalize" lesson this project already learned for
   the negation-cue constraint gap (2026-08-05), recurring here for T5
   instead of the CRF. **Next step, still open**: source 2-3 more
   diverse 3-way (and ideally 4-way) `magnitude` examples specifically
   covering decimal percentages and dollar amounts, not just
   whole-number percentages like `rw_051`. **2026-08-10 update: the
   `eval_on_real_world.py` scoring fix flagged above is done** — it now
   requires every gold element to match some individually-parsed
   predicted item, not just any single one anywhere in the joined
   string — and re-running it against the (still-live, round 5) model
   revealed the gap is bigger than previously understood: it's not just
   3-way percentage joins, it's **any joined multi-value magnitude
   touching a decimal dollar-per-share amount**, 2-way included.
   `rw_016` (already in the frozen holdout) was the proof: `$0.50`→`$50`,
   a 100x digit-corruption error at 0.465 confidence, previously scored
   as correct by the old buggy scorer. Direct `pipe.synthesize()` tests
   confirmed the pattern generalizes across decimal shapes — `$0.75`
   comes back as garbled `"$100, '$100,'"`, `$1.25` as `$1,25` — all at
   0.85-0.98 confidence, so this renders as *more* confidently wrong
   than the original 3-way-join finding, not less. 3 new real dividend
   examples sourced (`rw_052`-`rw_054`, see Current status) targeting 3
   different decimal-precision shapes, retrained alongside the 2 gap-7
   rows above — genuinely fixed `rw_016`'s magnitude exactly on that
   retrain, but the retrain wasn't promoted for unrelated reasons (see
   Current status). **Still open**: retry this sourcing with the batch
   isolated from the gap-7 rows to see if the fix holds without the
   gap-1 regression; the training data itself is sound and doesn't need
   to be resourced.

Full detail and reasoning for all of the above lives in git history — see
commit `db3e52e`'s message specifically.
