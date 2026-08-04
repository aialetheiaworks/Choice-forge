"""
One module per LLM provider, each exposing a single generate(prompt) ->
str function with the same contract. llm_client.py dispatches to whichever
one LLM_PROVIDER selects -- see API_KEYS.md.
"""
