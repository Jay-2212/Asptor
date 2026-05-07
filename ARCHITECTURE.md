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

### Phase 0 (Current)
- Scaffold project structure
- Establish docs + handoff workflow

### Phase 1
- Implement source fetchers with robust error handling/retries

### Phase 2
- Implement per-source cleaner modules + schema normalization

### Phase 3
- Implement diff/dedup state logic

### Phase 4
- Implement static publishing pipeline

### Phase 5
- Add scheduled GitHub Actions + Pages deployment

### Phase 6
- UX polish and reading optimization

## Token Guidance (for later implementation)
- Start with `GITHUB_TOKEN` in Actions for same-repo writes.
- Use PAT only if required by repository policy or cross-repo writes.
- Keep tokens in repository secrets; never hardcode.
