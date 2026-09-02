# The training dataset

The bundled classifier is trained on a **blend of four sources**, ~13,300
balanced rows across 13 topic buckets (politics, world, business, sci/tech,
sports, health, finance, entertainment, environment, general/satire).

| Source | Contributes |
|---|---|
| `train_data_synthetic.csv` | Template-generated clickbait-vs-measured-prose pairs across 8 topics (`scripts/generate_dataset.py`) |
| `train_data_real.csv` | 6,335 real 2016-era political articles, real vs. fabricated — [lutzhamel/fake-news](https://github.com/lutzhamel/fake-news) (McIntire) |
| `train_data_agnews.csv` | Genuine published news blurbs (World/Sports/Business/Sci-Tech) — [AG News](https://github.com/mhjabreel/CharCnn_Keras); real-only, for topic/length diversity |
| `train_data_onion.csv` | Satirical vs. genuine headlines across most topics — [Onion-or-Not](https://github.com/lukefeilberg/onion) |

## Why four sources

Trained on the political set alone, the model hit **95%** held-out accuracy
— but it had learned "real == 2016-election vocabulary", not general
credibility signals, and failed on tech news, Fed announcements, literary
quotes. After broadening the mix, held-out accuracy is a more honest
**~86%** and it handles those cases. A higher number on one narrow dataset
is often *worse*.

## Regenerate from scratch

`data/train_data.csv` (the merged, balanced result) is committed, so
`python scripts/train_models.py` works out of the box. To rebuild
everything (run inside the activated backend venv, from `backend/`):

```bash
python scripts/generate_dataset.py       # rebuild the synthetic slice
# re-download the 3 real-world CSVs into data/ — the curl command is in the
# docstring at the top of each build_*.py
python scripts/build_real_dataset.py
python scripts/build_agnews_dataset.py
python scripts/build_onion_dataset.py
python scripts/combine_datasets.py       # merge + balance -> data/train_data.csv
python scripts/train_models.py           # retrain both models -> app/ml/artifacts/
```

`metrics.json` (accuracy/precision/recall/F1, dataset size, timestamp) is
written alongside the artifacts and surfaced on the Analytics page.

## Before shipping for real use

Add non-English sources, post-2018 real-world fake-news examples (every set
above predates ~2018), and a genuine transformer model — bag-of-words
cannot reason about a claim's factual content, only its lexical style.
`backend/app/ml/inference.py` is structured to accept a `transformers`
pipeline as a third mode.
