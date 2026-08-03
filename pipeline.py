"""
Full inference pipeline: spaCy (Layer 1, pretrained) -> CRF (Layer 2,
trained on your data, extracts grounding spans) -> T5 (Layer 3, trained on
your data, turns each span into the canonical value).

Nothing here calls a third-party LLM API. Both trained components
(role_tagger.joblib, value_synthesizer/) are produced by train_crf.py and
train_seq2seq.py against your own labeled dataset and run entirely locally.

Known simplification, flagged honestly: `status` (explicit/inferred) is
derived here with a simple rule -- "explicit" whenever the CRF found a
grounding span, "missing" when it didn't. Checking the real data shows
gold status doesn't line up cleanly with literal-word-overlap (e.g. most
"context" values are paraphrases but are still labeled "explicit"), so a
string-similarity heuristic would misclassify a lot of rows. The more
correct fix is a small classifier trained on (span, value, gold_status)
triples -- not built yet, tracked as a follow-up once this base pipeline
is validated.

Run:
    python3 pipeline.py "Cut support ticket backlog by 40% for enterprise
    accounts within the next sprint."
"""

import sys

import spacy
import joblib
from transformers import T5Tokenizer, T5ForConditionalGeneration

from train_crf import token_features, ROLES
from polarity_guard import has_negation, apply_polarity_guard

CRF_MODEL_PATH = "role_tagger.joblib"
T5_MODEL_PATH = "value_synthesizer"

# Below this, a second-or-later B-tag for an already-filled role is treated as
# a likely spurious extraction rather than a legitimate second occurrence --
# see decode_bio_multi / Pipeline.run for why this matters.
MIN_JOIN_OPEN_CONFIDENCE = 0.4

nlp = spacy.load("en_core_web_sm")


def decode_bio_multi(doc, tags, marginals):
    """Collect ALL spans per role (a role can legitimately appear more than
    once in one query, e.g. two separate numeric constraints under magnitude).

    Tracks "open_confidence" (the B-tag's own marginal) separately from the
    span's mean confidence, because I-tag continuation confidence inflates
    once the CRF has committed to a tag -- a weak, spurious B- decision can
    still be followed by high-confidence I- tags riding the transition prior
    (see the "cut; creep above where it was last quarter" bug: B-INTENT on
    "creep" opened at 0.179 but its I-INTENT tail averaged well above 0.5).
    open_confidence is the signal that actually reflects whether the CRF was
    sure this span belongs here at all."""
    spans = {role: [] for role in ROLES}
    i = 0
    while i < len(tags):
        tag = tags[i]
        if tag.startswith("B-"):
            role = tag[2:].lower()
            start = i
            open_confidence = marginals[i].get(tag, 0.0)
            probs = [open_confidence]
            j = i + 1
            while j < len(tags) and tags[j] == f"I-{tag[2:]}":
                probs.append(marginals[j].get(tags[j], 0.0))
                j += 1
            spans[role].append({
                "text": doc[start:j].text,
                "confidence": round(sum(probs) / len(probs), 3),
                "open_confidence": round(open_confidence, 3),
            })
            i = j
        else:
            i += 1
    return spans


