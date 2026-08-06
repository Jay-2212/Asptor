"""Tests for the full-article-body fetch/clean stage.

Covers the diff-file bookkeeping fix (a scheduled run must not re-walk
every diff file ever produced -- see the comment in run_full_clean.py) and
that per-article failures are counted and surfaced rather than silently
swallowed.
"""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.clean.run_full_clean import FullArticleProcessor
from scripts.clean.schema import Article


def _article(hash_, url="https://example.com/a", content_html="") -> dict:
    return Article(
        source="the_caravan",
        source_id=hash_,
        url=url,
        title="A reasonably long article title",
        subtitle=None,
        author=None,
        published_at=None,
        image_url=None,
        image_caption=None,
        content_html=content_html,
        content_text="",
        fetched_at="2026-05-01T10:00:00Z",
        hash=hash_,
    ).to_dict()


class FullArticleProcessorDiffBookkeepingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        root = Path(self.tmp.name)
        self.processed_root = root / "processed"
        self.diff_root = root / "diff"
        self.state_root = root / "state"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_diff(self, filename: str, articles: list) -> Path:
        path = self.diff_root / "the_caravan" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(articles), encoding="utf-8")
        return path

    def test_second_run_skips_already_seen_diff_file(self):
        self._write_diff("20260501T100000Z.json", [_article("h1")])
        processor = FullArticleProcessor(self.processed_root, self.diff_root, self.state_root)

        with patch(
            "scripts.clean.run_full_clean.fetch_with_retries",
            return_value="<html></html>",
        ), patch(
            "scripts.clean.article_cleaners.the_caravan.TheCaravanArticleCleaner.clean",
            return_value={"content_html": "<p>Body</p>", "content_text": "Body"},
        ) as mock_clean:
            processor.process_all(limit=5)
            self.assertEqual(mock_clean.call_count, 1)

            # Second run over the same (unchanged) diff directory: nothing
            # new should be fetched.
            processor2 = FullArticleProcessor(self.processed_root, self.diff_root, self.state_root)
            processor2.process_all(limit=5)
            self.assertEqual(mock_clean.call_count, 1)

    def test_new_diff_file_is_still_processed_after_prior_run(self):
        self._write_diff("20260501T100000Z.json", [_article("h1")])
        processor = FullArticleProcessor(self.processed_root, self.diff_root, self.state_root)
        with patch(
            "scripts.clean.run_full_clean.fetch_with_retries",
            return_value="<html></html>",
        ), patch(
            "scripts.clean.article_cleaners.the_caravan.TheCaravanArticleCleaner.clean",
            return_value={"content_html": "<p>Body</p>", "content_text": "Body"},
        ) as mock_clean:
            processor.process_all(limit=5)
            self.assertEqual(mock_clean.call_count, 1)

            self._write_diff("20260502T100000Z.json", [_article("h2", url="https://example.com/b")])
            processor.process_all(limit=5)
            self.assertEqual(mock_clean.call_count, 2)

    def test_repair_mode_ignores_seen_diffs_marker(self):
        # repair_empty scans processed_root directly, independent of the
        # diff-file bookkeeping used for scheduled runs.
        proc_file = self.processed_root / "the_caravan" / "20260501T100000Z.json"
        proc_file.parent.mkdir(parents=True)
        proc_file.write_text(json.dumps([_article("h1", content_html="<p>old</p>")]), encoding="utf-8")

        processor = FullArticleProcessor(self.processed_root, self.diff_root, self.state_root)
        with patch(
            "scripts.clean.run_full_clean.fetch_with_retries",
            return_value="<html></html>",
        ), patch(
            "scripts.clean.article_cleaners.the_caravan.TheCaravanArticleCleaner.clean",
            return_value={"content_html": "<p>Repaired</p>", "content_text": "Repaired"},
        ) as mock_clean:
            processor.process_all(limit=5, repair_empty=True)
            self.assertEqual(mock_clean.call_count, 1)

    def test_stats_count_fetch_failures(self):
        self._write_diff("20260501T100000Z.json", [_article("h1"), _article("h2", url="https://example.com/b")])
        processor = FullArticleProcessor(self.processed_root, self.diff_root, self.state_root)
        with patch(
            "scripts.clean.run_full_clean.fetch_with_retries",
            side_effect=Exception("network down"),
        ):
            stats = processor.process_all(limit=5)
        self.assertEqual(stats["attempted"], 2)
        self.assertEqual(stats["failed"], 2)
        self.assertEqual(stats["succeeded"], 0)

    def test_missing_diff_root_returns_stats_without_crashing(self):
        processor = FullArticleProcessor(self.processed_root, self.diff_root, self.state_root)
        stats = processor.process_all(limit=5)
        self.assertEqual(stats, {"attempted": 0, "succeeded": 0, "failed": 0})

    def test_already_enriched_article_is_not_refetched(self):
        self._write_diff("20260501T100000Z.json", [_article("h1", content_html="<p>Already has body</p>")])
        processor = FullArticleProcessor(self.processed_root, self.diff_root, self.state_root)
        with patch("scripts.clean.run_full_clean.fetch_with_retries") as mock_fetch:
            processor.process_all(limit=5)
            mock_fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
