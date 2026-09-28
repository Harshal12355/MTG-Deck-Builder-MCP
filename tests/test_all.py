"""Offline tests. Run with:  python -m unittest discover -s tests -v"""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakes import CARDS, FakeApis  # noqa: E402
from mtg_mcp import server  # noqa: E402
from mtg_mcp.analysis import analyze, card_roles  # noqa: E402
from mtg_mcp.decklist import parse_decklist  # noqa: E402
from mtg_mcp.edhrec import partner_slug, slugify  # noqa: E402


def run(coro):
    return asyncio.run(coro)


# A legal-sized Atraxa list built from the fake card pool.
def atraxa_list(fmt="moxfield"):
    body = [
        "1 Sol Ring", "1 Cultivate", "1 Rhystic Study", "1 Swords to Plowshares", "1 Wrath of God",
        "1 Counterspell", "1 Demonic Tutor", "1 Doubling Season", "1 Command Tower",
        "45 Forest", "45 Island",
    ]
    if fmt == "moxfield":  # Moxfield plain export: commander alone after a blank line
        return "\n".join(body) + "\n\n1 Atraxa, Praetors' Voice\n"
    if fmt == "arena":
        return "Commander\n1 Atraxa, Praetors' Voice (ONE) 190\n\nDeck\n" + "\n".join(b + " (TST) 1" for b in body)
    if fmt == "archidekt":
        return "1x Atraxa, Praetors' Voice (2x2) 190 [Commander{top}]\n" + "\n".join(
            b.replace(" ", "x ", 1) + " [Ramp]" for b in body)
    raise ValueError(fmt)


class ParserTests(unittest.TestCase):
    def test_moxfield_trailing_commander(self):
        d = parse_decklist(atraxa_list("moxfield"))
        self.assertEqual([e.name for e in d.commanders], ["Atraxa, Praetors' Voice"])
        self.assertEqual(d.card_count, 100)

    def test_arena_sections_and_printing(self):
        d = parse_decklist(atraxa_list("arena"))
        self.assertEqual(d.commanders[0].name, "Atraxa, Praetors' Voice")
        self.assertEqual(d.commanders[0].set_code, "one")
        self.assertEqual(d.card_count, 100)

    def test_archidekt_categories(self):
        d = parse_decklist(atraxa_list("archidekt"))
        self.assertEqual(d.commanders[0].name, "Atraxa, Praetors' Voice")
        self.assertIn("Ramp", d.main[0].categories)
        self.assertEqual(d.card_count, 100)

    def test_misc_markers(self):
        text = """// Commander
1 Atraxa, Praetors' Voice *CMDR*
// Main
1x Sol Ring (C21) 263 *F*
Lightning Bolt
2 Counterspell #!Interaction
SIDEBOARD:
1 Forest
Maybeboard
1 Mana Crypt
"""
        d = parse_decklist(text)
        self.assertEqual([e.name for e in d.commanders], ["Atraxa, Praetors' Voice"])
        self.assertEqual([(e.name, e.quantity) for e in d.main], [("Sol Ring", 1), ("Lightning Bolt", 1), ("Counterspell", 2)])
        self.assertEqual(d.main[0].set_code, "c21")
        self.assertEqual([e.name for e in d.sideboard], ["Forest"])
        self.assertEqual([e.name for e in d.maybe], ["Mana Crypt"])

    def test_blank_lines_as_grouping_stay_main(self):
        d = parse_decklist("1 Sol Ring\n\n1 Counterspell\n\n1 Forest\n")
        self.assertEqual(len(d.main), 3)
        self.assertEqual(d.commanders, [])

    def test_explicit_commander(self):
        d = parse_decklist("1 Atraxa, Praetors' Voice\n1 Sol Ring", commanders=["Atraxa, Praetors' Voice"])
        self.assertEqual([e.name for e in d.commanders], ["Atraxa, Praetors' Voice"])
        self.assertEqual([e.name for e in d.main], ["Sol Ring"])

    def test_arena_about_block(self):
        d = parse_decklist("About\nName My Deck\n\nDeck\n4 Lightning Bolt\n")
        self.assertEqual([(e.name, e.quantity) for e in d.main], [("Lightning Bolt", 4)])


