"""
Train a CRF sequence tagger on choice_forge_dataset_full_100_v2.json to
locate, for every role, the span of the query that grounds it.

Key design decision (confirmed against the real data -- see analysis below):
  Train against `source_text`, NOT `value`. Across all 655 non-missing role
  instances in the dataset, source_text is a 100% verbatim substring of
  input_query (zero mismatches). `value` is frequently a paraphrase of
  source_text (e.g. intent: 89/100 rows introduce wording not present in
  the source span -- "Get monthly logo churn under 2%" -> "reduce churn").
  A sequence tagger is extractive by construction and cannot produce that
  paraphrase. So:
    - This CRF's job is ONLY span-finding + role assignment (extractive,
      learns well from labeled data, generalizes to new phrasing).
    - Turning the extracted span into the canonical `value` is a separate,
      generative step -- see train_seq2seq.py.

Multi-span roles: some fields (e.g. choice_015's magnitude: ["25,000",
"under ₹350"]) have more than one grounding span for a single role in
the same query. BIO tagging handles this natively -- we just tag each
occurrence as its own B-ROLE/I-ROLE run and decode collects all of them.

Install:
    pip install spacy sklearn-crfsuite joblib
    python -m spacy download en_core_web_sm

Run:
    python train_crf.py choice_forge_dataset_full_100_v2.json
"""

import json
import sys

import spacy
import sklearn_crfsuite
from sklearn_crfsuite import metrics
from sklearn.model_selection import train_test_split

nlp = spacy.load("en_core_web_sm")

ROLES = ["actor", "object", "intent", "scope", "measure",
          "magnitude", "time", "constraints", "context"]


def as_span_list(source_text):
    """source_text can be None, a string, or a list of strings -- normalize to a list."""
    if source_text is None:
        return []
    if isinstance(source_text, list):
        return [str(s) for s in source_text]
    return [str(source_text)]


def find_all_char_spans(query, needle):
    """Find every non-overlapping occurrence of `needle` in `query` (case-insensitive)."""
    spans = []
    q_low, n_low = query.lower(), needle.lower().strip()
    if not n_low:
        return spans
    start = 0
    while True:
        idx = q_low.find(n_low, start)
        if idx == -1:
            break
        spans.append((idx, idx + len(n_low)))
        start = idx + len(n_low)
    return spans


def row_to_bio(doc, row):
    tags = ["O"] * len(doc)
    query = row["input_query"]
    for role in ROLES:
        info = row["choice"][role]
        if info["status"] == "missing":
            continue
        for needle in as_span_list(info["source_text"]):
            char_spans = find_all_char_spans(query, needle)
            if not char_spans:
                continue
            # first occurrence not already claimed by another role -- avoids
            # relabeling the same tokens twice for duplicate substrings
            for cs, ce in char_spans:
                span = doc.char_span(cs, ce, alignment_mode="expand")
                if span is None:
                    continue
                if all(tags[t.i] == "O" for t in span):
                    for i, tok in enumerate(span):
                        tags[tok.i] = f"{'B' if i == 0 else 'I'}-{role.upper()}"
                    break  # one occurrence tagged per needle is enough
    return tags


def token_features(doc, i):
    tok = doc[i]
    feats = {
        "bias": 1.0,
        "word.lower": tok.lower_,
        "lemma": tok.lemma_,
        "pos": tok.pos_,
        "tag": tok.tag_,
        "dep": tok.dep_,
        "ent_type": tok.ent_type_,
        "is_stop": tok.is_stop,
        "like_num": tok.like_num,
        "is_punct": tok.is_punct,
        "is_title": tok.is_title,
        "head_dep": tok.head.dep_,
        "head_lemma": tok.head.lemma_,
    }
    if i > 0:
        prev = doc[i - 1]
        feats.update({"-1:word.lower": prev.lower_, "-1:pos": prev.pos_, "-1:dep": prev.dep_})
    else:
        feats["BOS"] = True
    if i < len(doc) - 1:
        nxt = doc[i + 1]
        feats.update({"+1:word.lower": nxt.lower_, "+1:pos": nxt.pos_, "+1:dep": nxt.dep_})
    else:
        feats["EOS"] = True
    return feats


def load_dataset(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_training_data(rows):
    X, y = [], []
    for row in rows:
        doc = nlp(row["input_query"])
        X.append([token_features(doc, i) for i in range(len(doc))])
        y.append(row_to_bio(doc, row))
    return X, y


def train(json_path, model_out="role_tagger.joblib"):
    rows = load_dataset(json_path)
    X, y = build_training_data(rows)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    crf = sklearn_crfsuite.CRF(
        algorithm="lbfgs", c1=0.1, c2=0.1, max_iterations=150,
        all_possible_transitions=True,
    )
    crf.fit(X_train, y_train)

    labels = [l for l in crf.classes_ if l != "O"]
    y_pred = crf.predict(X_test)
    print(metrics.flat_classification_report(y_test, y_pred, labels=labels, digits=3))

    import joblib
    joblib.dump(crf, model_out)
    print(f"Saved model to {model_out}")
    return crf


if __name__ == "__main__":
    train(sys.argv[1] if len(sys.argv) > 1 else "choice_forge_dataset_full_100_v2.json")
