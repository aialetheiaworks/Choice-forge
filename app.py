"""
Streamlit UI for stakeholders to test the CHOICE Forge pipeline without
touching the command line. Loads the trained CRF + T5 models once (cached
across reruns) and lets the user type a query and see the structured
9-field output.

Install:
    pip3 install streamlit

Run:
    streamlit run app.py
"""

import datetime
import html
import json
import os
import statistics

import streamlit as st

import llm_client
from correction_log import log_correction
from pipeline import Pipeline, ROLES
from prompt_synthesis import (
    NOT_APPLICABLE_ELIGIBLE_ROLES,
    render_sentence,
    synthesize_master_prompt,
)

st.set_page_config(page_title="CHOICE Forge", page_icon="🧭", layout="wide")

# Design system: "field survey instrument" -- CHOICE Forge reads a vague
# business ask like a surveyor's transit reads terrain, resolving it into
# precise bearings (the 9 fields) each with a stated confidence/tolerance.
# Space Grotesk labels the instrument itself; Source Serif sets the actual
# document content (query, master prompt, LLM output); JetBrains Mono is
# the readout face for numbers, spans, and status tags. The tick-mark
# confidence gauge (replacing a plain progress bar) is the one signature
# element repeated across every field card.
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=JetBrains+Mono:wght@400;500;700&display=swap');

    :root {
        --cf-ink: #12181A;
        --cf-panel: #1B2326;
        --cf-panel-2: #212B2E;
        --cf-paper: #EDE6D3;
        --cf-paper-dim: #A8A093;
        --cf-brass: #C08A3E;
        --cf-brass-bright: #D9A75C;
        --cf-verdigris: #5E8C7C;
        --cf-rust: #B24A3D;
        --cf-line: rgba(237, 230, 211, 0.14);
    }

    [data-testid="stAppViewContainer"], [data-testid="stApp"], [data-testid="stHeader"] {
        background: var(--cf-ink) !important;
    }
    [data-testid="stMainBlockContainer"] {
        max-width: 1180px;
        padding-top: 2.2rem;
    }
    body, [data-testid="stAppViewContainer"] { color: var(--cf-paper); }

    h1, h2, h3, [data-testid="stHeading"] p, .cf-section-title, .cf-card-label,
    .cf-metric-label, .cf-instrument-tag {
        font-family: 'Space Grotesk', sans-serif !important;
    }
    .stMarkdown p, [data-testid="stMarkdownContainer"] p, .cf-value, .cf-fieldnote,
    .cf-tagline, [data-testid="stCheckbox"] p, [data-testid="stAlert"] p {
        font-family: 'Source Serif 4', Georgia, serif !important;
    }
    code, .cf-readout, .cf-source code, .cf-metric-value {
        font-family: 'JetBrains Mono', monospace !important;
    }

    hr { border-color: var(--cf-line) !important; }
    [data-testid="stCaptionContainer"] { color: var(--cf-paper-dim) !important; }

    /* --- header --- */
    .cf-header { margin-bottom: 0.4rem; }
    .cf-wordmark {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.1rem;
        font-weight: 700;
        color: var(--cf-paper);
    }
    .cf-compass { margin-right: 0.35rem; }
    .cf-forge { color: var(--cf-brass-bright); }
    .cf-tagline {
        color: var(--cf-paper-dim);
        font-size: 1rem;
        margin: 0.5rem 0 1rem 0;
        max-width: 68ch;
    }
    .cf-tag-row { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.6rem; }
    .cf-instrument-tag {
        display: inline-block;
        padding: 0.18rem 0.6rem;
        border: 1px solid var(--cf-brass);
        border-radius: 3px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--cf-brass-bright);
        background: rgba(192, 138, 62, 0.08);
    }
    .cf-instrument-tag.cf-tag-verdigris {
        border-color: var(--cf-verdigris);
        color: var(--cf-verdigris);
        background: rgba(94, 140, 124, 0.1);
    }

    /* --- section titles --- */
    .cf-section-title {
        font-size: 1.28rem;
        font-weight: 700;
        margin-top: 0.3rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid var(--cf-line);
    }
    .cf-section-caption {
        font-family: 'Source Serif 4', serif;
        color: var(--cf-paper-dim);
        font-size: 0.92rem;
        margin: 0.5rem 0 1rem 0;
    }
    .cf-section-caption code {
        color: var(--cf-brass-bright);
        background: rgba(192, 138, 62, 0.1);
        padding: 0.05rem 0.3rem;
        border-radius: 2px;
    }
    .cf-section-caption strong { color: var(--cf-brass-bright); }

    /* --- example pills (st.pills -> stButtonGroup) --- */
    [data-testid="stButtonGroup"] button {
        background: var(--cf-panel) !important;
        border: 1px solid var(--cf-line) !important;
        color: var(--cf-paper) !important;
        border-radius: 3px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.78rem !important;
    }
    [data-testid="stButtonGroup"] button:hover {
        border-color: var(--cf-brass) !important;
        color: var(--cf-brass-bright) !important;
    }
    [data-testid="stButtonGroup"] button[aria-checked="true"] {
        background: rgba(192, 138, 62, 0.16) !important;
        border-color: var(--cf-brass) !important;
        color: var(--cf-brass-bright) !important;
    }

    /* --- text inputs / areas --- */
    [data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input {
        background: var(--cf-panel-2) !important;
        color: var(--cf-paper) !important;
        border: 1px solid var(--cf-line) !important;
        border-radius: 4px !important;
        font-family: 'Source Serif 4', serif !important;
    }
    [data-testid="stTextArea"] textarea:focus, [data-testid="stTextInput"] input:focus {
        border-color: var(--cf-brass) !important;
        box-shadow: 0 0 0 1px var(--cf-brass) !important;
    }
    [data-testid="stWidgetLabel"] p {
        font-size: 0.76rem !important;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--cf-paper-dim) !important;
    }

    /* --- buttons --- */
    button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-primaryFormSubmit"] {
        background: var(--cf-brass) !important;
        border: 1px solid var(--cf-brass) !important;
        color: #14181A !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        border-radius: 4px !important;
    }
    button[data-testid="stBaseButton-primary"]:hover,
    button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
        background: var(--cf-brass-bright) !important;
        border-color: var(--cf-brass-bright) !important;
    }
    button[data-testid="stBaseButton-secondary"],
    button[data-testid="stBaseButton-secondaryFormSubmit"],
    [data-testid="stDownloadButton"] button {
        background: transparent !important;
        border: 1px solid var(--cf-line) !important;
        color: var(--cf-paper) !important;
        font-family: 'Space Grotesk', sans-serif !important;
        border-radius: 4px !important;
    }
    button[data-testid="stBaseButton-secondary"]:hover,
    button[data-testid="stBaseButton-secondaryFormSubmit"]:hover,
    [data-testid="stDownloadButton"] button:hover {
        border-color: var(--cf-rust) !important;
        color: var(--cf-rust) !important;
    }
    button:disabled { opacity: 0.4 !important; }

    /* --- metric tiles --- */
    .cf-metric-row { display: flex; gap: 1rem; margin: 0.6rem 0 1.4rem 0; flex-wrap: wrap; }
    .cf-metric {
        background: var(--cf-panel);
        border: 1px solid var(--cf-line);
        border-radius: 4px;
        padding: 0.7rem 1.1rem;
        min-width: 150px;
    }
    .cf-metric-value { font-size: 1.5rem; font-weight: 700; color: var(--cf-brass-bright); }
    .cf-metric-label {
        font-size: 0.66rem; letter-spacing: 0.08em; text-transform: uppercase;
        color: var(--cf-paper-dim); margin-top: 0.15rem;
    }

    /* --- field card grid (the readout instrument) --- */
    .cf-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.9rem;
        margin-bottom: 1.4rem;
    }
    @media (max-width: 900px) { .cf-grid { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 620px) { .cf-grid { grid-template-columns: 1fr; } }

    .cf-card {
        background: var(--cf-panel);
        border: 1px solid var(--cf-line);
        border-radius: 5px;
        padding: 0.85rem 1rem;
    }
    .cf-card-label {
        font-size: 0.7rem; font-weight: 700; letter-spacing: 0.09em;
        text-transform: uppercase; color: var(--cf-brass-bright);
        margin-bottom: 0.4rem;
    }
    .cf-value { font-size: 1.05rem; line-height: 1.35; margin-bottom: 0.5rem; }
    .cf-value.cf-missing { color: var(--cf-paper-dim); font-style: italic; font-size: 0.92rem; }

    .cf-tags { display: flex; align-items: center; gap: 0.55rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
    .cf-tag {
        display: inline-block; padding: 0.1rem 0.5rem; border-radius: 3px;
        font-size: 0.64rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;
    }
    .cf-tag-explicit { background: rgba(94, 140, 124, 0.18); color: var(--cf-verdigris); }
    .cf-tag-missing { background: rgba(178, 74, 61, 0.16); color: var(--cf-rust); }
    .cf-readout { font-size: 0.72rem; color: var(--cf-paper-dim); }

    /* signature element: tick-mark confidence gauge, not a smooth progress bar */
    .cf-gauge { display: flex; gap: 2px; margin-bottom: 0.55rem; }
    .cf-tick { flex: 1; height: 5px; border-radius: 1px; background: var(--cf-line); }
    .cf-tick-high { background: var(--cf-verdigris); }
    .cf-tick-med { background: var(--cf-brass); }
    .cf-tick-low { background: var(--cf-rust); }

    .cf-source { font-size: 0.74rem; color: var(--cf-paper-dim); word-break: break-word; }
    .cf-source code {
        background: rgba(237, 230, 211, 0.06); padding: 0.05rem 0.3rem; border-radius: 2px;
    }
    .cf-note { margin-top: 0.5rem; font-size: 0.76rem; padding: 0.35rem 0.55rem; border-radius: 3px; }
    .cf-note-flag { background: rgba(178, 74, 61, 0.12); color: var(--cf-rust); }
    .cf-note-auto { background: rgba(192, 138, 62, 0.1); color: var(--cf-brass-bright); }

    /* --- master prompt field note --- */
    .cf-fieldnote {
        background: var(--cf-panel-2);
        border-left: 3px solid var(--cf-brass);
        border-radius: 3px;
        padding: 0.9rem 1.1rem;
        font-family: 'Source Serif 4', serif;
        font-size: 1.05rem;
        line-height: 1.6;
        margin-bottom: 1rem;
    }

    /* --- confirm/reject form --- */
    [data-testid="stForm"] {
        background: var(--cf-panel) !important;
        border: 1px solid var(--cf-line) !important;
        border-radius: 6px !important;
        padding: 1.2rem 1.3rem !important;
    }
    [data-testid="stCheckbox"] p {
        font-size: 0.88rem !important; color: var(--cf-paper) !important;
    }
    [data-testid="stExpander"], [data-testid="stJson"] {
        border: 1px solid var(--cf-line) !important;
        border-radius: 4px !important;
        background: var(--cf-panel) !important;
    }
    [data-testid="stAlert"] { border-radius: 5px !important; }

    /* accessibility floor: keep focus visible, don't rely on motion */
    button:focus-visible, input:focus-visible, textarea:focus-visible {
        outline: 2px solid var(--cf-brass) !important;
        outline-offset: 1px;
    }
    @media (prefers-reduced-motion: no-preference) {
        .cf-card, [data-testid="stButtonGroup"] button, button[data-testid^="stBaseButton"] {
            transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

ROLE_ICONS = {
    "actor": "🧑‍💼",
    "object": "📦",
    "intent": "🎯",
    "scope": "🗺️",
    "measure": "📏",
    "magnitude": "📈",
    "time": "⏱️",
    "constraints": "🚧",
    "context": "🧩",
}


def confidence_tier(conf):
    if conf >= 0.7:
        return "high", "High"
    if conf >= 0.4:
        return "med", "Medium"
    return "low", "Low"


def section_header(title, caption_html=None):
    block = f'<div class="cf-section-title">{html.escape(title)}</div>'
    if caption_html:
        block += f'<div class="cf-section-caption">{caption_html}</div>'
    st.markdown(block, unsafe_allow_html=True)


def _confidence_gauge(conf, tier):
    filled = round(min(max(conf, 0.0), 1.0) * 10)
    ticks = "".join(
        f'<span class="cf-tick cf-tick-{tier}"></span>' if i < filled else '<span class="cf-tick"></span>'
        for i in range(10)
    )
    return f'<div class="cf-gauge">{ticks}</div>'


def _field_card_html(role, icon, r):
    label = html.escape(role)
    if r["status"] == "missing":
        body = (
            f'<div class="cf-card-label">{icon} {label}</div>'
            '<div class="cf-value cf-missing">not surveyed — absent from query</div>'
            '<div class="cf-tags"><span class="cf-tag cf-tag-missing">missing</span></div>'
        )
    else:
        conf = r["confidence"]
        tier, tier_label = confidence_tier(conf)
        value_display = html.escape(str(r["value"]))
        source_display = html.escape(str(r["source_text"]))
        note = ""
        if r["flagged_for_review"]:
            note = f'<div class="cf-note cf-note-flag">⚠ flagged — {html.escape(r["guard_note"])}</div>'
        elif r["guard_note"]:
            note = f'<div class="cf-note cf-note-auto">auto-corrected — {html.escape(r["guard_note"])}</div>'
        body = (
            f'<div class="cf-card-label">{icon} {label}</div>'
            f'<div class="cf-value">{value_display}</div>'
            '<div class="cf-tags">'
            f'<span class="cf-tag cf-tag-explicit">{html.escape(r["status"])}</span>'
            f'<span class="cf-readout">{tier_label} · {conf:.2f}</span>'
            "</div>"
            f"{_confidence_gauge(conf, tier)}"
            f'<div class="cf-source">src <code>{source_display}</code></div>'
            f"{note}"
        )
    return f'<div class="cf-card">{body}</div>'


@st.cache_resource(show_spinner="Loading models (spaCy + CRF + T5)...")
def load_pipeline():
    return Pipeline()


EXAMPLES = [
    "Cut support ticket backlog by 40% for enterprise accounts within the next sprint.",
    "Marketing wants to grow trial-to-paid conversion for self-serve signups from 8% to 15% before the holiday season, without increasing the ad spend budget.",
    "Our field sales team needs to onboard 1,200 kirana stores in Pune onto the B2B ordering app by the end of Q3, using only the existing incentive budget.",
    "Acme Corp wants to expand into three new markets by Q3 without exceeding the current marketing budget.",
    "Reduce operating costs by 10% without letting service quality slip below current levels.",
    "Reduce churn unless it requires cutting the support team.",
    "We want to increase market share in the northeast region by 8 points next fiscal year while keeping customer acquisition cost flat.",
]

if "query_text" not in st.session_state:
    st.session_state.query_text = ""
st.session_state.setdefault("run_id", 0)


def _apply_example():
    picked = st.session_state.get("example_pick")
    if picked:
        st.session_state.query_text = picked


pipe = load_pipeline()

st.markdown(
    """
    <div class="cf-header">
      <div class="cf-wordmark"><span class="cf-compass">🧭</span>CHOICE <span class="cf-forge">Forge</span></div>
      <div class="cf-tagline">Turns a plain-English business ask into 9 structured fields — actor,
      object, intent, scope, measure, magnitude, time, constraints, context.</div>
      <div class="cf-tag-row">
        <span class="cf-instrument-tag">spaCy</span>
        <span class="cf-instrument-tag">CRF</span>
        <span class="cf-instrument-tag">T5</span>
        <span class="cf-instrument-tag cf-tag-verdigris">100% local</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

st.pills(
    "Try an example, or write your own below:",
    EXAMPLES,
    selection_mode="single",
    key="example_pick",
    on_change=_apply_example,
)

query = st.text_area(
    "Business query",
    key="query_text",
    height=100,
    placeholder="e.g. Reduce warehouse picking errors by 15% for the night shift crew before Q4.",
)

run = st.button("Run", type="primary", disabled=not query.strip())

if run and query.strip():
    with st.spinner("Extracting..."):
        result = pipe.run(query.strip())
    st.session_state.last_result = result
    st.session_state.last_query = query.strip()
    st.session_state.run_id += 1
    for key in ("last_decision", "last_master_prompt_final", "llm_output", "llm_error"):
        st.session_state.pop(key, None)

result = st.session_state.get("last_result")
synth = synthesize_master_prompt(result) if result else None

if result:
    section_header("Result")

    found_roles = [r for r in ROLES if result[r]["status"] != "missing"]
    avg_conf = (
        statistics.mean(result[r]["confidence"] for r in found_roles)
        if found_roles
        else 0.0
    )
    flagged_count = sum(1 for r in ROLES if result[r]["flagged_for_review"])

    st.markdown(
        '<div class="cf-metric-row">'
        '<div class="cf-metric">'
        f'<div class="cf-metric-value">{len(found_roles)}/{len(ROLES)}</div>'
        '<div class="cf-metric-label">fields found</div>'
        "</div>"
        '<div class="cf-metric">'
        f'<div class="cf-metric-value">{avg_conf:.2f}</div>'
        '<div class="cf-metric-label">avg. confidence</div>'
        "</div>"
        '<div class="cf-metric">'
        f'<div class="cf-metric-value">{flagged_count}</div>'
        '<div class="cf-metric-label">flagged</div>'
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    cards_html = "".join(
        _field_card_html(role, ROLE_ICONS.get(role, "🔹"), result[role]) for role in ROLES
    )
    st.markdown(f'<div class="cf-grid">{cards_html}</div>', unsafe_allow_html=True)

    dl_col, exp_col = st.columns([1, 3])
    dl_col.download_button(
        "⬇️ Download JSON",
        data=json.dumps(result, indent=2),
        file_name="choice_forge_result.json",
        mime="application/json",
    )
    with st.expander("Raw JSON"):
        st.json(result)

    st.divider()
    section_header(
        "Master Prompt",
        "Fill in any blanks and correct anything the pipeline got wrong, then "
        "Confirm or Reject. Every decision is logged and becomes training data "
        "for a future prompt-synthesis model (Phase 5).",
    )

    run_id = st.session_state.run_id
    st.markdown(
        f'<div class="cf-fieldnote">{html.escape(synth["master_prompt"])}</div>',
        unsafe_allow_html=True,
    )

    with st.form(f"master_prompt_form_{run_id}"):
        for role in ROLES:
            f = synth["fields"][role]
            icon = ROLE_ICONS.get(role, "🔹")
            label = f"{icon} {role}" + (" ⚠️" if f["needs_review"] else "")
            if f["blank"]:
                if role in NOT_APPLICABLE_ELIGIBLE_ROLES:
                    st.checkbox(
                        f"Not applicable to this query — {role} was never stated",
                        key=f"na_{role}_{run_id}",
                    )
                st.text_input(label, value="", placeholder=f["text"], key=f"field_{role}_{run_id}")
            else:
                st.text_input(label, value=f["text"], key=f"field_{role}_{run_id}")

        reject_reason = st.text_area(
            "Reject reason (optional)", key=f"reject_reason_{run_id}"
        )

        confirm_col, reject_col = st.columns(2)
        confirmed = confirm_col.form_submit_button("✅ Confirm", type="primary")
        rejected = reject_col.form_submit_button("❌ Reject")

    if confirmed or rejected:
        final_fields = {}
        log_fields = {}
        for role in ROLES:
            orig = synth["fields"][role]
            not_applicable = (
                role in NOT_APPLICABLE_ELIGIBLE_ROLES
                and st.session_state.get(f"na_{role}_{run_id}", False)
            )
            submitted = st.session_state[f"field_{role}_{run_id}"].strip()
            user_edited = (
                not not_applicable
                and bool(submitted)
                and (orig["blank"] or submitted != orig["text"])
            )

            if not_applicable:
                resolved_text, resolved_blank = "", True
            else:
                resolved_text = submitted if user_edited else orig["text"]
                resolved_blank = False if user_edited else orig["blank"]

            final_fields[role] = {
                "text": resolved_text,
                "blank": resolved_blank,
                "not_applicable": not_applicable,
            }
            log_fields[role] = {
                "original_value": result[role]["value"],
                "original_status": result[role]["status"],
                "original_confidence": result[role]["confidence"],
                "blank": resolved_blank,
                "not_applicable": not_applicable,
                "needs_review": orig["needs_review"],
                "multi_span": orig["multi_span"],
                "final_value": None if resolved_blank else resolved_text,
                "user_edited": user_edited,
            }

        master_prompt_final = render_sentence(final_fields)
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "query": st.session_state.last_query,
            "fields": log_fields,
            "master_prompt_shown": synth["master_prompt"],
            "master_prompt_final": master_prompt_final,
            "decision": "confirmed" if confirmed else "rejected",
            "reject_reason": (reject_reason.strip() or None) if rejected else None,
        }
        log_correction(entry)

        st.session_state.last_decision = entry["decision"]
        st.session_state.last_master_prompt_final = master_prompt_final

        if confirmed:
            st.success(f"Confirmed:\n\n{master_prompt_final}")
        else:
            st.warning(f"Rejected:\n\n{master_prompt_final}")

    if st.session_state.get("last_decision") == "confirmed":
        active_provider = os.environ.get(
            "LLM_PROVIDER", llm_client.DEFAULT_PROVIDER
        ).strip().lower()
        provider_label = active_provider.capitalize()

        st.divider()
        section_header(
            "Generate Output",
            "Sends the confirmed master prompt to the configured LLM provider "
            f"(currently <strong>{html.escape(provider_label)}</strong> — see "
            "<code>API_KEYS.md</code> to switch) and returns its answer to your "
            "original business query.",
        )
        if st.button(f"🚀 Send to {provider_label}"):
            with st.spinner(f"Calling {provider_label}..."):
                try:
                    st.session_state.llm_output = llm_client.generate_output(
                        st.session_state.last_master_prompt_final
                    )
                    st.session_state.llm_error = None
                except Exception as e:
                    st.session_state.llm_output = None
                    st.session_state.llm_error = str(e)

        if st.session_state.get("llm_error"):
            st.error(
                f"{provider_label} call failed: {st.session_state.llm_error}\n\n"
                f"Check the `{active_provider}` provider's setup in `API_KEYS.md`."
            )
        elif st.session_state.get("llm_output"):
            st.markdown(st.session_state.llm_output)

st.divider()
st.caption(
    "This is v1, trained on 120 rows (100 synthetic + 20 real, hand-sourced from public "
    "earnings calls and shareholder letters). Measured against a frozen 10-row real-world "
    "holdout: 77.8% field status accuracy, 63.0% value accuracy, 90% actor-detection accuracy. "
    "`actor`, `time`, and `constraints` (including negated ones like \"without increasing X\") "
    "are the most reliable fields. `measure`, `scope`, and `context` are still data-thin, and "
    "`intent` can come back short or low-confidence on multi-clause queries — that's the model "
    "correctly signalling it isn't sure, not a display bug. Flag anything that looks wrong so "
    "it can go into the next training round."
)
