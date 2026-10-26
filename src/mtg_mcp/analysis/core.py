"""Deck analysis: curve, colors, card roles, legality and price.

Role tagging is a heuristic over oracle text. It is good enough to spot gaps
("you have 5 ramp pieces, most decks run ~10") but it is not a substitute for
reading the cards, so results say so.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any

from ..decklist import ParsedDeck
from ..scryfall import front_type_line, oracle_text, price_usd

COLORS = "WUBRG"

# Official WotC Game Changers list (53 cards, Feb 9 2026 update) fallback when Scryfall flag is absent.
GAME_CHANGERS_SET: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "Ad Nauseam", "Ancient Tomb", "Aura Shards", "Biorhythm", "Bolas's Citadel",
        "Braids, Cabal Minion", "Chrome Mox", "Coalition Victory", "Consecrated Sphinx", "Crop Rotation",
        "Cyclonic Rift", "Demonic Tutor", "Drannith Magistrate", "Enlightened Tutor", "Farewell",
        "Field of the Dead", "Fierce Guardianship", "Force of Will", "Gaea's Cradle", "Gamble",
        "Gifts Ungiven", "Glacial Chasm", "Grand Arbiter Augustin IV", "Grim Monolith", "Humility",
        "Imperial Seal", "Intuition", "Jeska's Will", "Lion's Eye Diamond", "Mana Vault",
        "Mishra's Workshop", "Mox Diamond", "Mystical Tutor", "Narset, Parter of Veils", "Natural Order",
        "Necropotence", "Notion Thief", "Opposition Agent", "Orcish Bowmasters", "Panoptic Mirror",
        "Rhystic Study", "Seedborn Muse", "Serra's Sanctum", "Smothering Tithe", "Survival of the Fittest",
        "Teferi's Protection", "Tergrid, God of Fright", "Thassa's Oracle", "The One Ring",
        "The Tabernacle at Pendrell Vale", "Underworld Breach", "Vampiric Tutor", "Worldly Tutor",
    )
)

FAST_MANA_SET: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "Sol Ring", "Mana Crypt", "Mana Vault", "Grim Monolith", "Mox Diamond", "Chrome Mox",
        "Mox Opal", "Jeweled Lotus", "Lotus Petal", "Dark Ritual", "Cabal Ritual", "Seething Song",
        "Elvish Spirit Guide", "Simian Spirit Guide", "Rite of Flame", "Pyretic Ritual",
        "Desperate Ritual", "Ancient Tomb", "City of Traitors",
    )
)

EXTRA_TURN_SET: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "Time Walk", "Time Warp", "Temporal Manipulation", "Time Stretch", "Temporal Mastery",
        "Nexus of Fate", "Beacon of Tomorrows", "Capture of Jingzhou", "Karn's Temporal Sundering",
        "Magistrate's Scepter", "Part the Waterveil", "Alrund's Epiphany", "Expropriate",
        "Temporal Trespass", "Walk the Aeons", "Emrakul, the Promised End", "Ugin's Nexus",
        "Savor the Moment", "Medomai the Ageless", "Lighthouse Chronologist", "Teferi, Master of Time",
        "Seedtime",
    )
)

MLD_SET: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "Armageddon", "Ravages of War", "Jokulhaups", "Obliterate", "Decree of Annihilation",
        "Catastrophe", "Boom // Bust", "Sunder", "Mana Vortex", "Land Equilibrium", "Wildfire",
        "Burning Sands", "Keldon Firebombers", "Impending Disaster", "Ruination", "Price of Glory",
        "Thoughts of Ruin", "Devastation", "Cataclysm", "Winter Orb", "Static Orb", "Stasis",
        "Blood Moon", "Back to Basics", "Vorinclex, Voice of Hunger",
    )
)

# Curated 2-card combos fallback (with early=True for compact low-MV two-card wins).
CURATED_TWO_CARD_COMBOS: tuple[tuple[str, str, bool], ...] = (
    ("Thassa's Oracle", "Demonic Consultation", True),
    ("Thassa's Oracle", "Tainted Pact", True),
    ("Dramatic Reversal", "Isochron Scepter", True),
    ("Dockside Extortionist", "Temur Sabertooth", True),
    ("Dockside Extortionist", "Cloudstone Curio", True),
    ("Exquisite Blood", "Sanguine Bond", False),
    ("Kiki-Jiki, Mirror Breaker", "Pestermite", True),
    ("Kiki-Jiki, Mirror Breaker", "Deceiver Exarch", True),
    ("Kiki-Jiki, Mirror Breaker", "Zealous Conscripts", True),
    ("Splinter Twin", "Pestermite", True),
    ("Splinter Twin", "Deceiver Exarch", True),
    ("Mikaeus, the Unhallowed", "Triskelion", False),
    ("Mikaeus, the Unhallowed", "Walking Ballista", True),
    ("Devoted Druid", "Vizier of Remedies", True),
    ("Freed from the Real", "Selvala, Heart of the Wilds", True),
    ("Food Chain", "Eternal Scourge", True),
    ("Food Chain", "Misthollow Griffin", True),
    ("Auriok Salvagers", "Lion's Eye Diamond", True),
    ("Helm of Obedience", "Leyline of the Void", True),
    ("Painter's Servant", "Grindstone", True),
    ("Pili-Pala", "Grand Architect", True),
    ("Basalt Monolith", "Rings of Brighthearth", True),
    ("Grim Monolith", "Power Artifact", True),
    ("Worldgorger Dragon", "Animate Dead", True),
    ("Worldgorger Dragon", "Dance of the Dead", True),
    ("Curiosity", "Niv-Mizzet, the Firemind", False),
    ("Curiosity", "Niv-Mizzet, Parun", False),
    ("Helm of the Host", "Godo, Bandit Warlord", False),
    ("Heliod, Sun-Crowned", "Walking Ballista", False),
    ("Heliod, Sun-Crowned", "Spike Feeder", True),
    ("Vito, Thorn of the Dusk Rose", "Exquisite Blood", False),
    ("Bloodthirsty Conqueror", "Sanguine Bond", False),
    ("Bloodthirsty Conqueror", "Vito, Thorn of the Dusk Rose", False),
    ("Cephalid Illusionist", "Nomads en-Kor", True),
    ("Spike Feeder", "Archangel of Thune", False),
    ("Midnight Guard", "Presence of Gond", False),
    ("Demonic Consultation", "Jace, Wielder of Mysteries", True),
    ("Tainted Pact", "Laboratory Maniac", True),
    ("Demonic Consultation", "Laboratory Maniac", True),
    ("Dualcaster Mage", "Twinflame", False),
    ("Dualcaster Mage", "Heat Shimmer", False),
    ("Dualcaster Mage", "Molten Duplication", False),
    ("Village Bell-Ringer", "Kiki-Jiki, Mirror Breaker", True),
    ("Restoration Angel", "Kiki-Jiki, Mirror Breaker", True),
    ("Felidar Guardian", "Kiki-Jiki, Mirror Breaker", True),
    ("Phyrexian Altar", "Gravecrawler", True),
    ("Time Sieve", "Thopter Assembly", False),
    ("Chatterfang, Squirrel General", "Pitiless Plunderer", True),
    ("Kinnan, Bonder Prodigy", "Basalt Monolith", True),
    ("Leonin Relic-Warder", "Animate Dead", True),
    ("Leonin Relic-Warder", "Dance of the Dead", True),
    ("Leonin Relic-Warder", "Necromancy", True),
    ("Abdel Adrian, Gorion's Ward", "Animate Dead", True),
    ("Abdel Adrian, Gorion's Ward", "Dance of the Dead", True),
    ("Abdel Adrian, Gorion's Ward", "Necromancy", True),
)

# Community EDHREC salt scores for the most-flagged Commander staples (0-4 scale).
SALT_SCORES: dict[str, float] = {
    "stasis": 3.5, "winter orb": 3.4, "armageddon": 3.3, "TERGRID, GOD OF FRIGHT".lower(): 3.2,
    "vorinclex, voice of hunger": 3.1, "static orb": 3.1, "ravages of war": 3.1, "sunder": 3.0,
    "expropriate": 2.9, "jin-gitaxias, core augur": 2.9, "jokulhaups": 2.9, "obliterate": 2.9,
    "grand arbiter augustin iv": 2.8, "drannith magistrate": 2.8, "humility": 2.8, "back to basics": 2.8,
    "blood moon": 2.7, "rhystic study": 2.6, "cyclonic rift": 2.6, "smothering tithe": 2.5,
    "thassa's oracle": 2.6, "opposition agent": 2.6, "narset, parter of veils": 2.6, "farewell": 2.5,
    "fierce guardianship": 2.4, "force of will": 2.4, "the one ring": 2.4, "orcish bowmasters": 2.4,
    "consecrated sphinx": 2.3, "dockside extortionist": 2.3, "mana drain": 2.2, "teferi's protection": 2.2,
    "ad nauseam": 2.2, "underworld breach": 2.2, "demonic tutor": 2.1, "vampiric tutor": 2.1,
    "imperial seal": 2.1, "mana vault": 2.1, "ancient tomb": 2.1, "gaea's cradle": 2.3,
    "the tabernacle at pendrell vale": 3.0, "glacial chasm": 2.5, "seedborn muse": 2.1,
    "time stretch": 2.5, "time warp": 2.2, "nexus of fate": 2.4, "torabran": 1.8, "bolas's citadel": 2.1,
    "necropotence": 2.1, "aura shards": 2.2, "dictate of erebos": 2.2, "grave pact": 2.2,
}

# 10 Enabler x Payoff synergy axes (EDHcheck /how-we-score).
_SYNERGY_AXES: dict[str, tuple[re.Pattern[str], re.Pattern[str]]] = {
    "blink": (
        re.compile(r"exile (?:up to \w+ )?(?:another )?target [^.]*then return|flicker|conjurer's closet|teleportation circle"),
        re.compile(r"\bwhen (?:this |~ |it |\w+ )?enters\b"),
    ),
    "graveyard": (
        re.compile(r"\bmill\b|put the top [^.]*into your graveyard|\bsurveil\b|\bdiscard\b|\bentomb\b|\bdredge\b"),
        re.compile(r"from your graveyard|\bflashback\b|\bescape\b|\bdelve\b|\bthreshold\b|\bdelirium\b|\bretrace\b|\bunearthed?\b"),
    ),
    "sacrifice": (
        re.compile(r"\bsacrifice (?:a|an|another|one or more) (?:creature|artifact|permanent|token)"),
        re.compile(r"whenever (?:this creature or )?(?:a|another|one or more) [^.]*(?:dies|you sacrifice|leaves? your graveyard)|\bwhen this creature dies\b"),
    ),
    "tokens": (
        re.compile(r"\bcreates? (?:a|an|one|two|three|four|x|\d+|that many) [^.]*tokens?\b|\bamass\b|\bfabricate\b"),
        re.compile(r"\btokens? you control\b|for each (?:creature|token) you control|\bpopulate\b|twice that many of those tokens|convoke"),
    ),
    "counters": (
        re.compile(r"put (?:a|an|one|two|x|\d+|that many) (?:\+1/\+1|-1/-1) counters?|\bproliferate\b|\bundying\b|\bpersist\b|\bfabricate\b|additional \+1/\+1 counter"),
        re.compile(r"(?:\+1/\+1|-1/-1) counters?|remove (?:a|all|any number of) counters?|\bundying\b|\bpersist\b"),
    ),
    "spellslinger": (
        re.compile(r"\binstant\b|\bsorcery\b"),
        re.compile(r"whenever you cast (?:an|a) (?:instant|sorcery|noncreature)|\bmagecraft\b|\bstorm\b|\bprowess\b"),
    ),
    "artifacts": (
        re.compile(r"\bartifact\b|treasure token|clue token|food token|blood token"),
        re.compile(r"artifacts? you control|\baffinity for artifacts\b|\bmetalcraft\b|\bimprovise\b|whenever an artifact"),
    ),
    "lifegain": (
        re.compile(r"\bgains? (?:\d+|x|that much) life\b|\blifelink\b"),
        re.compile(r"whenever you gain life|if you gained (?:\d+ or more )?life"),
    ),
    "landfall": (
        re.compile(r"search your library for [^.]*land|play an additional land"),
        re.compile(r"whenever a land (?:you control )?enters|\blandfall\b"),
    ),
    "reanimator": (
        re.compile(r"\bmill\b|\bdiscard\b|search your library for a card, put that card into your graveyard"),
        re.compile(r"return target creature card from (?:a|your) graveyard to the battlefield|put .*creature cards? from .*graveyard.* onto the battlefield"),
    ),
}

LAND_CYCLES: list[dict[str, str]] = [
    {"slug": "fetch", "label": "Fetch Lands", "speed": "untapped", "query": "is:fetchland unique:cards", "description": "Sacrifice to search for a land with a listed basic type."},
    {"slug": "dual", "label": "Original Dual Lands", "speed": "untapped", "query": "is:dual unique:cards", "description": "ABUR two-basic-type untapped duals."},
    {"slug": "shock", "label": "Shock Lands", "speed": "conditional", "query": "is:shockland unique:cards", "description": "Enter untapped if you pay 2 life; two basic land types."},
    {"slug": "bond", "label": "Bond Lands (Battlebond)", "speed": "conditional", "query": "is:bondland unique:cards", "description": "Enter untapped if you have two or more opponents (always in 4-player Commander)."},
    {"slug": "pain", "label": "Pain Lands", "speed": "untapped", "query": "is:painland unique:cards", "description": "Always untapped; colorless free or 1 damage for colored mana."},
    {"slug": "fast", "label": "Fast Lands", "speed": "conditional", "query": "is:fastland unique:cards", "description": "Enter untapped while you control two or fewer other lands."},
    {"slug": "slow", "label": "Slow Lands", "speed": "conditional", "query": "is:slowland unique:cards", "description": "Enter untapped if you control two or more other lands."},
    {"slug": "check", "label": "Check Lands", "speed": "conditional", "query": "is:checkland unique:cards", "description": "Enter untapped if you control a land with one of the listed basic types."},
    {"slug": "pathway", "label": "Pathway Lands (MDFC)", "speed": "untapped", "query": "t:land is:mdfc name:pathway unique:cards", "description": "Modal double-faced untapped lands; pick one color when played."},
    {"slug": "verge", "label": "Verge Lands", "speed": "untapped", "query": 't:land name:verge o:"Activate only if you control" unique:cards', "description": "Always untapped for primary color; secondary color online with a matching basic type."},
    {"slug": "filter", "label": "Filter Lands", "speed": "untapped", "query": "is:filterland unique:cards", "description": "Always untapped; filter 1 colored mana into 2 colored mana."},
    {"slug": "canopy", "label": "Horizon Lands (Canopy)", "speed": "untapped", "query": "is:canopyland unique:cards", "description": "Always untapped; pay 1 life for colored mana or sacrifice to draw a card."},
    {"slug": "battle", "label": "Battle Lands (Tango)", "speed": "conditional", "query": "is:tangoland unique:cards", "description": "Enter untapped if you control two or more basic lands; fetchable."},
    {"slug": "reveal", "label": "Reveal Lands (Snarls)", "speed": "conditional", "query": 't:land o:"As this land enters, you may reveal" unique:cards', "description": "Enter untapped if you reveal a matching land/creature type from hand."},
    {"slug": "surveil", "label": "Surveil Lands", "speed": "tapped", "query": 't:land o:"When this land enters, surveil 1" o:"enters tapped" unique:cards', "description": "Enter tapped and surveil 1; carry two basic land types (fetchable)."},
    {"slug": "tri", "label": "Tri-Lands & Triomes", "speed": "tapped", "query": "(is:triland or is:triome) unique:cards", "description": "Three-color tapped lands; Triomes have basic types and cycling."},
    {"slug": "bounce", "label": "Bounce Lands (Karoo)", "speed": "tapped", "query": "is:bounceland unique:cards", "description": "Enter tapped, return a land to hand, and tap for two mana."},
    {"slug": "scry", "label": "Scry Lands (Temples)", "speed": "tapped", "query": "is:scryland unique:cards", "description": "Enter tapped and scry 1."},
    {"slug": "bike", "label": "Cycling Duals (Bicycle)", "speed": "tapped", "query": "is:bikeland unique:cards", "description": "Enter tapped with two basic types and cycling {2}."},
    {"slug": "mdfc", "label": "MDFC Spell-Lands", "speed": "varies", "query": "is:mdfc t:land -name:pathway unique:cards", "description": "Spell on front face, land on back face."},
    {"slug": "any-color", "label": "Any-Color Lands", "speed": "varies", "query": 't:land -t:basic o:"add one mana of any color" unique:cards', "description": "Command Tower, Exotic Orchard, City of Brass, Mana Confluence, etc."},
    {"slug": "panorama", "label": "Basic Fetches (Landscapes / Panoramas)", "speed": "tapped", "query": 't:land (o:"Search your library for a basic land card" o:tapped or o:/search your library for a basic (forest|plains|island|swamp|mountain)/) unique:cards', "description": "Budget fetches that put a basic land onto the battlefield tapped."},
    {"slug": "gain", "label": "Gain Lands", "speed": "tapped", "query": "is:gainland unique:cards", "description": "Enter tapped and gain 1 life."},
    {"slug": "gate", "label": "Gates", "speed": "tapped", "query": "t:land t:gate unique:cards", "description": "Enter tapped; support Gate payoffs like Gond Gate and Maze's End."},
]

# The Command Zone's Commander deckbuilding template (2025). Targets add up to
# 108 for 99 slots on purpose: ~9 cards should do double duty (e.g. a creature
# that ramps and draws). Players can override any number per call.
TEMPLATE_CATEGORIES: dict[str, dict[str, Any]] = {
    "lands": {
        "target": 38,
        "description": "Land cards.",
        "scryfall": "t:land",
    },
    "ramp": {
        "target": 10,
        "description": "Mana rocks, mana dorks, land-fetching spells, Treasure makers, extra land drops.",
        "scryfall": "otag:ramp",
    },
    "card_advantage": {
        "target": 12,
        "description": "Cards that draw or otherwise give you extra cards to play.",
        "scryfall": "otag:card-advantage",
    },
    "targeted_disruption": {
        "target": 12,
        "description": "One-for-one interaction: spot removal, counterspells, bounce, edicts.",
        "scryfall": "(otag:removal or otag:counterspell)",
    },
    "mass_disruption": {
        "target": 6,
        "description": "Board wipes and other effects that hit many things at once.",
        "scryfall": "otag:sweeper",
    },
    "plan": {
        "target": 30,
        "description": "Cards that advance the deck's own strategy: synergy pieces, payoffs, win conditions.",
        "scryfall": None,
    },
}

_ENTRY_CATEGORY_TO_ROLE = {
    "ramp": "ramp", "mana": "ramp",
    "draw": "card_draw", "card draw": "card_draw", "card advantage": "card_draw",
    "removal": "removal", "targeted disruption": "removal", "edict": "removal",
    "counter": "counterspell", "counterspell": "counterspell", "counterspells": "counterspell",
    "wipe": "board_wipe", "board wipe": "board_wipe", "boardwipe": "board_wipe", "mass disruption": "board_wipe",
    "tutor": "tutor", "tutors": "tutor",
    "protection": "protection",
    "recursion": "recursion",
}
_CATEGORY_ROLES = {
    "ramp": {"ramp"},
    "card_advantage": {"card_draw"},
    "targeted_disruption": {"removal", "counterspell"},
    "mass_disruption": {"board_wipe"},
}


def resolve_template(overrides: dict[str, int] | None = None) -> dict[str, int]:
    """Default template targets with the player's overrides applied."""
    targets = {k: v["target"] for k, v in TEMPLATE_CATEGORIES.items()}
    for key, value in (overrides or {}).items():
        if key not in targets:
            raise ValueError(f"Unknown template category {key!r}; expected one of {', '.join(targets)}.")
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 99:
            raise ValueError(f"Template target for {key!r} must be a whole number from 0 to 99, got {value!r}.")
        targets[key] = value
    return targets


