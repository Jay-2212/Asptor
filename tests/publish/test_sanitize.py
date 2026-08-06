"""Tests for output-boundary HTML sanitization."""
import unittest

from scripts.publish.sanitize import escape_text, is_safe_url, safe_url, sanitize_content_html


class EscapeTextTests(unittest.TestCase):
    def test_escapes_angle_brackets_and_quotes(self):
        self.assertEqual(
            escape_text('<script>alert("x")</script>'),
            "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;",
        )

    def test_none_becomes_empty_string(self):
        self.assertEqual(escape_text(None), "")

    def test_plain_text_unchanged(self):
        self.assertEqual(escape_text("Title 1"), "Title 1")

    def test_preserves_unicode(self):
        self.assertEqual(escape_text("दुनिया 世界 🌍"), "दुनिया 世界 🌍")


class SafeUrlTests(unittest.TestCase):
    def test_rejects_javascript_scheme(self):
        self.assertFalse(is_safe_url("javascript:alert(1)"))
        self.assertEqual(safe_url("javascript:alert(1)"), "")

    def test_rejects_data_scheme(self):
        self.assertFalse(is_safe_url("data:text/html,<script>alert(1)</script>"))

    def test_accepts_https(self):
        self.assertTrue(is_safe_url("https://example.com/a.jpg"))
        self.assertEqual(safe_url("https://example.com/a.jpg"), "https://example.com/a.jpg")

    def test_accepts_http(self):
        self.assertTrue(is_safe_url("http://example.com/a.jpg"))

    def test_accepts_mailto_and_tel(self):
        # Inert schemes commonly used by "share this article" widgets;
        # they open a client, never execute anything.
        self.assertTrue(is_safe_url("mailto:someone@example.com?subject=hi"))
        self.assertTrue(is_safe_url("tel:+1234567890"))

    def test_accepts_root_relative(self):
        self.assertTrue(is_safe_url("/images/a.jpg"))

    def test_accepts_fragment_only_urls(self):
        # e.g. The Hindu's live-blog in-page anchors: <a href="#424441">
        self.assertTrue(is_safe_url("#424441"))
        self.assertEqual(safe_url("#424441"), "#424441")

    def test_rejects_empty_and_none(self):
        self.assertFalse(is_safe_url(""))
        self.assertFalse(is_safe_url(None))
        self.assertEqual(safe_url(None, default="fallback"), "fallback")

    def test_escapes_quotes_in_otherwise_safe_url(self):
        # A malformed but scheme-safe URL should still be attribute-escaped.
        self.assertEqual(
            safe_url('https://example.com/"><script>x</script>'),
            "https://example.com/&quot;&gt;&lt;script&gt;x&lt;/script&gt;",
        )


class SanitizeContentHtmlTests(unittest.TestCase):
    def test_removes_script_tag(self):
        result = sanitize_content_html("<p>Hello</p><script>alert(1)</script>")
        self.assertNotIn("<script", result)
        self.assertIn("Hello", result)

    def test_removes_event_handler_attributes(self):
        result = sanitize_content_html('<p onclick="alert(1)">Hi</p>')
        self.assertNotIn("onclick", result)
        self.assertIn("Hi", result)

    def test_removes_javascript_href(self):
        result = sanitize_content_html('<a href="javascript:alert(1)">click</a>')
        self.assertNotIn("javascript:", result)
        self.assertIn("click", result)

    def test_keeps_safe_http_href(self):
        result = sanitize_content_html('<a href="https://example.com">link</a>')
        self.assertIn('href="https://example.com"', result)

    def test_keeps_fragment_only_href(self):
        result = sanitize_content_html('<a href="#424441">jump</a>')
        self.assertIn('href="#424441"', result)

    def test_removes_object_and_embed_and_iframe(self):
        result = sanitize_content_html(
            '<p>Body</p><object data="x"></object><embed src="y"><iframe src="z"></iframe>'
        )
        self.assertNotIn("<object", result)
        self.assertNotIn("<embed", result)
        self.assertNotIn("<iframe", result)

    def test_removes_unsafe_img_src(self):
        result = sanitize_content_html('<img src="javascript:alert(1)">')
        self.assertNotIn("javascript:", result)

    def test_keeps_safe_img_src(self):
        result = sanitize_content_html('<img src="https://example.com/a.jpg">')
        self.assertIn("https://example.com/a.jpg", result)

    def test_empty_input_returns_empty_string(self):
        self.assertEqual(sanitize_content_html(""), "")

    def test_preserves_paragraph_structure(self):
        result = sanitize_content_html("<p>One</p><p>Two</p>")
        self.assertEqual(result.count("<p>"), 2)

    def test_handles_svg_with_embedded_script(self):
        result = sanitize_content_html('<svg onload="alert(1)"><script>alert(2)</script></svg>')
        self.assertNotIn("onload", result)
        self.assertNotIn("<script", result)
        self.assertNotIn("<svg", result)

    def test_preserves_unicode_text(self):
        result = sanitize_content_html("<p>दुनिया 世界 🌍</p>")
        self.assertIn("दुनिया 世界 🌍", result)


if __name__ == "__main__":
    unittest.main()
