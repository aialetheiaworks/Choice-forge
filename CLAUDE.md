# CHOICE Forge v1 — project status & plan

This file is maintained across sessions so any future conversation (with or
without persistent memory) can pick up exactly where the last one left off.
Update it whenever a session makes real progress — treat it as a living
status doc, not a one-time snapshot. See `README.md` for setup/usage and
`ABOUT.md` for the architecture rationale; this file is specifically about
*where things currently stand and what to do next*.

## What this project is

Turns a plain-English business ask into a structured 9-field object (actor,
object, intent, scope, measure, magnitude, time, constraints, context) for
Aletheia Works. Local pipeline: spaCy -> CRF (`role_tagger.joblib`) -> T5
(`value_synthesizer/`) -> `polarity_guard.py`. No external LLM calls at
inference time. See `ABOUT.md` for why it's split into layers this way.

**Important, non-obvious fact:** the original 100-row "gold" dataset
(`choice_forge_dataset_full_100_v2.json`) was itself LLM-generated, not real
business text. Until 2026-07-27, this project had never been measured
against real-world text at all.

## Current state (as of 2026-07-27, commit `db3e52e`)

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
   real eval set below doesn't contain that sentence shape yet, so the fix
   is verified but doesn't move the tracked eval number.

3. **Built a real-data pipeline from scratch** (project had zero real ground
   truth before this). Sourced 30 hand-labeled rows from real public
   earnings-call transcripts and shareholder letters (Target, PNC, FIS,
   Wells Fargo, D.R. Horton, Citizens Financial, Buffer), each with a
   `_source_url` and independently fact-checked against the live source.
   - `data/build_real_world_pilot.py` — constructs the rows
   - `data/validate_real_world_pilot.py` — checks source_text substring
     correctness + no cross-role span overlap, against the *actual*
     `row_to_bio` training function (not a reimplementation)
   - `data/split_real_world_pilot.py` — stratified split
   - `data/eval_on_real_world.py` — end-to-end field-level scoring harness

4. **Split into a permanent eval holdout + training augmentation:**
   - `data/real_world_eval_holdout.json` — 10 rows. **NEVER train on this.**
     It's the only frozen, trustworthy real benchmark this project has.
   - `data/real_world_training_augment.json` — 20 rows, merged into training.

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

1. **`measure`, `scope`, `context` roles still thin**, even in the real
   30-row batch (scope: 4 rows total). Need more real sourcing targeted
   specifically at these.
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
   join-coherence fix (item 2 above, in "what happened") is verified on a
   hand-written example but not reflected in the tracked eval score.
5. **Longer-term, agreed direction: self-learning correction flywheel.**
   Capture stakeholder corrections via `app.py`, prioritize review by model
   confidence (active learning), periodically retrain and gate every new
   model against the frozen real eval set before promoting it. Not yet
   built — this is the "make it self-learning" goal the user asked about.

## Rules for continuing this work

- **Never train on `data/real_world_eval_holdout.json`.** It's the only
  frozen, real benchmark. If it gets contaminated, there is no way to
  honestly measure real-world quality anymore.
- **Always re-run `python3 data/eval_on_real_world.py` after any retrain**
  and compare against the numbers in the table above before claiming
  improvement. Don't trust a retrain "feels better" — measure it.
- When sourcing more real data, reuse the same
  build -> validate -> split pattern (see the four `data/*.py` scripts
  above) rather than hand-writing JSON rows directly — the validator has
  already caught real mistakes (overlapping spans, mismatched source_text)
  that would otherwise silently corrupt training.
- Full detail and reasoning for all of the above lives in the git history —
  see `git log` and specifically commit `db3e52e`'s message.
