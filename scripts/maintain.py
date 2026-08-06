"""Local maintainer CLI for Asptor: runs the pipeline and audits quality.

This mirrors the steps GitHub Actions runs on schedule, for local
development and debugging. Every step is invoked as an explicit argument
list (never ``shell=True``) so nothing in source configuration, filenames,
or generated data can be interpreted as shell syntax.

Use ``--dry-run`` to print the commands that would run without touching the
network or the filesystem.
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.report.health import audit_processed_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Maintainer")

REPO_ROOT = Path(__file__).resolve().parent.parent

PIPELINE_STEPS: list[list[str]] = [
    [sys.executable, "-m", "scripts.fetch.run_fetch", "--raw-root", "data/raw", "--allow-partial"],
    [sys.executable, "-m", "scripts.clean.run_clean", "--raw-root", "data/raw", "--processed-root", "data/processed", "--allow-partial"],
    [sys.executable, "-m", "scripts.diff.run_diff", "--processed-root", "data/processed", "--state-root", "data/state", "--diff-root", "data/diff"],
    [sys.executable, "-m", "scripts.clean.run_full_clean", "--processed-root", "data/processed", "--diff-root", "data/diff", "--limit", "10"],
    [sys.executable, "-m", "scripts.publish.run_publish", "--processed-root", "data/processed", "--site-root", "site"],
]


def run_command(command: list[str], *, cwd: Path) -> bool:
    """Run *command* as an explicit argument list in *cwd*. No shell involved."""
    if not cwd.is_dir():
        logger.error("Refusing to run command: working directory %r does not exist.", cwd.name)
        return False

    logger.info("Executing: %s", " ".join(command))
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, shell=False)
    if result.returncode != 0:
        logger.error("Command failed with exit code %d", result.returncode)
        if result.stderr:
            logger.error(result.stderr.strip())
        return False
    return True


def write_report(stats: dict, *, dry_run: bool) -> Path:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Asptor Maintenance Report",
        "",
        f"**Run Timestamp (UTC):** {generated_at}",
        "",
        "## Statistics",
        f"- **Total Articles Discovered:** {stats['total_articles']}",
        f"- **Empty/Short Content:** {stats['empty_or_short_content']}",
        f"- **Missing Hero Images:** {stats['missing_hero_images']}",
        f"- **Possible Duplicate Titles:** {stats['possible_duplicate_titles']}",
        f"- **Malformed Files:** {stats['malformed_files']}",
        "",
        "## Status",
    ]
    if dry_run:
        lines.append("Dry run only — no pipeline steps were executed; statistics reflect existing local data.")
    elif stats["total_articles"] and stats["empty_or_short_content"] > stats["total_articles"] * 0.5:
        lines.append("⚠️ **Warning:** More than 50% of articles have empty content. Check cleaners.")
    else:
        lines.append("✅ **System Healthy:** Pipeline is functioning within expected parameters.")

    report_path = REPO_ROOT / "MAINTENANCE_REPORT.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Asptor pipeline locally and audit output quality.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the pipeline commands and report on existing data without fetching or writing.",
    )
    args = parser.parse_args()

    logger.info("Starting Asptor Maintenance Run%s...", " (dry-run)" if args.dry_run else "")

    if args.dry_run:
        for step in PIPELINE_STEPS:
            logger.info("[dry-run] Would execute: %s", " ".join(step))
    else:
        for step in PIPELINE_STEPS:
            if not run_command(step, cwd=REPO_ROOT):
                logger.error("Pipeline interrupted due to error.")
                break

    stats = audit_processed_data(REPO_ROOT / "data" / "processed")
    logger.info(
        "Audit Summary: total=%d empty_or_short=%d missing_images=%d duplicate_titles=%d",
        stats["total_articles"],
        stats["empty_or_short_content"],
        stats["missing_hero_images"],
        stats["possible_duplicate_titles"],
    )

    report_path = write_report(stats, dry_run=args.dry_run)
    logger.info("Maintenance complete. Report saved to %s", report_path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
