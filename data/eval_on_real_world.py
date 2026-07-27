"""
Runs the current pipeline (spaCy -> CRF -> T5 -> polarity_guard, whatever is
currently saved as role_tagger.joblib / value_synthesizer/) against
data/real_world_eval_holdout.json and scores it field-by-field against the
hand-labeled, source-verified gold.

This is the first time this project has been measured against real
(non-LLM-generated) text end-to-end -- see chat history for why that
mattered enough to build this before any retraining decision.

Scoring, per field, per row:
  - status_correct: does "found something" vs "missing" match gold?
  - value_correct: only scored when gold status != missing. Loose match --
    exact (case-insensitive) OR one string contains the other. This is a
    coarse proxy, not exact-match paraphrase scoring (T5's job is
    paraphrase, so exact string match would be too strict) -- flagged
    clearly in the output as approximate.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline import Pipeline, ROLES


def norm(s):
    return str(s).strip().lower() if s is not None else ""


def loose_value_match(pred, gold):
    p, g = norm(pred), norm(gold)
    if not p or not g:
        return False
    return p == g or p in g or g in p


def main():
    with open("data/real_world_eval_holdout.json", encoding="utf-8") as f:
        rows = json.load(f)

    pipe = Pipeline()

    field_stats = {r: {"status_correct": 0, "value_correct": 0, "gold_present": 0, "total": 0}
                   for r in ROLES}
    row_reports = []

    for row in rows:
        pred = pipe.run(row["input_query"])
        report = {"id": row["id"], "query": row["input_query"], "fields": {}}
        for role in ROLES:
            gold = row["choice"][role]
            p = pred[role]
            field_stats[role]["total"] += 1

            gold_missing = gold["status"] == "missing"
            pred_missing = p["status"] == "missing" or p["value"] is None
            status_correct = gold_missing == pred_missing
            field_stats[role]["status_correct"] += int(status_correct)

            value_correct = None
            if not gold_missing:
                field_stats[role]["gold_present"] += 1
                gold_val = gold["value"]
                gold_vals = gold_val if isinstance(gold_val, list) else [gold_val]
                value_correct = any(loose_value_match(p["value"], gv) for gv in gold_vals) if not pred_missing else False
                field_stats[role]["value_correct"] += int(value_correct)

            report["fields"][role] = {
                "gold_value": gold["value"], "gold_status": gold["status"],
                "pred_value": p["value"], "pred_status": p["status"], "pred_conf": p["confidence"],
                "status_correct": status_correct, "value_correct": value_correct,
                "flagged": p["flagged_for_review"],
            }
        row_reports.append(report)
        print(f"scored {row['id']}", file=sys.stderr)

    print("\n=== Per-field results (over {} real, held-out rows) ===".format(len(rows)))
    print(f"{'field':12s} | status_acc | value_acc (of {{gold present}}) | gold_present")
    print("-" * 70)
    overall_status = overall_value = overall_gold_present = overall_total = 0
    for role in ROLES:
        s = field_stats[role]
        status_acc = s["status_correct"] / s["total"]
        value_acc = (s["value_correct"] / s["gold_present"]) if s["gold_present"] else float("nan")
        print(f"{role:12s} | {status_acc:9.2%}  | {value_acc if s['gold_present'] else 0:9.2%}"
              f"                | {s['gold_present']}/{s['total']}")
        overall_status += s["status_correct"]
        overall_value += s["value_correct"]
        overall_gold_present += s["gold_present"]
        overall_total += s["total"]
    print("-" * 70)
    print(f"{'OVERALL':12s} | {overall_status/overall_total:9.2%}  | "
          f"{overall_value/overall_gold_present:9.2%}                | {overall_gold_present}/{overall_total}")

    with open("data/real_world_eval_report.json", "w", encoding="utf-8") as f:
        json.dump(row_reports, f, indent=2, ensure_ascii=False)
    print("\nFull per-row, per-field detail written to data/real_world_eval_report.json")


if __name__ == "__main__":
    main()
