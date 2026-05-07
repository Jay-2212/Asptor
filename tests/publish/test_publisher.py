"""Tests for the publishing pipeline."""
import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.clean.schema import Article
from scripts.publish.publisher import Publisher


class TestPublisher(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.processed_root = Path(self.tmp_dir.name) / "processed"
        self.site_root = Path(self.tmp_dir.name) / "site"
        self.processed_root.mkdir()
        self.site_root.mkdir()

        # Create a dummy article
        self.article1 = Article(
            source="the_hindu",
            source_id="id1",
            url="http://example.com/1",
            title="Title 1",
            subtitle="Subtitle 1",
            author="Author 1",
            published_at="2026-05-07T12:00:00Z",
            image_url=None,
            content_html="<p>Body 1</p>",
            content_text="Body 1",
            fetched_at="2026-05-07T13:00:00Z",
            hash="hash1"
        )
        
        # Create another dummy article for same hash (newer)
        self.article1_newer = Article(
            source="the_hindu",
            source_id="id1",
            url="http://example.com/1",
            title="Title 1 Updated",
            subtitle="Subtitle 1",
            author="Author 1",
            published_at="2026-05-07T12:00:00Z",
            image_url=None,
            content_html="<p>Body 1 Updated</p>",
            content_text="Body 1 Updated",
            fetched_at="2026-05-07T14:00:00Z",
            hash="hash1"
        )

        self.article2 = Article(
            source="the_caravan",
            source_id="id2",
            url="http://example.com/2",
            title="Title 2",
            subtitle=None,
            author=None,
            published_at="2026-05-07T11:00:00Z",
            image_url=None,
            content_html="",
            content_text="",
            fetched_at="2026-05-07T13:00:00Z",
            hash="hash2"
        )

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _write_articles(self, source: str, filename: str, articles: list[Article]):
        source_dir = self.processed_root / source
        source_dir.mkdir(parents=True, exist_ok=True)
        with open(source_dir / filename, "w") as f:
            json.dump([a.to_dict() for a in articles], f)

    def test_load_all_articles_deduplication(self):
        self._write_articles("the_hindu", "file1.json", [self.article1])
        self._write_articles("the_hindu", "file2.json", [self.article1_newer])
        self._write_articles("the_caravan", "file1.json", [self.article2])

        publisher = Publisher(self.processed_root, self.site_root)
        articles = publisher.load_all_articles()

        self.assertEqual(len(articles), 2)
        # Should have article1_newer because fetched_at is later
        hashes = {a.hash: a for a in articles}
        self.assertEqual(hashes["hash1"].title, "Title 1 Updated")
        self.assertEqual(hashes["hash2"].title, "Title 2")

    def test_load_all_articles_sorting(self):
        self._write_articles("the_hindu", "file1.json", [self.article1])
        self._write_articles("the_caravan", "file1.json", [self.article2])

        publisher = Publisher(self.processed_root, self.site_root)
        articles = publisher.load_all_articles()

        # article1: 12:00, article2: 11:00 -> article1 should be first (descending)
        self.assertEqual(articles[0].hash, "hash1")
        self.assertEqual(articles[1].hash, "hash2")

    def test_publish_site_generates_files(self):
        self._write_articles("the_hindu", "file1.json", [self.article1])
        
        publisher = Publisher(self.processed_root, self.site_root)
        count = publisher.publish_site()

        self.assertEqual(count, 1)
        self.assertTrue((self.site_root / "index.html").exists())
        self.assertTrue((self.site_root / "content" / "hash1.html").exists())

        with open(self.site_root / "index.html", "r") as f:
            content = f.read()
            self.assertIn("Title 1", content)
            self.assertIn("content/hash1.html", content)

        with open(self.site_root / "content" / "hash1.html", "r") as f:
            content = f.read()
            self.assertIn("Title 1", content)
            self.assertIn("Body 1", content)

    def test_publish_article_page_handles_missing_content(self):
        # article2 has empty content_html and content_text
        publisher = Publisher(self.processed_root, self.site_root)
        publisher.ensure_dirs()
        publisher.publish_article_page(self.article2, "2026-05-07")
        
        with open(self.site_root / "content" / "hash2.html", "r") as f:
            content = f.read()
            self.assertIn("Title 2", content)
            self.assertIn("Content currently unavailable", content)

    def test_publish_article_page_handles_missing_html_but_has_text(self):
        article_text_only = Article(
            source="the_hindu",
            source_id="id3",
            url="http://example.com/3",
            title="Title 3",
            subtitle=None,
            author=None,
            published_at=None,
            image_url=None,
            content_html="",
            content_text="Paragraph 1\n\nParagraph 2",
            fetched_at="2026-05-07T13:00:00Z",
            hash="hash3"
        )
        publisher = Publisher(self.processed_root, self.site_root)
        publisher.ensure_dirs()
        publisher.publish_article_page(article_text_only, "2026-05-07")
        
        with open(self.site_root / "content" / "hash3.html", "r") as f:
            content = f.read()
            self.assertIn("<p>Paragraph 1</p><p>Paragraph 2</p>", content)
