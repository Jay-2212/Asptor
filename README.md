# Asptor

Asptor is a CAT preparation reading app hosted on GitHub Pages.

It runs a scheduled pipeline (every 4 hours, via GitHub Actions) that pulls
listing pages from a small set of publications — currently The Hindu
(Opinion and National), Indian Express (Explained), The Caravan, and Fifty
Two — cleans and normalises the articles it finds, deduplicates against
everything seen before, and republishes a static reading site to GitHub
Pages. This has been live and running on schedule for months; it is not a
dormant scaffold.

**Rights and attribution:** Jay's pipeline/cleaning/diffing code is MIT
licensed (`LICENSE-CODE`). Article content itself is not — see
`CONTENT_LICENSE.md` for the precise notice before assuming anything about
what you can do with the data in `data/` or `site/`.

## Current Pipeline (Live)

1. **Fetch** — retrying HTTP fetch with per-source fallback URLs; a
   scheduled run tolerates individual source failures
   (`--allow-partial`) but fails outright if every source fails.
2. **Clean** — per-source listing-page parsers normalise articles into a
   common schema; a scheduled run also tolerates individual malformed
   snapshots (`--allow-partial`) without losing a healthy source's output.
3. **Diff** — compares against persistent per-source seen-hash state so an
   article is only ever "new" once.
4. **Full clean** — fetches and extracts full article bodies for newly
   diffed articles (bounded per run — see `ARCHITECTURE.md` for the
   diff-bookkeeping fix that keeps this from re-processing history).
5. **Publish** — generates the static site, sanitizing every field at the
   output boundary (`scripts/publish/sanitize.py`) and validating the
   result (`scripts/publish/validate_site.py`) before anything is
   committed. A run that publishes zero articles fails the job rather than
   deploying an empty site.
6. **Health report** — `data/health_report.json` is regenerated every run:
   per-source counts, short/empty-content count, possible-duplicate
   counts. See `ARCHITECTURE.md` for what is a hard failure versus a
   visible warning.
7. **Commit + deploy** — generated `data/`/`site/` changes are committed,
   and GitHub Pages is deployed from the validated `site/` output.

See `ARCHITECTURE.md` for the full design, the health-gate policy, and the
generated-data retention policy. See `SECURITY.md` for the threat model
(this pipeline ingests untrusted third-party HTML unattended) and
`CONTRIBUTING.md` for the contribution/handoff workflow.

## Repository Structure

```text
Asptor/
├── AGENTS.md                  # Agent operating guide
├── ARCHITECTURE.md            # System design, health gates, retention policy
├── SECURITY.md                # Threat model, sanitizer design, reporting
├── CONTRIBUTING.md            # Contribution + handoff workflow
├── CONTENT_LICENSE.md         # Rights/attribution notice (read before reusing data/)
├── INSTRUCTIONS.md            # Quick execution instructions for agents
├── LOGBOOK.md                 # Handoff + signoff ledger between agents
├── data/
│   ├── raw/                   # Raw fetched source data (not committed -- see .gitignore)
│   ├── processed/             # Cleaned/normalized outputs
│   ├── diff/                  # New-content discovery history
│   ├── state/                 # Persistent dedup + full-clean bookkeeping
│   └── health_report.json     # Per-run health/quality report
├── scripts/
│   ├── fetch/                 # Source fetchers
│   ├── clean/                 # Source-specific cleaners
│   ├── diff/                  # New-content detection logic
│   ├── publish/                # Static output generation, sanitization, validation
│   ├── report/                 # Shared health/audit reporting
│   └── maintain.py             # Local pipeline runner + audit CLI (--dry-run supported)
├── site/
│   ├── assets/
│   └── content/
└── tests/
    ├── fetch/
    ├── clean/
    ├── diff/
    ├── publish/
    └── report/
```

## Notes on GitHub Pages + Actions

- `.github/workflows/pipeline.yml` (schedule + manual dispatch only) commits
  generated content using the default `GITHUB_TOKEN`, scoped per-job to the
  minimum permissions each job needs. No PAT is used.
- `.github/workflows/tests.yml` runs on every push/PR, read-only, and never
  touches live publishers or the repository. See `ARCHITECTURE.md`
  "Automation Layer" for why these are two separate workflows.

## Next Step

If you are an implementation agent, start with **`INSTRUCTIONS.md`**, then follow **`AGENTS.md`** and update **`LOGBOOK.md`** before and after your work.

## Phase 1 — Fetcher Foundation

The fetch layer persists raw listing-page HTML as timestamped JSON snapshots.