def template_overlap(targets: dict[str, int], slots: int = 99) -> dict[str, Any]:
    """How many cards must count in two categories for the targets to fit the deck."""
    total = sum(targets.values())
    return {
        "targets_total": total,
        "deck_slots": slots,
        "cards_doing_double_duty": max(total - slots, 0),
        "unassigned_slots": max(slots - total, 0),
    }


def _template_report(deck_cards: list[dict[str, Any]], lands: int, targets: dict[str, int], slots: int) -> dict[str, Any]:
    """Compare a deck against template targets. deck_cards are the resolved nonland cards."""
    members: dict[str, list[str]] = {k: [] for k in targets}
    for c in deck_cards:
        roles = set(card_roles(c))
        in_any = False
        for key, wanted in _CATEGORY_ROLES.items():
            if roles & wanted:
                members[key].append(c.get("name", "?"))
                in_any = True
        if not in_any:
            members["plan"].append(c.get("name", "?"))

    categories = {}
    gaps = []
    for key, target in targets.items():
        actual = lands if key == "lands" else len(members[key])
        diff = actual - target
        status = "on target" if diff == 0 else (f"{-diff} short" if diff < 0 else f"{diff} over")
        entry: dict[str, Any] = {"target": target, "actual": actual, "status": status}
        if key != "lands":
            entry["cards"] = sorted(members[key])
        categories[key] = entry
        # Over on lands is a real problem; over on a spell category usually just means overlap.
        if diff < 0 or (key == "lands" and diff > 0):
            gaps.append(f"{key}: {actual} (template target {target}, {status})")

    return {
        "categories": categories,
        "gaps": gaps,
        **template_overlap(targets, slots),
        "note": (
            "Spell categories are tagged heuristically from oracle text and a card can count in several; "
            "'plan' is every nonland card that fits none of the others. Verify borderline cards."
        ),
    }

