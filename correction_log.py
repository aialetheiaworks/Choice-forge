"""
Phase 3 of the CHOICE product vision (see CLAUDE.md "Agreed build order"):
append-only log of every confirm/reject decision from app.py's master-prompt
review step. One JSON object per line, in the same convention as
data/seq2seq_pairs.jsonl. This is the training data Phase 5 retrains the
prompt-synthesis model on.

Persistence: writes go straight to this repo's data/corrections_log.jsonl
via the GitHub Contents API -- see README.md's "Correction logging" section
for the GITHUB_TOKEN setup this requires. A hosted Streamlit Cloud
container's local filesystem is ephemeral and wiped on every
redeploy/restart, so a plain local append (the pre-2026-08-16 behavior)
silently lost every real user's correction -- see CLAUDE.md's 2026-08-16
status entry. Local append is now only a same-process fallback used when
GitHub is unreachable or unconfigured (e.g. local dev with no token set);
that fallback is exactly what log_correction()'s return value tells the
caller to flag to the user, since on a hosted deployment it is NOT durable
across a redeploy.
"""

import base64
import json
import os
import urllib.error
import urllib.request

try:
    # Streamlit Community Cloud: secrets are set via the Cloud dashboard's
    # Secrets UI and only exposed through st.secrets, not as real env vars.
    # Mirror them into os.environ -- same pattern llm_client.py already
    # uses -- so this module works whether GITHUB_TOKEN arrives via .env,
    # shell env, or Cloud secrets. setdefault() makes this a harmless no-op
    # if llm_client.py already ran this same bridge earlier in import order.
    import streamlit as st

    for _key, _value in st.secrets.items():
        os.environ.setdefault(_key, str(_value))
except Exception:
    pass

LOG_PATH = os.path.join(os.path.dirname(__file__), "data", "corrections_log.jsonl")

GITHUB_REPO = "aialetheiaworks/Choice-forge"
GITHUB_FILE_PATH = "data/corrections_log.jsonl"
GITHUB_BRANCH = "main"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
GITHUB_TIMEOUT_SECONDS = 8
GITHUB_MAX_RETRIES = 2  # extra attempts after a 409 (concurrent-write conflict)


def _github_token():
    return os.environ.get("GITHUB_TOKEN")


def _github_request(method, url, token, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=GITHUB_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode())


def _append_via_github(entry, token):
    """Fetch the file's current content + SHA, append one JSON line, commit
    via the Contents API. On a 409 (another correction landed between our
    GET and PUT) re-fetches the latest SHA and retries, up to
    GITHUB_MAX_RETRIES extra times. Raises on final failure so the caller
    can fall back to a local append instead of losing the correction."""
    new_line = json.dumps(entry)
    for attempt in range(GITHUB_MAX_RETRIES + 1):
        current = _github_request(
            "GET", f"{GITHUB_API_URL}?ref={GITHUB_BRANCH}", token
        )
        current_content = base64.b64decode(current["content"]).decode()
        if current_content and not current_content.endswith("\n"):
            current_content += "\n"
        updated_content = current_content + new_line + "\n"
        body = {
            "message": f"chore: log correction from hosted session {entry['timestamp']}",
            "content": base64.b64encode(updated_content.encode()).decode(),
            "sha": current["sha"],
            "branch": GITHUB_BRANCH,
        }
        try:
            _github_request("PUT", GITHUB_API_URL, token, body=body)
            return
        except urllib.error.HTTPError as e:
            if e.code == 409 and attempt < GITHUB_MAX_RETRIES:
                continue
            raise


def _append_local(entry):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def log_correction(entry):
    """Persist one correction and report how. Tries the GitHub Contents API
    first -- the only path durable across a Streamlit Cloud redeploy --
    and falls back to a local append (not durable on a hosted deployment)
    if GITHUB_TOKEN is unset or the GitHub write fails after retries.
    Returns {"method": "github" | "local_fallback", "error": str | None}
    so the caller can warn the user whenever method != "github", per the
    "never silently lose a correction again" goal this replaces."""
    token = _github_token()
    if not token:
        _append_local(entry)
        return {"method": "local_fallback", "error": "GITHUB_TOKEN not configured"}
    try:
        _append_via_github(entry, token)
        return {"method": "github", "error": None}
    except Exception as e:
        _append_local(entry)
        return {"method": "local_fallback", "error": str(e)}
