# CHOICE Forge v1

Turns a plain-English business ask ("Cut support ticket backlog by 40% for
enterprise accounts within the next sprint.") into a structured object with
9 fields: `actor`, `object`, `intent`, `scope`, `measure`, `magnitude`,
`time`, `constraints`, `context`. Each field gets a `value`, a `status`
(`explicit`/`missing`), a `confidence` score, and the `source_text` span it
was grounded in.

The 9-field extraction step runs entirely locally — no external LLM API
calls. The optional "Generate Output" step in the Streamlit UI (after you
confirm a master prompt) calls an LLM provider of your choice (Anthropic,
Gemini, or a local Ollama model) — see "Generate Output (Phase 4)" below
and `API_KEYS.md` for the full reference.

## Setup

Requires Python 3.10+.

```bash
pip3 install spacy sklearn-crfsuite joblib transformers torch sentencepiece accelerate
python3 -m spacy download en_core_web_sm
```

## Stakeholder UI (recommended way to try this)

```bash
pip3 install streamlit
streamlit run app.py
```

Opens a browser tab at `http://localhost:8501` with a text box to type (or
pick an example) query, and a results table showing each field's value,
status, confidence (🟢/🟡/🔴), and the source span it came from. Values
the polarity guard auto-corrected or flagged are called out inline — see
`ABOUT.md` for what that means.

This runs the actual trained models locally in your browser session —
nothing is sent anywhere. To share with remote stakeholders you'd need to
either run it on a shared machine they can reach, or tunnel it (e.g.
`ngrok http 8501`); it isn't deployed anywhere by default.

## Generate Output (Phase 4)

Below the field results, the UI shows a "Master Prompt" — an assembled
objective statement with blanks for anything the pipeline didn't confidently
extract. Fill in or mark blanks "not applicable", then Confirm. Once
confirmed, a "Generate Output" section appears with a "Send to
{Provider}" button that sends the confirmed prompt to whichever LLM
provider is currently configured and shows its answer.

**Which provider runs is a config change, not a code change** — see
`API_KEYS.md` for the full reference (every provider's env vars, how to
switch, how to add a new one). Quick version:

```bash
cp .env.example .env   # then fill in the one provider's key you're using
```

`.env` is gitignored — never commit it, and never paste a real key
anywhere (chat, docs, commits). Without a key set for the active
provider, clicking "Send to {Provider}" shows a clear error in the UI
instead of a live answer — the rest of the app (extraction, master-prompt
editing, confirm/reject logging) works the same either way.

## Run it from the command line

```bash
python3 pipeline.py "Grow self-serve trial-to-paid conversion from 8% to 15% before the holiday season, without increasing the ad spend budget."
```

If you don't pass a query, it runs a default example.

Output looks like:

```
field        | value                          | status    | conf | source_text
--------------------------------------------------------------------------------
actor        | None                           | missing   | 0.00 | None
object       | None                           | missing   | 0.00 | None
intent       | grow trial-to-paid conversion  | explicit  | 0.81 | grow trial-to-paid conversion
scope        | self-serve signups             | explicit  | 0.46 | for self-serve signups
measure      | None                           | missing   | 0.00 | None
magnitude    | from 8% to 15%                 | explicit  | 0.91 | from 8% to 15%
time         | before the holiday season      | explicit  | 0.98 | before the holiday season
constraints  | must not increase the ad spend budget | explicit | 0.85 | without increasing the ad spend budget
context      | None                           | missing   | 0.00 | None
```

## Retraining from scratch

Only needed if you're changing the training data or want to reproduce the
models yourself. Run in this order from this folder:

```bash
# 1. Trains the CRF extractor (locates each role's grounding span in the
#    query). Reads choice_forge_dataset_full_100_v2.json, writes
#    role_tagger.joblib (~30s).
python3 train_crf.py choice_forge_dataset_full_100_v2.json

# 2. (Re)builds the seq2seq training pairs from the same dataset.
#    Only needed if choice_forge_dataset_full_100_v2.json changed --
#    data/seq2seq_pairs.jsonl is already included.
python3 build_seq2seq_pairs.py

# 3. Fine-tunes the T5 value-synthesizer on those pairs. Writes
#    value_synthesizer/ (~5-6 min on a laptop CPU/MPS, 20 epochs).
python3 train_seq2seq.py

# 4. Run the pipeline against the freshly trained models.
python3 pipeline.py "<your query here>"
```

See `ABOUT.md` for how each piece works and why it's built this way.

## Files

| File | Purpose |
|---|---|
| `choice_forge_dataset_full_100_v2.json` | The 100 hand-labeled source rows everything is trained from. |
| `train_crf.py` | Trains the span-extraction model (Layer 1 of inference). |
| `build_seq2seq_pairs.py` | Generates `data/seq2seq_pairs.jsonl` from the source dataset. |
| `data/seq2seq_pairs.jsonl` | 629 (span → canonical value) training pairs. |
| `train_seq2seq.py` | Fine-tunes the T5 value-synthesizer (Layer 2 of inference). |
| `polarity_guard.py` | Runtime negation/direction-flip safety net used by `pipeline.py`. |
| `role_tagger.joblib` | Trained CRF model (output of `train_crf.py`). |
| `value_synthesizer/` | Trained T5 model (output of `train_seq2seq.py`). |
| `pipeline.py` | Runs a query through spaCy → CRF → T5 → polarity guard. Also the entry point for CLI use. |
| `prompt_synthesis.py` | Assembles the 9 fields into a master-prompt sentence, blanking low-confidence/missing fields. |
| `correction_log.py` | Appends every confirm/reject decision to `data/corrections_log.jsonl`. |
| `llm_client.py` | Routes a confirmed master prompt to whichever provider `LLM_PROVIDER` selects. |
| `llm_providers/` | One module per LLM provider (Anthropic/Gemini/Ollama), each behind the same `generate(prompt)` contract — see `API_KEYS.md`. |
| `API_KEYS.md` | The one file to read to switch LLM providers or add a new one. |
| `app.py` | Streamlit UI for stakeholders — **this is the recommended entry point.** |