_ROLE_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "ramp": [
        re.compile(r"\badd (?:\{[wubrgcsx0-9/]+\}|one mana|two mana|three mana|x mana|an amount of|mana of any|that much)"),
        re.compile(r"search your library for (?:a|an|up to \w+|two) (?:basic )?(?:land|forest|plains|island|swamp|mountain)[^.]*onto the battlefield"),
        re.compile(r"put (?:a|an|up to \w+) (?:basic )?land cards? [^.]*onto the battlefield"),
        re.compile(r"you may play (?:an )?additional lands?"),
        re.compile(r"create (?:a|an|\w+) treasure token"),
    ],
    "card_draw": [
        re.compile(r"\bdraws? (?:a|an|one|two|three|four|five|x|that many|cards equal|\d+) (?:additional )?cards?"),
        re.compile(r"\bdraw cards equal"),
        re.compile(r"exile the top [^.]* cards? of your library[^.]*\. (?:until [^.]*, )?you may (?:play|cast)"),
        re.compile(r"reveal the top [^.]* of your library[^.]*put (?:that card|it|one of them) into your hand"),
    ],
    "removal": [
        re.compile(r"\b(?:destroy|exile) (?:target|up to (?:one|two|three|x) target|another target)"),
        re.compile(r"deals? (?:\d+|x|that much) damage to (?:any target|target (?:creature|planeswalker|attacking|blocking))"),
        re.compile(r"return (?:target|up to one target) (?:nonland permanent|creature|artifact|enchantment|permanent)[^.]* to its owner's hand"),
        re.compile(r"target (?:player|opponent) sacrifices"),
        re.compile(r"each opponent sacrifices"),
        re.compile(r"\bfights? (?:target|another target|up to one target)"),
        re.compile(r"target creature gets -\d+/-\d+|target creature gets -x/-x"),
    ],
    "counterspell": [re.compile(r"\bcounter (?:target|up to one target|that spell|it)\b")],
    "board_wipe": [
        re.compile(r"\b(?:destroy|exile) all (?:other )?(?:creatures|nonland permanents|permanents|artifacts|enchantments|nontoken)"),
        re.compile(r"\b(?:destroy|exile) each (?:other )?(?:creature|nonland permanent)"),
        re.compile(r"all (?:other )?creatures get -"),
        re.compile(r"deals? (?:\d+|x) damage to each (?:other )?creature"),
        re.compile(r"return all (?:other )?(?:creatures|nonland permanents|permanents)[^.]* to their owners' hands"),
        re.compile(r"each player sacrifices (?:all|each)"),
    ],
    "tutor": [
        re.compile(r"search your library for (?:a|an|up to \w+|two|three|four|any number of) (?!basic )(?![^.]*\b(?:land|plains|island|swamp|mountain|forest)\b)[^.]*cards?"),
        re.compile(r"\btransmute\b"),
    ],
    "protection": [
        re.compile(r"(?:gains?|have|has) (?:[a-z ,]*)?(?:hexproof|indestructible|shroud|protection from)"),
        re.compile(r"phase out"),
    ],
    "recursion": [
        re.compile(r"return [^.]*from your graveyard to (?:your hand|the battlefield)"),
        re.compile(r"(?:cast|play) [^.]* from your graveyard"),
    ],
}

_ANY_NUMBER = re.compile(r"a deck can have any number of cards named")
_UP_TO_N = re.compile(r"a deck can have up to (\w+) cards named")
_PIP = re.compile(r"\{([^}]+)\}")


_DRAW_HERE = re.compile(
    r"\bdraws? (?:a|an|one|two|three|four|five|x|that many|cards equal|\d+) (?:additional )?cards?|\bdraw cards equal"
)
_IMPULSE = re.compile(r"exile the top [^.]* cards? of your library[^.]*\. (?:until [^.]*, )?you may (?:play|cast)")


def _draw_gates(text: str) -> list[str]:
    """How a draw actually happens. Combat and opponents are not the same as a cantrip.

    shortcut: upkeep draws and "whenever you cast" stay plain card_draw. Split those out when a list's draws are mostly that.
    """
    gates: list[str] = []

    def add(gate: str) -> None:
        if gate not in gates:
            gates.append(gate)

    if _IMPULSE.search(text) and not re.search(r"\bwhenever\b|\bat the beginning\b", text):
        add("draw_on_cast")
    for sent in re.split(r"[.\n]", text):
        if not _DRAW_HERE.search(sent):
            continue
        if "combat damage" in sent:
            add("draw_on_hit")
        elif re.search(r"\bopponent\b", sent) and re.search(r"\bcasts?\b", sent):
            add("draw_on_their_spell")
        elif re.search(r"\bwhenever\b|\bat the beginning\b", sent):
            continue
        else:
            add("draw_on_cast")
    return gates


def card_roles(card: dict[str, Any]) -> list[str]:
    if "Land" in front_type_line(card):
        return []
    text = oracle_text(card).lower()
    # Ignore reminder text in parentheses.
    text = re.sub(r"\([^)]*\)", "", text)
    roles = [role for role, pats in _ROLE_PATTERNS.items() if any(p.search(text) for p in pats)]
    # Mana rocks/dorks: "{T}: Add" on a nonland permanent.
    if "ramp" not in roles and re.search(r"\{t\}[^:]*: add\b", text):
        roles.insert(0, "ramp")
    if "card_draw" in roles:
        roles.extend(_draw_gates(text))
    return roles


def _pips(cost: str) -> Counter[str]:
    pips: Counter[str] = Counter()
    for sym in _PIP.findall(cost or ""):
        if "/" in sym and any(ch.isdigit() for ch in sym):
            continue
        for c in COLORS:
            if c in sym.upper():
                pips[c] += 1
    return pips


def _front_lower(name: str) -> str:
    return name.split(" // ")[0].strip().lower()


def _is_game_changer(card: dict[str, Any], fallback_name: str = "") -> bool:
    flag = card.get("game_changer")
    if flag is not None:
        return bool(flag)
    return _front_lower(card.get("name") or fallback_name) in GAME_CHANGERS_SET


def _is_fast_mana(card: dict[str, Any]) -> bool:
    name = _front_lower(card.get("name") or "")
    if name in FAST_MANA_SET:
        return True
    tl = front_type_line(card)
    if "Land" in tl or "Creature" in tl:
        return False
    cmc = float(card.get("cmc") or 0)
    if cmc > 1:
        return False
    text = re.sub(r"\([^)]*\)", "", oracle_text(card).lower())
    return bool(re.search(r"add \{[wubrgc]\}\{[wubrgc]\}|add (?:two|three|four|five) mana", text))


def _is_extra_turn(card: dict[str, Any]) -> bool:
    name = _front_lower(card.get("name") or "")
    if name in EXTRA_TURN_SET:
        return True
    text = re.sub(r"\([^)]*\)", "", oracle_text(card).lower())
    return bool(re.search(r"takes? an extra turn after this one", text)) and "you lose the game" not in text


def _is_mld(card: dict[str, Any]) -> bool:
    name = _front_lower(card.get("name") or "")
    if name in MLD_SET:
        return True
    text = re.sub(r"\([^)]*\)", "", oracle_text(card).lower())
    return bool(re.search(r"\b(?:destroy|exile|sacrifice) all lands\b|nonbasic lands are mountains", text))


def _is_instant_speed(card: dict[str, Any]) -> bool:
    tl = front_type_line(card)
    if "Instant" in tl:
        return True
    keywords = [k.lower() for k in (card.get("keywords") or [])]
    if "flash" in keywords:
        return True
    text = re.sub(r"\([^)]*\)", "", oracle_text(card).lower())
    return bool(re.search(r"\bflash\b|as though (?:it|they) had flash", text))


def _synergy_profile(nonland_cards: list[dict[str, Any]]) -> dict[str, Any]:
    axes: dict[str, dict[str, int]] = {}
    for axis, (enabler_pat, payoff_pat) in _SYNERGY_AXES.items():
        enablers = 0
        payoffs = 0
        for c in nonland_cards:
            text = f"{front_type_line(c)} {re.sub(r'\\([^)]*\\)', '', oracle_text(c))}".lower()
            ftags = c.get("forge_tags") or {}
            f_enables = set(ftags.get("synergy_enables") or ())
            f_needs = set(ftags.get("synergy_needs") or ())
            if enabler_pat.search(text) or axis in f_enables:
                enablers += 1
            if payoff_pat.search(text) or axis in f_needs:
                payoffs += 1
        score = min(enablers, payoffs)
        if enablers or payoffs:
            axes[axis] = {"enablers": enablers, "payoffs": payoffs, "score": score}
    signature = [
        {"axis": k, **v}
        for k, v in sorted(axes.items(), key=lambda kv: (-kv[1]["score"], -kv[1]["payoffs"], kv[0]))
        if v["score"] >= 3
    ]
    total_axis = sum(v["score"] for v in axes.values())
    synergy_score = round(min(10.0, total_axis * 0.45), 1)
    return {
        "score": synergy_score,
        "bonus": round(min(0.8, synergy_score * 0.08), 2),
        "signature_axes": signature,
        "axes": axes,
    }


