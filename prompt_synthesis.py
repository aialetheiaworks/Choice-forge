"""
Phase 1 of the CHOICE product vision (see CLAUDE.md "Product vision" ->
"Step 1 workflow", item 3): takes a Pipeline.run() result (the 9 extraction
fields) and assembles a deterministic-template master prompt -- the
"Objective Statement" a stakeholder reads, edits, and confirms before it
goes to an LLM.

This is a template, not a trained model -- there's no (fields -> ideal
master prompt) dataset to train on yet (see CLAUDE.md Phase 5). Blanking
rules come directly from the Phase 2 calibration audit (2026-07-29):
every field except `intent` is reliable whenever the pipeline commits to a
non-missing value, so those are only blanked on `status == "missing"` or
low confidence. `intent` alone is never trustworthy by confidence, so it's
always marked as needing user review even when filled in.

Run:
    python3 prompt_synthesis.py "Cut support ticket backlog by 40% for
    enterprise accounts within the next sprint."
"""

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
    "actor": "[actor — who is responsible? please fill in]",
    "object": "[object — what is being acted on? please fill in]",
    "intent": "[intent — what needs to happen? please fill in]",
    "scope": "[scope — please fill in]",
    "measure": "[measure — what's being measured? please fill in]",
    "magnitude": "[magnitude — target amount or percentage? please fill in]",
    "time": "[time — by when? please fill in]",
    "constraints": "[constraints — any limits? please fill in]",
    "context": "[context — why does this matter? please fill in]",
}


def _is_blank(field_result):
    return (
        field_result["status"] == "missing"
        or field_result["confidence"] < MIN_JOIN_OPEN_CONFIDENCE
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
        multi_span = r.get("multi_span", False)
        fields[role] = {
            "text": BLANK_PROMPTS[role] if blank else str(r["value"]),
            "blank": blank,
            # a single template slot can't safely disambiguate multiple
            # surviving spans (e.g. two actors) -- surface for review
            # rather than silently rendering the "; "-joined text as if it
            # were one value, same reasoning as ALWAYS_REVIEW_ROLES.
            "multi_span": multi_span,
            "needs_review": blank or role in ALWAYS_REVIEW_ROLES or multi_span,
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


def render_sentence(fields):
    """Assemble the master-prompt sentence from a fields dict shaped like
    build_fields()'s output (role -> {"text":..., "blank":...}, at least).
    Shared by synthesize_master_prompt() (pipeline-extracted fields) and
    app.py's confirm/reject step (user-edited fields).

    A NOT_APPLICABLE_ELIGIBLE_ROLES field marked not_applicable drops its
    clause entirely instead of rendering a blank placeholder -- e.g. a query
    with no stated constraint shouldn't force "while subject to this
    constraint: [constraints -- please fill in]" into the prompt."""
    subject = _capitalize(fields["actor"]["text"])
    intent_text = fields["intent"]["text"]
    target_phrase = _target_phrase(fields)

    core = f"{subject} wants to {intent_text} {target_phrase}"

    lead_clauses = []
    if not _not_applicable(fields["magnitude"]):
        lead_clauses.append(_prefixed_clause("by", fields["magnitude"], MAGNITUDE_SELF_PREPOSITIONS))
    if not _not_applicable(fields["time"]):
        lead_clauses.append(_prefixed_clause("within", fields["time"], TIME_SELF_PREPOSITIONS))

    trailing_clauses = []
    if not _not_applicable(fields["scope"]):
        trailing_clauses.append(f"by targeting {fields['scope']['text']}")
    if not _not_applicable(fields["constraints"]):
        trailing_clauses.append(f"while subject to this constraint: {fields['constraints']['text']}")
    if not _not_applicable(fields["context"]):
        trailing_clauses.append(f"because {fields['context']['text']}")

    sentence = core
    if lead_clauses:
        sentence += " " + " ".join(lead_clauses)
    if trailing_clauses:
        sentence += " " + ", ".join(trailing_clauses)
    return sentence + "."


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
    mandatory_review = [role for role in ROLES if fields[role]["needs_review"]]

    return {
        "master_prompt": sentence,
        "fields": fields,
        "blanks": blanks,
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
