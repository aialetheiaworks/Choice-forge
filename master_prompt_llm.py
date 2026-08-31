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

import llm_client

# Order the fields are listed to the model: subject -> verb -> target ->
# quantifiers -> qualifiers, so the model sees them in roughly the order a
# well-formed sentence uses them.
FIELD_ORDER = [
    "actor", "intent", "object", "measure", "magnitude",
    "time", "scope", "constraints", "context",
]


def build_user_message(query, final_fields):
    """final_fields is app.py's per-role dict at confirm time:
    {role: {"text": str, "blank": bool, "not_applicable": bool}}.
    Emits a compact payload -- no source spans, no confidence, no guard
    notes -- since the model only needs the values it's allowed to use."""
    lines = [f'Original query: "{query}"', "", "Confirmed fields:"]
    for role in FIELD_ORDER:
        f = final_fields.get(role, {})
        if f.get("not_applicable"):
            lines.append(f"- {role}: NOT APPLICABLE")
        elif f.get("blank") or not str(f.get("text", "")).strip():
            lines.append(f"- {role}: MISSING")
        else:
            lines.append(f"- {role}: {str(f['text']).strip()}")
    lines += ["", "Write the master prompt now."]
    return "\n".join(lines)


# One retry covers a transient network blip / rate-limit without making the
# confirm step wait through a long back-off.
_MAX_ATTEMPTS = 2


def generate_master_prompt(query, final_fields):
    """Returns (master_prompt_text, error_or_None). On any failure returns
    (None, error_string) so the caller can fall back to the deterministic
    template sentence instead of losing the confirm action."""
    message = build_user_message(query, final_fields)
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
