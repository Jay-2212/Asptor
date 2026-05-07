# AGENTS.md — Multi-Agent Operating Guide

## Mission
Build Asptor incrementally: a clean CAT reading experience fed by scheduled ingestion from selected journalism sources.

## Working Model
- One agent owns one focused component at a time.
- Each component must be implemented with depth (logic + tests + docs).
- Every agent must read and update `LOGBOOK.md`.

## Rules for Every Agent
1. Read `INSTRUCTIONS.md`, `ARCHITECTURE.md`, and latest `LOGBOOK.md` entries.
2. Claim a single scoped unit of work.
3. Document assumptions before implementation.
4. Add/adjust tests relevant to your changes.
5. Record completion + handoff notes in `LOGBOOK.md`.

## Definition of Done (per component)
- Component implemented to planned depth
- Tests written and run for that component
- Documentation updated for behavior and usage
- Handoff notes include:
  - what was done
  - what is pending
  - risks/blockers
  - exact next step

## Suggested Component Ownership Sequence
1. Source Fetchers (`scripts/fetch/`)
2. Cleaning + Normalization (`scripts/clean/`)
3. Dedupe/Diff Layer (`scripts/diff/`)
4. Static Output Generation (`scripts/publish/` + `site/content/`)
5. GitHub Actions Scheduling + Deploy pipeline
6. UI polish for reading experience

## Handoff Contract
Before leaving, each agent must ensure the next agent can continue without re-discovery work.
