"""
Phase 4 of the CHOICE product vision (see CLAUDE.md "Agreed build order"):
sends a confirmed master prompt to Claude (Anthropic API) and returns the
actual answer to the user's original business query. Thin wrapper only --
no retries/caching beyond what the SDK already does by default.

Requires ANTHROPIC_API_KEY in the environment (see README.md). Never
hardcode a key here.
"""

import anthropic

MODEL = "claude-opus-5"

SYSTEM_PROMPT = (
    "You are a business strategy assistant. The user will give you a "
    "fully-specified objective statement, already clarified and confirmed "
    "by the stakeholder who asked it. Answer the objective directly and "
    "practically -- give a concrete, actionable response grounded only in "
    "what the objective states, not a restatement of the objective itself."
)


def generate_output(master_prompt):
    """Call Claude on a confirmed master prompt, return the response text.

    Raises whatever the Anthropic SDK raises (AuthenticationError,
    RateLimitError, etc.) -- the caller (app.py) is responsible for
    catching and displaying these to the user.
    """
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": master_prompt}],
    )
    return next(block.text for block in response.content if block.type == "text")
