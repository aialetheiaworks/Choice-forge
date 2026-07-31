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
| `app.py` | Streamlit stakeholder UI — the planned home for the self-learning correction-capture flow (not built yet, see gaps below). |

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

## Product vision — the full workflow (agreed 2026-07-29)

CHOICE Forge (everything documented above) is layer 1 of a larger product,
not the end product itself. Full intended workflow:

1. User inputs a raw business query.
2. CHOICE Forge extracts it into structured buckets (actor, intent, measure,
   scope, context, etc.) — this is the pipeline that exists today.
3. A **prompt-synthesis layer** (not built yet) takes the query + its
   buckets and generates a **master prompt** — a well-formed, business-grade
   prompt scaffold, not just a template dump of the fields.
4. **Never assume a value for an empty or low-confidence bucket.** Any field
   the pipeline didn't fill, or filled with low confidence, becomes an
   explicit blank in the master prompt text rather than a guess. This should
   reuse the pipeline's existing confidence signals (e.g.
   `MIN_JOIN_OPEN_CONFIDENCE` in `pipeline.py`) as the "blank this field"
   trigger — but see Phase 2 below, that requires a calibration check first.
5. The user sees the full master prompt, blanks and all: fills in the
   blanks, and reads through the rest of the prompt. This does two jobs at
   once — real missing data comes from the user instead of being assumed,
   and the user reading the whole prompt is their implicit confirmation
   that the system understood the original query correctly.
6. If the user continues, the prompt is confirmed correct and complete. If
   not, a fallback path is needed: curate/regenerate an alternate prompt, or
   diagnose where understanding went wrong before retrying. This
   accept/reject signal is exactly the correction-capture data the
   self-learning flywheel (gap 5 below) needs.
7. Once confirmed, the completed master prompt is sent via API to an LLM to
   produce the actual best-quality output for the user's original query.

**Agreed build order (not started yet):**
- **Phase 1** — build the prompt-synthesis step as a deterministic
  *template*, not a trained model. There is no dataset yet of
  (buckets → ideal master prompt) pairs to train on, so a model isn't
  feasible yet. Wire blank-insertion to the existing per-field confidence
  scores.
- **Phase 2** — audit whether those confidence scores are actually
  calibrated (low confidence ⇔ actually wrong/missing), using the same
  eval-harness discipline as `data/eval_on_real_world.py`. This is the
  linchpin of the whole safety design: if confidence is miscalibrated, a
  wrong field slips through as a confident answer instead of getting
  blanked, and the "never assume" guarantee breaks silently.
- **Phase 3** — build the fill-in-blank + confirm/reject UI in `app.py`, and
  log every accept/reject and every user-filled blank. This log is what
  both measures how often the system gets it right *and* is the training
  data needed for Phase 5 — do not train a prompt-synthesis model before
  this data exists.
- **Phase 4** — wire the final LLM API call (default to Claude via the
  Anthropic API for this) on the confirmed master prompt.
- **Phase 5** (later) — once accept/reject + fill logs accumulate, train
  the real prompt-synthesis model on them, replacing the Phase 1 template.
  Gate any new version against a frozen holdout, the same way model
  promotion already works for the extraction layer.
- **Retraining is always batched, never per-query.** Log every correction
  as it comes in, but only retrain on a count/time trigger (e.g. every
  20-30 new rows, or weekly), then gate before promoting. Neither the CRF
  (no incremental-fit mode) nor a per-query eval-gate cost makes retrain-
  per-correction workable — this applies to the extraction layer today and
  will apply to the prompt-synthesis model in Phase 5 too.

## Current status (as of 2026-07-29 — planning + calibration audit session)

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
