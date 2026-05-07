"""Article schema — the common data contract for all cleaned records."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass
class Article:
    """Normalised article record.

    ``source_id`` and ``hash`` are both derived from ``url + title`` so that
    the same article discovered via different listing-page snapshots produces
    an identical record (enabling downstream dedup).
    """

    source: str
    source_id: str
    url: str
    title: str
    subtitle: str | None
    author: str | None
    published_at: str | None
    image_url: str | None
    image_caption: str | None
    content_html: str
    content_text: str
    fetched_at: str
    hash: str

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    @staticmethod
    def compute_hash(url: str, title: str) -> str:
        """Return a 16-hex-character SHA-256 fingerprint of ``url::title``."""
        payload = f"{url.strip()}::{title.strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, **kwargs)

    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """Load from dict, providing defaults for missing fields to handle schema updates."""
        # Ensure all fields exist, providing None for new optional ones if they are missing from JSON
        return cls(
            source=data["source"],
            source_id=data["source_id"],
            url=data["url"],
            title=data["title"],
            subtitle=data.get("subtitle"),
            author=data.get("author"),
            published_at=data.get("published_at"),
            image_url=data.get("image_url"),
            image_caption=data.get("image_caption"),
            content_html=data.get("content_html", ""),
            content_text=data.get("content_text", ""),
            fetched_at=data["fetched_at"],
            hash=data["hash"],
        )

    @classmethod
    def from_json(cls, text: str) -> "Article":
        return cls.from_dict(json.loads(text))