def _detect_combos_and_tiers(
    deck_names_lower: set[str],
    spellbook_combos: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    two_card: list[dict[str, Any]] = []
    three_plus: list[dict[str, Any]] = []
    template_combos: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, ...]] = set()

    for c in spellbook_combos or []:
        pieces = [p for p in (c.get("cards") or []) if p]
        if not pieces:
            continue
        also_req = c.get("also_requires") or []
        key = tuple(sorted(_front_lower(p) for p in pieces)) + tuple(also_req)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        tag = str(c.get("bracket_tag") or "").upper()
        # Commander Spellbook BracketTagEnum: 'R' (Ruthless), 'P' (Powerful) = early/Bracket 4+;
        # 'S' (Spicy) = late/Bracket 3; 'C' (Core), 'O' (Oddball), 'E' (Exhibition) = Bracket 1-2 (needs payoff).
        is_early = tag in {"R", "P", "4", "5", "EARLY", "RUTHLESS", "POWERFUL"} or (not tag and len(pieces) == 2)
        is_non_winning_two_card = len(pieces) <= 2 and tag in {"E", "O", "C", "1", "2"}
        item = {"cards": pieces, "early": is_early, "produces": c.get("produces"), "also_requires": also_req or None}
        # EDHcheck rule (05~mod.szojk4.js): `e.cards.length <= 2 && !e.requires?.length`
        # Combos with template `also_requires` ("+ needs Creature with Persist or Undying") are 3-card / template loops, not 2-card combos.
        if also_req:
            template_combos.append(item)
        elif len(pieces) <= 2 and not is_non_winning_two_card:
            two_card.append(item)
        else:
            three_plus.append(item)

    for a, b, is_early in CURATED_TWO_CARD_COMBOS:
        ka, kb = _front_lower(a), _front_lower(b)
        if ka in deck_names_lower and kb in deck_names_lower:
            key = tuple(sorted((ka, kb)))
            if key not in seen_pairs:
                seen_pairs.add(key)
                two_card.append({"cards": [a, b], "early": is_early})

    return {
        "two_card_combos": two_card,
        "three_plus_combos": three_plus,
        "template_combos": template_combos,
        "early_two_card": any(c["early"] for c in two_card),
        "late_two_card": any(not c["early"] for c in two_card),
        "total_combos": len(two_card) + len(three_plus),
        "total_including_templates": len(two_card) + len(three_plus) + len(template_combos),
    }


BRACKET_LABELS = {1: "Exhibition", 2: "Core", 3: "Upgraded", 4: "Optimized", 5: "cEDH"}


