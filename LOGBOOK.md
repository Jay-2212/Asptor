# Agent Logbook (Handoff Ledger)

Use this file as the single source of truth for task handoffs.

## [2026-08-06 16:00 UTC] Agent: Claude (autonomous maintenance pass)
### Scope Claimed
- Production-reliability, content-quality, workflow, and rights-safety
  pass across the whole pipeline (not a single component) — requested as
  a maintainer-level audit, not incremental feature work.

### Context Read
- [x] README.md, ARCHITECTURE.md, AGENTS.md, INSTRUCTIONS.md
- [x] LOGBOOK.md (full history)
- [x] All of scripts/ (fetch, clean, diff, publish, maintain.py)
- [x] All of tests/ (129 tests baseline)
- [x] .github/workflows/pipeline.yml, CONTENT_LICENSE.md, LICENSE-CODE

### Key findings before implementation
- **Output escaping gap:** `scripts/publish/publisher.py` interpolated
  article title/author/url/image_url/content_html into HTML via
  `string.Template.substitute` and f-strings with zero escaping.
  `javascript:` URLs and raw `<script>`/`on*` handlers from a publisher's
  page would have reached the deployed site unmodified.
- **`scripts/maintain.py`** used `subprocess.run(cmd, shell=True)`.
- **Full-clean runtime growth:** `run_full_clean` re-walked every diff
  file ever produced on every run (not just the current run's), which is
  why scheduled runs had grown to 1h13m–1h41m against a 4-hour schedule.
- **Empty-deploy risk:** `run_publish` always exited 0, including when 0
  articles were published — a total upstream failure could silently
  overwrite a healthy deployed site with an empty one.
- **Repo size:** ~2 GB, driven primarily by `data/raw/` (806 MB in a
  50-commit shallow clone) — raw HTML committed every 4 hours with no
  cross-run read dependency.
- **Docs stale:** README still described the project as "foundation
  phase" / "Scaffold" despite months of live scheduled operation.
- **`push` trigger overlap:** `pipeline.yml` ran the full ~90-minute
  scrape-and-deploy pipeline on every push to `main`, including
  docs-only commits.

### Work Completed
- Added `scripts/publish/sanitize.py` (`escape_text`, `safe_url`,
  `sanitize_content_html`) and wired it through
  `publisher.publish_article_page`/`publish_site` — every article field
  is now escaped or scheme-filtered at the output boundary.
- Rewrote `scripts/maintain.py`: explicit argument-list subprocess calls
  (no `shell=True`), cwd validation, `--dry-run` mode, timezone-aware
  timestamps, and shared health-audit logic factored into
  `scripts/report/health.py` (also used by the new per-run health report).
- Added `scripts/report/run_health_report.py` → writes
  `data/health_report.json` every pipeline run (counts only, no paths or
  secrets).
- Added `scripts/publish/validate_site.py`, run before the generated
  commit: checks `site/index.html` is non-empty, HTML-shaped, and that
  every linked article page actually exists.
- `run_publish` now exits non-zero when 0 articles are published.
- `run_clean` gained `--allow-partial` (mirrors the fetch layer): one
  malformed raw snapshot no longer fails the entire clean step for every
  other source.
- Fixed the full-clean runtime-growth bug: `FullArticleProcessor` now
  tracks processed diff files per source in
  `data/state/<source>/full_clean_seen_diffs.json` and only visits new
  ones; `--repair` mode is unaffected (still rescans all processed data on
  demand).
- Fixed a latent `None.startswith` crash in
  `article_cleaners/the_caravan.py`'s hero-image extraction.
- Split `.github/workflows/pipeline.yml` (schedule + `workflow_dispatch`
  only now) from a new `.github/workflows/tests.yml` (push/PR, offline,
  read-only). Added `concurrency: group: asptor-pipeline,
  cancel-in-progress: false`; split `permissions` per job
  (`contents: write` for the pipeline job, `pages: write`/`id-token:
  write` only for deploy); added the health-report and validate-site
  steps before commit.
- Pinned `requirements.txt` to `beautifulsoup4==4.15.0` (previously
  unpinned).
- `.gitignore`d new `data/raw/*/*.json` (forward-only — no history
  rewrite; existing committed snapshots are untouched).
- Added `SECURITY.md`, `CONTRIBUTING.md`; rewrote the stale parts of
  `README.md`; added an "Automation Layer" and "Generated-data retention
  policy" section to `ARCHITECTURE.md`; extended `CONTENT_LICENSE.md`
  with a "What is stored, and why" section (still MIT-for-code-only,
  still no relicensing of publisher content, still no legal-clearance
  claim).
- Added 63 new tests: `tests/publish/test_sanitize.py` (25),
  `tests/report/test_health.py` (11), `tests/publish/test_validate_site.py`
  (5), `tests/clean/test_run_full_clean.py` (6, new coverage — this module
  had none before), `tests/test_pipeline_integration.py` (5, end-to-end
  fixture tests covering partial-source-failure, malformed-snapshot,
  all-sources-failing, unicode, missing/malformed dates, and
  idempotent-rerun scenarios), `tests/publish/test_run_publish.py` (2),
  plus escaping/scheme-filtering assertions and CLI exit-code tests added
  to existing `test_publisher.py` (5 new) and `test_registry_and_run.py`
  (4 new).

### Tests/Validation
- Full suite: `python3 -m unittest discover tests -v` → **192 tests, all
  passing** (up from 129 baseline).
- `python3 -m scripts.publish.validate_site --site-root site` → passes
  against the currently-committed site.
- **Sanitizer verified against real production data, not just fixtures**
  (flagged as a gap by the advisor review before commit): republished all
  7,160 currently-processed articles through the new sanitizer into a
  scratch directory and diff'd every matching page against the committed
  `site/content/`. Result: 0 zero-byte pages, 0 pages shrunk >38%,
  paragraph counts (`<p` tag counts) identical on the largest article
  (297=297), fallback-page count unchanged (29=29), index link count
  unchanged (7160=7160). The one substantive change found: **5,159 of the
  7,160 currently-deployed article pages contain a live inline
  `onclick="if (!window.__cfRLUnblockHandlers) return false;
  openShareLink(...)"` handler**, sourced verbatim from The Hindu's
  share-widget markup — every one of those 5,159 pages currently executes
  third-party JavaScript on the deployed site. The new sanitizer strips
  all of them (confirmed 0 remaining in the regenerated output) while
  leaving surrounding content byte-for-byte structurally intact. This is
  the concrete, previously-live instance of the vulnerability this pass
  was meant to close, not a hypothetical one. During this verification,
  fragment-only anchors (`href="#424441"`, used by The Hindu's live-blog
  format) and `mailto:`/`tel:` share links were initially over-stripped as
  a side effect of the scheme allowlist; both were fixed and covered with
  tests before the numbers above were captured.
- 22 orphaned stale article pages were also surfaced by this diff (files
  that exist in the committed `site/content/` with no corresponding
  hash in current `data/processed/`) — `Publisher` has never deleted
  stale pages when an article drops out of processed data. Pre-existing,
  not caused by this pass; not fixed here (see Next Step).
- `python3 -m scripts.maintain --dry-run` → runs cleanly against local
  data (surfaced a real, pre-existing content-quality signal: 6253/7160
  local processed articles are missing a hero image — not fixed in this
  pass, flagged as a follow-up).
- `git diff --check` → clean (no whitespace errors). Secret/path scan of
  the diff (code + docs, excluding data/site) → clean; the only matches
  were the literal word "secret(s)" in prose.
- **Not run:** a live-fetch smoke test against real publishers. The
  pipeline's own next scheduled tick (cron `0 */4 * * *`) is the first
  live exercise of these changes — see Risks/Blockers.

### Decisions
- Did not prune or rewrite `data/raw/` history, or touch
  `data/processed/`'s growth (flagged, not fixed — see ARCHITECTURE.md
  retention policy) to avoid risking the existing body-preservation
  correctness logic without dedicated test coverage for a compaction pass.
