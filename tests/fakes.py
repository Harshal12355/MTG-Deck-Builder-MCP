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


# Universes Beyond / Secret Lair "flavor names": /cards/named matches them,
# /cards/collection does not (mirrors the real Scryfall API).
FLAVOR_NAMES = {
    "thrum of the vestige": "lightning bolt",
    "s.h.i.e.l.d. spy satellite": "sol ring",
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


def archidekt_card(name, qty=1, cats=("Uncategorized",), cmc=0, types=("Instant",), tcg=1.0):
    return {
        "quantity": qty,
        "categories": list(cats),
        "deletedAt": None,
        "card": {
            "prices": {"tcg": tcg, "ck": tcg + 0.5},
            "edition": {"editioncode": "tst"},
            "oracleCard": {"name": name, "cmc": cmc, "types": list(types), "colorIdentity": []},
        },
    }


def archidekt_deck(deck_id, commander="Atraxa, Praetors' Voice", extra=()):
    filler = [archidekt_card(f"Filler Card {i}", cats=("Plan",)) for i in range(45)]
    return {
        "id": deck_id,
        "name": f"Deck {deck_id}",
        "deckFormat": 3,
        "edhBracket": 3,
        "viewCount": 1000 - deck_id,
        "owner": {"username": "tester"},
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": "2026-01-02T00:00:00Z",
        "description": "A test deck.",
        "categories": [
            {"name": "Commander", "includedInDeck": True, "isPremier": True},
            {"name": "Ramp", "includedInDeck": True},
            {"name": "Maybeboard", "includedInDeck": False},
            {"name": "Sideboard", "includedInDeck": False},
        ],
        "cards": [
            archidekt_card(commander, cats=("Commander",), cmc=4, types=("Creature",), tcg=5.0),
            archidekt_card("Sol Ring", cats=("Ramp",), cmc=1, types=("Artifact",), tcg=1.5),
            archidekt_card("Forest", qty=20, cats=("Land",), types=("Land",), tcg=0),
            archidekt_card("Doubling Season", cats=("Maybeboard",), cmc=5, types=("Enchantment",), tcg=45.0),
            *[archidekt_card(n, cats=c) for n, c in extra],
            *filler,
        ],
    }


ARCHIDEKT_DECKS = {
    1: archidekt_deck(1, extra=[("Rhystic Study", ("Draw",))]),
    2: archidekt_deck(2, extra=[("Rhystic Study", ("Card Advantage", "Draw"))]),
    3: archidekt_deck(3, commander="Some Other Commander"),
}


def archidekt_search(params) -> dict[str, Any]:
    results = [
        {"id": i, "name": d["name"], "deckFormat": 3, "size": 100, "viewCount": d["viewCount"],
         "edhBracket": 3, "owner": {"username": "tester"}, "colors": {"W": 1, "U": 2, "B": 0, "R": 0, "G": 3},
         "tags": [], "private": False, "updatedAt": d["updatedAt"]}
        for i, d in ARCHIDEKT_DECKS.items()
    ]
    results.append({"id": 99, "name": "Modern deck", "deckFormat": 2, "viewCount": 5, "owner": {"username": "x"}})
    return {"count": len(results), "next": None, "results": results}


def moxfield_card(name, type_line="Instant", cmc=1, ci=(), usd=1.0):
    return {"name": name, "type_line": type_line, "cmc": cmc, "color_identity": list(ci), "prices": {"usd": usd}}


MOXFIELD_DECK = {
    "id": "int123", "publicId": "PUB1", "name": "Test Deck ", "publicUrl": "https://moxfield.com/decks/PUB1",
    "description": "desc", "likeCount": 3, "viewCount": 99, "lastUpdatedAtUtc": "2026-10-01T00:00:00Z",
    "colorIdentity": ["U", "B"], "bracket": 4,
    "authorTags": {"Counterspell": ["counter"], "Sol Ring": ["ramp"]},
    "boards": {
        "commanders": {"count": 1, "cards": {"a": {"quantity": 1, "card": moxfield_card(
            "Vren, the Relentless", "Legendary Creature — Rat Rogue", 4, "UB")}}},
        "mainboard": {"count": 3, "cards": {
            "b": {"quantity": 1, "card": moxfield_card("Counterspell", ci="U", cmc=2)},
            "c": {"quantity": 1, "card": moxfield_card("Sol Ring", "Artifact", 1)},
            "d": {"quantity": 1, "card": moxfield_card("Island", "Basic Land — Island", 0, "U", 0.2)},
        }},
        "maybeboard": {"count": 1, "cards": {"e": {"quantity": 1, "card": moxfield_card("Negate", ci="U")}}},
        "tokens": {"count": 0, "cards": {}},
    },
}


def moxfield_route(request: httpx.Request) -> httpx.Response:
    ua = request.headers.get("user-agent", "")
    assert ua.startswith("Mozilla/"), "Moxfield needs a browser user agent"
    path = request.url.path
    if path == "/v2/decks/search":
        return httpx.Response(200, json={"totalPages": 1, "data": [
            {"publicId": "PUB1", "format": "commander", "hasPrimer": True},
            {"publicId": "PUB2", "format": "modern", "hasPrimer": False},
        ]})
    if path == "/v3/decks/all/PUB1":
        return httpx.Response(200, json=MOXFIELD_DECK)
    if path == "/v1/decks/int123/primer":
        return httpx.Response(200, json={"content": "## Plan\nCounter everything."})
    return httpx.Response(404, json={"details": "unmocked"})


class FakeApis:
    def __init__(self):
        self.calls: list[tuple[str, str, Any]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = request.url
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.method, str(url), body))
        host, path = url.host, url.path
        if host == "api2.moxfield.com":
            return moxfield_route(request)
        assert request.headers.get("user-agent", "").startswith("mtg-deckbuilder-mcp/"), "User-Agent missing"

        if host == "api.scryfall.com":
            if path == "/cards/collection":
                data, nf = [], []
                for ident in body["identifiers"]:
                    c = CARDS.get(ident["name"].lower())
                    (data.append(c) if c else nf.append(ident))
                return httpx.Response(200, json={"object": "list", "data": data, "not_found": nf})
            if path == "/cards/named":
                q = (url.params.get("fuzzy") or url.params.get("exact") or "").lower()
                match = CARDS.get(q) or CARDS.get(FLAVOR_NAMES.get(q, ""))
                if match is None and "fuzzy" in url.params:
                    match = next((c for k, c in CARDS.items() if k.startswith(q)), None)
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

        if host == "archidekt.com":
            if path == "/api/decks/v3/":
                return httpx.Response(200, json=archidekt_search(dict(url.params)))
            m = path.strip("/").split("/")
            if len(m) == 3 and m[:2] == ["api", "decks"] and m[2].isdigit():
                deck = ARCHIDEKT_DECKS.get(int(m[2]))
                return httpx.Response(200, json=deck) if deck else httpx.Response(404, json={"detail": "Not found."})

        if host == "raw.githubusercontent.com":
            if path.endswith("/a/atraxa_praetors_voice.txt"):
                return httpx.Response(
                    200,
                    text=(
                        "Name:Atraxa, Praetors' Voice\n"
                        "T:Mode$ Phase | Phase$ End of Turn | Execute$ TrigProliferate\n"
                        "SVar:TrigProliferate:DB$ Proliferate\n"
                        "DeckHas:Ability$Proliferate & Ability$Counters\n"
                        "DeckNeeds:Ability$Counters\n"
                    ),
                )
            return httpx.Response(404, text="not found")

        return httpx.Response(404, json={"details": f"unmocked {request.method} {url}"})

    def client(self) -> HttpClient:
        return HttpClient(httpx.AsyncClient(transport=httpx.MockTransport(self.handler)), rate_limit=False)
