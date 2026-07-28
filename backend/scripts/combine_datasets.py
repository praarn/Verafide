"""
combine_datasets.py
--------------------
Merges data/train_data_synthetic.csv (topic-diverse, template-generated) with
data/train_data_real.csv (real-world political news articles) into the final
data/train_data.csv used by train_models.py. Keeping both sources means the
model sees genuine, varied real-world prose (so it doesn't over-fit to
templates) as well as topics beyond politics (health, tech, sports, etc.)
that the real-world dataset doesn't cover.
"""

import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_FILES = [
    "train_data_synthetic.csv",   # templated, topic-diverse (8 topics), both classes
    "train_data_real.csv",        # McIntire 2016-election political news, both classes
    "train_data_agnews.csv",      # AG News: World/Sports/Business/Sci-Tech, real only
    "train_data_onion.csv",       # Onion-or-Not: satire vs genuine headlines, both classes
]
OUT_PATH = os.path.join(BASE_DIR, "data", "train_data.csv")


def main():
    frames = []
    for name in SOURCE_FILES:
        path = os.path.join(BASE_DIR, "data", name)
        if os.path.exists(path):
            frames.append(pd.read_csv(path))
        else:
            print(f"Skipping missing file: {path}")

    if not frames:
        raise SystemExit("No source datasets found. Run the build_*.py / generate_dataset.py scripts first.")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=["text", "label"])
    combined["label"] = combined["label"].astype(int)
    combined = combined.drop_duplicates(subset=["text"])

    # Balance classes so one source (e.g. a large real-only corpus) can't skew the prior.
    counts = combined["label"].value_counts()
    minority_n = int(counts.min())
    balanced = (
        combined.groupby("label", group_keys=False)
        .apply(lambda g: g.sample(n=minority_n, random_state=42))
    )
    balanced = balanced.sample(frac=1, random_state=42).reset_index(drop=True)  # shuffle

    balanced.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(balanced)} combined, balanced rows to {OUT_PATH}")
    print(balanced["label"].value_counts())
    print("\nBy topic:")
    print(balanced["topic"].value_counts())


if __name__ == "__main__":
    main()
