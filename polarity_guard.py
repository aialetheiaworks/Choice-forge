"""
Runtime guard between the T5 synthesizer's output and the final value.

Only 23/655 role instances (3.5%) in the real dataset contain a negation
cue, almost all in `constraints`. T5-small doesn't have enough signal to
reliably learn that "without increasing X" means the opposite of
"increasing X" -- see train_seq2seq.py's oversampling fix for the training
side. This module is the runtime-side backstop for whatever the model
still gets wrong after that fix (and for the currently-deployed model,
which was trained before the fix existed).

Two failure patterns it catches:
  1. Direction flip -- source implies decrease, generated value implies
     increase (or vice versa). E.g. "Cut ... by 40%" -> generated value
     "40% increase". Also handles the case where the direction cue lives
     in a sibling role's phrasing rather than the role's own span (e.g.
     magnitude's span is just "by 40%"; the word "Cut" is in intent) via
     the optional `full_text` fallback.
  2. Dropped negation -- source has a negation cue, generated value has
     neither a negation cue nor a directional word at all. E.g. "without
     using external agencies" -> "use external agencies".

When a rule-based template matches ("without X-ing Y" -> "must not X Y",
"no more than N" -> "capped at N") or a direct direction-word swap fixes
it, we apply the correction. Otherwise we leave the value untouched but
set flagged_for_review=True and cap confidence at 0.3, so a bad generation
is visible in the output instead of silently wrong.
"""

import re

NEGATION_CUES = [
    "without", "cannot", "can't", "won't", "don't", "doesn't", "didn't",
    "never", "no more than", "not ", "n't", "avoid", "excluding", "except",
    "unless",
]

INCREASE_WORDS = {
    "increase", "increased", "increasing", "grow", "growing", "grew",
    "raise", "raised", "raising", "expand", "expanded", "expanding",
    "add", "added", "adding", "more", "higher", "up", "boost", "boosted",
}
DECREASE_WORDS = {
    "decrease", "decreased", "decreasing", "cut", "cutting", "reduce",
    "reduced", "reducing", "lower", "lowered", "lowering", "shrink",
    "shrinking", "drop", "dropped", "dropping", "fewer", "less", "down",
    "capped", "cap",
}

FLIP_MAP = {
    "increase": "decrease", "increased": "reduced", "increasing": "reducing",
    "grow": "reduce", "growing": "reducing", "grew": "reduced",
    "raise": "lower", "raised": "lowered", "raising": "lowering",
    "expand": "shrink", "expanded": "shrunk", "expanding": "shrinking",
    "add": "cut", "added": "cut", "adding": "cutting",
    "more": "less", "higher": "lower", "up": "down",
    "boost": "cut", "boosted": "cut",
}
FLIP_MAP.update({v: k for k, v in FLIP_MAP.items()})

VERB_BASE = {
    "using": "use", "increasing": "increase", "adding": "add",
    "spending": "spend", "hiring": "hire", "raising": "raise",
    "expanding": "expand", "growing": "grow", "exceeding": "exceed",
    "reducing": "reduce", "cutting": "cut", "lowering": "lower",
}


def has_negation(text):
    low = text.lower()
    return any(cue in low for cue in NEGATION_CUES)


def _direction(text):
    if not text:
        return None
    words = set(re.findall(r"[a-z']+", text.lower()))
    inc = bool(words & INCREASE_WORDS)
    dec = bool(words & DECREASE_WORDS)
    negated = has_negation(text)
    if inc and not dec:
        return "decrease" if negated else "increase"
    if dec and not inc:
        return "increase" if negated else "decrease"
    return None


def _degeminate(stem):
    """Undo doubled-consonant gerund spelling ("lett" -> "let", "cutt" ->
    "cut") for verbs not covered by VERB_BASE. A naive `-ing` strip alone
    leaves the doubled consonant from the gerund spelling rule behind."""
    if len(stem) >= 3 and stem[-1] == stem[-2] and stem[-1] not in "aeiou" and stem[-3] in "aeiou":
        return stem[:-1]
    return stem


def _apply_without_template(source_text):
    m = re.search(r"without (\w+ing) (.+)", source_text, re.IGNORECASE)
    if not m:
        return None
    verb, obj = m.group(1).lower(), m.group(2).strip()
    base = VERB_BASE.get(verb, _degeminate(verb[:-3]) if verb.endswith("ing") else verb)
    return f"must not {base} {obj}"


def _apply_no_more_than_template(source_text):
    m = re.search(r"no more than (.+)", source_text, re.IGNORECASE)
    if not m:
        return None
    return f"capped at {m.group(1).strip()}"


def apply_polarity_guard(source_text, generated_value, full_text=None):
    """Check `generated_value` against `source_text` (falling back to
    `full_text` for direction cues when the role's own span carries none).
    Returns (value, flagged_for_review, note)."""
    source_dir = _direction(source_text) or _direction(full_text)
    gen_dir = _direction(generated_value)

    if source_dir and gen_dir and source_dir != gen_dir:
        corrected = (_apply_without_template(source_text)
                     or _apply_no_more_than_template(source_text))
        if corrected:
            return corrected, False, "direction-flip corrected via template"
        words = generated_value.split()
        swapped = " ".join(FLIP_MAP.get(w.lower(), w) for w in words)
        if swapped.lower() != generated_value.lower():
            return swapped, False, "direction-flip corrected via word swap"
        return generated_value, True, "direction-flip detected, no correction rule matched"

    if has_negation(source_text) and not has_negation(generated_value) and gen_dir is None:
        corrected = (_apply_without_template(source_text)
                     or _apply_no_more_than_template(source_text))
        if corrected:
            return corrected, False, "dropped negation corrected via template"
        return generated_value, True, "dropped negation detected, no correction rule matched"

    return generated_value, False, None
