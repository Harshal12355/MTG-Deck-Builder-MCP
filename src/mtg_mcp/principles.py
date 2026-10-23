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

# The table this process is building for. Bracket 4 is greedy about its own plan.
# cEDH spends slots answering a meta. ~$100 sits at the Bracket 4 table.
BUILD_PROCESS_FRAME: dict[str, str] = {
    "table": "high-power Bracket 4",
    "budget": "~$100",
    "guidance": "Bracket 4 spends its slots on the deck's own plan. cEDH spends slots answering a known meta. "
                "Build the ~$100 list for the Bracket 4 table. It will not have Rhystic Study, a free counter, "
                "or a Mox, and it will not cast a 3 or 4 mana commander on turn 1. That is not a power cut "
                "when the plan does not need those cards.",
}

# Step-by-step process from Budget Bros MTG, as summarised by the player.
# It complements the principles above: the principles say what a strong
# budget deck looks like, the process says in which order to build it.
# `test` is the check that step has to pass before the next one starts.
BUILD_PROCESS: list[dict[str, Any]] = [
    {
        "step": 1,
        "key": "analyze_commander",
        "title": "Analyze the commander beyond its surface theme",
        "guidance": "Read the ability that is not the obvious theme, then the ruling that decides the sequence. "
                    "Rowan, Scion of War looks like big X spells. She discounts every black and/or red spell you "
                    "cast this turn by the life you lost this turn, and only as a sorcery. X locks when the "
                    "ability resolves, and only generic mana is reduced. Lose 3 or 4 life first, then activate. "
                    "Big Score ({3}{R}) then costs {R} and still makes two Treasures.",
        "test": "Name the surface theme and the line it hides, including what locks and which mana you still pay. "
                "Phyrexian Arena loses 1 life at the next upkeep. That counts, and it is not the storm turn. "
                "Life you lose after the ability resolves does not raise the discount.",
    },
    {
        "step": 2,
        "key": "win_condition_first",
        "title": "Start with the win condition",
        "guidance": "Pick the win, then the cards that make that win castable. Do not add synergy in this step. "
                    "The win is not always a combo. Rowan wins with one black/red finisher once the generic cost "
                    "is gone (Torment of Hailfire is the video's finisher). Vren wins by having enough edicts "
                    "that each end step makes the most Rats.",
        "test": "One sentence: the card, or the pile of the same effect, that ends the game.",
    },
    {
        "step": 3,
        "key": "fill_the_veggies",
        "title": "Fill the 'veggies' at higher counts than usual",
        "guidance": "Card draw, mana, and interaction come before any card that is only the theme. Run more of "
                    "them than a typical video list. The best card in the format dies to one cheap answer. "
                    "The win attempt does not matter if the deck cannot play up to that turn.",
        "test": "Draw, ramp, and interaction are in the list. A theme-only card is not.",
    },
    {
        "step": 4,
        "key": "synergy_in_every_slot",
        "title": "Make utility cards synergistic",
        "guidance": "A counter, a removal spell, and a draw spell should each also be the plan. In a deck that "
                    "already wants fliers, Lofty Denial replaces Counterspell: one blue pip, tax {1}, or tax {4} "
                    "if you control a flyer. A type card can be right when the deck is not that type. Naban, Dean "
                    "of Iteration doubles a Wizard's own enter-the-battlefield trigger. Kefka, Court Mage is not "
                    "a Wizard deck, and Kefka and Dualcaster Mage are Wizards, so Dualcaster's copy trigger "
                    "happens twice.",
        "test": "Each utility card does its job and one of the commander's jobs. A 4-mana enabler that is blank "
                "the turn you cast it is out, even if you can afford it. Mondrak, Glory Dominus is that card: "
                "tokens you make later are doubled, and the turn you play it nothing happens.",
    },
]

BUILD_PROCESS_INSIGHTS: list[dict[str, str]] = [
    {
        "key": "avoid_cookie_cutter",
        "guidance": "Don't copy EDHREC averages wholesale. High inclusion is how a do-nothing enabler gets into the list. "
                    "Judge the card by what it does the turn you cast it.",
    },
    {
        "key": "nothing_this_turn",
        "guidance": "Cut the enabler that is blank the turn it enters. Mondrak, Glory Dominus is the picture: 4 mana, "
                    "doubles tokens you make later. Re-check the price with get_card. Out even when you can afford it.",
    },
    {
        "key": "missing_fast_mana",
        "guidance": "Do not spend slots imitating cards the budget cannot buy. No Rhystic Study, no free counter, no Mox. "
                    "Build the turn the deck can actually take.",
    },
    {
        "key": "budget_mana_bases",
        "guidance": "Untapped multicolor lands are cheap enough that five colors is a real ~$100 deck. Pathways, fast "
                    "lands, slow lands, pain lands. Prefer them over taplands. Color count is a choice.",
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
            "frame": BUILD_PROCESS_FRAME,
            "steps": BUILD_PROCESS,
            "insights": BUILD_PROCESS_INSIGHTS,
        },
        "how_to_use": [
            "Call get_skill in order when building a ~$100 list: nero-read, defcat-read, nero-lines, nero-hunt, defcat-turn. "
            "defcat-fuel only when the commander sets a mana-value bar. nero-build is the order around them.",
            "Follow build_process in order. Draw, ramp, and interaction are in the list before a card that is only the theme.",
            "State the commander's bend, including what locks and which mana you still pay, before suggesting cards.",
            "Work backwards from the win. A win can be one spell or a pile of the same effect. It does not have to be a combo.",
            "Pass a template with 29-34 lands to deckbuilding_template / analyze_deck when building to these principles, "
            "and check analyze_deck's average_cmc_nonland against the ~2.0 target.",
            "Count interaction by whether it protects the win, not only by raw removal numbers.",
            "Use EDHREC after candidates exist, to see the cookie-cutter shell. Cut the enabler that does nothing the "
            "turn it enters. Prefer untapped budget duals over taplands. Five colors is allowed at ~$100.",
        ],
    }
