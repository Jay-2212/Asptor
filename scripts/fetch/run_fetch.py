from __future__ import annotations

import argparse
import json
from pathlib import Path

from .fetcher import run_all_sources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch configured source pages and persist raw snapshots."
    )
    parser.add_argument(
        "--raw-root",
        default="data/raw",
        help="Directory where raw source snapshots are stored.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Max fetch attempts per source before marking as failed.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=20,
        help="Network timeout for each individual request.",
    )
    parser.add_argument(
        "--backoff-seconds",
        type=float,
        default=1.0,
        help="Initial backoff delay between retries (exponential).",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop immediately if any source fetch fails.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    results = run_all_sources(
        raw_root=Path(args.raw_root),
        max_attempts=args.max_attempts,
        timeout_seconds=args.timeout_seconds,
        backoff_seconds=args.backoff_seconds,
        fail_fast=args.fail_fast,
    )
    print(json.dumps(results, indent=2))
    return 1 if results["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
