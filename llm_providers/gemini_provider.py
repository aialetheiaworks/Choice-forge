"""
Google Gemini provider. Requires GEMINI_API_KEY (or GOOGLE_API_KEY -- takes
precedence if both are set) in the environment -- never hardcode a key
here. Full reference: API_KEYS.md.
"""

import os

from google import genai

from llm_providers._shared import SYSTEM_PROMPT

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


def generate(prompt, system_prompt=SYSTEM_PROMPT):
    """Raises whatever genai.Client().interactions.create() raises --
    llm_client.py's caller is responsible for catching it."""
    client = genai.Client()
    interaction = client.interactions.create(
        model=MODEL,
        system_instruction=system_prompt,
        input=prompt,
    )
    return interaction.output_text