class Pipeline:
    def __init__(self, crf_path=CRF_MODEL_PATH, t5_path=T5_MODEL_PATH):
        self.crf = joblib.load(crf_path)
        self.tokenizer = T5Tokenizer.from_pretrained(t5_path)
        self.t5 = T5ForConditionalGeneration.from_pretrained(t5_path)

    def synthesize(self, role, span_text):
        """Run the extracted span through the T5 normalizer for this role."""
        tag = "[NEGATED] " if has_negation(span_text) else ""
        prompt = f"normalize {tag}{role}: {span_text}"
        inputs = self.tokenizer(prompt, return_tensors="pt")
        out = self.t5.generate(
            **inputs, max_new_tokens=32,
            output_scores=True, return_dict_in_generate=True,
        )
        value = self.tokenizer.decode(out.sequences[0], skip_special_tokens=True)
        # sequence-level confidence proxy: mean of per-step top-token probabilities
        import torch
        if out.scores:
            probs = [torch.softmax(s, dim=-1).max().item() for s in out.scores]
            synth_conf = sum(probs) / len(probs)
        else:
            synth_conf = 0.5
        return value, round(synth_conf, 3)

    def extract(self, text):
        doc = nlp(text)
        feats = [token_features(doc, i) for i in range(len(doc))]
        tags = self.crf.predict_single(feats)
        marginals = self.crf.predict_marginals_single(feats)
        return doc, decode_bio_multi(doc, tags, marginals)

    def run(self, text):
        doc, span_map = self.extract(text)
        result = {}
        for role in ROLES:
            found = span_map[role]
            if not found:
                result[role] = {
                    "value": None, "status": "missing", "confidence": 0.0,
                    "source_text": None, "flagged_for_review": False,
                    "guard_note": None, "multi_span": False,
                }
                continue

            dropped_note = None
            if len(found) > 1:
                # A second (or third...) B-tag for the same role is only a
                # legitimate multi-span field if the CRF was actually
                # confident about opening it. A low-confidence extra span is
                # more likely a spurious tag riding an unrelated clause (see
                # decode_bio_multi docstring) -- joining it in anyway is what
                # produced nonsense like "reduce; creep above where it was
                # last quarter". Keep at least one span so a role never gets
                # dropped to "missing" purely by this filter.
                confident = [s for s in found if s["open_confidence"] >= MIN_JOIN_OPEN_CONFIDENCE]
                if not confident:
                    confident = [max(found, key=lambda s: s["open_confidence"])]
                if len(confident) < len(found):
                    dropped_note = (
                        f"dropped {len(found) - len(confident)} low-confidence span(s) "
                        f"(< {MIN_JOIN_OPEN_CONFIDENCE}) from multi-span join"
                    )
                found = confident

            joined_span = "; ".join(s["text"] for s in found)
            if len(found) == 1:
                extraction_conf = found[0]["confidence"]
            else:
                # min, not mean: a joined field is only as trustworthy as its
                # weakest surviving span -- averaging let one strong span mask
                # a shaky one (this was the root of the original bug)
                extraction_conf = min(s["open_confidence"] for s in found)
            value, synth_conf = self.synthesize(role, joined_span)
            value, flagged, guard_note = apply_polarity_guard(
                joined_span, value, full_text=text
            )
            confidence = round(extraction_conf * synth_conf, 3)
            if flagged:
                confidence = min(confidence, 0.3)
            if dropped_note:
                flagged = True
                guard_note = f"{guard_note}; {dropped_note}" if guard_note else dropped_note
            result[role] = {
                "value": value,
                # simplification -- see module docstring
                "status": "explicit",
                "confidence": confidence,
                "source_text": joined_span if len(found) > 1 else found[0]["text"],
                "flagged_for_review": flagged,
                "guard_note": guard_note,
                # true when >1 span survived the confidence filter above --
                # a real second occurrence, not spurious noise that got
                # dropped. Downstream consumers (e.g. prompt_synthesis.py)
                # use this to flag "this field may bundle >1 distinct
                # actor/object/etc." for human review, since a single
                # template slot can't safely disambiguate multiple values.
                "multi_span": len(found) > 1,
            }
        return result


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) or (
        "Cut support ticket backlog by 40% for enterprise accounts within the next sprint."
    )
    pipe = Pipeline()
    out = pipe.run(text)
    print(f"{'field':12s} | {'value':40s} | {'status':9s} | conf | source_text")
    print("-" * 110)
    for field, r in out.items():
        flag = "  [FLAGGED: " + r["guard_note"] + "]" if r["flagged_for_review"] else ""
        print(f"{field:12s} | {str(r['value'])[:40]:40s} | {r['status']:9s} | {r['confidence']:.2f} | {r['source_text']}{flag}")
