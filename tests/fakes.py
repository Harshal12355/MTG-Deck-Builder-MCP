"""Offline fakes for Scryfall, Commander Spellbook and EDHREC, served via httpx.MockTransport."""

from __future__ import annotations

import json
from typing import Any

import httpx

from mtg_mcp.http import HttpClient


def card(name, cost="", cmc=0, type_line="", text="", ci=(), price="1.00", produced=None, legal="legal", **extra):
    colors = sorted({c for c in "WUBRG" if f"{{{c}}}" in cost})
    d = {
        "object": "card",
        "id": f"id-{name.lower().replace(' ', '-')}",
        "oracle_id": f"oracle-{name.lower().replace(' ', '-')}",
        "name": name,
        "mana_cost": cost,
        "cmc": cmc,
        "type_line": type_line,
        "oracle_text": text,
        "colors": colors,
        "color_identity": list(ci),
        "legalities": {"commander": legal, "standard": "not_legal", "modern": legal},
        "prices": {"usd": price, "usd_foil": None},
        "rarity": "rare",
        "set": "tst",
        "set_name": "Test Set",
        "collector_number": "1",
        "scryfall_uri": f"https://scryfall.com/card/tst/1/{name}",
        "rulings_uri": f"https://api.scryfall.com/cards/id-{name.lower().replace(' ', '-')}/rulings",
    }
    if produced is not None:
        d["produced_mana"] = produced
    d.update(extra)
    return d


CARDS = {
    c["name"].lower(): c
    for c in [
        card("Atraxa, Praetors' Voice", "{G}{W}{U}{B}", 4, "Legendary Creature — Phyrexian Angel Horror",
             "Flying, vigilance, deathtouch, lifelink\nAt the beginning of your end step, proliferate.", "BGUW", "5.00"),
        card("Sol Ring", "{1}", 1, "Artifact", "{T}: Add {C}{C}.", "", "1.50", game_changer=False),
        card("Cultivate", "{2}{G}", 3, "Sorcery",
             "Search your library for up to two basic land cards, reveal those cards, put one onto the battlefield tapped and the other into your hand, then shuffle.", "G", "0.25"),
        card("Rhystic Study", "{2}{U}", 3, "Enchantment",
             "Whenever an opponent casts a spell, you may draw a card unless that player pays {1}.", "U", "40.00", game_changer=True),
        card("Swords to Plowshares", "{W}", 1, "Instant",
             "Exile target creature. Its controller gains life equal to its power.", "W", "2.00"),
        card("Wrath of God", "{2}{W}{W}", 4, "Sorcery",
             "Destroy all creatures. They can't be regenerated.", "W", "6.00"),
        card("Counterspell", "{U}{U}", 2, "Instant", "Counter target spell.", "U", "1.20"),
        card("Demonic Tutor", "{1}{B}", 2, "Sorcery",
             "Search your library for a card, put that card into your hand, then shuffle.", "B", "30.00", game_changer=True),
        card("Lightning Bolt", "{R}", 1, "Instant", "Lightning Bolt deals 3 damage to any target.", "R", "1.00"),
        card("Forest", "", 0, "Basic Land — Forest", "({T}: Add {G}.)", "G", None, produced=["G"]),
        card("Island", "", 0, "Basic Land — Island", "({T}: Add {U}.)", "U", None, produced=["U"]),
        card("Command Tower", "", 0, "Land", "{T}: Add one mana of any color in your commander's color identity.", "", "0.30",
             produced=["W", "U", "B", "R", "G"]),
        card("Doubling Season", "{4}{G}", 5, "Enchantment",
             "If an effect would create one or more tokens under your control, it creates twice that many of those tokens instead.", "G", "45.00"),
        card("Mana Crypt", "{0}", 0, "Artifact", "{T}: Add {C}{C}.", "", "180.00", legal="banned"),
    ]
}