def _score_and_bracket(
    *,
    resolved: list[tuple[Any, dict[str, Any]]],
    nonland_cards: list[dict[str, Any]],
    lands: int,
    avg_cmc: float,
    roles: dict[str, list[str]],
    interaction_total: int,
    game_changers: list[str],
    spellbook_combos: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    deck_names_lower = {_front_lower(c.get("name", e.name)) for e, c in resolved}
    fast_mana = sorted({c.get("name", e.name) for e, c in resolved if _is_fast_mana(c)})
    extra_turns = sorted({c.get("name", e.name) for e, c in resolved if _is_extra_turn(c)})
    mld = sorted({c.get("name", e.name) for e, c in resolved if _is_mld(c)})
    combo_info = _detect_combos_and_tiers(deck_names_lower, spellbook_combos)

    nonland_count = max(1, len(nonland_cards))
    tutors_count = len(set(roles.get("tutor", [])))
    ramp_count = len(set(roles.get("ramp", [])))
    draw_count = len(set(roles.get("card_draw", [])))
    protection_count = len(set(roles.get("protection", [])))
    recursion_count = len(set(roles.get("recursion", [])))

    ramp_pct = ramp_count / nonland_count
    draw_pct = draw_count / nonland_count
    removal_pct = interaction_total / nonland_count

    interaction_names = set(roles.get("removal", [])) | set(roles.get("counterspell", [])) | set(roles.get("board_wipe", []))
    instant_interaction = sum(
        1 for _, c in resolved if c.get("name") in interaction_names and _is_instant_speed(c)
    )
    instant_ratio = round(instant_interaction / max(1, len(interaction_names)), 2) if interaction_names else 0.0

    # Salt average over salty cards present (or 0.2 baseline)
    salty_hits = [SALT_SCORES[_front_lower(c.get("name", e.name))] for e, c in resolved if _front_lower(c.get("name", e.name)) in SALT_SCORES]
    avg_salt = sum(salty_hits) / max(4, len(salty_hits)) if salty_hits else 0.15

    # 8 EDHcheck 0-10 sub-scores (exact EDHcheck weights and scalers)
    tutor_sub = min(10.0, tutors_count * 0.9)
    combo_sub = min(10.0, combo_info["total_combos"] * 3.2)
    gc_sub = min(10.0, len(game_changers) * 2.0)
    curve_sub = max(0.0, min(10.0, (4.2 - avg_cmc) * 3.8))
    draw_sub = min(10.0, draw_pct * 65.0)
    ramp_sub = min(10.0, ramp_pct * 70.0)
    salt_sub = min(10.0, avg_salt * 4.0)
    removal_sub = min(10.0, removal_pct * 47.0)

    synergy = _synergy_profile(nonland_cards)
    interaction_score = round(min(10.0, removal_sub * (0.65 + 0.35 * instant_ratio)), 1)
    interaction_bonus = round(min(0.4, interaction_score * 0.04), 2)

    weighted = (
        tutor_sub * 0.18
        + combo_sub * 0.15
        + gc_sub * 0.15
        + curve_sub * 0.12
        + draw_sub * 0.12
        + ramp_sub * 0.10
        + salt_sub * 0.10
        + removal_sub * 0.08
    )
    raw = weighted + synergy["bonus"] + interaction_bonus

    # Allow clean synergy/combo density (including satisfied template combos) to stand in for budget adjusted score
    full_combo_sub = min(10.0, combo_info["total_including_templates"] * 3.2)
    effective_gc_sub = max(gc_sub, min(10.0, (full_combo_sub + tutor_sub) * 0.5))
    effective_salt_sub = max(salt_sub, min(10.0, synergy["score"] * 0.9))
    budget_raw = (
        tutor_sub * 0.18
        + full_combo_sub * 0.15
        + effective_gc_sub * 0.15
        + curve_sub * 0.12
        + draw_sub * 0.12
        + ramp_sub * 0.10
        + effective_salt_sub * 0.10
        + min(10.0, removal_pct * 65.0) * 0.08
        + synergy["bonus"]
        + interaction_bonus
    )
    budget_stretched = 6.0 + (budget_raw - 6.0) * 1.3 if budget_raw > 6.0 else budget_raw
    budget_power_total = round(min(10.0, max(0.0, budget_stretched)), 1)

    # Base Bracket 1..4 decision (EDHcheck decideBracket)
    b4_reasons: list[str] = []
    if len(game_changers) > 3:
        b4_reasons.append(f"{len(game_changers)} Game Changers (Bracket 3 allows up to 3)")
    if combo_info["early_two_card"]:
        b4_reasons.append("an early two-card infinite combo")
    if mld:
        b4_reasons.append(f"mass land denial ({', '.join(mld[:3])})")

    b3_reasons: list[str] = []
    if 1 <= len(game_changers) <= 3:
        b3_reasons.append(f"{len(game_changers)} Game Changer(s) ({', '.join(game_changers)})")
    if combo_info["late_two_card"]:
        b3_reasons.append("a late two-card infinite combo")
    if len(extra_turns) > 1:
        b3_reasons.append(f"{len(extra_turns)} extra-turn spells ({', '.join(extra_turns[:3])})")

    b2_reasons: list[str] = []
    if len(extra_turns) == 1:
        b2_reasons.append(f"1 extra-turn spell ({extra_turns[0]})")
    if fast_mana:
        b2_reasons.append(f"{len(fast_mana)} fast mana source(s) (e.g. {fast_mana[0]})")
    if combo_info["three_plus_combos"]:
        b2_reasons.append(f"{len(combo_info['three_plus_combos'])} infinite combo(s) of 3+ cards")

    if b4_reasons:
        base_bracket = 4
    elif b3_reasons:
        base_bracket = 3
    elif b2_reasons or raw >= 6.5:
        base_bracket = 2
        if raw >= 6.5 and not b2_reasons:
            b2_reasons.append("a power score of 6.5+")
    else:
        base_bracket = 1

    # Soft floor/cap before top-end stretch
    adjusted = raw
    if base_bracket == 4 and adjusted < 6.8:
        adjusted = 6.8
    elif base_bracket == 1 and adjusted > 4.2:
        adjusted = 4.2

    stretched = 6.0 + (adjusted - 6.0) * 1.3 if adjusted > 6.0 else adjusted
    power_total = round(min(10.0, max(0.0, stretched)), 1)

    # Check Bracket 5 cEDH upgrade signals
    cedh_signals: list[str] = []
    if len(game_changers) >= 5:
        cedh_signals.append(f"{len(game_changers)} Game Changers")
    if len(fast_mana) >= 3:
        cedh_signals.append(f"{len(fast_mana)} fast mana")
    if combo_info["early_two_card"]:
        cedh_signals.append("an early two-card combo")
    if tutors_count >= 5:
        cedh_signals.append(f"{tutors_count} tutors")
    if power_total >= 8.5:
        cedh_signals.append(f"power {power_total:.1f}")

    bracket = base_bracket
    if (
        base_bracket == 4
        and len(game_changers) >= 4
        and (combo_info["early_two_card"] or power_total >= 8.5)
        and len(cedh_signals) >= 3
    ):
        bracket = 5
        if power_total < 8.6:
            power_total = 8.6
        reason = f"cEDH profile: {', '.join(cedh_signals)}."
    elif base_bracket == 4:
        reason = f"Optimized: {', '.join(b4_reasons)}."
    elif base_bracket == 3:
        reason = f"Upgraded: {', '.join(b3_reasons)}."
    elif base_bracket == 2:
        reason = f"Core: {', '.join(b2_reasons)}."
    else:
        reason = "Exhibition: no Game Changers, fast mana, extra turns, mass land denial, or infinite combos."

    bracket_up_warning = None
    if bracket == 2 and power_total >= 6.5:
        bracket_up_warning = (
            f"Bracket 2 by the rules, but a power score of {power_total:.1f} is where Bracket 3 decks usually sit. "
            "Wizards asks players to bracket up when a deck plays stronger than its list suggests."
        )
    elif bracket == 3 and power_total >= 7.5:
        bracket_up_warning = (
            f"Bracket 3 by the rules, but a power score of {power_total:.1f} is where Bracket 4 decks usually sit. "
            "Mention its speed/consistency before the game or play it at Bracket 4 tables."
        )

    # Actionable Bracket Path
    bracket_path: list[str] = []
    if bracket >= 4:
        if len(game_changers) > 3:
            excess = len(game_changers) - 3
            bracket_path.append(f"Cut {excess} Game Changer(s) (from {', '.join(game_changers)}) to fit Bracket 3's 3-card limit.")
        if combo_info["early_two_card"]:
            early_names = [" + ".join(c["cards"]) for c in combo_info["two_card_combos"] if c["early"]]
            bracket_path.append(f"Break up early 2-card infinite combo(s) ({'; '.join(early_names[:2])}) to drop to Bracket 3.")
        if mld:
            bracket_path.append(f"Cut mass land denial ({', '.join(mld)}) to play in Brackets 1–3.")
    if bracket == 3:
        if game_changers:
            bracket_path.append(f"Cut all {len(game_changers)} Game Changer(s) ({', '.join(game_changers)}) to drop to Bracket 2.")
        if combo_info["late_two_card"]:
            late_names = [" + ".join(c["cards"]) for c in combo_info["two_card_combos"] if not c["early"]]
            bracket_path.append(f"Remove 2-card combo(s) ({'; '.join(late_names[:2])}) to drop to Bracket 2.")
        if len(extra_turns) > 1:
            bracket_path.append(f"Trim extra-turn spells ({', '.join(extra_turns)}) down to at most 1 for Bracket 2.")

    speed_score = round(min(10.0, curve_sub * 0.35 + ramp_sub * 0.25 + tutor_sub * 0.20 + combo_sub * 0.20), 1)
    consistency_score = round(min(10.0, (draw_sub * 0.45 + tutor_sub * 0.35 + ramp_sub * 0.20) * 0.83), 1)
    token_axis = (synergy["axes"].get("tokens") or {}).get("score", 0)
    resilience_score = round(min(10.0, (protection_count + recursion_count) * 0.35 + token_axis * 0.2), 1)

    tier = (
        "Bleeding Edge" if power_total >= 9.5 else
        "Razor's Edge" if power_total >= 9.0 else
        "Hyper-Tuned" if power_total >= 8.5 else
        "Elite" if power_total >= 8.0 else
        "High Power" if power_total >= 7.0 else
        "Tuned" if power_total >= 5.5 else
        "Focused" if power_total >= 4.0 else
        "Casual"
    )

    bracket_report = {
        "bracket": bracket,
        "label": BRACKET_LABELS[bracket],
        "reason": reason,
        "bracket_up_warning": bracket_up_warning,
        "bracket_path": bracket_path,
        "flags": {
            "game_changers": game_changers,
            "fast_mana": fast_mana,
            "extra_turns": extra_turns,
            "mass_land_denial": mld,
            "two_card_combos": combo_info["two_card_combos"],
            "three_plus_combos": len(combo_info["three_plus_combos"]),
            "early_two_card_combo": combo_info["early_two_card"],
            "late_two_card_combo": combo_info["late_two_card"],
        },
    }

    power_report = {
        "total": power_total,
        "budget_adjusted_total": budget_power_total,
        "tier": tier,
        "raw_weighted": round(weighted, 2),
        "speed": speed_score,
        "consistency": consistency_score,
        "saltiness": round(salt_sub, 1),
        "interaction": interaction_score,
        "synergy": synergy["score"],
        "resilience": resilience_score,
        "components": {
            "tutors": round(tutor_sub, 1),
            "combos": round(combo_sub, 1),
            "game_changers": round(gc_sub, 1),
            "mana_curve": round(curve_sub, 1),
            "card_draw": round(draw_sub, 1),
            "ramp": round(ramp_sub, 1),
            "salt": round(salt_sub, 1),
            "removal": round(removal_sub, 1),
            "synergy_bonus": synergy["bonus"],
            "interaction_bonus": interaction_bonus,
            "instant_interaction_ratio": instant_ratio,
        },
    }

    # ---- House 3-School Scorecard (NeRo + Defcat + Based 33-card) ----
    draw_on_cast = len(set(roles.get("draw_on_cast", [])))
    immediate_draw_share = draw_on_cast / max(1, draw_count) if draw_count else 0.0
    veggie_total = ramp_count + draw_count + interaction_total + tutors_count
    nero_score = round(
        min(
            10.0,
            min(4.0, max(0.0, (3.4 - avg_cmc) * 3.1))
            + min(3.5, veggie_total / 9.5)
            + min(2.5, immediate_draw_share * 1.5 + min(1.0, combo_info["total_combos"] * 0.25)),
        ),
        1,
    )
    instant_nonlands = sum(1 for c in nonland_cards if _is_instant_speed(c))
    defcat_score = round(min(10.0, instant_ratio * 6.0 + min(4.0, (instant_nonlands / nonland_count) * 12.0)), 1)

    # Based 33-card core alignment: how well role counts scale into 3 x 33 games
    per_33 = {
        "lands": round(lands / 3.0, 1),
        "ramp": round(ramp_count / 3.0, 1),
        "card_draw": round(draw_count / 3.0, 1),
        "interaction": round(interaction_total / 3.0, 1),
    }
    uneven_roles = [
        name for name, count in (("lands", lands), ("ramp", ramp_count), ("card_draw", draw_count), ("interaction", interaction_total))
        if count % 3 != 0
    ]
    combo_piece_counts: Counter[str] = Counter()
    for c in combo_info["two_card_combos"] + combo_info["three_plus_combos"] + combo_info["template_combos"]:
        for piece in c.get("cards") or []:
            combo_piece_counts[piece] += 1
    keystone_cards = [card for card, cnt in combo_piece_counts.most_common() if cnt >= 3]

    based_hits = (
        (3.0 if 9.5 <= per_33["lands"] <= 13.5 else 1.0)
        + (2.5 if per_33["ramp"] >= 2.5 else per_33["ramp"])
        + (2.5 if per_33["card_draw"] >= 3.0 else per_33["card_draw"] * 0.8)
        + (2.0 if per_33["interaction"] >= 3.0 else per_33["interaction"] * 0.6)
        - 0.3 * len(uneven_roles)
    )
    based_score = round(max(0.0, min(10.0, based_hits)), 1)
    school_notes: list[str] = []
    if avg_cmc > 2.5:
        school_notes.append(f"NeRo: average nonland MV is {avg_cmc} (target <= 2.2 for fast Bracket 4).")
    if draw_count and immediate_draw_share < 0.5:
        school_notes.append(f"NeRo: only {draw_on_cast}/{draw_count} draw spells are draw_on_cast; replace slow engines with immediate draw.")
    if instant_ratio < 0.6 and interaction_total > 0:
        school_notes.append(f"Defcat: only {int(instant_ratio * 100)}% of interaction is instant-speed; prefer Instant/Flash answers.")
    if uneven_roles:
        school_notes.append(f"Based 3x33: {', '.join(uneven_roles)} are not clean multiples of 3 across Piles A/B/C.")
    if keystone_cards:
        school_notes.append(
            f"Based 3x33: keystone combo pieces in 3+ lines ({', '.join(keystone_cards[:3])}) need functional twins or tutors across Piles B/C."
        )

    school_report = {
        "total": round((nero_score + defcat_score + based_score) / 3.0, 1),
        "nero": nero_score,
        "defcat": defcat_score,
        "based_33": based_score,
        "per_33_game": per_33,
        "uneven_3x33_roles": uneven_roles,
        "keystone_combo_pieces": keystone_cards,
        "notes": school_notes,
    }

    return bracket_report, power_report, synergy, school_report


# ---- Hypergeometric & Karsten Mana Base Analysis ----

def _hypergeom_at_least(pop: int, successes: int, draws: int, wanted: int) -> float:
    """Exact probability of drawing >= wanted successes in `draws` from `pop` (hypergeometric)."""
    if wanted <= 0:
        return 1.0
    if successes < wanted or draws < wanted or pop <= 0:
        return 0.0
    draws = min(draws, pop)
    total_ways = math.comb(pop, draws)
    if total_ways == 0:
        return 0.0
    hit_ways = sum(
        math.comb(successes, k) * math.comb(pop - successes, draws - k)
        for k in range(wanted, min(successes, draws) + 1)
        if draws - k <= pop - successes
    )
    return min(1.0, max(0.0, hit_ways / total_ways))


def classify_land(card: dict[str, Any]) -> dict[str, str]:
    """Classify a land into its EDHcheck cycle and tempo speed (untapped | conditional | tapped)."""
    tl = front_type_line(card).lower()
    text = re.sub(r"\([^)]*\)", "", oracle_text(card).lower())
    name = (card.get("name") or "").lower()
    produced = [c for c in (card.get("produced_mana") or []) if c in COLORS]

    if "basic" in tl:
        return {"slug": "basic", "label": "Basic Land", "speed": "untapped"}
    if "search your library" in text and "land" in text:
        if "tapped" in text and "unless" not in text:
            return {"slug": "panorama", "label": "Basic Fetch (Tapped)", "speed": "tapped"}
        return {"slug": "fetch", "label": "Fetch Land", "speed": "untapped"}
    if "gate" in tl:
        return {"slug": "gate", "label": "Gate", "speed": "tapped"}
    if "return a land you control" in text:
        return {"slug": "bounce", "label": "Bounce Land (Karoo)", "speed": "tapped"}
    if "you gain 1 life" in text and "tapped" in text:
        return {"slug": "gain", "label": "Gain Land", "speed": "tapped"}
    if "pay 2 life" in text:
        return {"slug": "shock", "label": "Shock Land", "speed": "conditional"}
    if "two or more opponents" in text:
        return {"slug": "bond", "label": "Bond Land (Battlebond)", "speed": "conditional"}
    if "two or more basic lands" in text:
        return {"slug": "battle", "label": "Battle Land (Tango)", "speed": "conditional"}
    if "unless you control two or more other lands" in text:
        return {"slug": "slow", "label": "Slow Land", "speed": "conditional"}
    if "two or fewer other lands" in text:
        return {"slug": "fast", "label": "Fast Land", "speed": "conditional"}
    if re.search(r"unless you control an? [\w']+ or an? [\w']+", text):
        return {"slug": "check", "label": "Check Land", "speed": "conditional"}
    if "as this land enters, you may reveal" in text:
        return {"slug": "reveal", "label": "Reveal Land (Snarl)", "speed": "conditional"}
    if "verge" in name and "activate only if you control" in text:
        return {"slug": "verge", "label": "Verge Land", "speed": "untapped"}
    if "//" in name and "pathway" in name:
        return {"slug": "pathway", "label": "Pathway Land (MDFC)", "speed": "untapped"}
    if "deals 1 damage to you" in text or "pay 1 life" in text and "sacrifice" not in text:
        return {"slug": "pain", "label": "Pain Land", "speed": "untapped"}
    if "add two mana in any combination" in text:
        return {"slug": "filter", "label": "Filter Land", "speed": "untapped"}
    if "surveil 1" in text and "tapped" in text:
        return {"slug": "surveil", "label": "Surveil Land", "speed": "tapped"}
    if "scry 1" in text and "tapped" in text:
        return {"slug": "scry", "label": "Scry Land (Temple)", "speed": "tapped"}
    if "cycling" in text and "tapped" in text:
        return {"slug": "bike", "label": "Cycling Dual", "speed": "tapped"}
    if "sacrifice" in text and "draw a card" in text:
        return {"slug": "canopy", "label": "Horizon Land (Canopy)", "speed": "untapped"}
    if len(produced) >= 3 and "tapped" in text:
        return {"slug": "tri", "label": "Tri-Land / Triome", "speed": "tapped"}
    if "enters tapped" in text or "enters the battlefield tapped" in text:
        if any(w in text for w in ("unless", "you may pay", "if you control")):
            return {"slug": "conditional-utility", "label": "Conditional Land", "speed": "conditional"}
        return {"slug": "utility-tapped", "label": "Tapped Utility Land", "speed": "tapped"}
    if sum(t in tl for t in ("plains", "island", "swamp", "mountain", "forest")) >= 2:
        return {"slug": "dual", "label": "Original Dual Land", "speed": "untapped"}
    return {"slug": "utility", "label": "Untapped Land", "speed": "untapped"}


def analyze_mana(
    deck: ParsedDeck,
    cards: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """EDHcheck-style Mana Base Analysis: Karsten live hypergeometric solver, tipping point, and 0-100 grade."""
    entries = [(e, cards.get(e.name.lower())) for e in deck.playing]
    resolved = [(e, c) for e, c in entries if c is not None]
    cmd_set = {_front_lower(e.name) for e in deck.commanders}

    total_cards = sum(e.quantity for e, _ in resolved)
    library_size = max(1, total_cards - len(cmd_set))

    lands = 0
    ramp_count = 0
    nonland_cmcs: list[float] = []
    pip_counts: Counter[str] = Counter()
    color_sources: Counter[str] = Counter()
    land_color_sources: Counter[str] = Counter()
    speed_counts: Counter[str] = Counter()
    groups: dict[str, dict[str, Any]] = {}
    pip_demands: list[dict[str, Any]] = []
    identity: set[str] = set()

    for e, c in resolved:
        for col in c.get("color_identity") or []:
            if col in COLORS:
                identity.add(col)

    for e, c in resolved:
        is_cmd = _front_lower(c.get("name", e.name)) in cmd_set
        tl = front_type_line(c)
        raw_prod = [col for col in (c.get("produced_mana") or []) if col in COLORS]
        text_low = oracle_text(c).lower()
        if not raw_prod and "any color" in text_low:
            raw_prod = list(COLORS)
        produced = [col for col in raw_prod if not identity or col in identity]

        if "Land" in tl:
            lands += e.quantity
            info = classify_land(c)
            speed_counts[info["speed"]] += e.quantity
            g = groups.setdefault(info["slug"], {"slug": info["slug"], "label": info["label"], "speed": info["speed"], "count": 0, "cards": []})
            g["count"] += e.quantity
            g["cards"].append(c.get("name", e.name))
            # Fetch lands count as sources for any color in identity
            cols = produced or (list(identity) if info["slug"] in {"fetch", "panorama"} else [])
            for col in cols:
                color_sources[col] += e.quantity
                land_color_sources[col] += e.quantity
        else:
            cmc = float(c.get("cmc") or 0)
            if not is_cmd:
                nonland_cmcs.extend([cmc] * e.quantity)
            roles = card_roles(c)
            if "ramp" in roles and not is_cmd:
                ramp_count += e.quantity
                for col in produced:
                    color_sources[col] += e.quantity
            cost = c.get("mana_cost") or ((c.get("card_faces") or [{}])[0].get("mana_cost", ""))
            pips = _pips(cost)
            # EDHcheck rule: reactive Instants get +2 turns of grace on Karsten pip demand
            demand_turn = max(1, round(cmc)) + (2 if "Instant" in tl else 0)
            for col, p_count in pips.items():
                pip_counts[col] += p_count * e.quantity
                if not is_cmd:
                    pip_demands.append({"color": col, "pips": p_count, "turn": demand_turn, "card": c.get("name", e.name)})

    avg_cmc = sum(nonland_cmcs) / len(nonland_cmcs) if nonland_cmcs else 3.0
    # Frank Karsten 99-card regression: 31.42 + 3.13 * avg_cmc - 0.75 * ramp * 0.28
    rec_lands = max(30, min(45, round(31.42 + 3.13 * avg_cmc - 0.75 * ramp_count * 0.28)))

    # Tipping point turn: earliest turn where hypergeometric probability of >= round(avg_cmc) lands+ramp >= 0.80 (and 0.90)
    target_mana = max(2, round(avg_cmc))
    effective_mana_cards = lands + round(ramp_count * 0.75)
    tipping_80 = next(
        (t for t in range(1, 16) if _hypergeom_at_least(library_size, effective_mana_cards, min(library_size, 7 + t), target_mana) >= 0.80),
        None,
    )
    tipping_90 = next(
        (t for t in range(1, 16) if _hypergeom_at_least(library_size, effective_mana_cards, min(library_size, 7 + t), target_mana) >= 0.90),
        None,
    )

    # Solve Karsten colored-source requirements per color (90% threshold)
    toughest: dict[str, dict[str, Any]] = {}
    for d in pip_demands:
        draws = min(library_size, 7 + d["turn"])
        needed = next(
            (s for s in range(d["pips"], library_size + 1) if _hypergeom_at_least(library_size, s, draws, d["pips"]) >= 0.90),
            library_size,
        )
        cur = toughest.get(d["color"])
        if cur is None or needed > cur["sources_needed"]:
            toughest[d["color"]] = {
                "color": d["color"],
                "pips_needed": d["pips"],
                "demand_turn": d["turn"],
                "demand_card": d["card"],
                "sources_needed": needed,
            }

    color_reqs = []
    for col, req in toughest.items():
        have = color_sources[col]
        color_reqs.append({
            **req,
            "sources_have": have,
            "land_sources_have": land_color_sources[col],
            "deficit": max(0, req["sources_needed"] - have),
        })
    color_reqs.sort(key=lambda r: (-r["deficit"], -r["sources_needed"], r["color"]))

    # Cast rate by color across turns 1..8
    cast_rate_by_color = {
        col: {
            str(t): round(_hypergeom_at_least(library_size, color_sources[col], min(library_size, 7 + t), 1), 3)
            for t in range(1, 9)
        }
        for col in COLORS
        if col in identity or color_sources[col]
    }

    # Overall on-curve cast rate across all pip demands
    if pip_demands:
        overall_cast_rate = sum(
            _hypergeom_at_least(library_size, color_sources[d["color"]], min(library_size, 7 + d["turn"]), d["pips"])
            for d in pip_demands
        ) / len(pip_demands)
    else:
        overall_cast_rate = 1.0

    # Opener 2+ lands probability (accounting for Commander's free mulligan when hand has <2 or >5 lands)
    p_two_plus = _hypergeom_at_least(library_size, lands, min(library_size, 7), 2)
    p_six_plus = _hypergeom_at_least(library_size, lands, min(library_size, 7), 6)
    p_mull = (1.0 - p_two_plus) + p_six_plus
    two_plus_lands = min(1.0, (p_two_plus - p_six_plus) + p_mull * p_two_plus)
    untapped_share = (speed_counts["untapped"] + 0.85 * speed_counts["conditional"]) / max(1, lands) if lands else 1.0

    # EDHcheck 0-100 gradeManaBase
    score = 100
    factors: list[dict[str, Any]] = []
    tp_pen = 55 if tipping_80 is None else (0 if tipping_80 <= 2 else 6 if tipping_80 == 3 else 16 if tipping_80 == 4 else 28 if tipping_80 == 5 else 40 if tipping_80 == 6 else 50)
    if tp_pen > 0:
        score -= tp_pen
        factors.append({"label": "Never reaches 80% on-curve consistency" if tipping_80 is None else f"Tipping point turn {tipping_80}", "impact": -tp_pen})
    total_deficit = sum(r["deficit"] for r in color_reqs)
    def_pen = min(15, 3 * total_deficit)
    if def_pen > 0:
        score -= def_pen
        factors.append({"label": f"{total_deficit} missing colored source(s)", "impact": -def_pen})
    if two_plus_lands < 0.90:
        op_pen = min(12, round((0.90 - two_plus_lands) * 80))
        if op_pen > 0:
            score -= op_pen
            factors.append({"label": f"Only {round(two_plus_lands * 100)}% of 7-card hands have 2+ lands", "impact": -op_pen})
    if untapped_share < 0.85:
        ut_pen = min(10, round((0.85 - untapped_share) * 50))
        if ut_pen > 0:
            score -= ut_pen
            factors.append({"label": f"Lands enter tapped too often (effective untapped {round(untapped_share * 100)}%)", "impact": -ut_pen})
    if overall_cast_rate < 0.95:
        cr_pen = min(15, round((0.95 - overall_cast_rate) * 60))
        if cr_pen > 0:
            score -= cr_pen
            factors.append({"label": f"Overall on-curve color cast rate {round(overall_cast_rate * 100, 1)}%", "impact": -cr_pen})

    score = max(0, min(100, round(score)))
    letter = (
        "S" if score >= 93 else "A+" if score >= 88 else "A" if score >= 83 else "A-" if score >= 78 else
        "B+" if score >= 73 else "B" if score >= 67 else "B-" if score >= 61 else "C+" if score >= 55 else
        "C" if score >= 48 else "C-" if score >= 42 else "D+" if score >= 36 else "D" if score >= 30 else "D-"
    )

    return {
        "grade": {"letter": letter, "score": score, "factors": factors},
        "lands": lands,
        "recommended_land_count": rec_lands,
        "land_count_delta": lands - rec_lands,
        "ramp_count": ramp_count,
        "average_cmc_nonland": round(avg_cmc, 2),
        "tipping_point": {"turn_80_pct": tipping_80, "turn_90_pct": tipping_90, "target_mana": target_mana},
        "opener_two_plus_lands_pct": round(two_plus_lands * 100, 1),
        "overall_on_curve_cast_pct": round(overall_cast_rate * 100, 1),
        "speed_breakdown": {
            "untapped": speed_counts["untapped"],
            "conditional": speed_counts["conditional"],
            "tapped": speed_counts["tapped"],
            "effective_untapped_pct": round(untapped_share * 100, 1),
        },
        "color_requirements": color_reqs,
        "cast_rate_by_color": cast_rate_by_color,
        "land_groups": sorted(groups.values(), key=lambda g: (-g["count"], g["slug"])),
    }


def compare_decks_analysis(
    deck_a: ParsedDeck,
    deck_b: ParsedDeck,
    cards: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compare two decklists side by side (EDHcheck Deck Compare)."""
    counts_a: Counter[str] = Counter()
    counts_b: Counter[str] = Counter()
    display: dict[str, str] = {}
    for e in deck_a.playing:
        c = cards.get(e.name.lower())
        name = c.get("name", e.name) if c else e.name
        key = name.lower()
        display[key] = name
        counts_a[key] += e.quantity
    for e in deck_b.playing:
        c = cards.get(e.name.lower())
        name = c.get("name", e.name) if c else e.name
        key = name.lower()
        display[key] = name
        counts_b[key] += e.quantity

    all_keys = sorted(set(counts_a) | set(counts_b))
    added = [{"card": display[k], "qty": counts_b[k] - counts_a[k]} for k in all_keys if counts_b[k] > counts_a[k]]
    removed = [{"card": display[k], "qty": counts_a[k] - counts_b[k]} for k in all_keys if counts_a[k] > counts_b[k]]
    shared = sum(min(counts_a[k], counts_b[k]) for k in all_keys)
    union = max(1, sum(max(counts_a[k], counts_b[k]) for k in all_keys))
    similarity_pct = round(shared / union * 100, 1)

    rep_a = analyze(deck_a, cards)
    rep_b = analyze(deck_b, cards)

    def delta(val_a: float, val_b: float, ndigits: int = 2) -> dict[str, Any]:
        diff = round(val_b - val_a, ndigits)
        return {"before": val_a, "after": val_b, "delta": diff}

    return {
        "commanders_before": rep_a["commanders"],
        "commanders_after": rep_b["commanders"],
        "similarity_pct": similarity_pct,
        "cards_added": added,
        "cards_removed": removed,
        "deltas": {
            "bracket": delta(rep_a["bracket"]["bracket"], rep_b["bracket"]["bracket"], 0),
            "power_score": delta(rep_a["power_score"]["total"], rep_b["power_score"]["total"], 1),
            "speed": delta(rep_a["power_score"]["speed"], rep_b["power_score"]["speed"], 1),
            "consistency": delta(rep_a["power_score"]["consistency"], rep_b["power_score"]["consistency"], 1),
            "school_score": delta(rep_a["school_score"]["total"], rep_b["school_score"]["total"], 1),
            "average_cmc_nonland": delta(rep_a["average_cmc_nonland"], rep_b["average_cmc_nonland"], 2),
            "lands": delta(rep_a["lands"], rep_b["lands"], 0),
            "ramp": delta(rep_a["roles"]["counts"].get("ramp", 0), rep_b["roles"]["counts"].get("ramp", 0), 0),
            "card_draw": delta(rep_a["roles"]["counts"].get("card_draw", 0), rep_b["roles"]["counts"].get("card_draw", 0), 0),
            "interaction_total": delta(rep_a["roles"]["counts"].get("interaction_total", 0), rep_b["roles"]["counts"].get("interaction_total", 0), 0),
            "tutors": delta(rep_a["roles"]["counts"].get("tutor", 0), rep_b["roles"]["counts"].get("tutor", 0), 0),
            "game_changers": delta(len(rep_a["game_changers"]), len(rep_b["game_changers"]), 0),
            "price_usd": delta(rep_a["price"]["total_usd"], rep_b["price"]["total_usd"], 2),
        },
        "game_changers_added": sorted(set(rep_b["game_changers"]) - set(rep_a["game_changers"])),
        "game_changers_removed": sorted(set(rep_a["game_changers"]) - set(rep_b["game_changers"])),
    }


def evaluate_pod(seats: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare 2-4 analyzed decks for Rule 0 table balance (EDHcheck Pod Checker)."""
    brackets = [s["analysis"]["bracket"]["bracket"] for s in seats]
    powers = [s["analysis"]["power_score"]["total"] for s in seats]
    speeds = [s["analysis"]["power_score"]["speed"] for s in seats]

    b_spread = max(brackets) - min(brackets) if brackets else 0
    p_spread = round(max(powers) - min(powers), 1) if powers else 0.0
    s_spread = round(max(speeds) - min(speeds), 1) if speeds else 0.0
    p_avg = sum(powers) / len(powers) if powers else 0.0
    b_max, b_min = max(brackets, default=0), min(brackets, default=0)

    outliers: list[dict[str, Any]] = []
    for s in seats:
        b = s["analysis"]["bracket"]["bracket"]
        p = s["analysis"]["power_score"]["total"]
        if b_spread >= 2 and b == b_max and brackets.count(b_max) == 1:
            outliers.append({"seat": s["name"], "direction": "above", "reason": f"Bracket {b} against a pod of Bracket {b_min}–{max(x for x in brackets if x != b_max)}"})
        elif b_spread >= 2 and b == b_min and brackets.count(b_min) == 1:
            outliers.append({"seat": s["name"], "direction": "below", "reason": f"Bracket {b} against a pod of Bracket {min(x for x in brackets if x != b_min)}+"})
        elif b_spread <= 1 and p_spread >= 2.0 and p - p_avg >= 1.2:
            outliers.append({"seat": s["name"], "direction": "above", "reason": f"Power {p:.1f} against a pod average of {p_avg:.1f}"})

    if b_spread >= 2:
        verdict = "mismatched"
        headline = "Mismatched pod"
        detail = f"These decks are {b_spread} brackets apart. The lower-bracket decks are unlikely to interact with what the higher-bracket deck is doing."
    elif b_spread == 1 and p_spread >= 2.5:
        verdict = "uneven"
        headline = "Uneven pod"
        detail = f"One bracket apart with a {p_spread:.1f}-point power gap. Expect the top deck to draw table attention early."
    elif b_spread == 1 or p_spread >= 1.5:
        verdict = "slight"
        headline = "Close pod, slight edge"
        detail = f"Within one bracket and a {p_spread:.1f}-point power spread. Competitive games with a mild favourite."
    else:
        verdict = "balanced"
        headline = "Balanced pod"
        detail = f"Same bracket, {p_spread:.1f} points between strongest and weakest. Built for the same game."

    if s_spread >= 3.0:
        detail += f" Speed varies noticeably ({s_spread:.1f} points), so one deck sets the clock."

    seat_summaries = []
    for s in seats:
        a = s["analysis"]
        flags = a["bracket"]["flags"]
        notes: list[str] = []
        if flags["game_changers"]:
            notes.append(f"{len(flags['game_changers'])} Game Changer(s): {', '.join(flags['game_changers'])}")
        if flags["two_card_combos"]:
            notes.append(f"{len(flags['two_card_combos'])} two-card combo(s)")
        if flags["early_two_card_combo"]:
            notes.append("early combo potential")
        tutors = a["roles"]["counts"].get("tutor", 0)
        if tutors >= 5:
            notes.append(f"{tutors} tutors")
        if flags["fast_mana"]:
            notes.append(f"{len(flags['fast_mana'])} fast mana")
        if flags["extra_turns"]:
            notes.append(f"{len(flags['extra_turns'])} extra turns")
        if flags["mass_land_denial"]:
            notes.append(f"mass land denial ({', '.join(flags['mass_land_denial'])})")
        seat_summaries.append({
            "seat": s["name"],
            "commanders": a["commanders"],
            "bracket": a["bracket"]["bracket"],
            "bracket_label": a["bracket"]["label"],
            "power_score": a["power_score"]["total"],
            "speed_score": a["power_score"]["speed"],
            "consistency_score": a["power_score"]["consistency"],
            "median_commander_turn": s.get("median_commander_turn"),
            "rule_zero_notes": notes,
        })

    return {
        "verdict": verdict,
        "headline": headline,
        "detail": detail,
        "bracket_spread": b_spread,
        "power_spread": p_spread,
        "speed_spread": s_spread,
        "outliers": outliers,
        "seats": seat_summaries,
    }


_TOKEN_DOUBLERS = frozenset({
    "doubling season", "parallel lives", "anointed procession", "primal vigor",
    "mondrak, glory dominus", "adrix and nev, twincasters", "ojer taq, deepest foundation",
    "chatterfang, squirrel general",
})
_TOKEN_BATCH_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_CREATE_TOKEN_RE = re.compile(
    r"creates?\s+(a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+|x)\s+([^.;\n]*?\btokens?)",
    re.IGNORECASE,
)


def collect_deck_tokens(deck: ParsedDeck, cards: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Identify every token and helper marker a deck creates and estimate how many copies to bring."""
    entries = [(e, cards.get(e.name.lower())) for e in deck.playing]
    resolved = [(e, c) for e, c in entries if c is not None]
    doublers = [c.get("name", e.name) for e, c in resolved if _front_lower(c.get("name", e.name)) in _TOKEN_DOUBLERS]

    by_token: dict[str, dict[str, Any]] = {}
    for e, c in resolved:
        card_name = c.get("name", e.name)
        text = oracle_text(c)
        text_low = text.lower()
        repeatable = bool(re.search(r"\bwhenever\b|\bat the beginning of\b|\beach (?:turn|combat|upkeep|end step)\b", text_low)) or ":" in text_low

        # 1. Scryfall all_parts token references if present; otherwise fallback to oracle regex
        parts = [p for p in (c.get("all_parts") or []) if p.get("component") == "token"]
        if parts:
            for part in parts:
                tname = part.get("name") or "Token"
                tkey = f"{tname}|{part.get('type_line', '')}".lower()
                scales = "for each" in text_low or "create x " in text_low
                item = by_token.setdefault(tkey, {
                    "name": tname,
                    "type_line": part.get("type_line", "Token"),
                    "scryfall_uri": part.get("uri"),
                    "sources": [],
                    "max_batch": 1,
                    "repeatable": False,
                    "scales": False,
                })
                if card_name not in item["sources"]:
                    item["sources"].append(card_name)
                item["repeatable"] = item["repeatable"] or repeatable
                item["scales"] = item["scales"] or scales
        else:
            for m in _CREATE_TOKEN_RE.finditer(text):
                cnt_raw, desc = m.group(1).lower(), m.group(2).strip()
                scales = cnt_raw == "x" or "for each" in text_low
                batch = 3 if scales else (_TOKEN_BATCH_WORDS.get(cnt_raw) or (int(cnt_raw) if cnt_raw.isdigit() else 1))
                tkey = re.sub(r"\btokens?\b", "token", desc.lower()).strip()
                item = by_token.setdefault(tkey, {
                    "name": desc,
                    "type_line": "Token",
                    "sources": [],
                    "max_batch": 1,
                    "repeatable": False,
                    "scales": False,
                })
                if card_name not in item["sources"]:
                    item["sources"].append(card_name)
                item["max_batch"] = max(item["max_batch"], batch)
                item["repeatable"] = item["repeatable"] or repeatable
                item["scales"] = item["scales"] or scales

    tokens_out = []
    for item in by_token.values():
        qty = max(len(item["sources"]), item["max_batch"])
        reasons: list[str] = []
        if len(item["sources"]) > 1:
            reasons.append(f"{len(item['sources'])} cards create it")
        elif item["max_batch"] > 1:
            reasons.append(f"creates {item['max_batch']} at once")
        if item["scales"]:
            qty = max(qty, 10)
            reasons.append("scales with board")
        elif item["repeatable"]:
            qty = max(qty, 6)
            reasons.append("repeatable trigger/ability")
        if doublers:
            qty *= 2
            reasons.append(f"doubled by {', '.join(doublers)}")
        qty = max(1, min(12, qty))
        tokens_out.append({
            "token": item["name"],
            "type_line": item["type_line"],
            "suggested_quantity": qty,
            "reason": ", ".join(reasons).capitalize() if reasons else "One-shot effect",
            "created_by": sorted(item["sources"]),
        })

    tokens_out.sort(key=lambda t: (-t["suggested_quantity"], t["token"]))
    return {
        "total_distinct_tokens": len(tokens_out),
        "total_suggested_cards": sum(t["suggested_quantity"] for t in tokens_out),
        "token_doublers_in_deck": doublers,
        "tokens": tokens_out,
    }


def _is_basic(card: dict[str, Any]) -> bool:
    return "Basic" in (card.get("type_line") or "") and "Land" in (card.get("type_line") or "")


def _copy_limit(card: dict[str, Any], singleton: bool) -> int | None:
    """Max copies allowed; None means unlimited."""
    text = oracle_text(card).lower()
    if _is_basic(card) or _ANY_NUMBER.search(text):
        return None
    m = _UP_TO_N.search(text)
    if m:
        words = {"seven": 7, "nine": 9}
        return words.get(m.group(1), int(m.group(1)) if m.group(1).isdigit() else None)
    return 1 if singleton else 4


def analyze(
    deck: ParsedDeck,
    cards: dict[str, dict[str, Any]],
    *,
    fmt: str = "commander",
    budget_per_card: float | None = None,
    template: dict[str, int] | None = None,
    combos: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fmt = fmt.lower()
    targets = resolve_template(template)
    singleton = fmt in {"commander", "brawl", "standardbrawl", "oathbreaker", "duel", "paupercommander", "predh"}
    entries = [(e, cards.get(e.name.lower())) for e in deck.playing]
    resolved = [(e, c) for e, c in entries if c is not None]
    missing = [e.name for e, c in entries if c is None]

    total = sum(e.quantity for e, _ in entries)
    type_counts: Counter[str] = Counter()
    curve: Counter[str] = Counter()
    pips: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    roles: dict[str, list[str]] = defaultdict(list)
    nonland_cmc: list[float] = []
    lands = 0

    for e, c in resolved:
        tl = front_type_line(c)
        for t in ("Creature", "Instant", "Sorcery", "Artifact", "Enchantment", "Planeswalker", "Battle", "Land"):
            if t in tl:
                type_counts[t] += e.quantity
        is_land = "Land" in tl
        if is_land:
            lands += e.quantity
            produced = c.get("produced_mana") or []
            for color in COLORS:
                if color in produced:
                    sources[color] += e.quantity
        else:
            cmc = float(c.get("cmc") or 0)
            nonland_cmc.extend([cmc] * e.quantity)
            bucket = str(int(cmc)) if cmc < 7 else "7+"
            curve[bucket] += e.quantity
            cost = c.get("mana_cost") or ((c.get("card_faces") or [{}])[0].get("mana_cost", ""))
            p = _pips(cost)
            for k, v in p.items():
                pips[k] += v * e.quantity
        detected_roles = list(card_roles(c))
        if not is_land and not detected_roles and e.categories:
            for cat in e.categories:
                mapped = _ENTRY_CATEGORY_TO_ROLE.get(cat.strip().lower())
                if mapped and mapped not in detected_roles:
                    detected_roles.append(mapped)
        for r in detected_roles:
            roles[r].append(c.get("name", e.name))

    # ---- Commander colour identity ----
    commander_cards = [cards.get(e.name.lower()) for e in deck.commanders]
    identity: set[str] = set()
    for c in commander_cards:
        if c:
            identity |= set(c.get("color_identity") or [])

    # ---- Legality ----
    issues: list[str] = []
    if fmt == "commander":
        if total != 100:
            issues.append(f"Commander decks must be exactly 100 cards including the commander; this list has {total}.")
        if not deck.commanders:
            issues.append("No commander identified. Mark it with a 'Commander' section, *CMDR*, or pass it explicitly.")
    elif fmt in {"standard", "pioneer", "modern", "legacy", "vintage", "pauper", "historic", "timeless", "explorer", "alchemy"}:
        if total < 60:
            issues.append(f"{fmt.title()} decks need at least 60 main-deck cards; this list has {total}.")
        side = sum(e.quantity for e in deck.sideboard)
        if side > 15:
            issues.append(f"Sideboard has {side} cards; the maximum is 15.")

    not_legal: list[dict[str, str]] = []
    copies: Counter[str] = Counter()
    by_name: dict[str, dict[str, Any]] = {}
    for e, c in resolved:
        name = c.get("name", e.name)
        copies[name] += e.quantity
        by_name[name] = c
        status = (c.get("legalities") or {}).get(fmt)
        if status and status != "legal" and not (status == "restricted" and e.quantity == 1):
            not_legal.append({"card": name, "status": status})
        if identity and deck.commanders and fmt == "commander":
            outside = set(c.get("color_identity") or []) - identity
            if outside:
                issues.append(f"{name} is outside the commander's colour identity (has {''.join(sorted(outside))}).")
    for name, n in copies.items():
        limit = _copy_limit(by_name[name], singleton)
        if limit is not None and n > limit:
            issues.append(f"{n} copies of {name}; the limit is {limit}.")
    if not_legal:
        issues.append(f"{len(not_legal)} card(s) not legal in {fmt}: " + ", ".join(f"{x['card']} ({x['status']})" for x in not_legal))

    # ---- Price ----
    priced: list[tuple[str, float, int]] = []
    unpriced: list[str] = []
    for e, c in resolved:
        p = price_usd(c)
        if p is None:
            unpriced.append(c.get("name", e.name))
        else:
            priced.append((c.get("name", e.name), p, e.quantity))
    total_price = round(sum(p * q for _, p, q in priced), 2)
    priciest = sorted(priced, key=lambda x: -x[1])[:10]
    over_budget = [{"card": n, "usd": p} for n, p, _ in priced if budget_per_card is not None and p > budget_per_card]

    game_changers = sorted({c.get("name", e.name) for e, c in resolved if _is_game_changer(c, e.name)})

    # ---- Role comparison against rules of thumb ----
    role_counts = {r: len(v) for r, v in roles.items()}
    interaction = len(set(roles.get("removal", [])) | set(roles.get("counterspell", [])) | set(roles.get("board_wipe", [])))
    template_report = None
    nonland_all = [c for _, c in resolved if "Land" not in front_type_line(c)]
    if fmt == "commander":
        nonland = [c for e, c in resolved if "Land" not in front_type_line(c) and e not in deck.commanders]
        slots = 100 - max(len(deck.commanders), 1)
        template_report = _template_report(nonland, lands, targets, slots)

    avg_cmc = round(sum(nonland_cmc) / len(nonland_cmc), 2) if nonland_cmc else 0.0
    curve_order = ["0", "1", "2", "3", "4", "5", "6", "7+"]

    bracket_report, power_report, synergy_report, school_report = _score_and_bracket(
        resolved=resolved,
        nonland_cards=nonland_all,
        lands=lands,
        avg_cmc=avg_cmc,
        roles=roles,
        interaction_total=interaction,
        game_changers=game_changers,
        spellbook_combos=combos,
    )

    return {
        "format": fmt,
        "card_count": total,
        "commanders": [c.get("name") for c in commander_cards if c],
        "color_identity": "".join(c for c in COLORS if c in identity) or None,
        "legal": not issues,
        "legality_issues": issues,
        "bracket": bracket_report,
        "power_score": power_report,
        "school_score": school_report,
        "synergy": synergy_report,
        "types": dict(type_counts.most_common()),
        "mana_curve_nonland": {k: curve.get(k, 0) for k in curve_order},
        "average_cmc_nonland": avg_cmc,
        "lands": lands,
        "color_pips": {c: pips[c] for c in COLORS if pips[c]},
        "land_color_sources": {c: sources[c] for c in COLORS if sources[c]},
        "roles": {
            "counts": {**role_counts, "interaction_total": interaction},
            "cards": {r: sorted(v) for r, v in roles.items()},
            "note": (
                "Roles are tagged heuristically from oracle text; verify borderline cards. "
                "card_draw is every draw. draw_on_cast happens when the spell resolves, "
                "draw_on_hit waits for combat damage, draw_on_their_spell waits for an opponent to cast a spell. "
                "A draw with no gate still counts as card_draw."
            ),
        },
        "template": template_report,
        "game_changers": game_changers,
        "price": {
            "total_usd": total_price,
            "most_expensive": [{"card": n, "usd": p} for n, p, _ in priciest],
            "no_price_listed": unpriced,
            "over_budget": over_budget or None,
            "source": "Scryfall (TCGplayer market, cheapest listed finish of the printing Scryfall returned)",
        },
        "cards_not_found": missing,
        "sideboard_count": sum(e.quantity for e in deck.sideboard),
        "maybeboard_count": sum(e.quantity for e in deck.maybe),
    }
