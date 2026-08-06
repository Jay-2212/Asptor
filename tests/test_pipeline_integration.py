"""End-to-end fixture tests: fetch output -> clean -> diff -> publish.

These exercise the real clean/diff/publish layers together (not mocked) to
verify the property the task cares about most: partial upstream failure
must never silently become an empty or misleading deployment, and a total
failure must be loud rather than silently publishing nothing.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.clean.run_clean import run_clean
from scripts.diff.run_diff import diff_all_sources
from scripts.publish.publisher import Publisher

_HINDU_HTML = """
<html><body>
  <article>
    <a href="/opinion/editorial/first-story/">
      First Real Story About Governance Reform
    </a>
    <time datetime="2026-05-01T10:00:00Z"></time>
  </article>
  <article>
    <a href="/opinion/editorial/unicode-story/">
      दुनिया 世界 की कहानी: A Story About the World 🌍
    </a>
  </article>
  <article>
    <a href="/opinion/editorial/bad-date-story/">
      Story With A Malformed Publish Date Field
    </a>
    <time datetime="not-a-real-date"></time>
  </article>
  <article>
    <a href="/opinion/editorial/no-date-story/">
      Story That Has No Publish Date At All
    </a>
  </article>
</body></html>
"""


def _write_snapshot(raw_root: Path, source_name: str, source_url: str, html: str, timestamp: str) -> None:
    snapshot = {
        "source": {"name": source_name, "url": source_url},
        "fetched_at": "2026-05-01T10:00:00Z",
        "content_html": html,
    }
    out_file = raw_root / source_name / f"{timestamp}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(snapshot), encoding="utf-8")


class PipelinePartialFailureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        root = Path(self.tmp.name)
        self.raw_root = root / "raw"
        self.processed_root = root / "processed"
        self.state_root = root / "state"
        self.diff_root = root / "diff"
        self.site_root = root / "site"

    def tearDown(self):
        self.tmp.cleanup()

    def test_one_malformed_snapshot_does_not_block_healthy_source(self):
        """A malformed raw file for one source must not prevent a healthy
        source's articles from reaching the published site."""
        _write_snapshot(
            self.raw_root, "the_hindu_opinion", "https://www.thehindu.com/opinion/",
            _HINDU_HTML, "20260501T100000Z",
        )
        bad_file = self.raw_root / "the_hindu_national" / "20260501T100000Z.json"
        bad_file.parent.mkdir(parents=True)
        bad_file.write_text("NOT VALID JSON {{{", encoding="utf-8")

        clean_result = run_clean(self.raw_root, self.processed_root, fail_fast=False)
        self.assertEqual(len(clean_result["errors"]), 1)
        self.assertGreater(len(clean_result["processed"]), 0)

        diff_all_sources(
            processed_root=self.processed_root,
            state_root=self.state_root,
            diff_root=self.diff_root,
        )

        publisher = Publisher(self.processed_root, self.site_root)
        count = publisher.publish_site()

        self.assertGreater(count, 0, "healthy source must still publish despite the other source's malformed snapshot")
        index_html = (self.site_root / "index.html").read_text(encoding="utf-8")
        self.assertIn("content/", index_html)

    def test_all_sources_failing_produces_zero_published_articles(self):
        """No raw snapshots at all (total upstream failure) must result in
        an empty publish count, which is the signal run_publish uses to
        refuse to deploy."""
        self.raw_root.mkdir(parents=True)
        run_clean(self.raw_root, self.processed_root, fail_fast=False)

        publisher = Publisher(self.processed_root, self.site_root)
        count = publisher.publish_site()
        self.assertEqual(count, 0)

    def test_unicode_titles_survive_the_full_pipeline(self):
        _write_snapshot(
            self.raw_root, "the_hindu_opinion", "https://www.thehindu.com/opinion/",
            _HINDU_HTML, "20260501T100000Z",
        )
        run_clean(self.raw_root, self.processed_root, fail_fast=False)
        publisher = Publisher(self.processed_root, self.site_root)
        publisher.publish_site()

        index_html = (self.site_root / "index.html").read_text(encoding="utf-8")
        self.assertIn("दुनिया 世界 की कहानी", index_html)

    def test_missing_and_malformed_dates_do_not_crash_pipeline(self):
        _write_snapshot(
            self.raw_root, "the_hindu_opinion", "https://www.thehindu.com/opinion/",
            _HINDU_HTML, "20260501T100000Z",
        )
        clean_result = run_clean(self.raw_root, self.processed_root, fail_fast=False)
        self.assertEqual(len(clean_result["errors"]), 0)

        publisher = Publisher(self.processed_root, self.site_root)
        count = publisher.publish_site()
        self.assertGreaterEqual(count, 4)
        self.assertTrue((self.site_root / "index.html").exists())

    def test_republishing_identical_snapshot_is_idempotent(self):
        """Running clean/diff/publish twice on the same raw snapshot should
        not duplicate articles or change the published count."""
        _write_snapshot(
            self.raw_root, "the_hindu_opinion", "https://www.thehindu.com/opinion/",
            _HINDU_HTML, "20260501T100000Z",
        )
        run_clean(self.raw_root, self.processed_root, fail_fast=False)
        diff_all_sources(processed_root=self.processed_root, state_root=self.state_root, diff_root=self.diff_root)
        publisher = Publisher(self.processed_root, self.site_root)
        first_count = publisher.publish_site()

        # Second run with the same source content (e.g. next scheduled fetch
        # rediscovers the same listing page, same URLs/titles).
        _write_snapshot(
            self.raw_root, "the_hindu_opinion", "https://www.thehindu.com/opinion/",
            _HINDU_HTML, "20260501T140000Z",
        )
        run_clean(self.raw_root, self.processed_root, fail_fast=False)
        second_diff = diff_all_sources(processed_root=self.processed_root, state_root=self.state_root, diff_root=self.diff_root)
        second_count = Publisher(self.processed_root, self.site_root).publish_site()

        self.assertEqual(first_count, second_count)
        # No new articles should have been diffed on the second identical run.
        total_new = sum(entry["new_articles"] for entry in second_diff["diffed"])
        self.assertEqual(total_new, 0)


if __name__ == "__main__":
    unittest.main()
