"""
Ollama provider -- runs against a local Ollama server, no API key needed.
The model must already be pulled locally (`ollama pull <model>`) before
this will work. Full reference: API_KEYS.md.
"""

import os

from ollama import Client

from llm_providers._shared import SYSTEM_PROMPT

HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
# qwen2.5:7b-instruct: chosen for the master-prompt-assembly workload -- a
# short, constraint-heavy rephrase (use only the given fields, omit
# MISSING/NOT APPLICABLE, invent nothing). Strong instruction-following at
# 7B, non-reasoning (no wasted think tokens), fits an M4/16GB alongside the
# spaCy+CRF+T5 pipeline. See CLAUDE.md 2026-09-03 for the selection rationale
# and the data/eval_master_prompt_faithfulness.py check it was gated on.
MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct")


def generate(prompt, system_prompt=SYSTEM_PROMPT, max_tokens=None, thinking_level=None):
    """Raises whatever ollama.Client().chat() raises (e.g. a connection
    error if no local server is running) -- llm_client.py's caller is
    responsible for catching it. thinking_level is accepted for a uniform
    provider signature but ignored here."""
    client = Client(host=HOST)
    response = client.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        options={"num_predict": max_tokens} if max_tokens else None,
    )
    return response.message.content
