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

st.markdown(
    """
    <style>
    .cf-role-label {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        opacity: 0.55;
        margin-bottom: 2px;
    }
    .cf-value {
        font-size: 1.12rem;
        font-weight: 600;
        line-height: 1.35;
        margin: 2px 0 8px 0;
    }
    .cf-value.cf-missing {
        opacity: 0.4;
        font-weight: 400;
        font-style: italic;
    }
    .cf-source {
        font-size: 0.8rem;
        opacity: 0.6;
        margin-top: 6px;
        word-break: break-word;
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
        return "green", "High"
    if conf >= 0.4:
        return "orange", "Medium"
    return "red", "Low"


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

st.title("🧭 CHOICE Forge")
st.caption(
    "Turns a plain-English business ask into 9 structured fields "
    "(actor, object, intent, scope, measure, magnitude, time, constraints, context)."
)
badge_cols = st.columns([1, 1, 1, 1, 6])
badge_cols[0].badge("spaCy", color="blue")
badge_cols[1].badge("CRF", color="violet")
badge_cols[2].badge("T5", color="orange")
badge_cols[3].badge("100% local", color="green")

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
    st.subheader("Result")

    found_roles = [r for r in ROLES if result[r]["status"] != "missing"]
    avg_conf = (
        statistics.mean(result[r]["confidence"] for r in found_roles)
        if found_roles
        else 0.0
    )
    flagged_count = sum(1 for r in ROLES if result[r]["flagged_for_review"])

    metric_cols = st.columns(3)
    metric_cols[0].metric("Fields found", f"{len(found_roles)}/{len(ROLES)}")
    metric_cols[1].metric("Avg confidence (found fields)", f"{avg_conf:.2f}")
    metric_cols[2].metric("Flagged for review", flagged_count)

    st.write("")

    cols = st.columns(3)
    for i, role in enumerate(ROLES):
        r = result[role]
        icon = ROLE_ICONS.get(role, "🔹")
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(
                    f'<div class="cf-role-label">{icon} {html.escape(role)}</div>',
                    unsafe_allow_html=True,
                )

                if r["status"] == "missing":
                    st.markdown(
                        '<div class="cf-value cf-missing">— not found in query —</div>',
                        unsafe_allow_html=True,
                    )
                    st.badge("missing", color="gray")
                else:
                    value_display = html.escape(str(r["value"]))
                    st.markdown(
                        f'<div class="cf-value">{value_display}</div>',
                        unsafe_allow_html=True,
                    )

                    conf = r["confidence"]
                    tier_color, tier_label = confidence_tier(conf)
                    b1, b2 = st.columns(2)
                    b1.badge(r["status"], color="blue")
                    b2.badge(f"{tier_label} · {conf:.2f}", color=tier_color)
                    st.progress(min(max(conf, 0.0), 1.0))

                    st.markdown(
                        f'<div class="cf-source">source: <code>{html.escape(str(r["source_text"]))}</code></div>',
                        unsafe_allow_html=True,
                    )

                    if r["flagged_for_review"]:
                        st.warning(f"⚠️ Flagged — {r['guard_note']}")
                    elif r["guard_note"]:
                        st.info(f"🛠️ Auto-corrected — {r['guard_note']}")

    st.write("")
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
    st.subheader("Master Prompt")
    st.caption(
        "Fill in any blanks and correct anything the pipeline got wrong, then "
        "Confirm or Reject. Every decision is logged and becomes training data "
        "for a future prompt-synthesis model (Phase 5)."
    )

    run_id = st.session_state.run_id
    st.markdown(f"> {html.escape(synth['master_prompt'])}")

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
        st.divider()
        st.subheader("Generate Output")
        st.caption(
            "Sends the confirmed master prompt to Claude (Anthropic API) and "
            "returns its answer to your original business query."
        )
        if st.button("🚀 Send to Claude"):
            with st.spinner("Calling Claude..."):
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
                f"Claude API call failed: {st.session_state.llm_error}\n\n"
                "Check that ANTHROPIC_API_KEY is set in your environment."
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
