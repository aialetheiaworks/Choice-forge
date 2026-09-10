"""
Regression gate for a retrained model, run after data/eval_on_real_world.py.

Why this exists: CRF retraining (train_crf.py, via sklearn-crfsuite) has no
warm-start / incremental-fit mode -- every retrain starts from scratch, so
there's no way to protect an already-working role the way --continual does
for T5 (see train_seq2seq.py). This project's history has repeatedly hit
the same failure mode: a retrain's AGGREGATE eval score looks fine or even
better, while it silently flips specific previously-correct rows to wrong
on an unrelated role (see CLAUDE.md Known gaps 1, 7, 9, and the 2026-09-10
session where a from-scratch retrain improved nothing and regressed
magnitude/constraints/context/scope all at once). Aggregate-score
comparison hides this. Row-by-row comparison catches it.

What it does: compares the just-produced data/real_world_eval_report.json
(the candidate) against the same file as committed at a baseline git ref
(default: HEAD, i.e. whatever's currently promoted) and flags any
(row, field, status_correct|value_correct) that flips from True to False.
Any such flip is a REGRESSION regardless of what happens to the aggregate
score, and the gate fails (exit 1) if there are any.

Run after retraining and re-running the eval harness:
    python3 data/eval_on_real_world.py
    python3 data/gate_retrain.py [--baseline-ref HEAD]
"""

import argparse
import json
import subprocess
import sys

REPORT_PATH = "data/real_world_eval_report.json"
FIELDS = ["actor", "object", "intent", "scope", "measure",
          "magnitude", "time", "constraints", "context"]
CHECKS = ["status_correct", "value_correct"]


def load_current():
    with open(REPORT_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_baseline(ref):
    out = subprocess.run(
        ["git", "show", f"{ref}:{REPORT_PATH}"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def index_by_id(rows):
    return {r["id"]: r for r in rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-ref", default="HEAD",
                     help="git ref to compare against (default: HEAD, i.e. currently committed/promoted)")
    args = ap.parse_args()

    try:
        baseline = index_by_id(load_baseline(args.baseline_ref))
    except subprocess.CalledProcessError:
        print(f"Could not read {REPORT_PATH} at {args.baseline_ref!r} -- nothing to gate against.")
        sys.exit(2)
    current = index_by_id(load_current())

    regressions, improvements = [], []
    for row_id, base_row in baseline.items():
        if row_id not in current:
            continue  # row dropped from holdout -- not this gate's job to judge
        base_fields = base_row.get("fields", {})
        cur_fields = current[row_id].get("fields", {})
        for role in FIELDS:
            bf, cf = base_fields.get(role, {}), cur_fields.get(role, {})
            for check in CHECKS:
                # value_correct is None when gold is "missing" -- skip, not a real signal
                if bf.get(check) is None or cf.get(check) is None:
                    continue
                if bf[check] is True and cf[check] is False:
                    regressions.append((row_id, role, check, bf.get("pred_value"), cf.get("pred_value")))
                elif bf[check] is False and cf[check] is True:
                    improvements.append((row_id, role, check))

    print(f"Compared {len(current)} rows against {args.baseline_ref} ({len(baseline)} rows in baseline).\n")

    if improvements:
        print(f"{len(improvements)} improvement(s):")
        for row_id, role, check in improvements:
            print(f"  + {row_id:8s} {role:12s} {check}")
        print()

    if regressions:
        print(f"{len(regressions)} REGRESSION(S) -- previously correct, now wrong:")
        for row_id, role, check, old_val, new_val in regressions:
            print(f"  - {row_id:8s} {role:12s} {check}: {old_val!r} -> {new_val!r}")
        print(f"\nFAIL: {len(regressions)} regression(s) found. Do not promote this model as-is --")
        print("either fix the specific rows above or don't overwrite the committed model/artifacts.")
        sys.exit(1)

    print("PASS: no row/field that was previously correct is now wrong.")
    print("(This does not mean the model is better overall -- only that it's not silently worse")
    print(" on anything that used to work. Still compare aggregate status_acc/value_acc by hand.)")
    sys.exit(0)


if __name__ == "__main__":
    main()
