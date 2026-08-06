# Security Policy

## Scope

Asptor is a personal, non-commercial static site generator that fetches
publicly available listing/article pages from a small set of news
publishers, extracts and normalises their content, and republishes it as a
static site on GitHub Pages. There are no user accounts, no user-submitted
content, and no server-side runtime beyond the scheduled GitHub Actions
pipeline — the attack surface is small but real, because the pipeline
ingests and republishes third-party HTML unattended, on a schedule, without
a human reviewing each run.

## Threat model

The primary risk is **untrusted content flowing through an automated
pipeline into a publicly deployed site**:

- Third-party publisher HTML is not trustworthy input. A publisher's page
  could (accidentally or via a compromise of that publisher) contain
  `<script>` tags, inline event handlers, or `javascript:`/`data:` URLs.
  The cleaning layer (`scripts/clean/`) and the publish-time sanitizer
  (`scripts/publish/sanitize.py`) exist specifically to strip these before
  anything reaches `site/`.
- All article fields (title, author, URL, image URL, body HTML) are treated
  as untrusted at the point they are written into generated HTML:
  - Plain-text fields are HTML-escaped (`sanitize.escape_text`).
  - `href`/`src` targets are restricted to `http(s)` and relative URLs
    (`sanitize.safe_url`); `javascript:`, `data:`, and other schemes are
    dropped.
  - `content_html` is parsed and stripped of `<script>`, `<style>`,
    `<iframe>`, `<object>`, `<embed>`, `<form>`, `<svg>`, and any `on*`
    event-handler attribute (`sanitize.sanitize_content_html`).
- Generated reports (`data/health_report.json`, `MAINTENANCE_REPORT.md`)
  contain only counts and source names — never file paths, tokens, or
  other machine/account-identifying information. If you add a new report
  or log line, keep it that way.

## Subprocess and CI safety

- No script in this repository invokes a shell via `subprocess.run(...,
  shell=True)`. Commands are always explicit argument lists.
- The GitHub Actions workflow uses the default `GITHUB_TOKEN`, scoped to
  the minimum permissions each job needs (`contents: write` only for the
  job that commits generated data; `pages: write` / `id-token: write` only
  for the deploy job). See `.github/workflows/pipeline.yml`.
- Network fetches use a timeout and bounded retry count
  (`scripts/fetch/fetcher.py`); nothing in the pipeline blocks
  indefinitely on a hung connection.

## Reporting a vulnerability

This is a small personal project without a dedicated security team. If you
find a security issue (e.g. a sanitizer bypass that lets publisher content
execute script on the deployed site, or a credential/token leak in a
workflow log), please open a GitHub issue on this repository, or contact
the maintainer via the details on https://jaybharti.me/. Please avoid
filing public issues for anything that could be actively exploited before
a fix ships (e.g. a live sanitizer bypass) — reach out privately first.

## Non-goals

- This project does not process secrets or PII beyond the GitHub Actions
  `GITHUB_TOKEN`, which GitHub itself manages and rotates.
- This project does not claim to be resilient against a compromised
  publisher deliberately targeting Asptor's cleaners; the sanitizer is a
  defense-in-depth measure, not a guarantee.
