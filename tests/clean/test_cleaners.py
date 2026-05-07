"""Unit tests for source-specific cleaners."""
from __future__ import annotations

import unittest

from scripts.clean.fifty_two_cleaner import FiftyTwoCleaner
from scripts.clean.the_caravan_cleaner import TheCaravanCleaner
from scripts.clean.the_hindu_cleaner import TheHinduCleaner

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_FETCHED_AT = "2026-05-01T12:00:00Z"


def _make_snapshot(source_name: str, source_url: str, content_html: str) -> dict:
    return {
        "source": {"name": source_name, "url": source_url},
        "fetched_at": _FETCHED_AT,
        "content_html": content_html,
    }


# ---------------------------------------------------------------------------
# The Hindu Opinion cleaner
# ---------------------------------------------------------------------------

_HINDU_HTML = """
<html><body>
  <article>
    <img src="https://www.thehindu.com/images/img1.jpg" />
    <a href="/opinion/editorial/democracy-under-pressure/">
      Democracy Under Pressure: A Critical Analysis
    </a>
    <time datetime="2026-04-30">April 30, 2026</time>
  </article>
  <article>
    <a href="/opinion/columns/the-climate-emergency-revisited/">
      The Climate Emergency Revisited: What Policy Must Deliver
    </a>
  </article>
  <article>
    <!-- navigation link: should be excluded -->
    <a href="/opinion/">Opinion Home</a>
  </article>
  <nav>
    <a href="/subscribe">Subscribe</a>
    <a href="/login">Login</a>
  </nav>
</body></html>
"""


class TheHinduCleanerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cleaner = TheHinduCleaner()
        self.snapshot = _make_snapshot(
            "the_hindu_opinion",
            "https://www.thehindu.com/opinion/",
            _HINDU_HTML,
        )

    def test_source_name(self) -> None:
        self.assertEqual(self.cleaner.source_name, "the_hindu_opinion")

    def test_returns_articles(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        self.assertGreater(len(articles), 0)

    def test_article_urls_are_absolute(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        for a in articles:
            self.assertTrue(a.url.startswith("https://"), msg=f"Not absolute: {a.url}")

    def test_excludes_subscribe_and_login(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        urls = [a.url for a in articles]
        self.assertFalse(any("subscribe" in u for u in urls))
        self.assertFalse(any("login" in u for u in urls))

    def test_extracts_editorial_article(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        urls = [a.url for a in articles]
        self.assertTrue(any("democracy-under-pressure" in u for u in urls))

    def test_extracts_columns_article(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        urls = [a.url for a in articles]
        self.assertTrue(any("climate-emergency" in u for u in urls))

    def test_article_title_non_empty(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        for a in articles:
            self.assertTrue(len(a.title) >= 12, msg=f"Short title: {a.title!r}")

    def test_article_has_hash(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        for a in articles:
            self.assertEqual(len(a.hash), 16)

    def test_no_duplicate_urls(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        urls = [a.url for a in articles]
        self.assertEqual(len(urls), len(set(urls)))

    def test_fetched_at_propagated(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        for a in articles:
            self.assertEqual(a.fetched_at, _FETCHED_AT)

    def test_source_field_correct(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        for a in articles:
            self.assertEqual(a.source, "the_hindu_opinion")

    def test_content_fields_empty_at_listing_stage(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        for a in articles:
            self.assertEqual(a.content_html, "")
            self.assertEqual(a.content_text, "")

    def test_image_url_extracted(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        images = [a.image_url for a in articles if a.image_url]
        self.assertGreater(len(images), 0)

    def test_date_extracted(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        dates = [a.published_at for a in articles if a.published_at]
        self.assertGreater(len(dates), 0)

    def test_empty_html_returns_empty_list(self) -> None:
        snapshot = _make_snapshot("the_hindu_opinion", "https://www.thehindu.com/opinion/", "")
        articles = self.cleaner.clean_snapshot(snapshot)
        self.assertEqual(articles, [])

    def test_hash_equals_source_id(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        for a in articles:
            self.assertEqual(a.hash, a.source_id)


# ---------------------------------------------------------------------------
# The Caravan cleaner
# ---------------------------------------------------------------------------

_CARAVAN_HTML = """
<html><body>
  <article>
    <img src="https://caravanmagazine.in/images/cover.jpg" />
    <a href="https://caravanmagazine.in/politics/opposition-strategy-2026">
      The Opposition Strategy That Could Work in 2026
    </a>
    <time datetime="2026-04-28">April 28, 2026</time>
  </article>
  <article>
    <a href="https://caravanmagazine.in/culture/literature-of-resistance">
      A Literature of Resistance: New Voices from the Margins
    </a>
  </article>
  <nav>
    <a href="https://caravanmagazine.in/subscribe">Subscribe</a>
    <a href="https://caravanmagazine.in/tag/environment">Environment</a>
    <a href="https://caravanmagazine.in/author/staff-writer">Staff Writer</a>
  </nav>
</body></html>
"""


class TheCaravanCleanerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cleaner = TheCaravanCleaner()
        self.snapshot = _make_snapshot(
            "the_caravan",
            "https://caravanmagazine.in/",
            _CARAVAN_HTML,
        )

    def test_source_name(self) -> None:
        self.assertEqual(self.cleaner.source_name, "the_caravan")

    def test_returns_articles(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        self.assertGreater(len(articles), 0)

    def test_excludes_utility_pages(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        urls = [a.url for a in articles]
        self.assertFalse(any("subscribe" in u for u in urls))
        self.assertFalse(any("/tag/" in u for u in urls))
        self.assertFalse(any("/author/" in u for u in urls))

    def test_extracts_politics_article(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        urls = [a.url for a in articles]
        self.assertTrue(any("opposition-strategy" in u for u in urls))

    def test_extracts_culture_article(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        urls = [a.url for a in articles]
        self.assertTrue(any("literature-of-resistance" in u for u in urls))

    def test_no_duplicate_urls(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        urls = [a.url for a in articles]
        self.assertEqual(len(urls), len(set(urls)))

    def test_fetched_at_propagated(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        for a in articles:
            self.assertEqual(a.fetched_at, _FETCHED_AT)

    def test_empty_html_returns_empty_list(self) -> None:
        snapshot = _make_snapshot("the_caravan", "https://caravanmagazine.in/", "")
        self.assertEqual(self.cleaner.clean_snapshot(snapshot), [])


# ---------------------------------------------------------------------------
# Fifty Two cleaner
# ---------------------------------------------------------------------------

_FIFTY_TWO_HTML = """
<html><body>
  <article>
    <img src="https://fiftytwo.in/images/story1.jpg" />
    <a href="https://fiftytwo.in/story/the-last-wilderness/">
      The Last Wilderness: Saving India's Forgotten Forests
    </a>
    <time datetime="2026-03-15">March 15, 2026</time>
  </article>
  <article>
    <a href="https://fiftytwo.in/story/a-river-runs-through-it/">
      A River Runs Through It: Life Along the Ganga
    </a>
  </article>
  <nav>
    <a href="https://fiftytwo.in/about">About</a>
    <a href="https://fiftytwo.in/tag/nature">Nature</a>
  </nav>
</body></html>
"""


class FiftyTwoCleanerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cleaner = FiftyTwoCleaner()
        self.snapshot = _make_snapshot(
            "fifty_two",
            "https://fiftytwo.in/",
            _FIFTY_TWO_HTML,
        )

    def test_source_name(self) -> None:
        self.assertEqual(self.cleaner.source_name, "fifty_two")

    def test_returns_articles(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        self.assertGreater(len(articles), 0)

    def test_extracts_article_one(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        urls = [a.url for a in articles]
        self.assertTrue(any("last-wilderness" in u for u in urls))

    def test_extracts_article_two(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        urls = [a.url for a in articles]
        self.assertTrue(any("river-runs" in u for u in urls))

    def test_excludes_utility_pages(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        urls = [a.url for a in articles]
        self.assertFalse(any("/about" in u for u in urls))
        self.assertFalse(any("/tag/" in u for u in urls))

    def test_no_duplicate_urls(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        urls = [a.url for a in articles]
        self.assertEqual(len(urls), len(set(urls)))

    def test_fetched_at_propagated(self) -> None:
        articles = self.cleaner.clean_snapshot(self.snapshot)
        for a in articles:
            self.assertEqual(a.fetched_at, _FETCHED_AT)

    def test_empty_html_returns_empty_list(self) -> None:
        snapshot = _make_snapshot("fifty_two", "https://fiftytwo.in/", "")
        self.assertEqual(self.cleaner.clean_snapshot(snapshot), [])


if __name__ == "__main__":
    unittest.main()
