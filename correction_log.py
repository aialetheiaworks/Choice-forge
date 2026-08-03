"""
Phase 3 of the CHOICE product vision (see CLAUDE.md "Agreed build order"):
append-only log of every confirm/reject decision from app.py's master-prompt
review step. One JSON object per line, in the same convention as
data/seq2seq_pairs.jsonl. This is the training data Phase 5 retrains the
prompt-synthesis model on.
"""

import json
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), "data", "corrections_log.jsonl")


def log_correction(entry):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
