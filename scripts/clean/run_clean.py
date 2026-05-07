"""CLI for processing raw snapshots → normalised Article records.

Usage::

    python -m scripts.clean.run_clean \\
        --raw-root data/raw \\
        --processed-root data/processed

For each ``*.json`` file found recursively under *raw_root*, the script:

1. Reads the snapshot and determines the source name.
2. Looks up the registered cleaner for that source.
3. Parses the HTML and produces Article records.
4. Writes the normalised records to
   ``<processed_root>/<source_name>/<timestamp>.json``.

Unknown sources are skipped with a warning rather than aborting the run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .registry import CLEANERS, get_cleaner
from .schema import Article


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------


def process_snapshot(snapshot_path: Path, processed_root: Path) -> list[Article]:
    """Read *snapshot_path*, clean it, and write output.  Return Articles."""
    raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
    source_name: str = raw.get("source", {}).get("name", "")

    try:
        cleaner = get_cleaner(source_name)
    except KeyError as exc:
        print(f"[SKIP] {exc}", file=sys.stderr)
        return []

    articles = cleaner.clean_snapshot(raw)
    if not articles:
        return []

    # Derive output filename from input filename (same timestamp stem).
    out_dir = processed_root / source_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / snapshot_path.name

    payload = [a.to_dict() for a in articles]
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return articles


def run_clean(
    raw_root: Path,
    processed_root: Path,
    *,
    fail_fast: bool = False,
) -> dict[str, list[dict]]:
    """Process all raw snapshots under *raw_root*.

    Returns a summary dict::

        {
            "processed": [{"snapshot": "...", "articles": N}, ...],
            "errors":    [{"snapshot": "...", "error":    "..."}, ...],
        }
    """
    results: dict[str, list[dict]] = {"processed": [], "errors": []}

    snapshot_files = sorted(raw_root.rglob("*.json"))
    if not snapshot_files:
        print("[INFO] No raw snapshots found.", file=sys.stderr)
        return results

    for snap in snapshot_files:
        try:
            articles = process_snapshot(snap, processed_root)
            results["processed"].append(
                {"snapshot": str(snap), "articles": len(articles)}
            )
        except Exception as exc:  # noqa: BLE001
            results["errors"].append({"snapshot": str(snap), "error": str(exc)})
            print(f"[ERROR] {snap}: {exc}", file=sys.stderr)
            if fail_fast:
                raise

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clean and normalise raw source snapshots into Article records."
    )
    parser.add_argument(
        "--raw-root",
        default="data/raw",
        help="Directory that contains raw source snapshot JSON files.",
    )
    parser.add_argument(
        "--processed-root",
        default="data/processed",
        help="Directory where normalised Article JSON files are written.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop immediately if any snapshot fails to process.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    results = run_clean(
        raw_root=Path(args.raw_root),
        processed_root=Path(args.processed_root),
        fail_fast=args.fail_fast,
    )
    print(json.dumps(results, indent=2))
    return 1 if results["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
