"""
Phase 1 of the CHOICE product vision (see CLAUDE.md "Product vision" ->
"Step 1 workflow", item 3): takes a Pipeline.run() result (the 9 extraction
fields) and assembles a deterministic-template master prompt -- the
"Objective Statement" a stakeholder reads, edits, and confirms before it
goes to an LLM.

This is a template, not a trained model -- there's no (fields -> ideal
master prompt) dataset to train on yet (see CLAUDE.md Phase 5).

Blanking rule (changed 2026-09-03): a field is only blanked when the
pipeline extracted nothing for it (`status == "missing"`). A low-confidence
prediction is now shown in its own field -- the user sees the model's
actual guess, not a "[please fill in]" placeholder -- but the field is
forced into `needs_review` and carries a `low_confidence` flag so the UI
marks it distinctly. This reverses the original Phase 2 calibration-audit
design; see `_is_blank` and CLAUDE.md for the full trade-off. `intent` is
additionally always flagged for review regardless of confidence (T5
hallucination gap).

Run:
    python3 prompt_synthesis.py "Cut support ticket backlog by 40% for
    enterprise accounts within the next sprint."
"""

import ast
import sys

from pipeline import Pipeline, ROLES, MIN_JOIN_OPEN_CONFIDENCE

# Field never trustworthy by confidence alone (T5 hallucination gap, see
# CLAUDE.md known gaps #3) -- always surfaced for user review regardless of
# how confident the pipeline was.
ALWAYS_REVIEW_ROLES = {"intent"}

# Roles that are trailing clauses, not part of the core actor/intent/target
# skeleton -- a query can legitimately never state one of these (e.g. no
# constraint was ever mentioned), so the user gets a "not applicable" option
# instead of being forced to invent a value for a blank. actor/intent/object/
# measure are excluded: they're structural (subject, verb, target phrase) and
# omitting them would leave the sentence without a subject or target.
NOT_APPLICABLE_ELIGIBLE_ROLES = {"scope", "magnitude", "time", "constraints", "context"}

BLANK_PROMPTS = {
    "actor": "[actor — who is responsible?]",
    "object": "[object — what is being acted on?]",
    "intent": "[intent — what needs to happen?]",
    "scope": "[scope]",
    "measure": "[measure — what's being measured?]",
    "magnitude": "[magnitude — target amount or percentage?]",
    "time": "[time — by when?]",
    "constraints": "[constraints — any limits?]",
    "context": "[context — why does this matter?]",
}


def parse_value_items(value):
    """A multi-span field's value is a list -- either a real Python list
    (source_text, straight from the CRF spans) or a string that literally
    contains Python-list-repr syntax like "['a', 'b']" (T5's normalized
    output: build_seq2seq_pairs.py trains multi-value targets in that exact
    str(list) format, so T5 generates it verbatim as text, not as real
    structured data). Parses either back into a real list of item strings.
    Shared by humanize_value() (display) and eval_on_real_world.py's
    scoring (needs each element individually, not the joined string)."""
    if isinstance(value, list):
        items = value
    elif isinstance(value, str) and value.startswith("[") and value.endswith("]"):
        try:
            parsed = ast.literal_eval(value)
            items = parsed if isinstance(parsed, list) else None
        except (ValueError, SyntaxError):
            items = None
        if items is None:
            # T5 doesn't reliably quote items that contain characters like
            # "%" (ast.literal_eval chokes on bare "12%" as invalid Python),
            # so fall back to a plain comma-split inside the brackets rather
            # than leaving the raw "[12%, 9%, 15%]" text unparsed.
            inner = value[1:-1]
            items = [p.strip().strip("'\"") for p in inner.split(",")] if inner.strip() else []
    elif value in (None, ""):
        items = []
    else:
        return [str(value)]
    return [str(v) for v in items if str(v).strip()]


def humanize_value(value):
    """Join a field's value (see parse_value_items) as natural prose for
    user-facing text, instead of leaking raw list/bracket syntax (found
    2026-08-09 live-testing the app -- both the master-prompt sentence and
    the extraction-detail field cards were showing e.g. "['in the West',
    'in the East']" literally)."""
    items = parse_value_items(value)
    if not items:
        return value if isinstance(value, str) else ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _is_blank(field_result):
    """A field is a blank (shown as a "[role -- please fill in]" placeholder,
    no value carried into the master prompt) ONLY when the pipeline extracted
    nothing at all for it -- i.e. the CRF never opened a span.

    NOTE (changed 2026-09-03, per explicit product-owner decision): a
    low-confidence field is NO LONGER blanked. The model's predicted value
    is shown in its own field regardless of score, so the user can see and
    correct the actual guess instead of a placeholder. Low confidence still
    forces the field into `needs_review` (see build_fields), so it is
    flagged for the user to check -- it just isn't hidden. This reverses the
    original Phase 1 item 4 / Phase 2-audit design ("never assume a value
    for a low-confidence field"); the reasoning-integrity safeguard now
    rests on the review flag + confidence gauge being visible, not on
    withholding the value. See CLAUDE.md for the full trade-off."""
    return field_result["status"] == "missing"


