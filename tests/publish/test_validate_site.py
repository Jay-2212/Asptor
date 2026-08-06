"""Tests for the pre-commit site validation gate."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.publish.validate_site import validate_site


class ValidateSiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.site_root = Path(self.tmp.name) / "site"

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_index_is_invalid(self):
        self.site_root.mkdir()
        problems = validate_site(self.site_root)
        self.assertTrue(any("does not exist" in p for p in problems))

    def test_empty_index_is_invalid(self):
        self.site_root.mkdir()
        (self.site_root / "index.html").write_text("", encoding="utf-8")
        problems = validate_site(self.site_root)
        self.assertTrue(any("empty" in p for p in problems))

    def test_index_with_no_article_links_is_invalid(self):
        self.site_root.mkdir()
        (self.site_root / "index.html").write_text("<html><body>No articles</body></html>", encoding="utf-8")
        problems = validate_site(self.site_root)
        self.assertTrue(any("no links to article pages" in p for p in problems))

    def test_index_linking_missing_article_page_is_invalid(self):
        self.site_root.mkdir()
        (self.site_root / "index.html").write_text(
            '<html><body><a href="content/abcdef0123456789.html">A</a></body></html>',
            encoding="utf-8",
        )
        problems = validate_site(self.site_root)
        self.assertTrue(any("do not exist on disk" in p for p in problems))

    def test_valid_site_passes(self):
        self.site_root.mkdir()
        (self.site_root / "content").mkdir()
        (self.site_root / "content" / "abcdef0123456789.html").write_text("<html></html>", encoding="utf-8")
        (self.site_root / "index.html").write_text(
            '<html><body><a href="content/abcdef0123456789.html">A</a></body></html>',
            encoding="utf-8",
        )
        problems = validate_site(self.site_root)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
