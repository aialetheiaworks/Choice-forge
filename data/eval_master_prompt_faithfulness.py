"""
Phase C check for TOOLTIP_INTEGRATION_PLAN.md: does the LLM master-prompt
assembly (master_prompt_llm.generate_master_prompt) ever introduce a
*specific* -- a number, percent, money amount, or year -- that is not
present in either the original query or the confirmed field values?

The whole safety premise of the pivot is that the LLM only rephrases
already-vetted data (CLAUDE.md: "never assume a value for an empty
field"). A fabricated specific is the failure mode that would break it,
and specifics are exactly the thing a reader is least likely to
double-check. This script does NOT judge wording quality -- only whether a
hard specific in the output can be traced back to the inputs.

Runs each query through the real pipeline, builds the fields the way
app.py's "confirm as-is" path does (no user edits -- the pipeline output
is the confirmed set), assembles the master prompt, and diffs the
specifics.

Run:
    python3 data/eval_master_prompt_faithfulness.py
Needs a working LLM_PROVIDER (see API_KEYS.md) -- it makes one real call
per query.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline import Pipeline, ROLES  # noqa: E402
from prompt_synthesis import build_fields  # noqa: E402
import master_prompt_llm  # noqa: E402

# A spread of shapes: multi-field, sparse, compound, negation-cue, and a
# few real holdout queries with dense numbers.
QUERIES = [
    "Cut support ticket backlog by 40% for enterprise accounts within the next sprint.",
    "Marketing wants to grow trial-to-paid conversion for self-serve signups from 8% to 15% before the holiday season, without increasing the ad spend budget.",
    "Our field sales team needs to onboard 1,200 kirana stores in Pune onto the B2B ordering app by the end of Q3, using only the existing incentive budget.",
    "Acme Corp wants to expand into three new markets by Q3 without exceeding the current marketing budget.",
    "Reduce operating costs by 10% without letting service quality slip below current levels.",
    "We want to increase market share in the northeast region by 8 points next fiscal year while keeping customer acquisition cost flat.",
    "Improve onboarding.",
    "The supply chain team will consolidate our vendor base in North America.",
    "Target added around 1,500 new items and plans to refresh around 40% of its wellness assortment this year.",
    "PNC's operating target for its CET1 capital ratio is 10% over the next several quarters.",
    "Reduce churn unless it requires cutting the support team.",
    "Get night-shift warehouse picking errors from 15 per 1000 down to under 5 by Q4 at the Ohio DC, no overtime budget, because the Q3 audit flagged accuracy.",
]

# Numbers, percentages, money amounts, and 4-digit years. Deliberately
# narrow -- these are unambiguous and exactly-checkable, unlike proper
# nouns (which the pipeline paraphrases legitimately).
SPECIFIC_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?")


def specifics(text):
    return {m.group(0).strip(".,").lower() for m in SPECIFIC_RE.finditer(text or "")}


def normalise(tok):
    """A specific counts as 'present' if it appears verbatim, or as the
    bare digits (so '40%' in the output is covered by '40' in the source
    and vice versa, and '1,200' matches '1200')."""
    bare = tok.replace("$", "").replace("%", "").replace(",", "")
    return {tok, bare}


def main():
    pipe = Pipeline()
    total_flags = 0
    for q in QUERIES:
        result = pipe.run(q)
        fields = build_fields(result)
        # "confirm as-is": text is the pipeline value (or blank placeholder)
        final_fields = {
            r: {"text": fields[r]["text"], "blank": fields[r]["blank"],
                "not_applicable": False}
            for r in ROLES
        }
        prompt, err = master_prompt_llm.generate_master_prompt(q, final_fields)
        print("=" * 88)
        print("QUERY  :", q)
        if err:
            print("  !! LLM error:", err)
            continue
        print("PROMPT :", prompt)

        source_blob = q + " " + " ".join(
            final_fields[r]["text"] for r in ROLES if not final_fields[r]["blank"]
        )
        source_specifics = set()
        for s in specifics(source_blob):
            source_specifics |= normalise(s)

        unbacked = [
            s for s in specifics(prompt)
            if not (normalise(s) & source_specifics)
        ]
        if unbacked:
            total_flags += 1
            print("  ⚠ SPECIFICS NOT FOUND IN INPUTS:", unbacked)
        else:
            print("  ✓ every specific traces back to the query or a field")

    print("=" * 88)
    print(f"\n{total_flags} / {len(QUERIES)} queries had an unbacked specific.")
    print("Any flag needs a human look -- some are false alarms (e.g. '5' inside "
          "'5%' vs a bare '5'), but a genuine invented number means the system "
          "prompt needs tightening or the template fallback is safer.")
    sys.exit(1 if total_flags else 0)


if __name__ == "__main__":
    main()
