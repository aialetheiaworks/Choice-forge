"""
Fine-tune a small local T5 model to turn an extracted span into the
canonical `value` for a role -- the piece a CRF structurally cannot do.

Input file: data/seq2seq_pairs.jsonl (629 pairs, generated from all 655
non-missing role instances in choice_forge_dataset_full_100_v2.json --
some multi-span rows collapse to one joined string; see build note below).
Each line: {"id", "role", "input": "normalize <role>: <source_text>",
            "target": "<value>", "gold_status": "explicit"|"inferred"}

Why one pooled model instead of 9 separate per-role models:
  Some roles (actor: 25 examples, constraints: 38) are too thin on their
  own to fine-tune a seq2seq model reliably. Pooling all roles into one
  model with a role-prefix instruction ("normalize actor: ...", "normalize
  intent: ...") is standard T5-style multi-task conditioning -- the model
  shares general "clean up and canonicalize this span" ability across
  roles while the prefix tells it which normalization style to apply.

Honest expectation: 629 pairs is small for fine-tuning even a small
pretrained model. Expect it to do well on phrasing patterns close to what
it's seen and to need more data over time -- this is not a one-shot fix,
it's a model you keep improving as your labeled set grows, same as the CRF.

Install:
    pip3 install transformers torch sentencepiece accelerate

Run:
    python3 train_seq2seq.py
"""

import json
import random

from transformers import (
    T5Tokenizer, T5ForConditionalGeneration,
    Seq2SeqTrainer, Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq,
)
from datasets import Dataset

from polarity_guard import has_negation

MODEL_NAME = "t5-small"
PAIRS_PATH = "data/seq2seq_pairs.jsonl"
MODEL_OUT = "value_synthesizer"

# Only 23/655 role instances (3.5%) contain a negation cue, concentrated
# almost entirely in `constraints`. T5-small never saw enough of them to
# learn that "without increasing X" means the opposite of "increasing X" --
# see polarity_guard.py for the runtime symptom. Oversampling duplicates
# those examples in the TRAIN split only (never in val, so evaluation stays
# representative of real-world frequency, not artificially inflated).
NEGATION_OVERSAMPLE_FACTOR = 5


def load_pairs(path):
    pairs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            pairs.append(json.loads(line))
    return pairs


def tag_negation(pair):
    """Prepend an explicit marker when the input span contains a negation
    cue, so the model gets an unambiguous signal instead of having to infer
    negation implicitly from rare surface patterns."""
    if has_negation(pair["input"]):
        pair = dict(pair)
        pair["input"] = pair["input"].replace("normalize ", "normalize [NEGATED] ", 1)
    return pair


def main():
    pairs = [tag_negation(p) for p in load_pairs(PAIRS_PATH)]
    random.seed(42)
    random.shuffle(pairs)
    split = int(len(pairs) * 0.85)
    train_pairs, val_pairs = pairs[:split], pairs[split:]

    negation_pairs = [p for p in train_pairs if has_negation(p["input"])]
    train_pairs = train_pairs + negation_pairs * (NEGATION_OVERSAMPLE_FACTOR - 1)
    random.shuffle(train_pairs)
    print(f"train: {len(train_pairs)} pairs ({len(negation_pairs)} negation examples oversampled "
          f"{NEGATION_OVERSAMPLE_FACTOR}x) | val: {len(val_pairs)} pairs (unmodified)")

    tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME)
    model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME)

    def to_hf_dataset(items):
        return Dataset.from_dict({
            "input": [p["input"] for p in items],
            "target": [p["target"] for p in items],
        })

    train_ds, val_ds = to_hf_dataset(train_pairs), to_hf_dataset(val_pairs)

    def preprocess(batch):
        model_inputs = tokenizer(batch["input"], max_length=64, truncation=True, padding="max_length")
        labels = tokenizer(text_target=batch["target"], max_length=32, truncation=True, padding="max_length")
        labels["input_ids"] = [
            [(t if t != tokenizer.pad_token_id else -100) for t in seq]
            for seq in labels["input_ids"]
        ]
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    train_ds = train_ds.map(preprocess, batched=True, remove_columns=["input", "target"])
    val_ds = val_ds.map(preprocess, batched=True, remove_columns=["input", "target"])

    args = Seq2SeqTrainingArguments(
        output_dir="seq2seq_ckpt",
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=20,           # small dataset -> more epochs, watch eval loss for overfitting
        learning_rate=3e-4,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,             # keep best + latest only -- unbounded before, 40 checkpoints hit 27GB
        load_best_model_at_end=True,
        predict_with_generate=True,
        logging_steps=10,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model),
    )
    trainer.train()

    model.save_pretrained(MODEL_OUT)
    tokenizer.save_pretrained(MODEL_OUT)
    print(f"Saved fine-tuned model to {MODEL_OUT}/")

    # quick qualitative check on a few held-out examples
    print("\nSample val predictions:")
    for p in val_pairs[:8]:
        ids = tokenizer(p["input"], return_tensors="pt").input_ids.to(model.device)
        out = model.generate(ids, max_new_tokens=32)
        pred = tokenizer.decode(out[0], skip_special_tokens=True)
        print(f"  [{p['role']}] {p['input']!r}\n    gold: {p['target']!r}\n    pred: {pred!r}")


if __name__ == "__main__":
    main()
