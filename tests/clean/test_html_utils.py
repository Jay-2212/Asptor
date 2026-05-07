"""Unit tests for scripts.clean.html_utils."""
from __future__ import annotations

import unittest

from scripts.clean.html_utils import (
    LinkInfo,
    extract_cards,
    extract_links,
    extract_meta,
    extract_text,
)


class ExtractTextTests(unittest.TestCase):
    def test_strips_html_tags(self) -> None:
        result = extract_text("<p>Hello <b>world</b>!</p>")
        self.assertIn("Hello", result)
        self.assertIn("world", result)
        self.assertNotIn("<b>", result)

    def test_skips_script_content(self) -> None:
        html = "<p>Visible</p><script>var x = 1;</script>"
        result = extract_text(html)
        self.assertIn("Visible", result)
        self.assertNotIn("var x", result)

    def test_skips_style_content(self) -> None:
        html = "<p>Visible</p><style>.cls { color: red; }</style>"
        result = extract_text(html)
        self.assertIn("Visible", result)
        self.assertNotIn("color", result)

    def test_empty_html_returns_empty_string(self) -> None:
        self.assertEqual(extract_text(""), "")


class ExtractLinksTests(unittest.TestCase):
    def test_extracts_absolute_links(self) -> None:
        html = '<a href="https://example.com/article">Read More</a>'
        links = extract_links(html)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].href, "https://example.com/article")
        self.assertEqual(links[0].text, "Read More")

    def test_resolves_root_relative_links(self) -> None:
        html = '<a href="/opinion/article-slug">Opinion Piece</a>'
        links = extract_links(html, base_url="https://www.thehindu.com")
        self.assertEqual(links[0].href, "https://www.thehindu.com/opinion/article-slug")

    def test_skips_fragment_only_links(self) -> None:
        html = '<a href="#top">Back to top</a>'
        links = extract_links(html)
        self.assertEqual(len(links), 0)

    def test_skips_links_without_text(self) -> None:
        html = '<a href="https://example.com/article"><img src="img.jpg"></a>'
        links = extract_links(html)
        self.assertEqual(len(links), 0)

    def test_skips_script_inside_link(self) -> None:
        html = (
            '<a href="https://example.com/article">'
            "<script>alert(1)</script>Visible</a>"
        )
        links = extract_links(html)
        self.assertEqual(links[0].text, "Visible")

    def test_link_info_equality(self) -> None:
        a = LinkInfo(href="https://a.com", text="A")
        b = LinkInfo(href="https://a.com", text="A")
        self.assertEqual(a, b)

    def test_collapses_internal_whitespace(self) -> None:
        html = '<a href="https://example.com/a">  Title   With  Spaces  </a>'
        links = extract_links(html)
        self.assertEqual(links[0].text, "Title With Spaces")

    def test_protocol_relative_href(self) -> None:
        html = '<a href="//example.com/path">Protocol Relative</a>'
        links = extract_links(html, base_url="https://example.com")
        self.assertEqual(links[0].href, "https://example.com/path")


class ExtractMetaTests(unittest.TestCase):
    def test_extracts_og_title(self) -> None:
        html = '<meta property="og:title" content="My Article Title">'
        meta = extract_meta(html)
        self.assertEqual(meta.og("title"), "My Article Title")

    def test_extracts_og_image(self) -> None:
        html = '<meta property="og:image" content="https://example.com/img.jpg">'
        meta = extract_meta(html)
        self.assertEqual(meta.og("image"), "https://example.com/img.jpg")

    def test_extracts_page_title(self) -> None:
        html = "<html><head><title>Page Title</title></head></html>"
        meta = extract_meta(html)
        self.assertEqual(meta.page_title, "Page Title")

    def test_extracts_meta_description(self) -> None:
        html = '<meta name="description" content="A description">'
        meta = extract_meta(html)
        self.assertEqual(meta.get("description"), "A description")

    def test_returns_empty_string_for_missing_tag(self) -> None:
        meta = extract_meta("<html></html>")
        self.assertEqual(meta.og("title"), "")
        self.assertEqual(meta.page_title, "")


class ExtractCardsTests(unittest.TestCase):
    """Tests for the card-context-aware extractor."""

    _LISTING_HTML = """
    <html><body>
      <article>
        <img src="https://example.com/img1.jpg" />
        <h2><a href="https://example.com/opinion/article-one">
          Democracy Under Pressure: The Long View
        </a></h2>
      </article>
      <article>
        <img src="https://example.com/img2.jpg" />
        <h2><a href="https://example.com/opinion/article-two">
          Economic Reforms and Their Discontents
        </a></h2>
        <time datetime="2026-05-01">May 1, 2026</time>
      </article>
      <article>
        <a href="/login">Sign In</a>
      </article>
    </body></html>
    """

    def test_extracts_article_cards(self) -> None:
        cards = extract_cards(self._LISTING_HTML, base_url="https://example.com")
        urls = [c.url for c in cards]
        self.assertIn("https://example.com/opinion/article-one", urls)
        self.assertIn("https://example.com/opinion/article-two", urls)

    def test_card_includes_title(self) -> None:
        cards = extract_cards(self._LISTING_HTML, base_url="https://example.com")
        titles = [c.title for c in cards]
        self.assertTrue(
            any("Democracy Under Pressure" in t for t in titles)
        )

    def test_card_includes_image_url(self) -> None:
        cards = extract_cards(self._LISTING_HTML, base_url="https://example.com")
        images = [c.image_url for c in cards if c.image_url]
        self.assertIn("https://example.com/img1.jpg", images)

    def test_card_includes_datetime(self) -> None:
        cards = extract_cards(self._LISTING_HTML, base_url="https://example.com")
        dates = [c.date_text for c in cards if c.date_text]
        self.assertIn("2026-05-01", dates)

    def test_url_filter_applied(self) -> None:
        def only_opinion(url: str) -> bool:
            return "/opinion/" in url

        cards = extract_cards(
            self._LISTING_HTML,
            base_url="https://example.com",
            url_filter=only_opinion,
        )
        for card in cards:
            self.assertIn("/opinion/", card.url)

    def test_short_title_links_not_emitted(self) -> None:
        html = """
        <article>
          <a href="https://example.com/opinion/x">Hi</a>
        </article>
        """
        cards = extract_cards(html, base_url="https://example.com")
        self.assertEqual(len(cards), 0)

    def test_deduplication_not_done_by_extractor(self) -> None:
        """Dedup is the cleaner's responsibility, not html_utils."""
        html = """
        <article>
          <a href="https://example.com/opinion/dup">A Title Long Enough To Pass</a>
        </article>
        <article>
          <a href="https://example.com/opinion/dup">A Title Long Enough To Pass</a>
        </article>
        """
        cards = extract_cards(html, base_url="https://example.com")
        self.assertEqual(len(cards), 2)


if __name__ == "__main__":
    unittest.main()
