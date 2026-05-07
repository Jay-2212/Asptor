"""Cleaner for Fifty Two listing/homepage."""
from __future__ import annotations

import re

from .base_cleaner import BaseCleaner
from .html_utils import extract_cards, extract_links
from .schema import Article

_BASE = "https://fiftytwo.in"

# Fifty Two article URLs: https://fiftytwo.in/<slug>/
# Articles are directly under the root path with a slug that contains a hyphen
# and is at least 5 characters long.  Skip known utility and tag paths.
_SKIP_SEGMENTS = frozenset(
    {
        "tag",
        "author",
        "category",
        "search",
        "subscribe",
        "login",
        "logout",
        "about",
        "contact",
        "advertise",
        "page",
        "privacy",
        "terms",
        "sitemap",
        "newsletter",
        "rss",
        "feed",
        "feeds",
        "podcast",
    }
)

_ARTICLE_PATH_RE = re.compile(
    r"^https://fiftytwo\.in/story/([a-z0-9][a-z0-9-]{3,})/?$",
    re.IGNORECASE,
)

_MIN_TITLE_LEN = 12


def _is_article_url(url: str) -> bool:
    m = _ARTICLE_PATH_RE.match(url)
    if not m:
        return False
    segment = m.group(1).lower()
    return segment not in _SKIP_SEGMENTS


class FiftyTwoCleaner(BaseCleaner):
    """Parses the Fifty Two homepage / listing page into Article stubs."""

    source_name = "fifty_two"

    def parse(
        self,
        content_html: str,
        source_url: str,
        fetched_at: str,
    ) -> list[Article]:
        cards = extract_cards(
            content_html,
            base_url=_BASE,
            url_filter=_is_article_url,
        )

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
                    image_url=card.image_url, image_caption=None,
                    content_html="",
                    content_text="",
                    fetched_at=fetched_at,
                    hash=h,
                    category="Reading Material"
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
            if not _is_article_url(link.href):
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
                    image_url=None, image_caption=None,
                    content_html="",
                    content_text="",
                    fetched_at=fetched_at,
                    hash=h,
                    category="Reading Material"
                )
            )
        return articles
