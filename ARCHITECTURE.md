# Architecture and Delivery Phases

## Product Goal
A static GitHub Pages app for CAT VARC prep that provides ad-free, clean article reading from selected high-quality sources.

## Initial Target Sources
- The Hindu (Opinion / Editorial and/or RSS)
- The Caravan
- Fifty Two

## High-Level Pipeline

1. **Fetch Layer** (`scripts/fetch/`)
   - Pull source feeds/pages
   - Retry transient failures and use source-specific fallback URLs
   - Save raw snapshots to `data/raw/`

2. **Clean Layer** (`scripts/clean/`)
   - Source-specific parsing + sanitization
   - Normalize into common article schema
   - Store results in `data/processed/`

3. **Diff Layer** (`scripts/diff/`)
   - Compare current normalized set vs prior state
   - Keep only newly discovered/updated articles

4. **Publish Layer** (`scripts/publish/`)
   - Generate static content for `site/content/`
   - Include metadata and image links for display

5. **Automation Layer** (GitHub Actions)
   - Run every 3–4 hours
   - Execute pipeline
   - Continue on partial source availability, but fail if no source is fetched
   - Commit generated output
   - Deploy via GitHub Pages

## Core Data Contract (Draft)
All cleaned records should converge toward:

- `source`
- `source_id`
- `url`
- `title`
- `subtitle` (optional)
- `author` (optional)
- `published_at`
- `image_url` (optional)
- `content_html`
- `content_text`
- `fetched_at`
- `hash` (for diffing)

## Phase Plan

### Phase 0 — Scaffold ✅ complete
Project structure, docs, and the agent handoff workflow (`LOGBOOK.md`).

### Phase 1 — Fetchers ✅ complete
Retrying fetch, per-source fallback URLs (e.g. Indian Express RSS fallback
when the HTML listing is blocked), `--allow-partial` for scheduled runs.

### Phase 2 — Cleaning + normalization ✅ complete
Per-source listing cleaners (`scripts/clean/*_cleaner.py`) and per-source
full-article-body cleaners (`scripts/clean/article_cleaners/`), with
body-preservation across snapshots so a later empty listing fetch never
overwrites an already-enriched article.

### Phase 3 — Diff/dedup ✅ complete
Monotonic seen-hash state (`data/state/`) so an article is only ever
"new" once.

### Phase 4 — Static publishing ✅ complete
Static HTML generation with an output-boundary sanitizer
(`scripts/publish/sanitize.py`) and a structural validator
(`scripts/publish/validate_site.py`) that runs before every commit.

### Phase 5 — Scheduling + deploy ✅ complete
`.github/workflows/pipeline.yml` runs every 4 hours (schedule) or on
demand (`workflow_dispatch`), commits generated `data/`/`site/` changes,
and deploys via GitHub Pages. Code changes are validated separately by
`.github/workflows/tests.yml` on every push, without touching live
publishers or committing anything — see "Automation Layer" below for why
these are split.

### Phase 6 — UX polish — ongoing
Category tabs, source interleaving, and reading-preference persistence
(font size) are implemented. Remaining known content-quality gaps (e.g. a
majority of articles currently missing a hero image) are tracked via the
per-run health report, not hidden.

## Automation Layer

Two workflows, deliberately separated by concern:

- **`tests.yml`** — runs on every push/PR to `main`. Fast, offline, no
  network calls to publishers, no repository writes. This is the
  code-correctness gate.
- **`pipeline.yml`** — runs only on the 4-hour schedule or manual
  `workflow_dispatch`. This is the content-freshness gate: fetch → clean
  → diff → full-clean (body enrichment) → publish → health report →
  validate → commit → deploy.

They used to be one workflow triggered on every push, which meant a
documentation-only commit could kick off ~90 minutes of live scraping
against third-party sites, and a code push could race a scheduled run for
the same generated files. Splitting them removes both problems while still
letting a human (or agent) trigger a full content refresh on demand via
`workflow_dispatch`.

**Concurrency:** `pipeline.yml` uses `concurrency: group: asptor-pipeline,
cancel-in-progress: false` so overlapping scheduled/manual runs queue
instead of racing, and a cancelled run can never leave `data/`/`site/`
mid-commit.

**Self-trigger loops:** the pipeline's generated commit is pushed using
the job's own `GITHUB_TOKEN`. GitHub does not trigger new workflow runs
from `GITHUB_TOKEN`-authenticated pushes (this is a built-in anti-loop
guard, not something this repo implements itself); the `[skip ci]` commit
message marker is a second, redundant safety net for any tooling that
doesn't honor that default.

**Health gates:**
- `run_publish` exits non-zero (and therefore the job fails, and deploy
  never runs) when a run produces **zero** published articles — a total
  upstream failure must never silently deploy an empty site over a
  previously-healthy one.
- `validate_site.py` checks the generated `site/index.html` is non-empty,
  well-formed enough to be HTML, and that every article link it contains
  resolves to an actual generated page — this runs before the commit step.
- `scripts/report/run_health_report.py` writes `data/health_report.json`
  every run: per-source article counts, empty/short-content count,
  possible-duplicate-title/URL counts, and malformed-file count. This is a
  **reporting** gate, not a fatal one — a single blocked publisher or a
  batch of short articles should be visible, not fatal, as long as the
  overall publish is non-empty.

## Generated-data retention policy

Repository size at the time of this pass: ~2 GB across `data/raw/` (raw
HTML snapshots), `data/processed/` (normalised articles), and `data/diff/`
(discovery history), accumulated over months of 4-hourly commits.

- **`data/raw/`** — no longer committed (see `.gitignore`). Raw
  listing-page HTML is consumed by the clean stage within the same job run
  and has no cross-run value; it was also the single largest growth
  driver. Existing committed snapshots are left in git history untouched —
  this repository does not rewrite history to reclaim space.
- **`data/diff/`** — kept. This is the append-only "what was newly
  discovered, and when" record described in Phase 3, and it is
  comparatively small. `scripts/clean/run_full_clean.py` now tracks which
  diff files it has already processed
  (`data/state/<source>/full_clean_seen_diffs.json`) so a scheduled run
  only does work on *new* diff files instead of re-walking every diff file
  ever produced — this was the main driver of the pipeline's growing
  runtime (it had reached 1h30m+ against a 4-hour schedule before this
  fix).
- **`data/state/`** — kept. Tiny, and required for dedup correctness.
- **`data/processed/`** — kept, but flagged: this is now the largest
  remaining growth driver (one output file per processed snapshot, each
  carrying full article bodies). A compaction strategy — periodically
  collapsing each source's processed files into one canonical file
  retaining only the richest record per article hash — would materially
  shrink this, but has not been implemented in this pass: the existing
  cross-snapshot body-preservation logic in `run_clean.py` and
  `publisher.py` was itself a bug-fix for data loss (see `LOGBOOK.md`,
  2026-05-08 entries), and a compaction pass touching the same code paths
  needs its own dedicated test coverage before being safe to automate.
- **`data/health_report.json`** — new, tiny, safe to commit every run.

## Token Guidance
- `GITHUB_TOKEN` is used for same-repo writes (generated-data commit and
  Pages deploy), scoped per-job to the minimum permission each job needs
  (see `.github/workflows/pipeline.yml`). No PAT is used or required.
- Keep tokens in repository secrets; never hardcode.
