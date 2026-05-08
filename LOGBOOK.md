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

## [2026-05-08 07:15 UTC] Agent: Gemini CLI
### Scope Claimed
- **Urgent Fix:** Resolution of "empty content" issues on the live site.
- **UI Enhancement:** Implementation of a Tabbed UI for category switching.
- **Pipeline Integrity:** Fixing destructive behavior in the cleaning script.

### Context Read
- [x] Live site URLs provided by user.
- [x] Local `data/processed/` JSON content.
- [x] `scripts/clean/run_clean.py` logic.

### Work Completed
- **Tabbed UI:** Successfully implemented a tabbed navigation (Reading Material vs National News) with interactive JavaScript switching and updated CSS.
- **Non-Destructive Cleaning:** Modified `scripts/clean/run_clean.py` to preserve existing article bodies in `data/processed/`. Previously, every run would overwrite full articles with empty listing-page data.
- **Large-Scale Repair:** Performed a local repair run for **150+ historical articles** from Fifty Two and The Caravan. Confirmed locally that these now contain full HTML content (e.g., article `025649bf1beefc3e` is now 32KB).
- **Cleaner Updates:** Refined 52 and Caravan cleaners to handle JSON-LD and Svelte-based DOMs.
- **Scroll Removal:** Completely purged Scroll Magazine data and code.

### Status: NOT FIXED (User Side)
Despite local confirmation that repaired files have been pushed to GitHub, the user reports that the live site content for repaired articles remains empty.

### Potential Areas for Investigation
1. **GitHub Actions Overwrite:** Even with the "non-destructive" fix, the GitHub Actions environment starts with a fresh checkout. If the repairs were not correctly merged or if the Action's `Run Clean` step is somehow ignoring the pushed data, it might still be generating empty articles.
2. **Publishing Mismatch:** Verify if `scripts/publish/run_publish.py` is correctly reading from the enriched `data/processed/` files or if it's using an older state.
3. **GitHub Pages Caching/Propagation:** The user mentioned clearing cookies, but GitHub Pages can take up to 10 minutes to invalidate its CDN cache.
4. **Scraping Block in CI:** GitHub Actions IPs are often flagged by news sites. If the repair only happened locally and the CI is trying to "re-fetch" (even if logic says not to), it might be failing and reverting to empty content.

### Potential Ideas for Solving
- **Decouple Clean from Fetch:** Change the CI to *only* fetch new articles and never re-run cleaning on historical snapshots unless explicitly triggered.
- **Artifact Analysis:** Inspect the "site" artifact in GitHub Actions to see the exact content of the `.html` files before they are deployed.
- **Proxy/MCP Integration:** Re-evaluate the MCP/Cloudflare Warp idea specifically for the GitHub Actions environment to bypass IP blocks.

### Next Step for Next Agent
- **Examine CI Logs:** Look at the most recent "Asptor Pipeline" run logs to see if `Run Full Article Clean` is actually succeeding or hitting 403/Empty errors.
- **Force Deployment:** Manually verify the repository's `site/content/` folder on GitHub to see if the files there actually contain the text I confirmed locally.

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

... rest of file ...
