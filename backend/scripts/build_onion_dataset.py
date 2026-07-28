"""
build_onion_dataset.py
------------------------
Onion-or-Not (https://github.com/lukefeilberg/onion) pairs real Onion
headlines (fabricated/satirical, spanning almost every topic — tech,
politics, business, everyday life) against genuine non-satirical headlines.
This is the best available real-world source of *non-political* fabricated
content, and it's short-form, which helps the model generalize beyond
long-article-length input.

Source label: 1 = Onion (satire/fabricated), 0 = not Onion (genuine).
We map that to this project's convention: 1 = real, 0 = fake.

Run once after downloading:
    curl -o data/onion_or_not.csv \
      https://raw.githubusercontent.com/lukefeilberg/onion/master/OnionOrNot.csv
    python scripts/build_onion_dataset.py
"""

import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATH = os.path.join(BASE_DIR, "data", "onion_or_not.csv")
OUT_PATH = os.path.join(BASE_DIR, "data", "train_data_onion.csv")

SAMPLE_PER_CLASS = 2000


def main():
    df = pd.read_csv(RAW_PATH)
    df = df.dropna(subset=["text", "label"])
    df["label"] = 1 - df["label"].astype(int)  # invert: onion(1)->fake(0), real(0)->real(1)
    df["topic"] = "satire_or_general"

    balanced = (
        df.groupby("label", group_keys=False)
        .apply(lambda g: g.sample(n=min(SAMPLE_PER_CLASS, len(g)), random_state=42))
    )
    out = balanced[["text", "label", "topic"]]
    out.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(out)} rows to {OUT_PATH}")
    print(out["label"].value_counts())


if __name__ == "__main__":
    main()
