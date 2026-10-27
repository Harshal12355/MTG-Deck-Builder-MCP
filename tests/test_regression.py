"""Golden-deck and skill-chain regression tests.

Run before refactors: if these fail, behavior changed — update fixtures only on purpose.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakes import CARDS, FakeApis  # noqa: E402
from mtg_mcp import server  # noqa: E402
from mtg_mcp.analysis import analyze  # noqa: E402
from mtg_mcp.decklist import parse_decklist  # noqa: E402
from mtg_mcp.skills import load_skills  # noqa: E402
from test_all import atraxa_list, run  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "golden_atraxa_pipeline.json"
REPO = Path(__file__).resolve().parents[1]

SKILL_REF_RE = re.compile(r"""get_skill\(\s*["']([a-z0-9-]+)["']\s*\)""")
SKILL_SCAN_ROOTS = (
    REPO / "src" / "mtg_mcp" / "deck_skills",
    REPO / ".cursor" / "skills",
    REPO / ".cursor" / "rules",
)


def _load_golden() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class GoldenPipelineTests(unittest.TestCase):
    """End-to-end pipeline on the offline Atraxa fake deck (fixed seed where random)."""

    def setUp(self):
        self.golden = _load_golden()
        self.fake = FakeApis()
        server.set_http_client(self.fake.client())
        self.deck = atraxa_list()

    def test_parse_decklist(self):
        exp = self.golden["parse"]
        d = parse_decklist(self.deck)
        self.assertEqual([e.name for e in d.commanders], exp["commanders"])
        self.assertEqual(d.card_count, exp["card_count"])

    def test_analyze_direct_matches_golden(self):
        exp = self.golden["analyze_direct"]
        r = analyze(parse_decklist(self.deck), CARDS)
        self.assertEqual(r["legal"], exp["legal"])
        self.assertEqual(r["color_identity"], exp["color_identity"])
        self.assertEqual(r["lands"], exp["lands"])
        self.assertEqual(r["bracket"]["bracket"], exp["bracket"])
        self.assertEqual(r["bracket"]["label"], exp["bracket_label"])
        self.assertEqual(r["power_score"]["total"], exp["power_score_total"])
        self.assertEqual(r["game_changers"], exp["game_changers"])
        self.assertEqual(r["school_score"]["nero"], exp["school_nero"])
        self.assertEqual(r["school_score"]["defcat"], exp["school_defcat"])
        self.assertEqual(r["school_score"]["based_33"], exp["school_based_33"])
        self.assertEqual(r["template"]["cards_doing_double_duty"], exp["template_double_duty"])
        self.assertEqual(round(r["price"]["total_usd"], 2), exp["price_total_usd"])

    def test_analyze_deck_tool_with_combos(self):
        exp = self.golden["analyze_tool_with_combos"]
        r = run(server.analyze_deck(self.deck, include_combos=True))
        self.assertEqual(r["bracket"]["bracket"], exp["bracket"])
        self.assertEqual(r["bracket"]["label"], exp["bracket_label"])
        self.assertEqual(r["power_score"]["total"], exp["power_score_total"])
        self.assertEqual(r["power_score"]["speed"], exp["power_speed"])
        self.assertEqual(r["power_score"]["consistency"], exp["power_consistency"])

    def test_find_combos(self):
        exp = self.golden["combos"]
        r = run(server.find_combos(self.deck))
        self.assertEqual(len(r["in_deck"]["combos"]), exp["in_deck"])
        self.assertEqual(len(r["one_card_away"]["combos"]), exp["one_card_away"])

    def test_simulate_deck_seed_1(self):
        exp = self.golden["simulate_seed_1"]
        r = run(
            server.simulate_deck(
                self.deck,
                win_lines=[["Doubling Season", "Cultivate"]],
                turns=6,
                trials=exp["trials"],
                seed=1,
            )
        )
        self.assertEqual(r["trials"], exp["trials"])
        self.assertEqual(round(r["opening_hand"]["kept_seven"], 3), round(exp["kept_seven"], 3))
        self.assertEqual(round(r["commander"]["castable_by_turn"]["6"], 3), round(exp["cast_t6"], 3))
        self.assertEqual(
            round(r["commander"]["castable_ignoring_color_by_turn"]["6"], 3),
            round(exp["cast_ignore_t6"], 3),
        )
        self.assertEqual(
            round(r["win_lines"][0]["assembled_by_turn"]["6"], 3),
            round(exp["win_line_assembled_t6"], 3),
        )

    def test_analyze_mana_base(self):
        exp = self.golden["mana"]
        r = run(server.analyze_mana_base(self.deck))
        self.assertEqual(r["recommended_land_count"], exp["recommended_land_count"])
        self.assertEqual(r["grade"]["letter"], exp["grade_letter"])
        self.assertEqual(r["grade"]["score"], exp["grade_score"])

    def test_find_tokens(self):
        exp = self.golden["tokens"]
        r = run(server.find_tokens(self.deck))
        self.assertEqual(r["token_doublers_in_deck"], exp["token_doublers_in_deck"])

    def test_compare_decks(self):
        exp = self.golden["compare_decks"]
        list_b = self.deck.replace("1 Rhystic Study", "1 Lightning Bolt").replace("1 Demonic Tutor", "1 Forest")
        r = run(server.compare_decks(self.deck, list_b))
        self.assertEqual(r["deltas"]["bracket"]["before"], exp["bracket_before"])
        self.assertEqual(r["deltas"]["bracket"]["after"], exp["bracket_after"])
        self.assertEqual(r["deltas"]["bracket"]["delta"], exp["bracket_delta"])
        self.assertEqual(r["game_changers_removed"], exp["game_changers_removed"])


class SkillChainTests(unittest.TestCase):
    """Skills and agent docs must reference skills that actually ship with the server."""

    def test_get_skill_references_resolve(self):
        loaded = load_skills()
        refs: set[str] = set()
        for root in SKILL_SCAN_ROOTS:
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                if path.suffix not in {".md", ".mdc"}:
                    continue
                rel = path.relative_to(REPO)
                if len(rel.parts) >= 3 and rel.parts[:2] == (".cursor", "skills") and rel.parts[2].startswith("ponytail"):
                    continue
                text = path.read_text(encoding="utf-8")
                refs.update(SKILL_REF_RE.findall(text))
        missing = sorted(refs - set(loaded))
        self.assertFalse(missing, f"get_skill() references unknown skills: {missing}")

    def test_packaged_and_cursor_deck_skills_match(self):
        loaded = load_skills()
        for name in loaded:
            packaged = REPO / "src" / "mtg_mcp" / "deck_skills" / name / "SKILL.md"
            cursor = REPO / ".cursor" / "skills" / name / "SKILL.md"
            self.assertTrue(packaged.is_file(), packaged)
            self.assertTrue(cursor.is_file(), f"missing .cursor mirror for {name!r}")
            self.assertEqual(
                packaged.read_text(encoding="utf-8"),
                cursor.read_text(encoding="utf-8"),
                f"{name}: edit src/mtg_mcp/deck_skills only, then sync .cursor/skills",
            )


if __name__ == "__main__":
    unittest.main()