def spellbook_response() -> dict[str, Any]:
    def variant(vid, cards, produces, identity, pop):
        return {
            "id": vid,
            "uses": [{"card": {"id": i, "name": n}, "quantity": 1, "mustBeCommander": False} for i, n in enumerate(cards)],
            "requires": [],
            "produces": [{"feature": {"id": 1, "name": p}, "quantity": 1} for p in produces],
            "identity": identity,
            "manaNeeded": "",
            "easyPrerequisites": "All permanents on the battlefield.",
            "notablePrerequisites": "",
            "description": "Step 1. Step 2.",
            "popularity": pop,
            "bracketTag": "R",
        }

    return {
        "count": 2,
        "next": None,
        "previous": None,
        "results": {
            "identity": "WUBG",
            "included": [variant("1-2", ["Sol Ring", "Rhystic Study"], ["Infinite fun"], "U", 10)],
            "includedByChangingCommanders": [],
            "almostIncluded": [
                variant("3-4", ["Doubling Season", "Cultivate"], ["Infinite tokens"], "G", 5),
                variant("5-6", ["Counterspell", "Isochron Scepter"], ["Infinite counters"], "U", 50),
            ],
            "almostIncludedByAddingColors": [],
            "almostIncludedByChangingCommanders": [],
            "almostIncludedByAddingColorsAndChangingCommanders": [],
        },
    }


EDHREC_PAGE = {
    "num_decks_avg": 40000,
    "panels": {"taglinks": [{"value": "Superfriends", "slug": "superfriends", "count": 9000}]},
    "container": {
        "json_dict": {
            "cardlists": [
                {
                    "header": "High Synergy Cards",
                    "tag": "highsynergycards",
                    "cardviews": [
                        {"name": "Doubling Season", "num_decks": 20000, "potential_decks": 40000, "synergy": 0.4},
                        {"name": "Vorinclex, Monstrous Raider", "num_decks": 18000, "potential_decks": 40000, "synergy": 0.35},
                    ],
                },
                {
                    "header": "Top Cards",
                    "tag": "topcards",
                    "cardviews": [{"name": "Sol Ring", "num_decks": 39000, "potential_decks": 40000, "synergy": 0.01}],
                },
            ]
        }
    },
}


class FakeApis:
    def __init__(self):
        self.calls: list[tuple[str, str, Any]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = request.url
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.method, str(url), body))
        assert request.headers.get("user-agent", "").startswith("mtg-deckbuilder-mcp/"), "User-Agent missing"
        host, path = url.host, url.path

        if host == "api.scryfall.com":
            if path == "/cards/collection":
                data, nf = [], []
                for ident in body["identifiers"]:
                    c = CARDS.get(ident["name"].lower())
                    (data.append(c) if c else nf.append(ident))
                return httpx.Response(200, json={"object": "list", "data": data, "not_found": nf})
            if path == "/cards/named":
                q = (url.params.get("fuzzy") or url.params.get("exact") or "").lower()
                match = CARDS.get(q) or next((c for k, c in CARDS.items() if k.startswith(q)), None)
                if match:
                    return httpx.Response(200, json=match)
                return httpx.Response(404, json={"object": "error", "status": 404, "details": f"No cards found matching “{q}”"})
            if path == "/cards/search":
                q = url.params.get("q", "")
                if q == "nothingmatches":
                    return httpx.Response(404, json={"object": "error", "status": 404, "details": "Your query didn't match any cards."})
                page = int(url.params.get("page", "1"))
                allc = list(CARDS.values())
                chunk = allc[(page - 1) * 5 : page * 5]
                has_more = page * 5 < len(allc)
                return httpx.Response(200, json={
                    "object": "list", "total_cards": len(allc), "has_more": has_more,
                    "next_page": f"https://api.scryfall.com/cards/search?q={q}&page={page + 1}" if has_more else None,
                    "data": chunk,
                })
            if path.endswith("/rulings"):
                return httpx.Response(200, json={"data": [{"source": "wotc", "published_at": "2020-01-01", "comment": "A ruling."}]})
            if path == "/cards/autocomplete":
                return httpx.Response(200, json={"data": ["Sol Ring", "Solemn Simulacrum"]})

        if host == "backend.commanderspellbook.com" and path.rstrip("/") == "/find-my-combos":
            return httpx.Response(200, json=spellbook_response())

        if host == "json.edhrec.com":
            if path == "/pages/commanders/atraxa-praetors-voice.json":
                return httpx.Response(200, json=EDHREC_PAGE)
            return httpx.Response(404, text="not found")

        return httpx.Response(404, json={"details": f"unmocked {request.method} {url}"})

    def client(self) -> HttpClient:
        return HttpClient(httpx.AsyncClient(transport=httpx.MockTransport(self.handler)), rate_limit=False)
