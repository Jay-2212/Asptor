"""Persistent store for seen article hashes.

State is kept in ``data/state/<source_name>/seen_hashes.json``, which holds
a JSON array of 16-hex hash strings.  The state file grows monotonically:
hashes are only ever added, never removed.
"""
from __future__ import annotations

import json
from pathlib import Path


def _state_path(state_root: Path, source_name: str) -> Path:
    return state_root / source_name / "seen_hashes.json"


def load_seen_hashes(state_root: Path, source_name: str) -> set[str]:
    """Return the set of hashes already seen for *source_name*.

    Returns an empty set if no state file exists yet.
    """
    path = _state_path(state_root, source_name)
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(
            f"State file {path} has unexpected format (expected a JSON list)."
        )
    return set(data)


def save_seen_hashes(
    state_root: Path,
    source_name: str,
    hashes: set[str],
) -> Path:
    """Persist *hashes* to the state file for *source_name*.

    Merges with any existing hashes so that the state file is always a
    complete record of everything that has ever been seen.

    Returns the path of the written state file.
    """
    path = _state_path(state_root, source_name)
    existing = load_seen_hashes(state_root, source_name)
    merged = sorted(existing | hashes)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return path
