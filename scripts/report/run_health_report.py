"""CLI: generate the per-run health/report artifact.

Usage::

    python -m scripts.report.run_health_report \\
        --processed-root data/processed \\
        --out data/health_report.json

This is a reporting step only -- it never fails the pipeline by itself.
Empty-site protection is enforced by ``scripts.publish.run_publish`` (which
exits non-zero when 0 articles are published); this report exists so that
partial degradation (stale sources, short/duplicate content) is visible
without being fatal.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .health import audit_processed_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a health/report artifact summarising processed article quality."
    )
    parser.add_argument(
        "--processed-root",
        default="data/processed",
        help="Directory containing per-source processed Article JSON files.",
    )
    parser.add_argument(
        "--out",
        default="data/health_report.json",
        help="Path to write the JSON health report to.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    stats = audit_processed_data(Path(args.processed_root))
    stats["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
