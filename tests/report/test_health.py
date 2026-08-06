"""Tests for the shared health/audit reporting module."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.report.health import audit_processed_data


def _write(path: Path, articles: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(articles), encoding="utf-8")


def _article(**overrides) -> dict:
    base = {
        "source": "the_hindu_opinion",
        "source_id": "abc123",
        "url": "https://example.com/a",
        "title": "A reasonably long article title",
        "subtitle": None,
        "author": None,
        "published_at": None,
        "image_url": "https://example.com/img.jpg",
        "image_caption": None,
        "content_html": "<p>" + ("word " * 40) + "</p>",
        "content_text": "word " * 40,
        "fetched_at": "2026-05-07T12:00:00Z",
        "hash": "hash1",
        "category": "Reading Material",
    }
    base.update(overrides)
    return base


class AuditProcessedDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.processed_root = Path(self.tmp_dir.name) / "processed"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_missing_processed_root_returns_zeroed_stats_with_warning(self):
        stats = audit_processed_data(self.processed_root)
        self.assertEqual(stats["total_articles"], 0)
        self.assertIn("processed_root does not exist", stats["warnings"])

    def test_empty_processed_root_reports_no_articles_warning(self):
        self.processed_root.mkdir()
        stats = audit_processed_data(self.processed_root)
        self.assertEqual(stats["total_articles"], 0)
        self.assertIn("No articles found in processed data.", stats["warnings"])

    def test_counts_articles_per_source(self):
        _write(
            self.processed_root / "the_hindu_opinion" / "f1.json",
            [_article(hash="h1"), _article(hash="h2", url="https://example.com/b")],
        )
        _write(self.processed_root / "the_caravan" / "f1.json", [_article(hash="h3", source="the_caravan")])

        stats = audit_processed_data(self.processed_root)
        self.assertEqual(stats["total_articles"], 3)
        self.assertEqual(stats["per_source_counts"], {"the_hindu_opinion": 2, "the_caravan": 1})
        self.assertEqual(sorted(stats["sources"]), ["the_caravan", "the_hindu_opinion"])

    def test_same_hash_counted_once_across_files(self):
        _write(self.processed_root / "the_hindu_opinion" / "f1.json", [_article(hash="h1")])
        _write(self.processed_root / "the_hindu_opinion" / "f2.json", [_article(hash="h1")])

        stats = audit_processed_data(self.processed_root)
        self.assertEqual(stats["total_articles"], 1)

    def test_short_content_flagged(self):
        _write(
            self.processed_root / "src" / "f1.json",
            [_article(hash="h1", content_html="", content_text="")],
        )
        stats = audit_processed_data(self.processed_root)
        self.assertEqual(stats["empty_or_short_content"], 1)

    def test_missing_image_flagged(self):
        _write(self.processed_root / "src" / "f1.json", [_article(hash="h1", image_url=None)])
        stats = audit_processed_data(self.processed_root)
        self.assertEqual(stats["missing_hero_images"], 1)

    def test_majority_empty_content_triggers_warning(self):
        articles = [
            _article(hash=f"h{i}", content_html="", content_text="")
            for i in range(3)
        ] + [_article(hash="h_full")]
        _write(self.processed_root / "src" / "f1.json", articles)

        stats = audit_processed_data(self.processed_root)
        self.assertTrue(any("empty/short content" in w for w in stats["warnings"]))

    def test_duplicate_title_different_url_detected(self):
        _write(
            self.processed_root / "src" / "f1.json",
            [
                _article(hash="h1", url="https://example.com/a", title="Same Headline Text Here"),
                _article(hash="h2", url="https://example.com/a-updated", title="Same Headline Text Here"),
            ],
        )
        stats = audit_processed_data(self.processed_root)
        self.assertEqual(stats["possible_duplicate_titles"], 1)
        self.assertTrue(any("duplicate title" in w for w in stats["warnings"]))

    def test_duplicate_url_detected(self):
        _write(
            self.processed_root / "src" / "f1.json",
            [
                _article(hash="h1", url="https://example.com/a"),
                _article(hash="h2", url="https://example.com/a", title="Different title text here"),
            ],
        )
        stats = audit_processed_data(self.processed_root)
        self.assertEqual(stats["possible_duplicate_urls"], 1)

    def test_malformed_json_file_counted_not_crashed(self):
        source_dir = self.processed_root / "src"
        source_dir.mkdir(parents=True)
        (source_dir / "bad.json").write_text("{not valid json", encoding="utf-8")

        stats = audit_processed_data(self.processed_root)
        self.assertEqual(stats["malformed_files"], 1)
        self.assertTrue(any("could not be parsed" in w for w in stats["warnings"]))

    def test_non_list_json_file_counted_as_malformed(self):
        source_dir = self.processed_root / "src"
        source_dir.mkdir(parents=True)
        (source_dir / "bad.json").write_text(json.dumps({"not": "a list"}), encoding="utf-8")

        stats = audit_processed_data(self.processed_root)
        self.assertEqual(stats["malformed_files"], 1)


if __name__ == "__main__":
    unittest.main()