Key modules:
- `scripts/fetch/sources.py` — default source configuration
- `scripts/fetch/fetcher.py` — retrying fetch + raw snapshot persistence
- `scripts/fetch/run_fetch.py` — CLI entrypoint

```bash
python -m scripts.fetch.run_fetch --raw-root data/raw --max-attempts 3
```

Snapshots are saved to `data/raw/<source_name>/<YYYYMMDDTHHMMSSZ>.json`.

The fetch command is strict by default and exits non-zero when any source
fails. Scheduled Actions runs use `--allow-partial`: they continue when at
least one source succeeds, while still failing when every source is
unavailable. Source configurations may also provide ordered fallback URLs;
the Indian Express fetcher uses its public Explained RSS feed when the HTML
listing is blocked for a runner.

---

## Phase 2 — Cleaning + Normalization

The clean layer reads raw snapshots, parses the listing-page HTML, and writes
normalised Article records to `data/processed/`.

Key modules:
- `scripts/clean/schema.py` — `Article` dataclass (common data contract)
- `scripts/clean/html_utils.py` — stdlib-only HTML parsing utilities
- `scripts/clean/base_cleaner.py` — abstract `BaseCleaner` interface
- `scripts/clean/the_hindu_cleaner.py` — The Hindu Opinion listing-page parser
- `scripts/clean/the_caravan_cleaner.py` — The Caravan listing-page parser
- `scripts/clean/fifty_two_cleaner.py` — Fifty Two listing-page parser
- `scripts/clean/registry.py` — source-name → cleaner dispatch
- `scripts/clean/run_clean.py` — CLI entrypoint

```bash
python -m scripts.clean.run_clean --raw-root data/raw --processed-root data/processed
```

Each processed file is written to
`data/processed/<source_name>/<YYYYMMDDTHHMMSSZ>.json` and contains a JSON
array of Article records conforming to the schema in `ARCHITECTURE.md`.

When a listing-page snapshot rediscovers an article whose full body was already
fetched in an older processed snapshot, `run_clean` carries the existing
`content_html` and `content_text` forward into the new processed file. This
prevents scheduled runs from reintroducing empty article bodies for articles
that have already been enriched.

### Article schema

| Field | Type | Notes |
|---|---|---|
| `source` | string | Source name key |
| `source_id` | string | 16-hex SHA-256 of url+title |
| `url` | string | Article URL |
| `title` | string | Article title |
| `subtitle` | string \| null | Optional deck text |
| `author` | string \| null | Optional byline |
| `published_at` | string \| null | ISO 8601 date when available |
| `image_url` | string \| null | Lead image URL |
| `content_html` | string | Full article HTML (empty at listing stage) |
| `content_text` | string | Plain text body (empty at listing stage) |
| `fetched_at` | string | ISO 8601 UTC fetch timestamp |
| `hash` | string | 16-hex SHA-256 of url+title (for diffing) |

---

## Phase 3 — Diff / Dedup Layer

The diff layer compares the latest processed Article records against a
persistent store of previously-seen hashes, emitting only newly discovered
articles.  This prevents re-publishing the same content on every pipeline run.

Key modules:
- `scripts/diff/state_store.py` — load/save `data/state/<source>/seen_hashes.json`
- `scripts/diff/differ.py` — core diff logic (per-source and all-sources entry-points)
- `scripts/diff/run_diff.py` — CLI entrypoint

```bash
python -m scripts.diff.run_diff \
    --processed-root data/processed \
    --state-root     data/state \
    --diff-root      data/diff
```

For each source the diff layer:

1. Loads all Article records from `data/processed/<source>/`.
2. Loads previously-seen hashes from `data/state/<source>/seen_hashes.json`.
3. Filters to articles whose `hash` has **not** been seen before.
4. Writes those new articles to `data/diff/<source>/<YYYYMMDDTHHMMSSZ>.json`.
5. Updates the state file so the same articles are skipped on the next run.

State files grow monotonically (hashes are only added, never removed).  If no
state file exists yet, all current articles are treated as new.

---

## Phase 4 — Static Publishing

The publish layer reads all processed source files and generates:

- `site/index.html`
- one article page per unique article hash under `site/content/`

```bash
python -m scripts.publish.run_publish \
    --processed-root data/processed \
    --site-root      site
```

If the same article hash appears in multiple processed snapshots, the publisher
uses the newest metadata for ordering and display, while preserving body content
from any older enriched record. This is important because scheduled listing
fetches can produce newer empty records for articles whose full bodies were
already fetched earlier.
