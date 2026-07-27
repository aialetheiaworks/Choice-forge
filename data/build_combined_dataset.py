"""
Regenerates choice_forge_dataset_combined_120.json (or whatever the current
combined training set should be named) from its source pieces:

  choice_forge_dataset_full_100_v2.json   (original, LLM-generated, immutable)
+ data/real_world_training_augment.json   (real, source-verified, grows over time)
= choice_forge_dataset_combined_<N>.json

Run this instead of hand-building the combined file with a one-off script --
that's how choice_forge_dataset_combined_120.json was first created and it
wasn't reproducible. Whenever real_world_training_augment.json grows, rerun
this, then rerun train_crf.py / build_seq2seq_pairs.py / train_seq2seq.py
against the new combined file, then rerun data/eval_on_real_world.py to
measure the effect against the frozen holdout.

Run:
    python3 data/build_combined_dataset.py
"""

import json

ORIGINAL = "choice_forge_dataset_full_100_v2.json"
REAL_AUGMENT = "data/real_world_training_augment.json"


def main():
    with open(ORIGINAL, encoding="utf-8") as f:
        original = json.load(f)
    with open(REAL_AUGMENT, encoding="utf-8") as f:
        real = json.load(f)

    combined = original + real
    out_path = f"choice_forge_dataset_combined_{len(combined)}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"{len(original)} original + {len(real)} real = {len(combined)} rows -> {out_path}")
    print("Now run, in order:")
    print(f"  python3 train_crf.py {out_path}")
    print(f"  python3 build_seq2seq_pairs.py {out_path}")
    print("  python3 train_seq2seq.py")
    print("  python3 data/eval_on_real_world.py")


if __name__ == "__main__":
    main()
