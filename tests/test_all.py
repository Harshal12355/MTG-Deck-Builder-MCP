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
        self.assertIn("draw_on_their_spell", self.roles("Rhystic Study"))
        self.assertNotIn("draw_on_cast", self.roles("Rhystic Study"))
        self.assertNotIn("draw_on_hit", self.roles("Rhystic Study"))

    def test_draw_gates(self):
        def gates(text, type_line="Instant"):
            return card_roles({"type_line": type_line, "oracle_text": text})

        opt = gates("Scry 1.\nDraw a card.")
        self.assertIn("card_draw", opt)
        self.assertEqual([r for r in opt if r.startswith("draw_")], ["draw_on_cast"])
        piracy = gates(
            "Whenever a creature you control deals combat damage to an opponent, you may draw a card.",
            "Enchantment",
        )
        self.assertIn("draw_on_hit", piracy)
        self.assertNotIn("draw_on_their_spell", piracy)
        self.assertNotIn("draw_on_cast", piracy)
        enters = gates("When this creature enters, draw a card.", "Creature — Human")
        self.assertIn("draw_on_cast", enters)
        arena = gates("At the beginning of your upkeep, you draw a card and you lose 1 life.", "Enchantment")
        self.assertIn("card_draw", arena)
        self.assertFalse(any(r.startswith("draw_on_") for r in arena))
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
        self.assertEqual(r["bracket"]["bracket"], 3)
        self.assertEqual(r["bracket"]["label"], "Upgraded")
        self.assertTrue(r["bracket"]["bracket_path"])
        self.assertGreater(r["power_score"]["total"], 0)
        self.assertIn("speed", r["power_score"])
        self.assertIn("consistency", r["power_score"])
        self.assertIn("school_score", r)
        self.assertIn("nero", r["school_score"])
        self.assertIn("defcat", r["school_score"])
        self.assertIn("based_33", r["school_score"])
        r_keystone = analyze(
            d,
            CARDS,
            combos=[
                {"cards": ["Zuran Orb", "A", "B"], "bracket_tag": "E"},
                {"cards": ["Zuran Orb", "C", "D"], "bracket_tag": "E"},
                {"cards": ["Zuran Orb", "E", "F"], "bracket_tag": "E"},
            ],
        )
        self.assertEqual(r_keystone["school_score"]["keystone_combo_pieces"], ["Zuran Orb"])
        self.assertIn("synergy", r)
        self.assertEqual(r["roles"]["cards"]["draw_on_their_spell"], ["Rhystic Study"])
        self.assertEqual(r["price"]["most_expensive"][0], {"card": "Doubling Season", "usd": 45.0})
        t = r["template"]
        self.assertEqual(t["categories"]["lands"], {"target": 38, "actual": 91, "status": "53 over"})
        self.assertEqual(t["categories"]["ramp"]["cards"], ["Cultivate", "Sol Ring"])
        self.assertEqual(t["categories"]["mass_disruption"]["cards"], ["Wrath of God"])
        self.assertEqual(t["categories"]["targeted_disruption"]["cards"], ["Counterspell", "Swords to Plowshares"])
        self.assertIn("Doubling Season", t["categories"]["plan"]["cards"])
        self.assertNotIn("Atraxa, Praetors' Voice", t["categories"]["plan"]["cards"])
        self.assertTrue(any(g.startswith("lands: 91") for g in t["gaps"]))
        self.assertEqual(t["cards_doing_double_duty"], 9)

    def test_custom_template(self):
        r = analyze(parse_decklist(atraxa_list()), CARDS, template={"lands": 91, "ramp": 2})
        cats = r["template"]["categories"]
        self.assertEqual(cats["lands"]["status"], "on target")
        self.assertEqual(cats["ramp"]["status"], "on target")
        self.assertFalse(any(g.startswith(("lands", "ramp")) for g in r["template"]["gaps"]))
        with self.assertRaises(ValueError):
            analyze(parse_decklist(atraxa_list()), CARDS, template={"wincons": 3})
        with self.assertRaises(ValueError):
            analyze(parse_decklist(atraxa_list()), CARDS, template={"lands": -1})

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
        with_combos = run(server.analyze_deck(atraxa_list(), include_combos=True))
        self.assertEqual(with_combos["bracket"]["bracket"], 4)  # Spellbook 'R' early 2-card combo elevates to B4

    def test_edhcheck_suite_tools(self):
        mana = run(server.analyze_mana_base(atraxa_list()))
        self.assertIn("grade", mana)
        self.assertIn("letter", mana["grade"])
        self.assertGreaterEqual(mana["recommended_land_count"], 30)
        self.assertTrue(mana["color_requirements"])

        cycles = run(server.search_lands())
        self.assertEqual(len(cycles["cycles"]), 24)
        pains = run(server.search_lands(color_identity="wubg", cycle="pain", max_price=5.0))
        self.assertEqual(pains["cycle"]["slug"], "pain")
        self.assertIn("is:painland", pains["query"])

        list_b = atraxa_list().replace("1 Rhystic Study", "1 Lightning Bolt").replace("1 Demonic Tutor", "1 Forest")
        diff = run(server.compare_decks(atraxa_list(), list_b))
        self.assertLess(diff["deltas"]["bracket"]["after"], diff["deltas"]["bracket"]["before"])
        self.assertEqual(diff["game_changers_removed"], ["Demonic Tutor", "Rhystic Study"])

        pod = run(server.check_pod([atraxa_list(), list_b], names=["Tuned Atraxa", "Core Atraxa"]))
        self.assertIn(pod["verdict"], {"balanced", "slight", "uneven", "mismatched"})
        self.assertEqual(len(pod["seats"]), 2)

        tokens = run(server.find_tokens(atraxa_list()))
        self.assertEqual(tokens["token_doublers_in_deck"], ["Doubling Season"])

        priced = run(server.price_decklist(atraxa_list(), budget_target=50.0))
        self.assertLessEqual(priced["total_after_cuts"], 50.0)
        self.assertTrue(priced["suggested_cuts_to_hit_budget"])

    def test_deckbuilding_template_tool(self):
        r = run(server.deckbuilding_template())
        self.assertEqual({k: v["target"] for k, v in r["categories"].items()},
                         {"lands": 38, "ramp": 10, "card_advantage": 12, "targeted_disruption": 12,
                          "mass_disruption": 6, "plan": 30})
        self.assertIsNone(r["customized"])
        self.assertEqual(r["cards_doing_double_duty"], 9)
        r = run(server.deckbuilding_template({"lands": 36, "plan": 34}, color_identity="WUB"))
        self.assertEqual(r["customized"], ["lands", "plan"])
        self.assertEqual(r["categories"]["ramp"]["search_query"], "otag:ramp f:commander id<=wub")
        self.assertNotIn("search_query", r["categories"]["plan"])
        self.assertIn("error", run(server.deckbuilding_template({"lands": "lots"})))
        self.assertIn("error", run(server.analyze_deck(atraxa_list(), template={"bogus": 1})))

    def test_deckbuilding_principles_tool(self):
        r = run(server.deckbuilding_principles())
        keys = [p["key"] for p in r["principles"]]
        self.assertEqual(keys, ["commander", "win_condition", "build_backwards", "mana_curve", "synergy",
                                "no_rigid_templates", "interaction"])
        by_key = {p["key"]: p for p in r["principles"]}
        self.assertEqual(by_key["mana_curve"]["target_average_mana_value"], 2.0)
        self.assertEqual(by_key["no_rigid_templates"]["land_range"], [29, 34])
        self.assertIn("Budget Pub Stomper", r["source"])
        process = r["build_process"]
        self.assertIn("Budget Bros", process["source"])
        self.assertEqual([st["key"] for st in process["steps"]],
                         ["analyze_commander", "win_condition_first", "fill_the_veggies", "synergy_in_every_slot"])
        self.assertEqual([st["step"] for st in process["steps"]], [1, 2, 3, 4])
        self.assertTrue(all(st.get("test") for st in process["steps"]))
        self.assertEqual(process["frame"]["table"], "high-power Bracket 4")
        self.assertEqual(process["frame"]["budget"], "~$100")
        self.assertIn("Mondrak", process["steps"][3]["test"])
        self.assertEqual({i["key"] for i in process["insights"]},
                         {"avoid_cookie_cutter", "budget_mana_bases", "nothing_this_turn", "missing_fast_mana"})
        self.assertIn("nero-read", " ".join(r["how_to_use"]))

    def test_simulate_deck_tool(self):
        r = run(server.simulate_deck(atraxa_list(), win_lines=[["Doubling Season", "Cultivate"], ["Not In Deck"]],
                                     turns=6, trials=500, seed=1))
        self.assertEqual(r["trials"], 500)
        self.assertEqual(r["commander"]["names"], ["Atraxa, Praetors' Voice"])
        by_turn = r["commander"]["castable_by_turn"]
        self.assertEqual(list(by_turn), ["1", "2", "3", "4", "5", "6"])
        self.assertTrue(all(a <= b for a, b in zip(list(by_turn.values()), list(by_turn.values())[1:])))
        self.assertEqual(len(r["win_lines"]), 1)
        self.assertEqual(r["win_line_cards_not_in_deck"], ["Not In Deck"])
        self.assertIn("Sol Ring", r["classified"]["mana_sources"])
        self.assertIn("Cultivate", r["classified"]["land_ramp"])
        self.assertIn("Demonic Tutor", r["classified"]["tutors"])
        same = run(server.simulate_deck(atraxa_list(), win_lines=[["Doubling Season", "Cultivate"]],
                                        turns=6, trials=500, seed=1))
        self.assertEqual(same["win_lines"], r["win_lines"])
        self.assertIn("error", run(server.simulate_deck(atraxa_list(), trials=5)))
        alt = run(server.simulate_deck(atraxa_list(), win_lines=[["Doubling Season | Rhystic Study"]], trials=200, seed=2))
        self.assertEqual(alt["win_lines"][0]["cards"], ["Doubling Season | Rhystic Study"])
        either = alt["win_lines"][0]["assembled_by_turn"]["8"]
        one = run(server.simulate_deck(atraxa_list(), win_lines=[["Doubling Season"]], trials=200, seed=2))
        self.assertGreaterEqual(either, one["win_lines"][0]["assembled_by_turn"]["8"])
        # 45 Forest, 45 Island, one Command Tower. Atraxa needs G, W, U, and B.
        # Tower pays one of those colors, not all four.
        self.assertEqual(r["commander"]["castable_by_turn"]["6"], 0.0)
        self.assertGreater(r["commander"]["castable_ignoring_color_by_turn"]["6"], 0.5)
        self.assertGreaterEqual(
            r["win_lines"][0]["seen_by_turn"]["6"],
            r["win_lines"][0]["assembled_by_turn"]["6"],
        )
        self.assertIn("1", r["development"]["median_hand_by_turn"])
        mull = run(server.simulate_deck(
            atraxa_list(),
            turns=4,
            trials=200,
            seed=1,
            mulligan_targets=[{"category": "land", "count": 3, "by_turn": 3}, {"category": "ramp", "count": 1, "by_turn": 2}],
            track_card_impact=True,
        ))
        self.assertIn("mulligan_strategy", mull)
        self.assertEqual(len(mull["mulligan_strategy"]["targets"]), 2)
        self.assertIn("card_impact", mull)

    def test_goldfish_color_hand_and_payable_line(self):
        from mtg_mcp.goldfish import SimCard, _play_game, pay

        class _KeepOrder:
            def shuffle(self, seq):
                pass

        pips = [frozenset(c) for c in "GWUB"]
        # Four mana, but the only source that can pay white or black is one land. It pays one pip.
        self.assertIsNone(pay(0, [frozenset("WUBRG"), frozenset("G"), frozenset("U"), frozenset("G")], 0, pips))
        self.assertIsNotNone(pay(0, [frozenset(c) for c in "GWUB"], 0, pips))

        island = SimCard("Island", "land", sources=(frozenset({"U"}),))
        forest = SimCard("Forest", "land", sources=(frozenset({"G"}),))
        cost = (0, (frozenset({"U"}), frozenset({"U"})))
        islands = _play_game([island] * 6 + [SimCard("Bear", "other", cmc=2)], _KeepOrder(), 2, 2, True, 0, [], cost)
        self.assertEqual(islands["commander_turn"], 2)
        forests = _play_game([forest] * 6 + [SimCard("Bear", "other", cmc=2)], _KeepOrder(), 2, 2, True, 0, [], cost)
        self.assertIsNone(forests["commander_turn"])
        self.assertEqual(forests["commander_turn_ignoring_color"], 2)

        cantrip = SimCard("Opt", "other", cmc=1, generic=1, draws=1)
        # 3 lands keeps the hand, so the only card lost is the cantrip, and the draw puts one back.
        library = [island] * 3 + [cantrip] + [SimCard(f"F{i}", "other", cmc=3) for i in range(4)]
        drawn = _play_game(library, _KeepOrder(), None, 1, True, 0, [])
        self.assertEqual(drawn["hand_by_turn"], [6])
        self.assertEqual(drawn["follow_up_turn"], 1)

        season = SimCard("Season", "other", cmc=5, generic=5)
        cultivate = SimCard("Cultivate", "other", cmc=3, generic=3)
        line = [[(["Season"], False), (["Cultivate"], False)]]
        early = _play_game([season, cultivate] + [forest] * 6, _KeepOrder(), None, 1, True, 0, line)
        self.assertIsNone(early["line_turns"][0])
        self.assertEqual(early["seen_turns"][0], 1)

    def test_unpaid_rituals_do_not_cast_the_commander(self):
        # The hand keeps (3 lands) but turn 1 plays one land. Two rituals cost 4,
        # so neither can be cast. Adding their leftover mana anyway would pretend
        # a commander that costs 3 is cast.
        from mtg_mcp.goldfish import SimCard, _play_game

        class _KeepOrder:
            def shuffle(self, seq):
                pass

        def library(rituals):
            cards = [SimCard("Mountain", "land") for _ in range(3)]
            cards += rituals
            cards += [SimCard(f"Filler {i}", "other") for i in range(7 - len(cards))]
            return cards

        too_expensive = SimCard("Big Ritual", "ritual", cmc=4, mana=5)
        missed = _play_game(library([too_expensive, too_expensive]), _KeepOrder(), 3, 1, True, 0, [])
        self.assertIsNone(missed["commander_turn"])

        dark_ritual = SimCard("Dark Ritual", "ritual", cmc=1, mana=3)
        cast = _play_game(library([dark_ritual]), _KeepOrder(), 3, 1, True, 0, [])
        self.assertEqual(cast["commander_turn"], 1)

    def test_analyze_reports_unknown_cards(self):
        r = run(server.analyze_deck("1 Sol Ring\n1 Not A Real Card"))
        self.assertEqual(r["cards_not_found"], ["Not A Real Card"])

    def test_flavor_names_resolve(self):
        r = run(server.price_decklist("1 Thrum of the Vestige\n1 S.H.I.E.L.D. Spy Satellite\n1 Not A Real Card"))
        self.assertEqual(r["cards_not_found"], ["Not A Real Card"])
        self.assertAlmostEqual(r["total_usd"], 2.5)
        named = [c[1] for c in self.fake.calls if "/cards/named" in c[1]]
        self.assertTrue(all("exact=" in u for u in named))  # never fuzzy: no silent swaps

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
        r_forge = run(server.get_card("atraxa", include_forge_tags=True))
        self.assertEqual(r_forge["forge_tags"]["deck_needs"], ["Ability$Counters"])
        self.assertIn("counters", r_forge["forge_tags"]["synergy_enables"])
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


class ArchidektTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeApis()
        server.set_http_client(self.fake.client())

    def test_parse_deck_id(self):
        from mtg_mcp.archidekt import parse_deck_id
        self.assertEqual(parse_deck_id("https://archidekt.com/decks/123456/my-deck"), 123456)
        self.assertEqual(parse_deck_id("987"), 987)
        self.assertIsNone(parse_deck_id("moxfield.com/decks/abc"))

    def test_search_params_and_format_filter(self):
        r = run(server.archidekt_search_decks(commander="atraxa", colors="gwu", bracket=3, limit=10))
        self.assertEqual([d["id"] for d in r["decks"]], [1, 2, 3])  # modern deck filtered out
        self.assertEqual(r["decks"][0]["colors"], "WUG")
        self.assertEqual(r["decks"][0]["format"], "Commander")
        call = next(c[1] for c in self.fake.calls if "/api/decks/v3/" in c[1])
        self.assertIn("commanderName=Atraxa", call)
        self.assertIn("deckFormat=3", call)
        self.assertIn("edhBracket=3", call)
        self.assertIn("colors=Green%2CWhite%2CBlue", call)

    def test_color_letters_with_commas(self):
        from mtg_mcp.archidekt import color_param
        self.assertEqual(color_param("w,u"), "White,Blue")
        self.assertEqual(color_param("gwu"), "Green,White,Blue")
        self.assertEqual(color_param("White,Blue"), "White,Blue")

    def test_search_bad_format(self):
        r = run(server.archidekt_search_decks(format="hearthstone"))
        self.assertIn("Unknown format", r["error"])

    def test_get_deck(self):
        r = run(server.archidekt_get_deck("https://archidekt.com/decks/1/test"))
        self.assertEqual(r["commanders"], ["Atraxa, Praetors' Voice"])
        self.assertEqual(r["card_count"], 1 + 1 + 20 + 1 + 45)
        self.assertEqual(r["other_boards"], {"Maybeboard": 1})
        self.assertNotIn("Doubling Season", r["decklist"])
        self.assertEqual(r["category_counts"]["Land"], 20)
        # The decklist round-trips through our own parser.
        d = parse_decklist(r["decklist"])
        self.assertEqual(d.commanders[0].name, "Atraxa, Praetors' Voice")
        self.assertEqual(d.card_count, r["card_count"])

    def test_get_deck_missing(self):
        r = run(server.archidekt_get_deck("424242"))
        self.assertIn("not found", r["error"])

    def test_popular_cards(self):
        r = run(server.archidekt_popular_cards("atraxa", decks=5, decklist="1 Sol Ring"))
        self.assertEqual(r["decks_sampled"], 2)  # deck 3 has a different commander
        names = {c["name"]: c for c in r["cards"]}
        self.assertNotIn("Sol Ring", names)      # excluded: already in decklist
        self.assertNotIn("Forest", names)        # basics hidden by default
        self.assertNotIn("Doubling Season", names)  # maybeboard only
        self.assertEqual(names["Rhystic Study"]["inclusion_pct"], 100.0)
        self.assertEqual(names["Filler Card 0"]["usual_category"], "Plan")


