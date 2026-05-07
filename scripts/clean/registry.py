"""Registry: maps source names to their cleaner instances.

Usage::

    from scripts.clean.registry import get_cleaner, CLEANERS

    cleaner = get_cleaner("the_hindu_opinion")
    articles = cleaner.clean_snapshot(snapshot_dict)
"""
from __future__ import annotations

from .base_cleaner import BaseCleaner
from .fifty_two_cleaner import FiftyTwoCleaner
from .the_caravan_cleaner import TheCaravanCleaner
from .the_hindu_cleaner import TheHinduCleaner

# Map of source_name → cleaner instance.
CLEANERS: dict[str, BaseCleaner] = {
    c.source_name: c
    for c in (
        TheHinduCleaner(),
        TheCaravanCleaner(),
        FiftyTwoCleaner(),
    )
}


def get_cleaner(source_name: str) -> BaseCleaner:
    """Return the cleaner for *source_name*.

    Raises:
        KeyError: if no cleaner is registered for the given source name.
    """
    try:
        return CLEANERS[source_name]
    except KeyError:
        known = ", ".join(sorted(CLEANERS))
        raise KeyError(
            f"No cleaner registered for source {source_name!r}. "
            f"Known sources: {known}"
        ) from None
