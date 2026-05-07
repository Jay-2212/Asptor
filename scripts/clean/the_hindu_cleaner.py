"""Cleaner for The Hindu Opinion listing page."""
from __future__ import annotations

import re

from .base_cleaner import BaseCleaner
from .html_utils import CardInfo, extract_cards, extract_links
from .schema import Article

_BASE = "https://www.thehindu.com"

# The Hindu opinion/editorial articles live under these path prefixes.
_ARTICLE_PATH_RE = re.compile(
    r"/opinion/",
    re.IGNORECASE,
)

# Patterns that indicate non-article URLs (navigation, utility pages).
_SKIP_PATH_RE = re.compile(
    r"/(subscribe|login|logout|search|tag|author|about|advertise|sitemap"
    r"|contact|account|profile|newsletter|rss|feeds?)/",
    re.IGNORECASE,
)

_MIN_TITLE_LEN = 12


class TheHinduCleaner(BaseCleaner):
    """Parses The Hindu listing pages into Article stubs."""

    def __init__(
        self,
        source_name: str = "the_hindu_opinion",
        article_path_pattern: str = "/opinion/",
    ) -> None:
        self.source_name = source_name
        self._article_path_re = re.compile(article_path_pattern, re.IGNORECASE)

    def _is_article_url(self, url: str) -> bool:
        if not url.startswith(_BASE) and not url.startswith("/"):
            return False
        if _SKIP_PATH_RE.search(url):
            return False
        return bool(self._article_path_re.search(url))

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

        # Deduplicate by URL; preserve first-seen order.
        seen: set[str] = set()
        articles: list[Article] = []

        for card in cards:
            if card.url in seen:
                continue
            if len(card.title) < _MIN_TITLE_LEN:
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

        # Fall back to plain link extraction if the card extractor found nothing.
        if not articles:
            articles = self._fallback_link_parse(content_html, fetched_at)

        return articles

    # ------------------------------------------------------------------
    # Fallback: plain <a> link scan
    # ------------------------------------------------------------------

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
