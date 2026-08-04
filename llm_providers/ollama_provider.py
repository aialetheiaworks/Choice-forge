"""
Ollama provider -- runs against a local Ollama server, no API key needed.
The model must already be pulled locally (`ollama pull <model>`) before
this will work. Full reference: API_KEYS.md.
"""

import os

from ollama import Client

from llm_providers._shared import SYSTEM_PROMPT

HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")


def generate(master_prompt):
    """Raises whatever ollama.Client().chat() raises (e.g. a connection
    error if no local server is running) -- llm_client.py's caller is
    responsible for catching it."""
    client = Client(host=HOST)
    response = client.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": master_prompt},
        ],
    )
    return response.message.content
