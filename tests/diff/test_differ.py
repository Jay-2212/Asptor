"""Unit tests for scripts/diff/differ.py."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.diff.differ import diff_all_sources, diff_source
from scripts.diff.state_store import load_seen_hashes

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FETCHED_AT = "2026-05-07T12:00:00Z"


def _article_dict(
    source: str = "test_source",
    url: str = "https://example.com/article-one/",
    title: str = "Article One: A Long Enough Title",
    hash_: str | None = None,
) -> dict:
    h = hash_ or "aabbccdd00112233"
    return {
        "source": source,
        "source_id": h,
        "url": url,
        "title": title,
        "subtitle": None,
        "author": None,
        "published_at": None,
        "image_url": None,
        "content_html": "",
        "content_text": "",
        "fetched_at": _FETCHED_AT,
        "hash": h,
    }


def _write_processed(root: Path, source: str, articles: list[dict], stem: str = "20260507T120000Z") -> Path:
    out_dir = root / source
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{stem}.json"
    path.write_text(json.dumps(articles, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# diff_source
# ---------------------------------------------------------------------------

class DiffSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.processed_root = self.tmp / "processed"
        self.state_root = self.tmp / "state"
        self.diff_root = self.tmp / "diff"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_returns_all_articles_on_first_run(self) -> None:
        art = _article_dict(hash_="hash0001")
        _write_processed(self.processed_root, "test_source", [art])
        result = diff_source(
            source_name="test_source",
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
            timestamp="20260507T120000Z",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].hash, "hash0001")

    def test_emits_nothing_for_already_seen_articles(self) -> None:
        art = _article_dict(hash_="hash0001")
        _write_processed(self.processed_root, "test_source", [art])
        # First run: marks article as seen
        diff_source(
            source_name="test_source",
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
            timestamp="20260507T120000Z",
        )
        # Second run: same article, nothing new
        result = diff_source(
            source_name="test_source",
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
            timestamp="20260507T130000Z",
        )
        self.assertEqual(result, [])

    def test_emits_only_new_articles_on_subsequent_run(self) -> None:
        art1 = _article_dict(hash_="hash0001", url="https://example.com/one/")
        art2 = _article_dict(hash_="hash0002", url="https://example.com/two/")
        _write_processed(self.processed_root, "test_source", [art1])
        diff_source(
            source_name="test_source",
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
            timestamp="20260507T120000Z",
        )
        # Add a second article to the processed dir
        _write_processed(self.processed_root, "test_source", [art1, art2], stem="20260507T130000Z")
        result = diff_source(
            source_name="test_source",
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
            timestamp="20260507T130000Z",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].hash, "hash0002")

    def test_writes_diff_output_file(self) -> None:
        art = _article_dict(hash_="hashXXXX")
        _write_processed(self.processed_root, "test_source", [art])
        diff_source(
            source_name="test_source",
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
            timestamp="20260507T120000Z",
        )
        out_file = self.diff_root / "test_source" / "20260507T120000Z.json"
        self.assertTrue(out_file.exists())
        data = json.loads(out_file.read_text())
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["hash"], "hashXXXX")

    def test_no_diff_file_written_when_nothing_new(self) -> None:
        art = _article_dict(hash_="hash0001")
        _write_processed(self.processed_root, "test_source", [art])
        diff_source(
            source_name="test_source",
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
            timestamp="run1",
        )
        diff_source(
            source_name="test_source",
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
            timestamp="run2",
        )
        # No diff file should exist for the second run
        self.assertFalse((self.diff_root / "test_source" / "run2.json").exists())

    def test_state_updated_after_run(self) -> None:
        art = _article_dict(hash_="hash0001")
        _write_processed(self.processed_root, "test_source", [art])
        diff_source(
            source_name="test_source",
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
        )
        seen = load_seen_hashes(self.state_root, "test_source")
        self.assertIn("hash0001", seen)

    def test_returns_empty_list_when_no_processed_dir(self) -> None:
        result = diff_source(
            source_name="nonexistent_source",
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
        )
        self.assertEqual(result, [])

    def test_returns_empty_list_when_processed_dir_is_empty(self) -> None:
        (self.processed_root / "empty_source").mkdir(parents=True)
        result = diff_source(
            source_name="empty_source",
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
        )
        self.assertEqual(result, [])

    def test_multiple_processed_files_aggregated(self) -> None:
        art1 = _article_dict(hash_="hash_a", url="https://example.com/a/")
        art2 = _article_dict(hash_="hash_b", url="https://example.com/b/")
        _write_processed(self.processed_root, "test_source", [art1], stem="file1")
        _write_processed(self.processed_root, "test_source", [art2], stem="file2")
        result = diff_source(
            source_name="test_source",
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
        )
        hashes = {a.hash for a in result}
        self.assertIn("hash_a", hashes)
        self.assertIn("hash_b", hashes)

    def test_same_hash_in_multiple_files_recorded_in_state(self) -> None:
        # The same article may appear in two processed snapshot files.
        # Both copies are emitted (differ does not dedup within a run), but
        # the hash is correctly recorded in state so future runs skip it.
        art = _article_dict(hash_="same_hash")
        _write_processed(self.processed_root, "test_source", [art], stem="file1")
        _write_processed(self.processed_root, "test_source", [art], stem="file2")
        result = diff_source(
            source_name="test_source",
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
        )
        # Both copies are included in the diff output (within-run dedup is the
        # responsibility of the clean layer, not the diff layer).
        hashes = [a.hash for a in result]
        self.assertEqual(hashes.count("same_hash"), 2)
        # The hash is persisted to state so the next run skips it.
        seen = load_seen_hashes(self.state_root, "test_source")
        self.assertIn("same_hash", seen)


# ---------------------------------------------------------------------------
# diff_all_sources
# ---------------------------------------------------------------------------

class DiffAllSourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.processed_root = self.tmp / "processed"
        self.state_root = self.tmp / "state"
        self.diff_root = self.tmp / "diff"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_returns_empty_summary_when_no_processed_root(self) -> None:
        result = diff_all_sources(
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
        )
        self.assertEqual(result["diffed"], [])
        self.assertEqual(result["errors"], [])

    def test_processes_multiple_sources(self) -> None:
        for src in ("source_a", "source_b"):
            _write_processed(self.processed_root, src, [_article_dict(hash_=f"h_{src}")])
        result = diff_all_sources(
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
        )
        sources_processed = [d["source"] for d in result["diffed"]]
        self.assertIn("source_a", sources_processed)
        self.assertIn("source_b", sources_processed)
        self.assertEqual(result["errors"], [])

    def test_summary_new_articles_count(self) -> None:
        _write_processed(
            self.processed_root,
            "src_x",
            [
                _article_dict(hash_="h1", url="https://example.com/1/"),
                _article_dict(hash_="h2", url="https://example.com/2/"),
            ],
        )
        result = diff_all_sources(
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
            timestamp="20260507T120000Z",
        )
        entry = next(d for d in result["diffed"] if d["source"] == "src_x")
        self.assertEqual(entry["new_articles"], 2)

    def test_errors_do_not_abort_by_default(self) -> None:
        # Create a valid source and a source with a malformed processed file.
        _write_processed(self.processed_root, "good_source", [_article_dict()])
        bad_dir = self.processed_root / "bad_source"
        bad_dir.mkdir(parents=True)
        (bad_dir / "broken.json").write_text("not valid json", encoding="utf-8")

        result = diff_all_sources(
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
        )
        sources_processed = [d["source"] for d in result["diffed"]]
        self.assertIn("good_source", sources_processed)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0]["source"], "bad_source")

    def test_fail_fast_raises_on_error(self) -> None:
        bad_dir = self.processed_root / "bad_source"
        bad_dir.mkdir(parents=True)
        (bad_dir / "broken.json").write_text("not valid json", encoding="utf-8")
        with self.assertRaises(Exception):
            diff_all_sources(
                processed_root=self.processed_root,
                state_root=self.state_root,
                diff_root=self.diff_root,
                fail_fast=True,
            )

    def test_returns_empty_summary_when_processed_root_has_no_subdirs(self) -> None:
        self.processed_root.mkdir(parents=True)
        result = diff_all_sources(
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
        )
        self.assertEqual(result["diffed"], [])
        self.assertEqual(result["errors"], [])

    def test_shared_timestamp_used_across_sources(self) -> None:
        for src in ("src_one", "src_two"):
            _write_processed(self.processed_root, src, [_article_dict(hash_=f"h_{src}")])
        diff_all_sources(
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
            timestamp="STAMP001",
        )
        for src in ("src_one", "src_two"):
            self.assertTrue((self.diff_root / src / "STAMP001.json").exists())


if __name__ == "__main__":
    unittest.main()
