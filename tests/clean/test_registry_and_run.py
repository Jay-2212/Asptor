"""Unit tests for scripts.clean.registry and scripts.clean.run_clean."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.clean.registry import CLEANERS, get_cleaner
from scripts.clean.run_clean import process_snapshot, run_clean

# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class RegistryTests(unittest.TestCase):
    def test_all_expected_sources_registered(self) -> None:
        expected = {
            "the_hindu_opinion",
            "the_hindu_national",
            "indian_express_explained",
            "scroll_magazine",
            "the_caravan",
            "fifty_two",
        }
        self.assertEqual(set(CLEANERS.keys()), expected)

    def test_get_cleaner_returns_correct_instance(self) -> None:
        cleaner = get_cleaner("the_hindu_opinion")
        self.assertEqual(cleaner.source_name, "the_hindu_opinion")

    def test_get_cleaner_raises_for_unknown_source(self) -> None:
        with self.assertRaises(KeyError):
            get_cleaner("unknown_source_xyz")

    def test_error_message_includes_known_sources(self) -> None:
        try:
            get_cleaner("missing_source")
        except KeyError as exc:
            msg = str(exc)
            self.assertIn("fifty_two", msg)
            self.assertIn("the_caravan", msg)
            self.assertIn("the_hindu_opinion", msg)


# ---------------------------------------------------------------------------
# run_clean integration tests
# ---------------------------------------------------------------------------

_HINDU_LISTING_HTML = """
<html><body>
  <article>
    <a href="/opinion/editorial/democracy-test/">
      Democracy Under Pressure: A Comprehensive Look
    </a>
  </article>
</body></html>
"""


def _write_snapshot(directory: Path, source_name: str, source_url: str, html: str) -> Path:
    snapshot = {
        "source": {"name": source_name, "url": source_url},
        "fetched_at": "2026-05-01T10:00:00Z",
        "content_html": html,
    }
    out_file = directory / source_name / "20260501T100000Z.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(snapshot), encoding="utf-8")
    return out_file


class ProcessSnapshotTests(unittest.TestCase):
    def test_processes_hindu_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as proc_dir:
            snap_path = _write_snapshot(
                Path(raw_dir),
                "the_hindu_opinion",
                "https://www.thehindu.com/opinion/",
                _HINDU_LISTING_HTML,
            )
            articles = process_snapshot(snap_path, Path(proc_dir))
            self.assertGreater(len(articles), 0)

    def test_writes_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as proc_dir:
            snap_path = _write_snapshot(
                Path(raw_dir),
                "the_hindu_opinion",
                "https://www.thehindu.com/opinion/",
                _HINDU_LISTING_HTML,
            )
            process_snapshot(snap_path, Path(proc_dir))
            out_file = Path(proc_dir) / "the_hindu_opinion" / "20260501T100000Z.json"
            self.assertTrue(out_file.exists())

    def test_output_file_is_valid_json_list(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as proc_dir:
            snap_path = _write_snapshot(
                Path(raw_dir),
                "the_hindu_opinion",
                "https://www.thehindu.com/opinion/",
                _HINDU_LISTING_HTML,
            )
            process_snapshot(snap_path, Path(proc_dir))
            out_file = Path(proc_dir) / "the_hindu_opinion" / "20260501T100000Z.json"
            data = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertIsInstance(data, list)
            self.assertGreater(len(data), 0)

    def test_skips_unknown_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as proc_dir:
            snap_path = _write_snapshot(
                Path(raw_dir),
                "unknown_source_xyz",
                "https://unknown.example.com/",
                "<html></html>",
            )
            articles = process_snapshot(snap_path, Path(proc_dir))
            self.assertEqual(articles, [])


class RunCleanTests(unittest.TestCase):
    def test_returns_summary_with_no_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as proc_dir:
            result = run_clean(Path(raw_dir), Path(proc_dir))
            self.assertIn("processed", result)
            self.assertIn("errors", result)

    def test_processes_all_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as proc_dir:
            _write_snapshot(
                Path(raw_dir),
                "the_hindu_opinion",
                "https://www.thehindu.com/opinion/",
                _HINDU_LISTING_HTML,
            )
            result = run_clean(Path(raw_dir), Path(proc_dir))
            self.assertEqual(len(result["errors"]), 0)
            self.assertEqual(len(result["processed"]), 1)

    def test_error_collected_without_fail_fast(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as proc_dir:
            # Write a malformed JSON file.
            bad_file = Path(raw_dir) / "bad_source" / "20260501T100000Z.json"
            bad_file.parent.mkdir(parents=True)
            bad_file.write_text("NOT_JSON", encoding="utf-8")
            result = run_clean(Path(raw_dir), Path(proc_dir), fail_fast=False)
            self.assertEqual(len(result["errors"]), 1)

    def test_fail_fast_raises_on_bad_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as proc_dir:
            bad_file = Path(raw_dir) / "bad_source" / "20260501T100000Z.json"
            bad_file.parent.mkdir(parents=True)
            bad_file.write_text("NOT_JSON", encoding="utf-8")
            with self.assertRaises(Exception):
                run_clean(Path(raw_dir), Path(proc_dir), fail_fast=True)


if __name__ == "__main__":
    unittest.main()
