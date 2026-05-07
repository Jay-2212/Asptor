"""Abstract base class for all source-specific cleaners."""
from __future__ import annotations

from abc import ABC, abstractmethod

from .schema import Article


class BaseCleaner(ABC):
    """All source cleaners implement this interface.

    ``source_name`` must match the ``name`` field stored in the raw snapshot's
    ``source`` dict — this is how the registry maps a snapshot to a cleaner.
    """

    source_name: str

    @abstractmethod
    def parse(
        self,
        content_html: str,
        source_url: str,
        fetched_at: str,
    ) -> list[Article]:
        """Parse raw listing-page HTML and return normalised Article records.

        Args:
            content_html: Raw HTML string from the fetched listing page.
            source_url:   The URL of the listing page (used for resolving
                          relative links).
            fetched_at:   ISO 8601 UTC timestamp string of when the page was
                          fetched (carried through to every Article).

        Returns:
            A (possibly empty) list of Article records found on the page.
        """

    def clean_snapshot(self, snapshot: dict) -> list[Article]:
        """Convenience entry-point: accept a raw snapshot *dict* and return Articles.

        The snapshot dict is expected to have the shape produced by
        ``scripts.fetch.fetcher.save_raw_snapshot``:

        .. code-block:: json

            {
              "source": {"name": "...", "url": "..."},
              "fetched_at": "2026-01-02T03:04:05Z",
              "content_html": "<html>...</html>"
            }
        """
        return self.parse(
            content_html=snapshot.get("content_html", ""),
            source_url=snapshot.get("source", {}).get("url", ""),
            fetched_at=snapshot.get("fetched_at", ""),
        )
