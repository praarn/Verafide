FROM python:3.12-slim

# curl: container HEALTHCHECK. tesseract-ocr: image/scanned-PDF OCR.
# gcc: occasional source builds.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc curl tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake the ML models + RAG index into the image so the first request is fast.
RUN python scripts/train_models.py && python scripts/build_rag_index.py

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

ENTRYPOINT ["bash", "docker-entrypoint.sh"]
