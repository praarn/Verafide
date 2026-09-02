# Multimodal analysis

Four input types converge on one verdict pipeline (`predict_smart`), with
`modality` recorded on the response and in case history.

| Modality | Endpoint | Pre-processing | Config |
|---|---|---|---|
| Text | `POST /api/predict/text` | none | `MAX_TEXT_CHARS` |
| URL | `POST /api/predict/url` | `utils/scraper.py` fetches + extracts article text (streamed, 8 MB cap, layered selectors); known domains get `source_credibility` | — |
| Image | `POST /api/predict/image` (multipart) | `ml/media.analyze_image` | `MAX_IMAGE_MB`, `GROQ_VISION_MODEL` |
| Audio | `POST /api/predict/audio` (multipart) | `ml/media.analyze_audio` | `MAX_AUDIO_MB`, `GROQ_WHISPER_MODEL` |

## Image

`analyze_image(bytes, mime)`:

1. **Preferred** — Groq vision model. Prompt asks for two labelled
   sections: `TEXT:` (verbatim transcription of everything readable) and
   `OBSERVATIONS:` (2–4 bullets on apparent source, authenticity,
   manipulation signs, framing — *no* verdict). Parsed into
   `extracted_text` + `media_observations`.
2. **Fallback** — if the key has no vision access (or the call fails),
   local **Tesseract OCR** extracts text only; observations note that
   visual analysis was unavailable.

The extracted text is analyzed as text; `media_observations` is passed to
the LLM verdict as `ANALYST NOTES` so it can factor in "looks like a
fabricated graphic, not a real screenshot".

Accepted types: PNG, JPEG, WebP, GIF.

## Audio

`analyze_audio(bytes, filename)` → Groq Whisper
(`/audio/transcriptions`) → `transcript`, analyzed as text. Accepted
extensions: `.mp3 .m4a .wav .webm .ogg .flac .mp4 .mpeg .mpga`.

## Failure modes

- Vision **and** OCR yield nothing → `422` "no readable text".
- Groq unreachable for audio → `502` with a clear message.
- The downstream verdict still degrades to the local model if the LLM
  verdict call fails — `verdict_source: "classic_fallback"`.

## Tests

`backend/tests/test_multimodal.py` mocks `vision_completion` /
`transcribe_audio` so the endpoints, parsing, size/type guards, and the
join into `predict_smart` are all covered offline.
