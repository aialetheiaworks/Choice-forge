"""
Google Gemini provider. Requires GEMINI_API_KEY (or GOOGLE_API_KEY -- takes
precedence if both are set) in the environment -- never hardcode a key
here. Full reference: API_KEYS.md.
"""

import os

from google import genai

from llm_providers._shared import SYSTEM_PROMPT

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


def generate(prompt, system_prompt=SYSTEM_PROMPT, max_tokens=None):
    """Raises whatever genai.Client().interactions.create() raises --
    llm_client.py's caller is responsible for catching it."""
    client = genai.Client()
    kwargs = {
        "model": MODEL,
        "system_instruction": system_prompt,
        "input": prompt,
    }
    if max_tokens:
        kwargs["generation_config"] = {"max_output_tokens": max_tokens}
    interaction = client.interactions.create(**kwargs)
    return interaction.output_text
