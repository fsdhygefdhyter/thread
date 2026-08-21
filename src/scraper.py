"""
src/scraper.py — Article content fetcher for AWS affiliate URLs.

Fetches the article HTML, extracts the main text content and title.
Uses trafilatura as primary extractor, BeautifulSoup as fallback.
"""

import requests
from dataclasses import dataclass
from urllib.parse import urlparse

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Minimum characters of text content for a valid scrape
MIN_TEXT_LENGTH = 150


@dataclass
class ScrapedArticle:
    url: str
    title: str = ""
    text: str = ""       # plain text body (fed to Gemini)
    domain: str = ""
    error: str = ""

    @property
    def is_ok(self) -> bool:
        return len(self.text) >= MIN_TEXT_LENGTH and not self.error

    def __str__(self) -> str:
        status = "OK" if self.is_ok else f"FAIL: {self.error}"
        return f"ScrapedArticle({self.domain} | {status} | {len(self.text)} chars)"


def scrape(url: str, timeout: int = 20) -> ScrapedArticle:
    """
    Fetch and extract the main text content from a URL.
    Returns a ScrapedArticle dataclass.
    """
    domain = urlparse(url).netloc
    article = ScrapedArticle(url=url, domain=domain)

    # ── Fetch HTML ────────────────────────────────────────────────────
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        raw_html = resp.text
    except requests.exceptions.Timeout:
        article.error = f"Request timed out after {timeout}s"
        return article
    except requests.exceptions.HTTPError as e:
        article.error = f"HTTP error: {e.response.status_code}"
        return article
    except requests.exceptions.RequestException as e:
        article.error = f"Request failed: {e}"
        return article

    # ── Extract with trafilatura (preferred) ──────────────────────────
    if HAS_TRAFILATURA:
        extracted = trafilatura.extract(
            raw_html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_precision=True,
            output_format="txt",
        )
        meta = trafilatura.extract_metadata(raw_html)
        if extracted and len(extracted.strip()) >= MIN_TEXT_LENGTH:
            article.text = extracted.strip()
            if meta:
                article.title = meta.title or ""
            if not article.title:
                article.title = _extract_title_bs4(raw_html) if HAS_BS4 else ""
            return article

    # ── Fallback: BeautifulSoup ───────────────────────────────────────
    if HAS_BS4:
        article.title = _extract_title_bs4(raw_html)
        article.text = _extract_text_bs4(raw_html)
        if article.is_ok:
            return article

    # ── Nothing worked ────────────────────────────────────────────────
    if not article.text:
        article.error = (
            "Could not extract text content. "
            "The page may require JavaScript, be behind a paywall, or be empty."
        )
    return article


def _extract_title_bs4(html: str) -> str:
    """Extract page title using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)
    return ""


def _extract_text_bs4(html: str) -> str:
    """Extract body text using BeautifulSoup as fallback."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()
    body = soup.find("article") or soup.find("main") or soup.find("body")
    if not body:
        return ""
    lines = [line.strip() for line in body.get_text(separator="\n").splitlines() if line.strip()]
    return "\n".join(lines)
