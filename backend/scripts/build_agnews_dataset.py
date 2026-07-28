"""
build_agnews_dataset.py
-------------------------
AG News (Zhang et al., via https://github.com/mhjabreel/CharCnn_Keras) is a
corpus of genuine published news blurbs across four broad topics: World,
Sports, Business, and Sci/Tech. Every row is real news, so it only
contributes to the "real" class here — but critically, it adds topic and
length diversity the political-only datasets don't have, which is what
keeps the model from learning "real == 2016 election vocabulary."

Run once after downloading:
    curl -o data/ag_news_train.csv \
      https://raw.githubusercontent.com/mhjabreel/CharCnn_Keras/master/data/ag_news_csv/train.csv
    python scripts/build_agnews_dataset.py
"""

import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATH = os.path.join(BASE_DIR, "data", "ag_news_train.csv")
OUT_PATH = os.path.join(BASE_DIR, "data", "train_data_agnews.csv")

TOPIC_MAP = {1: "world", 2: "sports", 3: "business", 4: "sci_tech"}
SAMPLE_PER_TOPIC = 750  # keep this source proportionate to the others


def main():
    df = pd.read_csv(RAW_PATH, header=None, names=["label", "title", "description"])
    df["text"] = (df["title"].fillna("") + ". " + df["description"].fillna("")).str.replace("\\", " ", regex=False)
    df["topic"] = df["label"].map(TOPIC_MAP)
    df["label"] = 1  # every AG News row is genuine published news

    sampled = (
        df.groupby("topic", group_keys=False)
        .apply(lambda g: g.sample(n=min(SAMPLE_PER_TOPIC, len(g)), random_state=42))
    )
    out = sampled[["text", "label", "topic"]]
    out.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(out)} rows to {OUT_PATH}")
    print(out["topic"].value_counts())


if __name__ == "__main__":
    main()