class ReferenceLibraryTests(unittest.TestCase):
    """The bundled NeRo library (src/mtg_mcp/data/library/nero) and the reference_* tools."""

    @classmethod
    def setUpClass(cls):
        from mtg_mcp.library import Library
        cls.lib = Library()

    def test_library_loads_complete_decks(self):
        self.assertIn("nero", self.lib.sources)
        self.assertGreaterEqual(len(self.lib.active_decks()), 27)
        for d in self.lib.decks:
            total = sum(q for _, q, b, _ in d["cards"] if b in ("main", "commander"))
            self.assertEqual(total, 100, d["name"])
            for name, _, _, _ in d["cards"]:
                self.assertIn(name, self.lib.cards, f"{name} has no metadata")

    def test_win_lines_are_in_their_decks(self):
        for d in self.lib.decks:
            names = {n for n, _, b, _ in d["cards"] if b in ("main", "commander")}
            for line in d.get("notes", {}).get("win_lines", []):
                self.assertTrue(set(line) <= names, (d["name"], line))

    def test_principles_present(self):
        res = run(server.reference_principles("nero"))
        principles = res["sources"][0]["principles"]
        self.assertGreaterEqual(len(principles), 10)
        self.assertTrue(all(p["guidance"] and p["evidence"] for p in principles))

    def test_reference_cards_filters(self):
        res = run(server.reference_cards(role="counter", color_identity="UB", min_decks=3))
        names = [c["name"] for c in res["cards"]]
        self.assertIn("Arcane Denial", names)
        self.assertTrue(all(set(c["color_identity"]) <= set("UB") for c in res["cards"]))
        counts = [c["deck_count"] for c in res["cards"]]
        self.assertEqual(counts, sorted(counts, reverse=True))
        cheap = run(server.reference_cards(max_price=0.5, min_decks=2))
        self.assertTrue(all(c["usd_at_capture"] is None or c["usd_at_capture"] <= 0.5 for c in cheap["cards"]))
        self.assertIn("error", run(server.reference_cards(role="banana")))

    def test_reference_card_and_deck(self):
        card = run(server.reference_card("sol ring"))
        self.assertTrue(card["in_library"])
        self.assertGreater(card["deck_count"], 20)
        self.assertFalse(run(server.reference_card("Definitely Not A Card"))["in_library"])
        deck = run(server.reference_deck("Hapatra"))
        self.assertEqual(deck["commanders"], ["Hapatra, Vizier of Poisons"])
        self.assertTrue(deck["notes"]["win_lines"])
        parsed = parse_decklist(deck["decklist"])
        self.assertEqual(parsed.card_count, 100)
        self.assertEqual([e.name for e in parsed.commanders], ["Hapatra, Vizier of Poisons"])
        self.assertIn("error", run(server.reference_deck("zzzz no such deck")))

    def test_reference_library_overview(self):
        res = run(server.reference_library())
        self.assertGreaterEqual(len(res["decks"]), 28)
        kefka = [d for d in res["decks"] if d["deck"].startswith("Kefka (2026")][0]
        self.assertEqual(kefka["cards"], 100)
        self.assertAlmostEqual(kefka["average_mana_value_nonland"], 2.04, places=2)


class ReferenceCompareAndImportTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeApis()
        server.set_http_client(self.fake.client())

    def test_compare_suggests_staples_in_identity(self):
        res = run(server.reference_compare(atraxa_list(), min_decks=5))
        self.assertEqual(res["commanders"], ["Atraxa, Praetors' Voice"])
        suggested = {c["name"] for cards in res["missing_staples_by_role"].values() for c in cards}
        self.assertIn("Arcane Signet", suggested)
        self.assertNotIn("Sol Ring", suggested)  # already in the deck
        self.assertNotIn("Lightning Bolt", suggested)  # red is outside Atraxa's identity

    def test_compare_needs_a_resolved_commander(self):
        res = run(server.reference_compare("1 Sol Ring", commanders=["Not A Real Commander"]))
        self.assertIn("Couldn't look up", res["error"])

    def test_moxfield_import_writes_source(self):
        import os
        import tempfile
        from mtg_mcp import library
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["MTG_MCP_LIBRARY_DIR"] = tmp
            try:
                res = run(server.moxfield_import_user("SomeUser"))
                self.assertEqual(res["decks_imported"], 1)  # the modern deck is skipped
                self.assertEqual(res["primers_saved"], 1)
                lib = library.get_library()
                deck = lib.find_decks("Vren")[0]
                self.assertEqual(deck["name"], "Test Deck")
                self.assertIn(["Counterspell", 1, "main", ["counter"]], deck["cards"])
                self.assertIn(["Negate", 1, "considering", []], deck["cards"])
                self.assertEqual(lib.cards["Counterspell"]["ci"], "U")
                primers = list((Path(tmp) / "someuser" / "primers").glob("*.md"))
                self.assertEqual(len(primers), 1)
                self.assertIn("Counter everything", primers[0].read_text())
            finally:
                del os.environ["MTG_MCP_LIBRARY_DIR"]
                library.reload_library()


