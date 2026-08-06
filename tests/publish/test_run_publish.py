"""Tests for the publish CLI's empty-site health gate.

A run that produces 0 articles must fail loudly rather than silently
overwrite (or leave in place) a deployable ``site/`` directory -- see
SECURITY.md / ARCHITECTURE.md health-gate notes.
"""
import sys
import unittest
from unittest.mock import patch

from scripts.publish import run_publish


class RunPublishEmptySiteGateTests(unittest.TestCase):
    def test_exits_nonzero_when_zero_articles_published(self) -> None:
        with patch("scripts.publish.publisher.Publisher.publish_site", return_value=0):
            with patch.object(sys, "argv", ["run_publish"]):
                with self.assertRaises(SystemExit) as ctx:
                    run_publish.main()
                self.assertNotEqual(ctx.exception.code, 0)

    def test_exits_zero_when_articles_published(self) -> None:
        with patch("scripts.publish.publisher.Publisher.publish_site", return_value=5):
            with patch.object(sys, "argv", ["run_publish"]):
                # main() only calls sys.exit() on failure paths; a normal
                # return means success.
                run_publish.main()


if __name__ == "__main__":
    unittest.main()
