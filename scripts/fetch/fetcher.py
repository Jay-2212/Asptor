from __future__ import annotations

import json
import re
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.request import urlopen

from .sources import DEFAULT_SOURCES, SourceConfig


class FetchError(Exception):
    def __init__(self, url: str, attempts: int, last_error: Exception) -> None:
        self.url = url
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Failed to fetch {url} after {attempts} attempt(s): {last_error}"
        )


import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/124.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]

def fetch_with_retries(
    *,
    url: str,
    max_attempts: int = 3,
    timeout_seconds: int = 20,
    backoff_seconds: float = 1.0,
    sleeper: Callable[[float], None] = time.sleep,
) -> str:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    last_error: Exception | None = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            ua = random.choice(USER_AGENTS)
            headers = {
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            from urllib.request import Request
            req = Request(url, headers=headers)
            with urlopen(req, timeout=timeout_seconds) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == max_attempts:
                break
            sleeper(backoff_seconds * (2 ** (attempt - 1)))

    raise FetchError(
        url=url,
        attempts=max_attempts,
        last_error=last_error or Exception("No error captured during retries"),
    )


def _normalize_source_name(source_name: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", source_name.strip().lower())


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def save_raw_snapshot(
    *,
    raw_root: Path,
    source: SourceConfig,
    content: str,
    fetched_at: datetime | None = None,
) -> Path:
    moment = fetched_at or datetime.now(timezone.utc)
    source_dir = raw_root / _normalize_source_name(source.name)
    source_dir.mkdir(parents=True, exist_ok=True)
    file_path = source_dir / f"{moment.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}.json"

    payload = {
        "source": asdict(source),
        "fetched_at": _iso_utc(moment),
        "content_html": content,
    }
    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return file_path


def run_source_fetch(
    *,
    source: SourceConfig,
    raw_root: Path,
    max_attempts: int = 3,
    timeout_seconds: int = 20,
    backoff_seconds: float = 1.0,
    sleeper: Callable[[float], None] = time.sleep,
) -> Path:
    content = fetch_with_retries(
        url=source.url,
        max_attempts=max_attempts,
        timeout_seconds=timeout_seconds,
        backoff_seconds=backoff_seconds,
        sleeper=sleeper,
    )
    return save_raw_snapshot(raw_root=raw_root, source=source, content=content)


def run_all_sources(
    *,
    raw_root: Path,
    sources: tuple[SourceConfig, ...] = DEFAULT_SOURCES,
    max_attempts: int = 3,
    timeout_seconds: int = 20,
    backoff_seconds: float = 1.0,
    fail_fast: bool = False,
) -> dict[str, list[dict[str, str]]]:
    results: dict[str, list[dict[str, str]]] = {"saved": [], "errors": []}
    for source in sources:
        try:
            output_file = run_source_fetch(
                source=source,
                raw_root=raw_root,
                max_attempts=max_attempts,
                timeout_seconds=timeout_seconds,
                backoff_seconds=backoff_seconds,
            )
            results["saved"].append(
                {"source": source.name, "url": source.url, "path": str(output_file)}
            )
        except Exception as exc:  # noqa: BLE001
            results["errors"].append(
                {"source": source.name, "url": source.url, "error": str(exc)}
            )
            if fail_fast:
                raise
    return results
