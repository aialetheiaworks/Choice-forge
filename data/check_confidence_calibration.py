"""
Re-runs the Phase 2 confidence-calibration audit (2026-07-29) against the
CURRENT model's data/real_world_eval_report.json, instead of trusting that
audit's one-time result forever.

Phase 1's entire "never assume a value for an empty field" design rests on
one claim: confidence separates right from wrong for every field except
`intent`, so it's safe to trust any non-blank (confidence >=
pipeline.MIN_JOIN_OPEN_CONFIDENCE) prediction at face value. That claim was
checked once, on the round-1 model against a 10-row holdout, and never
re-checked across the ~5 retrains since. Run this after every retrain,
alongside data/eval_on_real_world.py, to catch calibration drift before it
silently erodes the safety guarantee.

The dangerous case this looks for: a WRONG prediction whose confidence is
>= the blank threshold -- prompt_synthesis.py won't blank it, so the user
sees it rendered as confident fact.

Run:
    python3 data/eval_on_real_world.py   # regenerates the report first
    python3 data/check_confidence_calibration.py
"""

import json
import sys

sys.path.insert(0, ".")
from pipeline import MIN_JOIN_OPEN_CONFIDENCE

ROLES = ["actor", "object", "intent", "scope", "measure",
         "magnitude", "time", "constraints", "context"]


def main():
    with open("data/real_world_eval_report.json", encoding="utf-8") as f:
        report = json.load(f)

    print(f"Blank threshold: confidence < {MIN_JOIN_OPEN_CONFIDENCE} gets blanked "
          f"(prompt_synthesis.MIN_JOIN_OPEN_CONFIDENCE)\n")
    print(f"{'field':12s} | {'n':>3s} | {'correct':>7s} | {'wrong':>5s} | "
          f"{'wrong >= threshold (shown as fact, actually wrong)':s}")
    print("-" * 90)

    any_dangerous = False
    for role in ROLES:
        correct_confs, wrong_confs = [], []
        for row in report:
            f = row["fields"][role]
            if f["pred_status"] == "missing":
                continue
            if f["value_correct"] is True:
                correct_confs.append(f["pred_conf"])
            elif f["value_correct"] is False:
                wrong_confs.append((row["id"], f["pred_conf"], f["pred_value"], f["gold_value"]))

        n = len(correct_confs) + len(wrong_confs)
        if n == 0:
            continue
        dangerous = [(rid, c, p, g) for rid, c, p, g in wrong_confs if c >= MIN_JOIN_OPEN_CONFIDENCE]
        flag = f"{len(dangerous)} row(s): " + ", ".join(f"{rid}@{c:.3f}" for rid, c, _, _ in dangerous) if dangerous else "none"
        print(f"{role:12s} | {n:3d} | {len(correct_confs):7d} | {len(wrong_confs):5d} | {flag}")
        if dangerous:
            any_dangerous = True
            for rid, c, pred_val, gold_val in dangerous:
                print(f"             -> {rid}: pred={pred_val!r} (conf {c:.3f}) but gold={gold_val!r}")

    print()
    if any_dangerous:
        print("CALIBRATION DRIFT DETECTED: at least one field has a wrong prediction at or "
              "above the blank threshold -- it renders as confident fact in the product UI. "
              "Do not treat 'not blanked' as 'trustworthy' for that field until re-audited "
              "against a larger sample or fixed.")
    else:
        print("No above-threshold wrong predictions found in this holdout -- consistent with "
              "the original Phase 2 audit's finding. Sample size is still small per field "
              "(see counts above); treat as directional, same caveat as the original audit.")


if __name__ == "__main__":
    main()
