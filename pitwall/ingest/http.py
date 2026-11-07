"""A polite HTTP client: rate limiting, retries with backoff, and Retry-After support."""
from __future__ import annotations

import logging
import time

import httpx

log = logging.getLogger(__name__)


class RateLimitedClient:
    def __init__(self, base_url: str, max_per_second: float, transport: httpx.BaseTransport | None = None,
                 retries: int = 6, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.min_interval = 1.0 / max_per_second
        self.retries = retries
        self._last = 0.0
        self._client = httpx.Client(timeout=timeout, transport=transport,
                                    headers={"User-Agent": "pitwall-analytics/1.0 (+github.com/AbdulSohail018/pitwall)"})
        self.requests_made = 0

    def _throttle(self) -> None:
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()

    def get_json(self, path: str, params: dict | None = None):
        url = f"{self.base_url}/{path.lstrip('/')}"
        for attempt in range(self.retries):
            self._throttle()
            try:
                resp = self._client.get(url, params=params)
                self.requests_made += 1
            except httpx.TransportError as exc:
                log.warning("network error on %s: %s (attempt %d)", url, exc, attempt + 1)
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 404:
                return None
            if resp.status_code == 429 or resp.status_code >= 500:
                delay = float(resp.headers.get("Retry-After", 2 ** attempt))
                log.warning("HTTP %s on %s, retrying in %.1fs", resp.status_code, url, delay)
                time.sleep(min(delay, 60))
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError(f"giving up on {url} after {self.retries} attempts")

    def close(self) -> None:
        self._client.close()
