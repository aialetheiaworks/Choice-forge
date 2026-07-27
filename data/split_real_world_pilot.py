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
