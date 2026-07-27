"""
Validates data/real_world_pilot_batch.json against the same constraint
train_crf.py relies on: every source_text must be an exact (case-insensitive)
substring of input_query, and no two roles may claim overlapping character
spans (overlap silently drops the later role during BIO tagging -- see
row_to_bio in train_crf.py).
"""

import json

ROLES = ["actor", "object", "intent", "scope", "measure",
         "magnitude", "time", "constraints", "context"]


def as_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return [str(s) for s in x]
    return [str(x)]


def find_all(query, needle):
    spans = []
    q, n = query.lower(), needle.lower().strip()
    if not n:
        return spans
    start = 0
    while True:
        idx = q.find(n, start)
        if idx == -1:
            break
        spans.append((idx, idx + len(n)))
        start = idx + len(n)
    return spans


def main():
    with open("data/real_world_pilot_batch.json", encoding="utf-8") as f:
        rows = json.load(f)

    errors = []
    for row in rows:
        query = row["input_query"]
        claimed = []  # (start, end, role, needle)
        for role in ROLES:
            info = row["choice"][role]
            if info["status"] == "missing":
                continue
            for needle in as_list(info["source_text"]):
                spans = find_all(query, needle)
                if not spans:
                    errors.append(f"{row['id']}: {role} source_text {needle!r} NOT FOUND in query")
                    continue
                # take first unclaimed occurrence, mirroring row_to_bio's greedy behavior
                placed = False
                for s, e in spans:
                    if not any(s < ce and cs < e for cs, ce, _, _ in claimed):
                        claimed.append((s, e, role, needle))
                        placed = True
                        break
                if not placed:
                    errors.append(
                        f"{row['id']}: {role} source_text {needle!r} OVERLAPS an "
                        f"already-claimed span -- would be silently dropped by row_to_bio"
                    )

    print(f"Checked {len(rows)} rows.")
    if errors:
        print(f"{len(errors)} problem(s):")
        for e in errors:
            print(" -", e)
    else:
        print("All source_text spans are valid substrings with no cross-role overlap.")


if __name__ == "__main__":
    main()
