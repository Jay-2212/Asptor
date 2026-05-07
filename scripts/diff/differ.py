"""Core diff logic: compare latest processed articles against stored state.

For each source the differ:

1. Loads all ``*.json`` files from ``<processed_root>/<source_name>/`` and
   collects every Article record.
2. Loads the set of previously-seen hashes from
   ``<state_root>/<source_name>/seen_hashes.json``.
3. Filters to articles whose ``hash`` has **not** been seen before.
4. Writes those new articles to
   ``<diff_root>/<source_name>/<timestamp>.json``.
5. Updates the state file so the same articles are not emitted again on the
   next run.

The timestamp used for output filenames is derived from the most recent
``fetched_at`` value among the new articles, falling back to the current UTC
time if no articles are new.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.clean.schema import Article

from .state_store import load_seen_hashes, save_seen_hashes


def _utc_now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_articles_from_dir(processed_dir: Path) -> list[Article]:
    """Load all Article records from ``<processed_dir>/*.json`` files."""
    articles: list[Article] = []
    for path in sorted(processed_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            for item in data:
                articles.append(Article.from_dict(item))
    return articles


def diff_source(
    *,
    source_name: str,
    processed_root: Path,
    state_root: Path,
    diff_root: Path,
    timestamp: str | None = None,
) -> list[Article]:
    """Compute new articles for *source_name* and persist the diff output.

    Parameters
    ----------
    source_name:
        The normalised source identifier, e.g. ``"the_hindu_opinion"``.
    processed_root:
        Root directory that contains per-source subdirectories of processed
        Article JSON files (output of the clean layer).
    state_root:
        Root directory for persistent hash-state files.
    diff_root:
        Root directory where diff output files are written.
    timestamp:
        Optional ISO-8601-compact stamp (``YYYYMMDDTHHMMSSz``) used as the
        output filename stem.  Defaults to the current UTC time.

    Returns
    -------
    list[Article]
        The articles that are new (i.e. not previously seen).
    """
    processed_dir = processed_root / source_name
    if not processed_dir.is_dir():
        print(
            f"[SKIP] No processed directory for source '{source_name}': "
            f"{processed_dir}",
            file=sys.stderr,
        )
        return []

    all_articles = _load_articles_from_dir(processed_dir)
    if not all_articles:
        print(
            f"[INFO] No articles found for source '{source_name}'.",
            file=sys.stderr,
        )
        return []

    seen_hashes = load_seen_hashes(state_root, source_name)
    new_articles = [a for a in all_articles if a.hash not in seen_hashes]

    # Always update state with all hashes (not just new ones) so that
    # articles which appear in processed but were already in state remain
    # tracked across runs.
    all_hashes = {a.hash for a in all_articles}
    save_seen_hashes(state_root, source_name, all_hashes)

    if not new_articles:
        print(
            f"[INFO] No new articles for source '{source_name}'.",
            file=sys.stderr,
        )
        return []

    stamp = timestamp or _utc_now_stamp()
    out_dir = diff_root / source_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stamp}.json"
    payload = [a.to_dict() for a in new_articles]
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"[OK] {len(new_articles)} new article(s) for '{source_name}' → {out_path}",
        file=sys.stderr,
    )
    return new_articles


def diff_all_sources(
    *,
    processed_root: Path,
    state_root: Path,
    diff_root: Path,
    timestamp: str | None = None,
    fail_fast: bool = False,
) -> dict[str, list[dict]]:
    """Run the diff for every source subdirectory found in *processed_root*.

    Returns a summary dict::

        {
            "diffed":  [{"source": "...", "new_articles": N}, ...],
            "errors":  [{"source": "...", "error": "..."}, ...],
        }
    """
    results: dict[str, list[dict]] = {"diffed": [], "errors": []}

    if not processed_root.is_dir():
        print(
            f"[INFO] processed_root does not exist: {processed_root}",
            file=sys.stderr,
        )
        return results

    source_dirs = [d for d in sorted(processed_root.iterdir()) if d.is_dir()]
    if not source_dirs:
        print("[INFO] No source directories found under processed_root.", file=sys.stderr)
        return results

    stamp = timestamp or _utc_now_stamp()

    for source_dir in source_dirs:
        source_name = source_dir.name
        try:
            new_articles = diff_source(
                source_name=source_name,
                processed_root=processed_root,
                state_root=state_root,
                diff_root=diff_root,
                timestamp=stamp,
            )
            results["diffed"].append(
                {"source": source_name, "new_articles": len(new_articles)}
            )
        except Exception as exc:  # noqa: BLE001
            results["errors"].append({"source": source_name, "error": str(exc)})
            print(f"[ERROR] {source_name}: {exc}", file=sys.stderr)
            if fail_fast:
                raise

    return results
