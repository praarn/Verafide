# ML layer

The core pipeline (TF-IDF + LogisticRegression / MLPClassifier) is covered
in the repo `README.md` and `docs/dataset.md`. This note covers the wrapper
logic.

## `inference.py`

- `ModelBundle` — lazy-loads the vectorizer + both classifiers + metrics
  once per process.
- `predict(text, mode)` — local-only: clean → vectorize → classify →
  `{label, confidence, confidence_band, probabilities, mode, signal_words}`.
- `top_signal_words(...)` — the words in *this* text that moved the linear
  model most (row TF-IDF × coefficient), shown regardless of which model
  produced the final label.
- `confidence_band(c)` — `high ≥ 0.85`, `moderate ≥ 0.65`, else `low`.
  Thresholds in `CONFIDENCE_BANDS`; read by the API, batch rows, and the
  frontend copy so they can't drift.
- `predict_smart(text, mode, modality, media_context)` — runs `predict()`,
  then tries `get_llm_verdict()`. On **any** failure returns the local
  result with `verdict_source="classic_fallback"`. On success returns the
  LLM's label/confidence/reasoning plus `citations`, keeping the local
  `signal_words`. `media_context` (analyst notes from image pre-processing)
  is forwarded to the LLM.

## `llm_verdict.py`

Groq chat call that returns strict JSON
`{label, confidence, reasoning, citation_ids}`. Before the call it runs
`rag.retrieve(text[:2000])` and injects the passages as numbered
`REFERENCE NOTES`; `citation_ids` are mapped back to passage objects and
returned as `citations`. Retrieval failure is swallowed — the verdict still
runs. Raises `LLMVerdictError` (caught by `predict_smart`) on unreachable
Groq, unparseable output, or an invalid label/confidence.

## `media.py`

- `analyze_image(bytes, mime)` — Groq vision model first (transcription +
  credibility observations, parsed from `TEXT:` / `OBSERVATIONS:`
  sections); **falls back to local Tesseract OCR** for text-only extraction
  if vision is unavailable. Raises `MediaError` only if both yield nothing.
- `analyze_audio(bytes, filename)` — Groq Whisper transcription.

## `source_credibility.py`

Static `domain -> tier` map (`high` / `mixed` / `low` / `satire` /
`state`), ~90 well-known outlets, with `TIER_META` for display. **Advisory
only** — attached to URL responses as `source_credibility`, never an input
to the label or confidence. `registrable_domain()` handles a leading `www`
and common two-part ccTLDs without a PSL dependency.
