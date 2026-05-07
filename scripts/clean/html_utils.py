"""Lightweight HTML parsing utilities built on the Python stdlib ``html.parser``.

These helpers deliberately avoid third-party dependencies (no BeautifulSoup).
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

# Tags whose content should be silently discarded.
_INVISIBLE_TAGS = frozenset({"script", "style", "noscript", "head"})


# ---------------------------------------------------------------------------
# Plain-text extraction
# ---------------------------------------------------------------------------


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth: int = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in _INVISIBLE_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _INVISIBLE_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._parts)


def extract_text(html: str) -> str:
    """Return a single whitespace-separated plain-text string from *html*."""
    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()


# ---------------------------------------------------------------------------
# Link extraction
# ---------------------------------------------------------------------------


class LinkInfo:
    """A hyperlink and the visible text associated with it."""

    __slots__ = ("href", "text")

    def __init__(self, href: str, text: str) -> None:
        self.href = href
        self.text = text

    def __repr__(self) -> str:
        return f"LinkInfo(href={self.href!r}, text={self.text!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LinkInfo):
            return NotImplemented
        return self.href == other.href and self.text == other.text


_FRAGMENT_ONLY_RE = re.compile(r"^#")
_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+\-.]*:", re.IGNORECASE)


def _resolve_href(href: str, base_url: str) -> str:
    """Resolve an absolute or root-relative *href* against *base_url*."""
    href = href.strip()
    if not href or _FRAGMENT_ONLY_RE.match(href):
        return ""
    if _SCHEME_RE.match(href):
        return href
    if href.startswith("//"):
        # Protocol-relative: inherit scheme from base_url
        scheme = base_url.split("://")[0] if "://" in base_url else "https"
        return f"{scheme}:{href}"
    if href.startswith("/"):
        if base_url:
            # Strip path from base_url to get origin
            m = re.match(r"(https?://[^/]+)", base_url)
            origin = m.group(1) if m else base_url.rstrip("/")
            return origin + href
    return href


class _LinkExtractor(HTMLParser):
    def __init__(self, base_url: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self._links: list[LinkInfo] = []
        self._current_href: str | None = None
        self._current_text_parts: list[str] = []
        self._base_url = base_url
        self._skip_depth: int = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attr_dict = dict(attrs)
        if tag in _INVISIBLE_TAGS:
            self._skip_depth += 1
            return
        if tag == "a" and self._skip_depth == 0:
            href = _resolve_href(attr_dict.get("href", ""), self._base_url)
            if href:
                self._current_href = href
                self._current_text_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag in _INVISIBLE_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if tag == "a" and self._current_href is not None:
            text = " ".join(self._current_text_parts).strip()
            # Collapse internal whitespace
            text = re.sub(r"\s+", " ", text)
            if text:
                self._links.append(LinkInfo(href=self._current_href, text=text))
            self._current_href = None
            self._current_text_parts = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and self._current_href is not None:
            stripped = data.strip()
            if stripped:
                self._current_text_parts.append(stripped)

    def get_links(self) -> list[LinkInfo]:
        return list(self._links)


def extract_links(html: str, base_url: str = "") -> list[LinkInfo]:
    """Return all hyperlinks found in *html*, resolving relative paths against *base_url*."""
    parser = _LinkExtractor(base_url=base_url)
    parser.feed(html)
    return parser.get_links()


# ---------------------------------------------------------------------------
# <meta> / Open Graph tag extraction
# ---------------------------------------------------------------------------


class MetaTags:
    """Parsed collection of ``<meta>`` and ``<title>`` values."""

    __slots__ = ("_data", "page_title")

    def __init__(self, data: dict[str, str], page_title: str) -> None:
        self._data = data
        self.page_title = page_title

    def get(self, name: str, default: str = "") -> str:
        return self._data.get(name, default)

    def og(self, property_suffix: str, default: str = "") -> str:
        """Shorthand for ``og:<property_suffix>`` Open Graph tags."""
        return self._data.get(f"og:{property_suffix}", default)

    def all_og(self) -> dict[str, str]:
        return {k: v for k, v in self._data.items() if k.startswith("og:")}


class _MetaExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._data: dict[str, str] = {}
        self._page_title: str = ""
        self._in_title: bool = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attr_dict = dict(attrs)
        if tag == "meta":
            name = attr_dict.get("property") or attr_dict.get("name", "")
            content = attr_dict.get("content", "")
            if name and content:
                self._data[name] = content
        elif tag == "title":
            self._in_title = True
            self._title_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            self._page_title = " ".join(self._title_parts).strip()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)

    def get_tags(self) -> MetaTags:
        return MetaTags(data=dict(self._data), page_title=self._page_title)


def extract_meta(html: str) -> MetaTags:
    """Return structured meta-tag data from *html*."""
    parser = _MetaExtractor()
    parser.feed(html)
    return parser.get_tags()


# ---------------------------------------------------------------------------
# Card-context-aware extraction
# ---------------------------------------------------------------------------


class CardInfo:
    """Represents one article card found on a listing page.

    Attributes are intentionally optional — not all listing pages expose
    authors, dates, or secondary images.
    """

    __slots__ = ("url", "title", "image_url", "author", "date_text")

    def __init__(
        self,
        url: str,
        title: str,
        image_url: str | None = None,
        author: str | None = None,
        date_text: str | None = None,
    ) -> None:
        self.url = url
        self.title = title
        self.image_url = image_url
        self.author = author
        self.date_text = date_text

    def __repr__(self) -> str:
        return (
            f"CardInfo(url={self.url!r}, title={self.title!r}, "
            f"image_url={self.image_url!r})"
        )


class _CardExtractor(HTMLParser):
    """
    State-machine HTML parser that groups ``<img>``, ``<a>``, and metadata
    spans into article-card bundles.

    Strategy:
    - Track a sliding "card" window: when we enter a structural block tag
      (``<article>``, ``<li>``, ``<div>``, ``<section>``), reset our local
      card state.
    - Inside each block, collect the first ``<img src>``, the first
      content ``<a href>`` whose link text is long enough to be a title,
      and any ``<time>`` or author-tagged elements.
    - On block end, emit a CardInfo if we have at minimum a URL and a title.
    """

    _CARD_TAGS = frozenset({"article", "li", "div", "section"})
    _DATE_TAGS = frozenset({"time"})
    _MIN_TITLE_LEN = 12

    def __init__(self, base_url: str = "", url_filter=None) -> None:
        super().__init__(convert_charrefs=True)
        self._base_url = base_url
        self._url_filter = url_filter or (lambda _: True)
        self._cards: list[CardInfo] = []

        # Stack of card-context dicts; push on block open, pop on block close.
        self._stack: list[dict] = []
        self._skip_depth: int = 0

    # -- helpers -----------------------------------------------------------

    def _push(self) -> None:
        self._stack.append(
            {
                "url": None,
                "title": None,
                "image_url": None,
                "author": None,
                "date_text": None,
                "in_link": False,
                "link_parts": [],
                "in_date": False,
                "date_parts": [],
            }
        )

    def _pop(self) -> None:
        if not self._stack:
            return
        ctx = self._stack.pop()
        if ctx["url"] and ctx["title"] and self._url_filter(ctx["url"]):
            self._cards.append(
                CardInfo(
                    url=ctx["url"],
                    title=ctx["title"],
                    image_url=ctx["image_url"],
                    author=ctx["author"],
                    date_text=ctx["date_text"],
                )
            )

    @property
    def _ctx(self) -> dict | None:
        return self._stack[-1] if self._stack else None

    # -- HTMLParser overrides ----------------------------------------------

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attr_dict = dict(attrs)

        if tag in _INVISIBLE_TAGS:
            self._skip_depth += 1
            return

        if self._skip_depth > 0:
            return

        if tag in self._CARD_TAGS:
            self._push()
            return

        ctx = self._ctx
        if ctx is None:
            return

        if tag == "img":
            if ctx["image_url"] is None:
                src = attr_dict.get("src", "").strip()
                if src and not src.startswith("data:"):
                    ctx["image_url"] = _resolve_href(src, self._base_url) or src

        elif tag == "a":
            href = _resolve_href(attr_dict.get("href", ""), self._base_url)
            if href and ctx["url"] is None:
                ctx["url"] = href
                ctx["in_link"] = True
                ctx["link_parts"] = []

        elif tag in self._DATE_TAGS:
            ctx["in_date"] = True
            ctx["date_parts"] = []
            dt = attr_dict.get("datetime", "")
            if dt:
                ctx["date_text"] = dt

    def handle_endtag(self, tag: str) -> None:
        if tag in _INVISIBLE_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return

        if self._skip_depth > 0:
            return

        ctx = self._ctx

        if tag in self._CARD_TAGS:
            self._pop()
            return

        if ctx is None:
            return

        if tag == "a" and ctx["in_link"]:
            text = re.sub(r"\s+", " ", " ".join(ctx["link_parts"])).strip()
            if len(text) >= self._MIN_TITLE_LEN and ctx["title"] is None:
                ctx["title"] = text
            ctx["in_link"] = False
            ctx["link_parts"] = []

        elif tag in self._DATE_TAGS and ctx["in_date"]:
            if ctx["date_text"] is None:
                ctx["date_text"] = re.sub(
                    r"\s+", " ", " ".join(ctx["date_parts"])
                ).strip() or None
            ctx["in_date"] = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        ctx = self._ctx
        if ctx is None:
            return
        stripped = data.strip()
        if not stripped:
            return
        if ctx["in_link"]:
            ctx["link_parts"].append(stripped)
        if ctx["in_date"]:
            ctx["date_parts"].append(stripped)

    def get_cards(self) -> list[CardInfo]:
        # Flush any unclosed blocks
        while self._stack:
            self._pop()
        return list(self._cards)


def extract_cards(html: str, base_url: str = "", url_filter=None) -> list[CardInfo]:
    """Return article-card bundles extracted from a listing-page HTML.

    *url_filter* is an optional ``callable(url: str) -> bool`` used to discard
    non-article links before they are emitted as cards.
    """
    parser = _CardExtractor(base_url=base_url, url_filter=url_filter)
    parser.feed(html)
    return parser.get_cards()
