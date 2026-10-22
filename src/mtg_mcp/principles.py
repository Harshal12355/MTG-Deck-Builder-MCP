"""Deckbuilding principles for strong decks on a budget.

From Budget Pub Stomper's video "(Budget Commander) Build Broken Decks on a
Budget: Part One" (March 2026), as summarised by the player. Use these
alongside the numeric template: the template is a starting point, these
decide how a focused, powerful (often ~$100) deck should bend it.
"""

from __future__ import annotations

from typing import Any

SOURCE = "Budget Pub Stomper, '(Budget Commander) Build Broken Decks on a Budget: Part One' (YouTube, March 2026)"

BUILD_PROCESS_SOURCE = "Budget Bros MTG, framework for high-power ~$100 Commander decks (YouTube, 2026)"

# Step-by-step process from Budget Bros MTG, as summarised by the player.
# It complements the principles above: the principles say what a strong
# budget deck looks like, the process says in which order to build it.
BUILD_PROCESS: list[dict[str, Any]] = [
    {
        "step": 1,
        "key": "analyze_commander",
        "title": "Analyze the commander beyond its surface theme",
        "guidance": "Read what the commander actually enables, not the obvious theme. Example: Rowan, Scion of War "
                    "can be a storm-style deck, not just a big X-spell deck. Name the engine the commander really is.",
    },
    {
        "step": 2,
        "key": "win_condition_first",
        "title": "Start with the win condition",
        "guidance": "Pick how the deck wins first, then work backwards to the pieces it needs: the combo or "
                    "finisher, the cards that enable it, and the cards that find it.",
    },
    {
        "step": 3,
        "key": "fill_the_veggies",
        "title": "Fill the 'veggies' at higher counts than usual",
        "guidance": "Ramp, card draw and interaction (removal and counterspells) come next. Run more of them "
                    "than typical decklists do: consistency comes from these, not from expensive bombs.",
    },
    {
        "step": 4,
        "key": "synergy_in_every_slot",
        "title": "Make utility cards synergistic",
        "guidance": "Prefer cards that fill a role and also advance the theme. Example: Lofty Denial in a "
                    "flying-heavy deck is efficient counter-magic that also rewards the plan.",
    },
]

BUILD_PROCESS_INSIGHTS: list[dict[str, str]] = [
    {
        "key": "avoid_cookie_cutter",
        "guidance": "Don't copy EDHREC averages wholesale. High-cost 'enabler' cards that appear in many lists "
                    "often do too little on the turn they are played. Judge each card by its impact that turn.",
    },
    {
        "key": "budget_mana_bases",
        "guidance": "Modern budget lands (pathways, slow lands, fast lands and similar untapped duals) make "
                    "consistent multicolour mana possible for ~$100. Prefer them over taplands.",
    },
]

PRINCIPLES: list[dict[str, Any]] = [
    {
        "key": "commander",
        "title": "Pick a commander that is an engine",
        "guidance": "A strong commander is a mana engine, a card-advantage engine or a combo piece. "
                    "The best ones are more than one of these.",
    },
    {
        "key": "win_condition",
        "title": "Define the win line first",
        "guidance": "Decide exactly how the deck wins before choosing cards. Without expensive staples, "
                    "build the commander into the win condition.",
    },
    {
        "key": "build_backwards",
        "title": "Build backwards from the ideal turn",
        "guidance": "Name the deck's ideal turn (e.g. a turn-three win) and its general cadence "
                    "(what it reliably does after mulligans). Choose cards that make those happen.",
    },
    {
        "key": "mana_curve",
        "title": "Keep the curve very low",
        "guidance": "A too-high average mana value is the most common mistake. "
                    "Aim for an average near or below 2.0.",
        "target_average_mana_value": 2.0,
    },
    {
        "key": "synergy",
        "title": "Synergy over staples",
        "guidance": "Replace expensive generically busted cards with synergy: build 'machines' of several "
                    "cards that work together as value engines.",
    },
    {
        "key": "no_rigid_templates",
        "title": "Don't follow templates rigidly",
        "guidance": "Every commander, strategy and colour identity needs its own build. Treat category "
                    "counts as a starting point. A land count of 29-34 is a reasonable general range.",
        "land_range": [29, 34],
    },
    {
        "key": "interaction",
        "title": "Interaction protects your win first",
        "guidance": "Build the interaction suite to protect your own win condition first. Offensive or "
                    "defensive, its job is to stop opponents from stopping you.",
    },
]


def principles() -> dict[str, Any]:
    return {
        "source": SOURCE,
        "principles": PRINCIPLES,
        "build_process": {
            "source": BUILD_PROCESS_SOURCE,
            "steps": BUILD_PROCESS,
            "insights": BUILD_PROCESS_INSIGHTS,
        },
        "how_to_use": [
            "Follow build_process in order: analyze the commander, pick the win condition, fill ramp/draw/interaction "
            "at higher-than-usual counts, then choose synergistic cards for every slot.",
            "State the commander's role and the exact win line before suggesting cards.",
            "Work backwards from the ideal turn; check every card against that plan.",
            "Pass a template with 29-34 lands to deckbuilding_template / analyze_deck when building to these principles, "
            "and check analyze_deck's average_cmc_nonland against the ~2.0 target.",
            "Count interaction by whether it protects the win, not only by raw removal numbers.",
            "Use EDHREC and Archidekt data as a starting pool, not a list to copy; cut expensive enablers that do "
            "little the turn they land, and prefer untapped budget duals over taplands.",
        ],
    }
