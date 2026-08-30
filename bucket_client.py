"""
Phase B of TOOLTIP_INTEGRATION_PLAN.md: client for the CHOICE Bucket
Matching Engine -- a separate REST service that takes a confirmed master
prompt and returns up to ~7 "if you're speaking about X, also consider Y"
reflection prompts, matched against an 80-bucket business taxonomy. Those
prompts are CHOICE's think-harder mechanism now that the app no longer
generates an answer.

Uses stdlib urllib (same choice as correction_log.py -- no new dependency).
Never raises: get_tooltips() returns (ranked, error_or_None) so app.py can
degrade to "reflection prompts unavailable" instead of breaking the
confirmed view.

Config: BUCKET_API_URL overrides the default base URL (env or Streamlit
secrets -- the st.secrets->os.environ bridge in app.py / correction_log.py
covers the hosted case). Default points at the current Render deployment.
"""

import json
import os
import ssl
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://choice-bucket-matching.onrender.com"


def _ssl_context():
    """Some Python installs (notably the python.org macOS framework build)
    ship without a usable CA bundle, so a plain urlopen() over HTTPS fails
    with CERTIFICATE_VERIFY_FAILED. Prefer certifi's bundle when present
    (it's already an indirect dependency via requests/transformers), else
    fall back to the system default."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


_SSL_CONTEXT = _ssl_context()

# The free-tier Render instance spins down after ~15 min idle and reloads an
# NLP model + large vocabulary on the next request -- the service's own docs
# say the first call after that can take "minutes", not the usual ~50s. A
# short timeout here would turn every cold start into a spurious failure.
REQUEST_TIMEOUT_SECONDS = 150


def _base_url():
    return os.environ.get("BUCKET_API_URL", DEFAULT_BASE_URL).rstrip("/")


def get_tooltips(master_prompt):
    """POST the master prompt to /tooltip. Returns (ranked, error):
    - ranked: list of bucket dicts ({name, prompt, score, matched_terms,
      tooltip_line, ...}), already ordered by the service; [] on any problem.
    - error: None on success, else a short human-readable string.
    """
    text = (master_prompt or "").strip()
    if not text:
        return [], "master prompt was empty"

    body = json.dumps({"master_prompt": text}).encode()
    req = urllib.request.Request(
        f"{_base_url()}/tooltip",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(
            req, timeout=REQUEST_TIMEOUT_SECONDS, context=_SSL_CONTEXT
        ) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return [], f"bucket service returned HTTP {e.code}"
    except urllib.error.URLError as e:
        return [], f"could not reach the bucket service ({e.reason})"
    except (TimeoutError, json.JSONDecodeError) as e:
        return [], f"bucket service error ({e})"

    ranked = payload.get("ranked") if isinstance(payload, dict) else None
    if not isinstance(ranked, list):
        return [], "bucket service response was not in the expected shape"
    return ranked, None
