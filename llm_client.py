"""
Phase 4 of the CHOICE product vision (see CLAUDE.md "Agreed build order"):
sends a confirmed master prompt to an LLM and returns its answer to the
user's original business query.

Which LLM actually runs the call is controlled entirely by the
LLM_PROVIDER environment variable -- see API_KEYS.md for the full
reference (every provider's env vars, defaults, and how to add a new
one). Swapping providers (e.g. Anthropic -> Gemini -> a local Ollama
model) never requires touching this file or app.py -- only API_KEYS.md
and the environment.
"""

import os

from dotenv import load_dotenv

from llm_providers import anthropic_provider, gemini_provider, ollama_provider

load_dotenv()  # no-op if there's no .env file

PROVIDERS = {
    "anthropic": anthropic_provider.generate,
    "gemini": gemini_provider.generate,
    "ollama": ollama_provider.generate,
}

# Temporary for testing -- see API_KEYS.md "Current default" before changing.
DEFAULT_PROVIDER = "gemini"


def generate_output(master_prompt):
    """Call the LLM_PROVIDER-configured provider on a confirmed master
    prompt, return the response text.

    Raises whatever the underlying provider raises -- the caller (app.py)
    is responsible for catching and displaying these to the user.
    """
    provider_name = os.environ.get("LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    if provider_name not in PROVIDERS:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider_name}'. "
            f"Valid options: {', '.join(sorted(PROVIDERS))}. See API_KEYS.md."
        )
    return PROVIDERS[provider_name](master_prompt)
