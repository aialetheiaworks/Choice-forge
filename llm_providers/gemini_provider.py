"""
Google Gemini provider. Requires GEMINI_API_KEY (or GOOGLE_API_KEY -- takes
precedence if both are set) in the environment -- never hardcode a key
here. Full reference: API_KEYS.md.
"""

import os

from google import genai

from llm_providers._shared import SYSTEM_PROMPT

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


def generate(master_prompt):
    """Raises whatever genai.Client().interactions.create() raises --
    llm_client.py's caller is responsible for catching it."""
    client = genai.Client()
    interaction = client.interactions.create(
        model=MODEL,
        system_instruction=SYSTEM_PROMPT,
        input=master_prompt,
    )
    return interaction.output_text
