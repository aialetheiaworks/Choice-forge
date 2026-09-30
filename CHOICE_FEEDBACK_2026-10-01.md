# Feedback from CHOICE testing — CHOICE Forge · 1 Oct 2026

CHOICE (the product in `../CHOICE`) calls this repo's API (`api.py`, run on port 8101) for the **Understand**
screen: `POST /extract` (the 9 fields) and `POST /assemble` (the first draft statement, with
`LLM_PROVIDER=llamacpp`, the local Horizon model, adapter off). This file is feedback from full walkthroughs
with real-sounding cases. It is self-contained.

Note: CHOICE already runs a second pass on your fields (a review by the Horizon model that can only change a
field when it quotes the question's own words). It fixes some of the problems below after the fact; fixing
them at the source is still better, and the owner sees your fields first.

## Case 1 (1 Oct): tuition centre

> We run a tuition centre in Indore with 120 students in classes 9 to 12. For the last year parents keep asking
> for online classes, and two students left for an online coaching app. Should we build our own online learning
> app or use an existing platform like Zoom with a learning management system? We want online classes running
> before the next academic year starts in April.

Fields shown to the owner (after CHOICE's review):
- **Limits: "two students left"** — wrong: that's background (why they're considering this), not a constraint.
- **Where / for whom: "the tuition centre"** — misses "Indore" and "students in classes 9 to 12".
- **What: "a tuition centre"** — weak; the object of the decision is the online classes / learning app.
- Banner: **"This may be two decisions. Consider splitting it."** — a false alarm (see below).

### The false "two decisions" banner
`prompt_synthesis.detect_possible_compound_query()` flags a query when ≥2 of the compound-signal roles are
`multi_span`. A question that offers a **choice between two options** ("build our own app **or** use an existing
platform") naturally produces multi-span intent/object, so it is flagged, though it's one decision.
Seen on every "A or B" test question in CHOICE (café: "delivery through Swiggy/Zomato **or** partnering with an
office park"; SaaS: "build an AI assistant **or** integrate an existing one").

Suggested direction: don't flag when the query offers alternatives for one decision, e.g. the multi-span values
come from the two sides of an "either … or …" / "should we … or …" / "whether to … or …" construction. Keep
flagging genuinely separate decisions ("Marketing will grow brand awareness while Sales grows enterprise
accounts").

## Case 2 (30 Sep): café

> We run a 20-seat café in Koregaon Park, Pune. Our sales have dropped 15% in the last 3 months since a big coffee
> chain opened two doors away. We are thinking of either starting delivery through Swiggy and Zomato, or
> partnering with a nearby office park to supply their pantry. Which should we do?

Forge's raw fields: intent **"run; dropped"**, constraints **"either starting delivery through Swiggy and Zomato,
or partnering with a nearby office park"** (the two options filed as a constraint), context **"supply pantry"**
(a fragment), time **"last 3 months"** (history, not a deadline), measure missing (should be "sales").

## Other patterns seen across CHOICE's test set

- Intent direction flips: "improve inventory turnover" → **"decrease inventory turnover"** (Surat textile case).
- Places filed as time: time **"India"** (SaaS case: "…small businesses in India").
- Amounts filed as time: time **"by 30%"** (competitor price-cut case).
- Background filed as constraints: "resulting in excess working capital of ₹4 crore" (Surat case).

These match the known weak spots in `ABOUT.md` (CRF span F1 ≈ 0.41; T5 direction flips). They are also the
kind of rows worth adding to training data from real owner questions (with the build → validate → split
workflow and never touching `data/real_world_eval_holdout.json`).

## How to check

- `python data/eval_on_real_world.py` before and after; don't regress the frozen holdout.
- The two questions above: no "two decisions" banner; options not in constraints; "Indore" in scope.

## Don't break (CHOICE depends on these)

- `POST /extract` response keys: `fields`, `display_fields` (per role: `text`, `blank`, `not_applicable`,
  `needs_review`, `multi_span`…), `template_master_prompt`, `blanks`, `low_confidence`, `needs_review`,
  `possible_compound_query`.
- `POST /assemble` with `{query, fields}` → `master_prompt`, `template_master_prompt`, `used_llm`, `error`.
- `LLM_PROVIDER=llamacpp` (`llm_providers/llamacpp_provider.py`), run by `../CHOICE/scripts/services.sh`.
