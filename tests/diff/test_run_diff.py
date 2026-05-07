"""Unit tests for scripts/diff/run_diff.py (CLI integration)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.diff.run_diff import main


def _article_dict(hash_: str, url: str = "https://example.com/a/") -> dict:
    return {
        "source": "test_source",
        "source_id": hash_,
        "url": url,
        "title": "A Long Enough Article Title",
        "subtitle": None,
        "author": None,
        "published_at": None,
        "image_url": None,
        "content_html": "",
        "content_text": "",
        "fetched_at": "2026-05-07T12:00:00Z",
        "hash": hash_,
    }


def _write_processed(root: Path, source: str, articles: list[dict]) -> None:
    out_dir = root / source
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "20260507T120000Z.json").write_text(
        json.dumps(articles, indent=2), encoding="utf-8"
    )


class RunDiffMainTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, extra_args: list[str] | None = None) -> int:
        args = [
            "--processed-root", str(self.tmp / "processed"),
            "--state-root",     str(self.tmp / "state"),
            "--diff-root",      str(self.tmp / "diff"),
        ] + (extra_args or [])
        with patch("sys.argv", ["run_diff"] + args):
            return main()

    def test_exit_code_0_on_success(self) -> None:
        _write_processed(
            self.tmp / "processed",
            "test_source",
            [_article_dict("hAAA")],
        )
        rc = self._run()
        self.assertEqual(rc, 0)

    def test_exit_code_0_when_no_processed_root(self) -> None:
        rc = self._run()
        self.assertEqual(rc, 0)

    def test_diff_file_written(self) -> None:
        _write_processed(
            self.tmp / "processed",
            "test_source",
            [_article_dict("hBBB")],
        )
        self._run()
        diff_files = list((self.tmp / "diff" / "test_source").glob("*.json"))
        self.assertEqual(len(diff_files), 1)
        data = json.loads(diff_files[0].read_text())
        self.assertEqual(data[0]["hash"], "hBBB")

    def test_exit_code_1_on_error(self) -> None:
        bad_dir = self.tmp / "processed" / "bad_source"
        bad_dir.mkdir(parents=True)
        (bad_dir / "broken.json").write_text("not valid json", encoding="utf-8")
        rc = self._run()
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
