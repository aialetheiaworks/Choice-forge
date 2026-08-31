"""
Google Gemini provider. Requires GEMINI_API_KEY (or GOOGLE_API_KEY -- takes
precedence if both are set) in the environment -- never hardcode a key
here. Full reference: API_KEYS.md.
"""

import os

from google import genai

from llm_providers._shared import SYSTEM_PROMPT

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


def generate(prompt, system_prompt=SYSTEM_PROMPT, max_tokens=None, thinking_level=None):
    """Raises whatever genai.Client().interactions.create() raises --
    llm_client.py's caller is responsible for catching it.

    thinking_level: one of "minimal"/"low"/"medium"/"high" -- gemini-3.x
    models are reasoning models that spend (billed, latency-adding)
    thinking tokens before any visible output. For a pure rephrasing task
    like master-prompt assembly, "minimal" cuts a ~30s call to a few
    seconds. Ignored by providers that don't have the concept.
    """
    client = genai.Client()
    gen_config = {}
    if max_tokens:
        gen_config["max_output_tokens"] = max_tokens
    if thinking_level:
        gen_config["thinking_level"] = thinking_level
    kwargs = {
        "model": MODEL,
        "system_instruction": system_prompt,
        "input": prompt,
    }
    if gen_config:
        kwargs["generation_config"] = gen_config
    interaction = client.interactions.create(**kwargs)
    return interaction.output_text