- Kept tag-pinned (not SHA-pinned) first-party `actions/*` versions —
  judged proportionate for first-party GitHub Actions; documented instead
  of guessing SHAs.
- Chose to drop `push` as a trigger for the full pipeline rather than add
  a path filter, since any code change (not just non-docs changes)
  shouldn't imply "also re-scrape now" — `workflow_dispatch` remains
  available for on-demand full runs.

### Risks/Blockers
- `data/processed/` growth is unresolved (flagged in ARCHITECTURE.md).
- Missing hero images (~87% of local processed articles) is a pre-existing
  content-quality gap, not introduced or fixed here.
- `Publisher` never deletes a stale `site/content/<hash>.html` page once
  the corresponding article drops out of `data/processed/` — 22 such
  orphans exist in the currently-committed site. Not fixed here (would
  need care: deleting on every run based on current processed data is
  safe only if merge-forward body preservation is airtight, which is the
  same code path flagged as needing dedicated tests before touching).
- This commit was pushed directly (no PR); `pipeline.yml` no longer
  triggers on `push` (see ARCHITECTURE.md "Automation Layer"), so this
  push itself only ran `tests.yml`. The full pipeline — and therefore the
  first live exercise of the new sanitizer, health gate, and validate-site
  step against a fresh `git clone` in Actions rather than this local
  checkout — will not run until the next `0 */4 * * *` schedule tick or a
  manual `workflow_dispatch`.

