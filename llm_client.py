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

import streamlit as st
from dotenv import load_dotenv

from llm_providers import anthropic_provider, gemini_provider, ollama_provider
from llm_providers._shared import SUGGESTION_SYSTEM_PROMPT

load_dotenv()  # local dev: reads .env if present, no-op otherwise

try:
    # Streamlit Community Cloud: secrets are set via the Cloud dashboard's
    # Secrets UI and only exposed through st.secrets, not as real env vars.
    # Mirror them into os.environ so every provider module can keep reading
    # via os.environ.get(...) unchanged, whether run locally or deployed.
    # Raises StreamlitSecretNotFoundError locally when no secrets.toml
    # exists anywhere -- expected and fine, .env/shell env vars still work.
    for _key, _value in st.secrets.items():
        os.environ.setdefault(_key, str(_value))
except Exception:
    pass

PROVIDERS = {
    "anthropic": anthropic_provider.generate,
    "gemini": gemini_provider.generate,
    "ollama": ollama_provider.generate,
}

# Temporary for testing -- see API_KEYS.md "Current default" before changing.
DEFAULT_PROVIDER = "gemini"


def _provider_fn():
    provider_name = os.environ.get("LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    if provider_name not in PROVIDERS:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider_name}'. "
            f"Valid options: {', '.join(sorted(PROVIDERS))}. See API_KEYS.md."
        )
    return PROVIDERS[provider_name]


def generate_output(master_prompt):
    """Call the LLM_PROVIDER-configured provider on a confirmed master
    prompt, return the response text.

    Raises whatever the underlying provider raises -- the caller (app.py)
    is responsible for catching and displaying these to the user.
    """
    return _provider_fn()(master_prompt)


def generate_suggestions(prompt):
    """Call the LLM_PROVIDER-configured provider with the blank-suggestion
    system prompt instead of the Phase 4 objective-answering one (see
    blank_suggestions.py). Same raise/catch convention as generate_output.
    """
    return _provider_fn()(prompt, system_prompt=SUGGESTION_SYSTEM_PROMPT)
