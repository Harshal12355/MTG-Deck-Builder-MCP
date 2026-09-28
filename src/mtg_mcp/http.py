"""Shared HTTP client: polite per-host rate limiting and a small in-memory TTL cache.

Scryfall asks for a User-Agent, an Accept header, and roughly 50-100 ms between
requests. EDHREC and Commander Spellbook get the same courtesy.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from . import __version__

USER_AGENT = f"mtg-deckbuilder-mcp/{__version__} (+https://github.com/Harshal12355/MTG-Deck-Builder-MCP)"

# Minimum seconds between requests to the same host.
DEFAULT_MIN_INTERVAL = 0.1
HOST_INTERVALS = {
    "api.scryfall.com": 0.1,
    "json.edhrec.com": 0.5,
    "backend.commanderspellbook.com": 0.25,
}


class ApiError(Exception):
    """An upstream API returned an error we should show to the model."""

    def __init__(self, message: str, status: int | None = None, details: Any = None):
        super().__init__(message)
        self.status = status
        self.details = details


class TTLCache:
    def __init__(self, max_items: int = 2000):
        self._data: dict[str, tuple[float, Any]] = {}
        self._max = max_items

    def get(self, key: str) -> Any | None:
        item = self._data.get(key)
        if item is None:
            return None
        expires, value = item
        if expires < time.monotonic():
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: float) -> None:
        if len(self._data) >= self._max:
            # Drop the entry closest to expiry (cheap, good enough for this size).
            oldest = min(self._data, key=lambda k: self._data[k][0])
            self._data.pop(oldest, None)
        self._data[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        self._data.clear()


class HttpClient:
    def __init__(self, client: httpx.AsyncClient | None = None, rate_limit: bool = True):
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(20.0),
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            follow_redirects=True,
        )
        # Make sure headers are present even on an injected client.
        # (httpx always sets its own default User-Agent, so overwrite rather than setdefault.)
        self._client.headers["User-Agent"] = USER_AGENT
        self._client.headers["Accept"] = "application/json"
        self._rate_limit = rate_limit
        self._locks: dict[str, asyncio.Lock] = {}
        self._last: dict[str, float] = {}
        self.cache = TTLCache()

    async def _throttle(self, url: str) -> None:
        if not self._rate_limit:
            return
        host = urlparse(url).netloc
        lock = self._locks.setdefault(host, asyncio.Lock())
        async with lock:
            interval = HOST_INTERVALS.get(host, DEFAULT_MIN_INTERVAL)
            wait = self._last.get(host, 0.0) + interval - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last[host] = time.monotonic()

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        ttl: float = 0,
        allow_404: bool = False,
    ) -> Any:
        key = None
        if ttl > 0:
            key = json.dumps([method, url, params, json_body], sort_keys=True, default=str)
            cached = self.cache.get(key)
            if cached is not None:
                return cached

        for attempt in range(3):
            await self._throttle(url)
            try:
                resp = await self._client.request(method, url, params=params, json=json_body)
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise ApiError(f"Network error calling {urlparse(url).netloc}: {exc}") from exc
                await asyncio.sleep(0.5 * (attempt + 1))
                continue

            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < 2:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
            break

        if resp.status_code == 404 and allow_404:
            return None
        if resp.status_code >= 400:
            details: Any
            try:
                details = resp.json()
            except ValueError:
                details = resp.text[:500]
            message = details.get("details") if isinstance(details, dict) else None
            raise ApiError(
                message or f"{urlparse(url).netloc} returned HTTP {resp.status_code}",
                status=resp.status_code,
                details=details,
            )

        data = resp.json()
        if key is not None:
            self.cache.set(key, data, ttl)
        return data

    async def get(self, url: str, **kw: Any) -> Any:
        return await self.request_json("GET", url, **kw)

    async def post(self, url: str, json_body: Any, **kw: Any) -> Any:
        return await self.request_json("POST", url, json_body=json_body, **kw)

    async def aclose(self) -> None:
        await self._client.aclose()
