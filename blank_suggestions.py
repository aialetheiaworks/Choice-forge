"""
Extension to Phase 3 of the CHOICE product vision (see CLAUDE.md): optional,
explicitly opt-in AI-generated suggestions for fields the extraction
pipeline left blank.

This exists specifically in response to 2026-08-06 stakeholder feedback
that wanted invented actor/context/constraint text folded straight into
the master prompt as if it were extracted fact -- doing that silently
would break the "never assume a value for an empty field" guarantee in
CLAUDE.md's Rules. Instead: a suggestion is generated only on explicit
user request (app.py's "Suggest values for blanks" button), labeled as an
unverified guess wherever shown, and never auto-applied -- the user must
tick a box to pull it into a field, same as typing it themselves.
correction_log.py's entries record `ai_suggested` per field so this can be
told apart from real user-supplied knowledge in any future Phase 5
training data.
"""

import json
import re

import llm_client
from pipeline import ROLES


def build_prompt(query, fields, blank_roles):
    """fields is shaped like prompt_synthesis.build_fields()'s output
    (role -> {"text":..., "blank":...}). Only non-blank fields are passed
    as "already found" context so the model doesn't ground itself on
    another field's own blank placeholder text."""
    known = "\n".join(
        f"- {role}: {fields[role]['text']}"
        for role in ROLES
        if role not in blank_roles and not fields[role]["blank"]
    )
    blanks_list = ", ".join(blank_roles)
    return (
        f'Original query: "{query}"\n\n'
        f"Fields already found:\n{known or '(none)'}\n\n"
        f"Blank fields needing suggestions: {blanks_list}"
    )


_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$")


def parse_suggestions(raw_text, blank_roles):
    """Best-effort JSON parse. Never raises -- a malformed LLM response
    degrading to "no suggestions" is safe; a fabricated field slipping
    through unlabeled would not be."""
    text = _CODE_FENCE_RE.sub("", raw_text.strip()).strip()
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {
        role: str(value).strip()
        for role, value in parsed.items()
        if role in blank_roles and str(value).strip()
    }


def get_suggestions(query, fields, blank_roles):
    """Calls the configured LLM provider for suggestions on the given blank
    roles. Raises whatever the provider raises (network/auth errors) --
    same convention as llm_client.generate_output; the caller (app.py) is
    responsible for catching and displaying these."""
    if not blank_roles:
        return {}
    prompt = build_prompt(query, fields, blank_roles)
    raw = llm_client.generate_suggestions(prompt)
    return parse_suggestions(raw, blank_roles)
