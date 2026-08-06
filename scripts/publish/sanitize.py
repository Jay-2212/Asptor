"""Output-boundary sanitization for the static publisher.

All article fields originate from third-party publisher HTML. Nothing in the
fetch/clean layers guarantees they are safe to interpolate into the generated
site, so every value is treated as untrusted here, at the last point before
it is written to disk.

Two distinct treatments are used:

- ``escape_text`` — for plain text rendered into HTML text nodes or
  attributes (titles, authors, dates, excerpts). Escapes everything.
- ``safe_url`` — for values used as ``href``/``src`` targets. Rejects any
  scheme other than http(s) (blocks ``javascript:``, ``data:``, etc.) and
  HTML-escapes what remains so it is attribute-safe.
- ``sanitize_content_html`` — for ``content_html``, which is meant to render
  as markup. Strips dangerous tags/attributes instead of escaping, since
  escaping would blank every article body.
"""
from __future__ import annotations

import html
import re

from bs4 import BeautifulSoup

_SAFE_URL_SCHEMES = frozenset({"http", "https", "mailto", "tel"})
_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")

_DANGEROUS_TAGS = frozenset(
    {"script", "style", "iframe", "object", "embed", "form", "meta", "link", "base", "svg"}
)
_URL_ATTRS = frozenset({"href", "src"})


def escape_text(value) -> str:
    """Return *value* safe for insertion into an HTML text node or attribute."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def is_safe_url(value) -> bool:
    """Return whether *value* is an absolute http(s) URL or a root-relative path."""
    if not value:
        return False
    value = str(value).strip()
    if not value:
        return False
    match = _SCHEME_RE.match(value)
    if match:
        return match.group(1).lower() in _SAFE_URL_SCHEMES
    # Scheme-less: allow root-relative paths and same-page fragment links
    # (e.g. The Hindu's live-blog in-page anchors like "#424441"), reject
    # anything else (opaque strings are not usable as a URL anyway).
    return value.startswith("/") or value.startswith("#")


def safe_url(value, *, default: str = "") -> str:
    """Return an HTML-attribute-safe URL, or *default* if *value* is unsafe."""
    if not is_safe_url(value):
        return default
    return html.escape(str(value).strip(), quote=True)


def sanitize_content_html(content_html: str) -> str:
    """Strip script-execution vectors from already-rendered article HTML.

    The per-source cleaners already remove ``<script>``/``<style>``/``<iframe>``
    from the body, but do not strip inline event handlers or dangerous URL
    schemes on the tags they keep. This is the single choke point that runs
    regardless of which cleaner produced the HTML.
    """
    if not content_html:
        return ""

    soup = BeautifulSoup(content_html, "html.parser")

    for tag in soup.find_all(list(_DANGEROUS_TAGS)):
        tag.decompose()

    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            if attr.lower().startswith("on"):
                del tag.attrs[attr]
        for attr in _URL_ATTRS:
            if tag.has_attr(attr) and not is_safe_url(tag.attrs[attr]):
                del tag.attrs[attr]

    return str(soup)
