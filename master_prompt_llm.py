"""
Phase A of TOOLTIP_INTEGRATION_PLAN.md: replaces the old final "generate an
answer" step (Phase 4). Takes the user's already-confirmed extraction
fields + their original query and asks the configured LLM to assemble them
into one well-formed objective statement ("master prompt") -- rephrasing
only, never inventing a value for anything the user left blank or marked
not-applicable.

The deterministic template (prompt_synthesis.render_sentence) still runs
first and is what the user reviews and edits; this is a single polish pass
on the confirmed field set, and the caller falls back to the template
sentence if the LLM call fails.

Which provider runs the call is controlled entirely by LLM_PROVIDER -- see
API_KEYS.md. The system prompt lives in llm_providers/_shared.py
(MASTER_PROMPT_SYSTEM_PROMPT).
"""

import re

import llm_client

# Order the fields are listed to the model: subject -> verb -> target ->
# quantifiers -> qualifiers, so the model sees them in roughly the order a
# well-formed sentence uses them.
FIELD_ORDER = [
    "actor", "intent", "object", "measure", "magnitude",
    "time", "scope", "constraints", "context",
]


def build_user_message(query, final_fields, omitted=()):
    """final_fields is app.py's per-role dict at confirm time:
    {role: {"text": str, "blank": bool, "not_applicable": bool,
    "confirmed": bool}}. `confirmed` marks a field the owner typed or
    edited (CHOICE's gateway sets it); those are labelled for the model.
    Emits a compact payload -- no source spans, no confidence, no guard
    notes -- since the model only needs the values it's allowed to use.
    `omitted`: roles a previous attempt left out, named so the retry fixes it."""
    lines = [f'Original query: "{query}"', "", "Confirmed fields:"]
    for role in FIELD_ORDER:
        f = final_fields.get(role, {})
        if f.get("not_applicable"):
            lines.append(f"- {role}: NOT APPLICABLE")
        elif f.get("blank") or not str(f.get("text", "")).strip():
            lines.append(f"- {role}: MISSING")
        else:
            owner = " (stated by the owner)" if f.get("confirmed") else ""
            lines.append(f"- {role}{owner}: {str(f['text']).strip()}")
    if omitted:
        lines += ["", "Your previous statement left out: " + ", ".join(omitted)
                  + ". Include every one of them this time."]
    lines += ["", "Write the master prompt now."]
    return "\n".join(lines)


# --- completeness: the model must not drop confirmed content (found
# 2026-09-10 on llama3.2:3b and again 2026-10-08 in a CHOICE audit, where a
# whole constraints and context field vanished from the statement).
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_WORD = re.compile(r"[a-z][a-z'-]{3,}")
_STOP = {"that", "this", "with", "from", "have", "will", "into", "than", "they",
         "their", "them", "were", "been", "being", "about", "over", "under",
         "only", "also", "more", "most", "very", "much", "some", "such", "each",
         "what", "when", "which", "while", "would", "could", "should", "there"}


def _numbers(text):
    return {n.replace(",", "").rstrip(".") for n in _NUMBER.findall(text)}


def _stems(text):
    return {w[:5] for w in _WORD.findall(text.lower()) if w not in _STOP}


def coverage(statement, field_text):
    """How much of a field the statement carries, 0..1: the lower of the
    share of its figures present and the share of its content words present
    (5-letter stems, so 'supplies' matches 'supply')."""
    nums, words = _numbers(field_text), _stems(field_text)
    num_share = len(nums & _numbers(statement)) / len(nums) if nums else 1.0
    word_share = len(words & _stems(statement)) / len(words) if words else 1.0
    return min(num_share, word_share)


def covers(statement, field_text):
    """Present = every figure kept and at least half the content words.
    Paraphrase-tolerant, omission-strict."""
    return _numbers(field_text) <= _numbers(statement) and coverage(statement, field_text) >= 0.5


# The statement speaks as "we", so the actor is carried by the voice, not its words.
_CHECKED = [r for r in FIELD_ORDER if r != "actor"]


def omitted_fields(statement, final_fields):
    return [role for role in _CHECKED
            if (f := final_fields.get(role, {})) and not f.get("blank") and not f.get("not_applicable")
            and str(f.get("text", "")).strip() and not covers(statement, str(f["text"]))]


_LABELS = {"actor": "Who", "object": "What", "intent": "Goal", "measure": "Measure",
           "magnitude": "Figures", "time": "Timing", "scope": "Scope",
           "constraints": "Constraints", "context": "Context"}


def with_owner_facts(statement, final_fields, omitted):
    """Last resort after the retry: append, in the owner's own words, any
    owner-stated field the model still left out. Extracted-but-unconfirmed
    fields are not forced in -- the extractor can be wrong; the owner can't."""
    tail = [f"{_LABELS[r]}: {str(final_fields[r]['text']).strip().rstrip('.')}."
            for r in omitted if final_fields[r].get("confirmed")
            # mostly missing only: re-appending a field that lost one detail would repeat it
            and coverage(statement, str(final_fields[r]["text"])) < 0.5]
    return " ".join([statement.rstrip()] + tail) if tail else statement


# One retry covers a transient network blip / rate-limit without making the
# confirm step wait through a long back-off.
_MAX_ATTEMPTS = 2


def generate_master_prompt(query, final_fields):
    """Returns (master_prompt_text, error_or_None). On any failure returns
    (None, error_string) so the caller can fall back to the deterministic
    template sentence instead of losing the confirm action. A statement
    that drops a confirmed field gets one corrective retry; owner-stated
    fields still missing after that are appended in the owner's words."""
    text, error = _generate(build_user_message(query, final_fields))
    if text is None:
        return None, error
    omitted = omitted_fields(text, final_fields)
    if omitted:  # one corrective retry, naming what was dropped
        retry, _ = _generate(build_user_message(query, final_fields, omitted))
        if retry and len(omitted_fields(retry, final_fields)) < len(omitted):
            text, omitted = retry, omitted_fields(retry, final_fields)
    return with_owner_facts(text, final_fields, omitted), None


def _generate(message):
    last_error = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            text = llm_client.generate_master_prompt(message)
            text = (text or "").strip().strip('"').strip()
            if text:
                return text, None
            last_error = "LLM returned an empty response"
        except Exception as e:  # network / auth / provider -- see API_KEYS.md
            last_error = str(e)
    return None, last_error
