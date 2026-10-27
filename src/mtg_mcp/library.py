"""Reference library: real, tested decklists from builders we learn from, with their card choices,
tags, primers' principles and win lines, queryable by role, colour and price.

Data lives in ``data/library/<source>/`` (one folder per builder):

- ``source.json``  who the builder is, their principles and rules of thumb
- ``decks.json``   every deck: metadata, notes/win lines, and cards ``[name, qty, board, tags]``
- ``cards.json``   card metadata at capture time: type line, mana value, colour identity, USD price

Set ``MTG_MCP_LIBRARY_DIR`` to keep the library somewhere else (e.g. outside site-packages).
New sources can be added or refreshed with the ``moxfield_import_user`` tool.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

PACKAGE_DIR = Path(__file__).resolve().parent / "data" / "library"

# Canonical roles. Builders' own tags are mapped onto these; anything else is kept as a theme tag.
ROLES = [
    "ramp", "draw", "tutor", "counter", "removal", "wipe", "protection", "stax",
    "combo", "recursion", "untap", "clone", "tokens", "evasion", "land",
]

# Builder roles map 1:1 to analysis.roles heuristic names except draw->card_draw, counter->counterspell, wipe->board_wipe.
ROLE_TO_ANALYSIS_ROLE = {
    "ramp": "ramp",
    "draw": "card_draw",
    "tutor": "tutor",
    "counter": "counterspell",
    "removal": "removal",
    "wipe": "board_wipe",
    "protection": "protection",
    "recursion": "recursion",
}

_TAG_TO_ROLE = {
    "ramp": "ramp", "mana": "ramp", "land ramp": "ramp", "extra land drops": "ramp", "land tutors": "ramp", "land-tutor": "ramp",
    "draw": "draw", "card draw": "draw", "card_draw": "draw", "card advantage": "draw", "t2 flip": "draw",
    "tutor": "tutor", "tutors": "tutor",
    "counter": "counter", "counterspell": "counter", "counterspells": "counter",
    "removal": "removal", "targeted disruption": "removal", "edict": "removal", "burn": "removal",
    "wipe": "wipe", "board wipe": "wipe", "board_wipe": "wipe", "boardwipe": "wipe", "mass disruption": "wipe",
    "protection": "protection",
    "stax": "stax", "hate": "stax", "rule of law": "stax", "etb hate": "stax", "active hate": "stax",
    "cost up": "stax", "tutor hate": "stax", "cast hate": "stax",
    "combo": "combo", "gifts pile": "combo", "breach": "combo",
    "recursion": "recursion",
    "untap": "untap",
    "clone": "clone", "copy": "clone", "legend clone": "clone",
    "tokens": "tokens",
    "evasion": "evasion",
    "lands": "land", "land...duh": "land",
}

_BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}


def library_dir() -> Path:
    env = os.environ.get("MTG_MCP_LIBRARY_DIR")
    return Path(env).expanduser() if env else PACKAGE_DIR


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def _front(name: str) -> str:
    return name.split(" // ")[0]


def normalize_tags(tags: Iterable[str]) -> tuple[list[str], list[str]]:
    """Split a builder's tags into (canonical roles, other theme tags)."""
    roles: list[str] = []
    themes: list[str] = []
    for t in tags:
        key = t.strip().lower()
        role = _TAG_TO_ROLE.get(key)
        if role:
            if role not in roles:
                roles.append(role)
        elif key and key not in themes:
            themes.append(key)
    return roles, themes


def _type_roles(type_line: str) -> list[str]:
    return ["land"] if "Land" in type_line.split(" — ")[0] else []


def _color_subset(card_ci: str, identity: str) -> bool:
    return set(card_ci) <= set(identity.upper())