### Next Step for Next Agent
- After the next scheduled/manual pipeline run, check
  `data/health_report.json` and Actions logs to confirm the health gates
  behave as designed end-to-end in Actions (verified locally in this pass,
  but not yet inside the Actions environment itself).
- Consider a `data/processed/` compaction pass (see ARCHITECTURE.md) with
  its own dedicated tests before implementing.
- Consider addressing the missing-hero-image rate surfaced by
  `MAINTENANCE_REPORT.md`.
- Consider having `Publisher` prune orphaned `site/content/*.html` pages
  that no longer correspond to any current processed article.

## [2026-08-03 07:30 UTC] Agent: Codex
### Scope Claimed
- Stabilize the scheduled source-fetch pipeline when an external publisher returns an HTTP error.

### Context Read
- [x] README.md
- [x] INSTRUCTIONS.md
- [x] ARCHITECTURE.md
- [x] AGENTS.md
- [x] LOGBOOK.md (latest entries)

### Assumptions Before Implementation
- A single unavailable source should not discard successful snapshots from the other configured sources.
- Indian Express's recurring 403 is an external access-policy change, so its RSS feed is an appropriate source-level fallback rather than a secret or dependency change.
- The pipeline should remain strict when all sources fail, so a green run never means that ingestion produced no usable input.

### Expected Outputs
- Source-fetch fallback and partial-success exit policy.
- Tests covering fallback selection and CLI exit behaviour.
- Workflow and documentation updates describing the failure policy.

### Work Completed
- Added ordered source fallback URLs and recorded the URL actually used in each raw snapshot.
- Added an Indian Express Explained RSS fallback and RSS-to-Article parsing for GitHub-runner 403 responses.
- Changed retries to stop immediately on permanent HTTP statuses such as 403/404 while retaining retries for transient statuses and transport failures.
- Added `--allow-partial` for scheduled runs: the pipeline continues when at least one source succeeds and still fails when all sources fail.
- Updated the workflow, README, and architecture notes.

### Tests/Validation
- Full suite passed: 129 tests.
- Live fetch smoke test passed for all five configured sources.
- Live Indian Express RSS smoke test extracted 200 articles; clean smoke test normalized 32 current Explained articles.
- `git diff --check` and Python compilation passed.

### Decisions
- Kept the CLI strict by default so local and diagnostic invocations still expose partial failures as non-zero.
- Made only the scheduled workflow tolerant of partial source availability; a completely unavailable ingestion run remains a failure.

### Risks/Blockers
- Indian Express may still be intermittently unavailable from GitHub-hosted runners; the RSS fallback and partial-success policy keep the rest of the site updating, but article-body fetches can remain source-dependent.

### Next Step for Next Agent
- Monitor the first post-fix scheduled run and confirm that the Actions job reaches Clean, Publish, and Pages deployment with either the HTML or RSS listing path.

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

## [2026-05-09 06:12 UTC] Agent: Codex
### Scope Claimed
- Improve article reading quality by preserving paragraph formatting for fetched bodies and making index ordering feel less source-clumped.

### Context Read
- [x] README.md
- [x] INSTRUCTIONS.md
- [x] ARCHITECTURE.md
- [x] AGENTS.md
- [x] LOGBOOK.md (latest entries)

### Assumptions Before Implementation
- Fifty Two formatting is primarily lost because JSON-LD `articleBody` is preferred over DOM paragraph nodes.
- Index monotony is primarily caused by many articles sharing identical fetch timestamps, so source/file order dominates within a category.
- The fix should preserve category tabs while interleaving sources inside each category.

### Work Completed
- Updated `scripts/clean/article_cleaners/fifty_two.py` so Fifty Two body extraction prefers DOM paragraph blocks over flat JSON-LD `articleBody`, preserving paragraph structure and stripping inline source-site styles that conflict with Asptor's dark reader.
- Repaired the latest Fifty Two processed snapshot (`data/processed/fifty_two/20260509T051648Z.json`) with the improved cleaner.
- Updated `scripts/publish/publisher.py` to interleave sources within each category tab while preserving recency inside each source, avoiding long same-publication blocks when articles share a fetch timestamp.
- Strengthened duplicate article merging so the publisher keeps newer metadata while preferring the richest paragraph-preserving body when a newer duplicate has flattened content.
- Regenerated `site/` from the updated processed data.