def _is_low_confidence(field_result):
    return (
        field_result["status"] != "missing"
        and field_result["confidence"] < MIN_JOIN_OPEN_CONFIDENCE
    )


def _capitalize(text):
    return text[0].upper() + text[1:] if text else text


def build_fields(result):
    """Resolve each of the 9 extraction fields to display text (real value
    or blank placeholder) plus review/blank metadata."""
    fields = {}
    for role in ROLES:
        r = result[role]
        blank = _is_blank(r)
        low_confidence = _is_low_confidence(r)
        multi_span = r.get("multi_span", False)
        # pipeline.py can silently drop a real second (or third) span from a
        # multi-value join when it falls below MIN_JOIN_OPEN_CONFIDENCE --
        # it records this in guard_note/flagged_for_review, but does NOT
        # lower the surviving value's own confidence (that capping only
        # happens for polarity-guard corrections, checked before the drop
        # logic runs -- see pipeline.py's Pipeline.run()). So a field that
        # lost real, stated information (e.g. a second constraint clause)
        # can still read as high-confidence and sail past the blank
        # threshold with no visible signal (CLAUDE.md Known gap 10, found
        # 2026-08-12). Treat a recorded drop as its own review trigger,
        # independent of confidence.
        dropped_values = bool(r.get("flagged_for_review")) and "dropped" in (r.get("guard_note") or "")
        fields[role] = {
            "text": BLANK_PROMPTS[role] if blank else humanize_value(r["value"]),
            "blank": blank,
            # a single template slot can't safely disambiguate multiple
            # surviving spans (e.g. two actors) -- surface for review
            # rather than silently rendering the "; "-joined text as if it
            # were one value, same reasoning as ALWAYS_REVIEW_ROLES.
            "multi_span": multi_span,
            "dropped_values": dropped_values,
            # low_confidence: value is shown (not blanked) but the pipeline
            # was unsure -- always a review trigger, surfaced to the UI so it
            # can mark the field distinctly from a confident one.
            "low_confidence": low_confidence,
            "needs_review": (
                blank
                or low_confidence
                or role in ALWAYS_REVIEW_ROLES
                or multi_span
                or dropped_values
            ),
            "confidence": r["confidence"],
            "status": r["status"],
            # never set by the pipeline -- only the user, at confirm time,
            # can know a field genuinely doesn't apply to this query.
            "not_applicable": False,
        }
    return fields


MAGNITUDE_SELF_PREPOSITIONS = {"by", "to", "into", "from", "up", "down"}
TIME_SELF_PREPOSITIONS = {"by", "within", "before", "during", "in", "on", "at", "through", "until"}


def _prefixed_clause(prefix, field, self_prepositions):
    """T5 often keeps the preposition from the source span in the
    normalized value itself ("within the next sprint", "by 40%"), so a
    fixed template prefix would double up ("within within the next
    sprint"). Skip the prefix when the value already opens with one of its
    own -- but not for blank placeholders, which always need the prefix to
    read naturally ("by [magnitude — ...]")."""
    text = field["text"]
    if not field["blank"]:
        first_word = text.split()[0].lower() if text.split() else ""
        if first_word in self_prepositions:
            return text
    return f"{prefix} {text}"


def _target_phrase(fields):
    """Fuse measure + object into one noun phrase ("annual sales of
    premium office chairs") when both are known; fall back to whichever one
    is known. If both are blank, surface the measure blank placeholder --
    the object blank is still tracked separately in `blanks`."""
    measure, obj = fields["measure"], fields["object"]
    if not measure["blank"] and not obj["blank"] and measure["text"] != obj["text"]:
        return f"{measure['text']} of {obj['text']}"
    if not measure["blank"]:
        return measure["text"]
    if not obj["blank"]:
        return obj["text"]
    return measure["text"]


def _not_applicable(field):
    return field.get("not_applicable", False)


def _clause_text(field):
    return str(field.get("text", "")).strip()


def _omit_clause(field):
    """Skip an optional clause entirely when the field doesn't apply, or
    has no text at all to render. A genuine unfilled blank in the Streamlit
    flow still carries its "[role -- please fill in]" placeholder text and
    is NOT omitted -- that's how the user sees what's still missing. A
    field that arrives blank with an empty string (e.g. via api.py's
    /assemble with {"blank": true} and no text) has nothing to show and is
    dropped rather than rendered as a dangling "because ." """
    return _not_applicable(field) or not _clause_text(field)


