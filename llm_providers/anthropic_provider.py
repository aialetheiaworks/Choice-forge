"""
Anthropic (Claude) provider. Requires ANTHROPIC_API_KEY in the environment
-- never hardcode a key here. Full reference: API_KEYS.md.
"""

import os

import anthropic

from llm_providers._shared import SYSTEM_PROMPT

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")


def generate(prompt, system_prompt=SYSTEM_PROMPT, max_tokens=None, thinking_level=None):
    """Raises whatever anthropic.Anthropic().messages.create() raises --
    llm_client.py's caller is responsible for catching it.

    thinking_level is accepted for a uniform provider signature but ignored
    here -- claude-opus-5 is not in extended-thinking mode by default."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens or 4096,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    return next(block.text for block in response.content if block.type == "text")
