"""EDHREC recommendations.

EDHREC has no official public API. Its site loads data from static JSON pages
at json.edhrec.com; this module reads those politely (slow rate limit, long
cache). Treat it as best-effort: page shapes can change without notice, and a
public app built on this should get EDHREC's permission first.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .http import HttpClient

BASE = "https://json.edhrec.com/pages"
TTL = 24 * 3600


def slugify(name: str) -> str:
    """Match EDHREC's URL slugs: 'Atraxa, Praetors' Voice' -> 'atraxa-praetors-voice'."""
    name = name.split(" // ")[0]  # double-faced commanders use the front face
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = name.lower().replace("'", "").replace("+", "plus-")
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")


def partner_slug(names: list[str]) -> str:
    # EDHREC orders partner pairs alphabetically by slug.
    return "-".join(sorted(slugify(n) for n in names))


def _cardlists(page: dict[str, Any]) -> list[dict[str, Any]]:
    container = page.get("container") or {}
    json_dict = container.get("json_dict") or {}
    return json_dict.get("cardlists") or []


def _summarize_cardview(cv: dict[str, Any]) -> dict[str, Any]:
    num = cv.get("num_decks")
    potential = cv.get("potential_decks")
    out: dict[str, Any] = {"name": cv.get("name")}
    if num is not None and potential:
        out["inclusion_pct"] = round(100 * num / potential, 1)
    elif cv.get("inclusion") is not None and potential:
        out["inclusion_pct"] = round(100 * cv["inclusion"] / potential, 1)
    if cv.get("synergy") is not None:
        out["synergy_pct"] = round(100 * cv["synergy"], 1)
    if num is not None:
        out["num_decks"] = num
    return out


class Edhrec:
    def __init__(self, http: HttpClient):
        self.http = http

    async def _page(self, path: str) -> dict[str, Any] | None:
        return await self.http.get(f"{BASE}/{path}.json", ttl=TTL, allow_404=True)

    async def commander(
        self,
        commanders: list[str],
        *,
        theme: str | None = None,
        budget: str | None = None,
        exclude: set[str] | None = None,
        per_list: int = 15,
        categories: list[str] | None = None,
    ) -> dict[str, Any]:
        slug = partner_slug(commanders) if len(commanders) > 1 else slugify(commanders[0])
        path = f"commanders/{slug}"
        if theme:
            path += f"/{slugify(theme)}"
        if budget in {"budget", "expensive"}:
            path += f"/{budget}"
        page = await self._page(path)
        if page is None:
            return {
                "error": f"EDHREC has no page at {path}. Check the commander name/theme spelling.",
                "slug": slug,
            }
        exclude = {x.lower() for x in (exclude or set())}
        wanted = {c.lower() for c in categories} if categories else None
        lists: dict[str, Any] = {}
        for cl in _cardlists(page):
            header = cl.get("header") or cl.get("tag") or "cards"
            tag = (cl.get("tag") or "").lower()
            if wanted and tag not in wanted and header.lower() not in wanted:
                continue
            views = [cv for cv in cl.get("cardviews") or [] if (cv.get("name") or "").lower() not in exclude]
            if views:
                lists[header] = [_summarize_cardview(cv) for cv in views[:per_list]]

        themes = [
            {"theme": t.get("value") or t.get("slug"), "decks": t.get("count")}
            for t in (page.get("panels") or {}).get("taglinks", [])[:20]
        ]
        return {
            "commander": commanders,
            "page": f"https://edhrec.com/{path}",
            "num_decks": page.get("num_decks_avg") or (page.get("container") or {}).get("json_dict", {}).get("card", {}).get("num_decks"),
            "themes": themes or None,
            "recommendations": lists,
            "excluded_cards_already_in_deck": len(exclude) or None,
            "source": "EDHREC (unofficial JSON; best-effort)",
        }

    async def card(self, name: str) -> dict[str, Any]:
        page = await self._page(f"cards/{slugify(name)}")
        if page is None:
            return {"error": f"EDHREC has no card page for {name}."}
        lists = {}
        for cl in _cardlists(page):
            header = cl.get("header") or cl.get("tag") or "cards"
            lists[header] = [_summarize_cardview(cv) for cv in (cl.get("cardviews") or [])[:10]]
        return {
            "card": name,
            "page": f"https://edhrec.com/cards/{slugify(name)}",
            "lists": lists,
            "source": "EDHREC (unofficial JSON; best-effort)",
        }
