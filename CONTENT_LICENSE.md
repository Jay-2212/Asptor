# Content notice

This repository contains two different kinds of material:

1. Jay's original pipeline, cleaning, and diffing code (see `LICENSE-CODE`); and
2. article snapshots and sample HTML fetched from external publishers —
   currently Indian Express, The Fifty Two, The Caravan, and The Hindu —
   stored under `data/diff/` and in the `sample_*.html` fixtures at the repo
   root.

No license is granted for the second category. That material is reproduced
from its respective publishers. Jay is not the author of this content and
claims no ownership of it or of the publishers' trademarks. It is committed
here for personal reading/practice use and as test fixtures, refreshed on a
schedule by `.github/workflows/pipeline.yml`. Each publisher's own terms and
copyright continue to apply; this notice does not relicense their content or
grant permission to redistribute it.

`LICENSE-CODE` covers the fetching, cleaning, and diffing code, not the
content itself.

## What is stored, and why

- `data/processed/` and `data/diff/` store normalised article metadata
  (title, author, published date, canonical source URL) and, where
  fetched, full article body HTML/text, exactly as extracted from the
  publisher's own page. Nothing is paraphrased, summarised, or altered
  beyond structural cleanup (removing ads/navigation/scripts).
- Every stored article record retains its original `url` (the canonical
  source link) and `source` field, and every generated article page is
  built to link back to that original URL. This is a deliberate design
  choice, not incidental: attribution to the original publisher is
  preserved at every layer, not just on the index page. (The one exception
  is defensive, not intentional: if a stored `url` ever failed the
  publish-time safety check in `scripts/publish/sanitize.py` — e.g. an
  unexpected non-http(s) scheme — the page omits the source link rather
  than rendering something unsafe. In practice every configured source's
  URLs are validated at extraction time, so this should not occur.)
- `data/health_report.json` and `MAINTENANCE_REPORT.md` contain only
  aggregate counts (article totals, per-source counts, duplicate/short
  counts) — never article text, tokens, or local file paths.
- See `ARCHITECTURE.md` for the retention policy governing how long raw,
  processed, and diff data are kept.

This notice describes what is stored and why; it is not a legal opinion,
and it does not represent that this storage or republishing is cleared
under any particular publisher's terms of use or applicable copyright law.
If you are a rights holder with a concern about content appearing here,
please open a GitHub issue or contact the maintainer via
https://jaybharti.me/.
