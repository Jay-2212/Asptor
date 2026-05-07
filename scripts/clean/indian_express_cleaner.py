"""Cleaner for Indian Express Explained listing page."""
from __future__ import annotations

import re

from .base_cleaner import BaseCleaner
from .html_utils import extract_cards, extract_links
from .schema import Article

_BASE = "https://indianexpress.com"

# Indian Express Explained articles live under /article/explained/
_ARTICLE_PATH_RE = re.compile(
    r"/article/explained/",
    re.IGNORECASE,
)

# Skip utility pages.
_SKIP_PATH_RE = re.compile(
    r"/(subscribe|login|logout|search|tag|author|about|advertise|sitemap"
    r"|contact|account|profile|newsletter|rss|feeds?)/",
    re.IGNORECASE,
)

_MIN_TITLE_LEN = 12


class IndianExpressCleaner(BaseCleaner):
    """Parses Indian Express Explained listing page into Article stubs."""

    source_name = "indian_express_explained"

    def _is_article_url(self, url: str) -> bool:
        if not url.startswith(_BASE) and not url.startswith("/"):
            return False
        if _SKIP_PATH_RE.search(url):
            return False
        return bool(_ARTICLE_PATH_RE.search(url))

    def parse(
        self,
        content_html: str,
        source_url: str,
        fetched_at: str,
    ) -> list[Article]:
        cards = extract_cards(
            content_html,
            base_url=_BASE,
            url_filter=self._is_article_url,
        )

        seen: set[str] = set()
        articles: list[Article] = []

        for card in cards:
            if card.url in seen:
                continue
            if len(card.title) < _MIN_TITLE_LEN:
                continue
            # Clutter filtering: ignore "Live Updates" or "Live Highlights"
            if "live updates" in card.title.lower() or "live highlights" in card.title.lower():
                continue
            
            seen.add(card.url)
            h = Article.compute_hash(card.url, card.title)
            articles.append(
                Article(
                    source=self.source_name,
                    source_id=h,
                    url=card.url,
                    title=card.title,
                    subtitle=None,
                    author=card.author,
                    published_at=card.date_text,
                    image_url=card.image_url,
                    content_html="",
                    content_text="",
                    fetched_at=fetched_at,
                    hash=h,
                )
            )

        if not articles:
            articles = self._fallback_link_parse(content_html, fetched_at)

        return articles

    def _fallback_link_parse(
        self,
        content_html: str,
        fetched_at: str,
    ) -> list[Article]:
        links = extract_links(content_html, base_url=_BASE)
        seen: set[str] = set()
        articles: list[Article] = []
        for link in links:
            if not self._is_article_url(link.href):
                continue
            title = re.sub(r"\s+", " ", link.text).strip()
            if len(title) < _MIN_TITLE_LEN:
                continue
            if "live updates" in title.lower() or "live highlights" in title.lower():
                continue
            if link.href in seen:
                continue
            seen.add(link.href)
            h = Article.compute_hash(link.href, title)
            articles.append(
                Article(
                    source=self.source_name,
                    source_id=h,
                    url=link.href,
                    title=title,
                    subtitle=None,
                    author=None,
                    published_at=None,
                    image_url=None,
                    content_html="",
                    content_text="",
                    fetched_at=fetched_at,
                    hash=h,
                )
            )
        return articles
