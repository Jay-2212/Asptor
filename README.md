# Asptor

Asptor is a CAT preparation reading app hosted on GitHub Pages.

This repository is currently in the **foundation phase**. The goal is to build a clean, ad-free reading experience that periodically pulls high-quality journalism (starting with The Hindu Opinion/Edit, The Caravan, and Fifty Two), cleans article content, deduplicates updates, and publishes a static site.

## Current Scope (Scaffold)

This initial scaffold provides:

- Project structure for data ingestion, cleaning, diffing, and static site output
- Agent-facing execution and handoff documentation
- A shared logbook for multi-agent progress tracking

## Planned Workflow

1. Python fetch pipeline runs on schedule (GitHub Actions, every 3–4 hours)
2. Source-specific cleaning and normalization
3. Diff layer identifies newly fetched content only
4. Static content is generated for GitHub Pages
5. GitHub Pages serves updated reading site

## Repository Structure

```text
Asptor/
├── AGENTS.md                  # Agent operating guide
├── ARCHITECTURE.md            # System design and delivery phases
├── INSTRUCTIONS.md            # Quick execution instructions for agents
├── LOGBOOK.md                 # Handoff + signoff ledger between agents
├── data/
│   ├── raw/                   # Raw fetched source data
│   └── processed/             # Cleaned/normalized outputs
├── scripts/
│   ├── fetch/                 # Source fetchers
│   ├── clean/                 # Source-specific cleaners
│   ├── diff/                  # New-content detection logic
│   └── publish/               # Static output generation helpers
├── site/
│   ├── assets/
│   └── content/
└── tests/
    ├── fetch/
    ├── clean/
    ├── diff/
    └── publish/
```

## Notes on GitHub Pages + Actions

- GitHub Actions can commit generated content back to the repository using the default `GITHUB_TOKEN` (usually enough for same-repo updates).
- A Personal Access Token (PAT) may be needed only for advanced cross-repo or restricted-permission workflows.
- Final token strategy should be documented when workflow implementation begins.

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
