"""Build (or rebuild) the RAG retrieval index.

    python scripts/build_rag_index.py

Reads app/rag/corpus/*.md plus the optional data/fact_checks.csv and writes
app/rag/artifacts/rag_index.joblib. The app also builds this lazily on
first use if the artifact is missing, so running this is only needed to
pre-warm the image at build time or after editing the corpus.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.retriever import build_index  # noqa: E402


def main() -> None:
    index = build_index(persist=True)
    print("RAG index built:")
    for k, v in index.meta.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
