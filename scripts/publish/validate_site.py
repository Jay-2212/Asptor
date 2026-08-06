"""Structural validation of the generated static site.

Run after publish, before the generated commit, so a structurally broken
``site/`` (empty, no article links, article pages missing) fails the
Actions job loudly instead of being committed and deployed.

This is deliberately cheap and dependency-free: it checks structure, not
rendering fidelity (a real browser/HTML5 validator is out of scope for a
CI gate that runs every four hours).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_CONTENT_LINK_RE = re.compile(r'href="content/([a-f0-9]{16})\.html"')


def validate_site(site_root: Path) -> list[str]:
    """Return a list of human-readable problems; empty list means valid."""
    problems: list[str] = []

    index_path = site_root / "index.html"
    if not index_path.exists():
        problems.append("site/index.html does not exist.")
        return problems

    index_html = index_path.read_text(encoding="utf-8")
    if len(index_html.strip()) == 0:
        problems.append("site/index.html is empty.")
        return problems

    if "<html" not in index_html.lower():
        problems.append("site/index.html does not look like an HTML document.")

    linked_hashes = set(_CONTENT_LINK_RE.findall(index_html))
    if not linked_hashes:
        problems.append("site/index.html contains no links to article pages.")

    content_dir = site_root / "content"
    missing = [h for h in linked_hashes if not (content_dir / f"{h}.html").exists()]
    if missing:
        problems.append(
            f"{len(missing)} article page(s) linked from index.html do not exist on disk."
        )

    return problems


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the generated site/ directory before it is committed."
    )
    parser.add_argument("--site-root", default="site", help="Path to the generated site directory.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    problems = validate_site(Path(args.site_root))
    if problems:
        for problem in problems:
            print(f"[INVALID] {problem}", file=sys.stderr)
        return 1
    print("[OK] site/ passed structural validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
