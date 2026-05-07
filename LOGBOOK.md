# Agent Logbook (Handoff Ledger)

Use this file as the single source of truth for task handoffs.

## Entry Template

```md
## [YYYY-MM-DD HH:MM UTC] Agent: <name-or-id>
### Scope Claimed
- <single component/task>

### Context Read
- [ ] README.md
- [ ] INSTRUCTIONS.md
- [ ] ARCHITECTURE.md
- [ ] LOGBOOK.md (latest entries)

### Work Completed
- <what was implemented>

### Tests/Validation
- <what was run and result>

### Decisions
- <key technical decisions and why>

### Risks/Blockers
- <known gaps/issues>

### Next Step for Next Agent
- <one clear next task>
```

---

## [2026-05-07 14:50 UTC] Agent: copilot-task-agent (Phase 3)
### Scope Claimed
- Implement Phase 3: Diff / dedup layer under `scripts/diff/` with tests in `tests/diff/`.
- Audit Phase 2 cleaner logic for real-page validation coverage.

### Context Read
- [x] README.md
- [x] INSTRUCTIONS.md
- [x] ARCHITECTURE.md
- [x] LOGBOOK.md (latest entries)

### Phase 2 Audit Finding
**The Phase 2 cleaning scripts were NOT developed against real fetched HTML.**

Evidence:
- `data/raw/` contains only `.gitkeep` — no actual raw snapshots were ever fetched or committed.
- All test fixtures in `tests/clean/test_cleaners.py` (`_HINDU_HTML`, `_CARAVAN_HTML`, `_FIFTY_TWO_HTML`) are minimal 10–15 line hand-crafted HTML examples, not real listing-page HTML.
- The LOGBOOK Phase 2 entry states "Per-source parsers are tested against representative HTML fixtures" — confirming fixture-based testing only.
- URL-matching regexes and `extract_cards` logic were designed from assumed/documented URL patterns, not from inspecting real pages.

**Risk:** The cleaning logic (URL filter patterns, card-grouping state machine, fallback link-scan) may not correctly identify articles from the actual live pages, which can have deeply nested DOM structures, JavaScript-rendered content, CDN-served images with different URL shapes, etc.

**Required future task (see Next Step below):** A dedicated agent must fetch real HTML from all three sources, run the cleaner on each, inspect the output, and update the per-source cleaner modules to correctly handle the actual page structure.

### Work Completed
- Added `scripts/diff/__init__.py` and `tests/diff/__init__.py` package markers.
- Added `scripts/diff/state_store.py`:
  - `load_seen_hashes(state_root, source_name) -> set[str]` — reads `data/state/<source>/seen_hashes.json`; returns empty set if no file.
  - `save_seen_hashes(state_root, source_name, hashes) -> Path` — merges with existing hashes and writes sorted JSON list.
- Added `scripts/diff/differ.py`:
  - `diff_source(...)` — loads all processed Article records for a source, filters to unseen hashes, writes diff file, updates state.
  - `diff_all_sources(...)` — iterates all source subdirs under `processed_root`, delegates to `diff_source`, returns summary dict.
- Added `scripts/diff/run_diff.py` — CLI (`python -m scripts.diff.run_diff`) with `--processed-root`, `--state-root`, `--diff-root`, `--fail-fast` flags.
- Added comprehensive test suite in `tests/diff/`: `test_state_store.py` (10 tests), `test_differ.py` (17 tests), `test_run_diff.py` (4 tests).
- Updated `README.md` with Phase 3 usage docs.

### Tests/Validation
- Full test suite after implementation:
  - `python -m unittest discover -v` ✅ (113 tests passed, 0 failures, 0 errors)
  - Phase 1 fetch tests: 5/5 green.
  - Phase 2 clean tests: 77/77 green.
  - Phase 3 diff tests: 31 new tests, all pass.

### Decisions
- State file holds all hashes ever seen for a source (monotonically growing); never removes old hashes. This ensures articles discovered in one run are never re-emitted, even if they drop off the listing page later.
- `diff_source` aggregates all `*.json` files in the processed source directory (not just the latest). This means articles from any historical processed snapshot are tracked; the diff is always relative to the full known universe.
- A shared `timestamp` parameter in `diff_all_sources` ensures all sources in a single run get the same output filename stem for easy cross-source correlation.

### Risks/Blockers
- **Phase 2 cleaning logic has not been validated against real page HTML** (see audit finding above). Until that validation task is completed, the entire pipeline may produce zero or incorrect articles from real fetches.
- The diff layer depends on the processed data; it will work correctly only once the clean layer is validated and producing real Article records.

