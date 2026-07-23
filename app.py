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

import streamlit as st

from pipeline import Pipeline, ROLES

st.set_page_config(page_title="CHOICE Forge", page_icon="🧭", layout="wide")


@st.cache_resource(show_spinner="Loading models (spaCy + CRF + T5)...")
def load_pipeline():
    return Pipeline()


EXAMPLES = [
    "Cut support ticket backlog by 40% for enterprise accounts within the next sprint.",
    "Marketing wants to grow trial-to-paid conversion for self-serve signups from 8% to 15% before the holiday season, without increasing the ad spend budget.",
    "Our field sales team needs to onboard 1,200 kirana stores in Pune onto the B2B ordering app by the end of Q3, using only the existing incentive budget.",
]

st.title("🧭 CHOICE Forge")
st.caption(
    "Turns a plain-English business ask into 9 structured fields "
    "(actor, object, intent, scope, measure, magnitude, time, constraints, context). "
    "Runs entirely locally — spaCy → CRF → T5, no external LLM API."
)

pipe = load_pipeline()

example = st.selectbox(
    "Try an example, or write your own below:",
    ["(write your own)"] + EXAMPLES,
)
default_text = "" if example == "(write your own)" else example

query = st.text_area(
    "Business query",
    value=default_text,
    height=100,
    placeholder="e.g. Reduce warehouse picking errors by 15% for the night shift crew before Q4.",
)

run = st.button("Run", type="primary", disabled=not query.strip())

if run and query.strip():
    with st.spinner("Extracting..."):
        result = pipe.run(query.strip())

    st.subheader("Result")

    for role in ROLES:
        r = result[role]
        cols = st.columns([1.3, 4, 1.3, 1.3, 3])
        cols[0].markdown(f"**{role}**")

        if r["status"] == "missing":
            cols[1].markdown("*— not found in query —*")
            cols[2].write("missing")
            cols[3].write("—")
            cols[4].write("—")
            continue

        value_display = str(r["value"])
        if r["flagged_for_review"]:
            value_display = f"⚠️ {value_display}"
        cols[1].write(value_display)
        cols[2].write(r["status"])

        conf = r["confidence"]
        conf_color = "🟢" if conf >= 0.7 else ("🟡" if conf >= 0.4 else "🔴")
        cols[3].write(f"{conf_color} {conf:.2f}")
        cols[4].write(f"`{r['source_text']}`")

        if r["flagged_for_review"]:
            st.caption(f"⚠️ **{role}** flagged for review — {r['guard_note']}")
        elif r["guard_note"]:
            st.caption(f"🛠️ **{role}** auto-corrected by polarity guard — {r['guard_note']}")

    with st.expander("Raw JSON"):
        st.json(result)

st.divider()
st.caption(
    "This is v1, trained on a 100-row labeled dataset. Expect it to do well on phrasing "
    "close to what it's seen, and to make mistakes on unfamiliar patterns — that's expected "
    "at this stage, not a bug. Flag anything that looks wrong so it can go into the next "
    "training round."
)