class SkillTest(unittest.TestCase):
    def test_packaged_skills_parse(self):
        from mtg_mcp.skills import fetch_skill, load_skills

        loaded = load_skills()
        names = {"nero-build", "nero-tune", "nero-mana", "nero-goldfish", "nero-read", "nero-lines", "nero-hunt",
                 "defcat-build", "defcat-read", "defcat-fuel", "defcat-turn",
                 "based-build", "based-core", "based-scale", "based-split", "moxfield-primer"}
        self.assertEqual(set(loaded), names)
        for skill in loaded.values():
            self.assertTrue(skill.description)
            self.assertTrue(skill.instructions)
        self.assertIn("reference_principles", loaded["nero-tune"].instructions)
        self.assertIn("nero-read", loaded["nero-build"].instructions)
        self.assertIn("defcat-read", loaded["nero-build"].instructions)
        self.assertIn("based-core", loaded["nero-build"].instructions)
        self.assertIn("based-scale", loaded["nero-build"].instructions)
        self.assertIn("nero-goldfish", loaded["nero-build"].instructions)
        self.assertIn("defcat-turn", loaded["nero-tune"].instructions)
        self.assertIn("based-split", loaded["nero-tune"].instructions)
        self.assertIn("nero-goldfish", loaded["nero-tune"].instructions)
        self.assertIn("nero-goldfish", loaded["defcat-build"].instructions)
        self.assertIn("based-core", loaded["based-build"].instructions)
        self.assertIn("based-scale", loaded["based-build"].instructions)
        self.assertIn("based-split", loaded["based-build"].instructions)
        self.assertIn("Sauron, the Dark Lord", loaded["based-core"].instructions)
        self.assertIn("simulate_deck", loaded["based-core"].instructions)
        self.assertIn("Archmage Emeritus", loaded["based-scale"].instructions)
        self.assertIn("Exalted Flamer of Tzeentch", loaded["based-scale"].instructions)
        self.assertIn("Archmage Emeritus", loaded["based-split"].instructions)
        self.assertIn("Exalted Flamer of Tzeentch", loaded["based-split"].instructions)
        self.assertIn("Keystone bottlenecks", loaded["based-split"].instructions)
        self.assertIn("Board gate", loaded["nero-read"].instructions)
        self.assertIn("get_card_rulings", loaded["nero-read"].instructions)
        self.assertIn("search_combos", loaded["nero-lines"].instructions)
        self.assertIn("Bracket 3", loaded["nero-lines"].instructions)
        self.assertIn("10% Color-Screw", loaded["nero-goldfish"].instructions)
        self.assertIn("compare_decks(before, after)", loaded["nero-tune"].instructions)
        self.assertIn("Lofty Denial", loaded["nero-hunt"].instructions)
        self.assertIn("lesser mana value", loaded["defcat-read"].instructions)
        self.assertIn("Treasure Cruise", loaded["defcat-fuel"].instructions)
        self.assertIn("Leyline of Anticipation", loaded["defcat-turn"].instructions)
        self.assertIn("defcat-fuel", loaded["defcat-build"].instructions)
        self.assertIn("#land", loaded["moxfield-primer"].instructions)
        self.assertIn("analyze_deck", loaded["moxfield-primer"].instructions)
        missing = fetch_skill("ponytail")
        self.assertIn("error", missing)
        self.assertEqual(set(missing["skills"]), names)

    def test_frontmatter_required(self):
        from mtg_mcp.skills import parse_skill

        with self.assertRaises(ValueError):
            parse_skill("# no frontmatter\n")


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
                    prompts = await s.list_prompts()
                    tune = await s.get_prompt("nero-tune")
                    return init, [t.name for t in tools.tools], prompts, tune

        init, names, prompts, tune = run(go())
        self.assertEqual(init.serverInfo.name, "mtg-deckbuilder")
        self.assertIn("Never answer card text from memory", init.instructions)
        self.assertIn("get_skill", init.instructions)
        self.assertEqual(
            set(names),
            {"search_cards", "get_card", "get_card_rulings", "get_card_printings", "autocomplete_card_name",
             "random_card", "analyze_deck", "analyze_mana_base", "search_lands", "compare_decks", "check_pod",
             "find_tokens", "find_combos", "search_combos", "edhrec_recommendations",
             "edhrec_card", "price_decklist", "deckbuilding_template", "deckbuilding_principles", "simulate_deck",
             "archidekt_search_decks", "archidekt_get_deck", "archidekt_popular_cards",
             "reference_library", "reference_principles", "reference_cards", "reference_card", "reference_deck",
             "reference_compare", "moxfield_import_user", "get_skill"},
        )
        self.assertEqual(
            {p.name for p in prompts.prompts},
            {"nero-build", "nero-tune", "nero-mana", "nero-goldfish", "nero-read", "nero-lines", "nero-hunt",
             "defcat-build", "defcat-read", "defcat-fuel", "defcat-turn",
             "based-build", "based-core", "based-scale", "based-split", "moxfield-primer"},
        )
        text = tune.messages[0].content.text
        self.assertIn("reference_principles", text)


