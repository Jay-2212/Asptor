"""Shared health/audit reporting for the Asptor pipeline.

Used by both the automated per-run health report
(``scripts/report/run_health_report.py``) and the local maintenance CLI
(``scripts/maintain.py``) so the two never drift apart.

The output is a plain dict of counts and source names only -- no filesystem
paths, tokens, or other locally-identifying information -- so it is safe to
write into the repository and read by anyone.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

# content_html + content_text length below which an article is considered
# effectively bodyless. Matches the historical threshold used by the
# original ad-hoc maintenance script.
SHORT_CONTENT_THRESHOLD = 100


def audit_processed_data(processed_root: Path) -> dict[str, Any]:
    """Scan *processed_root* and return health statistics.

    Counts each article hash once per source (the richest/most recent
    record for that hash is a publish-time concern; this audit reports on
    raw processed volume and quality signals instead).
    """
    if not processed_root.exists():
        return {
            "total_articles": 0,
            "sources": [],
            "per_source_counts": {},
            "empty_or_short_content": 0,
            "missing_hero_images": 0,
            "possible_duplicate_titles": 0,
            "possible_duplicate_urls": 0,
            "malformed_files": 0,
            "warnings": ["processed_root does not exist"],
        }

    total_articles = 0
    empty_content = 0
    missing_images = 0
    malformed_files = 0
    sources_found: set[str] = set()
    per_source: Counter = Counter()
    title_counts: Counter = Counter()
    url_counts: Counter = Counter()

    for source_dir in sorted(p for p in processed_root.iterdir() if p.is_dir()):
        sources_found.add(source_dir.name)
        seen_hashes_here: set[str] = set()
        for json_file in sorted(source_dir.glob("*.json")):
            try:
                articles = json.loads(json_file.read_text(encoding="utf-8"))
            except Exception:
                malformed_files += 1
                continue
            if not isinstance(articles, list):
                malformed_files += 1
                continue

            for a in articles:
                if not isinstance(a, dict):
                    continue
                h = a.get("hash")
                if h in seen_hashes_here:
                    continue
                seen_hashes_here.add(h)

                total_articles += 1
                per_source[source_dir.name] += 1

                content_len = len(a.get("content_html") or "") + len(a.get("content_text") or "")
                if content_len < SHORT_CONTENT_THRESHOLD:
                    empty_content += 1
                if not a.get("image_url"):
                    missing_images += 1

                title = (a.get("title") or "").strip().lower()
                if title:
                    title_counts[title] += 1
                url = a.get("url")
                if url:
                    url_counts[url] += 1

    duplicate_titles = sum(1 for count in title_counts.values() if count > 1)
    duplicate_urls = sum(1 for count in url_counts.values() if count > 1)

    warnings: list[str] = []
    if total_articles == 0:
        warnings.append("No articles found in processed data.")
    elif empty_content > total_articles * 0.5:
        warnings.append("More than 50% of articles have empty/short content.")
    if duplicate_titles:
        warnings.append(f"{duplicate_titles} duplicate title(s) detected (possible same content under different URLs).")
    if malformed_files:
        warnings.append(f"{malformed_files} processed file(s) could not be parsed.")

    return {
        "total_articles": total_articles,
        "sources": sorted(sources_found),
        "per_source_counts": dict(per_source),
        "empty_or_short_content": empty_content,
        "missing_hero_images": missing_images,
        "possible_duplicate_titles": duplicate_titles,
        "possible_duplicate_urls": duplicate_urls,
        "malformed_files": malformed_files,
        "warnings": warnings,
    }