### Tests/Validation
- `python3 -m unittest tests.clean.test_cleaners.FiftyTwoArticleCleanerTests tests.publish.test_publisher.TestPublisher.test_mix_sources_for_feed_interleaves_same_timestamp_articles -v` passed.
- `python3 -m unittest discover -v` passed: 123 tests.
- `python3 -m scripts.publish.run_publish --processed-root data/processed --site-root site` published 283 articles after rebasing onto newer automated pipeline data.
- Verified The Diversion now resolves to a paragraph-rich body with 69 paragraph tags in generated HTML, no inline `style=` attributes, and preserved paragraph breaks.
- Verified index ordering now rotates Reading Material sources (`the_caravan`, `fifty_two`, `the_hindu_opinion`) and National News sources (`indian_express_explained`, `the_hindu_national`) instead of source-clumping.

### Decisions
- Kept category tabs intact and made ordering deterministic source interleaving rather than randomization.
- Preferred source DOM paragraphs for Fifty Two because the JSON-LD body can flatten the whole article into one large paragraph.

### Risks/Blockers
- Older Fifty Two snapshots may still contain flattened content, but the latest repaired snapshot is what the publisher selects for current pages. Future fetches will use the improved cleaner.

### Next Step for Next Agent
- If further typography issues appear, audit the other article cleaners for source-specific inline styles and non-paragraph containers.

## [2026-05-08 05:37 UTC] Agent: Codex
### Scope Claimed
- Diagnose and fix the GitHub Pages article body fallback where published articles show "Content is currently not available" despite fetchable source HTML.

### Context Read
- [x] README.md
- [x] INSTRUCTIONS.md
- [x] ARCHITECTURE.md
- [x] AGENTS.md
- [x] LOGBOOK.md (latest entries)

### Assumptions Before Implementation
- Local raw and processed data may include repaired content, but GitHub Actions can still overwrite generated site output if the pipeline republishes from empty or stale records.
- The fix should stay scoped to article content availability in the fetch/clean/diff/publish/Actions path, avoiding unrelated UI changes.
- Tests should lock the specific failure mode once identified.

### Work Completed
- Diagnosed the live blank-article issue as a duplicate-selection bug in the publish path: `Publisher.load_all_articles()` kept the newest processed record for a hash even when that newer listing snapshot had empty `content_html`/`content_text`, discarding older enriched bodies.
- Confirmed repository data had 107 hashes where an older processed snapshot contained body content but the latest duplicate was empty; before the fix, those would publish fallback pages.
- Updated `scripts/publish/publisher.py` so duplicate article records keep newest metadata while preserving body/content fields from any older enriched record.
- Updated `scripts/clean/run_clean.py` so newly cleaned listing snapshots preserve existing full body content from any prior processed snapshot for the same source/hash, not only from the same timestamped output file.
- Regenerated `site/` with the fixed publisher. A known affected article (`dabfc8c8817a83a2`) changed from the fallback page on GitHub Pages/raw GitHub to a local generated page containing the full article body.
- Documented the cross-snapshot body-preservation behavior in `README.md`.

### Tests/Validation
- `python3 -m unittest tests.publish.test_publisher tests.clean.test_registry_and_run -v` passed.
- `python3 -m unittest discover -v` passed: 120 tests.
- `python3 -m scripts.publish.run_publish --processed-root data/processed --site-root site` published 191 articles.
- Local publish candidate audit now shows 8 truly bodyless records, down from 115 latest-empty records before merge preservation.
- Public check before push: `https://jay-2212.github.io/Asptor/content/dabfc8c8817a83a2.html` and the matching raw GitHub file still contained the fallback, while the regenerated local file does not.

### Decisions
- Fixed the root cause in both publish and clean layers rather than relying on GitHub Actions successfully refetching every body on every run.
- Kept article ordering based on the newest `fetched_at`, but made content fields monotonic so already-fetched bodies are not lost to later listing snapshots.

### Risks/Blockers
- Eight records still have no body in any processed snapshot. Some appear to be section/index pages incorrectly admitted by The Hindu URL matching; others are real article URLs that need a targeted body-fetch repair or the next successful full-clean run.
- GitHub Pages will continue showing the old fallback until these changes and regenerated `site/` output are pushed and the Pages deployment completes.

### Next Step for Next Agent
- Tighten The Hindu listing URL filters to exclude section/index pages like `/news/national/andhra-pradesh/` and `/opinion/Readers-Editor/`, then target-repair the remaining real bodyless article records.

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