### Next Step for Next Agent
**PRIORITY: Validate and fix Phase 2 cleaning logic against real fetched HTML.**

Concrete steps:
1. Run `python -m scripts.fetch.run_fetch --raw-root data/raw` to fetch live HTML from all three sources (The Hindu, The Caravan, Fifty Two). Inspect the saved snapshots in `data/raw/`.
2. Run `python -m scripts.clean.run_clean --raw-root data/raw --processed-root data/processed` and inspect the output in `data/processed/`. If any source produces zero or clearly wrong Article stubs, the cleaner for that source needs to be updated.
3. For each source with issues: read the raw snapshot HTML, identify the real article-card structure (CSS classes, tag nesting), and update the URL filter regex and/or `extract_cards` logic in the corresponding `*_cleaner.py`.
4. Re-run the fetch → clean → diff pipeline end-to-end and confirm articles are being extracted correctly for all three sources.
5. Update `tests/clean/test_cleaners.py` with realistic HTML fixture snippets sampled from the real pages (redacted if needed) to lock in the correct behavior.

Once cleaning is validated, implement **Phase 4: static publishing pipeline** under `scripts/publish/`.

---

## [2026-05-07 14:30 UTC] Agent: copilot-task-agent (Phase 2)
### Scope Claimed
- Implement Phase 2: Cleaning + Normalization Layer under `scripts/clean/` with tests in `tests/clean/`.

### Context Read
- [x] README.md
- [x] INSTRUCTIONS.md
- [x] ARCHITECTURE.md
- [x] LOGBOOK.md (latest entries)

### Assumptions & Expected Outputs
- Assumption: Phase 1 raw snapshots are listing-page HTML (not individual article HTML). The clean layer extracts article stubs from these listing pages.
- Assumption: `content_html` / `content_text` fields are intentionally empty at this stage — individual-article content fetching is deferred to a later phase.
- Assumption: Stick to Python stdlib only (no BeautifulSoup), consistent with Phase 1 decisions.
- Expected output: `scripts/clean/` containing schema, HTML utilities, per-source cleaners, registry, and CLI; `tests/clean/` containing comprehensive unit tests.

### Work Completed
- Added `scripts/clean/schema.py` — `Article` dataclass with `compute_hash`, `to_dict/from_dict`, `to_json/from_json` serialisation.
- Added `scripts/clean/html_utils.py` — stdlib `HTMLParser`-based utilities: `extract_text`, `extract_links` (with root-relative resolution), `extract_meta` (Open Graph + `<title>`), and `extract_cards` (card-context-aware extractor that groups `<img>`, `<a>` title, and `<time>` into article-card bundles).
- Added `scripts/clean/base_cleaner.py` — abstract `BaseCleaner` with `parse()` and `clean_snapshot()` entry-point.
- Added `scripts/clean/the_hindu_cleaner.py` — The Hindu Opinion parser (filters `/opinion/` paths, deduplicates, falls back to plain link scan).
- Added `scripts/clean/the_caravan_cleaner.py` — The Caravan parser (filters `/<section>/<slug>` patterns, excludes utility paths).
- Added `scripts/clean/fifty_two_cleaner.py` — Fifty Two parser (filters top-level slug paths, excludes known utility segments).
- Added `scripts/clean/registry.py` — `CLEANERS` dict + `get_cleaner()` factory.
- Added `scripts/clean/run_clean.py` — CLI (`python -m scripts.clean.run_clean`) with `--raw-root`, `--processed-root`, `--fail-fast` flags; writes `data/processed/<source>/<timestamp>.json`.
- Added `scripts/clean/__init__.py` and `tests/clean/__init__.py` package markers.
- Added comprehensive test suite in `tests/clean/`: `test_schema.py`, `test_html_utils.py`, `test_cleaners.py`, `test_registry_and_run.py`.
- Updated `README.md` with Phase 2 usage docs and Article schema table.

### Tests/Validation
- Full test suite after implementation:
  - `python -m unittest discover -v` ✅ (82 tests passed, 0 failures, 0 errors)
  - Phase 1 fetch tests remain green (5/5).
  - Phase 2 clean tests: 77 new tests added and all pass.

### Decisions
- Listing-page approach: raw snapshots hold listing-page HTML; the clean layer extracts article stubs with url+title only. `content_html`/`content_text` are intentionally empty — full article body fetching is a future concern.
- `hash` = `source_id` = `sha256(url::title)[:16]` provides a stable dedup key for Phase 3's diff layer.
- `extract_cards` uses a stack-based state machine to group `<img>`, `<a>`, and `<time>` within structural block tags (`<article>`, `<li>`, `<div>`, `<section>`). This is more robust than pure link scanning for modern listing pages.
- Cleaners include a link-scan fallback in case the card extractor yields nothing (e.g., unusual HTML structure).

