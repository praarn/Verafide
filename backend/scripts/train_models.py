"""
train_models.py
----------------
Trains both bundled models on data/train_data.csv and writes artifacts to
app/ml/artifacts/. Run from the backend/ directory:

    python scripts/train_models.py

Swap data/train_data.csv for a real-world dataset (columns: text,label with
label 1=real / 0=fake) to retrain on production-quality data — no other
code changes required.
"""

import json
import os
import sys
import time

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.ml.preprocess import clean_text  # noqa: E402

ARTIFACT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "ml", "artifacts")
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "train_data.csv")


def main():
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    print(f"Loading dataset from {DATA_PATH} ...")
    df = pd.read_csv(DATA_PATH)
    df = df.dropna(subset=["text", "label"])
    df["clean_text"] = df["text"].apply(clean_text)
    df = df[df["clean_text"].str.len() > 0]

    X_train, X_test, y_train, y_test = train_test_split(
        df["clean_text"], df["label"], test_size=0.2, random_state=42, stratify=df["label"]
    )

    print("Fitting TF-IDF vectorizer ...")
    vectorizer = TfidfVectorizer(max_features=6000, ngram_range=(1, 2), min_df=2)
    Xtr = vectorizer.fit_transform(X_train)
    Xte = vectorizer.transform(X_test)

    print("Training classic model (Logistic Regression) ...")
    t0 = time.time()
    classic = LogisticRegression(max_iter=1000, C=2.0)
    classic.fit(Xtr, y_train)
    classic_time = time.time() - t0
    classic_preds = classic.predict(Xte)

    print("Training advanced model (MLP neural network) ...")
    t0 = time.time()
    advanced = MLPClassifier(
        hidden_layer_sizes=(128, 64),
        activation="relu",
        max_iter=300,
        random_state=42,
        early_stopping=True,
    )
    advanced.fit(Xtr, y_train)
    advanced_time = time.time() - t0
    advanced_preds = advanced.predict(Xte)

    def metrics_for(y_true, y_pred):
        return {
            "accuracy": round(accuracy_score(y_true, y_pred), 4),
            "precision": round(precision_score(y_true, y_pred), 4),
            "recall": round(recall_score(y_true, y_pred), 4),
            "f1": round(f1_score(y_true, y_pred), 4),
        }

    metrics = {
        "classic": {**metrics_for(y_test, classic_preds), "train_seconds": round(classic_time, 2), "algorithm": "TF-IDF + Logistic Regression"},
        "advanced": {**metrics_for(y_test, advanced_preds), "train_seconds": round(advanced_time, 2), "algorithm": "TF-IDF + MLP Neural Network (128,64)"},
        "dataset_size": len(df),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    print(json.dumps(metrics, indent=2))

    joblib.dump(vectorizer, os.path.join(ARTIFACT_DIR, "vectorizer.joblib"))
    joblib.dump(classic, os.path.join(ARTIFACT_DIR, "classic_model.joblib"))
    joblib.dump(advanced, os.path.join(ARTIFACT_DIR, "advanced_model.joblib"))
    with open(os.path.join(ARTIFACT_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Artifacts written to {ARTIFACT_DIR}")


if __name__ == "__main__":
    main()
