"""
build_real_dataset.py
----------------------
Cleans data/real_dataset_raw.csv (the McIntire "fake_or_real_news" dataset —
6,335 real-world political news articles/headlines, sourced from
https://github.com/lutzhamel/fake-news, originally compiled for the
kdnuggets fake-news classification article) into the same text/label schema
used everywhere else in this project, and writes data/train_data_real.csv.

Run once after downloading the raw file:
    curl -o data/real_dataset_raw.csv \
      https://raw.githubusercontent.com/lutzhamel/fake-news/master/data/fake_or_real_news.csv
    python scripts/build_real_dataset.py
"""

import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATH = os.path.join(BASE_DIR, "data", "real_dataset_raw.csv")
OUT_PATH = os.path.join(BASE_DIR, "data", "train_data_real.csv")


def main():
    df = pd.read_csv(RAW_PATH)
    df = df.dropna(subset=["text", "label"])
    df["title"] = df["title"].fillna("")
    df["text"] = (df["title"] + ". " + df["text"]).str.strip()
    df["label"] = df["label"].str.upper().map({"REAL": 1, "FAKE": 0})
    df = df.dropna(subset=["label"])
    df["label"] = df["label"].astype(int)
    df["topic"] = "politics_real_world"
    df = df[["text", "label", "topic"]]
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUT_PATH}")
    print(df["label"].value_counts())


if __name__ == "__main__":
    main()
