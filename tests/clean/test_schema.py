"""Unit tests for scripts.clean.schema.Article."""
from __future__ import annotations

import json
import unittest

from scripts.clean.schema import Article


def _make_article(**overrides) -> Article:
    defaults = dict(
        source="test_source",
        source_id="abc123",
        url="https://example.com/article/test-slug",
        title="A long enough title for testing",
        subtitle=None,
        author=None,
        published_at=None,
        image_url=None,
        image_caption=None,
        content_html="",
        content_text="",
        fetched_at="2026-01-02T03:04:05Z",
        hash="abc123",
    )
    defaults.update(overrides)
    return Article(**defaults)


class ArticleHashTests(unittest.TestCase):
    def test_compute_hash_is_deterministic(self) -> None:
        h1 = Article.compute_hash("https://example.com/a", "Title A")
        h2 = Article.compute_hash("https://example.com/a", "Title A")
        self.assertEqual(h1, h2)

    def test_compute_hash_differs_for_different_inputs(self) -> None:
        h1 = Article.compute_hash("https://example.com/a", "Title A")
        h2 = Article.compute_hash("https://example.com/b", "Title B")
        self.assertNotEqual(h1, h2)

    def test_compute_hash_is_16_hex_chars(self) -> None:
        h = Article.compute_hash("https://example.com/a", "Title A")
        self.assertEqual(len(h), 16)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_compute_hash_strips_whitespace(self) -> None:
        h1 = Article.compute_hash("https://example.com/a", "  Title A  ")
        h2 = Article.compute_hash("https://example.com/a", "Title A")
        self.assertEqual(h1, h2)


class ArticleSerializationTests(unittest.TestCase):
    def test_to_dict_returns_dict(self) -> None:
        article = _make_article()
        d = article.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["source"], "test_source")
        self.assertEqual(d["title"], "A long enough title for testing")

    def test_from_dict_roundtrip(self) -> None:
        article = _make_article()
        restored = Article.from_dict(article.to_dict())
        self.assertEqual(article, restored)

    def test_to_json_roundtrip(self) -> None:
        article = _make_article()
        json_str = article.to_json()
        restored = Article.from_json(json_str)
        self.assertEqual(article, restored)

    def test_to_json_is_valid_json(self) -> None:
        article = _make_article()
        parsed = json.loads(article.to_json())
        self.assertIsInstance(parsed, dict)

    def test_optional_fields_are_null_in_json(self) -> None:
        article = _make_article()
        d = json.loads(article.to_json())
        self.assertIsNone(d["subtitle"])
        self.assertIsNone(d["author"])
        self.assertIsNone(d["published_at"])
        self.assertIsNone(d["image_url"])


if __name__ == "__main__":
    unittest.main()
