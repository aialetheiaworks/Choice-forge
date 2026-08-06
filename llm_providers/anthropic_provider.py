"""
Anthropic (Claude) provider. Requires ANTHROPIC_API_KEY in the environment
-- never hardcode a key here. Full reference: API_KEYS.md.
"""

import os

import anthropic

from llm_providers._shared import SYSTEM_PROMPT

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")


def generate(prompt, system_prompt=SYSTEM_PROMPT):
    """Raises whatever anthropic.Anthropic().messages.create() raises --
    llm_client.py's caller is responsible for catching it."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    return next(block.text for block in response.content if block.type == "text")