class Library:
    def __init__(self, root: Path | None = None):
        self.root = root or library_dir()
        self.sources: dict[str, dict[str, Any]] = {}
        self.decks: list[dict[str, Any]] = []
        self.cards: dict[str, dict[str, Any]] = {}
        self._load()
        self._index()

    # ------------------------------------------------------------------ loading
    def _load(self) -> None:
        if not self.root.exists():
            return
        for folder in sorted(p for p in self.root.iterdir() if p.is_dir()):
            src_file, decks_file, cards_file = folder / "source.json", folder / "decks.json", folder / "cards.json"
            if not decks_file.exists():
                continue
            source = json.loads(src_file.read_text()) if src_file.exists() else {"key": folder.name}
            source.setdefault("key", folder.name)
            self.sources[source["key"]] = source
            for deck in json.loads(decks_file.read_text()):
                deck["source"] = source["key"]
                self.decks.append(deck)
            if cards_file.exists():
                for name, meta in json.loads(cards_file.read_text()).items():
                    self.cards.setdefault(name, meta)

    def _index(self) -> None:
        self._by_norm = {_norm(n): n for n in self.cards}
        for n in list(self.cards):
            self._by_norm.setdefault(_norm(_front(n)), n)
        usage: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "decks": [], "considering": [], "roles": Counter(), "themes": Counter(), "as_commander": [],
        })
        for deck in self.decks:
            if deck.get("placeholder"):
                continue
            label = deck_label(deck)
            for name, qty, board, tags in deck["cards"]:
                u = usage[name]
                roles, themes = normalize_tags(tags)
                if not roles:
                    roles = _type_roles(self.cards.get(name, {}).get("type", ""))
                if board == "considering":
                    u["considering"].append(label)
                    continue
                if board == "commander":
                    u["as_commander"].append(label)
                u["decks"].append(label)
                u["roles"].update(roles)
                u["themes"].update(themes)
        self.usage = dict(usage)

    # ------------------------------------------------------------------ helpers
    def resolve_card(self, name: str) -> str | None:
        if name in self.cards:
            return name
        return self._by_norm.get(_norm(name)) or self._by_norm.get(_norm(_front(name)))

    def card_entry(self, name: str) -> dict[str, Any]:
        meta = self.cards.get(name, {})
        u = self.usage.get(name, {})
        roles = [r for r, _ in u.get("roles", Counter()).most_common()] if u else []
        return {
            "name": name,
            "type": meta.get("type"),
            "mana_value": meta.get("cmc"),
            "color_identity": meta.get("ci", ""),
            "usd_at_capture": meta.get("usd"),
            "deck_count": len(u.get("decks", [])),
            "roles": roles,
            "themes": [t for t, _ in u.get("themes", Counter()).most_common(5)] if u else [],
            "decks": u.get("decks", []),
            "considering_in": u.get("considering", []),
            "commander_of": u.get("as_commander", []),
        }

    def active_decks(self) -> list[dict[str, Any]]:
        return [d for d in self.decks if not d.get("placeholder")]

    def find_decks(self, query: str) -> list[dict[str, Any]]:
        q = _norm(query)
        hits = []
        for d in self.decks:
            hay = " ".join([d.get("id", ""), d.get("name", ""), d.get("notes", {}).get("short", ""),
                            " ".join(d.get("commanders", []))])
            if d.get("id") == query or q in _norm(hay):
                hits.append(d)
        return hits

    # ------------------------------------------------------------------ queries
    def search_cards(
        self,
        role: str | None = None,
        color_identity: str | None = None,
        min_decks: int = 1,
        max_price: float | None = None,
        max_mana_value: float | None = None,
        query: str | None = None,
        theme: str | None = None,
        include_lands: bool = True,
        include_basics: bool = False,
        sort: str = "decks",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        role = role.lower() if role else None
        theme = theme.lower() if theme else None
        q = _norm(query) if query else None
        out = []
        for name, u in self.usage.items():
            if not u["decks"]:
                continue
            meta = self.cards.get(name, {})
            if not include_basics and name in _BASICS:
                continue
            if len(u["decks"]) < min_decks:
                continue
            if role and role not in u["roles"]:
                continue
            if theme and not any(theme in t for t in u["themes"]):
                continue
            is_land = "Land" in meta.get("type", "").split(" — ")[0]
            if not include_lands and is_land:
                continue
            if color_identity is not None and not _color_subset(meta.get("ci", ""), color_identity):
                continue
            price = meta.get("usd")
            if max_price is not None and price is not None and price > max_price:
                continue
            if max_mana_value is not None and (meta.get("cmc") or 0) > max_mana_value:
                continue
            if q and q not in _norm(name) and q not in _norm(meta.get("type", "")):
                continue
            out.append(self.card_entry(name))
        if sort == "price":
            out.sort(key=lambda c: (c["usd_at_capture"] is None, c["usd_at_capture"] or 0, -c["deck_count"]))
        elif sort == "mana_value":
            out.sort(key=lambda c: (c["mana_value"] or 0, -c["deck_count"], c["name"]))
        else:
            out.sort(key=lambda c: (-c["deck_count"], c["name"]))
        return out[:limit]

    def deck_stats(self, deck: dict[str, Any]) -> dict[str, Any]:
        main = [(n, q) for n, q, b, _ in deck["cards"] if b in ("main", "commander")]
        lands = sum(q for n, q in main if "Land" in self.cards.get(n, {}).get("type", "").split(" — ")[0])
        nonland = [(n, q) for n, q in main if "Land" not in self.cards.get(n, {}).get("type", "").split(" — ")[0]]
        mv_total = sum((self.cards.get(n, {}).get("cmc") or 0) * q for n, q in nonland)
        mv_count = sum(q for _, q in nonland)
        roles: Counter[str] = Counter()
        for n, q, b, tags in deck["cards"]:
            if b != "main":
                continue
            rs, _ = normalize_tags(tags)
            roles.update(rs)
        price = sum((self.cards.get(n, {}).get("usd") or 0) * q for n, q in main
                    if n not in _BASICS)
        return {
            "cards": sum(q for _, q in main),
            "lands": lands,
            "average_mana_value_nonland": round(mv_total / mv_count, 2) if mv_count else None,
            "tagged_role_counts": dict(roles.most_common()),
            "price_usd_at_capture_excl_basics": round(price, 2),
        }

    def compare(self, deck_names: Iterable[str], color_identity: str, min_decks: int = 3,
                max_price: float | None = None, limit: int = 40) -> dict[str, Any]:
        have = {self.resolve_card(n) or n for n in deck_names}
        staples = self.search_cards(color_identity=color_identity, min_decks=min_decks, max_price=max_price,
                                    include_lands=True, limit=1000)
        missing = [c for c in staples if c["name"] not in have]
        by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for c in missing:
            by_role[c["roles"][0] if c["roles"] else "other"].append(
                {k: c[k] for k in ("name", "deck_count", "mana_value", "usd_at_capture", "roles")})
        in_library = [n for n in have if n in self.usage and self.usage[n]["decks"]]
        return {
            "color_identity": color_identity,
            "missing_staples_by_role": {r: v[:limit] for r, v in sorted(by_role.items(), key=lambda kv: -len(kv[1]))},
            "already_shared_with_library": len(in_library),
            "not_in_library": sorted(n for n in have if n not in self.usage and n not in _BASICS),
        }


def deck_label(deck: dict[str, Any]) -> str:
    short = deck.get("notes", {}).get("short")
    return short or " + ".join(deck.get("commanders", [])) or deck.get("name", deck.get("id", "?"))


def decklist_text(deck: dict[str, Any], include_considering: bool = False) -> str:
    """Moxfield-style plain export: mainboard, blank line, commander(s)."""
    main = [f"{q} {n}" for n, q, b, _ in deck["cards"] if b == "main"]
    cmd = [f"{q} {n}" for n, q, b, _ in deck["cards"] if b == "commander"]
    text = "\n".join(main) + "\n\n" + "\n".join(cmd) + "\n"
    if include_considering:
        maybe = [f"{q} {n}" for n, q, b, _ in deck["cards"] if b == "considering"]
        if maybe:
            text += "\n// Considering\n" + "\n".join(maybe) + "\n"
    return text


@lru_cache(maxsize=1)
def get_library() -> Library:
    return Library()


def reload_library() -> Library:
    get_library.cache_clear()
    return get_library()