### Risks/Blockers
- Source-specific URL filters are based on known patterns and may need refinement if site structure changes.
- `content_html` / `content_text` are empty at this stage; a future individual-article fetch step is needed to populate them.
- Per-source parsers are tested against representative HTML fixtures; real-world pages may expose edge cases.

### Next Step for Next Agent
- Implement Phase 3: Diff / dedup layer under `scripts/diff/` with tests in `tests/diff/`.
- The diff layer should compare the latest `data/processed/<source>/` files against a stored state (e.g., `data/state/<source>/seen_hashes.json`) and emit only newly discovered articles.
- Key inputs: Article `hash` field (16-hex SHA-256 of url+title); key output: `data/diff/<source>/<timestamp>.json` containing only new/updated records.

---

## [2026-05-07 13:55 UTC] Agent: copilot-task-agent
### Scope Claimed
- Implement Phase 1 source fetcher foundation with retries, raw snapshot persistence, and focused unit tests.

### Context Read
- [x] README.md
- [x] INSTRUCTIONS.md
- [x] ARCHITECTURE.md
- [x] LOGBOOK.md (latest entries)

### Assumptions & Expected Outputs
- Assumption: keep implementation dependency-light using Python standard library only.
- Assumption: source URL list can start as configured defaults and evolve in later iterations.
- Expected output: reusable fetcher utilities under `scripts/fetch/`, plus tests under `tests/fetch/`.

### Work Completed
- Added `scripts/fetch/sources.py` with initial default source definitions for The Hindu Opinion, The Caravan, and Fifty Two.
- Added `scripts/fetch/fetcher.py` with:
  - retrying network fetch utility (`fetch_with_retries`)
  - structured fetch error type (`FetchError`)
  - raw snapshot persistence into `data/raw/<source>/<timestamp>.json`
  - orchestrators for single-source and all-source runs.
- Added `scripts/fetch/run_fetch.py` CLI for running fetches with configurable retry/backoff/timeout and fail-fast behavior.
- Added unit tests in `tests/fetch/test_fetcher.py`.
- Added package markers (`scripts/__init__.py`, `scripts/fetch/__init__.py`, `tests/__init__.py`, `tests/fetch/__init__.py`) to ensure clean module/test discovery.
- Updated `README.md` with Phase 1 fetcher usage docs.

### Tests/Validation
- Baseline before changes: `python -m unittest discover -v` (0 tests, exit code 5).
- After implementation:
  - `python -m unittest discover -s tests -v` ✅ (5 tests passed)
  - `python -m unittest discover -v` ✅ (5 tests passed)

### Decisions
- Kept implementation in Python standard library to avoid introducing dependency management overhead in early phase.
- Stored raw snapshots as JSON with source metadata and UTC fetch timestamp to support later clean/diff stages with traceability.
- Implemented retry logic with exponential backoff and optional fail-fast mode to balance resilience and controllability.

### Risks/Blockers
- Source URLs are first-pass placeholders and may require refinement (e.g., dedicated feed endpoints) during source-hardening work.
- HTML retrieval works, but source-specific parsing/normalization is intentionally deferred to the cleaning phase.

### Next Step for Next Agent
- Implement Phase 2 cleaning + normalization for the saved raw snapshots into the draft common schema under `scripts/clean/` with tests in `tests/clean/`.

## [2026-05-07 13:30 UTC] Agent: foundation-scaffold
### Scope Claimed
- Create base repository structure, foundational docs, and handoff workflow.

### Context Read
- [x] README.md
- [x] INSTRUCTIONS.md
- [x] ARCHITECTURE.md
- [x] LOGBOOK.md (latest entries)

### Work Completed
- Added initial app scaffold directories for fetch/clean/diff/publish, data, site, and tests.
- Rewrote public README with project goal, structure, and execution context.
- Added `INSTRUCTIONS.md`, `AGENTS.md`, and `ARCHITECTURE.md` for phased implementation.
- Initialized handoff process and template in this logbook.

### Tests/Validation
- No test framework exists yet; validated structure and document consistency manually.

### Decisions
- Chose documentation-first scaffold to enable parallel, non-overlapping agent execution.
- Kept implementation code out of Phase 0 to avoid premature coupling before architecture-specific work.

### Risks/Blockers
- No pipeline code exists yet.
- No CI/test tooling configured yet.

### Next Step for Next Agent
- Implement Phase 1: source fetcher modules and tests under `scripts/fetch/` and `tests/fetch/`.
