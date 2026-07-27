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

## Current status (as of 2026-07-27, commit `db3e52e` + `e0b5782`)

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
   join-coherence fix (item 2 above) is verified on a hand-written example
   but not reflected in the tracked eval score.
5. **Longer-term, agreed direction: self-learning correction flywheel.**
   Capture stakeholder corrections via `app.py`, prioritize review by model
   confidence (active learning), periodically retrain and gate every new
   model against the frozen real eval set before promoting it. Not yet
   built — this is the "make it self-learning" goal the user asked about.

Full detail and reasoning for all of the above lives in git history — see
commit `db3e52e`'s message specifically.
