"""
Splits data/real_world_pilot_batch.json into a permanent eval holdout and a
training-augmentation set.

Split is stratified by hand, not random: rare roles (scope: 4 rows total,
constraints: 4 rows total) are split roughly evenly between the two sets so
neither pool is blind to those patterns, and the remaining rows are chosen to
keep both sets diverse across the 7 source companies rather than clumping.

EVAL_IDS must never be added to training data -- that's the whole point of
having a real (not LLM-generated), permanently-frozen benchmark. See
ABOUT.md / chat history for why this project didn't have one until now.
"""

import json

EVAL_IDS = {
    "rw_016", "rw_021", "rw_027", "rw_029",  # rare-role picks (constraints x2, scope x2)
    "rw_003", "rw_009", "rw_012", "rw_017", "rw_020", "rw_022",  # diverse source/density picks
    # 2026-08-05 sourcing pass (rw_031-rw_038, see build_real_world_pilot.py):
    # rw_034 (scope via programs + causal context) and rw_035 (constraints via
    # delayed timeline, not "subject to" phrasing) picked for eval to keep rare
    # roles diverse there too. rw_036 (the "without increasing" negation-cue
    # constraint) deliberately kept in TRAIN instead -- it's the only example
    # of that pattern in the whole dataset, so putting it in eval-only would
    # guarantee a miss with no chance for the model to ever learn it.
    "rw_034", "rw_035",
    # rw_041 (Tesla "without sacrificing...") held out to actually test
    # whether 4 training examples of the negation-cue constraint pattern
    # (rw_036, rw_039, rw_040, rw_042) taught the CRF something rw_036
    # alone did not.
    "rw_041",
    # 2026-08-08 sourcing pass targeting the measure subject-position blind
    # spot (Known gap 1): rw_044 (TMO, "expects X" pattern) and rw_049
    # (DexCom, possessive-subject pattern) held out to test whether the 5
    # training examples of these two shapes (rw_045-rw_048, rw_050) taught
    # the CRF to open a measure span in subject position at all.
    "rw_044", "rw_049",
    # 2026-08-12 sourcing pass targeting Known gap 9 (actor misrouted into
    # time on "by <X>" phrases): rw_061 (BP, "a search committee of the
    # Board") held out to test whether the 4 training examples
    # (rw_057-rw_060, all "by <named person>") generalize to an
    # organizational-noun actor, not just a repeat of the trained shape.
    "rw_061",
}

with open("data/real_world_pilot_batch.json", encoding="utf-8") as f:
    rows = json.load(f)

eval_rows = [r for r in rows if r["id"] in EVAL_IDS]
train_rows = [r for r in rows if r["id"] not in EVAL_IDS]

assert len(eval_rows) == len(EVAL_IDS), "some EVAL_IDS didn't match any row"

with open("data/real_world_eval_holdout.json", "w", encoding="utf-8") as f:
    json.dump(eval_rows, f, indent=2, ensure_ascii=False)

with open("data/real_world_training_augment.json", "w", encoding="utf-8") as f:
    json.dump(train_rows, f, indent=2, ensure_ascii=False)

print(f"Eval holdout:  {len(eval_rows)} rows -> data/real_world_eval_holdout.json (NEVER train on this)")
print(f"Train augment: {len(train_rows)} rows -> data/real_world_training_augment.json")
