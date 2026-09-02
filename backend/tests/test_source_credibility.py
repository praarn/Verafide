import pytest

from app.ml import source_credibility as sc


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.theonion.com/some-story", "theonion.com"),
        ("http://reuters.com/article/1", "reuters.com"),
        ("https://news.bbc.co.uk/2/hi/x.stm", "bbc.co.uk"),
        ("nytimes.com", "nytimes.com"),
        ("https://sub.domain.example.com.au/x", "example.com.au"),
    ],
)
def test_registrable_domain(url, expected):
    assert sc.registrable_domain(url) == expected


def test_registrable_domain_garbage():
    assert sc.registrable_domain("") is None
    assert sc.registrable_domain("not a url") is None
    assert sc.registrable_domain("localhost") is None


def test_lookup_known_satire():
    out = sc.lookup("https://www.theonion.com/politics/story-123")
    assert out is not None
    assert out["tier"] == "satire"
    assert out["domain"] == "theonion.com"
    assert out["label"] and out["blurb"]


def test_lookup_known_high():
    assert sc.lookup("https://apnews.com/x")["tier"] == "high"


def test_lookup_unknown_returns_none():
    assert sc.lookup("https://some-random-blog-42.example/x") is None


def test_every_tier_has_meta():
    tiers = set(sc._DOMAINS.values())
    assert tiers <= set(sc.TIER_META)
    for meta in sc.TIER_META.values():
        assert meta["label"] and meta["blurb"]
