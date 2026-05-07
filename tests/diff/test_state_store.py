"""Unit tests for scripts/diff/state_store.py."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.diff.state_store import load_seen_hashes, save_seen_hashes


class LoadSeenHashesTests(unittest.TestCase):
    def test_returns_empty_set_when_no_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = load_seen_hashes(Path(tmp), "some_source")
            self.assertEqual(result, set())

    def test_loads_hashes_from_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "my_source"
            state_dir.mkdir()
            (state_dir / "seen_hashes.json").write_text(
                json.dumps(["aabbccdd00112233", "ffee998877665544"]), encoding="utf-8"
            )
            result = load_seen_hashes(root, "my_source")
            self.assertEqual(result, {"aabbccdd00112233", "ffee998877665544"})

    def test_raises_on_malformed_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_dir = root / "bad_source"
            state_dir.mkdir()
            (state_dir / "seen_hashes.json").write_text(
                json.dumps({"hashes": ["abc"]}), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                load_seen_hashes(root, "bad_source")


class SaveSeenHashesTests(unittest.TestCase):
    def test_creates_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_seen_hashes(root, "src", {"aabbccdd00112233"})
            path = root / "src" / "seen_hashes.json"
            self.assertTrue(path.exists())
            data = json.loads(path.read_text())
            self.assertIn("aabbccdd00112233", data)

    def test_creates_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "does" / "not" / "exist"
            save_seen_hashes(root, "src", {"hash1"})
            self.assertTrue((root / "src" / "seen_hashes.json").exists())

    def test_merges_with_existing_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_seen_hashes(root, "src", {"hash_a", "hash_b"})
            save_seen_hashes(root, "src", {"hash_c"})
            result = load_seen_hashes(root, "src")
            self.assertEqual(result, {"hash_a", "hash_b", "hash_c"})

    def test_idempotent_on_same_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_seen_hashes(root, "src", {"hash_x"})
            save_seen_hashes(root, "src", {"hash_x"})
            result = load_seen_hashes(root, "src")
            self.assertEqual(result, {"hash_x"})

    def test_returns_path_of_written_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = save_seen_hashes(root, "src", {"h1"})
            self.assertIsInstance(path, Path)
            self.assertTrue(path.exists())

    def test_output_is_sorted_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_seen_hashes(root, "src", {"zzz", "aaa", "mmm"})
            data = json.loads((root / "src" / "seen_hashes.json").read_text())
            self.assertEqual(data, sorted(data))

    def test_empty_set_saves_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_seen_hashes(root, "src", set())
            result = load_seen_hashes(root, "src")
            self.assertEqual(result, set())


if __name__ == "__main__":
    unittest.main()
