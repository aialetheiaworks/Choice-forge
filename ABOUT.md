# About CHOICE Forge v1

## The problem

Given a plain-English business ask, pull out 9 structured fields (actor,
object, intent, scope, measure, magnitude, time, constraints, context) —
each with a value, a confidence score, and the exact text span it came
from. The only source of truth is `choice_forge_dataset_full_100_v2.json`:
100 rows, each a hand-labeled `input_query` plus the 9 fields, each field
carrying `value`, `status` (explicit/inferred/missing), `confidence`, and
`source_text` (the literal span in the query that grounds it).

## Why it's three layers instead of one model

The first design question was: can one model just read the query and spit
out the 9 fields directly? Checking the real data against that idea killed
it. Across all 655 non-missing role instances in the dataset,
`source_text` is a **100% verbatim substring** of `input_query` — zero
mismatches, including rows with multiple spans for one role (e.g. a
`magnitude` field grounded in two separate numbers). That's a strong,
clean signal that span-finding is a solved, well-behaved sub-problem: a
sequence tagger that's good at locating known-pattern text.

But `value` is very often **not** the same words as `source_text` — it's a
real paraphrase or synthesis:

- `source_text`: "Get monthly logo churn under 2%" → `value`: "reduce churn"
- `source_text`: "onboard 1,200 kirana stores" → `value`: "number of kirana stores onboarded"

Measuring this across the dataset: `intent` paraphrases in 89/100 rows,
`measure` in 71/80, `context` in 60/61, `object` in 49/99, `magnitude` in
43/66. Only `time` is mostly a pure trim (64/70 rows). A sequence tagger
is extractive by construction — it can only select spans of the input, it
cannot invent "reduce churn" out of "Get monthly logo churn under 2%".
Hand-written rules hit the same wall: you'd end up writing one paraphrase
rule per phrasing pattern, which is the exact scaling problem you're
trying to avoid.

So the pipeline is split into what each technique is actually good at:

```
query text
   │
   ▼
[Layer 1] spaCy (pretrained, off the shelf)
   → tokenizes the query, gives every token its POS tag, dependency
     relation, lemma, entity type -- these become features for Layer 2.
   │
   ▼
[Layer 2] CRF, trained on this dataset (train_crf.py -> role_tagger.joblib)
   → per-token BIO tagging (B-ACTOR, I-ACTOR, B-INTENT, ...) trained
     against source_text, not value. Extractive job only: "which words in
     this query ground role X, if any." Handles multi-span roles natively
     -- each B-ROLE/I-ROLE run is decoded as its own span.
   │
   ▼
[Layer 3] T5-small, fine-tuned on this dataset
          (train_seq2seq.py -> value_synthesizer/)
   → takes the span(s) Layer 2 found and generates the canonical value.
     One pooled model handles all 9 roles via a role-prefix instruction
     ("normalize actor: ...", "normalize intent: ..."), standard T5-style
     multi-task conditioning. Pooling instead of 9 separate models exists
     because some roles are too thin alone to fine-tune reliably (actor:
     25 examples, constraints: 38) -- pooling lets the model share general
     "clean up and canonicalize this span" ability across roles while the
     prefix tells it which normalization style to apply.
   │
   ▼
[Layer 4] polarity_guard.py (rule-based, runtime only, no training)
   → catches a specific failure mode T5-small has on negated constraints
     (see below) and either fixes it with a template or flags it instead
     of silently returning a wrong answer.
   │
   ▼
structured 9-field output
```

`pipeline.py` is the class that chains all four layers into one call —
`Pipeline().run(text)`.

## How the training data is built

`build_seq2seq_pairs.py` walks every row in
`choice_forge_dataset_full_100_v2.json`, and for every role that isn't
`"missing"`, emits one training pair:

```json
{"id": "choice_001", "role": "actor",
 "input": "normalize actor: Our field sales team",
 "target": "field sales team",
 "gold_status": "explicit"}
```

Multi-span `source_text` (a list, not a string) gets joined with `"; "`
into one input string. This produces 629 pairs from the 655 non-missing
role instances (some multi-span rows collapse to one joined string, hence
629 < 655). That file is checked in at `data/seq2seq_pairs.jsonl` so you
can inspect exactly what the model is trained on without regenerating it.

## Known limitation: negation, and how it's handled