class RoleTests(unittest.TestCase):
    def roles(self, name):
        return card_roles(CARDS[name.lower()])

    def test_roles(self):
        self.assertIn("ramp", self.roles("Sol Ring"))
        self.assertIn("ramp", self.roles("Cultivate"))
        self.assertNotIn("tutor", self.roles("Cultivate"))
        self.assertIn("card_draw", self.roles("Rhystic Study"))
        self.assertIn("removal", self.roles("Swords to Plowshares"))
        self.assertIn("board_wipe", self.roles("Wrath of God"))
        self.assertNotIn("removal", self.roles("Wrath of God"))
        self.assertIn("counterspell", self.roles("Counterspell"))
        self.assertIn("tutor", self.roles("Demonic Tutor"))
        self.assertIn("removal", self.roles("Lightning Bolt"))
        self.assertEqual(self.roles("Forest"), [])


class AnalysisTests(unittest.TestCase):
    def test_legal_commander_deck(self):
        d = parse_decklist(atraxa_list())
        r = analyze(d, CARDS)
        self.assertTrue(r["legal"], r["legality_issues"])
        self.assertEqual(r["color_identity"], "WUBG")
        self.assertEqual(r["lands"], 91)
        self.assertEqual(r["land_color_sources"]["G"], 46)
        self.assertEqual(r["game_changers"], ["Demonic Tutor", "Rhystic Study"])
        self.assertEqual(r["price"]["most_expensive"][0], {"card": "Doubling Season", "usd": 45.0})
        self.assertTrue(any(g.startswith("lands: 91") for g in r["gaps_vs_typical_commander_deck"]))

    def test_illegal_things_flagged(self):
        text = "1 Atraxa, Praetors' Voice *CMDR*\n2 Sol Ring\n1 Lightning Bolt\n1 Mana Crypt\n"
        r = analyze(parse_decklist(text), CARDS)
        issues = " | ".join(r["legality_issues"])
        self.assertFalse(r["legal"])
        self.assertIn("exactly 100", issues)
        self.assertIn("Lightning Bolt is outside", issues)
        self.assertIn("2 copies of Sol Ring", issues)
        self.assertIn("Mana Crypt (banned)", issues)

    def test_basics_unlimited_and_budget(self):
        r = analyze(parse_decklist(atraxa_list()), CARDS, budget_per_card=20)
        self.assertFalse(any("Forest" in i for i in r["legality_issues"]))
        self.assertEqual({x["card"] for x in r["price"]["over_budget"]}, {"Rhystic Study", "Demonic Tutor", "Doubling Season"})