class HttpHostAllowlistTest(unittest.TestCase):
    """`--allowed-host` extends the SDK localhost Host check and changes nothing otherwise."""

    def setUp(self):
        self.settings = server.mcp.settings
        self.saved = (self.settings.host, self.settings.port, self.settings.transport_security)

    def tearDown(self):
        self.settings.host, self.settings.port, self.settings.transport_security = self.saved

    def _main(self, argv):
        from unittest.mock import patch

        with patch.object(server.mcp, "run"), patch("sys.argv", argv):
            server.main()

    def test_flag_adds_a_host_and_keeps_localhost(self):
        from mcp.server.transport_security import TransportSecurityMiddleware

        self._main(["mtg-mcp", "--http", "--allowed-host", "mtg.internal:*", "--allowed-host", "mtg.internal"])
        check = TransportSecurityMiddleware(self.settings.transport_security)._validate_host
        self.assertTrue(check("127.0.0.1:8000"))
        self.assertTrue(check("localhost:8000"))
        self.assertTrue(check("[::1]:8000"))
        self.assertTrue(check("mtg.internal:443"))
        self.assertTrue(check("mtg.internal"))
        self.assertFalse(check("evil.example:443"))

    def test_wildcard_pattern_does_not_match_a_bare_host(self):
        from mcp.server.transport_security import TransportSecurityMiddleware

        self._main(["mtg-mcp", "--http", "--allowed-host", "mtg.internal:*"])
        check = TransportSecurityMiddleware(self.settings.transport_security)._validate_host
        self.assertTrue(check("mtg.internal:443"))
        self.assertFalse(check("mtg.internal"))

    def test_no_flag_leaves_the_default_allowlist(self):
        from mcp.server.transport_security import TransportSecurityMiddleware

        before = self.settings.transport_security
        self._main(["mtg-mcp", "--http"])
        self.assertIs(self.settings.transport_security, before)
        check = TransportSecurityMiddleware(before)._validate_host
        self.assertTrue(check("127.0.0.1:8000"))
        self.assertFalse(check("mtg.internal:443"))


if __name__ == "__main__":
    unittest.main()
