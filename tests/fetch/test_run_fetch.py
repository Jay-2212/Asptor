from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from scripts.fetch import run_fetch


class RunFetchCliTests(unittest.TestCase):
    def test_allow_partial_succeeds_when_one_source_fails(self) -> None:
        result = {"saved": [{"source": "ok"}], "errors": [{"source": "blocked"}]}
        with patch.object(run_fetch, "run_all_sources", return_value=result):
            with patch.object(
                sys, "argv", ["run_fetch", "--allow-partial"]
            ):
                self.assertEqual(run_fetch.main(), 0)

    def test_allow_partial_still_fails_when_all_sources_fail(self) -> None:
        result = {"saved": [], "errors": [{"source": "blocked"}]}
        with patch.object(run_fetch, "run_all_sources", return_value=result):
            with patch.object(
                sys, "argv", ["run_fetch", "--allow-partial"]
            ):
                self.assertEqual(run_fetch.main(), 1)

    def test_default_mode_fails_on_partial_source_failure(self) -> None:
        result = {"saved": [{"source": "ok"}], "errors": [{"source": "blocked"}]}
        with patch.object(run_fetch, "run_all_sources", return_value=result):
            with patch.object(sys, "argv", ["run_fetch"]):
                self.assertEqual(run_fetch.main(), 1)


if __name__ == "__main__":
    unittest.main()
