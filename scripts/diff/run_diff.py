"""CLI for running the diff / dedup layer.

Usage::

    python -m scripts.diff.run_diff \\
        --processed-root data/processed \\
        --state-root     data/state \\
        --diff-root      data/diff

For every source subdirectory found under *processed_root* the script:

1. Loads all Article records produced by the clean layer.
2. Compares them against the persistent state of previously-seen hashes.
3. Writes only **new** articles to ``<diff_root>/<source>/<timestamp>.json``.
4. Updates ``<state_root>/<source>/seen_hashes.json`` so the same articles
   are not emitted again on the next run.

Exit code is 0 on success, 1 if any source encountered an error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .differ import diff_all_sources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Emit only newly discovered articles relative to stored state."
    )
    parser.add_argument(
        "--processed-root",
        default="data/processed",
        help="Root directory containing per-source processed Article JSON files.",
    )
    parser.add_argument(
        "--state-root",
        default="data/state",
        help="Root directory for persistent seen-hash state files.",
    )
    parser.add_argument(
        "--diff-root",
        default="data/diff",
        help="Root directory where new-article diff files are written.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Abort immediately if any source raises an error.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    results = diff_all_sources(
        processed_root=Path(args.processed_root),
        state_root=Path(args.state_root),
        diff_root=Path(args.diff_root),
        fail_fast=args.fail_fast,
    )
    print(json.dumps(results, indent=2))
    return 1 if results["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
