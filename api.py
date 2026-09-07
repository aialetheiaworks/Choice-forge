"""
Phase D of TOOLTIP_INTEGRATION_PLAN.md: the CHOICE flow as a JSON API, so a
standalone frontend can drive it instead of Streamlit. Every endpoint is a
thin wrapper over a function that already exists and is already tested --
no new logic lives here.

    POST /extract    query            -> 9 fields + the template master prompt
    POST /assemble   query + fields   -> the LLM-assembled master prompt
    POST /tooltip    master_prompt    -> Bucket Matching Engine reflection prompts
    POST /log        correction entry -> persists it (GitHub-backed, see correction_log)
    GET  /health     -> ok + model status

Run:
    pip install fastapi "uvicorn[standard]"
    uvicorn api:app --reload

app.py (the Streamlit prototype) is unaffected and still works; this is a
parallel interface, not a replacement, until the new frontend exists.
"""

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import bucket_client
import master_prompt_llm
from correction_log import log_correction
from pipeline import Pipeline, ROLES
from prompt_synthesis import render_sentence, synthesize_master_prompt

app = FastAPI(title="CHOICE Forge API", version="1.0")

# The frontend is a separate origin. Lock this to the real domain(s) before
# anything public -- mirrors the note in the bucket engine's own docs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_pipeline: Pipeline | None = None


def get_pipeline() -> Pipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = Pipeline()
    return _pipeline


class ExtractRequest(BaseModel):
    query: str = Field(min_length=1)


class FieldValue(BaseModel):
    text: str = ""
    blank: bool = False
    not_applicable: bool = False


class AssembleRequest(BaseModel):
    query: str = Field(min_length=1)
    # role -> {text, blank, not_applicable}; missing roles are treated as blank.
    fields: dict[str, FieldValue]


class TooltipRequest(BaseModel):
    master_prompt: str = Field(min_length=1)


class LogRequest(BaseModel):
    entry: dict[str, Any]


@app.get("/health")
def health():
    return {"status": "ok", "models_loaded": _pipeline is not None, "roles": ROLES}


@app.post("/extract")
def extract(req: ExtractRequest):
    """Everything the frontend needs to render the review-and-edit screen:
    - `fields`: raw pipeline output per role (value, status, confidence,
      source_text, flags) -- for the "see extraction details" view.
    - `display_fields`: role -> {text, blank, not_applicable, needs_review,
      multi_span, ...} -- the shape `/assemble` and the edit form use.
    - the deterministic template master prompt + its blank/review lists.
    """
    query = req.query.strip()
    result = get_pipeline().run(query)
    synth = synthesize_master_prompt(result)
    return {
        "query": query,
        "fields": result,
        "display_fields": synth["fields"],
        "template_master_prompt": synth["master_prompt"],
        "blanks": synth["blanks"],
        "low_confidence": synth["low_confidence"],
        "needs_review": synth["mandatory_review"],
        "possible_compound_query": synth["possible_compound_query"],
    }


@app.post("/assemble")
def assemble(req: AssembleRequest):
    """LLM-assembled master prompt from the user-confirmed field set.
    `template_master_prompt` is the deterministic fallback; `error` is set
    when the LLM call failed and the fallback is what to show."""
    final_fields = {
        role: req.fields.get(role, FieldValue(blank=True)).model_dump()
        for role in ROLES
    }
    text, error = master_prompt_llm.generate_master_prompt(req.query.strip(), final_fields)
    return {
        "master_prompt": text or render_sentence(final_fields),
        "template_master_prompt": render_sentence(final_fields),
        "used_llm": error is None,
        "error": error,
    }


@app.post("/tooltip")
def tooltip(req: TooltipRequest):
    """Proxy to the CHOICE Bucket Matching Engine. (The frontend could call
    it directly -- this keeps the base URL server-side and the response
    shape stable if the engine's changes.)"""
    ranked, error = bucket_client.get_tooltips(req.master_prompt)
    return {"ranked": ranked, "error": error}


@app.post("/log")
def log(req: LogRequest):
    """Persist one confirm/reject correction entry. Returns how it was
    stored ('github' | 'local_fallback') so the frontend can warn on the
    non-durable path, same as the Streamlit app does."""
    return log_correction(req.entry)
