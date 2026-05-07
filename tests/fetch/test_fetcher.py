from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.fetch.fetcher import (
    FetchError,
    fetch_with_retries,
    run_all_sources,
    save_raw_snapshot,
)
from scripts.fetch.sources import SourceConfig


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        return None


class FetcherTests(unittest.TestCase):
    def test_fetch_with_retries_retries_then_succeeds(self) -> None:
        calls: list[float] = []
        side_effects = [RuntimeError("temporary"), FakeResponse(b"ok")]

        with patch("scripts.fetch.fetcher.urlopen", side_effect=side_effects):
            body = fetch_with_retries(
                url="https://example.com",
                max_attempts=2,
                backoff_seconds=0.5,
                sleeper=calls.append,
            )

        self.assertEqual(body, "ok")
        self.assertEqual(calls, [0.5])

    def test_fetch_with_retries_raises_after_max_attempts(self) -> None:
        delays: list[float] = []
        with patch("scripts.fetch.fetcher.urlopen", side_effect=RuntimeError("boom")):
            with self.assertRaises(FetchError) as ctx:
                fetch_with_retries(
                    url="https://example.com",
                    max_attempts=3,
                    backoff_seconds=0.25,
                    sleeper=delays.append,
                )

        self.assertIn("Failed to fetch", str(ctx.exception))
        self.assertEqual(delays, [0.25, 0.5])

    def test_save_raw_snapshot_writes_expected_payload(self) -> None:
        source = SourceConfig(name="Example Source", url="https://example.com")
        fetched_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as tmp_dir:
            output = save_raw_snapshot(
                raw_root=Path(tmp_dir),
                source=source,
                content="<html>sample</html>",
                fetched_at=fetched_at,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(output.name, "20260102T030405Z.json")
        self.assertEqual(payload["source"]["name"], "Example Source")
        self.assertEqual(payload["fetched_at"], "2026-01-02T03:04:05Z")
        self.assertEqual(payload["content_html"], "<html>sample</html>")

    def test_run_all_sources_collects_errors_without_fail_fast(self) -> None:
        sources = (
            SourceConfig(name="ok_source", url="https://ok.example"),
            SourceConfig(name="bad_source", url="https://bad.example"),
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch(
                "scripts.fetch.fetcher.run_source_fetch",
                side_effect=[
                    Path(tmp_dir) / "ok.json",
                    RuntimeError("network down"),
                ],
            ):
                result = run_all_sources(
                    raw_root=Path(tmp_dir), sources=sources, fail_fast=False
                )

        self.assertEqual(len(result["saved"]), 1)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0]["source"], "bad_source")

    def test_run_all_sources_respects_fail_fast(self) -> None:
        sources = (SourceConfig(name="bad_source", url="https://bad.example"),)
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch(
                "scripts.fetch.fetcher.run_source_fetch",
                side_effect=RuntimeError("network down"),
            ):
                with self.assertRaises(RuntimeError):
                    run_all_sources(
                        raw_root=Path(tmp_dir), sources=sources, fail_fast=True
                    )


if __name__ == "__main__":
    unittest.main()
