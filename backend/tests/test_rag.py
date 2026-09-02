from app.rag import retriever


def test_index_builds_from_corpus():
    retriever.reset_cache()
    idx = retriever.get_index()
    assert idx is not None
    assert idx.meta["media_literacy_chunks"] > 10
    assert idx.meta["fact_check_entries"] > 0  # seed data/fact_checks.csv


def test_retrieve_finds_relevant_media_literacy_note():
    hits = retriever.retrieve("headline uses all caps and urgent share-before-deleted language", k=3)
    assert hits, "expected at least one retrieved passage"
    joined = " ".join(h["title"].lower() + " " + h["snippet"].lower() for h in hits)
    assert "sensational" in joined or "clickbait" in joined or "emotional" in joined


def test_retrieve_matches_seed_factcheck():
    hits = retriever.retrieve("does 5G spread coronavirus", k=5)
    assert any("5g" in h["snippet"].lower() or "5g" in h["title"].lower() for h in hits)


def test_rag_search_endpoint(auth_client):
    r = auth_client.post("/api/rag/search", json={"query": "miracle cure suppressed by doctors", "k": 3})
    assert r.status_code == 200, r.text
    results = r.json()["results"]
    assert isinstance(results, list)
    if results:
        assert {"id", "title", "source", "snippet", "score"} <= set(results[0])


def test_rag_status_endpoint(client):
    r = client.get("/api/rag/status")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["ready"] is True
    assert body["total_chunks"] > 0
