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
