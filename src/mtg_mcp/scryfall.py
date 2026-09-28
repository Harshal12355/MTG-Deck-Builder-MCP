"""Scryfall API wrapper (https://scryfall.com/docs/api)."""

from __future__ import annotations

from typing import Any, Iterable

from .http import ApiError, HttpClient

BASE = "https://api.scryfall.com"

# Card data changes rarely; prices update about once a day.
CARD_TTL = 6 * 3600
SEARCH_TTL = 3600


def oracle_text(card: dict[str, Any]) -> str:
    """Oracle text including every face of a double-faced / split card."""
    if card.get("oracle_text"):
        return card["oracle_text"]
    faces = card.get("card_faces") or []
    return "\n//\n".join(f.get("oracle_text", "") for f in faces if f.get("oracle_text"))


def mana_cost(card: dict[str, Any]) -> str:
    if card.get("mana_cost"):
        return card["mana_cost"]
    faces = card.get("card_faces") or []
    return " // ".join(f.get("mana_cost", "") for f in faces if f.get("mana_cost"))


def front_type_line(card: dict[str, Any]) -> str:
    """Type line of the front face (what the card 'is' for curve/land counts)."""
    faces = card.get("card_faces") or []
    if faces and faces[0].get("type_line"):
        return faces[0]["type_line"]
    return card.get("type_line", "")


def price_usd(card: dict[str, Any]) -> float | None:
    prices = card.get("prices") or {}
    for key in ("usd", "usd_foil", "usd_etched"):
        value = prices.get(key)
        if value:
            try:
                return float(value)
            except ValueError:
                pass
    return None


def summarize_card(card: dict[str, Any], detail: str = "full") -> dict[str, Any]:
    """Trim a Scryfall card object to what a model actually needs."""
    summary: dict[str, Any] = {
        "name": card.get("name"),
        "mana_cost": mana_cost(card),
        "cmc": card.get("cmc"),
        "type_line": card.get("type_line"),
        "price_usd": price_usd(card),
    }
    if detail == "brief":
        return summary
    summary.update(
        {
            "oracle_text": oracle_text(card),
            "power": card.get("power"),
            "toughness": card.get("toughness"),
            "loyalty": card.get("loyalty"),
            "colors": card.get("colors") or sorted({c for f in card.get("card_faces", []) for c in f.get("colors", [])}),
            "color_identity": card.get("color_identity"),
            "keywords": card.get("keywords"),
            "rarity": card.get("rarity"),
            "set": card.get("set"),
            "set_name": card.get("set_name"),
            "collector_number": card.get("collector_number"),
            "legalities": {k: v for k, v in (card.get("legalities") or {}).items() if v != "not_legal"},
            "game_changer": card.get("game_changer"),
            "edhrec_rank": card.get("edhrec_rank"),
            "scryfall_uri": card.get("scryfall_uri"),
            "id": card.get("id"),
            "oracle_id": card.get("oracle_id"),
        }
    )
    return {k: v for k, v in summary.items() if v not in (None, "", [], {})}


class Scryfall:
    def __init__(self, http: HttpClient):
        self.http = http

    async def search(
        self,
        query: str,
        *,
        order: str = "edhrec",
        direction: str = "auto",
        unique: str = "cards",
        limit: int = 25,
    ) -> dict[str, Any]:
        """Run a Scryfall search, following pages until `limit` cards are collected."""
        params = {"q": query, "order": order, "dir": direction, "unique": unique}
        data = await self.http.get(f"{BASE}/cards/search", params=params, ttl=SEARCH_TTL, allow_404=True)
        if data is None:
            return {"total_cards": 0, "cards": []}
        cards = list(data.get("data", []))
        total = data.get("total_cards", len(cards))
        while len(cards) < limit and data.get("has_more") and data.get("next_page"):
            data = await self.http.get(data["next_page"], ttl=SEARCH_TTL)
            cards.extend(data.get("data", []))
        return {"total_cards": total, "cards": cards[:limit], "warnings": data.get("warnings")}

    async def named(self, name: str, *, fuzzy: bool = True, set_code: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"fuzzy" if fuzzy else "exact": name}
        if set_code:
            params["set"] = set_code
        return await self.http.get(f"{BASE}/cards/named", params=params, ttl=CARD_TTL)

    async def by_id(self, card_id: str) -> dict[str, Any]:
        return await self.http.get(f"{BASE}/cards/{card_id}", ttl=CARD_TTL)

    async def rulings(self, card: dict[str, Any]) -> list[dict[str, Any]]:
        url = card.get("rulings_uri") or f"{BASE}/cards/{card['id']}/rulings"
        data = await self.http.get(url, ttl=CARD_TTL)
        return data.get("data", [])

    async def autocomplete(self, text: str) -> list[str]:
        data = await self.http.get(f"{BASE}/cards/autocomplete", params={"q": text}, ttl=CARD_TTL)
        return data.get("data", [])

    async def random(self, query: str | None = None) -> dict[str, Any]:
        params = {"q": query} if query else None
        return await self.http.get(f"{BASE}/cards/random", params=params)

    async def printings(self, card: dict[str, Any], limit: int = 100) -> list[dict[str, Any]]:
        oracle_id = card.get("oracle_id") or (card.get("card_faces") or [{}])[0].get("oracle_id")
        query = f"oracleid:{oracle_id}" if oracle_id else f'!"{card["name"]}"'
        result = await self.search(query, order="usd", direction="asc", unique="prints", limit=limit)
        return result["cards"]

    async def collection(self, names: Iterable[str]) -> tuple[dict[str, dict[str, Any]], list[str]]:
        """Fetch many cards by name via /cards/collection (75 per request).

        Returns ({requested_name_lower: card}, [names not found]).
        """
        unique: list[str] = []
        seen: set[str] = set()
        for n in names:
            key = n.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(n.strip())

        found: dict[str, dict[str, Any]] = {}
        not_found: list[str] = []
        for i in range(0, len(unique), 75):
            chunk = unique[i : i + 75]
            data = await self.http.post(
                f"{BASE}/cards/collection",
                {"identifiers": [{"name": n} for n in chunk]},
                ttl=CARD_TTL,
            )
            cards = data.get("data", [])
            missing = {(m.get("name") or "").lower() for m in data.get("not_found", [])}
            # Scryfall returns found cards in request order, skipping the missing ones.
            remaining = [n for n in chunk if n.lower() not in missing]
            by_name = _index_by_names(cards)
            for requested in remaining:
                card = by_name.get(requested.lower())
                if card is None and cards:
                    # Fall back to positional match if the name differs (e.g. accents).
                    card = cards[remaining.index(requested)] if remaining.index(requested) < len(cards) else None
                if card is None:
                    not_found.append(requested)
                else:
                    found[requested.lower()] = card
            not_found.extend(n for n in chunk if n.lower() in missing)
        return found, not_found


def _index_by_names(cards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for card in cards:
        names = [card.get("name", "")]
        names += [f.get("name", "") for f in card.get("card_faces") or []]
        for n in names:
            if n:
                index.setdefault(n.lower(), card)
    return index


__all__ = ["Scryfall", "ApiError", "summarize_card", "oracle_text", "front_type_line", "price_usd", "mana_cost"]