class SlugTests(unittest.TestCase):
    def test_slugs(self):
        self.assertEqual(slugify("Atraxa, Praetors' Voice"), "atraxa-praetors-voice")
        self.assertEqual(slugify("Jötun Grunt"), "jotun-grunt")
        self.assertEqual(slugify("Esika, God of the Tree // The Prismatic Bridge"), "esika-god-of-the-tree")
        self.assertEqual(partner_slug(["Tymna the Weaver", "Kraum, Ludevic's Opus"]), "kraum-ludevics-opus-tymna-the-weaver")


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeApis()
        server.set_http_client(self.fake.client())

    def test_analyze_deck_tool(self):
        r = run(server.analyze_deck(atraxa_list()))
        self.assertEqual(r["commanders"], ["Atraxa, Praetors' Voice"])
        self.assertIsNone(r["cards_not_found"])
        # 11 unique names in one /cards/collection batch
        posts = [c for c in self.fake.calls if c[0] == "POST"]
        self.assertEqual(len(posts), 1)

    def test_analyze_reports_unknown_cards(self):
        r = run(server.analyze_deck("1 Sol Ring\n1 Not A Real Card"))
        self.assertEqual(r["cards_not_found"], ["Not A Real Card"])

    def test_collection_batches_of_75(self):
        text = "\n".join(f"1 Fake Card {i}" for i in range(160))
        run(server.price_decklist(text))
        posts = [c for c in self.fake.calls if c[0] == "POST"]
        self.assertEqual([len(p[2]["identifiers"]) for p in posts], [75, 75, 10])

    def test_search_paginates_and_trims(self):
        r = run(server.search_cards("f:commander", limit=12))
        self.assertEqual(r["returned"], 12)
        self.assertEqual(r["total_matches"], len(CARDS))
        self.assertNotIn("oracle_text", r["cards"][0])

    def test_search_no_results(self):
        r = run(server.search_cards("nothingmatches"))
        self.assertEqual(r["total_matches"], 0)

    def test_get_card_and_error(self):
        r = run(server.get_card("rhystic"))
        self.assertEqual(r["name"], "Rhystic Study")
        self.assertIn("card_draw", r["roles"])
        err = run(server.get_card("zzzz"))
        self.assertEqual(err["status"], 404)
        self.assertIn("No cards found", err["error"])

    def test_rulings(self):
        r = run(server.get_card_rulings("Sol Ring"))
        self.assertEqual(r["rulings"][0]["text"], "A ruling.")

    def test_find_combos(self):
        r = run(server.find_combos(atraxa_list()))
        self.assertEqual(r["in_deck"]["total"], 1)
        almost = r["one_card_away"]["combos"]
        self.assertEqual(almost[0]["id"], "5-6")  # most popular first
        self.assertEqual(almost[0]["missing"], ["Isochron Scepter"])
        body = next(c[2] for c in self.fake.calls if "find-my-combos" in c[1])
        self.assertEqual(body["commanders"], [{"card": "Atraxa, Praetors' Voice", "quantity": 1}])
        self.assertEqual(len(body["main"]), 11)

    def test_edhrec_excludes_cards_in_deck(self):
        r = run(server.edhrec_recommendations("atraxa", decklist=atraxa_list()))
        high = r["recommendations"]["High Synergy Cards"]
        self.assertEqual([c["name"] for c in high], ["Vorinclex, Monstrous Raider"])
        self.assertEqual(high[0]["inclusion_pct"], 45.0)
        self.assertEqual(high[0]["synergy_pct"], 35.0)
        self.assertNotIn("Top Cards", r["recommendations"])  # Sol Ring removed -> list empty
        self.assertEqual(r["themes"][0]["theme"], "Superfriends")

    def test_edhrec_missing_page(self):
        r = run(server.edhrec_recommendations("Sol Ring"))
        self.assertIn("no page", r["error"])


class McpProtocolTest(unittest.TestCase):
    """Start the real server over stdio and list its tools."""

    def test_list_tools(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        src = str(Path(__file__).resolve().parents[1] / "src")

        async def go():
            params = StdioServerParameters(command=sys.executable, args=["-m", "mtg_mcp.server"], env={"PYTHONPATH": src})
            async with stdio_client(params) as (r, w):
                async with ClientSession(r, w) as s:
                    init = await s.initialize()
                    tools = await s.list_tools()
                    return init, [t.name for t in tools.tools]

        init, names = run(go())
        self.assertEqual(init.serverInfo.name, "mtg-deckbuilder")
        self.assertIn("Never answer card text from memory", init.instructions)
        self.assertEqual(
            set(names),
            {"search_cards", "get_card", "get_card_rulings", "get_card_printings", "autocomplete_card_name",
             "random_card", "analyze_deck", "find_combos", "search_combos", "edhrec_recommendations",
             "edhrec_card", "price_decklist"},
        )


if __name__ == "__main__":
    unittest.main()
