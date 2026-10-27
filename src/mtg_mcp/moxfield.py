"""Moxfield importer: pull every public deck (cards, the author's tags, primer) for a user
and save it as a reference-library source (see library.py).

Moxfield has no official public API. These are the endpoints its own site uses; they may change
or rate-limit. Calls are throttled to ~1 per second. Primers are saved as raw markdown under
``primers/`` so they can be read and distilled into principles later.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .http import ApiError, HttpClient

API = "https://api2.moxfield.com"
# Moxfield's API sits behind Cloudflare and rejects non-browser user agents.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/130.0 Safari/537.36",
    "Origin": "https://moxfield.com",
    "Referer": "https://moxfield.com/",
}
_BOARDS = {"commanders": "commander", "mainboard": "main", "maybeboard": "considering",
           "sideboard": "sideboard", "companions": "commander"}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "deck"


class Moxfield:
    def __init__(self, http: HttpClient):
        self.http = http

    async def _get(self, path: str, **kw: Any) -> Any:
        return await self.http.get(API + path, headers=BROWSER_HEADERS, **kw)

    async def user_decks(self, username: str) -> list[dict[str, Any]]:
        decks: list[dict[str, Any]] = []
        page = 1
        while True:
            data = await self._get("/v2/decks/search", params={
                "authorUserNames": username, "pageSize": 100, "pageNumber": page,
                "sortType": "updated", "sortDirection": "descending",
            })
            decks += data.get("data", [])
            if page >= int(data.get("totalPages", 1) or 1):
                return decks
            page += 1

    async def deck(self, public_id: str) -> dict[str, Any]:
        return await self._get(f"/v3/decks/all/{public_id}")

    async def primer(self, internal_id: str) -> str:
        data = await self._get(f"/v1/decks/{internal_id}/primer", allow_404=True)
        if isinstance(data, dict):
            return data.get("content") or ""
        return data or ""


def convert_deck(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Moxfield v3 deck JSON -> (library deck, card metadata)."""
    tags: dict[str, list[str]] = raw.get("authorTags") or {}
    cards: list[list[Any]] = []
    meta: dict[str, dict[str, Any]] = {}
    commanders: list[str] = []
    for board_name, board in (raw.get("boards") or {}).items():
        target = _BOARDS.get(board_name)
        if not target or not board.get("count"):
            continue
        for entry in (board.get("cards") or {}).values():
            card = entry.get("card") or {}
            name = card.get("name")
            if not name:
                continue
            if target == "commander":
                commanders.append(name)
            cards.append([name, int(entry.get("quantity", 1)), target, tags.get(name, [])])
            usd = (card.get("prices") or {}).get("usd")
            meta[name] = {
                "type": (card.get("type_line") or "").split(" // ")[0],
                "cmc": float(card.get("cmc") or 0),
                "ci": "".join(card.get("color_identity") or []),
                "usd": round(float(usd), 2) if usd is not None else None,
            }
    deck = {
        "id": raw.get("publicId"),
        "name": (raw.get("name") or "").strip(),
        "commanders": commanders,
        "colors": "".join(raw.get("colorIdentity") or []),
        "bracket": raw.get("bracket") or raw.get("userBracket") or raw.get("autoBracket"),
        "likes": raw.get("likeCount", 0),
        "views": raw.get("viewCount", 0),
        "updated": (raw.get("lastUpdatedAtUtc") or "")[:10],
        "description": raw.get("description") or "",
        "url": raw.get("publicUrl") or f"https://moxfield.com/decks/{raw.get('publicId')}",
        "cards": cards,
    }
    return deck, meta


async def import_user(http: HttpClient, username: str, dest: Path, source_key: str | None = None,
                      include_primers: bool = True, max_decks: int = 200) -> dict[str, Any]:
    """Fetch a user's public decks and write them as library source ``dest/<source_key>/``.

    Existing hand-written notes in decks.json (per deck id) and source.json are preserved.
    """
    mox = Moxfield(http)
    listing = await mox.user_decks(username)
    key = _slug(source_key or username)
    folder = dest / key
    (folder / "primers").mkdir(parents=True, exist_ok=True)

    old_notes: dict[str, Any] = {}
    old_decks = folder / "decks.json"
    if old_decks.exists():
        for d in json.loads(old_decks.read_text()):
            old_notes[d.get("id")] = {k: d[k] for k in ("notes", "placeholder") if k in d}

    decks: list[dict[str, Any]] = []
    all_meta: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for item in listing[:max_decks]:
        if item.get("format") not in (None, "commander"):
            continue
        pid = item.get("publicId")
        try:
            raw = await mox.deck(pid)
        except ApiError as exc:
            errors.append(f"{pid}: {exc}")
            continue
        deck, meta = convert_deck(raw)
        all_meta.update(meta)
        deck.update(old_notes.get(pid, {}))
        deck.setdefault("notes", {})
        if include_primers and item.get("hasPrimer"):
            try:
                text = await mox.primer(raw.get("id"))
            except ApiError as exc:
                errors.append(f"{pid} primer: {exc}")
                text = ""
            if text.strip():
                (folder / "primers" / f"{_slug(deck['name'])[:60]}-{_slug(str(pid))}.md").write_text(
                    f"# {deck['name']}\n\nSource: {deck['url']}\n\n{text}\n")
                deck["has_primer"] = True
        decks.append(deck)

    decks.sort(key=lambda d: -(d.get("views") or 0))
    (folder / "decks.json").write_text(json.dumps(decks, ensure_ascii=False, indent=1))
    (folder / "cards.json").write_text(json.dumps(all_meta, ensure_ascii=False, indent=0, sort_keys=True))
    src_file = folder / "source.json"
    source = json.loads(src_file.read_text()) if src_file.exists() else {}
    source.setdefault("key", key)
    source.setdefault("author", username)
    source["profile_url"] = f"https://moxfield.com/users/{username}"
    src_file.write_text(json.dumps(source, ensure_ascii=False, indent=1))
    return {
        "source": key,
        "folder": str(folder),
        "decks_imported": len(decks),
        "unique_cards": len(all_meta),
        "primers_saved": sum(1 for d in decks if d.get("has_primer")),
        "errors": errors,
        "next_steps": "Read the saved primers and add principles to source.json and notes/win_lines per deck "
                      "in decks.json, then run scripts/build_library_docs.py to refresh the markdown reference.",
    }
