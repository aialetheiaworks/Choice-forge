"""
Build data/seq2seq_pairs.jsonl from choice_forge_dataset_full_100_v2.json for
train_seq2seq.py. One pair per non-missing role instance; multi-span
source_text lists are joined with "; " into a single input string.
"""

import json
import os
import sys

SRC = "choice_forge_dataset_full_100_v2.json"
OUT = "data/seq2seq_pairs.jsonl"

ROLES = ["actor", "object", "intent", "scope", "measure",
         "magnitude", "time", "constraints", "context"]


def source_text_str(source_text):
    if isinstance(source_text, list):
        return "; ".join(str(s) for s in source_text)
    return str(source_text)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    with open(src, encoding="utf-8") as f:
        rows = json.load(f)

    os.makedirs("data", exist_ok=True)
    n = 0
    with open(OUT, "w", encoding="utf-8") as out:
        for row in rows:
            for role in ROLES:
                info = row["choice"][role]
                if info["status"] == "missing":
                    continue
                pair = {
                    "id": row["id"],
                    "role": role,
                    "input": f"normalize {role}: {source_text_str(info['source_text'])}",
                    "target": str(info["value"]),
                    "gold_status": info["status"],
                }
                out.write(json.dumps(pair) + "\n")
                n += 1
    print(f"Wrote {n} pairs to {OUT}")


if __name__ == "__main__":
    main()
