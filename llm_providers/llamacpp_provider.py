"""
llama.cpp provider -- the local Horizon model server (Llama 3.1 8B + the
Horizon LoRA adapter, served by llama-server; see Horizon/serving/README.md).
No API key, nothing leaves the machine.

Calls /completion with the Llama 3.1 chat template built by hand, the same
way Horizon does: llama-server's /v1/chat/completions adds a "Cutting
Knowledge / Today Date" header the adapter never saw in training.

    LLAMACPP_URL         default http://localhost:8089
    LLAMACPP_LORA_SCALE  default 1.0 (0 = base Llama, adapter off)
"""

import os

import requests

from llm_providers._shared import SYSTEM_PROMPT

URL = os.environ.get("LLAMACPP_URL", "http://localhost:8089").rstrip("/")
LORA_SCALE = float(os.environ.get("LLAMACPP_LORA_SCALE", "1.0"))


def _prompt(system, user):
    return ("<|begin_of_text|>"
            f"<|start_header_id|>system<|end_header_id|>\n\n{system.strip()}<|eot_id|>"
            f"<|start_header_id|>user<|end_header_id|>\n\n{user.strip()}<|eot_id|>"
            "<|start_header_id|>assistant<|end_header_id|>\n\n")


def generate(prompt, system_prompt=SYSTEM_PROMPT, max_tokens=None, thinking_level=None):
    """Raises on connection/HTTP errors -- llm_client.py's caller catches it.
    thinking_level is accepted for a uniform provider signature but ignored."""
    body = {
        "prompt": _prompt(system_prompt, prompt),
        "temperature": 0,
        "n_predict": max_tokens or 400,
        "lora": [{"id": 0, "scale": LORA_SCALE}],
    }
    resp = requests.post(f"{URL}/completion", json=body, timeout=300)
    resp.raise_for_status()
    return resp.json()["content"]