Only 23/655 role instances (3.5%) in the dataset contain a negation cue
("without increasing X", "no more than N"), almost all concentrated in
`constraints`. A model fine-tuned on 629 examples total doesn't get enough
signal from 23 of them to reliably learn that "without increasing X" means
the opposite of "increasing X" — early testing surfaced exactly this:
`"Cut ... by 40%"` synthesized as `"40% increase"`, and `"without
increasing the ad spend budget"` synthesized as `"ad spend budget
raised"`. Both are direction flips: the generated value contradicts the
input.

Fixed on both ends:

1. **Training side** (`train_seq2seq.py`): every input span containing a
   negation cue gets an explicit `[NEGATED]` marker prepended (e.g.
   `"normalize [NEGATED] constraints: without increasing the ad spend
   budget"`), instead of expecting the model to infer negation implicitly
   from a rare surface pattern. The 23 negation examples are also
   oversampled 5x, but **only in the train split** — validation stays at
   the real 3.5% frequency so eval numbers aren't inflated. `pipeline.py`
   applies the same `[NEGATED]` tagging at inference time so train and
   inference conditions match.

2. **Runtime side** (`polarity_guard.py`): a backstop for whatever the
   model still gets wrong, since 629 examples (even oversampled) is a
   small dataset and won't generalize to every negation phrasing. It
   compares the source span's implied direction (increase/decrease,
   accounting for negation) against the generated value's implied
   direction:
   - **Direction flip** (source says decrease, output says increase, or
     vice versa): tries a rule-based template first (`"without X-ing Y"` →
     `"must not X Y"`, `"no more than N"` → `"capped at N"`); if no
     template matches, swaps the offending direction word for its
     opposite (`"increase"` → `"decrease"`, etc).
   - **Dropped negation** (source has a negation cue, output has neither a
     negation cue nor a direction word at all, e.g. `"without using
     external agencies"` → `"use external agencies"`): same template
     correction applied.
   - **If neither correction applies**: the value is left as-is, but
     `flagged_for_review: true` is set and confidence is capped at 0.3, so
     a bad generation is visible in the output instead of silently wrong.

   For roles like `magnitude` where the direction cue often lives in a
   *sibling* role's phrasing rather than the role's own span (e.g.
   `magnitude`'s span is just `"by 40%"`; the word "Cut" is over in
   `intent`), the guard falls back to scanning the full original query
   text for a direction cue when the role's own span has none.

## Known limitation: `status` is a simplification

`status` (explicit vs. inferred) is set by a simple rule in
`pipeline.py`: `"explicit"` whenever the CRF found a grounding span,
`"missing"` when it didn't. Checking the gold data shows this doesn't line
up cleanly with literal word-overlap — most `context` values are full
paraphrases yet are still labeled `"explicit"` in the source dataset, so a
string-similarity heuristic would misclassify a lot of rows. The correct
fix would be a small classifier trained on `(span, value, gold_status)`
triples; not built yet, tracked as a known follow-up.

## Honest state of the models

- **CRF (span extraction)**: micro-avg F1 ≈ 0.41 on a held-out 20% split
  (80 rows). Strong on `TIME` (F1 0.77), `ACTOR` (0.67), `CONSTRAINTS`
  (0.62); weak on `CONTEXT` (0.0) and parts of `MEASURE`/`INTENT`. This
  reflects the dataset size (100 rows) more than the method — CRFs need
  more labeled examples per role than this dataset currently has,
  especially for roles like `context` where the grounding span is a loose,
  varied paraphrase target rather than a consistent surface pattern.

- **T5 (value synthesis)**: trained for 20 epochs on 629 pairs (train loss
  ≈ 0.83, eval loss ≈ 3.1 after the negation-oversampling retrain — the
  gap between train and eval loss indicates some overfitting, expected
  with this little data). It does well on phrasing patterns close to what
  it's seen (`"before the holiday season"` → passes through verbatim
  correctly) and worse on cases requiring real inference (e.g. `"drops per
  hour; damage complaints"` → `"reduce costs; damage complaints"`,
  hallucinating "reduce costs" instead of the gold `"damage complaints as
  share of parcels"`).

Neither model is a one-shot fix. Both are meant to be retrained as the
labeled dataset grows past 100 rows — the retraining commands in
`README.md` are the whole workflow, not a one-time setup step.
