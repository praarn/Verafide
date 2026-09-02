"""A small, static source-credibility lookup for URL analyses.

This is intentionally NOT a verdict input — the label still comes from the
text model / LLM. It's an *advisory* signal shown alongside the verdict:
"the words look measured, but this domain is a known satire site" is useful
context a bag-of-words model can't give you.

The list is hand-curated and deliberately short. It leans on widely-cited
media-bias / fact-check aggregators (Media Bias/Fact Check, Ad Fontes,
Wikipedia's perennial-sources list) but is a rough tier, not a citation.
Unknown domains return ``None`` and the UI simply omits the panel — absence
of an entry is not a judgement.
"""

from urllib.parse import urlparse

# tier -> how to present it
TIER_META = {
    "high": {
        "label": "Established newsroom",
        "blurb": "Widely regarded as a mainstream outlet with editorial standards and corrections policies. Individual stories can still be wrong or slanted.",
    },
    "mixed": {
        "label": "Mixed track record",
        "blurb": "Reports real news but has a documented history of strong slant, sensational framing, or failed fact-checks. Cross-check specific claims.",
    },
    "low": {
        "label": "Low credibility",
        "blurb": "Flagged by media-literacy aggregators for repeatedly publishing false, misleading, or conspiratorial content. Treat claims with strong skepticism.",
    },
    "satire": {
        "label": "Satire / parody",
        "blurb": "Publishes deliberate satire. Content is not intended as factual reporting even when written in a news style.",
    },
    "state": {
        "label": "State-controlled media",
        "blurb": "Operates under government editorial control. Useful for official positions, unreliable on topics where the state has an interest.",
    },
}

# domain (registrable, no www) -> tier
_DOMAINS: dict[str, str] = {
    # --- high ---
    "reuters.com": "high",
    "apnews.com": "high",
    "bbc.com": "high",
    "bbc.co.uk": "high",
    "npr.org": "high",
    "nytimes.com": "high",
    "washingtonpost.com": "high",
    "wsj.com": "high",
    "theguardian.com": "high",
    "economist.com": "high",
    "ft.com": "high",
    "bloomberg.com": "high",
    "nature.com": "high",
    "sciencemag.org": "high",
    "science.org": "high",
    "pbs.org": "high",
    "cbc.ca": "high",
    "abc.net.au": "high",
    "thehindu.com": "high",
    "indianexpress.com": "high",
    "aljazeera.com": "high",
    "politico.com": "high",
    "axios.com": "high",
    "propublica.org": "high",
    # --- mixed ---
    "cnn.com": "mixed",
    "foxnews.com": "mixed",
    "nypost.com": "mixed",
    "dailymail.co.uk": "mixed",
    "huffpost.com": "mixed",
    "msnbc.com": "mixed",
    "breitbart.com": "mixed",
    "vox.com": "mixed",
    "buzzfeednews.com": "mixed",
    "thedailybeast.com": "mixed",
    "newsmax.com": "mixed",
    "opindia.com": "mixed",
    "republicworld.com": "mixed",
    # --- low ---
    "infowars.com": "low",
    "naturalnews.com": "low",
    "zerohedge.com": "low",
    "beforeitsnews.com": "low",
    "yournewswire.com": "low",
    "newspunch.com": "low",
    "worldtruth.tv": "low",
    "thegatewaypundit.com": "low",
    "dailybuzzlive.com": "low",
    "empirenews.net": "low",
    "nationalreport.net": "low",
    # --- satire ---
    "theonion.com": "satire",
    "clickhole.com": "satire",
    "babylonbee.com": "satire",
    "thebeaverton.com": "satire",
    "waterfordwhispersnews.com": "satire",
    "thedailymash.co.uk": "satire",
    "fakingnews.com": "satire",
    "thehardtimes.net": "satire",
    "reductress.com": "satire",
    # --- state-controlled ---
    "rt.com": "state",
    "sputniknews.com": "state",
    "presstv.ir": "state",
    "globaltimes.cn": "state",
    "xinhuanet.com": "state",
    "cgtn.com": "state",
}


def registrable_domain(url_or_host: str) -> str | None:
    """Best-effort 'example.co.uk' from a URL or bare host. No PSL dependency
    — just strips a leading www and keeps the last two labels, plus a small
    allowance for common two-part ccTLD suffixes."""
    if not url_or_host:
        return None
    host = url_or_host.strip().lower()
    if "://" in host:
        host = urlparse(host).netloc or urlparse("http://" + host).netloc
    host = host.split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    if not host or "." not in host:
        return None

    parts = host.split(".")
    two_part_tlds = {"co.uk", "org.uk", "com.au", "co.in", "net.au", "co.nz", "com.br"}
    if len(parts) >= 3 and ".".join(parts[-2:]) in two_part_tlds:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def lookup(url: str) -> dict | None:
    """Returns an advisory dict for a known domain, else None.

    ``{"domain", "tier", "label", "blurb"}``
    """
    domain = registrable_domain(url)
    if not domain:
        return None
    tier = _DOMAINS.get(domain)
    if not tier:
        return None
    meta = TIER_META[tier]
    return {"domain": domain, "tier": tier, "label": meta["label"], "blurb": meta["blurb"]}
