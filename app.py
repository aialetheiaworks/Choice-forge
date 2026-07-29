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

import html
import json
import statistics

import streamlit as st

from pipeline import Pipeline, ROLES

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

result = st.session_state.get("last_result")

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
