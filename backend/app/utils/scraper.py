import re

import requests
from bs4 import BeautifulSoup

# A real browser UA + realistic headers. Many news sites serve a stripped,
# mostly-navigation shell to unrecognized bot user-agents and only render
# full article markup for browser-like clients — using a generic
# "FakeNewsDetectionBot" UA was silently getting us the thin version of
# the page on some sites.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Common article body container patterns across major CMS platforms
# (WordPress, Arc/Washington Post, Assettype (used by many Indian outlets
# incl. Deccan Herald), Ghost, generic semantic HTML).
CONTENT_SELECTORS = [
    {"name": "article"},
    {"attrs": {"itemprop": "articleBody"}},
    {"attrs": {"class": re.compile(r"(article|story|post|entry)[-_]?(body|content)", re.I)}},
    {"attrs": {"class": re.compile(r"^(content|paragraphs)$", re.I)}},
]

JUNK_LINE_RE = re.compile(
    r"^(advertisement|read more|published|last updated|follow us|join us|"
    r"share|comments|subscribe|sign in|sign up|epaper|credit\s*:)",
    re.I,
)

MIN_CONTENT_CHARS = 40


class ArticleFetchError(Exception):
    pass


def _paragraphs_from(node) -> str:
    texts = [p.get_text(" ", strip=True) for p in node.find_all("p")]
    texts = [t for t in texts if len(t.split()) > 3 and not JUNK_LINE_RE.match(t)]
    return "\n".join(texts)


def _extract_body(soup) -> str:
    # 1. Try known article-container patterns first — these avoid nav/sidebar noise.
    for selector in CONTENT_SELECTORS:
        node = soup.find(**selector)
        if node:
            text = _paragraphs_from(node)
            if len(text) >= MIN_CONTENT_CHARS:
                return text

    # 2. Fall back to every <p> on the page (works for simple/blog-style sites).
    text = _paragraphs_from(soup)
    if len(text) >= MIN_CONTENT_CHARS:
        return text

    # 3. Last resort: meta description / og:description. Short, but real —
    #    better than failing outright on legitimately short wire-service articles.
    for attrs in (
        {"name": "description"},
        {"property": "og:description"},
        {"name": "twitter:description"},
    ):
        meta = soup.find("meta", attrs=attrs)
        if meta and meta.get("content") and len(meta["content"]) >= 20:
            return meta["content"].strip()

    return text  # whatever (possibly empty/short) text we found, let caller decide


def fetch_article_text(url: str, timeout: int = 12) -> dict:
    """Downloads a URL and extracts a best-effort title + main body text.

    Layered strategy: known article-container selectors, then a generic
    <p>-tag sweep, then meta description as a last resort — so genuinely
    short wire-service articles don't get rejected just for being short.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise ArticleFetchError(f"Could not fetch the URL: {exc}") from exc

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        tag.decompose()

    title = None
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()

    body = _extract_body(soup)

    if len(body) < MIN_CONTENT_CHARS:
        raise ArticleFetchError(
            "Could not find enough readable article text at that URL. "
            "The page may require JavaScript, sign-in, or a subscription to view — "
            "try pasting the article text directly instead."
        )

    return {"title": title or url, "text": body}