def render_sentence(fields):
    """Assemble the master-prompt sentence from a fields dict shaped like
    build_fields()'s output (role -> {"text":..., "blank":...}, at least).
    Shared by synthesize_master_prompt() (pipeline-extracted fields) and
    app.py's confirm/reject step (user-edited fields).

    A NOT_APPLICABLE_ELIGIBLE_ROLES field marked not_applicable drops its
    clause entirely instead of rendering a blank placeholder -- e.g. a query
    with no stated constraint shouldn't force "while subject to this
    constraint: [constraints -- please fill in]" into the prompt."""
    subject = _capitalize(_clause_text(fields["actor"]))
    intent_text = _clause_text(fields["intent"])
    target_phrase = _target_phrase(fields).strip()

    # The pipeline sometimes bundles the object straight into the intent
    # value ("cut ticket backlog"), which then reads as a stutter once the
    # object is appended again ("cut ticket backlog ticket backlog"). If
    # the target is already contained in the intent, don't repeat it.
    if target_phrase and target_phrase.lower() in intent_text.lower():
        core = f"{subject} wants to {intent_text}"
    elif target_phrase:
        core = f"{subject} wants to {intent_text} {target_phrase}"
    else:
        core = f"{subject} wants to {intent_text}"

    lead_clauses = []
    if not _omit_clause(fields["magnitude"]):
        lead_clauses.append(_prefixed_clause("by", fields["magnitude"], MAGNITUDE_SELF_PREPOSITIONS))
    if not _omit_clause(fields["time"]):
        lead_clauses.append(_prefixed_clause("within", fields["time"], TIME_SELF_PREPOSITIONS))

    trailing_clauses = []
    if not _omit_clause(fields["scope"]):
        trailing_clauses.append(f"by targeting {_clause_text(fields['scope'])}")
    if not _omit_clause(fields["constraints"]):
        trailing_clauses.append(f"while subject to this constraint: {_clause_text(fields['constraints'])}")
    if not _omit_clause(fields["context"]):
        trailing_clauses.append(f"because {_clause_text(fields['context'])}")

    sentence = core
    if lead_clauses:
        sentence += " " + " ".join(lead_clauses)
    if trailing_clauses:
        sentence += " " + ", ".join(trailing_clauses)
    sentence = " ".join(sentence.split()).rstrip(" ,")
    return _capitalize(sentence) + "."


# Roles whose multi_span co-occurrence actually signals a bundled query --
# "who does it" and "what do they do" both having multiple surviving spans
# is the actor<->intent pairing problem (CLAUDE.md Known gap 6, raised
# 2026-08-05); object joins the same signal since a query can bundle
# multiple targets instead of multiple actors ("grow enterprise accounts
# and reduce churn"). scope/magnitude/time etc. legitimately have multiple
# spans within a single decision (e.g. "7% in the Americas, 10% in APAC")
# and are excluded so they don't produce false positives here.
COMPOUND_SIGNAL_ROLES = {"actor", "intent", "object"}


def detect_possible_compound_query(fields):
    """A single master-prompt template has exactly one slot per role, so it
    can't correctly render two independent actor-intent(-object) chains
    bundled into one query (e.g. "Marketing will grow brand awareness while
    Sales grows enterprise accounts"). Rather than silently guessing a
    pairing, surface the condition so the user can be asked directly --
    per the recommended direction in CLAUDE.md Known gap 6: this is itself
    a clarifying question in the spirit of the product's actual goal, not
    a defect to paper over quietly."""
    multi_span_roles = [r for r in COMPOUND_SIGNAL_ROLES if fields[r]["multi_span"]]
    is_possible_compound = len(multi_span_roles) >= 2
    return {
        "is_possible_compound": is_possible_compound,
        "multi_span_roles": multi_span_roles,
        "message": (
            "This query might describe more than one decision bundled together "
            f"({' and '.join(multi_span_roles)} each found multiple candidates). "
            "If so, consider running each part through CHOICE Forge separately "
            "for a clearer master prompt per decision."
        ) if is_possible_compound else None,
    }


def synthesize_master_prompt(result):
    """Build the master prompt text + structured blank/review metadata from
    a Pipeline.run() result dict."""
    fields = build_fields(result)
    sentence = render_sentence(fields)

    blanks = [role for role in ROLES if fields[role]["blank"]]
    low_confidence = [role for role in ROLES if fields[role]["low_confidence"]]
    mandatory_review = [role for role in ROLES if fields[role]["needs_review"]]

    return {
        "master_prompt": sentence,
        "fields": fields,
        "blanks": blanks,
        "low_confidence": low_confidence,
        "mandatory_review": mandatory_review,
        "possible_compound_query": detect_possible_compound_query(fields),
    }


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) or (
        "Cut support ticket backlog by 40% for enterprise accounts within the next sprint."
    )
    pipe = Pipeline()
    result = pipe.run(text)
    synth = synthesize_master_prompt(result)

    print("Master prompt:\n")
    print(synth["master_prompt"])
    print()
    print(f"Blanks ({len(synth['blanks'])}): {', '.join(synth['blanks']) or 'none'}")
    print(f"Needs review ({len(synth['mandatory_review'])}): {', '.join(synth['mandatory_review'])}")
